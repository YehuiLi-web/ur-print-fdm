"""
可折叠状态监控栏组件
实现了垂直侧边栏结构，包含多个可折叠的逻辑块

主要功能区块：
1. 打印统计 - 进度、时间、层数
2. 温度监控 - 喷头温度、热床温度
3. 打印参数 - 打印速度、挤出机速度、流量
4. 运动状态 - TCP速度、机器人状态
5. 关节角度 - J1-J6 关节角
6. TCP 位姿 - 工具中心点位置/姿态
7. TCP 偏移 - 工具偏移量
"""
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel,
                             QScrollArea, QGroupBox, QToolButton, QFrame, QApplication,
                             QProgressBar, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer
from PyQt6.QtGui import QIcon, QFont
from ur_print_fdm.config import config_manager
from ur_print_fdm.ui.resources.icon_manager import IconManager
from ur_print_fdm.ui import theme as ui_theme


def _themed_qss(qss: str) -> str:
    """Replace common hard-coded dark palette colors with current theme tokens.

    This keeps legacy widget-local QSS readable while enabling light/dark switching.
    """
    if not qss:
        return qss

    t = ui_theme.current_tokens()

    sources_to_token = {
        # Surfaces
        "bg_secondary": ["#1e1e1e", "#262628", ui_theme.DARK["bg_secondary"], ui_theme.LIGHT["bg_secondary"]],
        "bg_tertiary": ["#252526", "#2d2d30", ui_theme.DARK["bg_tertiary"], ui_theme.LIGHT["bg_tertiary"]],
        "bg_panel": ["#2d2d2d", "#353538", ui_theme.DARK["bg_panel"], ui_theme.LIGHT["bg_panel"]],
        "bg_hover": ["#2a2a2a", "#2a2a2c", "#2a2a2e", "#3a3a3c", ui_theme.DARK["bg_hover"], ui_theme.LIGHT["bg_hover"]],
        "bg_hover_strong": ["#383838", "#3c3c3e", ui_theme.DARK["bg_hover_strong"], ui_theme.LIGHT["bg_hover_strong"]],
        # Borders
        "border": ["#3a3a3e", "#323234", ui_theme.DARK["border"], ui_theme.LIGHT["border"]],
        "border_light": ["#404044", "#48484a", "#38383c", ui_theme.DARK["border_light"], ui_theme.LIGHT["border_light"]],
        # Text
        "text": ["#e4e4e6", "#e6e6e8", "#cccccc", "#d4d4d4", ui_theme.DARK["text"], ui_theme.LIGHT["text"]],
        "text_muted": ["#8e8e92", "#8a8a8c", "#8a8a8a", ui_theme.DARK["text_muted"], ui_theme.LIGHT["text_muted"]],
        "text_dim": ["#6e6e72", "#6e6e6e", "#5a5a5c", ui_theme.DARK["text_dim"], ui_theme.LIGHT["text_dim"]],
        # Accents
        "accent_blue": ["#4FC3F7", "#007ACC", ui_theme.DARK["accent_blue"], ui_theme.LIGHT["accent_blue"]],
        "accent_link": ["#569CD6", ui_theme.DARK["accent_link"], ui_theme.LIGHT["accent_link"]],
    }

    for token_key, sources in sources_to_token.items():
        dst = str(t.get(token_key, ""))
        if not dst:
            continue
        for src in sources:
            qss = re.sub(re.escape(str(src)), dst, qss, flags=re.IGNORECASE)

    return qss


