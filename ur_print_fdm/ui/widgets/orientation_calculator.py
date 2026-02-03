"""
独立的姿态计算工具
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel, QTextEdit, QCheckBox, QGridLayout, QComboBox)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.core.print_lib import URPrintLib
import math
import numpy as np


class OrientationCalculatorWidget(QWidget):
    """姿态计算工具独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('tangent', 'tilt', 'curvature')
        """
        super().__init__()
        self.print_lib = URPrintLib()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'tangent':
            # 切线姿态跟随组
            tangent_group = QGroupBox("切线姿态跟随 (Tangential Following)")
            tangent_layout = QFormLayout(tangent_group)

            self.tangent_x1 = QDoubleSpinBox(); self.tangent_x1.setRange(-1000, 1000); self.tangent_x1.setValue(0.0)
            self.tangent_y1 = QDoubleSpinBox(); self.tangent_y1.setRange(-1000, 1000); self.tangent_y1.setValue(0.0)
            self.tangent_z1 = QDoubleSpinBox(); self.tangent_z1.setRange(-1000, 1000); self.tangent_z1.setValue(0.0)
            self.tangent_x2 = QDoubleSpinBox(); self.tangent_x2.setRange(-1000, 1000); self.tangent_x2.setValue(10.0)
            self.tangent_y2 = QDoubleSpinBox(); self.tangent_y2.setRange(-1000, 1000); self.tangent_y2.setValue(0.0)
            self.tangent_z2 = QDoubleSpinBox(); self.tangent_z2.setRange(-1000, 1000); self.tangent_z2.setValue(0.0)

            btn_calc_tangent = QPushButton("计算姿态"); btn_calc_tangent.clicked.connect(self._calc_tangent_orientation)
            self.tangent_result = QLabel("偏航角: --° | UR旋转向量: [rx, ry, rz]")

            tangent_layout.addRow("当前点 X (mm):", self.tangent_x1)
            tangent_layout.addRow("当前点 Y (mm):", self.tangent_y1)
            tangent_layout.addRow("当前点 Z (mm):", self.tangent_z1)
            tangent_layout.addRow("下一位置 X (mm):", self.tangent_x2)
            tangent_layout.addRow("下一位置 Y (mm):", self.tangent_y2)
            tangent_layout.addRow("下一位置 Z (mm):", self.tangent_z2)
            tangent_layout.addRow(btn_calc_tangent)
            tangent_layout.addRow(self.tangent_result)

            layout.addWidget(tangent_group)

        if self.show_only is None or self.show_only == 'tilt':
            # 变倾角计算组
            tilt_group = QGroupBox("变倾角计算 (Variable Tilt Angle)")
            tilt_layout = QFormLayout(tilt_group)

            self.tilt_angle = QDoubleSpinBox(); self.tilt_angle.setRange(-90, 90); self.tilt_angle.setValue(15)
            self.tilt_curvature = QDoubleSpinBox(); self.tilt_curvature.setRange(0, 100); self.tilt_curvature.setValue(5)

            btn_calc_tilt = QPushButton("计算倾角姿态"); btn_calc_tilt.clicked.connect(self._calc_variable_tilt)
            self.tilt_result = QLabel("绕Y轴旋转: --°")

            tilt_layout.addRow("目标倾角 (°):", self.tilt_angle)
            tilt_layout.addRow("路径曲率 (1/m):", self.tilt_curvature)
            tilt_layout.addRow(btn_calc_tilt)
            tilt_layout.addRow(self.tilt_result)

            layout.addWidget(tilt_group)

        if self.show_only is None or self.show_only == 'curvature':
            # 曲率半径校验组
            curvature_group = QGroupBox("曲率半径校验 (Min Bend Radius Check)")
            curvature_layout = QFormLayout(curvature_group)

            self.curvature_radius = QDoubleSpinBox(); self.curvature_radius.setRange(0.1, 1000); self.curvature_radius.setValue(50.0)
            self.fiber_min_radius = QDoubleSpinBox(); self.fiber_min_radius.setRange(0.1, 500); self.fiber_min_radius.setValue(5.0)
            self.fiber_min_radius.setToolTip("最小弯曲半径，小于该值纤维可能断裂")

            btn_check_radius = QPushButton("校验曲率"); btn_check_radius.clicked.connect(self._check_min_radius)
            self.radius_result = QLabel("状态: --")

            curvature_layout.addRow("当前路径半径 (mm):", self.curvature_radius)
            curvature_layout.addRow("纤维最小半径 (mm):", self.fiber_min_radius)
            curvature_layout.addRow(btn_check_radius)
            curvature_layout.addRow(self.radius_result)

            layout.addWidget(curvature_group)

        layout.addStretch()

    def _calc_tangent_orientation(self):
        """计算切线方向的机器人姿态"""
        # 获取两点坐标
        x1, y1, z1 = self.tangent_x1.value(), self.tangent_y1.value(), self.tangent_z1.value()
        x2, y2, z2 = self.tangent_x2.value(), self.tangent_y2.value(), self.tangent_z2.value()

        # 计算切线向量
        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist > 0:
            # 单位化切线向量
            dx, dy, dz = dx/dist, dy/dist, dz/dist

            # 计算偏航角 (绕Z轴旋转)
            yaw_deg = math.degrees(math.atan2(dy, dx))

            # 将方向向量转换为UR旋转向量 [rx, ry, rz]
            # 这里简化计算，实际应用中需要更复杂的旋转矩阵计算
            rz = math.atan2(dy, dx)
            ry = math.atan2(-dz, math.sqrt(dx*dx + dy*dy))
            rx = 0  # 简化，假设绕X轴无旋转

            self.tangent_result.setText(f"偏航角: {yaw_deg:.2f}° | UR旋转向量: [{rx:.4f}, {ry:.4f}, {rz:.4f}]")
        else:
            self.tangent_result.setText("错误: 两点重合，无法计算切线")

    def _calc_variable_tilt(self):
        """计算变倾角姿态"""
        tilt_angle = math.radians(self.tilt_angle.value())
        curvature = self.tilt_curvature.value()

        # 绕Y轴旋转的角度
        tilt_around_y = tilt_angle  # 实际应用中可能需要根据曲率调整

        self.tilt_result.setText(f"绕Y轴旋转: {math.degrees(tilt_around_y):.2f}°")

    def _check_min_radius(self):
        """校验最小弯曲半径"""
        current_radius = self.curvature_radius.value()
        min_radius = self.fiber_min_radius.value()

        if current_radius >= min_radius:
            self.radius_result.setText(f"安全: 当前半径 {current_radius}mm ≥ 最小半径 {min_radius}mm")
        else:
            self.radius_result.setText(f"警告: 当前半径 {current_radius}mm < 最小半径 {min_radius}mm，纤维可能断裂!")
