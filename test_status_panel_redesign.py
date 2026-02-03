#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UR5 FDM 打印状态监视面板 - UI 重设计测试

项目背景：
- 使用 UR5 机器人进行 FDM（熔融沉积）3D打印
- 数据来源：URDriver.get_status() → TCP位姿、关节角度、TCP偏移、TCP速度
- 挤出控制：Modbus (MODBUS_1) 或数字IO
- 运行模式：生产模式（SFTP+Dashboard）或 直连模式（RTDE）

核心监控需求（按优先级）：
1. 连接状态 - 最重要，影响所有操作
2. TCP位姿 - 打印头实时位置，核心数据
3. TCP速度 - 判断是否在运动/打印
4. 关节角度 - 机器人姿态，用于诊断
5. 打印进度 - 脚本执行进度（可选）
6. 挤出状态 - 是否正在出料（可选）

去除的无用信息：
- 温度监控（项目无温度数据源）
- 打印参数（层高、线宽等是脚本预设，非实时数据）
- 环境温度

运行方法：
    python test_status_panel_redesign.py
"""

import sys
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QToolButton, QProgressBar,
    QGridLayout, QSlider, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


# ============================================================
# 配色方案 - 专业深色主题（精简版）
# ============================================================
class Colors:
    """统一配色 - 只用必要的颜色"""
    # 背景
    BG_WINDOW = "#1e1e1e"
    BG_CARD = "#252526"
    BG_FIELD = "#2d2d30"
    BG_HOVER = "#3c3c3c"
    
    # 边框
    BORDER = "#3c3c3c"
    
    # 文字
    TEXT_PRIMARY = "#e4e4e6"
    TEXT_SECONDARY = "#9d9d9f"
    TEXT_DIM = "#6e6e70"
    
    # 状态色（只用3个）
    ACCENT = "#0078d4"      # 主强调色/正常
    SUCCESS = "#4caf50"     # 成功/已连接
    WARNING = "#ff9800"     # 警告/只读
    DANGER = "#f44336"      # 错误/断开


# ============================================================
# 基础组件
# ============================================================
class ConnectionBadge(QWidget):
    """连接状态徽章 - 圆点 + 状态文字 + 控制权限"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # LED 圆点
        self.led = QLabel()
        self.led.setFixedSize(10, 10)
        layout.addWidget(self.led)
        
        # 状态文字
        self.label = QLabel("未连接")
        self.label.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 9pt;")
        layout.addWidget(self.label)
        
        layout.addStretch()
        
        # 控制权限标签
        self.permission_label = QLabel("")
        self.permission_label.setStyleSheet(f"""
            color: {Colors.TEXT_DIM};
            font-size: 8pt;
            padding: 2px 6px;
            background: {Colors.BG_FIELD};
            border-radius: 3px;
        """)
        self.permission_label.hide()
        layout.addWidget(self.permission_label)
        
        self.set_status("disconnected")
    
    def set_status(self, status: str):
        """设置状态: connected, readonly, disconnected, connecting"""
        config = {
            "disconnected": (Colors.TEXT_DIM, "未连接", ""),
            "connecting":   (Colors.WARNING, "连接中...", ""),
            "connected":    (Colors.SUCCESS, "已连接", "读写"),
            "readonly":     (Colors.WARNING, "已连接", "只读"),
        }
        color, text, perm = config.get(status, config["disconnected"])
        
        self.led.setStyleSheet(f"background: {color}; border-radius: 5px;")
        self.label.setText(text)
        self.label.setStyleSheet(f"color: {color}; font-size: 9pt; font-weight: 500;")
        
        if perm:
            self.permission_label.setText(perm)
            self.permission_label.show()
            perm_color = Colors.SUCCESS if perm == "读写" else Colors.WARNING
            self.permission_label.setStyleSheet(f"""
                color: {perm_color};
                font-size: 8pt;
                padding: 2px 6px;
                background: {Colors.BG_FIELD};
                border-radius: 3px;
            """)
        else:
            self.permission_label.hide()


