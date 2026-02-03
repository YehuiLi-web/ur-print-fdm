"""
独立的硬件同步计算器
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel, QTextEdit, QCheckBox, QGridLayout, QComboBox)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.core.print_lib import URPrintLib
import math
import numpy as np


class SyncCalculatorWidget(QWidget):
    """硬件同步计算器独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('turntable', 'external', 'heat')
        """
        super().__init__()
        self.print_lib = URPrintLib()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'turntable':
            # 转台螺旋同步组
            turntable_group = QGroupBox("转台螺旋同步 (Turntable Spiral Sync)")
            turntable_layout = QFormLayout(turntable_group)

            self.turntable_dist = QDoubleSpinBox(); self.turntable_dist.setRange(0, 10000); self.turntable_dist.setValue(100.0)
            self.turntable_circum = QDoubleSpinBox(); self.turntable_circum.setRange(0.1, 1000); self.turntable_circum.setValue(314.16)
            self.turntable_ppr = QSpinBox(); self.turntable_ppr.setRange(1, 65535); self.turntable_ppr.setValue(16000)

            btn_calc_turntable = QPushButton("计算转台参数"); btn_calc_turntable.clicked.connect(self._calc_turntable_sync)
            self.turntable_result = QLabel("脉冲数 (BU): -- | 速度 (Pin): --")

            turntable_layout.addRow("路径长度 (mm):", self.turntable_dist)
            turntable_layout.addRow("转台周长 (mm):", self.turntable_circum)
            turntable_layout.addRow("每转脉冲数:", self.turntable_ppr)
            turntable_layout.addRow(btn_calc_turntable)
            turntable_layout.addRow(self.turntable_result)

            layout.addWidget(turntable_group)

        if self.show_only is None or self.show_only == 'external':
            # 外部轴坐标映射组
            external_group = QGroupBox("外部轴坐标映射 (External Axis Coord Mapping)")
            external_layout = QFormLayout(external_group)

            self.external_base_x = QDoubleSpinBox(); self.external_base_x.setRange(-1000, 1000); self.external_base_x.setValue(0.0)
            self.external_base_y = QDoubleSpinBox(); self.external_base_y.setRange(-1000, 1000); self.external_base_y.setValue(0.0)
            self.external_rot_offset = QDoubleSpinBox(); self.external_rot_offset.setRange(-360, 360); self.external_rot_offset.setValue(0.0)

            btn_calc_external = QPushButton("计算坐标映射"); btn_calc_external.clicked.connect(self._calc_external_coord)
            self.external_result = QLabel("转台坐标系下位姿: --")

            external_layout.addRow("基坐标 X (mm):", self.external_base_x)
            external_layout.addRow("基坐标 Y (mm):", self.external_base_y)
            external_layout.addRow("旋转偏置 (°):", self.external_rot_offset)
            external_layout.addRow(btn_calc_external)
            external_layout.addRow(self.external_result)

            layout.addWidget(external_group)

        if self.show_only is None or self.show_only == 'heat':
            # 加热功率预测组
            heat_group = QGroupBox("加热功率预测 (Heating Power Prediction)")
            heat_layout = QFormLayout(heat_group)

            self.heat_speed = QDoubleSpinBox(); self.heat_speed.setRange(0.1, 100); self.heat_speed.setValue(5.0)
            self.heat_material = QComboBox(); self.heat_material.addItems(["PLA", "ABS", "PETG", "CF-PLA", "GF-PA", "Custom"])
            self.heat_temp = QSpinBox(); self.heat_temp.setRange(150, 300); self.heat_temp.setValue(200)

            btn_calc_heat = QPushButton("预测加热功率"); btn_calc_heat.clicked.connect(self._calc_heating_power)
            self.heat_result = QLabel("喷头功率: --% | 热床功率: --%")

            heat_layout.addRow("打印速度 (mm/s):", self.heat_speed)
            heat_layout.addRow("材料类型:", self.heat_material)
            heat_layout.addRow("目标温度 (°C):", self.heat_temp)
            heat_layout.addRow(btn_calc_heat)
            heat_layout.addRow(self.heat_result)

            layout.addWidget(heat_group)

        layout.addStretch()

    def _calc_turntable_sync(self):
        """计算转台同步参数"""
        dist = self.turntable_dist.value()  # 路径长度
        circum = self.turntable_circum.value()  # 转台周长
        ppr = self.turntable_ppr.value()  # 每转脉冲数

        if circum > 0:
            # 计算需要转动的圈数
            turns = dist / circum
            # 计算总脉冲数
            bu = int(round(turns * ppr))
            # 计算转台速度 (简化计算)
            pin = 10000 + int(turns * 100)  # 假设正转且速度值

            self.turntable_result.setText(f"脉冲数 (BU): {bu} | 速度 (Pin): {pin}")
        else:
            self.turntable_result.setText("错误: 周长不能为0")

    def _calc_external_coord(self):
        """计算外部轴坐标映射"""
        base_x = self.external_base_x.value()
        base_y = self.external_base_y.value()
        rot_offset = math.radians(self.external_rot_offset.value())

        # 旋转变换
        rotated_x = base_x * math.cos(rot_offset) - base_y * math.sin(rot_offset)
        rotated_y = base_x * math.sin(rot_offset) + base_y * math.cos(rot_offset)

        self.external_result.setText(f"转台坐标系下位姿: [{rotated_x:.2f}, {rotated_y:.2f}, 0.0, 0, 0, 0]")

    def _calc_heating_power(self):
        """预测加热功率"""
        speed = self.heat_speed.value()
        material = self.heat_material.currentText()
        temp = self.heat_temp.value()

        # 简化的功率计算（实际应用中需要更复杂的物理模型）
        if material == "PLA":
            nozzle_power = min(100, max(20, 30 + speed * 0.5))
            bed_power = min(100, max(30, 40 + speed * 0.3))
        elif material == "ABS":
            nozzle_power = min(100, max(40, 50 + speed * 0.4))
            bed_power = min(100, max(50, 60 + speed * 0.3))
        elif material == "CF-PLA":
            nozzle_power = min(100, max(50, 60 + speed * 0.6))
            bed_power = min(100, max(60, 70 + speed * 0.4))
        else:
            # 其他材料或自定义
            nozzle_power = min(100, max(20, 30 + speed * 0.7))
            bed_power = min(100, max(30, 40 + speed * 0.5))

        self.heat_result.setText(f"喷头功率: {nozzle_power:.1f}% | 热床功率: {bed_power:.1f}%")
