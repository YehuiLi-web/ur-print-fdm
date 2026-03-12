import os
import uuid
import json
import platform
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QMenu, QApplication, QFileDialog, QLabel, QFrame)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QColor
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui.theme_manager import get_theme_manager
from ur_print_fdm.ui.mixins.theme_aware import ThemeAwareMixin
from ur_print_fdm.paths import editor_session_path

# 常量配置
MAX_TAB_NAME_LENGTH = 25  # 标签页名称最大显示长度
SAVE_FILE_FILTER = "URScript Files (*.script);;Text Files (*.txt);;All Files (*)"
UNSAVED_PATH_PREFIX = "__unsaved_"
WELCOME_TAB_PATH = "__welcome__"
TAB_PATH_PROPERTY = "_editor_tab_path"
TAB_MODIFIED_PROPERTY = "_editor_tab_modified"
MODIFIED_TAB_PREFIX = "● "

from .core import CodeEditor

# 会话文件路径（必须是用户可写目录，避免安装包场景写入 site-packages）
SESSION_FILE = str(editor_session_path())


class EditorStatusBar(QFrame, ThemeAwareMixin):
    """
    编辑器状态栏 - 中文友好设计
    参考 VSCode 布局，但使用中文标签
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_theme_awareness()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(24)
        self._items = {}
        self.init_ui()

    def _create_status_item(self, text, tooltip="", highlight=False):
        """创建状态栏项目"""
        label = QLabel(text)
        label.setToolTip(tooltip)
        label.setProperty("highlight", bool(highlight))
        return label

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # === 左侧：光标信息 ===
        self._items['cursor'] = self._create_status_item("行 1, 列 1", "光标位置 (Ctrl+G 跳转)")
        layout.addWidget(self._items['cursor'])
        self._items['cursor'].setObjectName("status_cursor")

        # 选中统计（动态显示）
        self._items['selection'] = self._create_status_item("", "选中内容")
        layout.addWidget(self._items['selection'])
        self._items['selection'].setObjectName("status_selection")
        self._items['selection'].setProperty("active", False)

        layout.addStretch()

        # === 右侧：文件信息 ===
        # 缩进
        self._items['indent'] = self._create_status_item("缩进: 2", "缩进设置")
        layout.addWidget(self._items['indent'])

        # 编码
        self._items['encoding'] = self._create_status_item("UTF-8", "文件编码")
        layout.addWidget(self._items['encoding'])

        # 换行符 - 使用更易懂的描述
        self._items['eol'] = self._create_status_item("LF", "换行符: Unix (LF)")
        layout.addWidget(self._items['eol'])

        # 语言模式 - 高亮显示
        self._items['lang'] = self._create_status_item("URScript", "语言模式", highlight=True)
        layout.addWidget(self._items['lang'])
        self._items['lang'].setObjectName("status_lang")

    @staticmethod
    def _repolish(widget) -> None:
        try:
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        except Exception:
            pass

    def on_theme_changed(self, theme_id: str):
        """主题变更回调"""
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply the current app theme to the status bar (VSCode-like)."""
        t = self.get_token  # 使用ThemeAwareMixin的便捷方法
        self.setStyleSheet(
            f"""
            EditorStatusBar {{
                background-color: {t("bg_tertiary")};
                border-top: 1px solid {t("border_light")};
            }}
            QLabel {{
                color: {t("text_muted")};
                font-size: 11px;
                padding: 3px 12px;
            }}
            QLabel:hover {{
                background-color: {t("bg_hover_strong")};
                color: {t("text")};
            }}
            QLabel[highlight="true"] {{
                color: {t("text")};
                font-weight: 600;
            }}
            QLabel#status_selection[active="true"] {{
                color: {t("accent_link")};
                font-weight: 600;
            }}
            """
        )
        for w in (self._items or {}).values():
            self._repolish(w)

    def update_cursor(self, line, col):
        """更新光标位置"""
        self._items['cursor'].setText(f"行 {line + 1}, 列 {col + 1}")

    def update_selection(self, lines, chars):
        """更新选中信息"""
        if chars > 0:
            if lines > 0:
                self._items['selection'].setText(f"已选 {lines + 1} 行 {chars} 字符")
            else:
                self._items['selection'].setText(f"已选 {chars} 字符")
            # 选中时高亮显示
            self._items['selection'].setProperty("active", True)
            self._repolish(self._items['selection'])
        else:
            self._items['selection'].setText("")
            self._items['selection'].setProperty("active", False)
            self._repolish(self._items['selection'])

    def set_item(self, key, text, tooltip=""):
        """设置状态项内容"""
        if key in self._items:
            self._items[key].setText(text)
            if tooltip:
                self._items[key].setToolTip(tooltip)


