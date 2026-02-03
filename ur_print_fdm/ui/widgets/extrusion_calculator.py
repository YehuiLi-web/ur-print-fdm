"""
独立的挤出流量计算器
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel, QTextEdit, QCheckBox, QGridLayout)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.core.print_lib import URPrintLib
import math
import numpy as np


class ExtrusionCalculatorWidget(QWidget):
    """挤出流量计算器独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('flow', 'fiber', 'pressure')
        """
        super().__init__()
        self.print_lib = URPrintLib()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'flow':
            # 基础流量映射组
            flow_group = QGroupBox("基础流量映射 (Flow Rate Mapping)")
            flow_layout = QFormLayout(flow_group)

            self.extr_fd = QDoubleSpinBox(); self.extr_fd.setRange(0.1, 50.0); self.extr_fd.setDecimals(3); self.extr_fd.setValue(1.75)
            self.extr_lw = QDoubleSpinBox(); self.extr_lw.setRange(0.01, 10.0); self.extr_lw.setDecimals(3); self.extr_lw.setValue(1.0)
            self.extr_lh = QDoubleSpinBox(); self.extr_lh.setRange(0.01, 2.0); self.extr_lh.setDecimals(3); self.extr_lh.setValue(0.5)
            self.extr_spd = QDoubleSpinBox(); self.extr_spd.setRange(0.1, 200.0); self.extr_spd.setDecimals(1); self.extr_spd.setValue(5.0)
            self.extr_base = QSpinBox(); self.extr_base.setRange(0, 999999); self.extr_base.setValue(4000)

            btn_calc_flow = QPushButton("计算流量"); btn_calc_flow.clicked.connect(self._calc_flow_rate)
            self.extr_result = QLabel("体积流速: -- mm³/s | 挤出寄存器: --")

            flow_layout.addRow("耗材直径 (mm):", self.extr_fd)
            flow_layout.addRow("线宽 (mm):", self.extr_lw)
            flow_layout.addRow("层高 (mm):", self.extr_lh)
            flow_layout.addRow("打印速度 (mm/s):", self.extr_spd)
            flow_layout.addRow("基准寄存器值:", self.extr_base)
            flow_layout.addRow(btn_calc_flow)
            flow_layout.addRow(self.extr_result)

            layout.addWidget(flow_group)

        if self.show_only is None or self.show_only == 'fiber':
            # 纤维比例补偿组
            fiber_group = QGroupBox("纤维比例补偿 (Fiber-Volume Ratio)")
            fiber_layout = QFormLayout(fiber_group)

            self.fiber_ratio = QDoubleSpinBox(); self.fiber_ratio.setRange(0.0, 1.0); self.fiber_ratio.setDecimals(2); self.fiber_ratio.setValue(0.3)
            self.fiber_multiplier = QDoubleSpinBox(); self.fiber_multiplier.setRange(0.1, 5.0); self.fiber_multiplier.setDecimals(2); self.fiber_multiplier.setValue(1.2)

            btn_calc_fiber = QPushButton("计算纤维补偿"); btn_calc_fiber.clicked.connect(self._calc_fiber_compensation)
            self.fiber_result = QLabel("树脂比例: -- | 补偿系数: --")

            fiber_layout.addRow("纤维体积比:", self.fiber_ratio)
            fiber_layout.addRow("挤出乘数:", self.fiber_multiplier)
            fiber_layout.addRow(btn_calc_fiber)
            fiber_layout.addRow(self.fiber_result)

            layout.addWidget(fiber_group)

        if self.show_only is None or self.show_only == 'pressure':
            # 动态压力补偿组
            pressure_group = QGroupBox("动态压力补偿 (Pressure Advance)")
            pressure_layout = QFormLayout(pressure_group)

            self.pressure_k = QDoubleSpinBox(); self.pressure_k.setRange(0.0, 10.0); self.pressure_k.setDecimals(3); self.pressure_k.setValue(0.05)
            self.pressure_t = QDoubleSpinBox(); self.pressure_t.setRange(0.0, 1.0); self.pressure_t.setDecimals(3); self.pressure_t.setValue(0.05)

            btn_calc_pressure = QPushButton("计算压力补偿"); btn_calc_pressure.clicked.connect(self._calc_pressure_advance)
            self.pressure_result = QLabel("提前量: -- ms")

            pressure_layout.addRow("压力系数 (K):", self.pressure_k)
            pressure_layout.addRow("时间常数 (T):", self.pressure_t)
            pressure_layout.addRow(btn_calc_pressure)
            pressure_layout.addRow(self.pressure_result)

            layout.addWidget(pressure_group)

        layout.addStretch()

    def _calc_flow_rate(self):
        """计算体积流速和挤出寄存器值"""
        fd = self.extr_fd.value()  # 耗材直径
        lw = self.extr_lw.value()  # 线宽
        lh = self.extr_lh.value()  # 层高
        spd = self.extr_spd.value()  # 速度
        base_reg = self.extr_base.value()  # 基准寄存器

        # 体积流速 Q = W * H * V
        vol_flow = lw * lh * spd

        # 挤出寄存器计算
        filament_area = math.pi * ((fd / 2.0) ** 2)
        if filament_area != 0:
            e_speed = vol_flow / filament_area
            if e_speed > 9.99: e_speed = 9.99
            ext_reg = int(base_reg + round(e_speed * 100))
        else:
            ext_reg = base_reg

        self.extr_result.setText(f"体积流速: {vol_flow:.3f} mm³/s | 挤出寄存器: {ext_reg}")

    def _calc_fiber_compensation(self):
        """计算纤维体积比例和补偿系数"""
        ratio = self.fiber_ratio.value()
        mult = self.fiber_multiplier.value()

        resin_ratio = 1.0 - ratio
        compensated_mult = mult * (1 + ratio * 0.2)  # 假设纤维需要额外20%流量

        self.fiber_result.setText(f"树脂比例: {resin_ratio:.2f} | 补偿系数: {compensated_mult:.2f}")

    def _calc_pressure_advance(self):
        """计算动态压力补偿"""
        k = self.pressure_k.value()
        t = self.pressure_t.value()

        # 压力补偿 = K * 加速度 + T * 速度变化
        # 这里简化为一个补偿时间
        advance_time_ms = t * 1000  # 转换为毫秒

        self.pressure_result.setText(f"提前量: {advance_time_ms:.1f} ms")
