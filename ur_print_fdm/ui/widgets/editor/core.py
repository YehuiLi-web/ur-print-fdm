from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu
from PyQt6.QtGui import QColor, QFont, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme
from ur_print_fdm.ui.mixins.theme_aware import ThemeAwareMixin

try:
    from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciAPIs
except ImportError:
    # 极简兜底方案
    from PyQt6.QtWidgets import QPlainTextEdit as QsciScintilla
    QsciLexerPython = None
    QsciAPIs = None

from .dialogs import FindReplaceDialog
from .urscript_lexer import URScriptLexer, ALL_URSCRIPT_COMMANDS, get_urscript_completions

class CodeEditor(QsciScintilla, ThemeAwareMixin):
    """
    经过彻底修复和优化的专业 URScript 编辑器内核。
    基于 QScintilla，专为处理大型 3D 打印脚本设计。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_theme_awareness()  # 设置主题感知
        self._is_qsci = QsciLexerPython is not None
        self._find_dialog = None
        self._find_replace_dialog = None
        self._scrollbar_visible = False  # 滚动条悬停状态
        self.setup_editor()
        self.apply_theme()
        # 安装事件过滤器以检测鼠标悬停
        self.installEventFilter(self)
        self.setMouseTracking(True)

    def eventFilter(self, obj, event):
        """事件过滤器，用于处理鼠标悬停事件控制滚动条显示"""
        if obj == self:
            if event.type() == QEvent.Type.Enter:
                self._show_scrollbar(True)
            elif event.type() == QEvent.Type.Leave:
                self._show_scrollbar(False)
        return super().eventFilter(obj, event)

    def _show_scrollbar(self, visible: bool):
        """显示或隐藏滚动条"""
        if self._scrollbar_visible == visible:
            return
        self._scrollbar_visible = visible

        t = theme.current_tokens()
        scrollbar = self.verticalScrollBar()
        if visible:
            # 显示滚动条
            scrollbar.setStyleSheet(f"""
                QScrollBar:vertical {{
                    border: none;
                    background: {t["bg_secondary"]};
                    width: 10px;
                    margin: 0;
                    padding: 0;
                }}
                QScrollBar::handle:vertical {{
                    background: {t["scroll_handle"]};
                    min-height: 20px;
                    border-radius: 0;
                    margin: 0;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {t["scroll_handle_hover"]};
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0;
                    background: transparent;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
        else:
            # 隐藏滚动条（透明手柄）
            scrollbar.setStyleSheet(f"""
                QScrollBar:vertical {{
                    border: none;
                    background: {t["bg_secondary"]};
                    width: 10px;
                    margin: 0;
                    padding: 0;
                }}
                QScrollBar::handle:vertical {{
                    background: transparent;
                    min-height: 20px;
                    border-radius: 0;
                    margin: 0;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0;
                    background: transparent;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)

    def on_theme_changed(self, theme_id: str):
        """主题变更回调"""
        self.apply_theme()

    def setup_editor(self):
        if not self._is_qsci:
            return

        # 注意：不在这里设置颜色，所有颜色由apply_theme()设置

        # --- 0. 字体定义 (提前定义以供后续引用) ---
        font = QFont("Consolas", 11)
        font.setFixedPitch(True)

        # --- 1. 语法高亮与词法分析 ---
        # 使用自定义 URScript lexer
        self.lexer = URScriptLexer(self)
        self.lexer.setFont(font)
        self.setFont(font)

        # --- 2. 自动补全 API 注入 ---
        self.api = QsciAPIs(self.lexer)
        # 使用扩展的 URScript 命令列表
        for cmd in get_urscript_completions():
            self.api.add(cmd)
        self.api.prepare()

        self.setLexer(self.lexer)

        # --- 3. 基础编辑器行为（非颜色相关）---
        self.setUtf8(True)
        self.setCaretLineVisible(True)
        self.setCaretWidth(2)

        self.setIndentationsUseTabs(False)
        self.setIndentationWidth(2)
        self.setTabWidth(2)
        self.setAutoIndent(True)

        # 缩进引导线
        self.setIndentationGuides(True)

        # --- 4. 侧边栏 (行号与折叠) ---
        # 行号边距 (Margin 0)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "  000  ")  # 预留足够宽度 + 两侧padding
        self.setMarginLineNumbers(0, True)

        # 折叠边距 - 使用简洁样式
        self.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)

        # 设置行号样式
        self.setMarginsFont(font)  # 使用相同字体

        # --- 5. 自动补全配置 ---
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)

        # --- 6. 括号匹配 ---
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

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

        # 基础样式（滚动条由事件过滤器动态控制）
        self.setStyleSheet(
            f"""
            QsciScintilla {{
                border: none;
            }}
            QScrollBar:vertical {{
                background: {t["bg_secondary"]};
                width: 10px;
                margin: 0;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: transparent;
                min-height: 20px;
                border-radius: 0;
                margin: 0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            QScrollBar:horizontal {{
                height: 0;
                background: transparent;
            }}
            QAbstractScrollArea::corner {{
                background: {t["bg_secondary"]};
            }}
            """
        )

        # 重置滚动条状态
        self._scrollbar_visible = False

        # Base paper/ink
        bg_color = QColor(t["bg_secondary"])
        text_color = QColor(t["text"])

        # 从主题令牌获取语法高亮颜色
        syntax = {
            "default": t["text"],
            "comment": t.get("syntax_comment", t["text_muted"]),
            "keyword": t.get("syntax_keyword", t["accent_blue"]),
            "type": t.get("syntax_type", "#4EC9B0"),  # 类型关键字
            "motion": t.get("syntax_motion", "#DCDCAA"),  # 运动指令
            "io": t.get("syntax_io", "#C586C0"),  # IO 指令
            "robot": t.get("syntax_robot", "#9CDCFE"),  # 机器人指令
            "math": t.get("syntax_math", t.get("syntax_number", "#B5CEA8")),  # 数学函数
            "pose": t.get("syntax_pose", t.get("syntax_string", "#CE9178")),  # 位姿函数
            "string": t.get("syntax_string", "#CE9178"),
            "number": t.get("syntax_number", "#B5CEA8"),
            "operator": t.get("syntax_operator", t["text_muted"]),
            "identifier": t["text"],
            "force": t.get("syntax_force", "#FF8C00"),  # 力控指令
        }

        # 为 URScript lexer 设置颜色
        if isinstance(self.lexer, URScriptLexer):
            # 先设置背景色（会为所有样式设置）
            self.lexer.setPaper(bg_color)
            # 再设置各样式的前景色
            self.lexer.setColors({
                URScriptLexer.Default: QColor(syntax["default"]),
                URScriptLexer.Comment: QColor(syntax["comment"]),
                URScriptLexer.Keyword: QColor(syntax["keyword"]),
                URScriptLexer.Type: QColor(syntax["type"]),
                URScriptLexer.MotionCommand: QColor(syntax["motion"]),
                URScriptLexer.IOCommand: QColor(syntax["io"]),
                URScriptLexer.RobotCommand: QColor(syntax["robot"]),
                URScriptLexer.MathFunction: QColor(syntax["math"]),
                URScriptLexer.PoseFunction: QColor(syntax["pose"]),
                URScriptLexer.String: QColor(syntax["string"]),
                URScriptLexer.Number: QColor(syntax["number"]),
                URScriptLexer.Operator: QColor(syntax["operator"]),
                URScriptLexer.Identifier: QColor(syntax["identifier"]),
                URScriptLexer.ForceCommand: QColor(syntax["force"]),
            })
        else:
            # 后备方案：使用 Python lexer 的样式
            self.lexer.setDefaultPaper(bg_color)
            self.lexer.setDefaultColor(text_color)
            self.lexer.setColor(QColor(syntax["operator"]), QsciLexerPython.Operator)
            self.lexer.setColor(QColor(syntax["comment"]), QsciLexerPython.Comment)
            self.lexer.setColor(QColor(syntax["comment"]), QsciLexerPython.CommentBlock)
            self.lexer.setColor(QColor(syntax["keyword"]), QsciLexerPython.Keyword)
            self.lexer.setColor(QColor(syntax["number"]), QsciLexerPython.Number)
            self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.DoubleQuotedString)
            self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.SingleQuotedString)
            self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.TripleDoubleQuotedString)
            self.lexer.setColor(QColor(syntax["string"]), QsciLexerPython.TripleSingleQuotedString)
            # 设置函数名颜色
            func_attr = "FunctionMethodName" if hasattr(QsciLexerPython, "FunctionMethodName") else "ClassName"
            self.lexer.setColor(QColor(syntax["motion"]), getattr(QsciLexerPython, func_attr))
            # 设置标识符和默认文本颜色
            if hasattr(QsciLexerPython, "Identifier"):
                self.lexer.setColor(text_color, QsciLexerPython.Identifier)
            if hasattr(QsciLexerPython, "Default"):
                self.lexer.setColor(text_color, QsciLexerPython.Default)

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

        # Margins - 行号区域与代码区域使用相同背景色
        self.setMarginsBackgroundColor(QColor(t["bg_secondary"]))
        self.setMarginsForegroundColor(QColor(t["text_dim"]))

        # 折叠边距颜色设置
        # 注意：setFoldMarginColors(fore, back) - fore是折叠区域背景，back是折叠线颜色
        self.setFoldMarginColors(QColor(t["bg_secondary"]), QColor(t["bg_secondary"]))

        # 折叠标记颜色 - 注意：Foreground是填充色，Background是边框色
        fold_symbol_color = QColor(t["text_muted"])  # 符号颜色（+/-）
        fold_bg = QColor(t["bg_secondary"])  # 背景色

        # 设置折叠标记颜色 - 前景色是符号填充色，背景色是符号边框色
        self.setMarkerForegroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerBackgroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDER)
        self.setMarkerForegroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.setMarkerBackgroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        self.setMarkerForegroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEREND)
        self.setMarkerBackgroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEREND)
        self.setMarkerForegroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
        self.setMarkerBackgroundColor(fold_symbol_color, QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
        # 折叠线条颜色
        fold_line_color = QColor(t["border_light"])
        self.setMarkerForegroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        self.setMarkerBackgroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        self.setMarkerForegroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERTAIL)
        self.setMarkerBackgroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERTAIL)
        self.setMarkerForegroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        self.setMarkerBackgroundColor(fold_line_color, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)

        # 缩进引导线颜色
        indent_guide_color = t["border_light"] if use_dark else t["border"]
        self.setIndentationGuidesBackgroundColor(QColor(indent_guide_color))
        self.setIndentationGuidesForegroundColor(QColor(indent_guide_color))

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