class CollapsibleBox(QGroupBox):
    """可折叠面板组件"""
    toggled = pyqtSignal(bool)  # 折叠状态改变信号

    def __init__(self, title="", parent=None, state_key=None, default_collapsed=False):
        super().__init__(title, parent)
        self.state_key = state_key  # 用于状态记忆的键
        self.default_collapsed = default_collapsed

        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 创建标题栏
        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        self._title_bar_styles = {
            "expanded": """
                QWidget#title_bar {
                    background-color: #2d2d30;
                    border-radius: 6px 6px 0 0;
                    border: 1px solid #3a3a3e;
                    border-bottom: 1px solid #323234;
                }
            """,
            "collapsed": """
                QWidget#title_bar {
                    background-color: #2d2d30;
                    border-radius: 6px;
                    border: 1px solid #3a3a3e;
                }
            """,
        }
        self.title_bar.setStyleSheet(self._title_bar_styles["expanded"])
        self.title_bar.setCursor(Qt.CursorShape.PointingHandCursor)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 6, 8, 6)
        title_layout.setSpacing(8)

        # 箭头按钮
        self.toggle_button = QToolButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_button.setFixedSize(18, 18)
        self.toggle_button.setStyleSheet("""
            QToolButton {
                background-color: #353538;
                border: 1px solid #404044;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3c3c3e;
                border-color: #48484a;
            }
            QToolButton:checked {
                background-color: #3a3a3c;
            }
        """)
        self.toggle_button.toggled.connect(self.toggle_content)
        self.toggle_button.setToolTip("点击展开或折叠")

        # 标题标签
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #e4e4e6; font-weight: 600; font-size: 10pt; "
            "letter-spacing: 0.2px; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )

        title_layout.addWidget(self.toggle_button)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # 内容区域
        self.content_area = QFrame()
        self.content_area.setObjectName("content_area")
        self.content_area.setStyleSheet("""
            QFrame#content_area {
                background-color: #262628;
                border: 1px solid #3a3a3e;
                border-top: none;
                border-radius: 0 0 6px 6px;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(8, 8, 8, 10)

        # 将标题栏和内容区域添加到主布局
        self.layout.addWidget(self.title_bar)
        self.layout.addWidget(self.content_area)

        # 加载上次保存的折叠状态
        if self.state_key:
            self.load_state()

    def toggle_content(self, checked):
        """切换内容区域的显示/隐藏（带平滑动画）"""
        self.title_bar.setStyleSheet(
            self._title_bar_styles["collapsed"] if checked else self._title_bar_styles["expanded"]
        )
        arrow_type = Qt.ArrowType.RightArrow if checked else Qt.ArrowType.DownArrow
        self.toggle_button.setArrowType(arrow_type)
        
        # 简单的显示/隐藏（PyQt6中复杂动画可能导致布局问题）
        self.content_area.setVisible(not checked)
        
        self.toggled.emit(not checked)

        # 保存状态
        if self.state_key:
            self.save_state(checked)

    def set_collapsed(self, collapsed):
        """设置折叠状态"""
        self.toggle_button.setChecked(collapsed)
        self.toggle_content(collapsed)

    def add_widget(self, widget):
        """向内容区域添加组件"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """向内容区域添加布局"""
        self.content_layout.addLayout(layout)

    def save_state(self, collapsed):
        """保存当前折叠状态"""
        try:
            config_manager.set(f"ui.panels.{self.state_key}", bool(collapsed))
            config_manager.save_config()
        except Exception as e:
            print(f"保存状态配置失败: {e}")

    def load_state(self):
        """加载上次的折叠状态，无保存值时使用 default_collapsed"""
        try:
            collapsed = config_manager.get(f"ui.panels.{self.state_key}")
            if collapsed is not None:
                self.set_collapsed(bool(collapsed))
            else:
                self.set_collapsed(self.default_collapsed)
        except Exception as e:
            print(f"加载状态配置失败: {e}")


class StatusValueWidget(QWidget):
    """状态值显示组件 - 用于显示标签+数值+单位的组合"""
    
    def __init__(self, label: str, value: str = "--", unit: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)
        
        # 标签
        self.lbl_name = QLabel(label)
        self.lbl_name.setStyleSheet(
            "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        self.lbl_name.setFixedWidth(70)
        layout.addWidget(self.lbl_name)
        
        # 数值（右对齐）
        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet(
            "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 10pt; font-weight: 600;"
        )
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.lbl_value, 1)
        
        # 单位
        if unit:
            self.lbl_unit = QLabel(unit)
            self.lbl_unit.setStyleSheet(
                "color: #6e6e72; font-size: 8.5pt; font-family: 'Segoe UI', sans-serif;"
            )
            self.lbl_unit.setFixedWidth(32)
            layout.addWidget(self.lbl_unit)
        else:
            self.lbl_unit = None
    
    def set_value(self, value: str):
        """设置显示的数值"""
        self.lbl_value.setText(value)
    
    def set_highlight(self, highlight: bool, color: str = "#4FC3F7"):
        """设置高亮状态"""
        if highlight:
            self.lbl_value.setStyleSheet(
                f"color: {color}; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                "font-size: 10pt; font-weight: 600;"
            )
        else:
            self.lbl_value.setStyleSheet(
                "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                "font-size: 10pt; font-weight: 600;"
            )


class TemperatureWidget(QWidget):
    """温度显示组件 - 显示当前温度/目标温度，带进度条"""
    
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self._current = 0.0
        self._target = 0.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # 上半部分：标签 + 温度值
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        self.lbl_name = QLabel(label)
        self.lbl_name.setStyleSheet(
            "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        top_layout.addWidget(self.lbl_name)
        
        top_layout.addStretch()
        
        # 当前温度
        self.lbl_current = QLabel("--")
        self.lbl_current.setStyleSheet(
            "color: #FF8A65; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 11pt; font-weight: bold;"
        )
        top_layout.addWidget(self.lbl_current)
        
        # 分隔符
        self.lbl_sep = QLabel("/")
        self.lbl_sep.setStyleSheet("color: #6e6e72; font-size: 9pt;")
        top_layout.addWidget(self.lbl_sep)
        
        # 目标温度
        self.lbl_target = QLabel("--")
        self.lbl_target.setStyleSheet(
            "color: #81C784; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 10pt;"
        )
        top_layout.addWidget(self.lbl_target)
        
        # 单位
        lbl_unit = QLabel("°C")
        lbl_unit.setStyleSheet("color: #6e6e72; font-size: 8.5pt;")
        top_layout.addWidget(lbl_unit)
        
        layout.addLayout(top_layout)
        
        # 下半部分：进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #363638;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #FF8A65, stop:1 #FFAB91);
            }
        """)
        layout.addWidget(self.progress)
    
    def set_temperature(self, current: float, target: float = None):
        """设置温度值"""
        self._current = current
        self.lbl_current.setText(f"{current:.1f}")
        
        if target is not None:
            self._target = target
            self.lbl_target.setText(f"{target:.0f}")
            # 计算进度
            if target > 0:
                progress = min(100, int(current / target * 100))
                self.progress.setValue(progress)
                
                # 根据温度接近程度改变颜色
                if abs(current - target) <= 2:  # 达到目标温度（±2°C）
                    self.lbl_current.setStyleSheet(
                        "color: #81C784; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                        "font-size: 11pt; font-weight: bold;"
                    )
                    self.progress.setStyleSheet("""
                        QProgressBar {
                            border: none;
                            border-radius: 3px;
                            background-color: #363638;
                        }
                        QProgressBar::chunk {
                            border-radius: 3px;
                            background: #81C784;
                        }
                    """)
                else:  # 加热中
                    self.lbl_current.setStyleSheet(
                        "color: #FF8A65; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                        "font-size: 11pt; font-weight: bold;"
                    )
                    self.progress.setStyleSheet("""
                        QProgressBar {
                            border: none;
                            border-radius: 3px;
                            background-color: #363638;
                        }
                        QProgressBar::chunk {
                            border-radius: 3px;
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #FF8A65, stop:1 #FFAB91);
                        }
                    """)
            else:
                self.progress.setValue(0)
        else:
            self.lbl_target.setText("--")
            self.progress.setValue(0)


