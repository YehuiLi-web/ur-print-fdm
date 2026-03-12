"""
文件资源管理器组件 - 用于显示和管理项目文件结构
专业的 IDE 级别文件管理界面
"""
import os
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
                            QTreeWidgetItem, QPushButton, QFileDialog, QHeaderView,
                            QMenu, QAbstractItemView, QCheckBox, QDialog,
                            QGridLayout, QLabel, QLineEdit, QComboBox, QToolButton, QStyle)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QContextMenuEvent, QKeySequence, QShortcut
from ur_print_fdm.config import config_manager  # 导入配置管理器
from ur_print_fdm.ui.resources.icon_manager import IconManager


class DeleteConfirmationDialog(QDialog):
    """自定义删除确认对话框，包含不再提示选项 - 与 StyledMessageBox 风格一致"""
    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("确认删除")
        self.setModal(True)
        self.file_name = file_name
        self.setFixedWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 消息标签
        msg_label = QLabel(f"确定要删除文件「{file_name}」吗？\n此操作无法撤销。")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # 不再提示复选框
        self.dont_ask_again_checkbox = QCheckBox("下次不再提示")
        layout.addWidget(self.dont_ask_again_checkbox)

        # 分隔线
        from PyQt6.QtWidgets import QFrame
        from ur_print_fdm.ui.theme_manager import get_theme_manager

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {get_theme_manager().current_tokens().get('border_light', '#3C3C3C')};")
        layout.addWidget(line)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedHeight(28)
        self.cancel_button.setMinimumWidth(72)
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("删除")
        self.ok_button.setObjectName("btn-toolbar-danger")
        self.ok_button.setFixedHeight(28)
        self.ok_button.setMinimumWidth(72)
        self.ok_button.clicked.connect(self.accept)

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addLayout(button_layout)

        # Styling is provided by the application theme.