class WelcomeWidget(QWidget, ThemeAwareMixin):
    """欢迎页面组件"""
    file_requested = pyqtSignal(str)  # 请求打开文件信号

    def __init__(self, recent_files=None):
        super().__init__()
        self.setup_theme_awareness()
        self.recent_files = recent_files or []
        self._recent_file_links = []  # list[(QLabel, file_path)]
        self._recent_label = None
        self._version_label = None
        self._robot_icon_label = None
        self._title_label = None
        self._subtitle_label = None
        self._tips_label = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(16)

        # 标题（图标 + 文字）
        icon_mgr = IconManager()
        title_row = QWidget()
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(12)
        title_layout.addStretch()
        robot_icon = QLabel()
        robot_pixmap = icon_mgr.get_svg_icon('robot', (32, 32)).pixmap(32, 32)
        robot_icon.setPixmap(robot_pixmap)
        title_layout.addWidget(robot_icon, 0, Qt.AlignmentFlag.AlignCenter)
        title = QLabel("UR5 Fiber Printer Studio")
        # 使用主题令牌
        title.setStyleSheet(f"font-size: 22pt; font-weight: 600; color: {self.get_token('accent_link')};")
        title_layout.addWidget(title, 0, Qt.AlignmentFlag.AlignCenter)
        title_layout.addStretch()
        layout.addWidget(title_row)
        self._robot_icon_label = robot_icon
        self._title_label = title

        # 副标题
        subtitle = QLabel("专业的机械臂 FDM 打印脚本编辑器")
        subtitle.setStyleSheet(f"font-size: 11pt; color: {self.get_token('text_muted')};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        self._subtitle_label = subtitle

        # 快捷操作提示
        tips = QLabel(
            "快速开始:\n\n"
            "- 从左侧文件资源管理器打开项目\n"
            "- Ctrl+N 创建新脚本\n"
            "- Ctrl+O 打开项目文件夹\n"
            "- Ctrl+S 保存当前脚本"
        )
        tips_color = self.get_token('text')
        tips.setStyleSheet(f"font-size: 11pt; color: {tips_color}; line-height: 2;")
        tips.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tips)
        self._tips_label = tips

        # 最近打开的文件
        if self.recent_files:
            recent_label = QLabel("最近打开")
            recent_label.setStyleSheet(f"font-size: 11pt; color: {self.get_token('text_muted')}; margin-top: 8px;")
            recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(recent_label)
            self._recent_label = recent_label

            link_color = self.get_token('accent_link')
            for file_path in self.recent_files[:5]:
                if os.path.exists(file_path):
                    file_name = os.path.basename(file_path)
                    file_btn = QLabel(f"<a href='{file_path}' style='color: {link_color}; text-decoration: none;'>{file_name}</a>")
                    file_btn.setStyleSheet("font-size: 11pt; padding: 2px 0;")
                    file_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    file_btn.setOpenExternalLinks(False)
                    file_btn.linkActivated.connect(self._on_file_clicked)
                    layout.addWidget(file_btn)
                    self._recent_file_links.append((file_btn, file_path))

        layout.addStretch()

        # 版本信息
        version = QLabel("v1.0 - Expert Edition")
        version.setStyleSheet(f"font-size: 9pt; color: {self.get_token('text_dim')};")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        self._version_label = version

    def on_theme_changed(self, theme_id: str):
        """主题变更回调"""
        self.apply_theme()

    def apply_theme(self) -> None:
        theme_mgr = get_theme_manager()
        t = theme_mgr.current_tokens()
        use_dark = theme_mgr.current_theme_id() == "dark"

        # Re-tint icon for the current theme
        if self._robot_icon_label is not None:
            icon_mgr = IconManager()
            self._robot_icon_label.setPixmap(icon_mgr.get_svg_icon("robot", (32, 32)).pixmap(32, 32))

        if self._title_label is not None:
            self._title_label.setStyleSheet(
                f"font-size: 22pt; font-weight: 600; color: {t['accent_link']};"
            )
        if self._subtitle_label is not None:
            self._subtitle_label.setStyleSheet(f"font-size: 11pt; color: {t['text_muted']};")

        if self._tips_label is not None:
            tips_color = t["text"] if use_dark else t["text_muted"]
            self._tips_label.setStyleSheet(f"font-size: 11pt; color: {tips_color}; line-height: 2;")

        if self._recent_label is not None:
            self._recent_label.setStyleSheet(
                f"font-size: 11pt; color: {t['text_muted']}; margin-top: 8px;"
            )

        link_color = t["accent_link"]
        for lbl, file_path in list(self._recent_file_links or []):
            try:
                file_name = os.path.basename(file_path)
                lbl.setText(
                    f"<a href='{file_path}' style='color: {link_color}; text-decoration: none;'>{file_name}</a>"
                )
                lbl.setStyleSheet("font-size: 11pt; padding: 2px 0;")
            except Exception:
                pass

        if self._version_label is not None:
            self._version_label.setStyleSheet(f"font-size: 9pt; color: {t['text_dim']};")

    def _on_file_clicked(self, file_path):
        self.file_requested.emit(file_path)


