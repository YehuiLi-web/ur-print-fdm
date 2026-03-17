import math
import time
import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
                             QLabel, QGridLayout, QPushButton, QListWidget, QTextEdit,
                             QMessageBox, QApplication, QTabWidget, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QProgressBar, QLineEdit, QSplitter, QFrame,
                             QToolButton)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt

from ur_print_fdm.shared.connection_state import ChannelState
from ur_print_fdm.ui.mixins.theme_aware import ThemeAwareMixin
from ur_print_fdm.ui.style_factory import StyleFactory


# ================= 手动标定面板类 =================
class ManualCalibrationWidget(QWidget, ThemeAwareMixin):
    """手动标定 - 用户手动移动机械臂到各点采集"""
    
    def __init__(self, main_window):
        super().__init__()
        self.setup_theme_awareness()
        self.main = main_window
        self.points = []
        self.o_idx = -1
        self.x_idx = -1
        self.y_idx = -1
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)

        # 左栏
        left_panel = QWidget()
        left_vbox = QVBoxLayout(left_panel)
        self.grp_live = QGroupBox("实时 TCP (Base)")
        self.grp_live.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {self.get_token('success')}; }}")
        live_layout = QFormLayout()
        self.lbl_tcp_pos = QLabel("Pos: 0, 0, 0")
        self.lbl_tcp_rot = QLabel("Rot: 0, 0, 0")
        live_layout.addRow(self.lbl_tcp_pos)
        live_layout.addRow(self.lbl_tcp_rot)
        self.grp_live.setLayout(live_layout)
        left_vbox.addWidget(self.grp_live)

        grp_keys = QGroupBox("关键点采集")
        grid = QGridLayout()
        btn_o = QPushButton("采集 原点 (O)")
        btn_o.clicked.connect(lambda: self.capture_point('O'))
        btn_x = QPushButton("采集 X轴方向 (X)")
        btn_x.clicked.connect(lambda: self.capture_point('X'))
        btn_y = QPushButton("采集 Y轴方向 (Y)")
        btn_y.clicked.connect(lambda: self.capture_point('Y'))
        btn_add = QPushButton("采集 辅助点 (+)")
        btn_add.clicked.connect(lambda: self.capture_point('Extra'))
        grid.addWidget(btn_o, 0, 0)
        grid.addWidget(btn_x, 0, 1)
        grid.addWidget(btn_y, 1, 0)
        grid.addWidget(btn_add, 1, 1)
        grp_keys.setLayout(grid)
        left_vbox.addWidget(grp_keys)

        grp_list = QGroupBox("采集记录")
        v_list = QVBoxLayout()
        self.pt_list_widget = QListWidget()
        btn_clear = QPushButton("清空所有点")
        btn_clear.clicked.connect(self.clear_points)
        v_list.addWidget(self.pt_list_widget)
        v_list.addWidget(btn_clear)
        grp_list.setLayout(v_list)
        left_vbox.addWidget(grp_list)
        left_vbox.addStretch()
        layout.addWidget(left_panel, 1)

        # 右栏
        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        grp_res = QGroupBox("计算结果")
        v_res = QVBoxLayout()
        self.btn_calc = QPushButton("拟合平面 & 计算 Feature")
        self.btn_calc.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_calc.clicked.connect(self.do_calculate)
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setPlaceholderText("采集至少3个点 (O, X, Y) 后点击计算...")
        v_res.addWidget(self.btn_calc)
        v_res.addWidget(self.txt_result)
        grp_res.setLayout(v_res)
        right_vbox.addWidget(grp_res)
        layout.addWidget(right_panel, 2)

    def on_theme_changed(self, theme_id: str):
        if hasattr(self, 'grp_live'):
            self.grp_live.setStyleSheet(f"QGroupBox {{ font-weight: bold; color: {self.get_token('success')}; }}")
        if hasattr(self, 'btn_calc'):
            self.btn_calc.setStyleSheet(StyleFactory.get_style("button_accent"))

    def update_live_tcp(self, tcp, joints):
        if tcp:
            self.lbl_tcp_pos.setText(f"Pos: {tcp[0]*1000:.3f}, {tcp[1]*1000:.3f}, {tcp[2]*1000:.3f} mm")
            self.lbl_tcp_rot.setText(f"Rot: {tcp[3]:.3f}, {tcp[4]:.3f}, {tcp[5]:.3f} rad")
        else:
            self.lbl_tcp_pos.setText("数据无效")

    def capture_point(self, p_type):
        if not self.main.driver.is_connected():
            QMessageBox.warning(self, "警告", "请先连接机器人！")
            return
        tcp, _, _, _ = self.main.driver.get_status()
        if not tcp:
            return
        p_mm = [tcp[0]*1000, tcp[1]*1000, tcp[2]*1000]
        idx = len(self.points)
        label = ""
        if p_type == 'O':
            self.o_idx = idx
            label = "🔵 原点 (O)"
        elif p_type == 'X':
            self.x_idx = idx
            label = "X轴向 (X)"
        elif p_type == 'Y':
            self.y_idx = idx
            label = "Y轴向 (Y)"
        else:
            label = f"辅助点 {idx+1}"
        self.points.append(p_mm)
        self.pt_list_widget.addItem(f"{label}: {p_mm[0]:.3f}, {p_mm[1]:.3f}, {p_mm[2]:.3f}")

    def clear_points(self):
        self.points = []
        self.pt_list_widget.clear()
        self.txt_result.clear()
        self.o_idx = -1
        self.x_idx = -1
        self.y_idx = -1

    def do_calculate(self):
        if self.o_idx == -1 or self.x_idx == -1 or self.y_idx == -1:
            QMessageBox.warning(self, "数据不足", "必须至少采集 O, X, Y 三个关键点！")
            return
        ordered_points = [self.points[self.o_idx], self.points[self.x_idx], self.points[self.y_idx]]
        for i, p in enumerate(self.points):
            if i not in [self.o_idx, self.x_idx, self.y_idx]:
                ordered_points.append(p)
        feat_str, log = self.main.print_lib.fit_plane_feature(ordered_points)
        if feat_str:
            self.txt_result.setText("计算成功!\n\n" + log)
            self.txt_result.append("\n=== URScript 代码 ===")
            self.txt_result.append(f"global feature1 = {feat_str}")
            QApplication.clipboard().setText(feat_str)
            self.main.log("标定成功，Feature 字符串已复制到剪贴板。")
        else:
            self.txt_result.setText("计算失败\n" + log)


