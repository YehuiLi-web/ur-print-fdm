# ui/main_window.py
import os
import logging
import time
import datetime
import re
from pathlib import Path

from PyQt6.QtWidgets import (QMainWindow, QDockWidget, QTextEdit,
                             QListWidget, QWidget, QPushButton, QToolBar,
                             QLabel, QVBoxLayout, QFileDialog,
                             QProgressBar, QHBoxLayout,
                             QCheckBox, QComboBox, QSizePolicy, QGroupBox, QStyle,
                             QInputDialog, QListView)
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QAction, QIcon

# === 核心逻辑引入 ===
from ur_print_fdm.core.driver import URDriver
from ur_print_fdm.ui.workers.production_processor import ProductionProcessor
from ur_print_fdm.core.print_lib import URPrintLib  # Add this import
from ur_print_fdm.core import toolbox as ur_toolbox
from ur_print_fdm.config import config_manager
from ur_print_fdm.constants import DEFAULT_DO_INDEX, SCRIPT_PORT
from ur_print_fdm.shared.net import is_valid_ip

# === 组件引入 (全部模块化) ===
from ur_print_fdm.ui.widgets.file_explorer import FileExplorerWidget  # 文件资源管理器组件
from ur_print_fdm.ui.widgets.collapsible_status_dock import StatusWidget
from ur_print_fdm.ui.widgets.combobox_fix import fix_combobox_popup
from ur_print_fdm.ui.widgets.editor import DockableEditorWidget  # 新增dockable编辑器组件
from ur_print_fdm.ui.theme import apply_app_theme  # 向后兼容
from ur_print_fdm.ui.theme_manager import get_theme_manager  # 新的主题管理器
from ur_print_fdm.ui.controllers.queue_controller import QueueController
from ur_print_fdm.ui.controllers.tools_controller import ToolsController
from ur_print_fdm.ui.services.log_service import LogService
from ur_print_fdm.ui.workers.threads import (
    ScriptSendThread,
    URScriptEstimateThread,
    SFTPUploadThread,
    StopThread,
    ConnectionThread,
    MonitorThread,
    ControlReconnectThread,
)
from ur_print_fdm.ui.workers.direct_mode_processor import DirectModeProcessor
from ur_print_fdm.estimators.simple_gcode import SimpleGCodeTimeEstimator
from ur_print_fdm.plugins.registry import registry
from ur_print_fdm.ui.resources.icon_manager import IconManager

class URPrintIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        # 使用新的ThemeManager
        theme_mgr = get_theme_manager()
        use_dark = bool(config_manager.get("ui.dark_theme", True))
        theme_mgr.set_theme("dark" if use_dark else "light")

        # 初始化IconManager的主题监听器（必须在QApplication创建之后）
        from ur_print_fdm.ui.resources.icon_manager import _init_theme_listener
        _init_theme_listener()

        self.backend_id = config_manager.get("robot.backend_id", "ur_rtde_cb3")
        self.backend = None
        self._backend_init_error = None
        self.driver = URDriver()
        try:
            factory = registry.robot_backends.get(self.backend_id)
            if factory is None:
                self._backend_init_error = f"未找到后端: {self.backend_id!r}"
            else:
                self.backend = factory.create()
                driver = getattr(self.backend, "driver", None)
                if driver is not None:
                    self.driver = driver
        except Exception as e:
            logging.exception("Robot backend init failed for %r: %s", self.backend_id, e)
            self._backend_init_error = f"{type(e).__name__}: {e}"
            self.backend = None
            self.driver = URDriver()
        self.processor = None
        self._single_run_processor = None
        self.print_lib = URPrintLib()  # Initialize print library for calibration

        # 线程管理
        self.monitor_thread = MonitorThread(self.driver)
        self.monitor_thread.status_signal.connect(self.on_robot_status_update)

        self.conn_thread = None
        self.stop_thread = None
        self.script_thread = None
        self.reconnect_thread = None
        self.upload_thread = None
        self._direct_mode_processor = None  # Direct mode processor (30002 port)
        self._upload_queue = []
        self._upload_also_loader = False
        self.last_static_time = 0
        self._last_tcp_pose = None

        # URScript estimate (optional, default off)
        self._urscript_estimate_thread = None
        self._urscript_estimate_run_id = 0
        self._urscript_estimate_active_run_id = None

        # 初始化队列对话框为None
        self.queue_dialog = None
        self.queue_controller = QueueController(self)
        self.tools_controller = None
        self._log_service = None

        # 为队列对话框预留基本控件（不需要完整的dock）
        self.queue_list = None
        self.chk_watchdog = None
        self.btn_start_batch = None
        self.btn_stop_batch = None
        self.prog_batch = None

        self.dockable_editor = None  # Will be initialized in init_ui

        # 计算器对话框缓存（避免重复创建）
        self._calculator_dialogs = {}
        
        # 状态指示器脉冲动画相关
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._pulse_status_indicator)
        self._pulse_opacity = 1.0
        self._pulse_direction = -1  # -1 减淡, 1 增亮

        self.init_ui()
        if self._backend_init_error:
            self.log(f"机器人后端初始化失败：{self._backend_init_error}，已回退到默认驱动。", "WARN")
        self.log("UR5 Printer Studio (Modular Edition) 已启动。")

    def init_ui(self):
        self.setWindowTitle("UR5 Fiber Printer Studio (Expert Edition)")
        # 应用图标（机械臂 + FDM 喷嘴）
        self.setWindowIcon(IconManager().get_svg_icon('app_icon', (64, 64)))
        # Load window size from config
        window_size = config_manager.get("ui.window_size", [1400, 900])
        self.resize(window_size[0], window_size[1])

        # 居中显示主窗口
        self.center_on_screen()

        self._init_menus()
        self._init_toolbar()

        # === 左侧文件资源管理器 Dock ===
        self.dock_project = QDockWidget("文件资源管理器", self)
        self.project_widget = FileExplorerWidget()
        self.project_widget.script_loaded.connect(self.on_script_loaded)
        self.project_widget.file_requested.connect(self.open_file_in_tab)  # 连接新信号
        self.project_widget.log_requested.connect(self.log)  # 连接日志信号
        self.project_widget.upload_requested.connect(self.upload_selected_files)  # 右键上传
        self.project_widget.estimate_requested.connect(self.tool_script_estimate_from_path)
        self.dock_project.setWidget(self.project_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_project)

        # === 右侧状态 Dock (使用新组件) ===
        self.dock_status = QDockWidget("状态监视", self)
        self.status_widget = StatusWidget() # 实例化
        self.dock_status.setWidget(self.status_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_status)

        # === 底部日志 Dock ===
        self._init_dock_log()

        # 使右侧「状态监视」占据右下角并延伸至底部，系统日志仅位于编辑器/左侧下方
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        # === 中央编辑器区域（支持动态模式）===
        # 创建 dockable 编辑器区域，根据状态动态显示为单编辑器或标签页
        self.dockable_editor = DockableEditorWidget()
        self.setCentralWidget(self.dockable_editor)
        self.tools_controller = ToolsController(self, self.dockable_editor, self.log)

        # === 订阅主题变更 ===
        theme_mgr = get_theme_manager()
        theme_mgr.add_listener(self._on_theme_changed)

    def _on_theme_changed(self, theme_id: str):
        """主题变更时的回调函数"""
        self._refresh_theme_dependent_ui()


    def create_new_tab(self):
        """创建新标签页 (包装器)"""
        if self.dockable_editor:
            self.dockable_editor.create_new_tab()
    def get_current_editor(self):
        """获取当前活动的编辑器实例"""
        if self.dockable_editor:
            return self.dockable_editor.get_current_editor()
        return None

    def center_on_screen(self):
        """将主窗口居中显示"""
        screen_geometry = self.screen().availableGeometry()
        window_geometry = self.geometry()
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)

    # === 信号处理槽函数 ===
    def on_robot_status_update(self, tcp, joints, offset, speed):
        """核心状态更新函数"""
        # 检查底层连接状态
        if not self.driver.is_connected():
            self._update_status_indicator("disconnected")
            return

        # 更新状态指示器
        if self.driver.is_read_only():
            self._update_status_indicator("readonly")
        else:
            self._update_status_indicator("connected")

        # 自动重连逻辑：检测静止并自动重连
        is_static = speed < 0.002  # 速度小于 2 mm/s

        if self.driver.is_read_only() and self.chk_auto_reconnect.isChecked():
            if is_static:
                current_time = time.time()
                if current_time - self.last_static_time > 1.0:
                    if self.reconnect_thread is None:
                        self.log(f"检测到静止 (v={speed*1000:.1f}mm/s)，尝试自动重连...")
                        self.trigger_reconnect()
            else:
                self.last_static_time = time.time()
        else:
            self.last_static_time = time.time()

        if tcp is not None:
            self._last_tcp_pose = tcp

        # 更新各个子组件
        self.status_widget.update_status(tcp, joints, offset)
        
        # 更新TCP速度（新增）
        self.status_widget.update_tcp_speed(speed)
        
        # 根据速度自动判断运动状态
        if speed > 0.01:  # > 10 mm/s
            self.status_widget.set_motion_status(action="运动中", motion_type="--")
        else:
            self.status_widget.set_motion_status(action="静止", motion_type="--")

        # 安全检查：只有当标定面板被打开过（已实例化）时才更新它
        if hasattr(self, 'calib_widget') and self.calib_widget:
            self.calib_widget.update_live_tcp(tcp, joints)
    #
    def on_code_inserted(self, code):
        editor = self.get_current_editor()
        if editor:
            cursor = editor.textCursor()
            cursor.insertText(code + "\n")
            editor.setTextCursor(cursor)


    def on_script_loaded(self, script):
        # 获取当前活动的编辑器
        current_editor = self.get_current_editor()
        if current_editor is not None:
            current_editor.setPlainText(script)
        self.log("样件脚本已加载。")

    def open_project(self):
        """打开项目"""
        self.project_widget.open_project()

    def trigger_reconnect(self):
        self._update_status_indicator("reconnecting")

        from ur_print_fdm.shared.logging_context import new_trace_id

        trace_id = new_trace_id()
        self.reconnect_thread = ControlReconnectThread(self.driver, trace_id=trace_id)
        self.reconnect_thread.result_signal.connect(self.on_reconnect_result)
        self.reconnect_thread.finished.connect(lambda: setattr(self, 'reconnect_thread', None))
        self.reconnect_thread.start()

    def on_reconnect_result(self, success: bool, msg: str) -> None:
        if success:
            if self.driver.is_read_only():
                self._update_status_indicator("readonly")
            else:
                self._update_status_indicator("connected")
        else:
            self._update_status_indicator("readonly" if self.driver.is_read_only() else "disconnected")

    # === UI 初始化辅助 (菜单/工具栏/队列/日志) ===
    def _init_menus(self):
        menubar = self.menuBar()

        # 获取标准图标的辅助函数
        def icon(standard_pixmap):
            return self.style().standardIcon(standard_pixmap)

        SP = QStyle.StandardPixmap  # 简化引用

        # ============================================================
        # 文件菜单 (File)
        # ============================================================
        file_menu = menubar.addMenu("文件(&F)")

        # 新建
        act_new = QAction(icon(SP.SP_FileIcon), "新建脚本(&N)", self)
        act_new.setShortcut("Ctrl+N")
        act_new.setStatusTip("创建一个新的空白脚本文件")
        act_new.triggered.connect(self.create_new_tab)
        file_menu.addAction(act_new)

        # 打开项目
        act_open_project = QAction(icon(SP.SP_DirOpenIcon), "打开项目(&O)...", self)
        act_open_project.setShortcut("Ctrl+O")
        act_open_project.setStatusTip("打开一个项目文件夹")
        act_open_project.triggered.connect(self.open_project)
        file_menu.addAction(act_open_project)

        # 保存
        act_save = QAction(icon(SP.SP_DialogSaveButton), "保存(&S)", self)
        act_save.setShortcut("Ctrl+S")
        act_save.setStatusTip("保存当前编辑的脚本")
        act_save.triggered.connect(self.save_current_script)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        # 退出
        act_exit = QAction(icon(SP.SP_DialogCloseButton), "退出(&X)", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.setStatusTip("退出程序")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # ============================================================
        # 工具菜单 (Tools) - 整合原有分散的功能
        # ============================================================
        tools_menu = menubar.addMenu("工具(&T)")

        # --- 计算工具子菜单 ---
        calc_submenu = tools_menu.addMenu(icon(SP.SP_ComputerIcon), "工艺计算器")
        calc_submenu.setStatusTip("打印工艺参数计算工具集")

        act_flow = QAction("流量控制", self)
        act_flow.setStatusTip("根据线宽、层高和速度计算挤出机流量参数")
        act_flow.triggered.connect(lambda: self.show_specific_calculator('flow'))
        calc_submenu.addAction(act_flow)

        act_turntable = QAction("转台同步", self)
        act_turntable.setStatusTip("计算转台旋转与机器人运动的同步参数")
        act_turntable.triggered.connect(lambda: self.show_specific_calculator('turntable'))
        calc_submenu.addAction(act_turntable)

        tools_menu.addSeparator()

        # --- 样件生成库 ---
        act_library = QAction(icon(SP.SP_FileDialogContentsView), "样件生成库(&L)...", self)
        act_library.setShortcut("Ctrl+L")
        act_library.setStatusTip("从预设模板快速生成打印路径脚本")
        act_library.triggered.connect(self.show_library_panel)
        tools_menu.addAction(act_library)

        # --- 平面标定 ---
        act_calibration = QAction(icon(SP.SP_DialogResetButton), "平面标定(&C)...", self)
        act_calibration.setStatusTip("通过三点标定建立工件坐标系")
        act_calibration.triggered.connect(self.show_calibration_panel)
        tools_menu.addAction(act_calibration)

        tools_menu.addSeparator()

        # --- 脚本工具子菜单 ---
        script_submenu = tools_menu.addMenu(icon(SP.SP_FileDialogDetailedView), "脚本处理")

        act_gcode = QAction("G-code 转换...", self)
        act_gcode.setStatusTip("将切片软件生成的 G-code 转换为 URScript")
        act_gcode.triggered.connect(self.tool_gcode_convert)
        script_submenu.addAction(act_gcode)

        act_split = QAction("脚本分割...", self)
        act_split.setStatusTip("将大型脚本按层或行数分割为多个小文件")
        act_split.triggered.connect(self.tool_split_script)
        script_submenu.addAction(act_split)

        act_flag = QAction("插入标志...", self)
        act_flag.setStatusTip("在脚本中插入 DO 信号标志用于生产监控")
        act_flag.triggered.connect(self.tool_insert_flag)
        script_submenu.addAction(act_flag)

        act_estimate = QAction("脚本估算...", self)
        act_estimate.setStatusTip("估算 URScript 的打印时间与线材长度")
        act_estimate.triggered.connect(self.tool_script_estimate)
        script_submenu.addAction(act_estimate)

        tools_menu.addSeparator()

        # --- 生产队列 ---
        act_queue = QAction(icon(SP.SP_FileDialogListView), "生产队列(&Q)...", self)
        act_queue.setShortcut("Ctrl+Q")
        act_queue.setStatusTip("管理批量生产任务队列")
        act_queue.triggered.connect(self.show_queue_panel)
        tools_menu.addAction(act_queue)

        # ============================================================
        # 设置菜单 (Settings)
        # ============================================================
        settings_menu = menubar.addMenu("设置(&S)")

        act_settings = QAction(icon(SP.SP_FileDialogDetailedView), "设置中心 / 首选项(&P)...", self)
        act_settings.setShortcut("Ctrl+,")
        act_settings.setStatusTip("打开设置中心：分类 + 搜索 + Apply/OK/Cancel")
        act_settings.triggered.connect(self.show_settings_panel)
        settings_menu.addAction(act_settings)

        act_open_logs = QAction(icon(SP.SP_DirOpenIcon), "打开日志目录(&L)", self)
        act_open_logs.setStatusTip("在资源管理器中打开日志文件保存目录")
        act_open_logs.triggered.connect(self.open_logs_directory)
        settings_menu.addAction(act_open_logs)

        # ============================================================
        # 帮助菜单 (Help)
        # ============================================================
        help_menu = menubar.addMenu("帮助(&H)")

        act_help = QAction(icon(SP.SP_DialogHelpButton), "说明文档(&D)...", self)
        act_help.setStatusTip("查看软件说明文档")
        act_help.triggered.connect(self.show_help_dialog)
        help_menu.addAction(act_help)

        act_notes = QAction(icon(SP.SP_FileDialogInfoView), "打印注意事项(&N)...", self)
        act_notes.setStatusTip("查看与维护打印注意事项")
        act_notes.triggered.connect(self.show_printing_notes_dialog)
        help_menu.addAction(act_notes)

        help_menu.addSeparator()

        act_about = QAction(icon(SP.SP_MessageBoxInformation), "关于(&A)", self)
        act_about.setStatusTip("查看软件版本和版权信息")
        act_about.triggered.connect(self._show_about_dialog)
        help_menu.addAction(act_about)

    def _show_about_dialog(self):
        """显示关于对话框"""
        StyledMessageBox.about(
            self,
            "关于 UR5 Fiber Printer Studio",
            "UR5 Fiber Printer Studio\n\n"
            "Expert Edition v1.0\n\n"
            "专为 UR5 机器人纤维增强 3D 打印工艺开发的集成环境\n\n"
            "基于 PyQt6 + ur_rtde 构建"
        )

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setStyleSheet("QToolBar { spacing: 10px; padding: 6px 8px; border: none; }")
        self.addToolBar(toolbar)

        # 获取标准图标的辅助函数
        def icon(sp):
            return self.style().standardIcon(sp)
        SP = QStyle.StandardPixmap

        # ============================================================
        # 区域1: 连接控制
        # ============================================================
        lbl_ip = QLabel("机器人:")
        lbl_ip.setProperty("ui_role", "toolbar_label")
        toolbar.addWidget(lbl_ip)

        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        fix_combobox_popup(self.ip_combo, allow_edit=True)  # 修复弹出框覆盖问题
        self.ip_combo.setMinimumWidth(140)
        self.ip_combo.setMaximumWidth(160)
        self.ip_combo.setProperty("ui_role", "toolbar_combo")
        self.ip_combo.setMaxVisibleItems(10)

        ip_addresses = config_manager.get("robot.ip_addresses",
            ["192.168.137.120", "192.168.137.100", "192.168.244.129", "192.168.56.101"])
        self.ip_combo.addItems(ip_addresses)
        default_ip = config_manager.get("robot.default_ip", "192.168.56.101")
        self.ip_combo.setCurrentText(default_ip)
        self.ip_combo.setToolTip("输入或选择 UR 机器人的 IP 地址")
        toolbar.addWidget(self.ip_combo)

        # 连接按钮
        self.btn_connect = QPushButton("连接")
        self.btn_connect.setObjectName("btn-toolbar-connect")
        self.btn_connect.setIcon(icon(SP.SP_ComputerIcon))
        self.btn_connect.setToolTip("连接到机器人并开始状态监控")
        self.btn_connect.setCheckable(True)
        self.btn_connect.clicked.connect(self.toggle_monitor)
        toolbar.addWidget(self.btn_connect)

        toolbar.addSeparator()

        # ============================================================
        # 区域2: 状态指示器 (LED风格优化 + 文字标签)
        # ============================================================
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(20, 20)  # 增大尺寸提高可见性
        self.status_indicator.setStyleSheet("""
            QLabel {
                background-color: #616161;
                border-radius: 10px;
                border: 2px solid #454545;
            }
        """)
        self.status_indicator.setToolTip("未连接到机器人\n请输入IP地址并点击连接")
        
        # 状态文字标签（减少对 Tooltip 的依赖）
        self.status_text_label = QLabel("未连接")
        self.status_text_label.setStyleSheet("""
            QLabel {
                color: #8a8a8a;
                font-size: 9pt;
                font-weight: 500;
                padding-left: 4px;
            }
        """)

        # 状态指示器容器，保证垂直居中
        indicator_container = QWidget()
        indicator_container.setStyleSheet("background: transparent;")
        indicator_layout = QHBoxLayout(indicator_container)
        indicator_layout.setContentsMargins(8, 0, 8, 0)
        indicator_layout.setSpacing(4)
        indicator_layout.addWidget(self.status_indicator, 0, Qt.AlignmentFlag.AlignVCenter)
        indicator_layout.addWidget(self.status_text_label, 0, Qt.AlignmentFlag.AlignVCenter)
        toolbar.addWidget(indicator_container)

        # ============================================================
        # 区域3: 脚本操作
        # ============================================================
        # 保存按钮
        self.btn_save = QPushButton("保存")
        self.btn_save.setIcon(icon(SP.SP_DialogSaveButton))
        self.btn_save.setToolTip("保存当前脚本 (Ctrl+S)")
        # self.btn_save.setShortcut("Ctrl+S") # 移除重复的快捷键定义，避免 Ambiguous shortcut overload
        self.btn_save.clicked.connect(self.save_current_script)
        toolbar.addWidget(self.btn_save)

        toolbar.addSeparator()

        # ============================================================
        # 区域4: 运行控制
        # ============================================================
        icon_mgr = IconManager()
        # Cache icons for stateful buttons (run/pause).
        self._icon_play = icon_mgr.get_svg_icon("play", (16, 16))
        self._icon_pause = icon_mgr.get_svg_icon("pause", (16, 16))

        # 运行模式（UR5 CB3 推荐：生产模式= SFTP 上传 + Dashboard 加载 loader.urp）
        lbl_mode = QLabel("模式:")
        lbl_mode.setProperty("ui_role", "toolbar_label")
        toolbar.addWidget(lbl_mode)

        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItem("生产模式", "production")
        self.run_mode_combo.addItem("直连模式", "direct")
        fix_combobox_popup(self.run_mode_combo)  # 修复弹出框覆盖问题（必须在 addItem 之后调用）
        self.run_mode_combo.setProperty("ui_role", "toolbar_combo")
        self.run_mode_combo.setMinimumWidth(80)
        self.run_mode_combo.setMaximumWidth(100)
        self.run_mode_combo.setToolTip(
            "生产模式（推荐，CB3 最稳定）：\n"
            "• SFTP 上传脚本到机器人\n"
            "• Dashboard 控制执行\n"
            "• 支持可靠的暂停/继续\n\n"
            "直连模式（调试用途）：\n"
            "• 直接发送脚本执行\n"
            "• 不支持可靠暂停/继续"
        )
        default_mode = str(config_manager.get("ui.run_mode", "production") or "production")
        default_idx = self.run_mode_combo.findData(default_mode)
        if default_idx >= 0:
            self.run_mode_combo.setCurrentIndex(default_idx)
        self.run_mode_combo.currentIndexChanged.connect(self._on_run_mode_changed)
        toolbar.addWidget(self.run_mode_combo)

        # 运行 / 暂停（合并按钮，自动切换）
        self.btn_play_pause = QPushButton("运行")
        self.btn_play_pause.setObjectName("btn-toolbar-primary")
        self.btn_play_pause.setIcon(self._icon_play)
        self.btn_play_pause.setToolTip(
            "运行 / 暂停 / 继续\n"
            "提示：生产模式下支持暂停/继续；直连 RTDE 不支持可靠暂停/继续。"
        )
        self.btn_play_pause.clicked.connect(self._on_play_pause_clicked)
        self.btn_play_pause.setEnabled(False)
        toolbar.addWidget(self.btn_play_pause)

        # 停止按钮
        self.btn_global_stop = QPushButton("停止")
        self.btn_global_stop.setObjectName("btn-toolbar-danger")
        self.btn_global_stop.setIcon(icon_mgr.get_svg_icon("stop", (16, 16)))
        self.btn_global_stop.setToolTip("紧急停止机器人\n立即终止当前脚本执行")
        self.btn_global_stop.clicked.connect(self.stop_current_script)
        self.btn_global_stop.setEnabled(False)
        toolbar.addWidget(self.btn_global_stop)

        # 上传按钮（独立功能：有时需要手动传文件到机器人端）
        self.btn_upload = QPushButton("上传")
        self.btn_upload.setObjectName("btn-toolbar-ghost")
        self.btn_upload.setIcon(icon_mgr.get_svg_icon("upload", (16, 16)))
        self.btn_upload.setToolTip(
            "通过 SFTP 上传文件到机器人端 programs 目录\n"
            "默认目标目录来自设置中心：设置 -> 设置中心/首选项 -> 传输 (SFTP)"
        )
        self.btn_upload.clicked.connect(self.upload_files)
        self.btn_upload.setEnabled(True)
        toolbar.addWidget(self.btn_upload)

        # ============================================================
        # 区域5: 辅助功能
        # ============================================================
        spacer = QWidget()
        spacer.setStyleSheet("background: transparent;")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # 自动重连
        self.chk_auto_reconnect = QCheckBox("自动重连")
        self.chk_auto_reconnect.setChecked(config_manager.get("robot.auto_reconnect", True))
        self.chk_auto_reconnect.setToolTip("当控制权丢失且机器人静止时，自动尝试重新获取控制权")
        toolbar.addWidget(self.chk_auto_reconnect)

        # 手动重连按钮 (使用专业 SVG 图标)
        self.btn_reconnect = QPushButton()
        self.btn_reconnect.setObjectName("btn-toolbar-icon")
        self.btn_reconnect.setIcon(IconManager().get_svg_icon('reconnect', (18, 18)))
        self.btn_reconnect.setIconSize(QSize(18, 18))
        self.btn_reconnect.setToolTip("手动重新连接控制接口")
        self.btn_reconnect.clicked.connect(self.trigger_reconnect)
        self.btn_reconnect.setEnabled(False)
        self.btn_reconnect.setFixedSize(28, 28)
        toolbar.addWidget(self.btn_reconnect)

        # 别名兼容
        self.btn_connect_action = self.btn_connect
        self.btn_save_script = self.btn_save
        self.lbl_control_status = self.status_indicator

    def _update_status_indicator(self, status: str, extra_info: str = ""):
        """
        统一更新状态指示器 (LED 模式 + 文字标签)
        """
        styles = {
            "disconnected": {
                "name": "未连接",
                "bg": "#616161",
                "border": "#454545",
                "text_color": "#8a8a8a",
                "tooltip": "状态: 未连接\n原因: 机器人未连接或监控已停止",
                "pulse": False
            },
            "connecting": {
                "name": "连接中...",
                "bg": "#1976D2",
                "border": "#64B5F6",
                "text_color": "#64B5F6",
                "tooltip": "状态: 正在连接...\n操作: 请等待握手信号完成",
                "pulse": True
            },
            "connected": {
                "name": "已连接",
                "bg": "#388E3C",
                "border": "#81C784",
                "text_color": "#81C784",
                "tooltip": "状态: 控制正常\n权限: 读写权限已获取\n提示: 可以正常发送脚本",
                "pulse": False
            },
            "readonly": {
                "name": "只读",
                "bg": "#D32F2F",
                "border": "#EF9A9A",
                "text_color": "#EF9A9A",
                "tooltip": "状态: 只读 (权限受限)\n原因: 控制接口被占用\n提示: 机器人静止后将自动重连",
                "pulse": False
            },
            "reconnecting": {
                "name": "重连中...",
                "bg": "#FFA000",
                "border": "#FFD54F",
                "text_color": "#FFD54F",
                "tooltip": "状态: 尝试重连...\n提示: 正在重新申请控制令牌",
                "pulse": True
            },
            "error": {
                "name": "错误",
                "bg": "#C62828",
                "border": "#FF8A80",
                "text_color": "#FF8A80",
                "tooltip": f"状态: 连接异常\n详情: {extra_info}",
                "pulse": False
            }
        }

        config = styles.get(status, styles["disconnected"])

        # 更新 LED 样式
        self.status_indicator.setToolTip(config["tooltip"])
        
        # 更新状态文字标签
        if hasattr(self, "status_text_label") and self.status_text_label:
            self.status_text_label.setText(config["name"])
            self.status_text_label.setStyleSheet(f"""
                QLabel {{
                    color: {config['text_color']};
                    font-size: 9pt;
                    font-weight: 500;
                    padding-left: 4px;
                }}
            """)

        # 联动状态监视面板的连接指示
        if hasattr(self, "status_widget") and self.status_widget:
            is_data = status in ["connected", "readonly", "reconnecting"]
            self.status_widget.set_connection_status(is_data, config["name"])
        
        # 脉冲动画效果（连接中/重连中时启用）
        if config.get("pulse", False):
            if not self._pulse_timer.isActive():
                self._pulse_opacity = 1.0
                self._pulse_direction = -1
                self._current_pulse_color = config['bg']
                self._pulse_timer.start(50)  # 50ms 更新一次
        else:
            self._pulse_timer.stop()
            self._pulse_opacity = 1.0
        
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {config['bg']};
                border: 2px solid {config['border']};
                border-radius: 10px;
            }}
        """)

        # 联动按钮逻辑
        is_connected = status in ["connected", "readonly", "reconnecting"]
        # 生产模式（loader.urp）只需要 SFTP + Dashboard，可在 readonly 下运行
        is_can_run = status in ["connected", "readonly"]

        self.btn_connect.setChecked(is_connected)
        self.btn_connect.setText("断开" if is_connected else "连接")
        # self.btn_connect.setToolTip("断开与机器人的连接" if is_connected else "连接到机器人并开始状态监控")

        self.btn_play_pause.setEnabled(is_can_run)
        self.btn_global_stop.setEnabled(is_connected)
        self.btn_reconnect.setEnabled(status == "readonly")
        self.ip_combo.setEnabled(not is_connected)
        self._sync_play_pause_button_state()

    def _pulse_status_indicator(self):
        """脉冲动画：使状态指示器呼吸闪烁"""
        self._pulse_opacity += self._pulse_direction * 0.05
        if self._pulse_opacity <= 0.4:
            self._pulse_opacity = 0.4
            self._pulse_direction = 1
        elif self._pulse_opacity >= 1.0:
            self._pulse_opacity = 1.0
            self._pulse_direction = -1
        
        # 应用透明度到背景色
        base_color = getattr(self, '_current_pulse_color', '#1976D2')
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {base_color};
                border: 2px solid {base_color};
                border-radius: 10px;
                opacity: {self._pulse_opacity};
            }}
        """)

    def _get_active_production_processor(self):
        """Return the currently running ProductionProcessor (queue or single-run), if any."""
        for proc in (getattr(self, "_single_run_processor", None), getattr(self, "processor", None)):
            if proc is not None and hasattr(proc, "isRunning") and proc.isRunning():
                return proc
        return None

    # -----------------------------
    # Toolbar: Run / Pause / Upload
    # -----------------------------

    def _set_play_pause_state(self, state: str) -> None:
        """Update the integrated Run/Pause button visual state.

        State meanings:
        - "run": next click will Run / Resume
        - "pause": next click will Pause
        """
        if not hasattr(self, "btn_play_pause") or self.btn_play_pause is None:
            return

        state = str(state or "run").strip().lower()
        if state not in ("run", "pause"):
            state = "run"

        if state == "pause":
            self.btn_play_pause.setText("暂停")
            try:
                self.btn_play_pause.setIcon(self._icon_pause)
            except Exception:
                pass
            # Orange indicates "running" (next click pauses)
            self.btn_play_pause.setStyleSheet(
                """
                QPushButton {
                    background-color: #F57C00;
                    color: white;
                    padding: 5px 14px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #FB8C00; }
                QPushButton:pressed { background-color: #EF6C00; }
                QPushButton:disabled { background-color: #E65100; color: #FFE0B2; }
                """
            )
        else:
            self.btn_play_pause.setText("运行")
            try:
                self.btn_play_pause.setIcon(self._icon_play)
            except Exception:
                pass
            self.btn_play_pause.setStyleSheet(
                """
                QPushButton {
                    background-color: #388E3C;
                    color: white;
                    padding: 5px 14px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #43A047; }
                QPushButton:pressed { background-color: #2E7D32; }
                QPushButton:disabled { background-color: #1B5E20; color: #81C784; }
                """
            )

    def _sync_play_pause_button_state(self) -> None:
        """Sync play/pause button based on the active ProductionProcessor state."""
        active = self._get_active_production_processor()
        if active is not None and hasattr(active, "isRunning") and active.isRunning():
            is_paused = bool(getattr(active, "paused", False))
            self._set_play_pause_state("run" if is_paused else "pause")
        else:
            self._set_play_pause_state("run")

    def _on_play_pause_clicked(self) -> None:
        """Integrated Run/Pause button handler."""
        active = self._get_active_production_processor()
        if active is not None and hasattr(active, "isRunning") and active.isRunning():
            was_paused = bool(getattr(active, "paused", False))
            try:
                if was_paused:
                    if hasattr(active, "request_resume"):
                        active.request_resume()
                    self.log("已请求继续（Dashboard play）", "INFO")
                    # Optimistic UI: the worker thread will flip `paused` once the command is applied.
                    self._set_play_pause_state("pause")
                else:
                    if hasattr(active, "request_pause"):
                        active.request_pause()
                    self.log("已请求暂停（Dashboard pause）", "INFO")
                    self._set_play_pause_state("run")
            except Exception as e:
                self.log(f"暂停/继续失败: {e}", "ERROR")
                self._sync_play_pause_button_state()
            return

        self.run_current_script()

    def upload_files(self) -> None:
        """Manual SFTP upload helper (independent from production run)."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "上传文件到机器人 programs 目录",
            "",
            "UR Programs/Scripts (*.urp *.script *.txt);;All Files (*.*)",
        )
        if not files:
            return
        self._begin_upload(files)

    def upload_selected_files(self, files: list) -> None:
        """右键菜单上传选中的文件"""
        if not files:
            return
        self._begin_upload(files)

    def _begin_upload(self, files: list) -> None:
        """统一上传入口，支持右键菜单与文件对话框"""
        if self.upload_thread is not None and self.upload_thread.isRunning():
            self.log("正在上传中，请稍候…", "WARN")
            return

        ip = str(self.ip_combo.currentText() or "").strip()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self, "IP 无效", f"不是有效的 IP 地址：{ip}")
            return

        # 询问上传方式
        dialog = StyledMessageBox(self, "上传选项", "请选择上传方式：", StyledMessageBox.Question)
        dialog.add_button("仅上传", "primary", is_default=True, is_accent=True)
        dialog.add_button("上传并同步加载器", "dual", is_default=False, is_accent=False)
        dialog.add_button("取消", StyledMessageBox.Cancel, is_default=False, is_accent=False)
        dialog.exec()
        result = dialog.result_role()
        if result == StyledMessageBox.Cancel or result is None:
            return
        also_upload_loader = (result == "dual")

        self._upload_queue = list(files)
        self._upload_also_loader = bool(also_upload_loader)
        if hasattr(self, "btn_upload") and self.btn_upload is not None:
            try:
                self.btn_upload.setEnabled(False)
            except Exception:
                pass
        self._start_next_upload(ip)

    def _start_next_upload(self, ip: str) -> None:
        if not self._upload_queue:
            if hasattr(self, "btn_upload") and self.btn_upload is not None:
                try:
                    self.btn_upload.setEnabled(True)
                except Exception:
                    pass
            return

        local_path = self._upload_queue.pop(0)
        remote_dir = str(config_manager.get("robot.sftp.remote_dir", "/home/ur/ursim-current/programs") or "")
        remote_name = os.path.basename(local_path)

        self.upload_thread = SFTPUploadThread(
            ip,
            local_path,
            remote_dir=remote_dir,
            remote_filename=remote_name,
            also_upload_loader=self._upload_also_loader,
        )
        self.upload_thread.result_signal.connect(self._on_upload_result)
        self.upload_thread.finished.connect(self.upload_thread.deleteLater)
        self.upload_thread.finished.connect(lambda: setattr(self, "upload_thread", None))
        self.upload_thread.finished.connect(lambda: self._start_next_upload(ip))
        self.upload_thread.start()

    def _on_upload_result(self, success: bool, message: str) -> None:
        self.log(str(message), "SUCCESS" if success else "ERROR")

    def _on_pause_clicked(self):
        """兼容旧的“暂停/继续”按钮：转发到合并后的运行/暂停逻辑。"""
        self._on_play_pause_clicked()

    def _init_dock_queue(self):
        # 检查是否已经初始化了队列
        if hasattr(self, 'dock_queue') and self.dock_queue:
            # 如果已经存在，只需显示它
            self.dock_queue.show()
            self.dock_queue.raise_()
            return

        self.dock_queue = QDockWidget("生产队列", self)
        self.dock_queue.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        queue_widget = QWidget()
        vbox = QVBoxLayout(queue_widget)
        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        # 添加双击事件处理
        self.queue_list.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
        vbox.addWidget(self.queue_list)
        icon_mgr = IconManager()
        hbox = QHBoxLayout()
        self.btn_queue_add = QPushButton("添加")
        self.btn_queue_add.setIcon(icon_mgr.get_svg_icon('add', (16, 16)))
        self.btn_queue_add.clicked.connect(self.queue_add)
        self.btn_queue_del = QPushButton("删除")
        self.btn_queue_del.setIcon(icon_mgr.get_svg_icon('trash', (16, 16)))
        self.btn_queue_del.clicked.connect(self.queue_remove)
        self.btn_queue_clear = QPushButton("清空")
        self.btn_queue_clear.clicked.connect(self.queue_list.clear)
        self.btn_queue_save = QPushButton("保存选中")
        self.btn_queue_save.setIcon(icon_mgr.get_svg_icon('save', (16, 16)))
        self.btn_queue_save.clicked.connect(self.save_selected_script)
        hbox.addWidget(self.btn_queue_add); hbox.addWidget(self.btn_queue_del); hbox.addWidget(self.btn_queue_clear); hbox.addWidget(self.btn_queue_save)
        vbox.addLayout(hbox)
        self.chk_watchdog = QGroupBox("安全设置")
        self.chk_watchdog.setCheckable(True); self.chk_watchdog.setTitle("启用挤出看门狗"); self.chk_watchdog.setChecked(True)
        vbox.addWidget(self.chk_watchdog)
        self.btn_start_batch = QPushButton("开始队列生产")
        self.btn_start_batch.setIcon(IconManager().get_svg_icon('play', (16, 16)))
        self.btn_start_batch.clicked.connect(self.start_production)
        vbox.addWidget(self.btn_start_batch)
        self.btn_stop_batch = QPushButton("停止 / 急停")
        self.btn_stop_batch.setIcon(IconManager().get_svg_icon('stop', (16, 16)))
        self.btn_stop_batch.clicked.connect(self.stop_production)
        self.btn_stop_batch.setEnabled(False)
        vbox.addWidget(self.btn_stop_batch)
        self.prog_batch = QProgressBar()
        vbox.addWidget(self.prog_batch)
        self.dock_queue.setWidget(queue_widget)

    def show_queue_panel(self):
        """显示生产队列面板 - 使用对话框形式"""
        if self.queue_dialog is None:
            # 如果对话框尚未创建，则创建它
            from ur_print_fdm.ui.widgets.queue_dialog import QueueDialog
            self.queue_dialog = QueueDialog(self)
            # 连接对话框的信号
            self.queue_dialog.queue_list.itemDoubleClicked.connect(self.on_queue_item_double_clicked)
            # 设置当对话框关闭时，重置引用以便下次能重新创建
            self.queue_dialog.finished.connect(self.on_queue_dialog_closed)

        # 无论是否新建，都显示对话框
        self.queue_dialog.show()
        # 确保对话框在前端显示
        self.queue_dialog.raise_()
        self.queue_dialog.activateWindow()

    def on_queue_dialog_closed(self):
        """当队列对话框关闭时的处理"""
        # 重置引用，允许下次重新创建
        self.queue_dialog = None

    # 以下是与队列对话框交互的方法
    def queue_add_to_dialog(self, dialog_list):
        """向对话框中的队列添加项目"""
        files, _ = QFileDialog.getOpenFileNames(self, "添加脚本", "", "URScript (*.script *.txt);;All (*.*)")
        if files:
            for f in files:
                dialog_list.addItem(f)
            self.log(f"添加 {len(files)} 个文件到队列。")

    def queue_remove_from_dialog(self, dialog_list):
        """从对话框中的队列删除项目"""
        for item in dialog_list.selectedItems():
            dialog_list.takeItem(dialog_list.row(item))

    def save_selected_script_dialog(self, dialog_list):
        """从对话框保存选中的脚本"""
        selected_items = dialog_list.selectedItems()
        if not selected_items:
            StyledMessageBox.warning(self, "警告", "请先选择要保存的文件！")
            return

        if len(selected_items) > 1:
            StyledMessageBox.warning(self, "警告", "只能同时保存一个文件！")
            return

        selected_item = selected_items[0]
        file_path = selected_item.text()

        # 确认是否覆盖
        reply = StyledMessageBox.question(self, "确认保存", f"是否保存到文件？\n{file_path}")
        if reply == StyledMessageBox.Yes:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.dockable_editor.current_text())
                self.log(f"已保存到文件: {file_path}")
            except Exception as e:
                self.log(f"保存文件失败: {e}")
                StyledMessageBox.critical(self, "错误", f"保存文件失败：\n{e}")

    def start_production_dialog(self, dialog_list, watchdog_enabled, prog_bar):
        """从对话框开始生产"""
        if dialog_list.count() == 0:
            StyledMessageBox.warning(self, "提示", "队列为空")
            return

        # 获取IP地址
        ip = self.ip_combo.currentText()
        # 获取队列中的脚本
        scripts = [dialog_list.item(i).text() for i in range(dialog_list.count())]

        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()
        self._active_production_trace_id = trace_id
        with trace_context(trace_id):
            self.log(f"[生产] 开始生产队列：{len(scripts)} 个脚本", "INFO")

        # 实例化引擎
        self.processor = ProductionProcessor(ip, SCRIPT_PORT, scripts, do_index=DEFAULT_DO_INDEX,
                                             watchdog_enable=watchdog_enabled, trace_id=trace_id)

        # 信号绑定
        self.processor.progress_signal.connect(lambda c, t: (prog_bar.setMaximum(t), prog_bar.setValue(c)))
        self.processor.finished_signal.connect(self.on_prod_finished_dialog)
        self.processor.error_signal.connect(lambda e: self._on_production_error(e, trace_id))
        self.processor.file_progress_signal.connect(self._on_single_run_file_progress)

        # UI 锁定 - 需要在对话框中禁用按钮
        # 直接修改对话框的按钮状态
        parent = dialog_list.parent()  # 这是队列对话框
        if hasattr(parent, 'btn_start_batch') and hasattr(parent, 'btn_stop_batch'):
            parent.btn_start_batch.setEnabled(False)
            parent.btn_stop_batch.setEnabled(True)
            if hasattr(parent, "btn_pause_batch"):
                parent.btn_pause_batch.setEnabled(True)
                parent.btn_pause_batch.setChecked(False)
                parent.btn_pause_batch.setText("暂停")

        try:
            self.run_mode_combo.setEnabled(False)
        except Exception:
            pass
        self._set_play_pause_state("pause")
        self.processor.start()

    def stop_production_dialog(self):
        """从对话框停止生产"""
        if self.processor and self.processor.isRunning():
            reply = StyledMessageBox.question(self, "急停", "确定要立即停止？")
            if reply == StyledMessageBox.Yes:
                self.processor.emergency_stop_action()
                self._reset_global_pause_button()
                if self.queue_dialog and hasattr(self.queue_dialog, "btn_pause_batch"):
                    self.queue_dialog.btn_pause_batch.setEnabled(False)

    def on_prod_finished_dialog(self):
        """生产完成回调（对话框版本）"""
        # 恢复对话框中的按钮状态
        if self.queue_dialog:
            self.queue_dialog.btn_start_batch.setEnabled(True)
            self.queue_dialog.btn_stop_batch.setEnabled(False)
            if hasattr(self.queue_dialog, "btn_pause_batch"):
                self.queue_dialog.btn_pause_batch.setEnabled(False)
                self.queue_dialog.btn_pause_batch.setChecked(False)
                self.queue_dialog.btn_pause_batch.setText("暂停")
        from ur_print_fdm.shared.logging_context import trace_context

        trace_id = getattr(self, "_active_production_trace_id", None)
        if trace_id:
            with trace_context(trace_id):
                self.log("生产任务结束")
            self._active_production_trace_id = None
        else:
            self.log("生产任务结束")
        try:
            self.run_mode_combo.setEnabled(True)
        except Exception:
            pass
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()

    def _on_production_error(self, error_msg: str, trace_id: str) -> None:
        StyledMessageBox.critical(self, "生产错误", f"{error_msg}\n\nTrace ID: {trace_id}")

    def pause_production_dialog(self, is_paused: bool) -> None:
        """队列生产：暂停/继续（优先走 ProductionProcessor 的请求接口）。"""
        if not self.processor or not self.processor.isRunning():
            return

        try:
            if is_paused and hasattr(self.processor, "request_pause"):
                self.processor.request_pause()
                self.log("生产已请求暂停", "INFO")
                self._set_play_pause_state("run")
            elif (not is_paused) and hasattr(self.processor, "request_resume"):
                self.processor.request_resume()
                self.log("生产已请求继续", "INFO")
                self._set_play_pause_state("pause")
        except Exception as e:
            self.log(f"暂停/继续失败: {e}", "ERROR")

    # 以下是新增的菜单面板显示函数
    def show_specific_calculator(self, calc_type):
        """显示特定类型的独立计算器（使用缓存避免重复创建）"""
        # 检查缓存中是否已有该类型的对话框
        if calc_type in self._calculator_dialogs:
            dialog = self._calculator_dialogs[calc_type]
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            return

        # 根据类型创建不同的计算器窗口
        from PyQt6.QtWidgets import QDialog, QVBoxLayout
        from ur_print_fdm.ui.widgets.extrusion_calculator import ExtrusionCalculatorWidget
        from ur_print_fdm.ui.widgets.sync_calculator import SyncCalculatorWidget

        # 创建一个对话框来容纳特定的计算器
        dialog = QDialog(self)
        dialog.setWindowTitle(self._get_calculator_title(calc_type))
        dialog.setModal(False)
        dialog.resize(600, 500)

        # 居中显示
        self.center_dialog_on_parent(dialog)

        # 根据类型创建计算器部件
        if calc_type == 'flow':
            calc_widget = ExtrusionCalculatorWidget(show_only=calc_type)
        elif calc_type == 'turntable':
            calc_widget = SyncCalculatorWidget(show_only=calc_type)
        else:
            # 不支持的类型，返回
            return

        layout = QVBoxLayout()
        layout.addWidget(calc_widget)
        dialog.setLayout(layout)

        # 缓存对话框
        self._calculator_dialogs[calc_type] = dialog

        # 显示并激活对话框
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _get_calculator_title(self, calc_type):
        """根据计算器类型返回合适的标题"""
        titles = {
            'flow': "流量控制",
            'turntable': "转台同步",
        }
        return titles.get(calc_type, "计算器")

    def show_library_panel(self):
        """显示样件生成库面板"""
        if not hasattr(self, 'lib_dialog') or self.lib_dialog is None:
            from ur_print_fdm.ui.widgets.library import LibraryWidget
            from PyQt6.QtWidgets import QDialog, QVBoxLayout

            self.lib_dialog = QDialog(self)
            self.lib_dialog.setWindowTitle("样件生成库")
            self.lib_dialog.setModal(False)
            self.lib_dialog.resize(700, 600)

            # 居中显示
            self.center_dialog_on_parent(self.lib_dialog)

            # 创建样件库部件
            self.lib_widget = LibraryWidget()
            self.lib_widget.script_generated.connect(self.on_script_loaded)
            layout = QVBoxLayout()
            layout.addWidget(self.lib_widget)
            self.lib_dialog.setLayout(layout)

        # 显示并激活对话框
        self.lib_dialog.show()
        self.lib_dialog.raise_()
        self.lib_dialog.activateWindow()

    def show_calibration_panel(self):
        """显示平面标定面板"""
        if not hasattr(self, 'calib_dialog') or self.calib_dialog is None:
            from ur_print_fdm.ui.widgets.calibration import CalibrationWidget
            from PyQt6.QtWidgets import QDialog, QVBoxLayout

            self.calib_dialog = QDialog(self)
            self.calib_dialog.setWindowTitle("平面标定")
            self.calib_dialog.setModal(False)
            self.calib_dialog.resize(800, 700)

            # 居中显示
            self.center_dialog_on_parent(self.calib_dialog)

            # 创建标定部件
            self.calib_widget = CalibrationWidget(self)
            layout = QVBoxLayout()
            layout.addWidget(self.calib_widget)
            self.calib_dialog.setLayout(layout)

        # 显示并激活对话框
        self.calib_dialog.show()
        self.calib_dialog.raise_()
        self.calib_dialog.activateWindow()

    def show_settings_panel(self):
        """打开设置中心 / 首选项（分类 + 搜索 + Apply/OK/Cancel）"""
        if not hasattr(self, "preferences_dialog") or self.preferences_dialog is None:
            from ur_print_fdm.ui.widgets.preferences_dialog import PreferencesDialog

            # 用于判断哪些设置需要重启才能生效
            self._preferences_snapshot = config_manager.snapshot()

            self.preferences_dialog = PreferencesDialog(self)
            self.preferences_dialog.setModal(False)
            self.center_dialog_on_parent(self.preferences_dialog)

            # 当对话框关闭时，重置引用以便下次能重新创建
            self.preferences_dialog.finished.connect(lambda _=None: setattr(self, "preferences_dialog", None))

            # 应用设置后，刷新日志系统与界面（细节在 on_preferences_applied 里处理）
            self.preferences_dialog.settings_applied.connect(self.on_preferences_applied)

        self.preferences_dialog.show()
        self.preferences_dialog.raise_()
        self.preferences_dialog.activateWindow()

    def open_logs_directory(self):
        """打开日志保存目录（按天滚动保存的文件日志）"""
        try:
            from pathlib import Path
            from ur_print_fdm.paths import logs_dir

            cfg = config_manager.get("logging.dir", "")
            path = Path(cfg).expanduser() if cfg else logs_dir()
            path.mkdir(parents=True, exist_ok=True)

            os.startfile(str(path))
        except Exception as e:
            StyledMessageBox.warning(self, "打开失败", f"无法打开日志目录：{e}")

    def on_preferences_applied(self):
        """
        当“设置中心”点击 Apply/OK 后触发：
        - 重新加载/热更新：日志、UI日志过滤、窗口主题/大小、IP 列表等
        - 对需要重启才能生效的设置进行提示
        """
        before = getattr(self, "_preferences_snapshot", None) or {}
        after = config_manager.snapshot()
        self._preferences_snapshot = after

        # 1) Reconfigure file logging (level/dir/retention)
        try:
            from ur_print_fdm.shared.logging_setup import setup_file_logging

            setup = setup_file_logging(config_manager, reconfigure=True)
            logging.getLogger("ur_print_fdm").info("Logging reconfigured (dir=%s)", setup.log_dir)
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to reconfigure file logging: %s", e)

        # 2) Update UI log policy (min_level / third-party)
        try:
            from ur_print_fdm.ui.services.qt_log_handler import install_qt_log_handler

            if hasattr(self, "_qt_log_emitter") and self._qt_log_emitter is not None:
                self._qt_log_handler = install_qt_log_handler(config_manager, self._qt_log_emitter)
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to update UI log handler: %s", e)

        # 3) Update log panel behavior (max lines / auto scroll)
        try:
            if self._log_service is not None:
                self._log_service.set_max_lines(config_manager.get("ui.log_max_lines", 2000))
                self._log_service.set_auto_scroll(config_manager.get("ui.auto_scroll_log", True))
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to update log panel settings: %s", e)

        # 4) Sync common UI widgets from config
        try:
            # IP combobox
            ips = config_manager.get("robot.ip_addresses", []) or []
            if not isinstance(ips, list):
                ips = []
            ips = [str(x).strip() for x in ips if str(x).strip()]

            default_ip = str(config_manager.get("robot.default_ip", "") or "").strip()
            current_ip = self.ip_combo.currentText().strip() if hasattr(self, "ip_combo") else ""

            if hasattr(self, "ip_combo"):
                self.ip_combo.clear()
                self.ip_combo.addItems(ips)
                desired = default_ip or current_ip
                if desired:
                    self.ip_combo.setCurrentText(desired)

            # Auto reconnect toggle
            if hasattr(self, "chk_auto_reconnect") and self.chk_auto_reconnect is not None:
                self.chk_auto_reconnect.setChecked(bool(config_manager.get("robot.auto_reconnect", True)))
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to refresh toolbar state from config: %s", e)

        # 5) Apply theme/window size immediately where possible
        try:
            use_dark = bool(config_manager.get("ui.dark_theme", True))
            theme_mgr = get_theme_manager()
            theme_mgr.set_theme("dark" if use_dark else "light")
            # 不再需要手动刷新，组件会通过信号自动响应
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to apply theme: %s", e)

        try:
            size = config_manager.get("ui.window_size", None)
            if isinstance(size, list) and len(size) == 2:
                self.resize(int(size[0]), int(size[1]))
        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to apply window size: %s", e)

        # 6) Restart-required hints (backend selection, etc.)
        restart_reasons = []
        try:
            b_backend = (before.get("robot", {}) or {}).get("backend_id", None)
            a_backend = (after.get("robot", {}) or {}).get("backend_id", None)
            if b_backend is not None and a_backend is not None and b_backend != a_backend:
                restart_reasons.append(f"机器人后端：{b_backend} → {a_backend}")
        except Exception:
            pass

        if restart_reasons:
            StyledMessageBox.information(self, "需要重启生效", "以下设置需要重启软件后生效：\n" + "\n".join(restart_reasons))

    def _refresh_theme_dependent_ui(self) -> None:
        """Refresh icons / widget-local styles that are not fully covered by global QSS."""
        try:
            icon_mgr = IconManager()

            # Cached toolbar icons
            self._icon_play = icon_mgr.get_svg_icon("play", (16, 16))
            self._icon_pause = icon_mgr.get_svg_icon("pause", (16, 16))

            if hasattr(self, "btn_global_stop") and self.btn_global_stop is not None:
                self.btn_global_stop.setIcon(icon_mgr.get_svg_icon("stop", (16, 16)))
            if hasattr(self, "btn_upload") and self.btn_upload is not None:
                self.btn_upload.setIcon(icon_mgr.get_svg_icon("upload", (16, 16)))
            if hasattr(self, "btn_reconnect") and self.btn_reconnect is not None:
                self.btn_reconnect.setIcon(icon_mgr.get_svg_icon("reconnect", (18, 18)))

            # Queue panel buttons (created lazily)
            for attr, name, size in (
                ("btn_queue_add", "add", (16, 16)),
                ("btn_queue_del", "trash", (16, 16)),
                ("btn_queue_save", "save", (16, 16)),
                ("btn_start_batch", "play", (16, 16)),
                ("btn_stop_batch", "stop", (16, 16)),
            ):
                btn = getattr(self, attr, None)
                if btn is not None:
                    btn.setIcon(icon_mgr.get_svg_icon(name, size))

            # Run mode combo: 不再使用图标，保持纯文字
            # (图标已在初始化时移除，此处无需重新设置)

            # File explorer embedded header buttons (if any)
            if hasattr(self, "project_widget") and self.project_widget is not None:
                try:
                    self.project_widget.refresh_header_icons()
                except Exception:
                    pass

            # Library widget local overrides
            if hasattr(self, "lib_widget") and self.lib_widget is not None:
                try:
                    self.lib_widget.apply_theme()
                except Exception:
                    pass

            # Editor (tabs/status bar/inline welcome + per-editor colors)
            if hasattr(self, "dockable_editor") and self.dockable_editor is not None:
                try:
                    self.dockable_editor.apply_theme()
                except Exception:
                    pass

            # Status dock contains some widget-local QSS that must be re-mapped on theme switch.
            if hasattr(self, "status_widget") and self.status_widget is not None:
                try:
                    self.status_widget.apply_theme()
                except Exception:
                    pass

            # Help dialog HTML (theme-aware)
            if hasattr(self, "help_dialog") and self.help_dialog is not None:
                try:
                    self.help_dialog.apply_theme()
                except Exception:
                    pass

            # Printing notes detail HTML (theme-aware)
            if hasattr(self, "printing_notes_dialog") and self.printing_notes_dialog is not None:
                try:
                    self.printing_notes_dialog.apply_theme()
                except Exception:
                    pass

        except Exception as e:
            logging.getLogger("ur_print_fdm").exception("Failed to refresh theme-dependent UI: %s", e)

    def show_help_dialog(self):
        """??????"""
        if not hasattr(self, 'help_dialog') or self.help_dialog is None:
            from ur_print_fdm.ui.widgets.help_dialog import HelpDialog

            self.help_dialog = HelpDialog(self)
            self.help_dialog.setModal(False)
            self.center_dialog_on_parent(self.help_dialog)

        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()

    def show_printing_notes_dialog(self):
        """????????"""
        if not hasattr(self, 'printing_notes_dialog') or self.printing_notes_dialog is None:
            from ur_print_fdm.ui.widgets.printing_notes_dialog import PrintingNotesDialog

            self.printing_notes_dialog = PrintingNotesDialog(self)
            self.printing_notes_dialog.setModal(False)
            self.center_dialog_on_parent(self.printing_notes_dialog)

        self.printing_notes_dialog.show()
        self.printing_notes_dialog.raise_()
        self.printing_notes_dialog.activateWindow()

    def center_dialog_on_parent(self, dialog):
        """将对话框相对于主窗口居中"""
        # 相对于主窗口居中
        main_geo = self.geometry()
        x = main_geo.x() + (main_geo.width() - dialog.width()) // 2
        y = main_geo.y() + (main_geo.height() - dialog.height()) // 2
        dialog.move(x, y)

    def open_file_in_tab(self, file_path):
        """在新标签页中打开文件"""
        self.dockable_editor.open_file_in_tab(file_path)

    def _init_dock_log(self):
        """初始化日志面板 - VSCode/专业IDE风格，功能集成到右键菜单"""
        self.dock_log = QDockWidget("输出", self)  # VSCode 风格命名
        
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 0, 0, 0)  # 无边距，更紧凑
        log_layout.setSpacing(0)

        # 日志显示区域 - 使用增强版日志组件
        from ur_print_fdm.ui.widgets.log_display import LogTextEdit
        self.console = LogTextEdit(parent=self)
        self.console.filter_changed.connect(self._on_log_filter_changed)
        log_layout.addWidget(self.console)
        
        self._log_service = LogService(
            self.console,
            max_lines=config_manager.get("ui.log_max_lines", 2000),
            auto_scroll=config_manager.get("ui.auto_scroll_log", True),
        )
        
        # 当前日志过滤级别
        self._log_filter_level = "ALL"

        # Bridge Python logging -> UI log console (thread-safe via Qt signals)
        from ur_print_fdm.ui.services.qt_log_handler import QtLogEmitter, install_qt_log_handler

        self._qt_log_emitter = QtLogEmitter()
        self._qt_log_emitter.message.connect(self._on_log_message_from_handler)
        self._qt_log_handler = install_qt_log_handler(config_manager, self._qt_log_emitter)

        self.dock_log.setWidget(log_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_log)
    
    def _on_log_filter_changed(self, level: str):
        """日志过滤级别变更（来自右键菜单）"""
        self._log_filter_level = level


    def log(self, msg, level="INFO"):
        ui_level = str(level).upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "SUCCESS": logging.INFO,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }
        levelno = level_map.get(ui_level, logging.INFO)
        logging.getLogger("ur_print_fdm.ui").log(levelno, str(msg), extra={"ui_level": ui_level}, stacklevel=2)

    def _on_log_message_from_handler(self, ui_level: str, message: str) -> None:
        if self._log_service is None:
            return
        
        # 应用日志过滤
        filter_level = getattr(self, '_log_filter_level', 'ALL')
        ui_level_upper = ui_level.upper()
        
        if filter_level == "ERROR" and ui_level_upper not in ("ERROR",):
            return
        elif filter_level == "WARN" and ui_level_upper not in ("ERROR", "WARN", "WARNING"):
            return
        
        self._log_service.log(message, ui_level)

    # === 业务逻辑封装 ===
    def clear_log(self):
        """清除系统日志"""
        if self._log_service is not None:
            self._log_service.clear()
        else:
            self.console.clear()
        self.log("日志已清除", "INFO")

    def _on_run_mode_changed(self) -> None:
        """保存运行模式选择，并在 CB3 只读模式下自动回退到生产模式。"""
        mode = "production"
        try:
            mode = str(self.run_mode_combo.currentData() or "production")
        except Exception:
            mode = "production"

        # CB3: 只读模式下无法 RTDE 发送脚本，强制回退到生产模式
        try:
            if self.driver.is_connected() and self.driver.is_read_only() and mode == "direct":
                idx = self.run_mode_combo.findData("production")
                if idx >= 0:
                    self.run_mode_combo.setCurrentIndex(idx)
                self.log("只读模式下无法直连发送脚本，已切换到生产模式（SFTP+loader.urp）。", "WARN")
                mode = "production"
        except Exception:
            pass

        try:
            config_manager.set("ui.run_mode", mode)
            config_manager.save_config()
        except Exception:
            pass

    def _reset_global_pause_button(self) -> None:
        """将运行/暂停合并按钮恢复到默认“运行”状态。"""
        self._set_play_pause_state("run")

    def _refresh_global_run_enabled(self) -> None:
        """根据连接状态与当前任务刷新运行按钮可用性。"""
        active = self._get_active_production_processor()
        if active is not None and hasattr(active, "isRunning") and active.isRunning():
            self.btn_play_pause.setEnabled(True)
        else:
            self.btn_play_pause.setEnabled(bool(self.driver.is_connected()))
        self._sync_play_pause_button_state()

    def _start_urscript_estimate_on_run(self, script_content: str, *, trace_id: str | None = None) -> None:
        """(Optional) Start URScript estimation + print timer when running."""
        if not bool(config_manager.get("ui.urscript_estimate_on_run", False)):
            return

        if not script_content or not script_content.strip():
            return

        try:
            self.status_widget.start_print_timer(0)
        except Exception:
            pass

        self._urscript_estimate_run_id += 1
        run_id = self._urscript_estimate_run_id
        self._urscript_estimate_active_run_id = run_id

        extruder_modbus_id = str(config_manager.get("printing.modbus_extruder", "MODBUS_1") or "MODBUS_1").strip()
        current_tcp_pose = getattr(self, "_last_tcp_pose", None)

        t = URScriptEstimateThread(
            run_id,
            script_content,
            current_tcp_pose=current_tcp_pose,
            extruder_modbus_id=extruder_modbus_id,
            trace_id=trace_id,
        )
        self._urscript_estimate_thread = t
        t.result_signal.connect(self._on_urscript_estimate_result)

        def _cleanup() -> None:
            if getattr(self, "_urscript_estimate_thread", None) is t:
                self._urscript_estimate_thread = None

        t.finished.connect(t.deleteLater)
        t.finished.connect(_cleanup)
        t.start()

    def _on_urscript_estimate_result(self, run_id: int, ok: bool, estimate: object, msg: str) -> None:
        if run_id != getattr(self, "_urscript_estimate_active_run_id", None):
            return

        if not ok or estimate is None:
            if msg:
                self.log(f"脚本估算失败: {msg}", "WARN")
            return

        try:
            total_s = int(round(float(getattr(estimate, "total_time_s", 0.0) or 0.0)))
        except Exception:
            total_s = 0

        try:
            self.status_widget.update_print_time(estimated_total_seconds=total_s)
        except Exception:
            pass

        try:
            cf_m = float(getattr(estimate, "cf_filament_mm", 0.0) or 0.0) / 1000.0
            ext_m = float(getattr(estimate, "extruder_filament_mm", 0.0) or 0.0) / 1000.0
            h = total_s // 3600
            m = (total_s % 3600) // 60
            s = total_s % 60
            self.log(f"[估算] 时间 {h:02d}:{m:02d}:{s:02d}，CF {cf_m:.3f}m，挤出 {ext_m:.3f}m", "INFO")
        except Exception:
            pass

    def _reset_urscript_estimate_run(self) -> None:
        if getattr(self, "_urscript_estimate_active_run_id", None) is None:
            return
        try:
            self.status_widget.reset_print_stats()
        except Exception:
            pass
        self._urscript_estimate_active_run_id = None

    def _save_current_script_for_run(self) -> str | None:
        """
        生产模式必须基于文件（SFTP 上传）。此函数确保当前编辑器内容已保存到真实文件，并返回路径。
        不弹出“是否加入队列”的提示，避免打断运行流程。
        """
        current_editor = self.get_current_editor()
        if current_editor is None or self.dockable_editor is None:
            return None

        script_content = current_editor.toPlainText()
        if not script_content.strip():
            StyledMessageBox.information(self, "空脚本", "编辑器内容为空，无法运行。")
            return None

        current_tab_index = self.dockable_editor.tabs.currentIndex()
        file_path = ""
        try:
            maybe_path = self.dockable_editor.tab_paths.get(current_tab_index, "")
            if maybe_path and os.path.isabs(str(maybe_path)):
                file_path = str(maybe_path)
        except Exception:
            file_path = ""

        default_save_path = ""
        if not file_path and hasattr(self, "project_widget") and getattr(self.project_widget, "current_project_path", ""):
            default_save_path = os.path.join(self.project_widget.current_project_path, "新脚本.script")

        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存脚本以运行（生产模式）",
                default_save_path,
                "URScript Files (*.script);;Text Files (*.txt);;All Files (*)",
            )

        if not file_path:
            return None

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            # 更新 tab 标题与路径映射
            file_name = os.path.basename(file_path)
            try:
                self.dockable_editor.tabs.setTabText(current_tab_index, file_name)
                self.dockable_editor.tab_paths[current_tab_index] = file_path
            except Exception:
                pass

            # 更新 editor 映射（移除旧的临时路径）
            try:
                old_paths_to_remove = []
                for path, editor in self.dockable_editor.editors.items():
                    if editor == current_editor and path != file_path:
                        old_paths_to_remove.append(path)
                for old_path in old_paths_to_remove:
                    if old_path in self.dockable_editor.editors:
                        del self.dockable_editor.editors[old_path]
                self.dockable_editor.editors[file_path] = current_editor
            except Exception:
                pass

            return file_path
        except Exception as e:
            self.log(f"保存失败: {e}", "ERROR")
            StyledMessageBox.critical(self, "错误", f"保存文件失败：\n{e}")
            return None

    def _start_single_run_production(self, script_path: str) -> None:
        """单文件生产运行：SFTP 双份上传 + Dashboard load loader.urp + play/pause/stop（CB3 友好）。"""
        if not os.path.isfile(script_path):
            StyledMessageBox.warning(self, "文件不存在", f"脚本文件不存在：\n{script_path}")
            return

        if self._get_active_production_processor() is not None:
            StyledMessageBox.information(self, "正在运行", "已有生产任务在运行中，请先停止/等待完成。")
            return

        ip = str(self.ip_combo.currentText() or "").strip()
        if not is_valid_ip(ip):
            StyledMessageBox.warning(self, "IP 无效", f"不是有效的 IP 地址：{ip}")
            return

        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()
        self._single_run_trace_id = trace_id
        with trace_context(trace_id):
            self.log(f"[运行] 单文件生产运行：{os.path.basename(script_path)}", "INFO")

        script_text = ""
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_text = f.read()
        except Exception:
            script_text = ""
        self._start_urscript_estimate_on_run(script_text, trace_id=trace_id)

        watchdog_enabled = self.chk_watchdog.isChecked() if self.chk_watchdog else True
        proc = ProductionProcessor(
            ip,
            SCRIPT_PORT,
            [script_path],
            do_index=DEFAULT_DO_INDEX,
            watchdog_enable=watchdog_enabled,
            trace_id=trace_id,
        )
        self._single_run_processor = proc

        # UI：锁定模式选择，显示上传进度；运行按钮进入“暂停”状态（允许暂停/继续）
        try:
            self.run_mode_combo.setEnabled(False)
        except Exception:
            pass
        self._set_play_pause_state("pause")

        proc.file_progress_signal.connect(self._on_single_run_file_progress)
        proc.error_signal.connect(lambda e: self._on_production_error(e, trace_id))
        proc.finished_signal.connect(self._on_single_run_finished)
        proc.start()

    def _on_single_run_file_progress(self, value: int) -> None:
        return

    def _on_single_run_finished(self) -> None:
        # 收尾：隐藏上传进度，释放引用，恢复按钮
        self._single_run_processor = None
        self._reset_urscript_estimate_run()

        try:
            self.run_mode_combo.setEnabled(True)
        except Exception:
            pass
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()

        from ur_print_fdm.shared.logging_context import trace_context

        trace_id = getattr(self, "_single_run_trace_id", None)
        if trace_id:
            with trace_context(trace_id):
                self.log("单文件生产任务结束。", "INFO")
        self._single_run_trace_id = None

    def run_current_script(self):
        # 获取当前活动的编辑器
        current_editor = self.get_current_editor()
        if current_editor is None:
            return

        # 如果已有生产任务在运行，避免叠加执行
        if self._get_active_production_processor() is not None:
            StyledMessageBox.information(self, "正在运行", "已有生产任务在运行中，请先停止/等待完成。")
            return

        if not self.driver.is_connected():
            StyledMessageBox.warning(self, "连接错误", "请先连接机器人（右上角 IP -> 连接）！")
            return

        # 选择运行模式；只读模式下自动回退到生产模式（CB3 友好）
        selected_mode = "production"
        try:
            selected_mode = str(self.run_mode_combo.currentData() or "production")
        except Exception:
            selected_mode = "production"

        if self.driver.is_read_only():
            selected_mode = "production"
            try:
                idx = self.run_mode_combo.findData("production")
                if idx >= 0:
                    self.run_mode_combo.setCurrentIndex(idx)
            except Exception:
                pass

        if selected_mode == "production":
            script_path = self._save_current_script_for_run()
            if not script_path:
                return
            self._start_single_run_production(script_path)
            return

        # 直连模式：使用 30002 端口直接发送脚本（不依赖 RTDE Control）
        script_content = current_editor.toPlainText()
        if not script_content.strip():
            StyledMessageBox.information(self, "空脚本", "编辑器内容为空，无法运行。")
            return

        if self._direct_mode_processor is not None and self._direct_mode_processor.isRunning():
            self.log("直连模式正在运行中，请稍候...")
            return

        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()
        with trace_context(trace_id):
            self.log("[运行] 正在发送当前脚本... (直连模式 - 30002端口)")

        self._start_urscript_estimate_on_run(script_content, trace_id=trace_id)

        self.btn_play_pause.setEnabled(False)

        # 使用 DirectModeProcessor 通过 30002 端口发送
        ip = self.driver.get_ip_address()
        self._direct_mode_processor = DirectModeProcessor(ip, script_content, trace_id=trace_id)
        self._direct_mode_processor.set_action_run(script_content)
        self._direct_mode_processor.log_signal.connect(lambda msg: self.log(msg))
        self._direct_mode_processor.script_sent_signal.connect(self._on_direct_mode_script_sent)
        self._direct_mode_processor.finished_signal.connect(self._on_direct_mode_finished)
        self._direct_mode_processor.error_signal.connect(lambda msg: self.log(msg, "ERROR"))
        self._direct_mode_processor.start()
    
    def stop_current_script(self):
        """停止当前任务：优先停止生产任务，直连模式使用 30002 端口停止。"""
        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()

        # 1. 检查生产模式处理器
        active = self._get_active_production_processor()
        if active is not None and active.isRunning():
            reply = StyledMessageBox.question(
                self,
                "停止生产",
                "确认停止当前生产任务？\n将发送 Dashboard stop，并尝试关闭挤出输出。",
            )
            if reply == StyledMessageBox.Yes:
                try:
                    if hasattr(active, "emergency_stop_action"):
                        active.emergency_stop_action()
                    else:
                        active.stop()
                    self._reset_global_pause_button()
                    self._reset_urscript_estimate_run()
                    with trace_context(trace_id):
                        self.log("[停止] 已请求停止（生产模式）。", "WARN")
                except Exception as e:
                    with trace_context(trace_id):
                        self.log(f"停止失败: {e}", "ERROR")
            return

        # 2. 检查当前运行模式
        selected_mode = "production"
        try:
            selected_mode = str(self.run_mode_combo.currentData() or "production")
        except Exception:
            selected_mode = "production"

        # 3. 直连模式：使用 30002 端口停止
        if selected_mode == "direct":
            self._stop_direct_mode()
            return

        # 4. 其他情况：使用原有的 StopThread（通过 driver.stop）
        if not self.driver.is_connected():
            self.log("未连接，无法发送停止指令。", "WARN")
            return

        if self.stop_thread is not None and self.stop_thread.isRunning():
            with trace_context(trace_id):
                self.log("停止指令正在执行中，请稍候...", "WARN")
            return

        self.btn_global_stop.setEnabled(False)  # 变灰，防止狂点
        self.stop_thread = StopThread(self.driver, trace_id=trace_id)
        self.stop_thread.finished_signal.connect(self.on_stop_finished)

        # 超时处理 - 如果 5 秒内没有完成，强制恢复按钮状态
        from PyQt6.QtCore import QTimer

        self.stop_timeout_timer = QTimer()
        self.stop_timeout_timer.setSingleShot(True)
        self.stop_timeout_timer.timeout.connect(self.on_stop_timeout)
        self.stop_timeout_timer.start(5000)

        self.stop_thread.finished.connect(self.stop_thread.deleteLater)
        self.stop_thread.finished.connect(lambda: setattr(self, "stop_thread", None))
        self.stop_thread.finished.connect(self.stop_timeout_timer.stop)
        self.stop_thread.start()

    def on_script_send_result(self, success, message):
        # 恢复按钮状态
        self._refresh_global_run_enabled()
        if not success:
            self._reset_urscript_estimate_run()
        # 注意：不要在这里清理script_thread，因为它会在finished信号中处理

    def on_stop_finished(self, msg):
        # 恢复按钮状态 + 写日志
        try:
            if msg:
                self.log(str(msg))
        except Exception:
            pass
        self.btn_global_stop.setEnabled(True)
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()
        self._reset_urscript_estimate_run()

    def on_stop_timeout(self):
        """停止操作超时处理"""
        self.log("停止操作超时，强制恢复按钮状态", "WARN")
        self.btn_global_stop.setEnabled(True)
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()
        # 如果线程还在运行，尝试优雅停止
        if hasattr(self, 'stop_thread') and self.stop_thread and self.stop_thread.isRunning():
            self.stop_thread.stop_gracefully()

    def _on_direct_mode_script_sent(self, success: bool, message: str):
        """直连模式脚本发送完成回调"""
        self._refresh_global_run_enabled()
        if success:
            self.log(f"[直连模式] {message}", "SUCCESS")
        else:
            self.log(f"[直连模式] {message}", "ERROR")
            self._reset_urscript_estimate_run()

    def _on_direct_mode_finished(self):
        """直连模式处理器完成回调"""
        if self._direct_mode_processor is not None:
            try:
                self._direct_mode_processor.deleteLater()
            except Exception:
                pass
            self._direct_mode_processor = None
        self._refresh_global_run_enabled()

    def _on_direct_mode_stop_completed(self, success: bool, message: str):
        """直连模式停止完成回调"""
        self.btn_global_stop.setEnabled(True)
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()
        self._reset_urscript_estimate_run()
        if success:
            self.log(f"[直连模式] {message}", "SUCCESS")
        else:
            self.log(f"[直连模式] {message}", "WARN")

    def _stop_direct_mode(self):
        """直连模式停止：通过 30002 端口发送 stopj"""
        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()

        if not self.driver.is_connected():
            self.log("未连接，无法发送停止指令。", "WARN")
            return

        with trace_context(trace_id):
            self.log("[停止] 正在发送停止指令... (直连模式 - 30002端口)")

        self.btn_global_stop.setEnabled(False)

        ip = self.driver.get_ip_address()
        stop_processor = DirectModeProcessor(ip, trace_id=trace_id)
        stop_processor.set_action_stop()
        stop_processor.connect_monitor()  # 连接 RTDE 用于检测停止状态
        stop_processor.log_signal.connect(lambda msg: self.log(msg))
        stop_processor.stop_completed_signal.connect(self._on_direct_mode_stop_completed)
        stop_processor.finished_signal.connect(stop_processor.deleteLater)
        stop_processor.start()

        # 保存引用以便后续清理
        self._direct_mode_stop_processor = stop_processor

    def toggle_monitor(self):
        if not self.driver.is_connected():
            # 从组合框获取当前文本（用户可能输入了新IP）
            ip = self.ip_combo.currentText()

            # 验证IP地址
            if not is_valid_ip(ip):
                StyledMessageBox.critical(self, "IP地址错误", f"无效的IP地址格式：{ip}\n请输入有效的IP地址（例如：192.168.1.100）")
                return

            # self.log(f"⏳ 正在连接到 {ip} ... (界面不会卡死)")
            self.btn_connect_action.setEnabled(False)

            # 修正点 3: 检查旧线程是否存活，防止多重点击
            if self.conn_thread is not None and self.conn_thread.isRunning():
                return

            from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

            trace_id = new_trace_id()
            with trace_context(trace_id):
                self.log(f"⏳ 正在连接到 {ip} ...", "INFO")

            # 启动连接线程（日志将自动进入文件+UI）
            self.conn_thread = ConnectionThread(self.driver, ip, trace_id=trace_id)

            self.conn_thread.result_signal.connect(self.on_connect_result)
            # 修正点 4: 线程结束后自动销毁，防止内存泄漏和信号累积
            self.conn_thread.finished.connect(self.conn_thread.deleteLater)
            # 添加finished信号连接，确保conn_thread引用被清理
            self.conn_thread.finished.connect(lambda: setattr(self, 'conn_thread', None))
            self.conn_thread.start()
        else:
            # 断开连接
            # 修正点 5: 使用 requestInterruption 安全停止
            if self.monitor_thread.isRunning():
                self.monitor_thread.requestInterruption()
                self.monitor_thread.wait() # 这里必须等待，否则断开连接会导致 monitor 报错
            self.driver.disconnect()
            self.log("[连接] 已断开")
            # --- 修复 3: 使用新的状态指示器更新 UI ---
            self._update_status_indicator("disconnected")

            # 安全检查：只有当标定面板已实例化时才重置它的显示
            if hasattr(self, 'calib_widget') and self.calib_widget:
                self.calib_widget.manual_widget.lbl_tcp_pos.setText("未连接")

    def save_current_script(self):
        """保存当前编辑器内容到文件"""
        # 获取当前活动的编辑器
        current_editor = self.get_current_editor()
        if current_editor is None:
            return

        script_content = current_editor.toPlainText()
        if not script_content.strip():
            StyledMessageBox.warning(self, "警告", "编辑器内容为空，无法保存。")
            return

        # 获取当前标签页索引
        current_tab_index = self.dockable_editor.tabs.currentIndex()

        # 检查是否已经有对应的文件路径
        file_path = ""
        if current_tab_index in self.dockable_editor.tab_paths:
            file_path = self.dockable_editor.tab_paths[current_tab_index]
            # 如果路径为空字符串或者不是有效的文件路径，则弹出保存对话框
            if not file_path or file_path == "" or not os.path.isabs(file_path):
                file_path = ""

        # 如果没有当前文件路径，使用项目浏览器的路径作为默认路径
        if not file_path and hasattr(self, 'project_widget') and self.project_widget.current_project_path:
            # 使用项目路径作为默认保存路径
            default_save_path = os.path.join(self.project_widget.current_project_path, "新脚本.script")
        else:
            default_save_path = ""

        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存脚本",
                default_save_path if default_save_path else "",
                "URScript Files (*.script);;Text Files (*.txt);;All Files (*)"
            )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)

                # 如果这是新保存的文件，更新标签页标题为文件名
                file_name = os.path.basename(file_path)

                # 更新标签页标题
                self.dockable_editor.tabs.setTabText(current_tab_index, file_name)

                # 更新标签路径映射
                self.dockable_editor.tab_paths[current_tab_index] = file_path

                # 更新编辑器映射
                # 删除旧的路径映射（如果是新保存的文件）
                old_paths_to_remove = []
                for path, editor in self.dockable_editor.editors.items():
                    if editor == current_editor and path != file_path:
                        old_paths_to_remove.append(path)

                for old_path in old_paths_to_remove:
                    if old_path in self.dockable_editor.editors:
                        del self.dockable_editor.editors[old_path]

                self.dockable_editor.editors[file_path] = current_editor

                self.log(f"已保存脚本到: {file_path}", "SUCCESS")

                # 如果文件不在队列中，询问是否添加到队列
                if self.queue_list and not any(self.queue_list.item(i).text() == file_path for i in range(self.queue_list.count())):
                    reply = StyledMessageBox.question(
                        self, "添加到队列",
                        "是否将保存的文件添加到生产队列？"
                    )
                    if reply == StyledMessageBox.Yes:
                        self.queue_list.addItem(file_path)
                        self.log(f"已添加到队列: {file_path}")

            except Exception as e:
                self.log(f"保存失败: {e}", "ERROR")
                StyledMessageBox.critical(self, "错误", f"保存文件失败：\n{e}")
    def on_connect_result(self, success, msg):
        self.btn_connect_action.setEnabled(True)
        if success:
            self.btn_connect_action.setText("断开")
            # 连接成功后，启动监控线程
            if not self.monitor_thread.isRunning():
                # 如果线程之前被终止过，需要重新创建实例
                if not self.monitor_thread.isFinished():
                    self.monitor_thread.quit()
                    self.monitor_thread.wait()
                self.monitor_thread = MonitorThread(self.driver)  # 重新创建线程实例
                self.monitor_thread.status_signal.connect(self.on_robot_status_update)
                self.monitor_thread.start()
        else:
            StyledMessageBox.warning(self, "连接错误", msg)
        
        # 清理conn_thread引用以避免访问已删除对象
        self.conn_thread = None

    # --- 2. 队列管理逻辑 ---
    def queue_add(self):
        if self.queue_list is None:
            self.log("队列未初始化", "WARN")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "添加脚本", "", "URScript (*.script *.txt);;All (*.*)")
        if files:
            for f in files:
                self.queue_list.addItem(f)
            self.log(f"添加 {len(files)} 个文件。")

    def queue_remove(self):
        if self.queue_list is None:
            return
        for item in self.queue_list.selectedItems():
            self.queue_list.takeItem(self.queue_list.row(item))

    def save_selected_script(self):
        """保存当前编辑器内容到选中的队列项"""
        if self.queue_list is None:
            self.log("队列未初始化", "WARN")
            return
        selected_items = self.queue_list.selectedItems()
        if not selected_items:
            StyledMessageBox.warning(self, "警告", "请先选择要保存的文件！")
            return
        
        if len(selected_items) > 1:
            StyledMessageBox.warning(self, "警告", "只能同时保存一个文件！")
            return
            
        selected_item = selected_items[0]
        file_path = selected_item.text()
        
        # 确认是否覆盖
        reply = StyledMessageBox.question(self, "确认保存", f"是否保存到文件？\n{file_path}")
        if reply == StyledMessageBox.Yes:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.dockable_editor.current_text())
                self.log(f"已保存到文件: {file_path}")
            except Exception as e:
                self.log(f"保存文件失败: {e}")
                StyledMessageBox.critical(self, "错误", f"保存文件失败：\n{e}")
    def on_queue_item_double_clicked(self, item):
        """双击队列中的项目，在编辑器中打开文件"""
        file_path = item.text()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            self.dockable_editor.set_current_text(script_content)
            self.log(f"已加载文件: {file_path}")
        except Exception as e:
            self.log(f"加载文件失败: {e}")
    # --- 3. 生产引擎逻辑 ---
    def start_production(self):
        if self.queue_list is None or self.queue_list.count() == 0:
            StyledMessageBox.warning(self, "提示", "队列为空")
            return
        
        # 修复：使用 self.ip_combo 替代 self.ip_input
        ip = self.ip_combo.currentText()
        scripts = [self.queue_list.item(i).text() for i in range(self.queue_list.count())]

        from ur_print_fdm.shared.logging_context import new_trace_id, trace_context

        trace_id = new_trace_id()
        self._active_production_trace_id = trace_id
        with trace_context(trace_id):
            self.log(f"[生产] 开始生产队列：{len(scripts)} 个脚本", "INFO")

        # 实例化引擎
        watchdog_enabled = self.chk_watchdog.isChecked() if self.chk_watchdog else True
        self.processor = ProductionProcessor(ip, SCRIPT_PORT, scripts, do_index=DEFAULT_DO_INDEX,
                                             watchdog_enable=watchdog_enabled, trace_id=trace_id)
        
        # 信号绑定
        self.processor.progress_signal.connect(lambda c, t: (self.prog_batch.setMaximum(t), self.prog_batch.setValue(c)))
        self.processor.finished_signal.connect(self.on_prod_finished)
        self.processor.error_signal.connect(lambda e: self._on_production_error(e, trace_id))
        self.processor.file_progress_signal.connect(self._on_single_run_file_progress)
        
        # UI 锁定
        if self.btn_start_batch:
            self.btn_start_batch.setEnabled(False)
        if self.btn_stop_batch:
            self.btn_stop_batch.setEnabled(True)
        if self.queue_list:
            self.queue_list.setEnabled(False)

        try:
            self.run_mode_combo.setEnabled(False)
        except Exception:
            pass
        self._set_play_pause_state("pause")

        self.processor.start()

    def on_prod_finished(self):
        if self.btn_start_batch:
            self.btn_start_batch.setEnabled(True)
        if self.btn_stop_batch:
            self.btn_stop_batch.setEnabled(False)
        if self.queue_list:
            self.queue_list.setEnabled(True)
        from ur_print_fdm.shared.logging_context import trace_context

        trace_id = getattr(self, "_active_production_trace_id", None)
        if trace_id:
            with trace_context(trace_id):
                self.log("生产任务结束")
            self._active_production_trace_id = None
        else:
            self.log("生产任务结束")
        try:
            self.run_mode_combo.setEnabled(True)
        except Exception:
            pass
        self._reset_global_pause_button()
        self._refresh_global_run_enabled()
    def stop_production(self):
        if self.processor and self.processor.isRunning():
            reply = StyledMessageBox.question(self, "急停", "确定要立即停止？")
            if reply == StyledMessageBox.Yes:
                self.processor.emergency_stop_action()
                self._reset_global_pause_button()
    def tool_gcode_convert(self):
        if self.tools_controller is None:
            self.tools_controller = ToolsController(self, self.dockable_editor, self.log)
        self.tools_controller.tool_gcode_convert()

    def tool_split_script(self):
        if self.tools_controller is None:
            self.tools_controller = ToolsController(self, self.dockable_editor, self.log)
        self.tools_controller.tool_split_script()
    def tool_insert_flag(self):
        if self.tools_controller is None:
            self.tools_controller = ToolsController(self, self.dockable_editor, self.log)
        self.tools_controller.tool_insert_flag()

    def tool_script_estimate(self):
        if self.tools_controller is None:
            self.tools_controller = ToolsController(self, self.dockable_editor, self.log)
        self.tools_controller.tool_script_estimate()

    def tool_script_estimate_from_path(self, file_path: str) -> None:
        if self.tools_controller is None:
            self.tools_controller = ToolsController(self, self.dockable_editor, self.log)
        self.tools_controller.tool_script_estimate(file_path)
     
    def closeEvent(self, event):
        # 1. 停止监控线程
        if self.monitor_thread.isRunning():
            self.monitor_thread.requestInterruption()
            self.monitor_thread.wait(1000)

        # 2. 如果正在连接中，也要停止
        if self.conn_thread and self.conn_thread.isRunning():
            self.conn_thread.quit()
            self.conn_thread.wait(1000)

        # 3. 停止生产流程
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)

        # 4. 断开底层驱动
        if self.driver.is_connected():
            self.driver.disconnect()

        # 5. 保存编辑器会话（记住打开的文件）
        if self.dockable_editor:
            self.dockable_editor.save_session()

        # 6. 保存配置
        current_ip = self.ip_combo.currentText()
        ip_list = [self.ip_combo.itemText(i) for i in range(self.ip_combo.count())]
        if current_ip not in ip_list:
            ip_list.append(current_ip)

        config_manager.set("robot.ip_addresses", ip_list)
        config_manager.set("robot.default_ip", current_ip)
        config_manager.set("robot.auto_reconnect", self.chk_auto_reconnect.isChecked())
        config_manager.set("ui.window_size", [self.width(), self.height()])
        config_manager.save_config()

        event.accept()
