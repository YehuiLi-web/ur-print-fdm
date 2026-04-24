"""
独立的挤出流量计算器
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox
import math


class ExtrusionCalculatorWidget(QWidget):
    """挤出流量计算器独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('flow')
        """
        super().__init__()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'flow':
            # 基础流量映射组
            flow_group = QGroupBox("基础流量映射 (Flow Rate Mapping)")
            flow_layout = QFormLayout(flow_group)

            # 计算模式选择
            self.calc_mode = FusedComboBox()
            self.calc_mode.setControlHeight(36)
            self.calc_mode.setPopupRowHeight(36)
            self.calc_mode.addItems(["正向: 速度 → 流量", "反向: 流量 → 速度"])
            self.calc_mode.currentIndexChanged.connect(self._on_calc_mode_changed)

            self.extr_fd = QDoubleSpinBox(); self.extr_fd.setRange(0.1, 50.0); self.extr_fd.setDecimals(3); self.extr_fd.setValue(1.75)
            self.extr_lw = QDoubleSpinBox(); self.extr_lw.setRange(0.01, 10.0); self.extr_lw.setDecimals(3); self.extr_lw.setValue(1.0)
            self.extr_lh = QDoubleSpinBox(); self.extr_lh.setRange(0.01, 2.0); self.extr_lh.setDecimals(3); self.extr_lh.setValue(0.5)
            self.extr_spd = QDoubleSpinBox(); self.extr_spd.setRange(0.1, 200.0); self.extr_spd.setDecimals(1); self.extr_spd.setValue(5.0)
            self.extr_base = QSpinBox(); self.extr_base.setRange(0, 999999); self.extr_base.setValue(4000)

            # 反向计算输入框 - 挤出机速度（线材进给速度）
            self.extr_e_speed = QDoubleSpinBox(); self.extr_e_speed.setRange(0.01, 50.0); self.extr_e_speed.setDecimals(3); self.extr_e_speed.setValue(1.0)
            self.extr_e_speed.setEnabled(False)

            # 标签（用于动态更新）
            self.label_spd = QLabel("打印速度 (mm/s):")
            self.label_e_speed = QLabel("挤出机速度 (mm/s):")

            btn_calc_flow = QPushButton("计算"); btn_calc_flow.clicked.connect(self._calc_flow_rate)
            self.extr_result = QLabel("挤出机速度: -- mm/s | 挤出寄存器: --")

            flow_layout.addRow("计算模式:", self.calc_mode)
            flow_layout.addRow("耗材直径 (mm):", self.extr_fd)
            flow_layout.addRow("线宽 (mm):", self.extr_lw)
            flow_layout.addRow("层高 (mm):", self.extr_lh)
            flow_layout.addRow(self.label_spd, self.extr_spd)
            flow_layout.addRow("基准寄存器值:", self.extr_base)
            flow_layout.addRow(self.label_e_speed, self.extr_e_speed)
            flow_layout.addRow(btn_calc_flow)
            flow_layout.addRow(self.extr_result)

            layout.addWidget(flow_group)

        layout.addStretch()

    def _on_calc_mode_changed(self, index):
        """切换计算模式时更新UI状态"""
        is_forward = (index == 0)  # 正向模式

        # 正向模式: 打印速度输入启用，挤出机速度输入禁用
        # 反向模式: 打印速度输入禁用，挤出机速度输入启用
        self.extr_spd.setEnabled(is_forward)
        self.extr_e_speed.setEnabled(not is_forward)

        # 更新结果标签提示
        if is_forward:
            self.extr_result.setText("挤出机速度: -- mm/s | 挤出寄存器: --")
        else:
            self.extr_result.setText("打印速度: -- mm/s")

    def _calc_flow_rate(self):
        """
        双向流量计算
        公式: 打印速度 × 线宽 × 层高 = 挤出机速度 × 线材截面积
        """
        fd = self.extr_fd.value()  # 耗材直径
        lw = self.extr_lw.value()  # 线宽
        lh = self.extr_lh.value()  # 层高
        base_reg = self.extr_base.value()  # 基准寄存器
        filament_area = math.pi * ((fd / 2.0) ** 2)  # 线材截面积
        cross_section = lw * lh  # 打印截面积

        is_forward = (self.calc_mode.currentIndex() == 0)

        if is_forward:
            # 正向计算: 打印速度 → 挤出机速度
            # 挤出机速度 = (打印速度 × 线宽 × 层高) / 线材截面积
            spd = self.extr_spd.value()

            if filament_area > 0:
                e_speed = (spd * cross_section) / filament_area
                if e_speed > 9.99:
                    e_speed = 9.99
                ext_reg = int(base_reg + round(e_speed * 100))
            else:
                e_speed = 0
                ext_reg = base_reg

            self.extr_result.setText(f"挤出机速度: {e_speed:.3f} mm/s | 挤出寄存器: {ext_reg}")
            # 同步更新反向输入框的值
            self.extr_e_speed.setValue(e_speed)
        else:
            # 反向计算: 挤出机速度 → 打印速度
            # 打印速度 = (挤出机速度 × 线材截面积) / (线宽 × 层高)
            e_speed = self.extr_e_speed.value()

            if cross_section > 0:
                spd = (e_speed * filament_area) / cross_section
            else:
                spd = 0

            # 计算对应的寄存器值
            ext_reg = int(base_reg + round(e_speed * 100))

            self.extr_result.setText(f"打印速度: {spd:.2f} mm/s | 挤出寄存器: {ext_reg}")
            # 同步更新正向输入框的值
            self.extr_spd.setValue(spd)
