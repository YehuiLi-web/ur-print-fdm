"""
Status Panel Prototype (Industrial Professional Version)
This file tests the new UI design focusing on:
1. Professional Aesthetics (No Emojis, Standard Icons)
2. High Data Density & Visibility (Fixed Layouts)
3. Drag-and-Drop Customization (User-defined Ordering)

Usage:
    python test_status_panel.py
"""

import sys
import math
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QProgressBar, QFrame, QScrollArea,
                             QToolButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSizePolicy, QGridLayout, QListWidget,
                             QListWidgetItem, QAbstractItemView, QStyle)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QIcon, QAction

# =============================================================================
# 1. Industrial Theme & Style
# =============================================================================
DARK_THEME = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 9pt;
}

QListWidget {
    background-color: #1e1e1e;
    border: none;
    outline: none;
}
QListWidget::item {
    background-color: transparent;
    border: none;
    padding: 2px;
}
QListWidget::item:selected {
    background-color: transparent;
    border: none;
}

/* Scrollbar */
QScrollBar:vertical {
    border: none;
    background: #1e1e1e;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #424242;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #616161; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* Table */
QTableWidget {
    background-color: transparent;
    border: none;
    gridline-color: #333333;
}
QTableWidget::item {
    padding: 2px 4px;
    border-bottom: 1px solid #2d2d2d;
}

/* Progress Bar */
QProgressBar {
    border: 1px solid #3e3e42;
    background-color: #252526;
    border-radius: 2px;
    text-align: center;
}
QProgressBar::chunk { background-color: #0e639c; }
"""

# =============================================================================
# 2. Reorderable Container & Base Components
# =============================================================================

class CollapsibleBox(QFrame):
    """
    Industrial Section Container
    Features: Standard Icon, Title, Toggle Button, Content Area
    """
    def __init__(self, title, icon_standard=None, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            CollapsibleBox {
                background-color: #252526;
                border: 1px solid #333337;
                border-radius: 4px;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- Header Bar ---
        self.header = QFrame()
        self.header.setFixedHeight(28)
        self.header.setStyleSheet("""
            QFrame {
                background-color: #333337;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom: 1px solid #2d2d2d;
            }
        """)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(6, 0, 6, 0)
        header_layout.setSpacing(8)

        # Icon
        if icon_standard:
            icon_lbl = QLabel()
            # Use Standard Pixmap for icons
            icon = QApplication.style().standardIcon(icon_standard)
            icon_lbl.setPixmap(icon.pixmap(14, 14))
            header_layout.addWidget(icon_lbl)

        # Title
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("font-weight: bold; color: #cccccc; font-size: 8.5pt; letter-spacing: 0.5px;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Toggle Button
        self.toggle_btn = QToolButton()
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False) # False means Expanded for ArrowType logic usually
        self.toggle_btn.setStyleSheet("""
            QToolButton { border: none; background: transparent; color: #aaa; }
            QToolButton:hover { color: #fff; }
        """)
        self.toggle_btn.clicked.connect(self.toggle_content)
        header_layout.addWidget(self.toggle_btn)

        self.main_layout.addWidget(self.header)

        # --- Content Area ---
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(4, 4, 4, 6)
        self.content_layout.setSpacing(4)

        self.main_layout.addWidget(self.content_area)

    def toggle_content(self):
        checked = self.toggle_btn.isChecked()
        self.content_area.setVisible(not checked)
        self.toggle_btn.setArrowType(Qt.ArrowType.RightArrow if checked else Qt.ArrowType.DownArrow)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


class ReorderablePanel(QListWidget):
    """
    Main container that allows Drag-and-Drop reordering of sections.
    """
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSpacing(4) # Space between cards

    def add_section(self, widget):
        """Add a custom widget as a list item"""
        item = QListWidgetItem(self)
        item.setSizeHint(widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, widget)

        # Hook up toggle event to resize list item
        if isinstance(widget, CollapsibleBox):
            widget.toggle_btn.clicked.connect(lambda: item.setSizeHint(widget.sizeHint()))

# =============================================================================
# 3. Functional Modules
# =============================================================================

class PrintStatsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Info Grid
        grid = QGridLayout()
        grid.setSpacing(6)

        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("font-family: Consolas; color: #fff; font-weight: bold;")

        self.lbl_remain = QLabel("--:--:--")
        self.lbl_remain.setStyleSheet("font-family: Consolas; color: #aaa;")

        grid.addWidget(QLabel("Elapsed:", styleSheet="color:#888;"), 0, 0)
        grid.addWidget(self.lbl_time, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        grid.addWidget(QLabel("Remaining:", styleSheet="color:#888;"), 1, 0)
        grid.addWidget(self.lbl_remain, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(grid)

        # Progress
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)

        self.lbl_pct = QLabel("0.0 %")
        self.lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_pct.setStyleSheet("font-size: 8pt; color: #4FC3F7;")
        layout.addWidget(self.lbl_pct)

    def update_data(self, elapsed, total):
        def fmt(s): return f"{int(s//3600):02}:{int((s%3600)//60):02}:{int(s%60):02}"
        self.lbl_time.setText(fmt(elapsed))
        pct = 0
        if total > 0:
            rem = max(0, total - elapsed)
            self.lbl_remain.setText(fmt(rem))
            pct = (elapsed / total) * 100
        self.bar.setValue(int(pct))
        self.lbl_pct.setText(f"{pct:.1f} %")


class MotionWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        # Velocity Display (Big Numbers)
        vel_frame = QFrame()
        vel_frame.setStyleSheet("background-color: #2a2a2a; border-radius: 3px;")
        vel_layout = QHBoxLayout(vel_frame)
        vel_layout.setContentsMargins(8, 6, 8, 6)

        v_label = QLabel("TCP VEL")
        v_label.setStyleSheet("color: #888; font-size: 8pt;")
        self.v_val = QLabel("0.0")
        self.v_val.setStyleSheet("color: #4FC3F7; font-size: 14pt; font-weight: bold; font-family: Consolas;")
        v_unit = QLabel("mm/s")
        v_unit.setStyleSheet("color: #666; font-size: 8pt; margin-top: 6px;")

        vel_layout.addWidget(v_label)
        vel_layout.addStretch()
        vel_layout.addWidget(self.v_val)
        vel_layout.addWidget(v_unit)
        layout.addWidget(vel_frame)

        # TCP Table (Compact)
        self.table = QTableWidget(6, 2)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        # Fix: Calculate exact height (6 rows * 22px + margins)
        row_height = 22
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        self.table.setFixedHeight(row_height * 6 + 4)

        labels = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        self.val_items = []

        for i, lbl in enumerate(labels):
            item_lbl = QTableWidgetItem(lbl)
            item_lbl.setFlags(Qt.ItemFlag.NoItemFlags)
            item_lbl.setForeground(QColor("#888"))
            self.table.setItem(i, 0, item_lbl)

            item_val = QTableWidgetItem("0.000")
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item_val.setFlags(Qt.ItemFlag.NoItemFlags)
            item_val.setForeground(QColor("#eee"))
            item_val.setFont(QFont("Consolas", 9))
            self.table.setItem(i, 1, item_val)
            self.val_items.append(item_val)

        layout.addWidget(self.table)

    def update_data(self, speed, pose):
        self.v_val.setText(f"{speed:.1f}")
        if not pose: return
        for i, val in enumerate(pose):
            if i < 3: # mm
                self.val_items[i].setText(f"{val*1000:.2f}")
            else: # rad
                self.val_items[i].setText(f"{val:.3f}")

class JointWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self.bars = []
        self.vals = []
        names = ["Base", "Shoulder", "Elbow", "Wrist1", "Wrist2", "Wrist3"]

        for name in names:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(name)
            lbl.setFixedWidth(55)
            lbl.setStyleSheet("color: #999; font-size: 8.5pt;")

            bar = QProgressBar()
            bar.setRange(-360, 360)
            bar.setFixedHeight(4)
            bar.setTextVisible(False)
            bar.setStyleSheet("QProgressBar { background: #333; border: none; } QProgressBar::chunk { background: #66BB6A; }")

            val = QLabel("0°")
            val.setFixedWidth(35)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            val.setStyleSheet("color: #ccc; font-family: Consolas; font-size: 8.5pt;")

            row.addWidget(lbl)
            row.addWidget(bar)
            row.addWidget(val)
            layout.addLayout(row)

            self.bars.append(bar)
            self.vals.append(val)

    def update_data(self, joints):
        if not joints: return
        for i, rad in enumerate(joints):
            deg = math.degrees(rad)
            self.bars[i].setValue(int(deg))
            self.vals[i].setText(f"{int(deg)}°")

            # Color logic
            adeg = abs(deg)
            color = "#66BB6A" # Green
            if adeg > 175: color = "#FFA726" # Orange
            if adeg > 350: color = "#EF5350" # Red
            self.bars[i].setStyleSheet(f"QProgressBar {{ background: #333; border: none; }} QProgressBar::chunk {{ background: {color}; }}")

class ExtruderWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        frame = QFrame()
        frame.setStyleSheet("background-color: #2a2a2a; border-radius: 3px;")
        fl = QHBoxLayout(frame)
        fl.setContentsMargins(8, 8, 8, 8)

        lbl = QLabel("FLOW RATE")
        lbl.setStyleSheet("color: #888;")

        self.val = QLabel("0.0 %")
        self.val.setStyleSheet("color: #FFA726; font-size: 12pt; font-weight: bold; font-family: Consolas;")

        fl.addWidget(lbl)
        fl.addStretch()
        fl.addWidget(self.val)
        layout.addWidget(frame)

    def update_data(self, rate):
        self.val.setText(f"{rate:.1f} %")

# =============================================================================
# 4. Main Application Test
# =============================================================================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR5 Industrial Status Panel")
        self.resize(300, 750)

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Header
        header = QLabel("STATUS MONITOR")
        header.setStyleSheet("color: #666; font-weight: bold; letter-spacing: 1px; padding: 5px;")
        layout.addWidget(header)

        # The Reorderable Panel
        self.panel = ReorderablePanel()
        layout.addWidget(self.panel)

        # --- Initialize Sections ---

        # 1. Print Statistics
        self.print_widget = PrintStatsWidget()
        self.sec_print = CollapsibleBox("Print Statistics", QStyle.StandardPixmap.SP_FileDialogInfoView)
        self.sec_print.add_widget(self.print_widget)
        self.panel.add_section(self.sec_print)

        # 2. Motion
        self.motion_widget = MotionWidget()
        self.sec_motion = CollapsibleBox("Motion Control", QStyle.StandardPixmap.SP_DriveNetIcon)
        self.sec_motion.add_widget(self.motion_widget)
        self.panel.add_section(self.sec_motion)

        # 3. Extrusion
        self.ext_widget = ExtruderWidget()
        self.sec_ext = CollapsibleBox("Extrusion System", QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton)
        self.sec_ext.add_widget(self.ext_widget)
        self.panel.add_section(self.sec_ext)

        # 4. Joints
        self.joint_widget = JointWidget()
        self.sec_joint = CollapsibleBox("Robot Joints", QStyle.StandardPixmap.SP_ComputerIcon)
        self.sec_joint.add_widget(self.joint_widget)
        self.panel.add_section(self.sec_joint)

        # --- Simulation ---
        self.elapsed = 0
        self.total = 7200
        self.timer = QTimer()
        self.timer.timeout.connect(self.simulate)
        self.timer.start(100)

    def simulate(self):
        self.elapsed += 1
        t = self.elapsed * 0.1

        # Update Print
        self.print_widget.update_data(self.elapsed, self.total)

        # Update Motion
        speed = abs(math.sin(t)) * 250
        pose = [
            0.5 + math.sin(t)*0.1, 0.2 + math.cos(t)*0.1, 0.4,
            3.14, 0.0, 1.57 + math.sin(t*0.5)*0.2
        ]
        self.motion_widget.update_data(speed, pose)

        # Update Extrusion
        rate = abs(math.sin(t)) * 100
        self.ext_widget.update_data(rate)

        # Update Joints
        joints = [
            math.sin(t)*3.14, math.cos(t)*1.0, -1.5,
            -0.5, 1.57, math.sin(t*2)*3.0
        ]
        self.joint_widget.update_data(joints)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)

    w = MainWindow()
    w.show()

    print("Test running. Drag sections to reorder.")
    sys.exit(app.exec())
