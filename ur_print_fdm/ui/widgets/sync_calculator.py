"""
独立的硬件同步计算器
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel)
from PyQt6.QtCore import pyqtSignal
import math


class SyncCalculatorWidget(QWidget):
    """硬件同步计算器独立组件"""

    def __init__(self, show_only=None):
        """
        初始化计算器
        :param show_only: 如果指定，只显示特定功能 ('turntable')
        """
        super().__init__()
        self.show_only = show_only
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        if self.show_only is None or self.show_only == 'turntable':
            # 转台螺旋同步组
            turntable_group = QGroupBox("转台螺旋同步 (Turntable Spiral Sync)")
            turntable_layout = QFormLayout(turntable_group)

            self.turntable_dist = QDoubleSpinBox(); self.turntable_dist.setRange(0, 10000); self.turntable_dist.setValue(100.0)
            self.turntable_diameter = QDoubleSpinBox(); self.turntable_diameter.setRange(0.1, 1000); self.turntable_diameter.setValue(100.0)
            self.turntable_angle = QDoubleSpinBox(); self.turntable_angle.setRange(0.1, 89.9); self.turntable_angle.setDecimals(1); self.turntable_angle.setValue(45.0)
            self.turntable_ppr = QSpinBox(); self.turntable_ppr.setRange(1, 65535); self.turntable_ppr.setValue(16000)

            btn_calc_turntable = QPushButton("计算转台参数"); btn_calc_turntable.clicked.connect(self._calc_turntable_sync)
            self.turntable_result = QLabel("转盘距离: -- mm | 上升距离: -- mm")
            self.turntable_result2 = QLabel("脉冲数 (BU): -- | 圈数: --")

            turntable_layout.addRow("路径长度 (mm):", self.turntable_dist)
            turntable_layout.addRow("圆筒直径 (mm):", self.turntable_diameter)
            turntable_layout.addRow("螺旋角度 (°):", self.turntable_angle)
            turntable_layout.addRow("每转脉冲数:", self.turntable_ppr)
            turntable_layout.addRow(btn_calc_turntable)
            turntable_layout.addRow(self.turntable_result)
            turntable_layout.addRow(self.turntable_result2)

            layout.addWidget(turntable_group)

        layout.addStretch()

    def _calc_turntable_sync(self):
        """
        计算转台螺旋同步参数

        螺旋展开几何关系:
        - 路径长度 L 是机械臂实际走过的斜边距离
        - 螺旋角度 θ 是展开后上升方向与水平方向的夹角
        - 转盘距离 (水平) = L × cos(θ)
        - 上升距离 (垂直) = L × sin(θ)
        - 圆筒周长 = π × 直径
        - 转盘圈数 = 转盘距离 / 圆筒周长
        - 脉冲数 = 圈数 × 每转脉冲数
        """
        dist = self.turntable_dist.value()  # 路径长度 (斜边)
        diameter = self.turntable_diameter.value()  # 圆筒直径
        angle = self.turntable_angle.value()  # 螺旋角度
        ppr = self.turntable_ppr.value()  # 每转脉冲数

        # 计算圆筒周长
        circumference = math.pi * diameter

        if circumference > 0:
            # 角度转弧度
            angle_rad = math.radians(angle)

            # 分解路径长度
            horizontal_dist = dist * math.cos(angle_rad)  # 转盘转过的距离
            vertical_dist = dist * math.sin(angle_rad)    # 机械臂上升的距离

            # 计算转盘圈数和脉冲数
            turns = horizontal_dist / circumference
            bu = int(round(turns * ppr))

            self.turntable_result.setText(
                f"转盘距离: {horizontal_dist:.2f} mm | 上升距离: {vertical_dist:.2f} mm"
            )
            self.turntable_result2.setText(
                f"脉冲数 (BU): {bu} | 圈数: {turns:.3f}"
            )
        else:
            self.turntable_result.setText("错误: 直径不能为0")
            self.turntable_result2.setText("")
