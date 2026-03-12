"""
可右键清除的日志显示组件
增强版：支持复制、过滤、自动滚动控制
参考 VSCode / MATLAB 风格设计
"""
from PyQt6.QtWidgets import QTextEdit, QMenu, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QAction, QCursor
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme


class LogTextEdit(QTextEdit):
    """增强版日志显示组件：支持复制、过滤、自动滚动控制
    
    特性：
    - 右键菜单集成所有功能（过滤、清除、复制等）
    - VSCode 风格滚动条（细、锐利、悬停显示）
    - 专业工业软件风格
    """
    
    # 信号：当用户手动滚动时发出
    user_scrolled = pyqtSignal()
    # 信号：过滤级别变更
    filter_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("log_console")
        self.parent_window = parent
        self._icon_manager = IconManager()
        self._user_is_scrolling = False
        self._auto_scroll = True
        self._filter_level = "ALL"
        self._scrollbar_visible = None

        # 去掉输出框额外容器感，让滚动条直接贴住右侧。
        self.setFrameStyle(0)
        self.setViewportMargins(0, 0, 0, 0)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.installEventFilter(self)
        self.verticalScrollBar().installEventFilter(self)

        # 创建右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 监听滚动事件
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self._set_scrollbar_visibility(False)

    def eventFilter(self, obj, event):
        if obj in (self, self.viewport(), self.verticalScrollBar()):
            if event.type() == QEvent.Type.Enter:
                self._set_scrollbar_visibility(True)
            elif event.type() == QEvent.Type.Leave:
                QTimer.singleShot(0, self._sync_scrollbar_visibility)
        return super().eventFilter(obj, event)

    def _sync_scrollbar_visibility(self):
        if not self.isVisible():
            self._set_scrollbar_visibility(False)
            return
        inside = self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        self._set_scrollbar_visibility(inside)

    def _set_scrollbar_visibility(self, visible: bool):
        if self._scrollbar_visible == visible:
            return
        self._scrollbar_visible = visible

        t = theme.current_tokens()
        handle_bg = t["scroll_handle"] if visible else "transparent"
        handle_hover = t["scroll_handle_hover"] if visible else "transparent"
        handle_pressed = t.get("scroll_handle_pressed", handle_hover) if visible else "transparent"

        self.verticalScrollBar().setStyleSheet(
            f"""
            QScrollBar:vertical {{
                border: none;
                background: {t["bg_secondary"]};
                width: 6px;
                margin: 0;
                padding: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_bg};
                min-height: 28px;
                border-radius: 3px;
                margin: 0;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {handle_pressed};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
                border: none;
                background: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            """
        )

    def _on_scroll_changed(self, value):
        """检测用户是否手动滚动"""
        sb = self.verticalScrollBar()
        # 如果滚动条不在最底部，说明用户在查看历史
        if value < sb.maximum() - 10:
            self._user_is_scrolling = True
            self.user_scrolled.emit()
        else:
            self._user_is_scrolling = False

    def show_context_menu(self, position):
        """显示增强版右键菜单 - 集成所有日志操作"""
        menu = QMenu()
        
        # === 复制操作 ===
        copy_action = QAction("复制", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        
        copy_all_action = QAction("复制全部", self)
        copy_all_action.triggered.connect(self.copy_all_logs)
        menu.addAction(copy_all_action)
        
        menu.addSeparator()
        
        # === 过滤级别子菜单 ===
        filter_menu = menu.addMenu("过滤级别")
        
        filter_all = QAction("全部", self)
        filter_all.setCheckable(True)
        filter_all.setChecked(self._filter_level == "ALL")
        filter_all.triggered.connect(lambda: self._set_filter("ALL"))
        filter_menu.addAction(filter_all)
        
        filter_warn = QAction("警告及以上", self)
        filter_warn.setCheckable(True)
        filter_warn.setChecked(self._filter_level == "WARN")
        filter_warn.triggered.connect(lambda: self._set_filter("WARN"))
        filter_menu.addAction(filter_warn)
        
        filter_error = QAction("仅错误", self)
        filter_error.setCheckable(True)
        filter_error.setChecked(self._filter_level == "ERROR")
        filter_error.triggered.connect(lambda: self._set_filter("ERROR"))
        filter_menu.addAction(filter_error)
        
        menu.addSeparator()
        
        # === 滚动控制 ===
        auto_scroll_action = QAction("自动滚动", self)
        auto_scroll_action.setCheckable(True)
        auto_scroll_action.setChecked(self._auto_scroll)
        auto_scroll_action.triggered.connect(self._toggle_auto_scroll)
        menu.addAction(auto_scroll_action)
        
        scroll_bottom_action = QAction("滚动到底部", self)
        scroll_bottom_action.triggered.connect(self.scroll_to_bottom)
        menu.addAction(scroll_bottom_action)
        
        menu.addSeparator()
        
        # === 清除 ===
        clear_action = QAction("清除日志", self)
        clear_action.triggered.connect(self.clear_log)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _set_filter(self, level: str):
        """设置过滤级别"""
        self._filter_level = level
        self.filter_changed.emit(level)
    
    def _toggle_auto_scroll(self, checked: bool):
        """切换自动滚动"""
        self._auto_scroll = checked
        self._user_is_scrolling = not checked
        if checked:
            self.scroll_to_bottom()
    
    def set_auto_scroll(self, enabled: bool):
        """外部设置自动滚动状态"""
        self._auto_scroll = enabled
        self._user_is_scrolling = not enabled
    
    def get_filter_level(self) -> str:
        """获取当前过滤级别"""
        return self._filter_level

    def copy_all_logs(self):
        """复制全部日志到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.toPlainText())
        if self.parent_window:
            self.parent_window.log("已复制全部日志到剪贴板", "INFO")

    def scroll_to_bottom(self):
        """滚动到最新日志"""
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._user_is_scrolling = False

    def clear_log(self):
        """清除日志并记录清除信息"""
        self.clear()
        if self.parent_window:
            self.parent_window.log("日志已清除", "INFO")
    
    def is_user_scrolling(self) -> bool:
        """返回用户是否正在查看历史日志"""
        return self._user_is_scrolling