class FileExplorerWidget(QWidget):
    """文件资源管理器组件，用于显示项目文件结构"""

    script_loaded = pyqtSignal(str)  # 当双击脚本文件时发出信号（用于直接加载内容）
    file_requested = pyqtSignal(str)  # 当请求打开文件时发出信号（用于在标签页中打开）
    log_requested = pyqtSignal(str)  # 当需要记录日志时发出信号
    upload_requested = pyqtSignal(list)  # 请求上传文件到机器人
    estimate_requested = pyqtSignal(str)  # 请求估算脚本

    def __init__(self):
        super().__init__()
        self.current_project_path = None
        self.confirmation_setting = None  # 存储配置
        self.icon_manager = IconManager()  # 图标管理器实例
        self._root_header_buttons = []  # (button, icon_name) pairs for theme refresh
        self.clipboard_files = []  # 剪贴板文件列表
        self.clipboard_operation = None  # 'copy' 或 'cut'
        self.all_items = []  # 存储所有文件项，用于搜索
        self.tree_collapsed = False  # 文件树是否折叠
        self.init_ui()
        self.setup_shortcuts()  # 设置快捷键
        # 自动加载上次的项目
        self.load_last_project()

    def load_last_project(self):
        """加载上次打开的项目"""
        last_project_path = config_manager.get("project.last_project_path", "")
        if last_project_path and os.path.exists(last_project_path):
            self.load_project(last_project_path)

    def save_last_project(self):
        """保存当前项目路径到配置"""
        if self.current_project_path:
            config_manager.set("project.last_project_path", self.current_project_path)
            config_manager.save_config()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距，让滚动条紧贴边缘
        layout.setSpacing(0)

        # === 文件树 ===
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("文件资源管理器")
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        # 样式设置：缩进与图标尺寸匹配
        self.tree.setIndentation(18)
        self.tree.setIconSize(QSize(16, 16))

        # 样式由全局主题统一管理，不再使用内联样式

        # 安装事件过滤器以捕获键盘事件和鼠标悬停事件
        self.tree.installEventFilter(self)
        # 启用鼠标追踪以检测悬停
        self.tree.setMouseTracking(True)
        self.setMouseTracking(True)

        # 设置表头自适应
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # 添加到主布局
        layout.addWidget(self.tree)
        self.setLayout(layout)

        # 初始化根节点
        self.root_item = None

        # 滚动条悬停状态
        self._scrollbar_visible = False

    def create_root_header_widget(self, project_name):
        """创建嵌入根节点的标题组件（包含图标、项目名和功能按钮）"""
        self._root_header_buttons = []
        widget = QWidget()
        # 强制背景透明，确保与树节点背景融合
        widget.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(widget)
        # 调整边距：左侧留出一点空间给文件夹图标
        layout.setContentsMargins(0, 0, 2, 0)
        layout.setSpacing(6)

        # 1. 添加文件夹图标 (使根节点看起来更像一个真实的文件夹)
        folder_icon_label = QLabel()
        folder_pixmap = self.icon_manager.get_folder_icon(is_expanded=True).pixmap(16, 16)
        folder_icon_label.setPixmap(folder_pixmap)
        folder_icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(folder_icon_label)

        # 2. 项目名称标签（保持原始大小写，更易读）
        label = QLabel(project_name)
        label.setStyleSheet("font-weight: bold; background: transparent; border: none;")
        label.setToolTip(f"项目路径: {self.current_project_path}")
        layout.addWidget(label)

        layout.addStretch()

        # 创建功能按钮 helper（带悬停效果）
        from ur_print_fdm.ui.theme_manager import get_theme_manager
        t = get_theme_manager().current_tokens()

        def create_btn(icon_name, tooltip, slot):
            btn = QToolButton()
            btn.setIcon(self.icon_manager.get_action_icon(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setFixedSize(22, 22)
            btn.setToolTip(tooltip)
            btn.setAutoRaise(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(slot)
            # 添加悬停效果样式
            btn.setStyleSheet(f"""
                QToolButton {{
                    border: none;
                    background: transparent;
                    border-radius: 4px;
                }}
                QToolButton:hover {{
                    background-color: {t['bg_hover']};
                }}
                QToolButton:pressed {{
                    background-color: {t['bg_hover_strong']};
                }}
            """)
            self._root_header_buttons.append((btn, icon_name))
            return btn

        # 添加按钮（新增搜索按钮在最前面）
        layout.addWidget(create_btn('search', "查找文件 (Ctrl+Shift+F)", self.quick_find_file))
        layout.addWidget(create_btn('new_file', "新建脚本 (Ctrl+N)", self.new_script_file_toolbar))
        layout.addWidget(create_btn('new_folder', "新建文件夹 (Ctrl+Shift+N)", self.new_folder))
        layout.addWidget(create_btn('refresh', "刷新 (F5)", self.refresh_project))
        layout.addWidget(create_btn('collapse_all', "折叠所有子项", self.collapse_all_children))

        return widget

    def refresh_header_icons(self) -> None:
        """Re-apply themed icons and styles for the embedded header buttons (after theme switch)."""
        from ur_print_fdm.ui.theme_manager import get_theme_manager
        t = get_theme_manager().current_tokens()

        for btn, icon_name in list(getattr(self, "_root_header_buttons", []) or []):
            try:
                btn.setIcon(self.icon_manager.get_action_icon(icon_name))
                # 更新悬停效果样式
                btn.setStyleSheet(f"""
                    QToolButton {{
                        border: none;
                        background: transparent;
                        border-radius: 4px;
                    }}
                    QToolButton:hover {{
                        background-color: {t['bg_hover']};
                    }}
                    QToolButton:pressed {{
                        background-color: {t['bg_hover_strong']};
                    }}
                """)
            except Exception:
                pass

    def on_header_enter(self, event):
        """已弃用"""
        pass

    def on_header_leave(self, event):
        """已弃用"""
        pass

    def setup_shortcuts(self):
        """设置键盘快捷键"""
        # F2: 重命名
        shortcut_rename = QShortcut(QKeySequence("F2"), self)
        shortcut_rename.activated.connect(self.rename_selected_file)

        # F5: 刷新
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self.refresh_project)

        # 移除 Ctrl+F 快捷键，避免与编辑器冲突
        # 改为右键菜单中的"查找文件"功能

        # Ctrl+N: 新建文件
        shortcut_new_file = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut_new_file.activated.connect(self.new_script_file_toolbar)

        # Ctrl+Shift+N: 新建文件夹
        shortcut_new_folder = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
        shortcut_new_folder.activated.connect(self.new_folder)

        # Enter: 打开文件
        shortcut_open = QShortcut(QKeySequence("Return"), self)
        shortcut_open.activated.connect(self.open_selected_file)

    def eventFilter(self, obj, event):
        """事件过滤器，用于处理键盘事件和鼠标悬停事件"""
        from PyQt6.QtCore import QEvent

        # 处理鼠标进入/离开事件 - 控制滚动条显示
        if obj == self.tree:
            if event.type() == QEvent.Type.Enter:
                self._show_scrollbar(True)
            elif event.type() == QEvent.Type.Leave:
                self._show_scrollbar(False)
            elif event.type() == QEvent.Type.KeyPress:
                # Delete: 删除
                if event.key() == Qt.Key.Key_Delete:
                    self.handle_delete_key()
                    return True
                # Ctrl+C: 复制
                elif event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.copy_files()
                    return True
                # Ctrl+X: 剪切
                elif event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.cut_files()
                    return True
                # Ctrl+V: 粘贴
                elif event.key() == Qt.Key.Key_V and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.paste_files()
                    return True
        return super().eventFilter(obj, event)

    def _show_scrollbar(self, visible: bool):
        """显示或隐藏滚动条"""
        if self._scrollbar_visible == visible:
            return
        self._scrollbar_visible = visible

        from ur_print_fdm.ui.theme_manager import get_theme_manager
        t = get_theme_manager().current_tokens()

        scrollbar = self.tree.verticalScrollBar()
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
                    min-height: 30px;
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
                    min-height: 30px;
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

    def open_project(self):
        """打开项目目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if dir_path:
            self.load_project(dir_path)

    def load_project(self, project_path):
        """加载项目目录"""
        self.current_project_path = project_path
        self.tree.clear()
        self.all_items = []  # 清空项目列表

        project_name = os.path.basename(project_path)

        # 创建根节点
        self.root_item = QTreeWidgetItem(self.tree)
        # 注意：这里我们不设置 Text，因为我们要用 setItemWidget 覆盖它
        self.root_item.setData(0, Qt.ItemDataRole.UserRole, project_path)

        # 创建自定义 Header Widget (包含按钮)
        header_widget = self.create_root_header_widget(project_name)
        self.tree.setItemWidget(self.root_item, 0, header_widget)

        # 递归加载文件
        self.populate_tree(self.root_item, project_path)

        self.root_item.setExpanded(True)

        # 保存当前项目路径到配置
        self.save_last_project()

    def collapse_all_children(self):
        """折叠根节点下的所有子节点"""
        if self.root_item:
            # 遍历一级子节点并折叠
            for i in range(self.root_item.childCount()):
                self.root_item.child(i).setExpanded(False)

    # 移除旧的 populate_tree_root 方法，不再需要


    def populate_tree(self, parent_item, parent_path):
        """填充树形结构"""
        try:
            items = os.listdir(parent_path)
            # 按类型排序：文件夹优先
            items.sort(key=lambda x: (os.path.isfile(os.path.join(parent_path, x)), x.lower()))

            for item in items:
                item_path = os.path.join(parent_path, item)

                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, item)
                child_item.setData(0, Qt.ItemDataRole.UserRole, item_path)

                # 存储到all_items用于搜索
                self.all_items.append(child_item)

                # 根据类型设置图标
                if os.path.isdir(item_path):
                    # 文件夹图标
                    child_item.setIcon(0, self.icon_manager.get_folder_icon(is_expanded=False))
                    child_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                    # 递归添加子目录
                    self.populate_tree(child_item, item_path)
                else:
                    # 文件图标
                    child_item.setIcon(0, self.icon_manager.get_file_icon(item_path))

                    # 设置工具提示
                    _, ext = os.path.splitext(item)
                    standardized_path = os.path.normpath(item_path)
                    if ext.lower() in ['.script', '.txt', '.py', '.urp']:
                        child_item.setToolTip(0, f"脚本文件: {standardized_path}")
                    else:
                        child_item.setToolTip(0, f"文件: {standardized_path}")
        except PermissionError:
            # 如果没有权限访问某些目录，则跳过
            pass

    def refresh_project(self):
        """刷新项目视图"""
        if self.current_project_path and os.path.exists(self.current_project_path):
            self.load_project(self.current_project_path)
        else:
            # 如果当前项目路径不存在，则清除项目路径
            self.current_project_path = None
            self.tree.clear()
            # 恢复初始状态
            self.root_item = QTreeWidgetItem(self.tree)
            self.root_item.setText(0, "未打开项目")
            self.root_item.setExpanded(True)

            # 清除配置中的项目路径
            config_manager.set("project.last_project_path", "")
            config_manager.save_config()

    def on_item_double_clicked(self, item, column):
        """处理项目双击事件"""
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_path and os.path.isfile(item_path):
            # 检查是否是脚本文件
            _, ext = os.path.splitext(item_path)
            if ext.lower() in ['.script', '.txt', '.py', '.urp']:
                # 发射信号，通知主窗口在新标签页中打开文件
                self.file_requested.emit(item_path)

    def show_context_menu(self, position):
        """显示上下文菜单"""
        item = self.tree.itemAt(position)

        menu = QMenu()

        # 获取项目路径
        item_path = None
        if item:
            item_path = item.data(0, Qt.ItemDataRole.UserRole)

        # 收集选中的文件路径（用于批量上传）
        selected_items = self.tree.selectedItems()
        selected_files = []
        for it in selected_items:
            p = it.data(0, Qt.ItemDataRole.UserRole)
            if p and os.path.isfile(p):
                selected_files.append(p)

        # 如果右键的是文件，确保加入上传集合（即使未被选中）
        if item_path and os.path.isfile(item_path) and item_path not in selected_files:
            selected_files.insert(0, item_path)

        # 如果有选中项目且为文件，则显示文件相关操作
        if item_path and os.path.isfile(item_path):
            _, ext = os.path.splitext(item_path)
            if ext.lower() in ['.script', '.txt', '.py', '.urp']:
                action_open = QAction(self.icon_manager.get_action_icon('open'), "在编辑器中打开", self)
                action_open.triggered.connect(lambda: self.open_file_requested(item_path))
                menu.addAction(action_open)
            
            if ext.lower() in ['.script', '.txt']:
                action_estimate = QAction("脚本估算...", self)
                action_estimate.triggered.connect(lambda: self.estimate_requested.emit(item_path))
                menu.addAction(action_estimate)

            # 添加重命名功能
            action_rename = QAction(self.icon_manager.get_action_icon('rename'), "重命名", self)
            action_rename.triggered.connect(lambda: self.rename_file(item, item_path))
            menu.addAction(action_rename)

            # 添加删除功能
            action_delete = QAction(self.icon_manager.get_action_icon('delete'), "删除", self)
            action_delete.triggered.connect(lambda: self.delete_file(item, item_path))
            menu.addAction(action_delete)

            # 添加复制路径功能
            action_copy_path = QAction(self.icon_manager.get_action_icon('copy_path'), "复制路径", self)
            action_copy_path.triggered.connect(lambda: self.copy_file_path(item_path))
            menu.addAction(action_copy_path)

            menu.addSeparator()

        # 上传文件（右键菜单集成）
        if selected_files:
            upload_icon = self.icon_manager.get_svg_icon("upload", (16, 16))
            action_upload = QAction(upload_icon, "上传到机器人", self)
            action_upload.triggered.connect(lambda: self.upload_requested.emit(selected_files))
            menu.addAction(action_upload)
            menu.addSeparator()

        # 如果有选中项目或右键在空白区域但有项目路径
        if self.current_project_path:
            # 如果选中的是目录或空白区域，添加新建文件功能
            if not item or (item_path and os.path.isdir(item_path)):
                # 为当前目录或根目录添加新建文件功能
                current_dir = item_path if item_path and os.path.isdir(item_path) else self.current_project_path

                # 新建脚本
                action_new_script = QAction(self.icon_manager.get_action_icon('new_file'), "新建脚本", self)
                action_new_script.triggered.connect(lambda: self.new_script_file(current_dir))
                menu.addAction(action_new_script)

                # 新建文件夹
                action_new_folder = QAction(self.icon_manager.get_action_icon('new_folder'), "新建文件夹", self)
                action_new_folder.triggered.connect(lambda: self.new_folder(current_dir))
                menu.addAction(action_new_folder)

            menu.addSeparator()

            # 添加查找文件功能
            action_find = QAction(self.icon_manager.get_action_icon('search'), "查找文件...", self)
            action_find.triggered.connect(self.quick_find_file)
            menu.addAction(action_find)

        # 添加刷新菜单项
        action_refresh = QAction(self.icon_manager.get_action_icon('refresh'), "刷新", self)
        action_refresh.triggered.connect(self.refresh_project)
        menu.addAction(action_refresh)

        # 只有在有项目路径时才显示在资源管理器中打开选项
        if item_path:
            action_open_explorer = QAction(self.icon_manager.get_action_icon('open_explorer'), "在资源管理器中打开", self)
            action_open_explorer.triggered.connect(lambda: self.open_in_explorer(item_path))
            menu.addAction(action_open_explorer)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def delete_file(self, item, file_path):
        """删除文件"""
        # 获取文件名
        file_name = os.path.basename(file_path)

        # 从配置中获取上次的设置
        self.confirmation_setting = config_manager.get("project.confirm_deletion", True)

        # 如果配置为需要确认，则显示确认对话框
        if self.confirmation_setting:
            # 创建自定义对话框
            dialog = DeleteConfirmationDialog(file_name, self)

            if dialog.exec():
                # 用户选择了删除
                try:
                    os.remove(file_path)

                    # 从树中删除该项目
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
                    else:
                        self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

                    self.log_requested.emit(f"已删除文件: {file_name}")

                    # 检查是否需要更新配置
                    if dialog.dont_ask_again_checkbox.isChecked():
                        config_manager.set("project.confirm_deletion", False)
                        config_manager.save_config()
                except Exception as e:
                    StyledMessageBox.critical(self, "错误", f"无法删除文件：{str(e)}")
        else:
            # 直接删除
            try:
                os.remove(file_path)

                # 从树中删除该项目
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

                self.log_requested.emit(f"已删除文件: {file_name}")
            except Exception as e:
                StyledMessageBox.critical(self, "错误", f"无法删除文件：{str(e)}")

    def open_file_in_editor(self, file_path):
        """在编辑器中打开文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            self.script_loaded.emit(script_content)
        except Exception as e:
            StyledMessageBox.critical(self, "错误", f"无法打开文件：{str(e)}")

    def open_file_requested(self, file_path):
        """发送信号在标签页中打开文件"""
        self.file_requested.emit(file_path)

    def copy_file_path(self, file_path):
        """复制文件路径到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        self.log_requested.emit(f"已复制路径到剪贴板: {file_path}")

    def open_in_explorer(self, path):
        """在资源管理器中打开路径"""
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                # 在Windows上使用os.startfile，这是处理中文路径更好的方法
                os.startfile(os.path.dirname(path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", os.path.dirname(path)], check=True, encoding='utf-8')
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(path)], check=True, encoding='utf-8')
        except Exception as e:
            StyledMessageBox.warning(self, "警告", f"无法打开资源管理器：{str(e)}")

    def new_script_file(self, directory):
        """新建脚本文件"""
        from PyQt6.QtWidgets import QInputDialog

        # 获取用户输入的新文件名
        file_name, ok = QInputDialog.getText(self, "新建脚本", "输入脚本名称:", text="新脚本.script")

        if ok and file_name.strip():
            # 确保文件扩展名为.script或.txt
            if not file_name.endswith(('.script', '.txt')):
                file_name += '.script'

            file_path = os.path.join(directory, file_name)

            # 检查文件是否已存在
            if os.path.exists(file_path):
                StyledMessageBox.warning(self, "警告", "文件已存在！")
                return

            try:
                # 创建新文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("# 新建URScript文件\n")

                # 刷新项目视图
                self.refresh_project()

                # 发送消息到主窗口
                self.file_requested.emit(file_path)  # 这样可以在新标签页中打开
                self.log_requested.emit(f"已创建新脚本: {file_name}")
            except Exception as e:
                StyledMessageBox.critical(self, "错误", f"无法创建文件：{str(e)}")

    def rename_file(self, item, file_path):
        """重命名文件"""
        from PyQt6.QtWidgets import QInputDialog
        from PyQt6.QtCore import QFileInfo

        # 获取当前文件名（不含扩展名）
        file_info = QFileInfo(file_path)
        current_name = file_info.fileName()
        name_without_ext = file_info.completeBaseName()
        extension = file_info.suffix()

        # 获取用户输入的新文件名
        new_name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=name_without_ext)

        if ok and new_name.strip():
            # 确保新文件名不为空
            if not new_name.strip():
                StyledMessageBox.warning(self, "警告", "文件名不能为空！")
                return

            # 构建新文件路径
            directory = os.path.dirname(file_path)
            if extension:
                new_file_name = f"{new_name}.{extension}"
            else:
                new_file_name = new_name
            new_file_path = os.path.join(directory, new_file_name)

            # 检查新文件名是否与原文件名相同
            if file_path == new_file_path:
                return  # 用户没有更改文件名

            # 检查新文件是否已存在
            if os.path.exists(new_file_path):
                StyledMessageBox.warning(self, "警告", "同名文件已存在！")
                return

            try:
                # 重命名文件
                os.rename(file_path, new_file_path)

                # 刷新项目视图
                self.refresh_project()

                self.log_requested.emit(f"已重命名文件: {current_name} -> {new_file_name}")
            except Exception as e:
                StyledMessageBox.critical(self, "错误", f"无法重命名文件：{str(e)}")

    def handle_delete_key(self):
        """处理删除键事件"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        # 遍历所有选定项目并删除文件
        for item in selected_items:
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_path and os.path.isfile(item_path):
                self.delete_file(item, item_path)
                # 只处理第一个文件以避免同时删除多个文件导致的问题
                break

    # === 阶段2新增功能 ===

    def toggle_tree_visibility(self):
        """已弃用：不再需要单独的折叠按钮，因为根节点自带折叠功能"""
        pass

    def quick_find_file(self):
        """快速定位文件 - 增强版搜索对话框"""
        if not self.all_items:
            StyledMessageBox.information(self, "提示", "请先打开一个项目")
            return

        # 创建搜索对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("查找文件")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 搜索输入框
        search_input = QLineEdit()
        search_input.setPlaceholderText("输入文件名进行搜索...")
        layout.addWidget(search_input)
        
        # 搜索结果列表
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem
        results_list = QListWidget()
        results_list.setMaximumHeight(300)
        layout.addWidget(results_list)
        
        # 状态标签
        status_label = QLabel(f"共 {len(self.all_items)} 个文件")
        status_label.setProperty("ui_role", "muted")
        layout.addWidget(status_label)
        
        # 实时搜索过滤
        def on_search_changed(text):
            results_list.clear()
            if not text.strip():
                status_label.setText(f"共 {len(self.all_items)} 个文件")
                return
            
            matches = []
            search_lower = text.lower()
            for item in self.all_items:
                item_name = item.text(0).lower()
                item_path = item.data(0, Qt.ItemDataRole.UserRole)
                if search_lower in item_name:
                    matches.append((item, item_name, item_path))
            
            for item, name, path in matches[:50]:  # 限制显示50条
                list_item = QListWidgetItem(name)
                list_item.setData(Qt.ItemDataRole.UserRole, item)
                list_item.setToolTip(path)
                results_list.addItem(list_item)
            
            status_label.setText(f"找到 {len(matches)} 个匹配")
        
        search_input.textChanged.connect(on_search_changed)
        
        # 双击或回车打开文件
        def on_item_activated(list_item):
            tree_item = list_item.data(Qt.ItemDataRole.UserRole)
            if tree_item:
                # 展开所有父节点
                parent = tree_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                
                # 选中并滚动到该项
                self.tree.setCurrentItem(tree_item)
                self.tree.scrollToItem(tree_item)
                
                # 如果是文件，打开它
                item_path = tree_item.data(0, Qt.ItemDataRole.UserRole)
                if item_path and os.path.isfile(item_path):
                    self.file_requested.emit(item_path)
                
                self.log_requested.emit(f"已定位到: {tree_item.text(0)}")
                dialog.accept()
        
        results_list.itemDoubleClicked.connect(on_item_activated)
        results_list.itemActivated.connect(on_item_activated)
        
        # 回车键跳转到第一个结果
        def on_return_pressed():
            if results_list.count() > 0:
                on_item_activated(results_list.item(0))
        
        search_input.returnPressed.connect(on_return_pressed)
        
        dialog.exec()

    def on_search_text_changed(self, text):
        """搜索文本变化时过滤文件树"""
        # 保留此方法以备后用
        pass

    def show_all_items(self):
        """显示所有项目"""
        # 保留此方法以备后用
        pass

    def hide_all_items(self):
        """隐藏所有项目"""
        # 保留此方法以备后用
        pass

    def collapse_all(self):
        """折叠所有节点"""
        self.tree.collapseAll()
        # VSCode风格：没有根节点，不需要特殊处理

    def on_sort_changed(self, index):
        """排序方式改变"""
        # 重新加载项目以应用新的排序
        # 注：已移除排序下拉框，保留方法以备后用
        if self.current_project_path:
            self.load_project(self.current_project_path)

    def new_script_file_toolbar(self):
        """从工具栏新建脚本文件"""
        if not self.current_project_path:
            StyledMessageBox.warning(self, "警告", "请先打开一个项目！")
            return

        # 获取当前选中的目录，如果没有则使用根目录
        selected_items = self.tree.selectedItems()
        if selected_items:
            item_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if os.path.isdir(item_path):
                target_dir = item_path
            else:
                target_dir = os.path.dirname(item_path)
        else:
            target_dir = self.current_project_path

        self.new_script_file(target_dir)

    def new_folder(self, target_path=None):
        """新建文件夹"""
        if not self.current_project_path:
            StyledMessageBox.warning(self, "警告", "请先打开一个项目！")
            return

        target_dir = None
        # 处理传入参数：如果是字符串则使用，如果是布尔值(信号)或None则自动判断
        if target_path and isinstance(target_path, str):
            target_dir = target_path
        else:
            # 获取目标目录
            selected_items = self.tree.selectedItems()
            if selected_items:
                item_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
                if os.path.isdir(item_path):
                    target_dir = item_path
                else:
                    target_dir = os.path.dirname(item_path)
            else:
                target_dir = self.current_project_path

        # 获取用户输入的文件夹名
        from PyQt6.QtWidgets import QInputDialog
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:", text="新文件夹")

        if ok and folder_name.strip():
            folder_path = os.path.join(target_dir, folder_name)

            # 检查文件夹是否已存在
            if os.path.exists(folder_path):
                StyledMessageBox.warning(self, "警告", "文件夹已存在！")
                return

            try:
                # 创建文件夹
                os.makedirs(folder_path)
                # 刷新项目视图
                self.refresh_project()
                self.log_requested.emit(f"已创建文件夹: {folder_name}")
            except Exception as e:
                StyledMessageBox.critical(self, "错误", f"无法创建文件夹：{str(e)}")

    def copy_files(self):
        """复制选中的文件到剪贴板"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        self.clipboard_files = []
        for item in selected_items:
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_path and os.path.exists(item_path):
                self.clipboard_files.append(item_path)

        self.clipboard_operation = 'copy'
        self.log_requested.emit(f"已复制 {len(self.clipboard_files)} 个项目")

    def cut_files(self):
        """剪切选中的文件到剪贴板"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        self.clipboard_files = []
        for item in selected_items:
            item_path = item.data(0, Qt.ItemDataRole.UserRole)
            if item_path and os.path.exists(item_path):
                self.clipboard_files.append(item_path)

        self.clipboard_operation = 'cut'
        self.log_requested.emit(f"已剪切 {len(self.clipboard_files)} 个项目")

    def paste_files(self):
        """粘贴剪贴板中的文件"""
        if not self.clipboard_files:
            return

        # 获取目标目录
        selected_items = self.tree.selectedItems()
        if selected_items:
            item_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            if os.path.isdir(item_path):
                target_dir = item_path
            else:
                target_dir = os.path.dirname(item_path)
        else:
            target_dir = self.current_project_path

        if not target_dir:
            StyledMessageBox.warning(self, "警告", "请先打开一个项目！")
            return

        # 执行复制或移动操作
        success_count = 0
        for source_path in self.clipboard_files:
            try:
                file_name = os.path.basename(source_path)
                dest_path = os.path.join(target_dir, file_name)

                # 如果目标已存在，添加序号
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(file_name)
                    counter = 1
                    while os.path.exists(dest_path):
                        new_name = f"{base}_{counter}{ext}"
                        dest_path = os.path.join(target_dir, new_name)
                        counter += 1

                if self.clipboard_operation == 'copy':
                    if os.path.isdir(source_path):
                        shutil.copytree(source_path, dest_path)
                    else:
                        shutil.copy2(source_path, dest_path)
                elif self.clipboard_operation == 'cut':
                    shutil.move(source_path, dest_path)

                success_count += 1
            except Exception as e:
                StyledMessageBox.warning(self, "警告", f"无法粘贴 {os.path.basename(source_path)}：{str(e)}")

        # 清空剪贴板（如果是剪切操作）
        if self.clipboard_operation == 'cut':
            self.clipboard_files = []
            self.clipboard_operation = None

        # 刷新视图
        self.refresh_project()
        self.log_requested.emit(f"已粘贴 {success_count} 个项目")

    def rename_selected_file(self):
        """重命名当前选中的文件"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_path and os.path.exists(item_path):
            self.rename_file(item, item_path)

    def open_selected_file(self):
        """打开当前选中的文件"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        item_path = item.data(0, Qt.ItemDataRole.UserRole)
        if item_path and os.path.isfile(item_path):
            _, ext = os.path.splitext(item_path)
            if ext.lower() in ['.script', '.txt', '.py', '.urp']:
                self.file_requested.emit(item_path)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = FileExplorerWidget()
    widget.show()
    sys.exit(app.exec())
