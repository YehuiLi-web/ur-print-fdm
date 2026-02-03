from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu
from PyQt6.QtGui import QColor, QFont, QAction
from PyQt6.QtCore import Qt, pyqtSignal
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme

try:
    from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs
except ImportError:
    # 极简兜底方案
    from PyQt6.QtWidgets import QPlainTextEdit as QsciScintilla
    QsciLexerPython = None
    QsciAPIs = None

from .dialogs import FindReplaceDialog

class CodeEditor(QsciScintilla):
    """
    经过彻底修复和优化的专业 URScript 编辑器内核。
    基于 QScintilla，专为处理大型 3D 打印脚本设计。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_qsci = QsciLexerPython is not None
        self._find_dialog = None
        self._find_replace_dialog = None
        self.setup_editor()
        self.apply_theme()

    def setup_editor(self):
        if not self._is_qsci:
            return
        
        # 设置滚动条样式 - VSCode 风格（无轨道背景，直接浮在内容上）
        self.setStyleSheet("""
            QsciScintilla {
                border: none;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 14px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(121, 121, 121, 0.2);
                min-height: 20px;
                border-radius: 0;
                margin: 0 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(121, 121, 121, 0.5);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(121, 121, 121, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
                background: #1e1e1e;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: #1e1e1e;
            }
            QScrollBar:horizontal {
                background: #1e1e1e;
                height: 14px;
                margin: 0;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: rgba(121, 121, 121, 0.2);
                min-width: 20px;
                border-radius: 0;
                margin: 3px 0;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(121, 121, 121, 0.5);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0;
                background: #1e1e1e;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: #1e1e1e;
            }
            QAbstractScrollArea::corner {
                background: #1e1e1e;
            }
        """)

        # --- 0. 字体定义 (提前定义以供后续引用) ---
        font = QFont("Consolas", 11)
        font.setFixedPitch(True)

        # --- 1. 语法高亮与词法分析 ---
        self.lexer = QsciLexerPython()
        self.lexer.setDefaultPaper(QColor("#1e1e1e"))
        self.lexer.setDefaultColor(QColor("#d4d4d4"))
        self.lexer.setFont(font)
        self.setFont(font)

        # 定制 Python 词法颜色 (适配 URScript 风格)
        self.lexer.setColor(QColor("#858585"), QsciLexerPython.Operator)    # 操作符
        self.lexer.setColor(QColor("#6A9955"), QsciLexerPython.Comment)     # 注释
        self.lexer.setColor(QColor("#569CD6"), QsciLexerPython.Keyword)     # 关键字
        self.lexer.setColor(QColor("#B5CEA8"), QsciLexerPython.Number)      # 数字
        self.lexer.setColor(QColor("#CE9178"), QsciLexerPython.DoubleQuotedString)
        self.lexer.setColor(QColor("#CE9178"), QsciLexerPython.SingleQuotedString)

        # 兼容性处理：不同版本的 FunctionMethodName 定义可能不同
        func_attr = "FunctionMethodName" if hasattr(QsciLexerPython, "FunctionMethodName") else "ClassName"
        self.lexer.setColor(QColor("#DCDCAA"), getattr(QsciLexerPython, func_attr))

        # --- 2. 自动补全 API 注入 ---
        self.api = QsciAPIs(self.lexer)
        ur_commands = [
            "movel", "movej", "movec", "speedl", "speedj", "servoj", "servoc", "speed_stop",
            "get_actual_tcp_pose", "get_actual_joint_positions", "set_tcp", "set_payload",
            "sleep", "textmsg", "popup", "d2r", "r2d", "sin", "cos", "tan", "sqrt", "log", "exp", "not",
            "modbus_set_output_register", "set_standard_digital_out", "stopl", "stopj",
            "pose_trans", "pose_inv", "pose_add",
            "set_tool_digital_out", "wait_wait", "get_inverse_kin", "def", "end", "thread", "global", "local",
            "get_standard_digital_in", "get_tool_digital_in"
        ]
        for cmd in ur_commands:
            self.api.add(cmd)
        self.api.prepare()

        self.setLexer(self.lexer)

        # --- 3. 基础编辑器行为 ---
        self.setUtf8(True)
        self.setSelectionBackgroundColor(QColor("#264f78"))
        self.setSelectionForegroundColor(QColor("#d4d4d4"))
        self.setCaretForegroundColor(QColor("#aeafad"))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#2a2d32"))
        self.setCaretWidth(2)

        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(2)
        self.setTabWidth(2)
        self.setAutoIndent(True)

        # 缩进引导线
        self.setIndentationGuides(True)
        self.setIndentationGuidesBackgroundColor(QColor("#3e3e42"))
        self.setIndentationGuidesForegroundColor(QColor("#3e3e42"))

        # --- 4. 侧边栏 (行号与折叠) ---
        # 行号边距 (Margin 0)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "  000  ")  # 预留足够宽度 + 两侧padding
        self.setMarginsBackgroundColor(QColor("#1e1e1e"))  # 与编辑器背景一致
        self.setMarginsForegroundColor(QColor("#6e7681"))  # 行号颜色，稍亮
        self.setMarginLineNumbers(0, True)

        # 当前行行号高亮
        # QScintilla 原生不支持单独高亮当前行号，但可以通过以下方式优化视觉效果

        # 添加一个细分隔线边距 (Margin 1) - 分隔行号和代码
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 2)  # 2像素宽的分隔
        self.setMarginSensitivity(1, False)
        # 分隔线使用稍暗的颜色
        self.setMarginBackgroundColor(1, QColor("#2d2d30"))

        # 折叠边距颜色
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
        self.setFoldMarginColors(QColor("#2d2d30"), QColor("#1e1e1e"))  # 前景/背景
        # 设置折叠标记颜色
        self.setMarkerBackgroundColor(QColor("#569CD6"), QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerForegroundColor(QColor("#1e1e1e"), QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerBackgroundColor(QColor("#569CD6"), QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.setMarkerForegroundColor(QColor("#1e1e1e"), QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.setMarkerBackgroundColor(QColor("#569CD6"), QsciScintilla.SC_MARKNUM_FOLDEREND)
        self.setMarkerBackgroundColor(QColor("#569CD6"), QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
        self.setMarkerBackgroundColor(QColor("#404040"), QsciScintilla.SC_MARKNUM_FOLDERSUB)
        self.setMarkerBackgroundColor(QColor("#404040"), QsciScintilla.SC_MARKNUM_FOLDERTAIL)
        self.setMarkerBackgroundColor(QColor("#404040"), QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)

        # 设置行号样式 (Style 33)
        self.setMarginsFont(font)  # 使用相同字体
        self.setMarginsForegroundColor(QColor("#6e7681"))  # VS Code 风格灰色

        # --- 5. 自动补全配置 ---
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        # --- 6. 括号匹配 ---
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceBackgroundColor(QColor("#3e3e42"))
        self.setMatchedBraceForegroundColor(QColor("#ffcc00"))

        # --- 7. 字体 ---
        font = QFont("Consolas", 11)
        font.setFixedPitch(True)
        self.lexer.setFont(font)
        self.setFont(font)

        # --- 8. 点击行号选中整行 ---
        self.setMarginSensitivity(0, True)
        self.marginClicked.connect(self._on_margin_clicked)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def apply_theme(self) -> None:
        """Apply the current application theme to editor colors (QScintilla + fallback)."""
        t = theme.current_tokens()
        use_dark = t is theme.DARK

        if not self._is_qsci:
            self.setStyleSheet(f"background-color: {t['bg_secondary']}; color: {t['text']};")
            return

        # Scrollbars: keep VSCode-like floating handle, but theme-aware.
        self.setStyleSheet(
            f"""
            QsciScintilla {{
                border: none;
            }}
            QScrollBar:vertical {{
                background: {t["bg_secondary"]};
                width: 14px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {t["scroll_handle"]};
                min-height: 20px;
                border-radius: 0;
                margin: 0 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t["scroll_handle_hover"]};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {t["scroll_handle_pressed"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                background: {t["bg_secondary"]};
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: {t["bg_secondary"]};
            }}
            QScrollBar:horizontal {{
                background: {t["bg_secondary"]};
                height: 14px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {t["scroll_handle"]};
                min-width: 20px;
                border-radius: 0;
                margin: 3px 0;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t["scroll_handle_hover"]};
            }}
            QScrollBar::handle:horizontal:pressed {{
                background: {t["scroll_handle_pressed"]};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
                background: {t["bg_secondary"]};
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: {t["bg_secondary"]};
            }}
            QAbstractScrollArea::corner {{
                background: {t["bg_secondary"]};
            }}
            """
        )

        # Base paper/ink
        self.lexer.setDefaultPaper(QColor(t["bg_secondary"]))
        self.lexer.setDefaultColor(QColor(t["text"]))
        # Also set editor-level defaults to avoid fallback black text on light themes.
        try:
            self.setPaper(QColor(t["bg_secondary"]))
            self.setColor(QColor(t["text"]))
        except Exception:
            pass
        # Ensure style 0 ("Default") matches the theme (some QScintilla builds keep an internal default).
        try:
            self.lexer.setPaper(QColor(t["bg_secondary"]), 0)
            self.lexer.setColor(QColor(t["text"]), 0)
        except Exception:
            pass

        # Syntax colors (simple, high-contrast palettes)
        if use_dark:
            syntax = {
                "op": "#858585",
                "comment": "#6A9955",
                "keyword": "#569CD6",
                "number": "#B5CEA8",
                "string": "#CE9178",
                "func": "#DCDCAA",
            }
        else:
            syntax = {
                "op": t["text_muted"],
                "comment": "#6a737d",
                "keyword": "#0550ae",
                "number": "#953800",
                "string": "#0a3069",
                "func": "#8250df",
            }

        self.lexer.setColor(QColor(syntax["op"]), QsciLexerPython.Operator)
        self.lexer.setColor(QColor(syntax["comment"]), QsciLexerPython.Comment)
        self.lexer.setColor(QColor(syntax["keyword"]), QsciLexerPython.Keyword)
        self.lexer.setColor(QColor(syntax["number"]), QsciLexerPython.Number)
        self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.DoubleQuotedString)
        self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.SingleQuotedString)

        func_attr = "FunctionMethodName" if hasattr(QsciLexerPython, "FunctionMethodName") else "ClassName"
        self.lexer.setColor(QColor(syntax["func"]), getattr(QsciLexerPython, func_attr))

        # Ensure lexer is active and re-colorize the document.
        try:
            self.setLexer(self.lexer)
            self.colorize(0, -1)
        except Exception:
            pass

        # Selection / caret
        self.setSelectionBackgroundColor(QColor(t["selection_bg"]))
        self.setSelectionForegroundColor(QColor(t["text"]))
        self.setCaretForegroundColor(QColor(t["text"]))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(t["bg_hover"]))

        # Margins
        margin_bg = t["bg_secondary"] if use_dark else t["bg_tertiary"]
        self.setMarginsBackgroundColor(QColor(margin_bg))
        self.setMarginsForegroundColor(QColor(t["text_dim"]))
        self.setMarginBackgroundColor(1, QColor(t["border_light"]))

        # Folding markers
        self.setFoldMarginColors(QColor(t["bg_tertiary"]), QColor(t["bg_secondary"]))
        self.setMarkerBackgroundColor(QColor(t["accent_link"]), QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerForegroundColor(QColor(t["bg_secondary"]), QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerBackgroundColor(QColor(t["accent_link"]), QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.setMarkerForegroundColor(QColor(t["bg_secondary"]), QsciScintilla.SC_MARKNUM_FOLDEROPEN)

        # Brace match
        self.setMatchedBraceBackgroundColor(QColor(t["bg_hover_strong"]))
        self.setMatchedBraceForegroundColor(QColor(t["accent_blue"]))

    def _on_margin_clicked(self, margin, line, modifiers):
        """点击行号边距时选中整行"""
        if margin == 0:  # 行号边距
            self.setSelection(line, 0, line + 1, 0)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        find_act = QAction("查找和替换 (Ctrl+H)", self)
        find_act.setIcon(IconManager().get_svg_icon('search', (16, 16)))
        find_act.triggered.connect(self.show_find_replace_dialog)
        menu.addAction(find_act)
        menu.addSeparator()
        menu.addAction("撤销", self.undo)
        menu.addAction("重做", self.redo)
        menu.addSeparator()
        menu.addAction("剪切", self.cut)
        menu.addAction("复制", self.copy)
        menu.addAction("粘贴", self.paste)
        menu.exec(self.mapToGlobal(pos))

    def keyPressEvent(self, event):
        # Ctrl+H: 查找替换
        if event.key() == Qt.Key.Key_H and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_find_replace_dialog()
        # Ctrl+F: 仅查找
        elif event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.show_find_dialog()
        else:
            super().keyPressEvent(event)

    def show_find_dialog(self):
        """显示查找对话框（仅查找，无替换功能）"""
        if self._find_dialog is None:
            self._find_dialog = FindReplaceDialog(self, find_only=True)
        self._find_dialog.set_find_only_mode(True)
        self._find_dialog.show()
        self._find_dialog.raise_()
        self._find_dialog.activateWindow()
        # 如果有选中文本，自动填入查找框
        if self.hasSelectedText():
            self._find_dialog.find_input.setText(self.selectedText())

    def show_find_replace_dialog(self):
        """显示查找替换对话框（完整功能）"""
        if self._find_replace_dialog is None:
            self._find_replace_dialog = FindReplaceDialog(self, find_only=False)
        self._find_replace_dialog.set_find_only_mode(False)
        self._find_replace_dialog.show()
        self._find_replace_dialog.raise_()
        self._find_replace_dialog.activateWindow()
        # 如果有选中文本，自动填入查找框
        if self.hasSelectedText():
            self._find_replace_dialog.find_input.setText(self.selectedText())

    def highlight_line(self, line_num):
        """高亮指定行 (用于生产追踪)"""
        self.setCursorPosition(line_num, 0)
        self.ensureLineVisible(line_num)

    # === 兼容性映射 ===
    def toPlainText(self):
        return self.text()

    def setPlainText(self, text):
        self.setText(text if text else "")
        self._update_margin_width()

    def _update_margin_width(self):
        """根据行数动态调整行号边距宽度"""
        if not self._is_qsci:
            return
        lines = self.lines()
        # 计算需要的位数，至少2位 + 左右padding
        digits = max(2, len(str(lines)))
        self.setMarginWidth(0, " " + "0" * digits + " ")

    def setPlaceholderText(self, text):
        pass