# ================= 自动标定配置 =================
@dataclass
class AutoCalibrationConfig:
    """自动标定配置参数"""
    contact_force_threshold: float = 3.0    # 接触力阈值 (N)
    approach_speed: float = 0.005           # 探测速度 (m/s)
    approach_accel: float = 0.05            # 加速度 (m/s²)
    max_approach_distance: float = 0.1      # 最大探测距离 (m)
    retract_distance: float = 0.02          # 接触后回退距离 (m)
    probe_repeat_count: int = 3             # 每点重复测量次数
    force_stable_threshold: float = 0.5     # 力稳定判定阈值 (N)
    force_stable_duration: float = 0.2      # 力稳定持续时间 (s)
    settle_time: float = 0.3                # 接触后稳定等待时间 (s)
    z_offset: float = 0.0                   # Z 偏移补偿 (m)
    simulate_mode: bool = False             # URSim 模拟模式
    simulate_contact_z: float = 0.0         # 模拟接触 Z 高度 (m)


# ================= 探测工作线程 =================
class ProbeWorker(QThread):
    """探测工作线程"""
    progress = pyqtSignal(str)  # 进度信息
    finished_probe = pyqtSignal(bool, list, float, str)  # success, pose, force, error_msg
    
    def __init__(self, driver, config: AutoCalibrationConfig):
        super().__init__()
        self.driver = driver
        self.config = config
        self._stop_flag = False
    
    def stop(self):
        self._stop_flag = True

    def _sleep_with_stop(self, duration: float, step: float = 0.02) -> bool:
        end_time = time.time() + max(0.0, duration)
        while time.time() < end_time:
            if self._stop_flag:
                return False
            time.sleep(min(step, max(0.0, end_time - time.time())))
        return not self._stop_flag

    def _sample_force_baseline(self, sample_count: int = 10, sample_interval: float = 0.02):
        samples = []
        deadline = time.time() + 2.0
        while len(samples) < sample_count and time.time() < deadline and not self._stop_flag:
            force = self.driver.get_tcp_force()
            if force is not None:
                samples.append(force[2])
            time.sleep(sample_interval)
        if len(samples) < max(3, sample_count // 2):
            return None
        return float(np.mean(samples)), float(max(samples) - min(samples))
    
    def run(self):
        cfg = self.config
        
        # 获取当前位置
        start_pose = self.driver.get_tcp_pose()
        if not start_pose:
            self.finished_probe.emit(False, [], 0.0, "无法获取当前位置")
            return
        
        self.progress.emit(f"开始探测，起始 Z = {start_pose[2]*1000:.1f} mm")

        baseline_fz = 0.0
        if not cfg.simulate_mode:
            baseline = self._sample_force_baseline()
            if baseline is None:
                self.finished_probe.emit(False, [], 0.0, "无法读取稳定的起始力基线")
                return
            baseline_fz, baseline_span = baseline
            self.progress.emit(f"起始力基线: Fz = {baseline_fz:.2f} N")
            if baseline_span > max(cfg.force_stable_threshold * 2.0, 1.0):
                self.progress.emit(f"警告: 起始力波动较大 ({baseline_span:.2f} N)")
        
        t0 = time.time()
        timeout = 60.0
        
        try:
            speed_vec = [0, 0, -cfg.approach_speed, 0, 0, 0]
            
            while time.time() - t0 < timeout and not self._stop_flag:
                force = self.driver.get_tcp_force()
                current_pose = self.driver.get_tcp_pose()
                
                if force is None or current_pose is None:
                    time.sleep(0.008)
                    continue
                
                fz = force[2]
                current_z = current_pose[2]
                
                # 检查是否已经移动太远
                moved_distance = start_pose[2] - current_z
                if moved_distance >= cfg.max_approach_distance:
                    self.driver.speed_stop()
                    self.finished_probe.emit(False, [], 0.0, f"已移动 {moved_distance*1000:.1f} mm，未检测到接触")
                    return
                
                # 接触检测
                contact_detected = False
                if cfg.simulate_mode:
                    if current_z <= cfg.simulate_contact_z:
                        contact_detected = True
                else:
                    if abs(fz - baseline_fz) > cfg.contact_force_threshold:
                        contact_detected = True
                
                if contact_detected:
                    self.driver.speed_stop()
                    self.progress.emit(f"检测到接触，等待稳定...")
                    if not self._sleep_with_stop(cfg.settle_time):
                        self.finished_probe.emit(False, [], 0.0, "用户取消")
                        return
                    
                    # 等待力稳定
                    stable_pose = self._wait_for_force_stable()
                    if stable_pose is None:
                        stable_pose = self.driver.get_tcp_pose()
                    if stable_pose is None:
                        self.finished_probe.emit(False, [], 0.0, "接触后无法读取稳定位置")
                        return
                    
                    stable_force = self.driver.get_tcp_force()
                    contact_fz = (stable_force[2] if stable_force else fz) - baseline_fz
                    
                    # 应用 Z 偏移补偿
                    if cfg.z_offset != 0:
                        stable_pose[2] += cfg.z_offset
                    
                    self.finished_probe.emit(True, stable_pose, contact_fz, "")
                    return
                
                # 发送速度命令
                if not self.driver.speed_l(speed_vec, cfg.approach_accel, 0.1):
                    try:
                        self.driver.speed_stop()
                    except Exception:
                        pass
                    self.finished_probe.emit(False, [], 0.0, "控制命令发送失败")
                    return
                time.sleep(0.008)
            
            self.driver.speed_stop()
            if self._stop_flag:
                self.finished_probe.emit(False, [], 0.0, "用户取消")
            else:
                self.finished_probe.emit(False, [], 0.0, "探测超时")
                
        except Exception as e:
            try:
                self.driver.speed_stop()
            except:
                pass
            self.finished_probe.emit(False, [], 0.0, f"探测异常: {e}")
    
    def _wait_for_force_stable(self, timeout: float = 2.0) -> Optional[List[float]]:
        cfg = self.config
        t0 = time.time()
        force_history = []
        
        while time.time() - t0 < timeout and not self._stop_flag:
            force = self.driver.get_tcp_force()
            if force is not None:
                force_history.append((time.time(), force[2]))
                recent = [(t, f) for t, f in force_history if time.time() - t < cfg.force_stable_duration]
                if len(recent) >= 5:
                    forces = [f for _, f in recent]
                    if max(forces) - min(forces) < cfg.force_stable_threshold:
                        return self.driver.get_tcp_pose()
            time.sleep(0.02)
        return None


# ================= 自动标定面板类 =================
class AutoCalibrationWidget(QWidget, ThemeAwareMixin):
    """自动标定 - 力控探测法"""
    
    def __init__(self, main_window):
        super().__init__()
        self.setup_theme_awareness()
        self.main = main_window
        self.config = AutoCalibrationConfig()
        self.calibration_points: List[List[float]] = []  # [[x,y,z], ...]
        self.probe_worker: Optional[ProbeWorker] = None
        self.reference_indices: Dict[str, Optional[int]] = {"origin": None, "x": None, "y": None}
        self._last_feature: Optional[str] = None
        self._batch_cancelled = False
        self._pending_capture_role: Optional[str] = None
        self._init_ui()

        self._next_probe_timer = QTimer(self)
        self._next_probe_timer.setSingleShot(True)
        self._next_probe_timer.timeout.connect(self._start_next_probe)
        
        # 实时更新定时器
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_live_display)
        self.update_timer.start(100)  # 10Hz
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        card_tcp = QFrame()
        card_tcp.setObjectName("autoCalCard")
        tcp_layout = QVBoxLayout(card_tcp)
        tcp_layout.setContentsMargins(14, 12, 14, 12)
        tcp_layout.setSpacing(4)
        lbl_tcp_title = QLabel("TCP (Base)")
        lbl_tcp_title.setObjectName("autoCalCaption")
        tcp_layout.addWidget(lbl_tcp_title)
        self.lbl_tcp_xyz = QLabel("X --.--   Y --.--   Z --.-- mm")
        self.lbl_tcp_xyz.setObjectName("autoCalMono")
        tcp_layout.addWidget(self.lbl_tcp_xyz)
        self.lbl_tcp_rot = QLabel("Rx --.--   Ry --.--   Rz --.-- rad")
        self.lbl_tcp_rot.setObjectName("autoCalMono")
        tcp_layout.addWidget(self.lbl_tcp_rot)
        status_row.addWidget(card_tcp, 3)

        card_force = QFrame()
        card_force.setObjectName("autoCalCard")
        force_layout = QVBoxLayout(card_force)
        force_layout.setContentsMargins(14, 12, 14, 12)
        force_layout.setSpacing(4)
        lbl_force_title = QLabel("接触力")
        lbl_force_title.setObjectName("autoCalCaption")
        force_layout.addWidget(lbl_force_title)
        self.lbl_force = QLabel("Fz -- N")
        self.lbl_force.setObjectName("autoCalMetric")
        force_layout.addWidget(self.lbl_force)
        force_layout.addStretch()
        status_row.addWidget(card_force, 1)

        card_refs = QFrame()
        card_refs.setObjectName("autoCalCard")
        ref_card_layout = QVBoxLayout(card_refs)
        ref_card_layout.setContentsMargins(14, 12, 14, 12)
        ref_card_layout.setSpacing(4)
        lbl_ref_title = QLabel("参考点")
        lbl_ref_title.setObjectName("autoCalCaption")
        ref_card_layout.addWidget(lbl_ref_title)
        self.lbl_reference_summary = QLabel("O -- | X -- | Y --")
        self.lbl_reference_summary.setObjectName("autoCalMono")
        ref_card_layout.addWidget(self.lbl_reference_summary)
        self.lbl_next_step = QLabel("下一步: 采原点")
        self.lbl_next_step.setObjectName("autoCalStep")
        ref_card_layout.addWidget(self.lbl_next_step)
        status_row.addWidget(card_refs, 2)

        layout.addLayout(status_row)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        # === 左栏：采点工作区 ===
        left_panel = QWidget()
        left_vbox = QVBoxLayout(left_panel)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(12)

        grp_probe = QGroupBox("采点")
        grp_probe.setObjectName("autoCalSection")
        probe_layout = QVBoxLayout()
        probe_layout.setSpacing(10)

        params_grid = QGridLayout()
        params_grid.setHorizontalSpacing(10)
        params_grid.setVerticalSpacing(8)

        self.spin_force_threshold = QDoubleSpinBox()
        self.spin_force_threshold.setRange(0.5, 20.0)
        self.spin_force_threshold.setValue(self.config.contact_force_threshold)
        self.spin_force_threshold.setSuffix(" N")
        self.spin_force_threshold.setToolTip("接触力阈值，超过此值判定为接触")
        params_grid.addWidget(QLabel("阈值"), 0, 0)
        params_grid.addWidget(self.spin_force_threshold, 0, 1)

        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(1.0, 20.0)
        self.spin_speed.setValue(self.config.approach_speed * 1000)
        self.spin_speed.setSuffix(" mm/s")
        self.spin_speed.setToolTip("探测下降速度")
        params_grid.addWidget(QLabel("速度"), 0, 2)
        params_grid.addWidget(self.spin_speed, 0, 3)

        self.spin_repeat = QSpinBox()
        self.spin_repeat.setRange(1, 10)
        self.spin_repeat.setValue(self.config.probe_repeat_count)
        self.spin_repeat.setToolTip("每点重复测量次数，取平均值")
        params_grid.addWidget(QLabel("重复"), 1, 0)
        params_grid.addWidget(self.spin_repeat, 1, 1)

        self.spin_z_offset = QDoubleSpinBox()
        self.spin_z_offset.setRange(-50.0, 50.0)
        self.spin_z_offset.setValue(self.config.z_offset * 1000)
        self.spin_z_offset.setSuffix(" mm")
        self.spin_z_offset.setToolTip("Z偏移补偿（探针与喷嘴高度差）")
        params_grid.addWidget(QLabel("Z偏移"), 1, 2)
        params_grid.addWidget(self.spin_z_offset, 1, 3)
        probe_layout.addLayout(params_grid)

        simulate_row = QHBoxLayout()
        self.chk_simulate = QCheckBox("URSim")
        self.chk_simulate.setToolTip("模拟模式下用位置阈值代替力阈值")
        self.chk_simulate.stateChanged.connect(self._on_simulate_changed)
        simulate_row.addWidget(self.chk_simulate)
        simulate_row.addWidget(QLabel("接触Z"))
        self.spin_simulate_z = QDoubleSpinBox()
        self.spin_simulate_z.setRange(-500.0, 500.0)
        self.spin_simulate_z.setValue(0.0)
        self.spin_simulate_z.setSuffix(" mm")
        self.spin_simulate_z.setEnabled(False)
        self.spin_simulate_z.setMaximumWidth(120)
        simulate_row.addWidget(self.spin_simulate_z)
        simulate_row.addStretch()
        probe_layout.addLayout(simulate_row)

        utility_row = QHBoxLayout()
        utility_row.setSpacing(8)
        self.btn_zero_ft = QPushButton("归零")
        self.btn_zero_ft.clicked.connect(self._zero_ft_sensor)
        utility_row.addWidget(self.btn_zero_ft)

        self.btn_probe = QPushButton("试探")
        self.btn_probe.clicked.connect(self._do_single_probe)
        utility_row.addWidget(self.btn_probe)

        self.btn_retract = QPushButton("抬起")
        self.btn_retract.clicked.connect(self._do_retract)
        utility_row.addWidget(self.btn_retract)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_probe)
        utility_row.addWidget(self.btn_stop)
        probe_layout.addLayout(utility_row)

        capture_grid = QGridLayout()
        capture_grid.setHorizontalSpacing(8)
        capture_grid.setVerticalSpacing(8)

        self.btn_probe_origin = QPushButton("采原点")
        self.btn_probe_origin.clicked.connect(lambda: self._do_probe_and_add("origin"))
        capture_grid.addWidget(self.btn_probe_origin, 0, 0)

        self.btn_probe_x = QPushButton("采 X参考")
        self.btn_probe_x.clicked.connect(lambda: self._do_probe_and_add("x"))
        capture_grid.addWidget(self.btn_probe_x, 0, 1)

        self.btn_probe_y = QPushButton("采 Y参考")
        self.btn_probe_y.clicked.connect(lambda: self._do_probe_and_add("y"))
        capture_grid.addWidget(self.btn_probe_y, 1, 0)

        self.btn_probe_add = QPushButton("采普通点")
        self.btn_probe_add.clicked.connect(lambda: self._do_probe_and_add(None))
        capture_grid.addWidget(self.btn_probe_add, 1, 1)
        probe_layout.addLayout(capture_grid)

        grp_probe.setLayout(probe_layout)
        left_vbox.addWidget(grp_probe)
        left_vbox.addStretch()
        splitter.addWidget(left_panel)

        # === 右栏：参考点与结果 ===
        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        right_vbox.setContentsMargins(0, 0, 0, 0)
        right_vbox.setSpacing(12)

        grp_points = QGroupBox("标定点")
        grp_points.setObjectName("autoCalSection")
        points_layout = QVBoxLayout()
        points_layout.setSpacing(10)

        toolbar = QFrame()
        toolbar.setObjectName("autoCalToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)

        self.btn_set_origin = QToolButton()
        self.btn_set_origin.setObjectName("autoCalToolBtn")
        self.btn_set_origin.setAutoRaise(True)
        self.btn_set_origin.setText("设 O")
        self.btn_set_origin.clicked.connect(lambda: self._set_reference("origin"))
        toolbar_layout.addWidget(self.btn_set_origin)

        self.btn_set_x_ref = QToolButton()
        self.btn_set_x_ref.setObjectName("autoCalToolBtn")
        self.btn_set_x_ref.setAutoRaise(True)
        self.btn_set_x_ref.setText("设 X")
        self.btn_set_x_ref.clicked.connect(lambda: self._set_reference("x"))
        toolbar_layout.addWidget(self.btn_set_x_ref)

        self.btn_set_y_ref = QToolButton()
        self.btn_set_y_ref.setObjectName("autoCalToolBtn")
        self.btn_set_y_ref.setAutoRaise(True)
        self.btn_set_y_ref.setText("设 Y")
        self.btn_set_y_ref.clicked.connect(lambda: self._set_reference("y"))
        toolbar_layout.addWidget(self.btn_set_y_ref)

        toolbar_divider = QFrame()
        toolbar_divider.setObjectName("autoCalToolbarDivider")
        toolbar_layout.addWidget(toolbar_divider)

        self.btn_delete = QToolButton()
        self.btn_delete.setObjectName("autoCalToolDanger")
        self.btn_delete.setAutoRaise(True)
        self.btn_delete.setText("删除")
        self.btn_delete.clicked.connect(self._delete_selected)
        toolbar_layout.addWidget(self.btn_delete)

        self.btn_clear = QToolButton()
        self.btn_clear.setObjectName("autoCalToolBtn")
        self.btn_clear.setAutoRaise(True)
        self.btn_clear.setText("清空")
        self.btn_clear.clicked.connect(self._clear_points)
        toolbar_layout.addWidget(self.btn_clear)
        toolbar_layout.addStretch()
        points_layout.addWidget(toolbar)

        self.pt_list = QListWidget()
        self.pt_list.setObjectName("autoCalPointList")
        points_layout.addWidget(self.pt_list, 1)

        grp_points.setLayout(points_layout)
        right_vbox.addWidget(grp_points, 3)

        grp_result = QGroupBox("结果")
        grp_result.setObjectName("autoCalSection")
        result_layout = QVBoxLayout()
        result_layout.setSpacing(10)

        result_btn_row = QHBoxLayout()
        result_btn_row.setSpacing(8)
        self.btn_fit = QPushButton("生成 Feature")
        self.btn_fit.clicked.connect(self._fit_plane)
        result_btn_row.addWidget(self.btn_fit, 2)

        self.btn_save_to_lib = QPushButton("存入库")
        self.btn_save_to_lib.clicked.connect(self._save_to_library)
        self.btn_save_to_lib.setEnabled(False)
        result_btn_row.addWidget(self.btn_save_to_lib, 1)
        result_layout.addLayout(result_btn_row)

        self.txt_result = QTextEdit()
        self.txt_result.setObjectName("autoCalResultBox")
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setPlaceholderText("采满 O / X / Y 后生成 Feature...")
        self.txt_result.setMinimumHeight(150)
        result_layout.addWidget(self.txt_result)

        grp_result.setLayout(result_layout)
        right_vbox.addWidget(grp_result, 2)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        for btn in (
            self.btn_probe_origin,
            self.btn_probe_x,
            self.btn_probe_y,
            self.btn_probe_add,
        ):
            btn.setMinimumHeight(42)

        self.btn_fit.setMinimumHeight(38)
        self.apply_theme()

        self._update_reference_summary()

    def _apply_button_styles(self):
        accent = StyleFactory.get_style("button_accent")
        neutral = StyleFactory.get_style("button_neutral")
        danger = StyleFactory.get_style("button_danger")

        for btn in (
            self.btn_probe_origin,
            self.btn_probe_x,
            self.btn_probe_y,
            self.btn_probe_add,
            self.btn_fit,
        ):
            btn.setStyleSheet(accent)

        for btn in (
            self.btn_zero_ft,
            self.btn_probe,
            self.btn_retract,
            self.btn_save_to_lib,
        ):
            btn.setStyleSheet(neutral)

        for btn in (self.btn_stop,):
            btn.setStyleSheet(danger)

    def apply_theme(self):
        text = self.get_token("text", "#e0e0e0")
        muted = self.get_token("text_muted", "#8a8a8a")
        panel = self.get_token("bg_panel", "#2d2d2d")
        tertiary = self.get_token("bg_tertiary", "#252526")
        border = self.get_token("border", "#3a3a3e")
        border_light = self.get_token("border_light", "#46464a")
        accent = self.get_token("accent_blue", "#2196F3")
        bg_main = self.get_token("bg_main", "#2b2b2b")
        hover = self.get_token("bg_hover_strong", "#383838")
        danger = self.get_token("danger", "#D32F2F")
        disabled = self.get_token("btn_disabled_text", "#6a6a6a")
        font_mono = self.get_token("font_mono", '"Consolas", "Courier New", monospace')

        self.setStyleSheet(
            f"""
            QFrame#autoCalCard {{
                background-color: {panel};
                border: 1px solid {border_light};
                border-radius: 10px;
            }}
            QLabel#autoCalCaption {{
                color: {muted};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#autoCalMono {{
                color: {text};
                font-family: {font_mono};
                font-size: 12px;
            }}
            QLabel#autoCalMetric {{
                color: {accent};
                font-size: 20px;
                font-weight: 700;
            }}
            QLabel#autoCalStep {{
                color: {text};
                font-weight: 600;
            }}
            QGroupBox#autoCalSection {{
                background-color: {panel};
                border: 1px solid {border};
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 10px;
            }}
            QGroupBox#autoCalSection::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                color: {muted};
                background-color: {bg_main};
                font-weight: 600;
            }}
            QListWidget#autoCalPointList,
            QTextEdit#autoCalResultBox {{
                background-color: {tertiary};
                border: 1px solid {border};
                border-radius: 8px;
                font-family: {font_mono};
            }}
            QFrame#autoCalToolbar {{
                background-color: {tertiary};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QFrame#autoCalToolbarDivider {{
                background-color: {border_light};
                min-width: 1px;
                max-width: 1px;
                margin: 4px 2px;
            }}
            QToolButton#autoCalToolBtn,
            QToolButton#autoCalToolDanger {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                color: {text};
                padding: 4px 10px;
                font-weight: 600;
            }}
            QToolButton#autoCalToolBtn:hover {{
                background-color: {hover};
            }}
            QToolButton#autoCalToolDanger {{
                color: {danger};
            }}
            QToolButton#autoCalToolDanger:hover {{
                background-color: {hover};
            }}
            QToolButton#autoCalToolBtn:disabled,
            QToolButton#autoCalToolDanger:disabled {{
                color: {disabled};
            }}
            """
        )
        self._apply_button_styles()

    def on_theme_changed(self, theme_id: str):
        self.apply_theme()
    
    def _on_simulate_changed(self, state):
        self.spin_simulate_z.setEnabled(state == 2)
    
    def _update_config(self):
        """从UI更新配置"""
        self.config.contact_force_threshold = self.spin_force_threshold.value()
        self.config.approach_speed = self.spin_speed.value() / 1000.0
        self.config.probe_repeat_count = self.spin_repeat.value()
        self.config.z_offset = self.spin_z_offset.value() / 1000.0
        self.config.simulate_mode = self.chk_simulate.isChecked()
        self.config.simulate_contact_z = self.spin_simulate_z.value() / 1000.0
    
    def _update_live_display(self):
        """更新实时显示"""
        if not self.main.driver.is_connected():
            self.lbl_tcp_xyz.setText("X --.--   Y --.--   Z --.-- mm")
            self.lbl_tcp_rot.setText("Rx --.--   Ry --.--   Rz --.-- rad")
            self.lbl_force.setText("Fz -- N")
            return
        
        pose = self.main.driver.get_tcp_pose()
        force = self.main.driver.get_tcp_force()
        
        if pose:
            self.lbl_tcp_xyz.setText(
                f"X {pose[0]*1000:8.2f}   Y {pose[1]*1000:8.2f}   Z {pose[2]*1000:8.2f} mm"
            )
            self.lbl_tcp_rot.setText(
                f"Rx {pose[3]:7.3f}   Ry {pose[4]:7.3f}   Rz {pose[5]:7.3f} rad"
            )
        if force:
            self.lbl_force.setText(f"Fz {force[2]:+.2f} N")
    
    def _check_connection(self) -> bool:
        if not self.main.driver.is_connected():
            QMessageBox.warning(self, "警告", "请先连接机器人！")
            return False
        return True

    def _ensure_rtde_control_ready(self) -> bool:
        """
        确保控制通道可用，失效时执行完整连接修复
        :return: True 如果可用，False 如果不可用
        """
        alive, detail = self.main.driver.is_rtde_control_alive()
        if alive:
            return True

        self.main.log(f"检测到 rtde_control 失效: {detail}")
        repair = getattr(self.main, "repair_connection_blocking", None)
        if callable(repair):
            success = bool(repair(reason="标定操作需要恢复控制通道，正在执行完整连接修复..."))
        else:
            success = self.main.driver.reconnect_control_interface(self.main.log)

        snapshot_getter = getattr(self.main.driver, "get_connection_snapshot", None)
        snapshot = snapshot_getter() if callable(snapshot_getter) else None
        if success and snapshot is not None and snapshot.control == ChannelState.UP:
            self.main.log("控制通道已恢复")
            return True

        QMessageBox.warning(
            self,
            "控制接口失效",
            "控制通道修复失败。\n\n"
            "可能原因：\n"
            "1. 示教器正在运行程序\n"
            "2. 机器人处于保护停止状态\n"
            "3. Dashboard 或监控链路未恢复\n\n"
            "请确保示教器处于空闲状态后重试。",
        )
        return False
    
    def _zero_ft_sensor(self):
        if not self._check_connection():
            return
        if self.main.driver.zero_ft_sensor():
            self.main.log("力传感器已归零")
        else:
            QMessageBox.warning(self, "错误", "力传感器归零失败")

    def _invalidate_fit_result(self):
        self._last_feature = None
        self.txt_result.clear()
        self.btn_save_to_lib.setEnabled(False)

    def _format_point_item(self, index: int) -> str:
        p = self.calibration_points[index]
        roles = []
        if self.reference_indices["origin"] == index:
            roles.append("O")
        if self.reference_indices["x"] == index:
            roles.append("X")
        if self.reference_indices["y"] == index:
            roles.append("Y")
        role_text = f" [{'/'.join(roles)}]" if roles else ""
        return f"P{index+1}{role_text}  {p[0]*1000:.2f}, {p[1]*1000:.2f}, {p[2]*1000:.2f} mm"

    def _update_reference_summary(self):
        parts = []
        for role, label in (("origin", "O"), ("x", "X"), ("y", "Y")):
            index = self.reference_indices[role]
            if index is None:
                parts.append(f"{label} --")
            else:
                parts.append(f"{label} P{index + 1}")
        self.lbl_reference_summary.setText(" | ".join(parts))

        if self.reference_indices["origin"] is None:
            next_step = "下一步: 采原点"
        elif self.reference_indices["x"] is None:
            next_step = "下一步: 采 X参考"
        elif self.reference_indices["y"] is None:
            next_step = "下一步: 采 Y参考"
        else:
            next_step = "下一步: 采普通点或生成 Feature"
        self.lbl_next_step.setText(next_step)

    def _refresh_point_list(self, selected_row: Optional[int] = None):
        if selected_row is None:
            selected_row = self.pt_list.currentRow()
        self.pt_list.clear()
        for index in range(len(self.calibration_points)):
            self.pt_list.addItem(self._format_point_item(index))
        if 0 <= selected_row < self.pt_list.count():
            self.pt_list.setCurrentRow(selected_row)
        self._update_reference_summary()

    def _assign_reference(self, role: str, row: int, *, invalidate: bool = True, log_change: bool = True):
        for key, value in self.reference_indices.items():
            if key != role and value == row:
                self.reference_indices[key] = None
        self.reference_indices[role] = row
        self._refresh_point_list(selected_row=row)
        if invalidate:
            self._invalidate_fit_result()
        if log_change:
            role_label = {"origin": "原点", "x": "X参考", "y": "Y参考"}[role]
            self.main.log(f"已将第 {row+1} 个点设为{role_label}")

    def _set_reference(self, role: str):
        row = self.pt_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个标定点")
            return
        self._assign_reference(role, row)

    def _set_buttons_enabled(self, enabled: bool):
        self.btn_probe.setEnabled(enabled)
        self.btn_probe_add.setEnabled(enabled)
        self.btn_probe_origin.setEnabled(enabled)
        self.btn_probe_x.setEnabled(enabled)
        self.btn_probe_y.setEnabled(enabled)
        self.btn_retract.setEnabled(enabled)
        self.btn_zero_ft.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
        self.btn_set_origin.setEnabled(enabled)
        self.btn_set_x_ref.setEnabled(enabled)
        self.btn_set_y_ref.setEnabled(enabled)
        self.btn_fit.setEnabled(enabled)
        self.btn_save_to_lib.setEnabled(enabled and bool(self._last_feature))
        self.btn_stop.setEnabled(not enabled)

    def _create_probe_worker(self, finished_slot):
        worker = ProbeWorker(self.main.driver, self.config)
        worker.progress.connect(lambda msg: self.main.log(msg))
        worker.finished_probe.connect(finished_slot)
        worker.finished.connect(worker.deleteLater)
        self.probe_worker = worker
        worker.start()
    
    def _do_single_probe(self):
        if not self._check_connection():
            return
        if not self._ensure_rtde_control_ready():
            return
        self._update_config()
        self._batch_cancelled = False
        self._next_probe_timer.stop()
        self._set_buttons_enabled(False)
        self._create_probe_worker(self._on_probe_finished_single)
    
    def _on_probe_finished_single(self, success, pose, force, error_msg):
        self.probe_worker = None
        self._set_buttons_enabled(True)
        if success:
            self.main.log(f"探测成功: Z = {pose[2]*1000:.3f} mm, ΔFz = {force:.2f} N")
        else:
            self.main.log(f"探测失败: {error_msg}")
    
    def _do_probe_and_add(self, capture_role: Optional[str] = None):
        if not self._check_connection():
            return
        if not self._ensure_rtde_control_ready():
            return
        self._update_config()
        self._pending_capture_role = capture_role
        self._batch_cancelled = False
        self._next_probe_timer.stop()
        self._set_buttons_enabled(False)

        if capture_role is not None:
            role_label = {"origin": "原点", "x": "X参考", "y": "Y参考"}[capture_role]
            self.main.log(f"开始探测并记录为{role_label}，请保持 TCP 位于目标点正上方")
        else:
            self.main.log("开始探测并记录为普通点")
        
        # 多次测量取平均
        self._probe_measurements = []
        self._probe_count = 0
        self._probe_total = self.config.probe_repeat_count
        self._start_next_probe()
    
    def _start_next_probe(self):
        if self._batch_cancelled:
            self._pending_capture_role = None
            self._set_buttons_enabled(True)
            return
        if not self._check_connection():
            self._pending_capture_role = None
            self._set_buttons_enabled(True)
            return
        if not self._ensure_rtde_control_ready():
            self._pending_capture_role = None
            self._set_buttons_enabled(True)
            return
        self._create_probe_worker(self._on_probe_finished_multi)
    
    def _on_probe_finished_multi(self, success, pose, force, error_msg):
        self.probe_worker = None
        if self._batch_cancelled:
            self._pending_capture_role = None
            self._set_buttons_enabled(True)
            self.main.log("多次探测已取消")
            return

        if success:
            xyz = [pose[0], pose[1], pose[2]]
            self._probe_measurements.append(xyz)
            self.main.log(f"第 {self._probe_count + 1}/{self._probe_total} 次: Z = {xyz[2]*1000:.3f} mm, ΔFz = {force:.2f} N")
        else:
            self.main.log(f"第 {self._probe_count + 1}/{self._probe_total} 次失败: {error_msg}")
        
        self._probe_count += 1
        
        if self._probe_count < self._probe_total:
            # 回退后继续下一次
            self._do_retract_silent()
            self._next_probe_timer.start(500)
        else:
            # 完成所有测量
            self._finish_multi_probe()
    
    def _finish_multi_probe(self):
        self._set_buttons_enabled(True)
        self._batch_cancelled = False
        
        if not self._probe_measurements:
            self._pending_capture_role = None
            self.main.log("所有测量均失败")
            return
        
        # 计算平均值
        arr = np.array(self._probe_measurements)
        mean_xyz = arr.mean(axis=0).tolist()
        
        if len(self._probe_measurements) >= 2:
            std_z = arr[:, 2].std()
            self.main.log(f"测量完成: 平均 Z = {mean_xyz[2]*1000:.3f} mm, 标准差 = {std_z*1000:.3f} mm")
        elif self._probe_total > 1:
            self.main.log(f"测量完成: 仅 {len(self._probe_measurements)}/{self._probe_total} 次成功，已使用单次结果")
        
        # 添加标定点
        self._invalidate_fit_result()
        self.calibration_points.append(mean_xyz)
        idx = len(self.calibration_points) - 1
        assigned_role = self._pending_capture_role
        if assigned_role is not None:
            self._assign_reference(assigned_role, idx, invalidate=False, log_change=False)
        self._refresh_point_list(selected_row=idx)
        self.main.log(f"已添加第 {idx + 1} 个标定点")
        if assigned_role is not None:
            role_label = {"origin": "原点", "x": "X参考", "y": "Y参考"}[assigned_role]
            self.main.log(f"已将第 {idx + 1} 个点记录为{role_label}")
        self._pending_capture_role = None
        
        # 回退
        self._do_retract_silent()
    
    def _do_retract(self):
        if not self._check_connection():
            return
        if not self._ensure_rtde_control_ready():
            return
        self._do_retract_silent()
        self.main.log(f"回退 {self.config.retract_distance*1000:.1f} mm")
    
    def _do_retract_silent(self):
        pose = self.main.driver.get_tcp_pose()
        if pose:
            target = pose.copy()
            target[2] += self.config.retract_distance
            self.main.driver.move_l(target, 0.1, 0.3)
    
    def _stop_probe(self):
        self._batch_cancelled = True
        self._pending_capture_role = None
        self._next_probe_timer.stop()
        if self.probe_worker:
            self.probe_worker.stop()
            self.main.driver.speed_stop()
        self._set_buttons_enabled(True)
        self.main.log("已请求停止自动标定")
    
    def _clear_points(self):
        self.calibration_points = []
        self.reference_indices = {"origin": None, "x": None, "y": None}
        self._refresh_point_list(selected_row=-1)
        self._invalidate_fit_result()
    
    def _delete_selected(self):
        row = self.pt_list.currentRow()
        if row >= 0:
            self.calibration_points.pop(row)
            for role, index in list(self.reference_indices.items()):
                if index is None:
                    continue
                if index == row:
                    self.reference_indices[role] = None
                elif index > row:
                    self.reference_indices[role] = index - 1
            self._refresh_point_list(selected_row=min(row, len(self.calibration_points) - 1))
            self._invalidate_fit_result()

    def _fit_plane(self):
        """拟合平面"""
        if len(self.calibration_points) < 3:
            QMessageBox.warning(self, "数据不足", "至少需要 3 个标定点！")
            return

        missing_refs = [label for key, label in (("origin", "原点"), ("x", "X参考"), ("y", "Y参考"))
                        if self.reference_indices[key] is None]
        if missing_refs:
            QMessageBox.warning(self, "参考点不足", f"请先指定：{'、'.join(missing_refs)}")
            return

        # 转换为 mm 单位供 fit_plane_feature 使用
        points_mm = [[p[0]*1000, p[1]*1000, p[2]*1000] for p in self.calibration_points]

        feat_str, log = self.main.print_lib.fit_plane_feature(
            points_mm,
            origin_index=self.reference_indices["origin"],
            x_index=self.reference_indices["x"],
            y_index=self.reference_indices["y"],
        )
        if feat_str:
            self._last_feature = feat_str  # 保存最后一次结果
            self.btn_save_to_lib.setEnabled(True)
            self.txt_result.setText("拟合成功!\n\n" + log)
            self.txt_result.append("\n=== URScript 代码 ===")
            self.txt_result.append(f"global feature1 = {feat_str}")
            QApplication.clipboard().setText(feat_str)
            self.main.log("自动标定成功，Feature 字符串已复制到剪贴板。")
        else:
            self._last_feature = None
            self.btn_save_to_lib.setEnabled(False)
            self.txt_result.setText("拟合失败\n" + log)

    def _save_to_library(self):
        """快捷保存到 Feature 库"""
        if not hasattr(self, '_last_feature') or not self._last_feature:
            QMessageBox.warning(self, "无数据", "请先完成标定拟合")
            return

        # 获取 CalibrationWidget（父容器）
        parent = self.parent()
        while parent and not isinstance(parent, CalibrationWidget):
            parent = parent.parent()

        if parent and hasattr(parent, 'feature_lib_widget'):
            # 填入 Feature 并切换到 Feature 库 Tab
            parent.feature_lib_widget.set_feature_for_save(self._last_feature)
            parent.tab_widget.setCurrentWidget(parent.feature_lib_widget)
            self.main.log("请在 Feature 库中输入名称和描述后保存")
        else:
            QMessageBox.warning(self, "错误", "无法找到 Feature 库页面")


# ================= Feature 库管理页面 =================
class FeatureLibraryWidget(QWidget, ThemeAwareMixin):
    """Feature 库管理页面 - 保存和加载标定结果"""

    def __init__(self, main_window):
        super().__init__()
        self.setup_theme_awareness()
        self.main = main_window
        self.features = {}
        self._init_ui()
        self._load_features()

    def _init_ui(self):
        layout = QHBoxLayout(self)

        # === 左栏：Feature 列表 ===
        left_panel = QWidget()
        left_vbox = QVBoxLayout(left_panel)

        grp_list = QGroupBox("已保存的 Feature")
        list_layout = QVBoxLayout()
        self.feature_list = QListWidget()
        self.feature_list.currentRowChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.feature_list)

        # 操作按钮
        btn_row = QHBoxLayout()
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._delete_feature)
        self.btn_copy = QPushButton("复制")
        self.btn_copy.clicked.connect(self._copy_feature)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_copy)
        list_layout.addLayout(btn_row)

        grp_list.setLayout(list_layout)
        left_vbox.addWidget(grp_list)
        left_vbox.addStretch()
        layout.addWidget(left_panel, 1)

        # === 右栏：详情显示 + 新增 ===
        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)

        # 详情区域
        grp_detail = QGroupBox("Feature 详情")
        detail_layout = QFormLayout()
        self.lbl_name = QLabel("--")
        self.lbl_desc = QLabel("--")
        self.lbl_time = QLabel("--")
        self.txt_feature = QTextEdit()
        self.txt_feature.setReadOnly(True)
        self.txt_feature.setMaximumHeight(80)
        self.txt_feature.setFont(QFont("Consolas", 10))
        detail_layout.addRow("名称:", self.lbl_name)
        detail_layout.addRow("描述:", self.lbl_desc)
        detail_layout.addRow("创建时间:", self.lbl_time)
        detail_layout.addRow("Feature:", self.txt_feature)
        grp_detail.setLayout(detail_layout)
        right_vbox.addWidget(grp_detail)

        # 新增区域
        grp_add = QGroupBox("添加 Feature")
        add_layout = QFormLayout()
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("例如: 热床_左上")
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText("例如: 左上角热床平面")
        self.input_feature = QLineEdit()
        self.input_feature.setPlaceholderText("p[x, y, z, rx, ry, rz]")
        self.btn_add = QPushButton("添加到库")
        self.btn_add.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_add.clicked.connect(self._add_feature)
        add_layout.addRow("名称:", self.input_name)
        add_layout.addRow("描述:", self.input_desc)
        add_layout.addRow("Feature:", self.input_feature)
        add_layout.addRow(self.btn_add)
        grp_add.setLayout(add_layout)
        right_vbox.addWidget(grp_add)

        right_vbox.addStretch()
        layout.addWidget(right_panel, 2)

    def on_theme_changed(self, theme_id: str):
        if hasattr(self, 'btn_add'):
            self.btn_add.setStyleSheet(StyleFactory.get_style("button_accent"))

    def _load_features(self):
        """从配置加载 Feature 列表"""
        from ur_print_fdm.config import config_manager
        self.features = config_manager.get("calibration.saved_features", {}) or {}
        self.feature_list.clear()
        for name in self.features.keys():
            self.feature_list.addItem(name)
        # 清空详情
        self._clear_detail()

    def _save_features(self):
        """保存 Feature 列表到配置"""
        from ur_print_fdm.config import config_manager
        config_manager.set("calibration.saved_features", self.features)
        config_manager.save()

    def _clear_detail(self):
        """清空详情显示"""
        self.lbl_name.setText("--")
        self.lbl_desc.setText("--")
        self.lbl_time.setText("--")
        self.txt_feature.clear()

    def _on_selection_changed(self, row):
        """选中项变化时更新详情"""
        if row < 0:
            self._clear_detail()
            return
        name = self.feature_list.item(row).text()
        data = self.features.get(name, {})
        self.lbl_name.setText(name)
        self.lbl_desc.setText(data.get("description", "无") or "无")
        self.lbl_time.setText(data.get("created_at", "未知"))
        self.txt_feature.setText(data.get("feature", ""))

    def _add_feature(self):
        """添加新 Feature"""
        import datetime

        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入名称")
            return
        feature = self.input_feature.text().strip()
        if not feature:
            QMessageBox.warning(self, "错误", "请输入 Feature 字符串")
            return

        # 检查是否已存在
        if name in self.features:
            reply = QMessageBox.question(self, "确认覆盖", f"'{name}' 已存在，是否覆盖？")
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.features[name] = {
            "feature": feature,
            "description": self.input_desc.text().strip(),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_features()
        self._load_features()

        # 清空输入
        self.input_name.clear()
        self.input_desc.clear()
        self.input_feature.clear()

        self.main.log(f"Feature '{name}' 已添加到库")

    def _delete_feature(self):
        """删除选中的 Feature"""
        row = self.feature_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要删除的 Feature")
            return
        name = self.feature_list.item(row).text()
        reply = QMessageBox.question(self, "确认删除", f"确定删除 '{name}'?")
        if reply == QMessageBox.StandardButton.Yes:
            del self.features[name]
            self._save_features()
            self._load_features()
            self.main.log(f"Feature '{name}' 已删除")

    def _copy_feature(self):
        """复制选中的 Feature 到剪贴板"""
        row = self.feature_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择要复制的 Feature")
            return
        name = self.feature_list.item(row).text()
        feature = self.features.get(name, {}).get("feature", "")
        if feature:
            QApplication.clipboard().setText(feature)
            self.main.log(f"Feature '{name}' 已复制到剪贴板")

    def set_feature_for_save(self, feature_str: str):
        """从外部设置待保存的 Feature（供标定页面调用）"""
        self.input_feature.setText(feature_str)
        self.input_name.setFocus()


# ================= Tab 容器 =================
class CalibrationWidget(QWidget, ThemeAwareMixin):
    """平面标定 Tab 容器 - 包含手动标定、自动标定和 Feature 库三个页面"""

    def __init__(self, main_window):
        super().__init__()
        self.setup_theme_awareness()
        self.main = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()

        # 手动标定页
        self.manual_widget = ManualCalibrationWidget(self.main)
        self.tab_widget.addTab(self.manual_widget, "手动标定")

        # 自动标定页
        self.auto_widget = AutoCalibrationWidget(self.main)
        self.tab_widget.addTab(self.auto_widget, "自动标定 (力控)")

        # Feature 库页
        self.feature_lib_widget = FeatureLibraryWidget(self.main)
        self.tab_widget.addTab(self.feature_lib_widget, "Feature 库")

        layout.addWidget(self.tab_widget)

    def on_theme_changed(self, theme_id: str):
        """主题变更时传递给子组件"""
        if hasattr(self, 'manual_widget'):
            self.manual_widget.on_theme_changed(theme_id)
        if hasattr(self, 'auto_widget'):
            self.auto_widget.on_theme_changed(theme_id)
        if hasattr(self, 'feature_lib_widget'):
            self.feature_lib_widget.on_theme_changed(theme_id)

    def update_live_tcp(self, tcp, joints):
        """更新实时 TCP 显示（供手动标定使用）"""
        if hasattr(self, 'manual_widget'):
            self.manual_widget.update_live_tcp(tcp, joints)
