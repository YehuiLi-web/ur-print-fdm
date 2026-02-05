"""
Unified Status Panel for UR5CB3 FDM Printer
Displays print progress, robot state, and extrusion details.

注意：这是旧版实现，新版已迁移至 collapsible_status_dock.py
主窗口现在使用 collapsible_status_dock.StatusWidget

此文件保留作为参考，不再使用。
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QProgressBar, QLabel, QScrollArea,
                             QGroupBox, QToolButton, QFrame, QSizePolicy, QHeaderView)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from ur_print_fdm.config import config_manager
from ur_print_fdm.ui.mixins.theme_aware import ThemeAwareMixin
from ur_print_fdm.ui.style_utils import themed_qss

class CollapsibleBox(QGroupBox, ThemeAwareMixin):
    """Collapsible panel component"""
    toggled = pyqtSignal(bool)  # Fold state changed signal

    def __init__(self, title="", parent=None, state_key=None):
        super().__init__(title, parent)
        self.setup_theme_awareness()
        self.state_key = state_key  # Key for state memory

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 5, 5, 5)
        title_layout.setSpacing(5)

        # Toggle Button
        self.toggle_button = QToolButton()
        self.toggle_button.setCheckable(True)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_button.setStyleSheet(themed_qss("""
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #4a4a4a, stop:1 #3a3a3a);
                border: 1px solid #5a5a5a;
                border-radius: 3px;
                width: 16px;
                height: 16px;
            }
            QToolButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #5a5a5a, stop:1 #4a4a4a);
            }
        """))
        self.toggle_button.toggled.connect(self.toggle_content)

        # Title Label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {self.get_token('text')}; font-weight: bold; font-size: 12px;")

        title_layout.addWidget(self.toggle_button)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        # Content Area
        self.content_area = QFrame()
        self.content_area.setObjectName("content_area")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 5)

        # Add title bar and content area to main layout
        self.layout.addWidget(self.title_bar)
        self.layout.addWidget(self.content_area)

        # Load saved state
        if self.state_key:
            self.load_state()

    def on_theme_changed(self, theme_id: str):
        """主题变更回调"""
        # 更新标题标签颜色
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"color: {self.get_token('text')}; font-weight: bold; font-size: 12px;")
        # 更新按钮样式
        if hasattr(self, 'toggle_button'):
            self.toggle_button.setStyleSheet(themed_qss("""
                QToolButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                              stop:0 #4a4a4a, stop:1 #3a3a3a);
                    border: 1px solid #5a5a5a;
                    border-radius: 3px;
                    width: 16px;
                    height: 16px;
                }
                QToolButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                              stop:0 #5a5a5a, stop:1 #4a4a4a);
                }
            """))

    def toggle_content(self, checked):
        """Toggle content visibility"""
        self.content_area.setVisible(not checked)
        arrow_type = Qt.ArrowType.RightArrow if checked else Qt.ArrowType.DownArrow
        self.toggle_button.setArrowType(arrow_type)
        self.toggled.emit(not checked)

        # Save state
        if self.state_key:
            self.save_state(checked)

    def set_collapsed(self, collapsed):
        """Set collapsed state"""
        self.toggle_button.setChecked(collapsed)
        self.toggle_content(collapsed)

    def add_widget(self, widget):
        """Add widget to content area"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Add layout to content area"""
        self.content_layout.addLayout(layout)

    def save_state(self, collapsed):
        """Save current state"""
        try:
            config_manager.set(f"ui.panels.{self.state_key}", bool(collapsed))
            config_manager.save_config()
        except Exception as e:
            print(f"Failed to save panel state: {e}")

    def load_state(self):
        """Load saved state"""
        try:
            collapsed = config_manager.get(f"ui.panels.{self.state_key}")
            if collapsed is not None:
                self.set_collapsed(bool(collapsed))
        except Exception as e:
            print(f"Failed to load panel state: {e}")