class TCPPoseCard(QFrame):
    """TCP位姿卡片 - 紧凑的3x2网格布局"""
    
    copy_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        
        self.value_labels = []
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # 标题行
        header = QHBoxLayout()
        title = QLabel("TCP 位姿")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 10pt; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        
        # 复制按钮
        btn_copy = QPushButton("复制")
        btn_copy.setFixedSize(44, 20)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_FIELD};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 3px;
                font-size: 8pt;
            }}
            QPushButton:hover {{ background: {Colors.BG_HOVER}; color: {Colors.TEXT_PRIMARY}; }}
        """)
        btn_copy.clicked.connect(self.copy_requested.emit)
        header.addWidget(btn_copy)
        layout.addLayout(header)
        
        # 数值网格：位置(X/Y/Z) + 姿态(Rx/Ry/Rz)
        grid = QGridLayout()
        grid.setSpacing(4)
        
        # 行1：标签
        for col, (label, unit) in enumerate([("位置", "mm"), ("姿态", "°")]):
            lbl = QLabel(f"{label} ({unit})")
            lbl.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
            grid.addWidget(lbl, 0, col * 3, 1, 3)
        
        # 行2：轴名
        axes = ["X", "Y", "Z", "Rx", "Ry", "Rz"]
        for i, axis in enumerate(axes):
            col = i % 3 + (i // 3) * 3
            row = 1 + (i // 3) * 2
            lbl = QLabel(axis)
            lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, row, col % 3 + (i // 3) * 3)
        
        # 行3：数值
        for i in range(6):
            val_lbl = QLabel("0.000")
            val_lbl.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 10pt;
            """)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col = i % 3 + (i // 3) * 3
            row = 2 + (i // 3) * 2
            grid.addWidget(val_lbl, row, col % 3 + (i // 3) * 3)
            self.value_labels.append(val_lbl)
        
        layout.addLayout(grid)
    
    def update_pose(self, tcp: list):
        """更新TCP位姿 [x,y,z,rx,ry,rz] 单位：m, rad"""
        if not tcp or len(tcp) < 6:
            return
        for i in range(6):
            if i < 3:
                val = tcp[i] * 1000.0  # m → mm
            else:
                val = tcp[i] * 57.2958  # rad → °
            self.value_labels[i].setText(f"{val:.3f}")


class JointBar(QWidget):
    """单个关节显示：名称 + 迷你滑块 + 数值"""
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(22)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 关节名
        self.lbl_name = QLabel(name)
        self.lbl_name.setFixedWidth(22)
        self.lbl_name.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
        layout.addWidget(self.lbl_name)
        
        # 滑块
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-360, 360)
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 3px;
                background: {Colors.BG_FIELD};
                border-radius: 1px;
            }}
            QSlider::handle:horizontal {{
                background: {Colors.ACCENT};
                width: 8px;
                margin: -2px 0;
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.slider, 1)
        
        # 数值
        self.lbl_value = QLabel("0.0°")
        self.lbl_value.setFixedWidth(48)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_value.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 9pt;
        """)
        layout.addWidget(self.lbl_value)
    
    def set_value(self, degrees: float):
        self.lbl_value.setText(f"{degrees:+.1f}°")
        self.slider.setValue(max(-360, min(360, int(degrees))))


class SpeedIndicator(QWidget):
    """TCP速度指示器 - 大号数字 + 进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 数值行
        row = QHBoxLayout()
        lbl_title = QLabel("TCP速度")
        lbl_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        row.addWidget(lbl_title)
        row.addStretch()
        
        self.lbl_value = QLabel("0.0")
        self.lbl_value.setStyleSheet(f"""
            color: {Colors.ACCENT};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 16pt;
            font-weight: bold;
        """)
        row.addWidget(self.lbl_value)
        
        lbl_unit = QLabel("mm/s")
        lbl_unit.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 9pt;")
        row.addWidget(lbl_unit)
        layout.addLayout(row)
        
        # 进度条
        self.bar = QProgressBar()
        self.bar.setRange(0, 500)
        self.bar.setValue(0)
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 2px;
                background: {Colors.BG_FIELD};
            }}
            QProgressBar::chunk {{
                border-radius: 2px;
                background: {Colors.ACCENT};
            }}
        """)
        layout.addWidget(self.bar)
    
    def set_speed(self, mm_per_s: float):
        self.lbl_value.setText(f"{mm_per_s:.1f}")
        self.bar.setValue(min(500, int(mm_per_s)))
        
        # 根据速度变色
        if mm_per_s < 1:
            color = Colors.TEXT_DIM
        elif mm_per_s < 100:
            color = Colors.ACCENT
        else:
            color = Colors.WARNING
        
        self.lbl_value.setStyleSheet(f"""
            color: {color};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 16pt;
            font-weight: bold;
        """)


class CollapsibleSection(QWidget):
    """简洁的可折叠区块"""
    
    def __init__(self, title: str, collapsed: bool = False, parent=None):
        super().__init__(parent)
        self._collapsed = collapsed
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题栏
        self.header = QWidget()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setStyleSheet(f"background: {Colors.BG_FIELD}; border-radius: 4px;")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 5, 8, 5)
        header_layout.setSpacing(6)
        
        self.arrow = QLabel("▼" if not collapsed else "▶")
        self.arrow.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
        self.arrow.setFixedWidth(12)
        header_layout.addWidget(self.arrow)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        main_layout.addWidget(self.header)
        
        # 内容区
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(4)
        self.content.setVisible(not collapsed)
        main_layout.addWidget(self.content)
        
        self.header.mousePressEvent = lambda e: self._toggle()
    
    def _toggle(self):
        self._collapsed = not self._collapsed
        self.content.setVisible(not self._collapsed)
        self.arrow.setText("▶" if self._collapsed else "▼")
    
    def add_widget(self, w):
        self.content_layout.addWidget(w)
    
    def add_layout(self, l):
        self.content_layout.addLayout(l)


# ============================================================
# 主面板：UR5 FDM 打印状态监视
# ============================================================
class UR5StatusPanel(QWidget):
    """UR5 FDM 打印状态面板 - 精简专业版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        self.setMaximumWidth(300)
        
        self.joint_bars = []
        self._tcp_values = [0.0] * 6
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # ====== 1. 连接状态 ======
        self.connection_badge = ConnectionBadge()
        layout.addWidget(self.connection_badge)
        
        # ====== 2. TCP位姿 ======
        self.tcp_card = TCPPoseCard()
        self.tcp_card.copy_requested.connect(self._copy_tcp)
        layout.addWidget(self.tcp_card)
        
        # ====== 3. 运动状态（速度 + 动作） ======
        motion_card = QFrame()
        motion_card.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_CARD};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """)
        motion_layout = QVBoxLayout(motion_card)
        motion_layout.setContentsMargins(12, 10, 12, 10)
        motion_layout.setSpacing(8)
        
        self.speed_indicator = SpeedIndicator()
        motion_layout.addWidget(self.speed_indicator)
        
        # 运动状态行
        state_row = QHBoxLayout()
        lbl_state_title = QLabel("状态")
        lbl_state_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        state_row.addWidget(lbl_state_title)
        state_row.addStretch()
        
        self.lbl_motion_state = QLabel("静止")
        self.lbl_motion_state.setStyleSheet(f"""
            color: {Colors.SUCCESS};
            font-size: 9pt;
            font-weight: 500;
            padding: 2px 8px;
            background: rgba(76, 175, 80, 0.15);
            border-radius: 3px;
        """)
        state_row.addWidget(self.lbl_motion_state)
        motion_layout.addLayout(state_row)
        
        layout.addWidget(motion_card)
        
        # ====== 4. 关节角度（可折叠） ======
        self.joints_section = CollapsibleSection("关节角度", collapsed=False)
        for i in range(6):
            bar = JointBar(f"J{i+1}")
            self.joints_section.add_widget(bar)
            self.joint_bars.append(bar)
        layout.addWidget(self.joints_section)
        
        # ====== 5. 打印进度（可折叠，默认折叠） ======
        self.print_section = CollapsibleSection("打印进度", collapsed=True)
        
        # 进度条
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        
        progress_row = QHBoxLayout()
        self.lbl_progress_title = QLabel("执行进度")
        self.lbl_progress_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        progress_row.addWidget(self.lbl_progress_title)
        progress_row.addStretch()
        
        self.lbl_progress_percent = QLabel("0%")
        self.lbl_progress_percent.setStyleSheet(f"""
            color: {Colors.ACCENT};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 11pt;
            font-weight: bold;
        """)
        progress_row.addWidget(self.lbl_progress_percent)
        progress_layout.addLayout(progress_row)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 3px;
                background: {Colors.BG_FIELD};
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background: {Colors.ACCENT};
            }}
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.print_section.add_layout(progress_layout)
        
        # 时间信息
        time_row = QHBoxLayout()
        time_row.setSpacing(16)
        
        # 已运行
        elapsed_col = QVBoxLayout()
        lbl_e_title = QLabel("已运行")
        lbl_e_title.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
        elapsed_col.addWidget(lbl_e_title)
        self.lbl_elapsed = QLabel("--:--")
        self.lbl_elapsed.setStyleSheet(f"""
            color: {Colors.SUCCESS};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 10pt;
        """)
        elapsed_col.addWidget(self.lbl_elapsed)
        time_row.addLayout(elapsed_col)
        
        # 剩余
        remain_col = QVBoxLayout()
        lbl_r_title = QLabel("剩余")
        lbl_r_title.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
        remain_col.addWidget(lbl_r_title)
        self.lbl_remain = QLabel("--:--")
        self.lbl_remain.setStyleSheet(f"""
            color: {Colors.WARNING};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 10pt;
        """)
        remain_col.addWidget(self.lbl_remain)
        time_row.addLayout(remain_col)
        
        time_row.addStretch()
        self.print_section.add_layout(time_row)
        
        layout.addWidget(self.print_section)
        
        # ====== 6. 挤出状态（可折叠，默认折叠） ======
        self.extrusion_section = CollapsibleSection("挤出状态", collapsed=True)
        
        ext_row = QHBoxLayout()
        lbl_ext_title = QLabel("Modbus 输出")
        lbl_ext_title.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        ext_row.addWidget(lbl_ext_title)
        ext_row.addStretch()
        
        self.lbl_extrusion_state = QLabel("停止")
        self.lbl_extrusion_state.setStyleSheet(f"""
            color: {Colors.TEXT_DIM};
            font-size: 9pt;
            font-weight: 500;
            padding: 2px 8px;
            background: {Colors.BG_FIELD};
            border-radius: 3px;
        """)
        ext_row.addWidget(self.lbl_extrusion_state)
        self.extrusion_section.add_layout(ext_row)
        
        # Modbus 值显示
        modbus_row = QHBoxLayout()
        lbl_modbus_title = QLabel("寄存器值")
        lbl_modbus_title.setStyleSheet(f"color: {Colors.TEXT_DIM}; font-size: 8pt;")
        modbus_row.addWidget(lbl_modbus_title)
        modbus_row.addStretch()
        
        self.lbl_modbus_value = QLabel("0")
        self.lbl_modbus_value.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 9pt;
        """)
        modbus_row.addWidget(self.lbl_modbus_value)
        self.extrusion_section.add_layout(modbus_row)
        
        layout.addWidget(self.extrusion_section)
        
        # 弹簧
        layout.addStretch()
    
    def _copy_tcp(self):
        """复制TCP位姿到剪贴板（URScript格式）"""
        try:
            # 转换回 m 和 rad
            values = []
            for i, v in enumerate(self._tcp_values):
                if i < 3:
                    values.append(v / 1000.0)  # mm → m
                else:
                    values.append(v / 57.2958)  # ° → rad
            
            pose_str = f"p[{values[0]:.6f}, {values[1]:.6f}, {values[2]:.6f}, {values[3]:.6f}, {values[4]:.6f}, {values[5]:.6f}]"
            
            clipboard = QApplication.clipboard()
            clipboard.setText(pose_str)
        except Exception as e:
            print(f"复制失败: {e}")
    
    # ============================================================
    # 公共接口（与 URDriver 数据对接）
    # ============================================================
    
    def set_connection_status(self, status: str):
        """设置连接状态: connected, readonly, disconnected, connecting"""
        self.connection_badge.set_status(status)
    
    def update_status(self, tcp: list, joints: list, offset: list, speed: float):
        """
        主更新接口 - 与 URDriver.get_status() 返回值对接
        
        Args:
            tcp: [x, y, z, rx, ry, rz] 单位：m, rad
            joints: [j1, j2, j3, j4, j5, j6] 单位：rad
            offset: [x, y, z, rx, ry, rz] 单位：m, rad（本面板暂不显示）
            speed: TCP速度模长 单位：m/s
        """
        # 更新 TCP 位姿
        if tcp and len(tcp) >= 6:
            self.tcp_card.update_pose(tcp)
            # 保存用于复制
            for i in range(6):
                if i < 3:
                    self._tcp_values[i] = tcp[i] * 1000.0
                else:
                    self._tcp_values[i] = tcp[i] * 57.2958
        
        # 更新关节角度
        if joints and len(joints) >= 6:
            for i in range(6):
                deg = joints[i] * 57.2958
                self.joint_bars[i].set_value(deg)
        
        # 更新 TCP 速度
        speed_mm = speed * 1000.0 if speed else 0.0
        self.speed_indicator.set_speed(speed_mm)
        
        # 更新运动状态
        if speed_mm > 10:
            self.set_motion_state("运动中")
        elif speed_mm > 1:
            self.set_motion_state("低速")
        else:
            self.set_motion_state("静止")
    
    def set_motion_state(self, state: str):
        """设置运动状态：静止、低速、运动中、打印中"""
        styles = {
            "静止":   (Colors.SUCCESS, "rgba(76, 175, 80, 0.15)"),
            "低速":   (Colors.ACCENT, "rgba(0, 120, 212, 0.15)"),
            "运动中": (Colors.ACCENT, "rgba(0, 120, 212, 0.15)"),
            "打印中": (Colors.WARNING, "rgba(255, 152, 0, 0.15)"),
            "错误":   (Colors.DANGER, "rgba(244, 67, 54, 0.15)"),
        }
        color, bg = styles.get(state, styles["静止"])
        self.lbl_motion_state.setText(state)
        self.lbl_motion_state.setStyleSheet(f"""
            color: {color};
            font-size: 9pt;
            font-weight: 500;
            padding: 2px 8px;
            background: {bg};
            border-radius: 3px;
        """)
    
    def set_print_progress(self, percent: float, elapsed: str = None, remain: str = None):
        """设置打印进度"""
        self.progress_bar.setValue(int(percent))
        self.lbl_progress_percent.setText(f"{percent:.1f}%")
        if elapsed:
            self.lbl_elapsed.setText(elapsed)
        if remain:
            self.lbl_remain.setText(remain)
    
    def set_extrusion_state(self, active: bool, modbus_value: int = 0):
        """设置挤出状态"""
        if active:
            self.lbl_extrusion_state.setText("出料中")
            self.lbl_extrusion_state.setStyleSheet(f"""
                color: {Colors.WARNING};
                font-size: 9pt;
                font-weight: 500;
                padding: 2px 8px;
                background: rgba(255, 152, 0, 0.15);
                border-radius: 3px;
            """)
        else:
            self.lbl_extrusion_state.setText("停止")
            self.lbl_extrusion_state.setStyleSheet(f"""
                color: {Colors.TEXT_DIM};
                font-size: 9pt;
                font-weight: 500;
                padding: 2px 8px;
                background: {Colors.BG_FIELD};
                border-radius: 3px;
            """)
        self.lbl_modbus_value.setText(str(modbus_value))