class StatusWidget(QWidget):
    """优化后的状态监控组件，使用可折叠面板设计
    
    包含以下面板：
    1. 打印统计 - 进度、时间、层数
    2. 温度监控 - 喷头温度、热床温度
    3. 打印参数 - 打印速度、挤出机速度、流量
    4. 运动状态 - TCP速度、机器人状态
    5. 关节角度 - J1-J6 关节角
    6. TCP 位姿 - 工具中心点位置/姿态
    7. TCP 偏移 - 工具偏移量
    """

    def __init__(self):
        super().__init__()
        self.joint_widgets = []  # 存储关节控件引用
        self.tcp_widgets = []    # 存储TCP控件引用
        self.offset_widgets = [] # 存储偏移控件引用
        
        # 打印计时器
        self._print_start_time = None
        self._print_timer = QTimer()
        self._print_timer.timeout.connect(self._update_print_time)
        self._elapsed_seconds = 0
        self._estimated_total_seconds = 0
        
        self._init_ui()
        self.apply_theme()

    def apply_theme(self) -> None:
        """Apply current UI theme to widget-local stylesheets."""
        # Convert existing (legacy) hard-coded colors to the active theme palette.
        for w in [self, *self.findChildren(QWidget)]:
            ss = w.styleSheet()
            if ss:
                w.setStyleSheet(_themed_qss(ss))

    def _init_ui(self):
        """初始化用户界面"""
        self.setObjectName("status_monitor_widget")
        # 垂直列表布局：面板可以更窄，每行只有一个数值
        self.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(0)

        # 连接/数据流状态指示器
        self.data_status_row = QWidget()
        data_status_layout = QHBoxLayout(self.data_status_row)
        data_status_layout.setContentsMargins(0, 0, 0, 6)
        data_status_layout.setSpacing(8)
        self.data_status_dot = QLabel()
        self.data_status_dot.setFixedSize(8, 8)
        self.data_status_dot.setStyleSheet(
            "background-color: #5a5a5c; border-radius: 4px;"
        )
        self.data_status_dot.setToolTip("数据流: 未连接")
        self.data_status_label = QLabel("未连接")
        self.data_status_label.setStyleSheet(
            "color: #8a8a8c; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        data_status_layout.addWidget(self.data_status_dot)
        data_status_layout.addWidget(self.data_status_label)
        data_status_layout.addStretch()
        
        # 机器人状态标签
        self.lbl_robot_state = QLabel("空闲")
        self.lbl_robot_state.setStyleSheet(
            "color: #81C784; font-size: 9pt; font-weight: 500; padding: 2px 8px; "
            "background-color: #2d3d2d; border-radius: 4px;"
        )
        data_status_layout.addWidget(self.lbl_robot_state)
        
        layout.addWidget(self.data_status_row)

        # 创建滚动区域以支持更多内容
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QScrollBar:vertical {
                width: 8px;
                border: none;
                border-radius: 4px;
                background: #2a2a2c;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                min-height: 24px;
                border-radius: 4px;
                background: #4a4a4c;
            }
            QScrollBar::handle:vertical:hover { background: #5a5a5c; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal {
                height: 6px;
                border: none;
                border-radius: 3px;
                background: #2a2a2c;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                min-width: 24px;
                border-radius: 3px;
                background: #4a4a4c;
            }
            QScrollBar::handle:horizontal:hover { background: #5a5a5c; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)

        # 滚动内容容器
        scroll_content = QWidget()
        scroll_content.setObjectName("status_scroll_content")
        scroll_content.setStyleSheet("QWidget#status_scroll_content { background-color: transparent; }")
        scroll_content.setMinimumWidth(220)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 2, 0, 0)
        scroll_layout.setSpacing(8)

        # ============================================================
        # 1. 打印统计面板 (Print Statistics) - 最重要，放在最上面
        # ============================================================
        self.print_stats_box = CollapsibleBox("打印统计", state_key="print_stats_collapsed")
        self.print_stats_box.title_label.setToolTip("当前打印任务的进度、时间和层数信息")
        self._create_print_stats_content()
        scroll_layout.addWidget(self.print_stats_box)

        # ============================================================
        # 2. 温度监控面板 (Temperature)
        # ============================================================
        self.temperature_box = CollapsibleBox("温度监控", state_key="temperature_collapsed")
        self.temperature_box.title_label.setToolTip("喷头和热床温度监控")
        self._create_temperature_content()
        scroll_layout.addWidget(self.temperature_box)

        # ============================================================
        # 3. 打印参数面板 (Print Parameters)
        # ============================================================
        self.print_params_box = CollapsibleBox("打印参数", state_key="print_params_collapsed")
        self.print_params_box.title_label.setToolTip("当前打印速度、挤出机速度和流量参数")
        self._create_print_params_content()
        scroll_layout.addWidget(self.print_params_box)

        # ============================================================
        # 4. 运动状态面板 (Motion Status)
        # ============================================================
        self.motion_box = CollapsibleBox("运动状态", state_key="motion_collapsed")
        self.motion_box.title_label.setToolTip("TCP速度和运动状态")
        self._create_motion_status_content()
        scroll_layout.addWidget(self.motion_box)

        # ============================================================
        # 5. 关节角度面板 (Robot Joints)
        # ============================================================
        self.joint_status_box = CollapsibleBox("关节角度 (Joints)", state_key="joint_panel_collapsed")
        self.joint_status_box.title_label.setToolTip("J1–J6 关节角 (°)，滑块表示角度在 ±360° 范围内的位置")
        self._create_joint_status_content()
        scroll_layout.addWidget(self.joint_status_box)

        # ============================================================
        # 6. TCP位姿面板 (TCP Pose)
        # ============================================================
        self.tcp_status_box = CollapsibleBox("TCP 位姿 (Base)", state_key="tcp_panel_collapsed")
        self.tcp_status_box.title_label.setToolTip("工具中心点在基坐标系下的位姿：X/Y/Z (mm)，Rx/Ry/Rz (°)")
        self._create_tcp_status_content()
        scroll_layout.addWidget(self.tcp_status_box)

        # ============================================================
        # 7. TCP偏移面板（默认折叠）
        # ============================================================
        self.offset_status_box = CollapsibleBox(
            "TCP 偏移 (Offset)", state_key="offset_panel_collapsed", default_collapsed=True
        )
        self.offset_status_box.title_label.setToolTip("TCP 相对法兰的偏移：位置 (mm)、姿态 (°)")
        self._create_offset_status_content()
        scroll_layout.addWidget(self.offset_status_box)

        # 添加弹簧，使面板靠上排列
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # 设置样式
        self._setup_styles()

    # ============================================================
    # 打印统计面板
    # ============================================================
    def _create_print_stats_content(self):
        """创建打印统计面板内容"""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        # 进度条（大号，醒目）
        progress_container = QFrame()
        progress_container.setObjectName("progress_container")
        progress_container.setStyleSheet("""
            QFrame#progress_container {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(10, 8, 10, 8)
        progress_layout.setSpacing(4)
        
        # 进度百分比标签
        progress_header = QHBoxLayout()
        self.lbl_progress_text = QLabel("打印进度")
        self.lbl_progress_text.setStyleSheet(
            "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        progress_header.addWidget(self.lbl_progress_text)
        progress_header.addStretch()
        
        self.lbl_progress_percent = QLabel("0%")
        self.lbl_progress_percent.setStyleSheet(
            "color: #4FC3F7; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 14pt; font-weight: bold;"
        )
        progress_header.addWidget(self.lbl_progress_percent)
        progress_layout.addLayout(progress_header)
        
        # 进度条
        self.print_progress_bar = QProgressBar()
        self.print_progress_bar.setRange(0, 100)
        self.print_progress_bar.setValue(0)
        self.print_progress_bar.setFixedHeight(10)
        self.print_progress_bar.setTextVisible(False)
        self.print_progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #363638;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4FC3F7, stop:1 #29B6F6);
            }
        """)
        progress_layout.addWidget(self.print_progress_bar)
        
        layout.addWidget(progress_container)
        
        # 时间信息区块
        time_frame = QFrame()
        time_frame.setObjectName("time_frame")
        time_frame.setStyleSheet("""
            QFrame#time_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        time_layout = QVBoxLayout(time_frame)
        time_layout.setContentsMargins(10, 8, 10, 8)
        time_layout.setSpacing(4)
        
        # 打印时间
        self.print_time_widget = StatusValueWidget("已打印", "--:--:--", "")
        self.print_time_widget.lbl_value.setStyleSheet(
            "color: #81C784; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 11pt; font-weight: 600;"
        )
        time_layout.addWidget(self.print_time_widget)
        
        # 剩余时间
        self.remaining_time_widget = StatusValueWidget("剩余时间", "--:--:--", "")
        self.remaining_time_widget.lbl_value.setStyleSheet(
            "color: #FFB74D; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 11pt; font-weight: 600;"
        )
        time_layout.addWidget(self.remaining_time_widget)
        
        # 预计完成
        self.eta_widget = StatusValueWidget("预计完成", "--:--", "")
        time_layout.addWidget(self.eta_widget)
        
        layout.addWidget(time_frame)
        
        # 层数信息
        layer_frame = QFrame()
        layer_frame.setObjectName("layer_frame")
        layer_frame.setStyleSheet("""
            QFrame#layer_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        layer_layout = QHBoxLayout(layer_frame)
        layer_layout.setContentsMargins(10, 8, 10, 8)
        
        # 当前层
        layer_left = QVBoxLayout()
        lbl_current_layer_title = QLabel("当前层")
        lbl_current_layer_title.setStyleSheet(
            "color: #6e6e72; font-size: 8.5pt; font-family: 'Segoe UI', sans-serif;"
        )
        lbl_current_layer_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_left.addWidget(lbl_current_layer_title)
        
        self.lbl_current_layer = QLabel("0")
        self.lbl_current_layer.setStyleSheet(
            "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 16pt; font-weight: bold;"
        )
        self.lbl_current_layer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_left.addWidget(self.lbl_current_layer)
        layer_layout.addLayout(layer_left)
        
        # 分隔符
        lbl_sep = QLabel("/")
        lbl_sep.setStyleSheet("color: #6e6e72; font-size: 14pt;")
        lbl_sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_layout.addWidget(lbl_sep)
        
        # 总层数
        layer_right = QVBoxLayout()
        lbl_total_layer_title = QLabel("总层数")
        lbl_total_layer_title.setStyleSheet(
            "color: #6e6e72; font-size: 8.5pt; font-family: 'Segoe UI', sans-serif;"
        )
        lbl_total_layer_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_right.addWidget(lbl_total_layer_title)
        
        self.lbl_total_layers = QLabel("--")
        self.lbl_total_layers.setStyleSheet(
            "color: #8e8e92; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 16pt;"
        )
        self.lbl_total_layers.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layer_right.addWidget(self.lbl_total_layers)
        layer_layout.addLayout(layer_right)
        
        layout.addWidget(layer_frame)
        
        self.print_stats_box.add_layout(layout)

    # ============================================================
    # 温度监控面板
    # ============================================================
    def _create_temperature_content(self):
        """创建温度监控面板内容"""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        # 喷头温度
        self.nozzle_temp_widget = TemperatureWidget("喷头温度")
        layout.addWidget(self.nozzle_temp_widget)
        
        # 热床温度（可选，FDM打印机可能有）
        self.bed_temp_widget = TemperatureWidget("热床温度")
        layout.addWidget(self.bed_temp_widget)
        
        # 环境温度（可选）
        env_frame = QFrame()
        env_frame.setObjectName("env_frame")
        env_frame.setStyleSheet("""
            QFrame#env_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        env_layout = QHBoxLayout(env_frame)
        env_layout.setContentsMargins(10, 6, 10, 6)
        
        lbl_env = QLabel("环境温度")
        lbl_env.setStyleSheet(
            "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        env_layout.addWidget(lbl_env)
        env_layout.addStretch()
        
        self.lbl_env_temp = QLabel("--")
        self.lbl_env_temp.setStyleSheet(
            "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 10pt;"
        )
        env_layout.addWidget(self.lbl_env_temp)
        
        lbl_unit = QLabel("°C")
        lbl_unit.setStyleSheet("color: #6e6e72; font-size: 8.5pt;")
        env_layout.addWidget(lbl_unit)
        
        layout.addWidget(env_frame)
        
        self.temperature_box.add_layout(layout)

    # ============================================================
    # 打印参数面板
    # ============================================================
    def _create_print_params_content(self):
        """创建打印参数面板内容"""
        layout = QVBoxLayout()
        layout.setSpacing(4)
        
        # 参数区块容器
        params_frame = QFrame()
        params_frame.setObjectName("params_frame")
        params_frame.setStyleSheet("""
            QFrame#params_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(4, 4, 4, 4)
        params_layout.setSpacing(2)
        
        # 打印速度
        self.print_speed_widget = StatusValueWidget("打印速度", "--", "mm/s")
        self.print_speed_widget.lbl_value.setStyleSheet(
            "color: #4FC3F7; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 10pt; font-weight: 600;"
        )
        params_layout.addWidget(self.print_speed_widget)
        
        # 移动速度
        self.travel_speed_widget = StatusValueWidget("移动速度", "--", "mm/s")
        params_layout.addWidget(self.travel_speed_widget)
        
        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #38383c;")
        sep.setFixedHeight(1)
        params_layout.addWidget(sep)
        
        # 挤出机速度
        self.extruder_speed_widget = StatusValueWidget("挤出速度", "--", "mm/s")
        self.extruder_speed_widget.lbl_value.setStyleSheet(
            "color: #FFB74D; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 10pt; font-weight: 600;"
        )
        params_layout.addWidget(self.extruder_speed_widget)
        
        # 流量倍率
        self.flow_rate_widget = StatusValueWidget("流量倍率", "100", "%")
        params_layout.addWidget(self.flow_rate_widget)
        
        # 分隔线
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background-color: #38383c;")
        sep2.setFixedHeight(1)
        params_layout.addWidget(sep2)
        
        # 层高
        self.layer_height_widget = StatusValueWidget("层高", "--", "mm")
        params_layout.addWidget(self.layer_height_widget)
        
        # 线宽
        self.line_width_widget = StatusValueWidget("线宽", "--", "mm")
        params_layout.addWidget(self.line_width_widget)
        
        layout.addWidget(params_frame)
        
        self.print_params_box.add_layout(layout)

    # ============================================================
    # 运动状态面板
    # ============================================================
    def _create_motion_status_content(self):
        """创建运动状态面板内容"""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        # TCP速度（大号显示）
        speed_frame = QFrame()
        speed_frame.setObjectName("speed_frame")
        speed_frame.setStyleSheet("""
            QFrame#speed_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        speed_layout = QVBoxLayout(speed_frame)
        speed_layout.setContentsMargins(10, 8, 10, 8)
        speed_layout.setSpacing(4)
        
        speed_header = QHBoxLayout()
        lbl_speed_title = QLabel("TCP 速度")
        lbl_speed_title.setStyleSheet(
            "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        speed_header.addWidget(lbl_speed_title)
        speed_header.addStretch()
        
        self.lbl_tcp_speed = QLabel("0.0")
        self.lbl_tcp_speed.setStyleSheet(
            "color: #4FC3F7; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 18pt; font-weight: bold;"
        )
        speed_header.addWidget(self.lbl_tcp_speed)
        
        lbl_speed_unit = QLabel("mm/s")
        lbl_speed_unit.setStyleSheet("color: #6e6e72; font-size: 9pt; padding-left: 4px;")
        speed_header.addWidget(lbl_speed_unit)
        
        speed_layout.addLayout(speed_header)
        
        # TCP速度进度条（可视化）
        self.tcp_speed_bar = QProgressBar()
        self.tcp_speed_bar.setRange(0, 500)  # 0-500 mm/s
        self.tcp_speed_bar.setValue(0)
        self.tcp_speed_bar.setFixedHeight(6)
        self.tcp_speed_bar.setTextVisible(False)
        self.tcp_speed_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #363638;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4FC3F7, stop:1 #29B6F6);
            }
        """)
        speed_layout.addWidget(self.tcp_speed_bar)
        
        layout.addWidget(speed_frame)
        
        # 运动模式/状态
        mode_frame = QFrame()
        mode_frame.setObjectName("mode_frame")
        mode_frame.setStyleSheet("""
            QFrame#mode_frame {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """)
        mode_layout = QVBoxLayout(mode_frame)
        mode_layout.setContentsMargins(10, 6, 10, 6)
        mode_layout.setSpacing(4)
        
        # 当前动作
        self.motion_action_widget = StatusValueWidget("当前动作", "空闲", "")
        mode_layout.addWidget(self.motion_action_widget)
        
        # 运动类型（打印/移动）
        self.motion_type_widget = StatusValueWidget("运动类型", "--", "")
        mode_layout.addWidget(self.motion_type_widget)
        
        layout.addWidget(mode_frame)
        
        self.motion_box.add_layout(layout)

    # ============================================================
    # 关节角度面板
    # ============================================================
    def _create_joint_status_content(self):
        """创建关节状态内容（UR 风格：名称 | 滑块 | 数值）"""
        joint_layout = QVBoxLayout()
        joint_layout.setSpacing(3)

        # UR 官方风格：每行 关节名 | 滑块 | 数值
        j_names = ["J1 基座", "J2 肩部", "J3 肘部", "J4 腕部1", "J5 腕部2", "J6 腕部3"]
        j_tooltips = ["Base", "Shoulder", "Elbow", "Wrist 1", "Wrist 2", "Wrist 3"]

        for i, (name, tip) in enumerate(zip(j_names, j_tooltips)):
            row = QFrame()
            row.setObjectName("joint_row")
            bg = "#2a2a2c" if i % 2 == 0 else "#262628"
            rad = "5px 5px 0 0" if i == 0 else ("0 0 5px 5px" if i == 5 else "0")
            row.setStyleSheet(
                f"QFrame#joint_row {{ background-color: {bg}; border-radius: {rad}; }}"
            )
            row.setToolTip(f"{tip} · 角度范围 ±360°")
            row.setFixedHeight(32)
            h = QHBoxLayout(row)
            h.setContentsMargins(6, 5, 6, 5)
            h.setSpacing(8)

            # 关节名称
            lbl_name = QLabel(name)
            lbl_name.setFixedWidth(48)
            lbl_name.setStyleSheet(
                "color: #8e8e92; font-size: 9pt; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
            )
            h.addWidget(lbl_name)

            # 滑块（带刻度，只读显示）
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(-360, 360)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setTickInterval(180)
            slider.setEnabled(False)
            slider.setFixedHeight(20)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    border: none;
                    height: 5px;
                    background: #363638;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #4a9eff;
                    width: 10px;
                    margin: -2px 0;
                    border-radius: 5px;
                }
                QSlider::sub-page:horizontal { background: transparent; }
                QSlider:disabled { opacity: 1; }
            """)
            h.addWidget(slider, 1)

            # 数值（左对齐：关节名后是滑块，再后直接跟角度，阅读更顺）
            value_label = QLabel("0.0°")
            value_label.setFixedWidth(48)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value_label.setStyleSheet(
                "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                "font-size: 9.5pt; font-weight: 500; letter-spacing: 0.3px;"
            )
            h.addWidget(value_label)

            joint_layout.addWidget(row)
            self.joint_widgets.append((value_label, slider))

        self.joint_status_box.add_layout(joint_layout)

    def _create_pose_block(self, parent_layout, widget_list, box_style: str):
        """创建位姿/偏移块：垂直列表布局，参考 UR/FANUC 工业标准
        
        布局示例：
            位置 (mm)
              X       -259.012
              Y        131.693
              Z         40.617
            姿态 (°)
              Rx        91.307
              Ry       153.681
              Rz         0.339
        
        特点：
        - 每行一个轴，数值右对齐，小数点纵向对齐
        - 面板可以更窄（~220px）
        - 8 位数据（如 -259.012）显示完整
        """
        # 样式定义
        axis_style = (
            "color: #8e8e92; font-size: 9pt; "
            "font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;"
        )
        value_style = (
            "color: #e6e6e8; font-family: 'Consolas', 'JetBrains Mono', monospace; "
            "font-size: 9.5pt; font-weight: 500;"
        )
        section_label_style = (
            "color: #6e6e72; font-size: 8.5pt; font-family: 'Segoe UI', sans-serif;"
        )

        def create_axis_row(axis_name: str):
            """创建单个轴行：轴名 + 数值（右对齐）"""
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(4, 2, 4, 2)
            h.setSpacing(8)
            
            # 轴名（固定宽度，左对齐）
            lbl = QLabel(axis_name)
            lbl.setStyleSheet(axis_style)
            lbl.setFixedWidth(24)
            lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(lbl)
            
            # 数值（右对齐，小数点对齐，工业标准）
            val = QLabel("0.000")
            val.setStyleSheet(value_style)
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            h.addWidget(val, 1)  # stretch=1，占满剩余空间
            
            widget_list.append(val)
            return row

        def create_section(title: str, axes: list):
            """创建一个区块（位置或姿态）"""
            frame = QFrame()
            frame.setObjectName("pose_block")
            frame.setStyleSheet(box_style)
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(2)
            
            # 区块标题
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(section_label_style)
            layout.addWidget(title_lbl)
            
            # 各轴行
            for axis in axes:
                layout.addWidget(create_axis_row(axis))
            
            return frame

        # 位置区块
        parent_layout.addWidget(create_section("位置 (mm)", ["X", "Y", "Z"]))
        # 姿态区块
        parent_layout.addWidget(create_section("姿态 (°)", ["Rx", "Ry", "Rz"]))

    def _create_tcp_status_content(self):
        """创建TCP位姿内容（位置/姿态块式布局 + 复制按钮）"""
        tcp_layout = QVBoxLayout()
        tcp_layout.setSpacing(8)
        
        # 复制按钮行
        copy_row = QWidget()
        copy_layout = QHBoxLayout(copy_row)
        copy_layout.setContentsMargins(0, 0, 0, 4)
        copy_layout.setSpacing(4)
        copy_layout.addStretch()
        
        # 复制位姿按钮
        self.btn_copy_tcp = QToolButton()
        self.btn_copy_tcp.setText("复制位姿")
        self.btn_copy_tcp.setToolTip("复制当前TCP位姿到剪贴板\n格式: p[x, y, z, rx, ry, rz]")
        self.btn_copy_tcp.setStyleSheet("""
            QToolButton {
                background-color: #353538;
                border: 1px solid #404044;
                border-radius: 4px;
                padding: 4px 10px;
                color: #b0b0b4;
                font-size: 9pt;
            }
            QToolButton:hover {
                background-color: #3c3c3e;
                border-color: #48484a;
                color: #e0e0e4;
            }
            QToolButton:pressed {
                background-color: #2a2a2c;
            }
        """)
        self.btn_copy_tcp.clicked.connect(self._copy_tcp_pose)
        copy_layout.addWidget(self.btn_copy_tcp)
        
        tcp_layout.addWidget(copy_row)
        
        block_style = """
            QFrame#pose_block {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """
        self._create_pose_block(tcp_layout, self.tcp_widgets, block_style)
        self.tcp_status_box.add_layout(tcp_layout)
    
    def _copy_tcp_pose(self):
        """复制当前TCP位姿到剪贴板"""
        try:
            values = []
            for i, widget in enumerate(self.tcp_widgets):
                text = widget.text().strip()
                # 将毫米转回米，度数转回弧度（URScript格式）
                val = float(text) if text else 0.0
                if i < 3:  # 位置：毫米 -> 米
                    val = val / 1000.0
                else:  # 旋转：度 -> 弧度
                    val = val / 57.2958
                values.append(val)
            
            # 格式化为 URScript pose 格式
            pose_str = f"p[{values[0]:.6f}, {values[1]:.6f}, {values[2]:.6f}, {values[3]:.6f}, {values[4]:.6f}, {values[5]:.6f}]"
            
            clipboard = QApplication.clipboard()
            clipboard.setText(pose_str)
            
            # 视觉反馈：按钮短暂变色
            self.btn_copy_tcp.setText("已复制 ✓")
            self.btn_copy_tcp.setStyleSheet("""
                QToolButton {
                    background-color: #2d5a2d;
                    border: 1px solid #4a7a4a;
                    border-radius: 4px;
                    padding: 4px 10px;
                    color: #90EE90;
                    font-size: 9pt;
                }
            """)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, self._reset_copy_button)
        except Exception as e:
            print(f"复制TCP位姿失败: {e}")
    
    def _reset_copy_button(self):
        """重置复制按钮状态"""
        self.btn_copy_tcp.setText("复制位姿")
        self.btn_copy_tcp.setStyleSheet("""
            QToolButton {
                background-color: #353538;
                border: 1px solid #404044;
                border-radius: 4px;
                padding: 4px 10px;
                color: #b0b0b4;
                font-size: 9pt;
            }
            QToolButton:hover {
                background-color: #3c3c3e;
                border-color: #48484a;
                color: #e0e0e4;
            }
            QToolButton:pressed {
                background-color: #2a2a2c;
            }
        """)

    def _create_offset_status_content(self):
        """创建TCP偏移内容（位置/姿态块式布局）"""
        offset_layout = QVBoxLayout()
        offset_layout.setSpacing(8)
        block_style = """
            QFrame#pose_block {
                background-color: #2a2a2c;
                border: 1px solid #38383c;
                border-radius: 6px;
            }
        """
        self._create_pose_block(offset_layout, self.offset_widgets, block_style)
        self.offset_status_box.add_layout(offset_layout)

    def _setup_styles(self):
        """设置整体样式"""
        self.setStyleSheet("""
            QWidget#status_monitor_widget {
                background-color: #2c2c2e;
            }
            QGroupBox {
                border: none;
                margin: 0;
                margin-bottom: 2px;
                padding: 0;
                padding-top: 0;
                border-radius: 6px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)

    def update_status(self, tcp, joints, offset):
        """更新所有状态信息

        Args:
            tcp: TCP位姿数组 [x, y, z, rx, ry, rz]
            joints: 关节角度数组 [j1, j2, j3, j4, j5, j6]
            offset: TCP偏移数组 [x, y, z, rx, ry, rz]
        """
        try:
            # 1. 更新关节角度（UR 风格：滑块表示角度在 ±360° 范围内的位置）
            if joints:
                for i in range(min(len(joints), 6)):
                    deg = joints[i] * 57.2958  # 转换为度
                    lbl, slider = self.joint_widgets[i]
                    lbl.setText(f"{deg:.1f}°")
                    # 滑块值限制在 -360~360，超出时显示在端点
                    slider_val = max(-360, min(360, int(round(deg))))
                    slider.setValue(slider_val)

            # 2. 更新TCP位姿（标签已含单位，数值仅显示数字）
            if tcp:
                for i in range(min(len(tcp), 6)):
                    if i < 3:  # 位置 (转换为毫米)
                        val = tcp[i] * 1000.0
                    else:  # 旋转 (转换为度)
                        val = tcp[i] * 57.2958
                    self.tcp_widgets[i].setText(f"{val:.3f}")

            # 3. 更新TCP偏移（标签已含单位，数值仅显示数字）
            if offset:
                for i in range(min(len(offset), 6)):
                    if i < 3:  # 位置 (转换为毫米)
                        val = offset[i] * 1000.0
                    else:  # 旋转 (转换为度)
                        val = offset[i] * 57.2958
                    self.offset_widgets[i].setText(f"{val:.3f}")

        except Exception as e:
            # 避免数据更新时的偶发闪退，但在开发时可以输出错误信息
            print(f"更新状态时出现错误: {e}")
            pass

    def set_connection_status(self, connected: bool, status_text: str = ""):
        """设置连接/数据流状态指示

        Args:
            connected: 是否已连接并可接收数据
            status_text: 状态描述，如 "已连接"、"只读模式"、"未连接"
        """
        if connected:
            color = "#388E3C"
            tip = "数据流: 正常"
        else:
            color = "#616161"
            tip = "数据流: 未连接"
        self.data_status_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        self.data_status_dot.setToolTip(tip)
        self.data_status_label.setText(status_text or ("正常" if connected else "未连接"))

    # ============================================================
    # 数据更新接口方法
    # ============================================================
    
    def update_tcp_speed(self, speed_m_s: float):
        """更新TCP速度显示
        
        Args:
            speed_m_s: TCP速度，单位 m/s
        """
        try:
            speed_mm_s = speed_m_s * 1000.0
            self.lbl_tcp_speed.setText(f"{speed_mm_s:.1f}")
            
            # 更新进度条（假设最大速度500mm/s）
            bar_value = min(500, int(speed_mm_s))
            self.tcp_speed_bar.setValue(bar_value)
            
            # 根据速度改变颜色
            if speed_mm_s > 300:
                color = "#FF8A65"  # 高速 - 橙色
            elif speed_mm_s > 100:
                color = "#4FC3F7"  # 中速 - 蓝色
            elif speed_mm_s > 2:
                color = "#81C784"  # 低速 - 绿色
            else:
                color = "#8e8e92"  # 静止 - 灰色
            
            self.lbl_tcp_speed.setStyleSheet(
                f"color: {color}; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                "font-size: 18pt; font-weight: bold;"
            )
        except Exception as e:
            print(f"更新TCP速度失败: {e}")

    def update_print_progress(self, progress: float, current_layer: int = None, total_layers: int = None):
        """更新打印进度
        
        Args:
            progress: 打印进度百分比 (0-100)
            current_layer: 当前层数（可选）
            total_layers: 总层数（可选）
        """
        try:
            progress = max(0, min(100, progress))
            self.print_progress_bar.setValue(int(progress))
            self.lbl_progress_percent.setText(f"{progress:.1f}%")
            
            # 根据进度改变颜色
            if progress >= 100:
                color = "#81C784"  # 完成 - 绿色
            elif progress >= 50:
                color = "#4FC3F7"  # 中途 - 蓝色
            else:
                color = "#FFB74D"  # 初期 - 橙色
            
            self.lbl_progress_percent.setStyleSheet(
                f"color: {color}; font-family: 'Consolas', 'JetBrains Mono', monospace; "
                "font-size: 14pt; font-weight: bold;"
            )
            
            # 更新层数
            if current_layer is not None:
                self.lbl_current_layer.setText(str(current_layer))
            if total_layers is not None:
                self.lbl_total_layers.setText(str(total_layers))
                
        except Exception as e:
            print(f"更新打印进度失败: {e}")

    def update_print_time(self, elapsed_seconds: int = None, remaining_seconds: int = None, 
                          estimated_total_seconds: int = None):
        """更新打印时间显示
        
        Args:
            elapsed_seconds: 已打印时间（秒）
            remaining_seconds: 剩余时间（秒）
            estimated_total_seconds: 预估总时间（秒）
        """
        try:
            if elapsed_seconds is not None:
                self._elapsed_seconds = elapsed_seconds
                self.print_time_widget.set_value(self._format_time(elapsed_seconds))
            
            if remaining_seconds is not None:
                self.remaining_time_widget.set_value(self._format_time(remaining_seconds))
                
                # 计算预计完成时间
                from datetime import datetime, timedelta
                eta = datetime.now() + timedelta(seconds=remaining_seconds)
                self.eta_widget.set_value(eta.strftime("%H:%M"))
            
            if estimated_total_seconds is not None:
                self._estimated_total_seconds = estimated_total_seconds
                
        except Exception as e:
            print(f"更新打印时间失败: {e}")

    def update_temperature(self, nozzle_current: float = None, nozzle_target: float = None,
                          bed_current: float = None, bed_target: float = None,
                          environment: float = None):
        """更新温度显示
        
        Args:
            nozzle_current: 喷头当前温度 (°C)
            nozzle_target: 喷头目标温度 (°C)
            bed_current: 热床当前温度 (°C)
            bed_target: 热床目标温度 (°C)
            environment: 环境温度 (°C)
        """
        try:
            if nozzle_current is not None:
                self.nozzle_temp_widget.set_temperature(nozzle_current, nozzle_target)
            
            if bed_current is not None:
                self.bed_temp_widget.set_temperature(bed_current, bed_target)
            
            if environment is not None:
                self.lbl_env_temp.setText(f"{environment:.1f}")
                
        except Exception as e:
            print(f"更新温度失败: {e}")

    def update_print_params(self, print_speed: float = None, travel_speed: float = None,
                           extruder_speed: float = None, flow_rate: float = None,
                           layer_height: float = None, line_width: float = None):
        """更新打印参数显示
        
        Args:
            print_speed: 打印速度 (mm/s)
            travel_speed: 移动速度 (mm/s)
            extruder_speed: 挤出机速度 (mm/s)
            flow_rate: 流量倍率 (%)
            layer_height: 层高 (mm)
            line_width: 线宽 (mm)
        """
        try:
            if print_speed is not None:
                self.print_speed_widget.set_value(f"{print_speed:.1f}")
            
            if travel_speed is not None:
                self.travel_speed_widget.set_value(f"{travel_speed:.1f}")
            
            if extruder_speed is not None:
                self.extruder_speed_widget.set_value(f"{extruder_speed:.2f}")
            
            if flow_rate is not None:
                self.flow_rate_widget.set_value(f"{flow_rate:.0f}")
            
            if layer_height is not None:
                self.layer_height_widget.set_value(f"{layer_height:.2f}")
            
            if line_width is not None:
                self.line_width_widget.set_value(f"{line_width:.2f}")
                
        except Exception as e:
            print(f"更新打印参数失败: {e}")

    def set_robot_state(self, state: str):
        """设置机器人状态显示
        
        Args:
            state: 状态字符串，如 "打印中"、"暂停"、"空闲"、"加热中"、"错误"
        """
        state_styles = {
            "打印中": ("#81C784", "#2d3d2d"),    # 绿色
            "printing": ("#81C784", "#2d3d2d"),
            "暂停": ("#FFB74D", "#3d3a2d"),       # 橙色
            "paused": ("#FFB74D", "#3d3a2d"),
            "空闲": ("#4FC3F7", "#2d3a3d"),       # 蓝色
            "idle": ("#4FC3F7", "#2d3a3d"),
            "加热中": ("#FF8A65", "#3d2d2d"),     # 红橙色
            "heating": ("#FF8A65", "#3d2d2d"),
            "错误": ("#EF5350", "#3d2d2d"),       # 红色
            "error": ("#EF5350", "#3d2d2d"),
            "未连接": ("#8e8e92", "#2d2d2d"),     # 灰色
            "disconnected": ("#8e8e92", "#2d2d2d"),
        }
        
        try:
            text_color, bg_color = state_styles.get(state.lower(), ("#8e8e92", "#2d2d2d"))
            self.lbl_robot_state.setText(state)
            self.lbl_robot_state.setStyleSheet(
                f"color: {text_color}; font-size: 9pt; font-weight: 500; padding: 2px 8px; "
                f"background-color: {bg_color}; border-radius: 4px;"
            )
        except Exception as e:
            print(f"设置机器人状态失败: {e}")

    def set_motion_status(self, action: str = None, motion_type: str = None):
        """设置运动状态
        
        Args:
            action: 当前动作，如 "移动中"、"打印中"、"等待"、"空闲"
            motion_type: 运动类型，如 "打印"、"移动"、"快速移动"
        """
        try:
            if action is not None:
                self.motion_action_widget.set_value(action)
            if motion_type is not None:
                self.motion_type_widget.set_value(motion_type)
        except Exception as e:
            print(f"设置运动状态失败: {e}")

    def start_print_timer(self, estimated_total_seconds: int = 0):
        """启动打印计时器
        
        Args:
            estimated_total_seconds: 预估总打印时间（秒）
        """
        self._elapsed_seconds = 0
        self._estimated_total_seconds = estimated_total_seconds
        self._print_timer.start(1000)  # 每秒更新一次
        self.set_robot_state("打印中")

    def stop_print_timer(self):
        """停止打印计时器"""
        self._print_timer.stop()

    def reset_print_stats(self):
        """重置打印统计"""
        self._elapsed_seconds = 0
        self._estimated_total_seconds = 0
        self.stop_print_timer()
        
        self.print_progress_bar.setValue(0)
        self.lbl_progress_percent.setText("0%")
        self.print_time_widget.set_value("--:--:--")
        self.remaining_time_widget.set_value("--:--:--")
        self.eta_widget.set_value("--:--")
        self.lbl_current_layer.setText("0")
        self.lbl_total_layers.setText("--")
        self.set_robot_state("空闲")

    def _update_print_time(self):
        """内部方法：定时更新打印时间"""
        self._elapsed_seconds += 1
        self.print_time_widget.set_value(self._format_time(self._elapsed_seconds))
        
        # 如果有预估总时间，计算剩余时间
        if self._estimated_total_seconds > 0:
            remaining = max(0, self._estimated_total_seconds - self._elapsed_seconds)
            self.remaining_time_widget.set_value(self._format_time(remaining))
            
            # 计算预计完成时间
            from datetime import datetime, timedelta
            eta = datetime.now() + timedelta(seconds=remaining)
            self.eta_widget.set_value(eta.strftime("%H:%M"))
            
            # 更新进度
            if self._estimated_total_seconds > 0:
                progress = min(100, (self._elapsed_seconds / self._estimated_total_seconds) * 100)
                self.update_print_progress(progress)

    @staticmethod
    def _format_time(seconds: int) -> str:
        """格式化时间为 HH:MM:SS 格式
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间字符串
        """
        if seconds < 0:
            return "--:--:--"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