class StatusPanel(QWidget):
    """Consolidated Status Panel"""

    def __init__(self):
        super().__init__()
        self.joint_widgets = []
        self.tcp_widgets = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)

        # 1. Print Statistics (New)
        self.stats_box = CollapsibleBox("Print Statistics", state_key="stats_panel_collapsed")
        self._create_print_stats_content()
        scroll_layout.addWidget(self.stats_box)

        # 2. Motion Status (Enhanced)
        self.motion_box = CollapsibleBox("Motion Status", state_key="motion_panel_collapsed")
        self._create_motion_status_content()
        scroll_layout.addWidget(self.motion_box)

        # 3. Extrusion Status (New)
        self.extrusion_box = CollapsibleBox("Extrusion Status", state_key="extrusion_panel_collapsed")
        self._create_extrusion_status_content()
        scroll_layout.addWidget(self.extrusion_box)

        # 4. Robot Joints (Existing)
        self.joint_box = CollapsibleBox("Robot Joints", state_key="joint_panel_collapsed")
        self._create_joint_status_content()
        scroll_layout.addWidget(self.joint_box)

        # Spacer
        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        self._setup_styles()

    def _create_print_stats_content(self):
        layout = QVBoxLayout()

        # Time info
        time_layout = QVBoxLayout()
        time_layout.setSpacing(2)

        self.lbl_print_time = QLabel("Print Time: --:--:--")
        self.lbl_remain_time = QLabel("Remaining: --:--:--")

        time_layout.addWidget(self.lbl_print_time)
        time_layout.addWidget(self.lbl_remain_time)

        layout.addLayout(time_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.stats_box.add_layout(layout)

    def _create_motion_status_content(self):
        layout = QVBoxLayout()

        # Velocity
        self.lbl_velocity = QLabel("TCP Velocity: 0.0 mm/s")
        self.lbl_velocity.setStyleSheet("font-weight: bold; color: #4FC3F7;")
        layout.addWidget(self.lbl_velocity)

        # TCP Table
        self.tcp_table = QTableWidget(6, 2)
        self._setup_table_style(self.tcp_table)

        t_labels = ["X (mm)", "Y (mm)", "Z (mm)", "Rx (°)", "Ry (°)", "Rz (°)"]
        for i, name in enumerate(t_labels):
            self.tcp_table.setItem(i, 0, QTableWidgetItem(name))
            item = QTableWidgetItem("0.000")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tcp_table.setItem(i, 1, item)
            self.tcp_widgets.append(item)

        layout.addWidget(self.tcp_table)
        self.motion_box.add_layout(layout)

    def _create_extrusion_status_content(self):
        layout = QVBoxLayout()

        # Rate
        self.lbl_extrusion_rate = QLabel("Rate: 0.0 %") # Or mm/s depending on data
        self.lbl_extrusion_rate.setStyleSheet("color: #FFB74D;")
        layout.addWidget(self.lbl_extrusion_rate)

        self.extrusion_box.add_layout(layout)

    def _create_joint_status_content(self):
        layout = QVBoxLayout()

        self.joint_table = QTableWidget(6, 2)
        self._setup_table_style(self.joint_table)

        j_labels = ["Base", "Shoulder", "Elbow", "Wrist 1", "Wrist 2", "Wrist 3"]
        for i, name in enumerate(j_labels):
            self.joint_table.setItem(i, 0, QTableWidgetItem(name))
            widget_container = QWidget()
            h_layout = QHBoxLayout(widget_container)
            h_layout.setContentsMargins(2, 2, 2, 2)

            val_lbl = QLabel("0.0°")
            val_lbl.setFixedWidth(50)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            prog = QProgressBar()
            prog.setRange(-360, 360)
            prog.setValue(0)
            prog.setTextVisible(False)
            prog.setFixedHeight(6)

            h_layout.addWidget(val_lbl)
            h_layout.addWidget(prog)

            self.joint_table.setCellWidget(i, 1, widget_container)
            self.joint_widgets.append((val_lbl, prog))

        layout.addWidget(self.joint_table)
        self.joint_box.add_layout(layout)

    def _setup_table_style(self, table):
        table.horizontalHeader().setVisible(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.verticalHeader().setDefaultSectionSize(24)
        table.setMinimumHeight(24 * 6 + 10)
        table.setFixedHeight(24 * 6 + 10)
        table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: transparent;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding-left: 5px;
                border-bottom: 1px solid #333;
            }
        """)

    def _setup_styles(self):
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #444;
                border-radius: 4px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QLabel {
                color: #ddd;
            }
        """)

    def update_status(self, tcp, joints, offset, speed=0.0):
        """
        Update status display
        :param tcp: [x, y, z, rx, ry, rz]
        :param joints: [j1...j6]
        :param offset: [x, y, z, rx, ry, rz] (optional, not currently displayed in simplified view)
        :param speed: velocity in m/s
        """
        # Update Motion
        if tcp:
            for i in range(min(len(tcp), 6)):
                val = tcp[i] * 1000.0 if i < 3 else tcp[i] * 57.2958
                unit = "mm" if i < 3 else "°"
                self.tcp_widgets[i].setText(f"{val:.2f} {unit}")

        if speed is not None:
             self.lbl_velocity.setText(f"TCP Velocity: {speed * 1000.0:.1f} mm/s")

        # Update Joints
        if joints:
            for i in range(min(len(joints), 6)):
                deg = joints[i] * 57.2958
                lbl, bar = self.joint_widgets[i]
                lbl.setText(f"{deg:.1f}°")
                bar.setValue(int(deg))

                # Dynamic color
                if abs(deg) > 350:
                    color = "#ef5350"
                elif abs(deg) > 175:
                    color = "#ffa726"
                else:
                    color = "#66bb6a"
                bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")

    def update_print_stats(self, print_time_str, remaining_time_str, progress):
        self.lbl_print_time.setText(f"Print Time: {print_time_str}")
        self.lbl_remain_time.setText(f"Remaining: {remaining_time_str}")
        self.progress_bar.setValue(int(progress))

    def update_extrusion(self, rate):
        self.lbl_extrusion_rate.setText(f"Rate: {rate:.1f} %")