class DockableEditorWidget(QWidget):
    """
    编辑器管理器 (Editor Manager)
    负责管理多个 CodeEditor 实例、标签页切换及文件路径映射。
    """

    # 信号
    content_changed = pyqtSignal(int)
    file_saved = pyqtSignal(str)  # 文件保存成功信号
    upload_requested = pyqtSignal(list)  # 请求上传指定标签对应的文件

    def __init__(self):
        super().__init__()
        self.editors = {}  # Map: Path -> CodeEditor
        self.tab_paths = {}  # Map: Tab Index -> Path
        self.tab_modified = {}  # Map: Tab Index -> bool (修改状态)
        self._current_path = None
        self._welcome_widget = None
        self._status_bar = None
        self._session_data = self._load_session()

        self.init_ui()
        self.apply_theme()

    def _load_session(self):
        """加载会话数据"""
        try:
            if os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"recent_files": [], "open_files": [], "active_index": 0}

    def save_session(self):
        """保存会话数据"""
        try:
            # 收集当前打开的文件
            open_files = []
            for idx in range(self.tabs.count()):
                path = self._tab_path(idx)
                # 只保存真实文件路径，不保存未命名文件
                if path and not self._is_unsaved_path(path) and os.path.exists(path):
                    open_files.append(path)

            # 更新最近文件列表
            recent_files = self._session_data.get("recent_files", [])
            for path in open_files:
                if path in recent_files:
                    recent_files.remove(path)
                recent_files.insert(0, path)
            recent_files = recent_files[:20]  # 最多保存20个

            session = {
                "recent_files": recent_files,
                "open_files": open_files,
                "active_index": self.tabs.currentIndex()
            }

            # 确保目录存在
            os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(session, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话失败: {e}")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 初始化标签页
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)  # 允许拖动标签
        self.tabs.setUsesScrollButtons(True) # 启用滚动按钮逻辑

        # 允许滚轮切换标签页 (VSCode 行为)
        self.tabs.tabBar().installEventFilter(self)

        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self.show_tab_context_menu)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self.tabs.tabCloseRequested.connect(self.close_tab)

        # 样式定义 - VSCode 风格标签栏（隐藏滚动按钮，保留滚轮切换）
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                border-top: 1px solid #252526;
                background-color: #1e1e1e;
            }
            QTabBar {
                background-color: #252526;
                qproperty-drawBase: 0;
                border: none;
            }
            QTabBar::tab {
                height: 30px;
                max-width: 220px;
                padding: 0 12px;
                margin: 0;
                background-color: #2d2d30;
                color: #969696;
                border-right: 1px solid #252526;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #ffffff;
                border-bottom: 1px solid #1e1e1e;
                border-top: 1px solid #007ACC;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3e3e42;
            }
            /* 隐藏滚动按钮 */
            QTabBar::scroller {
                width: 0px;
            }
            QTabBar QToolButton {
                width: 0px;
                height: 0px;
            }
        """)

        # 标签页切换时更新状态栏
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # 根据会话状态决定显示欢迎页还是恢复文件
        open_files = self._session_data.get("open_files", [])
        recent_files = self._session_data.get("recent_files", [])

        if open_files:
            # 恢复上次打开的文件
            self._restore_session(open_files, self._session_data.get("active_index", 0))
        else:
            # 显示欢迎页
            self._show_welcome_tab(recent_files)

        layout.addWidget(self.tabs)

        # 添加状态栏
        self._status_bar = EditorStatusBar()
        layout.addWidget(self._status_bar)

        self.setLayout(layout)

    def apply_theme(self) -> None:
        """Apply the current app theme to tabs, welcome page, status bar and editors."""
        theme_mgr = get_theme_manager()
        t = theme_mgr.current_tokens()
        use_dark = theme_mgr.current_theme_id() == "dark"

        tab_bar_bg = t["bg_tertiary"]
        tab_bg = t["bg_panel"] if use_dark else t["bg_tertiary"]
        pane_bg = t["bg_secondary"]
        border = t["border_light"]
        hover = t["bg_hover_strong"]
        selected_top = t["accent_blue"]

        try:
            self.tabs.setStyleSheet(
                f"""
                QTabWidget::pane {{
                    border: none;
                    border-top: 1px solid {border};
                    background-color: {pane_bg};
                }}
                QTabBar {{
                    background-color: {tab_bar_bg};
                    qproperty-drawBase: 0;
                    border: none;
                }}
                QTabBar::tab {{
                    height: 30px;
                    max-width: 220px;
                    padding: 0 12px;
                    margin: 0;
                    background-color: {tab_bg};
                    color: {t["text_muted"]};
                    border-right: 1px solid {border};
                }}
                QTabBar::tab:selected {{
                    background-color: {pane_bg};
                    color: {t["text"]};
                    border-bottom: 1px solid {pane_bg};
                    border-top: 1px solid {selected_top};
                }}
                QTabBar::tab:hover:!selected {{
                    background-color: {hover};
                    color: {t["text"]};
                }}
                /* 隐藏滚动按钮 */
                QTabBar::scroller {{
                    width: 0px;
                }}
                QTabBar QToolButton {{
                    width: 0px;
                    height: 0px;
                }}
                """
            )
        except Exception:
            pass

        if self._status_bar is not None:
            try:
                self._status_bar.apply_theme()
            except Exception:
                pass

        if self._welcome_widget is not None:
            try:
                self._welcome_widget.apply_theme()
            except Exception:
                pass

        for editor in list((self.editors or {}).values()):
            try:
                editor.apply_theme()
            except Exception:
                pass

    def eventFilter(self, watched, event):
        """处理标签栏滚轮事件，实现类似 VSCode 的快速切换"""
        if watched == self.tabs.tabBar() and event.type() == event.Type.Wheel:
            delta = event.angleDelta().y()
            if delta > 0:
                self.tabs.setCurrentIndex(max(0, self.tabs.currentIndex() - 1))
            else:
                self.tabs.setCurrentIndex(min(self.tabs.count() - 1, self.tabs.currentIndex() + 1))
            return True
        return super().eventFilter(watched, event)

    def _on_tab_changed(self, index):
        """标签页切换时更新状态栏"""
        editor = self.get_current_editor()
        if editor and hasattr(editor, 'cursorPositionChanged'):
            try:
                editor.cursorPositionChanged.disconnect()
            except:
                pass
            editor.cursorPositionChanged.connect(self._update_status_bar_cursor)
            # 立即更新一次
            self._update_status_bar_cursor()
        elif self._status_bar:
            self._status_bar.update_cursor(0, 0)
            self._status_bar.update_selection(0, 0)

    def _update_status_bar_cursor(self):
        """更新状态栏光标信息"""
        editor = self.get_current_editor()
        if editor and self._status_bar:
            line, col = editor.getCursorPosition()
            self._status_bar.update_cursor(line, col)
            # 更新选中信息
            if editor.hasSelectedText():
                text = editor.selectedText()
                lines = text.count('\n')
                self._status_bar.update_selection(lines, len(text))
            else:
                self._status_bar.update_selection(0, 0)

    def _truncate_tab_name(self, name, max_length=MAX_TAB_NAME_LENGTH):
        """
        截断过长的标签页名称，同时尽量保留扩展名。
        """
        if len(name) <= max_length:
            return name

        base, ext = os.path.splitext(name)
        ellipsis = "…"
        available = max_length - len(ext) - len(ellipsis)
        if available <= 1:
            available = max(1, max_length - len(ellipsis))
            return name[:available] + ellipsis

        front_len = max(1, available // 3)
        back_len = max(1, available - front_len)
        return base[:front_len] + ellipsis + base[-back_len:] + ext

    def _tab_widget(self, index):
        if 0 <= index < self.tabs.count():
            return self.tabs.widget(index)
        return None

    def _editor_from_widget(self, widget):
        if widget is None:
            return None
        layout = widget.layout()
        if layout is None or layout.count() == 0:
            return None
        editor = layout.itemAt(0).widget()
        if isinstance(editor, CodeEditor):
            return editor
        return None

    def _editor_for_index(self, index):
        return self._editor_from_widget(self._tab_widget(index))

    def _find_tab_index_for_editor(self, editor):
        if editor is None:
            return -1
        for index in range(self.tabs.count()):
            if self._editor_for_index(index) is editor:
                return index
        return -1

    @staticmethod
    def _editor_text(editor):
        if editor is None:
            return ""
        getter = getattr(editor, "text", None)
        if callable(getter):
            return getter()
        getter = getattr(editor, "toPlainText", None)
        if callable(getter):
            return getter()
        return ""

    @staticmethod
    def _set_editor_text(editor, text):
        if editor is None:
            return
        setter = getattr(editor, "setText", None)
        if callable(setter):
            setter(text)
            return
        setter = getattr(editor, "setPlainText", None)
        if callable(setter):
            setter(text)

    @staticmethod
    def _is_unsaved_path(path):
        return bool(path) and str(path).startswith(UNSAVED_PATH_PREFIX)

    @staticmethod
    def _is_welcome_path(path):
        return path == WELCOME_TAB_PATH

    def _tab_path(self, index):
        widget = self._tab_widget(index)
        if widget is None:
            return ""
        path = widget.property(TAB_PATH_PROPERTY)
        return str(path) if path else ""

    def _tab_is_modified(self, index):
        widget = self._tab_widget(index)
        if widget is None:
            return False
        return bool(widget.property(TAB_MODIFIED_PROPERTY))

    def _set_tab_metadata(self, index, *, path=None, modified=None):
        widget = self._tab_widget(index)
        if widget is None:
            return
        if path is not None:
            widget.setProperty(TAB_PATH_PROPERTY, path)
        if modified is not None:
            widget.setProperty(TAB_MODIFIED_PROPERTY, bool(modified))
        self._sync_tab_state()

    def _sync_tab_state(self):
        new_tab_paths = {}
        new_tab_modified = {}
        for index in range(self.tabs.count()):
            path = self._tab_path(index)
            if path:
                new_tab_paths[index] = path
            new_tab_modified[index] = self._tab_is_modified(index)
        self.tab_paths = new_tab_paths
        self.tab_modified = new_tab_modified

    def _on_tab_moved(self, _from_index, _to_index):
        self._sync_tab_state()

    def _tab_base_title(self, index):
        path = self._tab_path(index)
        if self._is_welcome_path(path):
            return "欢迎"
        if self._is_unsaved_path(path) or not path:
            return "未命名"
        return self._truncate_tab_name(os.path.basename(path))

    def _tab_tooltip(self, path):
        if not path or self._is_unsaved_path(path) or self._is_welcome_path(path):
            return ""
        return path

    def _apply_tab_visual_state(self, index, *, flash_saved=False):
        if not (0 <= index < self.tabs.count()):
            return
        title = self._tab_base_title(index)
        if self._tab_is_modified(index) and not self._is_welcome_path(self._tab_path(index)):
            title = MODIFIED_TAB_PREFIX + title
        self.tabs.setTabText(index, title)
        self.tabs.tabBar().setTabToolTip(index, self._tab_tooltip(self._tab_path(index)))

        if self._tab_is_modified(index):
            self.tabs.tabBar().setTabTextColor(index, QColor("#E74C3C"))
            return

        if flash_saved:
            widget = self._tab_widget(index)
            self.tabs.tabBar().setTabTextColor(index, QColor("#66BB6A"))
            QTimer.singleShot(
                800,
                lambda tab_widget=widget: self._apply_tab_visual_state(self.tabs.indexOf(tab_widget))
                if tab_widget is not None and self.tabs.indexOf(tab_widget) != -1
                else None,
            )
            return

        self.tabs.tabBar().setTabTextColor(index, QColor("#d4d4d4"))

    def _mark_editor_modified(self, editor):
        index = self._find_tab_index_for_editor(editor)
        if index == -1 or self._tab_is_modified(index):
            return
        self._set_tab_metadata(index, modified=True)
        self._apply_tab_visual_state(index)

    def _connect_editor_signals(self, editor):
        editor.textChanged.connect(lambda editor=editor: self._mark_editor_modified(editor))
        if hasattr(editor, 'cursorPositionChanged'):
            editor.cursorPositionChanged.connect(self._update_status_bar_cursor)

    def _is_empty_untitled_tab(self, index):
        editor = self._editor_for_index(index)
        if editor is None:
            return False
        path = self._tab_path(index)
        return self._is_unsaved_path(path) and not self._tab_is_modified(index) and not self._editor_text(editor).strip()

    def _show_welcome_tab(self, recent_files=None):
        """显示欢迎页标签"""
        self._welcome_widget = WelcomeWidget(recent_files)
        self._welcome_widget.file_requested.connect(self._on_welcome_file_requested)

        idx = self.tabs.addTab(self._welcome_widget, "欢迎")
        self._set_tab_metadata(idx, path=WELCOME_TAB_PATH, modified=False)
        self._apply_tab_visual_state(idx)
        self.tabs.setCurrentIndex(idx)

    def _on_welcome_file_requested(self, file_path):
        """从欢迎页请求打开文件"""
        self.open_file_in_tab(file_path)

    def _restore_session(self, open_files, active_index):
        """恢复上次会话"""
        restored_count = 0
        for file_path in open_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._add_file_tab(file_path, content)
                    restored_count += 1
                except Exception:
                    pass

        if restored_count == 0:
            # 如果没有恢复任何文件，显示欢迎页
            self._show_welcome_tab(self._session_data.get("recent_files", []))
        else:
            # 恢复活动标签
            if 0 <= active_index < self.tabs.count():
                self.tabs.setCurrentIndex(active_index)

    # === 公共 API (供 MainWindow 调用) ===

    def get_current_editor(self):
        """获取当前活动的编辑器内核"""
        return self._editor_from_widget(self.tabs.currentWidget())

    def current_text(self):
        """获取当前编辑器文本"""
        editor = self.get_current_editor()
        return self._editor_text(editor)

    def set_current_text(self, text):
        """设置当前编辑器文本"""
        editor = self.get_current_editor()
        if editor:
            self._set_editor_text(editor, text)

    # === 标签页逻辑 ===

    def create_new_tab(self):
        """创建新标签页"""
        new_editor = self._create_editor_instance()

        # 创建容器
        editor_wrapper = self._wrap_editor(new_editor)

        # 生成临时路径
        temp_path = os.path.normpath(f"{UNSAVED_PATH_PREFIX}{uuid.uuid4()}__.script")

        # 添加标签
        tab_index = self.tabs.addTab(editor_wrapper, "未命名")

        # 注册映射
        self.editors[temp_path] = new_editor
        self._set_tab_metadata(tab_index, path=temp_path, modified=False)
        self._apply_tab_visual_state(tab_index)

        # 绑定修改信号
        self._connect_editor_signals(new_editor)

        self.tabs.setCurrentIndex(tab_index)
        return new_editor, tab_index

    def open_file_in_tab(self, file_path):
        """在标签页打开文件"""
        file_path = os.path.normpath(file_path)

        # 1. 检查是否已打开
        for idx, path in self.tab_paths.items():
            if path == file_path:
                self.tabs.setCurrentIndex(idx)
                return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 2. 检查当前是否可以复用标签（欢迎页或空白未命名页）
            current_idx = self.tabs.currentIndex()

            # 逻辑：如果是欢迎页，或者是一个空的未命名文件，则直接顶替
            is_welcome = self._tab_path(current_idx) == WELCOME_TAB_PATH
            is_empty_untitled = self._is_empty_untitled_tab(current_idx)

            if is_welcome:
                # 修复逻辑：先添加新标签，再关闭欢迎页
                # 这样可以防止 close_tab 因为 tabs 为空而自动重建欢迎页
                self._add_file_tab(file_path, content)
                # 此时 current_idx 指向的旧欢迎页依然在原位（通常是 0）
                self.close_tab(current_idx)
            elif is_empty_untitled:
                # 如果是空文件，直接原地更新
                self._update_tab_to_file(current_idx, file_path, content)
            else:
                # 否则添加新标签
                self._add_file_tab(file_path, content)

        except Exception as e:
            StyledMessageBox.critical(self, "错误", f"无法打开文件：{str(e)}")

    def close_tab(self, index):
        """关闭标签页"""
        path = self._tab_path(index)

        # 检查是否有未保存更改
        if self._tab_is_modified(index):
            display_title = self._tab_base_title(index)
            reply = StyledMessageBox.question_yes_no_cancel(
                self, "未保存", 
                f"标签「{display_title}」有未保存更改，是否保存？"
            )
            if reply == StyledMessageBox.Cancel:
                return
            if reply == StyledMessageBox.Yes:
                # 执行保存逻辑
                if not self._save_tab(index):
                    return  # 保存失败或取消，不关闭标签

        # 清理映射
        if path in self.editors:
            del self.editors[path]

        self.tabs.removeTab(index)

        # 🔧 修复：重建 tab_paths 索引映射，防止索引错位
        self._rebuild_tab_paths()

        if self.tabs.count() == 0:
            # 修复逻辑：不再创建空白标签，而是返回欢迎页
            self._show_welcome_tab(self._session_data.get("recent_files", []))

    def save_tab(self, index, *, prompt_title="保存脚本", default_save_path="", dialog_parent=None):
        """保存指定标签页，返回保存后的文件路径。"""
        path = self._tab_path(index)
        editor = self._editor_for_index(index)
        if editor is None or self._is_welcome_path(path):
            return None

        if self._is_unsaved_path(path) or not path:
            save_path, _ = QFileDialog.getSaveFileName(
                dialog_parent or self,
                prompt_title,
                default_save_path,
                SAVE_FILE_FILTER,
            )
            if not save_path:
                return None
            path = os.path.normpath(save_path)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self._editor_text(editor))

            old_path = self._tab_path(index)
            if old_path and old_path != path and old_path in self.editors:
                del self.editors[old_path]

            self.editors[path] = editor
            self._set_tab_metadata(index, path=path, modified=False)
            self._apply_tab_visual_state(index, flash_saved=True)
            self.file_saved.emit(path)
            return path
        except Exception as e:
            StyledMessageBox.critical(dialog_parent or self, "保存失败", f"无法保存文件：{str(e)}")
            return None

    def save_current_tab(self, *, prompt_title="保存脚本", default_save_path="", dialog_parent=None):
        """保存当前标签页。"""
        return self.save_tab(
            self.tabs.currentIndex(),
            prompt_title=prompt_title,
            default_save_path=default_save_path,
            dialog_parent=dialog_parent,
        )

    def _save_tab(self, index):
        """保存指定标签页的内容，返回是否成功"""
        return self.save_tab(index) is not None

    def _rebuild_tab_paths(self):
        """重建 tab_paths 索引映射（关闭标签后调用）"""
        self._sync_tab_state()

    def mark_tab_modified(self, index):
        """标记已修改 - 使用圆点指示器"""
        self._mark_editor_modified(self._editor_for_index(index))

    # === 内部辅助 ===

    def _create_editor_instance(self):
        editor = CodeEditor()
        editor.setPlaceholderText("在此编写 URScript...\n点击'运行'执行。")
        return editor

    def _wrap_editor(self, editor):
        wrapper = QWidget()
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(editor)
        return wrapper

    def _create_initial_tab(self):
        editor = self._create_editor_instance()
        wrapper = self._wrap_editor(editor)
        temp_path = os.path.normpath(f"{UNSAVED_PATH_PREFIX}{uuid.uuid4()}__.script")

        idx = self.tabs.addTab(wrapper, "未命名")
        self.editors[temp_path] = editor
        self._set_tab_metadata(idx, path=temp_path, modified=False)
        self._apply_tab_visual_state(idx)

        # 修复：使用默认参数捕获 idx 值，避免闭包引用问题
        self._connect_editor_signals(editor)

    def _update_tab_to_file(self, index, path, content):
        """将当前空标签更新为文件状态"""
        editor = self._editor_for_index(index)
        self._set_editor_text(editor, content)

        old_path = self._tab_path(index)
        if old_path in self.editors:
            del self.editors[old_path]

        self.editors[path] = editor
        self._set_tab_metadata(index, path=path, modified=False)
        self._apply_tab_visual_state(index)

    def _add_file_tab(self, path, content):
        """添加新文件标签"""
        editor = self._create_editor_instance()
        self._set_editor_text(editor, content)
        wrapper = self._wrap_editor(editor)

        idx = self.tabs.addTab(wrapper, self._truncate_tab_name(os.path.basename(path)))
        self.tabs.setCurrentIndex(idx)

        self.editors[path] = editor
        self._set_tab_metadata(idx, path=path, modified=False)
        self._apply_tab_visual_state(idx)

        self._connect_editor_signals(editor)

    def show_tab_context_menu(self, pos):
        idx = self.tabs.tabBar().tabAt(pos)
        if idx == -1:
            return

        menu = self._build_tab_context_menu(idx)
        menu.exec(self.tabs.tabBar().mapToGlobal(pos))

    def _tab_context_menu_style(self):
        t = get_theme_manager().current_tokens()
        return f"""
            QMenu {{
                background-color: {t["bg_tertiary"]};
                border: 1px solid {t["border_light"]};
                border-radius: {t.get("radius", "6px")};
                color: {t["text"]};
                padding: 6px 0;
            }}
            QMenu::item {{
                padding: 8px 18px 8px 16px;
                margin: 2px 8px;
                border-radius: {t.get("radius", "6px")};
            }}
            QMenu::item:selected {{
                background-color: {t["accent"]};
                color: {t["text_on_accent"]};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {t["border_light"]};
                margin: 6px 12px;
            }}
        """

    def _build_tab_context_menu(self, idx):
        menu = QMenu(self)
        menu.setStyleSheet(self._tab_context_menu_style())
        path = self._tab_path(idx)

        # 关闭当前标签
        act_close = QAction("关闭", self)
        act_close.triggered.connect(lambda: self.close_tab(idx))
        menu.addAction(act_close)
        
        # 关闭其他标签
        if self.tabs.count() > 1:
            act_close_others = QAction("关闭其他标签", self)
            act_close_others.triggered.connect(lambda: self._close_other_tabs(idx))
            menu.addAction(act_close_others)
            
            # 关闭所有标签
            act_close_all = QAction("关闭所有标签", self)
            act_close_all.triggered.connect(self._close_all_tabs)
            menu.addAction(act_close_all)
        
        menu.addSeparator()

        upload_path = self._get_uploadable_tab_path(idx)
        if upload_path:
            act_upload = QAction("上传到机器人", self)
            act_upload.triggered.connect(lambda checked=False, tab_idx=idx: self.request_upload_for_tab(tab_idx))
            menu.addAction(act_upload)
            menu.addSeparator()

        if path and not self._is_unsaved_path(path) and not self._is_welcome_path(path):
            act_open = QAction("在资源管理器中打开", self)
            act_open.triggered.connect(lambda: self._open_explorer(path))
            menu.addAction(act_open)

            act_copy = QAction("复制路径", self)
            act_copy.triggered.connect(lambda: QApplication.clipboard().setText(path))
            menu.addAction(act_copy)

        return menu

    def _get_uploadable_tab_path(self, index):
        path = self._tab_path(index)
        if not path or self._is_unsaved_path(path) or self._is_welcome_path(path):
            return None
        normalized = os.path.normpath(path)
        if not os.path.isfile(normalized):
            return None
        return normalized

    def request_upload_for_tab(self, index):
        upload_path = self._get_uploadable_tab_path(index)
        if upload_path:
            self.upload_requested.emit([upload_path])
    
    def _close_other_tabs(self, keep_idx):
        """关闭除指定标签外的所有标签"""
        # 从后向前关闭，避免索引变化问题
        indices_to_close = [i for i in range(self.tabs.count()) if i != keep_idx]
        for idx in reversed(indices_to_close):
            self.close_tab(idx)
    
    def _close_all_tabs(self):
        """关闭所有标签"""
        # 从后向前关闭
        for idx in reversed(range(self.tabs.count())):
            self.close_tab(idx)
    
    def clear_tab_modified_mark(self, index):
        """清除标签页的修改标记"""
        if index >= self.tabs.count():
            return
        if self._tab_is_modified(index):
            self._set_tab_metadata(index, modified=False)
            self._apply_tab_visual_state(index)

    def _open_explorer(self, path):
        directory = os.path.dirname(path)
        if platform.system() == "Windows":
            os.startfile(directory)
        elif platform.system() == "Darwin":
            subprocess.run(["open", directory])
        else:
            subprocess.run(["xdg-open", directory])
