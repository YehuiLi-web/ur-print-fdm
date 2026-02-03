# ui/widgets/calculator.py
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox,
                             QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton,
                             QLabel, QLineEdit, QTextEdit, QMessageBox, QTabWidget, QComboBox,
                             QCheckBox, QGridLayout)
from PyQt6.QtCore import pyqtSignal
from ur_print_fdm.core.print_lib import URPrintLib
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class CalculatorWidget(QWidget):
    """纤维增强3D打印工艺核心计算器 - 连接模型几何与机器人底层指令"""

    def __init__(self):
        super().__init__()
        self.print_lib = URPrintLib()  # 独立的计算实例
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 主选项卡
        tabs = QTabWidget()

        # 一、挤出与流量控制 (Extrusion & Flow)
        tabs.addTab(self._create_extrusion_tab(), "挤出与流量控制")

        # 二、切线变角度姿态计算 (Tangential & Orientation)
        tabs.addTab(self._create_orientation_tab(), "切线变角度姿态计算")

        # 三、硬件同步与协同 (Hardware Sync)
        tabs.addTab(self._create_sync_tab(), "硬件同步与协同")

        # 四、几何工具与坐标变换 (Geometry & Transform)
        tabs.addTab(self._create_geometry_tab(), "几何工具与坐标变换")

        layout.addWidget(tabs)

    def _create_extrusion_tab(self):
        """创建挤出与流量控制标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

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

        layout.addWidget(flow_group)
        layout.addWidget(fiber_group)
        layout.addWidget(pressure_group)

        return widget

    def _create_orientation_tab(self):
        """创建切线变角度姿态计算标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

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

        layout.addWidget(tangent_group)
        layout.addWidget(tilt_group)
        layout.addWidget(curvature_group)

        return widget

    def _create_sync_tab(self):
        """创建硬件同步与协同标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 转盘螺旋同步组
        turntable_group = QGroupBox("转盘螺旋同步 (Turntable Spiral Sync)")
        turntable_layout = QFormLayout(turntable_group)

        self.turntable_dist = QDoubleSpinBox(); self.turntable_dist.setRange(0, 10000); self.turntable_dist.setValue(100.0)
        self.turntable_circum = QDoubleSpinBox(); self.turntable_circum.setRange(0.1, 1000); self.turntable_circum.setValue(314.16)
        self.turntable_ppr = QSpinBox(); self.turntable_ppr.setRange(1, 65535); self.turntable_ppr.setValue(16000)

        btn_calc_turntable = QPushButton("计算转盘参数"); btn_calc_turntable.clicked.connect(self._calc_turntable_sync)
        self.turntable_result = QLabel("脉冲数 (BU): -- | 速度 (Pin): --")

        turntable_layout.addRow("路径长度 (mm):", self.turntable_dist)
        turntable_layout.addRow("转盘周长 (mm):", self.turntable_circum)
        turntable_layout.addRow("每转脉冲数:", self.turntable_ppr)
        turntable_layout.addRow(btn_calc_turntable)
        turntable_layout.addRow(self.turntable_result)

        # 外部轴坐标映射组
        external_group = QGroupBox("外部轴坐标映射 (External Axis Coord Mapping)")
        external_layout = QFormLayout(external_group)

        self.external_base_x = QDoubleSpinBox(); self.external_base_x.setRange(-1000, 1000); self.external_base_x.setValue(0.0)
        self.external_base_y = QDoubleSpinBox(); self.external_base_y.setRange(-1000, 1000); self.external_base_y.setValue(0.0)
        self.external_rot_offset = QDoubleSpinBox(); self.external_rot_offset.setRange(-360, 360); self.external_rot_offset.setValue(0.0)

        btn_calc_external = QPushButton("计算坐标映射"); btn_calc_external.clicked.connect(self._calc_external_coord)
        self.external_result = QLabel("转盘坐标系下位姿: --")

        external_layout.addRow("基坐标 X (mm):", self.external_base_x)
        external_layout.addRow("基坐标 Y (mm):", self.external_base_y)
        external_layout.addRow("旋转偏置 (°):", self.external_rot_offset)
        external_layout.addRow(btn_calc_external)
        external_layout.addRow(self.external_result)

        # 加热功率预测组
        heat_group = QGroupBox("加热功率预测 (Heating Power Prediction)")
        heat_layout = QFormLayout(heat_group)

        self.heat_speed = QDoubleSpinBox(); self.heat_speed.setRange(0.1, 100); self.heat_speed.setValue(5.0)
        self.heat_material = QComboBox()
        self.heat_material.addItems(["PLA", "ABS", "PETG", "CF-PLA", "GF-PA", "Custom"])
        self.heat_temp = QSpinBox(); self.heat_temp.setRange(150, 300); self.heat_temp.setValue(200)

        btn_calc_heat = QPushButton("预测加热功率"); btn_calc_heat.clicked.connect(self._calc_heating_power)
        self.heat_result = QLabel("喷头功率: --% | 热床功率: --%")

        heat_layout.addRow("打印速度 (mm/s):", self.heat_speed)
        heat_layout.addRow("材料类型:", self.heat_material)
        heat_layout.addRow("目标温度 (°C):", self.heat_temp)
        heat_layout.addRow(btn_calc_heat)
        heat_layout.addRow(self.heat_result)

        layout.addWidget(turntable_group)
        layout.addWidget(external_group)
        layout.addWidget(heat_group)

        return widget

    def _create_geometry_tab(self):
        """创建几何工具与坐标变换标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

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

        # 单位一键转换组
        unit_group = QGroupBox("単位一键转换 (Unit Converter)")
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

        layout.addWidget(offset_group)
        layout.addWidget(tcp_group)
        layout.addWidget(unit_group)

        return widget

    # ====================== 挤出与流量控制计算函数 ======================

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

    # ====================== 切线姿态计算函数 ======================

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

    # ====================== 硬件同步计算函数 ======================

    def _calc_turntable_sync(self):
        """计算转盘同步参数"""
        dist = self.turntable_dist.value()  # 路径长度
        circum = self.turntable_circum.value()  # 转盘周长
        ppr = self.turntable_ppr.value()  # 每转脉冲数

        if circum > 0:
            # 计算需要转动的圈数
            turns = dist / circum
            # 计算总脉冲数
            bu = int(round(turns * ppr))
            # 计算转盘速度 (简化计算)
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

        self.external_result.setText(f"转盘坐标系下位姿: [{rotated_x:.2f}, {rotated_y:.2f}, 0.0, 0, 0, 0]")

    def _calc_heating_power(self):
        """预测加热功率"""
        speed = self.extr_speed.value()
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

    # ====================== 几何变换计算函数 ======================

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
        angle = math.radians(self.tcp_angle.value())

        # 假设TCP在Z轴方向偏移，并考虑倾斜
        tcp_x = length * math.sin(angle)
        tcp_y = 0  # 简化，假设在XZ平面内
        tcp_z = length * math.cos(angle)

        # 角度偏置
        tcp_rx = 0
        tcp_ry = -angle  # 假设倾斜是绕Y轴
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
