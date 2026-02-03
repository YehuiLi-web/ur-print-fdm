"""
独立的几何变换工具
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel, QTextEdit, QCheckBox, QGridLayout, QComboBox, QLineEdit)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.core.print_lib import URPrintLib
import math
import numpy as np


class GeometryCalculatorWidget(QWidget):
    """几何变换工具独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('offset', 'tcp', 'unit')
        """
        super().__init__()
        self.print_lib = URPrintLib()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'offset':
            # 位姿平移与偏置组
            offset_group = QGroupBox("位姿平移与偏置 (Pose Offset)")
            offset_layout = QFormLayout(offset_group)

            self.offset_base_x = QDoubleSpinBox(); self.offset_base_x.setRange(-1000, 1000); self.offset_base_x.setValue(0.0)
            self.offset_base_y = QDoubleSpinBox(); self.offset_base_y.setRange(-1000, 1000); self.offset_base_y.setValue(0.0)
            self.offset_base_z = QDoubleSpinBox(); self.offset_base_z.setRange(-1000, 1000); self.offset_base_z.setValue(0.0)
            self.offset_delta_x = QDoubleSpinBox(); self.offset_delta_x.setRange(-100, 100); self.offset_delta_x.setValue(0.0)
            self.offset_delta_y = QDoubleSpinBox(); self.offset_delta_y.setRange(-100, 100); self.offset_delta_y.setValue(0.0)
            self.offset_delta_z = QDoubleSpinBox(); self.offset_delta_z.setRange(-100, 100); self.offset_delta_z.setValue(20.0)

            btn_calc_offset = QPushButton("计算位姿偏置"); btn_calc_offset.clicked.connect(self._calc_pose_offset)
            self.offset_result = QLabel("新位姿: [x, y, z, rx, ry, rz]")

            offset_layout.addRow("当前位姿 X (mm):", self.offset_base_x)
            offset_layout.addRow("当前位姿 Y (mm):", self.offset_base_y)
            offset_layout.addRow("当前位姿 Z (mm):", self.offset_base_z)
            offset_layout.addRow("X偏移量 (mm):", self.offset_delta_x)
            offset_layout.addRow("Y偏移量 (mm):", self.offset_delta_y)
            offset_layout.addRow("Z偏移量 (mm):", self.offset_delta_z)
            offset_layout.addRow(btn_calc_offset)
            offset_layout.addRow(self.offset_result)

            layout.addWidget(offset_group)

        if self.show_only is None or self.show_only == 'tcp':
            # TCP自动转换与标定组
            tcp_group = QGroupBox("TCP自动转换与标定 (TCP Auto Conversion)")
            tcp_layout = QFormLayout(tcp_group)

            self.tcp_length = QDoubleSpinBox(); self.tcp_length.setRange(0, 500); self.tcp_length.setValue(150.0)
            self.tcp_angle = QDoubleSpinBox(); self.tcp_angle.setRange(-180, 180); self.tcp_angle.setValue(0.0)

            btn_calc_tcp = QPushButton("计算TCP偏置"); btn_calc_tcp.clicked.connect(self._calc_tcp_offset)
            self.tcp_result = QLabel("TCP偏置: [x, y, z, rx, ry, rz]")

            tcp_layout.addRow("喷嘴长度 (mm):", self.tcp_length)
            tcp_layout.addRow("倾斜角度 (°):", self.tcp_angle)
            tcp_layout.addRow(btn_calc_tcp)
            tcp_layout.addRow(self.tcp_result)

            layout.addWidget(tcp_group)

        if self.show_only is None or self.show_only == 'unit':
            # 単位转换组
            unit_group = QGroupBox("単位转换 (Unit Converter)")
            unit_layout = QGridLayout(unit_group)

            self.unit_input = QLineEdit()
            self.unit_input.setPlaceholderText("输入数值，例如: 45 或 0.785")
            self.unit_from = QComboBox()
            self.unit_from.addItems(["角度(°)", "弧度(rad)", "毫米(mm)", "米(m)", "英寸(in)"])
            self.unit_to = QComboBox()
            self.unit_to.addItems(["角度(°)", "弧度(rad)", "毫米(mm)", "米(m)", "英寸(in)"])

            btn_convert = QPushButton("转换"); btn_convert.clicked.connect(self._convert_units)
            self.unit_result = QLabel("结果: --")

            unit_layout.addWidget(QLabel("输入值:"), 0, 0)
            unit_layout.addWidget(self.unit_input, 0, 1)
            unit_layout.addWidget(QLabel("从:"), 1, 0)
            unit_layout.addWidget(self.unit_from, 1, 1)
            unit_layout.addWidget(QLabel("到:"), 2, 0)
            unit_layout.addWidget(self.unit_to, 2, 1)
            unit_layout.addWidget(btn_convert, 3, 0, 1, 2)
            unit_layout.addWidget(self.unit_result, 4, 0, 1, 2)

            layout.addWidget(unit_group)

        layout.addStretch()

    def _calc_pose_offset(self):
        """计算位姿偏置"""
        base_x = self.offset_base_x.value()
        base_y = self.offset_base_y.value()
        base_z = self.offset_base_z.value()
        delta_x = self.offset_delta_x.value()
        delta_y = self.offset_delta_y.value()
        delta_z = self.offset_delta_z.value()

        new_x = base_x + delta_x
        new_y = base_y + delta_y
        new_z = base_z + delta_z

        self.offset_result.setText(f"新位姿: [{new_x:.3f}, {new_y:.3f}, {new_z:.3f}, 0.000, 0.000, 0.000]")

    def _calc_tcp_offset(self):
        """计算TCP偏置"""
        length = self.tcp_length.value()
        angle_rad = math.radians(self.tcp_angle.value())

        # 假设TCP沿Z轴方向偏移，并考虑倾斜
        tcp_x = length * math.sin(angle_rad)
        tcp_y = 0  # 简化，假设在XZ平面内
        tcp_z = length * math.cos(angle_rad)

        # 角度偏置
        tcp_rx = 0
        tcp_ry = -angle_rad  # 假设倾斜是绕Y轴
        tcp_rz = 0

        self.tcp_result.setText(f"TCP偏置: [{tcp_x:.3f}, {tcp_y:.3f}, {tcp_z:.3f}, {tcp_rx:.4f}, {tcp_ry:.4f}, {tcp_rz:.4f}]")

    def _convert_units(self):
        """単位转换"""
        try:
            input_val = float(self.unit_input.text())
            from_unit = self.unit_from.currentText()
            to_unit = self.unit_to.currentText()

            # 首先转换到基本単位（度、毫米）
            if from_unit == "角度(°)":
                base_val = input_val
            elif from_unit == "弧度(rad)":
                base_val = math.degrees(input_val)
            elif from_unit == "米(m)":
                base_val = input_val * 1000  # 转换为毫米
            elif from_unit == "英寸(in)":
                base_val = input_val * 25.4  # 转换为毫米
            else:  # 毫米
                base_val = input_val

            # 然后转换为目标単位
            if to_unit == "角度(°)":
                result_val = base_val
            elif to_unit == "弧度(rad)":
                result_val = math.radians(base_val)
            elif to_unit == "米(m)":
                result_val = base_val / 1000
            elif to_unit == "英寸(in)":
                result_val = base_val / 25.4
            else:  # 毫米
                result_val = base_val

            self.unit_result.setText(f"结果: {result_val:.6f}")
        except ValueError:
            self.unit_result.setText("错误: 请输入有效的数字")