# ============================================================
# 测试窗口
# ============================================================
class TestWindow(QMainWindow):
    """测试窗口 - 模拟 UR5 FDM 打印数据"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR5 FDM 状态面板测试")
        self.setMinimumSize(550, 700)
        self.resize(550, 720)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 状态面板
        self.panel = UR5StatusPanel()
        layout.addWidget(self.panel)
        
        # 控制面板
        ctrl = self._create_control_panel()
        layout.addWidget(ctrl)
        
        # 模拟定时器
        self.sim_timer = QTimer()
        self.sim_timer.timeout.connect(self._simulate)
        self._sim_t = 0
        self._sim_running = False
        self._sim_printing = False
        
        self.setStyleSheet(f"background: {Colors.BG_WINDOW};")
    
    def _create_control_panel(self):
        panel = QFrame()
        panel.setFixedWidth(200)
        panel.setStyleSheet(f"background: {Colors.BG_CARD}; border-left: 1px solid {Colors.BORDER};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        title = QLabel("测试控制")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 11pt; font-weight: bold;")
        layout.addWidget(title)
        
        # 连接状态
        lbl = QLabel("连接状态")
        lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt; margin-top: 8px;")
        layout.addWidget(lbl)
        
        for status, text in [
            ("disconnected", "未连接"),
            ("connecting", "连接中"),
            ("connected", "已连接(读写)"),
            ("readonly", "已连接(只读)"),
        ]:
            btn = self._make_btn(text)
            btn.clicked.connect(lambda _, s=status: self.panel.set_connection_status(s))
            layout.addWidget(btn)
        
        # 分隔
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {Colors.BORDER};")
        layout.addWidget(sep)
        
        # 模拟控制
        lbl2 = QLabel("数据模拟")
        lbl2.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 9pt;")
        layout.addWidget(lbl2)
        
        self.btn_sim = self._make_btn("▶ 开始模拟", Colors.SUCCESS)
        self.btn_sim.clicked.connect(self._toggle_sim)
        layout.addWidget(self.btn_sim)
        
        self.btn_print = self._make_btn("开始打印模拟")
        self.btn_print.clicked.connect(self._toggle_print)
        layout.addWidget(self.btn_print)
        
        # 挤出控制
        ext_row = QHBoxLayout()
        btn_ext_on = self._make_btn("挤出开")
        btn_ext_on.clicked.connect(lambda: self.panel.set_extrusion_state(True, 1000))
        btn_ext_off = self._make_btn("挤出关")
        btn_ext_off.clicked.connect(lambda: self.panel.set_extrusion_state(False, 0))
        ext_row.addWidget(btn_ext_on)
        ext_row.addWidget(btn_ext_off)
        layout.addLayout(ext_row)
        
        layout.addStretch()
        return panel
    
    def _make_btn(self, text, color=None):
        btn = QPushButton(text)
        if color:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-weight: bold;
                }}
                QPushButton:hover {{ background: {color}cc; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.BG_FIELD};
                    color: {Colors.TEXT_PRIMARY};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 4px;
                    padding: 6px;
                }}
                QPushButton:hover {{ background: {Colors.BG_HOVER}; }}
            """)
        return btn
    
    def _toggle_sim(self):
        self._sim_running = not self._sim_running
        if self._sim_running:
            self.btn_sim.setText("■ 停止模拟")
            self.btn_sim.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.DANGER};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-weight: bold;
                }}
            """)
            self.panel.set_connection_status("connected")
            self.sim_timer.start(50)
        else:
            self.btn_sim.setText("▶ 开始模拟")
            self.btn_sim.setStyleSheet(f"""
                QPushButton {{
                    background: {Colors.SUCCESS};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-weight: bold;
                }}
            """)
            self.sim_timer.stop()
    
    def _toggle_print(self):
        self._sim_printing = not self._sim_printing
        if self._sim_printing:
            self.btn_print.setText("停止打印模拟")
            self.panel.set_motion_state("打印中")
            self.panel.set_extrusion_state(True, 800)
        else:
            self.btn_print.setText("开始打印模拟")
            self.panel.set_extrusion_state(False, 0)
    
    def _simulate(self):
        self._sim_t += 0.05
        t = self._sim_t
        
        # 模拟 TCP（单位：m, rad）
        tcp = [
            0.3 + 0.05 * math.sin(t * 0.5),
            0.15 + 0.05 * math.cos(t * 0.5),
            0.12 + 0.02 * math.sin(t * 0.3),
            math.pi / 2 + 0.1 * math.sin(t),
            0.1 * math.cos(t),
            0.05 * math.sin(t * 2),
        ]
        
        # 模拟关节（单位：rad）
        joints = [
            math.sin(t * 0.3) * 1.2,
            -math.pi / 4 + math.sin(t * 0.2) * 0.3,
            math.pi / 3 + math.cos(t * 0.25) * 0.2,
            math.sin(t * 0.4) * 0.5,
            math.cos(t * 0.35) * 0.4,
            t * 0.1,
        ]
        
        # 模拟速度（单位：m/s）
        if self._sim_printing:
            speed = 0.03 + 0.01 * abs(math.sin(t))  # 30-40 mm/s 打印速度
        else:
            speed = 0.05 + 0.03 * abs(math.sin(t * 0.5))  # 50-80 mm/s 移动速度
        
        # 调用面板更新
        self.panel.update_status(tcp, joints, None, speed)
        
        # 模拟打印进度
        if self._sim_printing:
            progress = (t % 60) / 60 * 100
            elapsed_s = int(t)
            remain_s = max(0, 60 - int(t % 60))
            self.panel.set_print_progress(
                progress,
                f"{elapsed_s // 60:02d}:{elapsed_s % 60:02d}",
                f"{remain_s // 60:02d}:{remain_s % 60:02d}"
            )
            
            # 模拟挤出值变化
            modbus_val = int(500 + 300 * math.sin(t * 2))
            self.panel.set_extrusion_state(True, modbus_val)


def main():
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
