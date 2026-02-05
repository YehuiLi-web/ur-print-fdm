import math
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
                             QLabel, QGridLayout, QPushButton, QListWidget, QTextEdit,
                             QMessageBox, QApplication, QTabWidget, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QProgressBar)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

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
    
    def run(self):
        cfg = self.config
        
        # 获取当前位置
        start_pose = self.driver.get_tcp_pose()
        if not start_pose:
            self.finished_probe.emit(False, [], 0.0, "无法获取当前位置")
            return
        
        self.progress.emit(f"开始探测，起始 Z = {start_pose[2]*1000:.1f} mm")
        
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
                    if abs(fz) > cfg.contact_force_threshold:
                        contact_detected = True
                
                if contact_detected:
                    self.driver.speed_stop()
                    self.progress.emit(f"检测到接触，等待稳定...")
                    time.sleep(cfg.settle_time)
                    
                    # 等待力稳定
                    stable_pose = self._wait_for_force_stable()
                    if stable_pose is None:
                        stable_pose = self.driver.get_tcp_pose()
                    
                    stable_force = self.driver.get_tcp_force()
                    contact_fz = stable_force[2] if stable_force else fz
                    
                    # 应用 Z 偏移补偿
                    if cfg.z_offset != 0:
                        stable_pose[2] += cfg.z_offset
                    
                    self.finished_probe.emit(True, stable_pose, contact_fz, "")
                    return
                
                # 发送速度命令
                self.driver.speed_l(speed_vec, cfg.approach_accel, 0.1)
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
        
        while time.time() - t0 < timeout:
            force = self.driver.get_tcp_force()
            if force:
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
        self._init_ui()
        
        # 实时更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_live_display)
        self.update_timer.start(100)  # 10Hz
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        
        # === 左栏：参数配置 + 操作 ===
        left_panel = QWidget()
        left_vbox = QVBoxLayout(left_panel)
        
        # 实时状态
        grp_live = QGroupBox("实时状态")
        live_layout = QFormLayout()
        self.lbl_tcp = QLabel("TCP: --")
        self.lbl_force = QLabel("力: Fz = --")
        live_layout.addRow(self.lbl_tcp)
        live_layout.addRow(self.lbl_force)
        grp_live.setLayout(live_layout)
        left_vbox.addWidget(grp_live)
        
        # 参数配置
        grp_params = QGroupBox("探测参数")
        params_layout = QFormLayout()
        
        self.spin_force_threshold = QDoubleSpinBox()
        self.spin_force_threshold.setRange(0.5, 20.0)
        self.spin_force_threshold.setValue(self.config.contact_force_threshold)
        self.spin_force_threshold.setSuffix(" N")
        self.spin_force_threshold.setToolTip("接触力阈值，超过此值判定为接触")
        params_layout.addRow("力阈值:", self.spin_force_threshold)
        
        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(1.0, 20.0)
        self.spin_speed.setValue(self.config.approach_speed * 1000)
        self.spin_speed.setSuffix(" mm/s")
        self.spin_speed.setToolTip("探测下降速度")
        params_layout.addRow("探测速度:", self.spin_speed)
        
        self.spin_repeat = QSpinBox()
        self.spin_repeat.setRange(1, 10)
        self.spin_repeat.setValue(self.config.probe_repeat_count)
        self.spin_repeat.setToolTip("每点重复测量次数，取平均值")
        params_layout.addRow("重复次数:", self.spin_repeat)
        
        self.spin_z_offset = QDoubleSpinBox()
        self.spin_z_offset.setRange(-50.0, 50.0)
        self.spin_z_offset.setValue(self.config.z_offset * 1000)
        self.spin_z_offset.setSuffix(" mm")
        self.spin_z_offset.setToolTip("Z偏移补偿（探针与喷嘴高度差）")
        params_layout.addRow("Z偏移:", self.spin_z_offset)
        
        self.chk_simulate = QCheckBox("URSim 模拟模式")
        self.chk_simulate.setToolTip("模拟模式下用位置阈值代替力阈值")
        self.chk_simulate.stateChanged.connect(self._on_simulate_changed)
        params_layout.addRow(self.chk_simulate)
        
        self.spin_simulate_z = QDoubleSpinBox()
        self.spin_simulate_z.setRange(-500.0, 500.0)
        self.spin_simulate_z.setValue(0.0)
        self.spin_simulate_z.setSuffix(" mm")
        self.spin_simulate_z.setEnabled(False)
        params_layout.addRow("模拟接触Z:", self.spin_simulate_z)
        
        grp_params.setLayout(params_layout)
        left_vbox.addWidget(grp_params)
        
        # 操作按钮
        grp_ops = QGroupBox("操作")
        ops_layout = QVBoxLayout()
        
        self.btn_zero_ft = QPushButton("力传感器归零")
        self.btn_zero_ft.clicked.connect(self._zero_ft_sensor)
        ops_layout.addWidget(self.btn_zero_ft)
        
        self.btn_probe = QPushButton("单次探测")
        self.btn_probe.clicked.connect(self._do_single_probe)
        ops_layout.addWidget(self.btn_probe)
        
        self.btn_probe_add = QPushButton("探测并添加标定点")
        self.btn_probe_add.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_probe_add.clicked.connect(self._do_probe_and_add)
        ops_layout.addWidget(self.btn_probe_add)
        
        self.btn_retract = QPushButton("回退 (抬起)")
        self.btn_retract.clicked.connect(self._do_retract)
        ops_layout.addWidget(self.btn_retract)
        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_probe)
        ops_layout.addWidget(self.btn_stop)
        
        grp_ops.setLayout(ops_layout)
        left_vbox.addWidget(grp_ops)
        
        left_vbox.addStretch()
        layout.addWidget(left_panel, 1)
        
        # === 右栏：标定点列表 + 结果 ===
        right_panel = QWidget()
        right_vbox = QVBoxLayout(right_panel)
        
        grp_points = QGroupBox("标定点列表")
        points_layout = QVBoxLayout()
        self.pt_list = QListWidget()
        points_layout.addWidget(self.pt_list)
        
        btn_row = QHBoxLayout()
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._clear_points)
        btn_row.addWidget(self.btn_clear)
        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.clicked.connect(self._delete_selected)
        btn_row.addWidget(self.btn_delete)
        points_layout.addLayout(btn_row)
        
        grp_points.setLayout(points_layout)
        right_vbox.addWidget(grp_points)
        
        grp_result = QGroupBox("拟合结果")
        result_layout = QVBoxLayout()
        self.btn_fit = QPushButton("拟合平面")
        self.btn_fit.setStyleSheet(StyleFactory.get_style("button_accent"))
        self.btn_fit.clicked.connect(self._fit_plane)
        result_layout.addWidget(self.btn_fit)
        
        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setPlaceholderText("至少采集 3 个点后点击拟合...")
        result_layout.addWidget(self.txt_result)
        
        grp_result.setLayout(result_layout)
        right_vbox.addWidget(grp_result)
        
        layout.addWidget(right_panel, 2)
    
    def on_theme_changed(self, theme_id: str):
        if hasattr(self, 'btn_probe_add'):
            self.btn_probe_add.setStyleSheet(StyleFactory.get_style("button_accent"))
        if hasattr(self, 'btn_fit'):
            self.btn_fit.setStyleSheet(StyleFactory.get_style("button_accent"))
    
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
            self.lbl_tcp.setText("TCP: 未连接")
            self.lbl_force.setText("力: --")
            return
        
        pose = self.main.driver.get_tcp_pose()
        force = self.main.driver.get_tcp_force()
        
        if pose:
            self.lbl_tcp.setText(f"TCP: [{pose[0]*1000:.2f}, {pose[1]*1000:.2f}, {pose[2]*1000:.2f}] mm")
        if force:
            self.lbl_force.setText(f"力: Fz = {force[2]:.2f} N")
    
    def _check_connection(self) -> bool:
        if not self.main.driver.is_connected():
            QMessageBox.warning(self, "警告", "请先连接机器人！")
            return False
        return True
    
    def _zero_ft_sensor(self):
        if not self._check_connection():
            return
        if self.main.driver.zero_ft_sensor():
            self.main.log("力传感器已归零")
        else:
            QMessageBox.warning(self, "错误", "力传感器归零失败")
    
    def _set_buttons_enabled(self, enabled: bool):
        self.btn_probe.setEnabled(enabled)
        self.btn_probe_add.setEnabled(enabled)
        self.btn_retract.setEnabled(enabled)
        self.btn_zero_ft.setEnabled(enabled)
        self.btn_stop.setEnabled(not enabled)
    
    def _do_single_probe(self):
        if not self._check_connection():
            return
        self._update_config()
        self._set_buttons_enabled(False)
        
        self.probe_worker = ProbeWorker(self.main.driver, self.config)
        self.probe_worker.progress.connect(lambda msg: self.main.log(msg))
        self.probe_worker.finished_probe.connect(self._on_probe_finished_single)
        self.probe_worker.start()
    
    def _on_probe_finished_single(self, success, pose, force, error_msg):
        self._set_buttons_enabled(True)
        if success:
            self.main.log(f"探测成功: Z = {pose[2]*1000:.3f} mm, Fz = {force:.2f} N")
        else:
            self.main.log(f"探测失败: {error_msg}")
    
    def _do_probe_and_add(self):
        if not self._check_connection():
            return
        self._update_config()
        self._set_buttons_enabled(False)
        
        # 多次测量取平均
        self._probe_measurements = []
        self._probe_count = 0
        self._probe_total = self.config.probe_repeat_count
        self._start_next_probe()
    
    def _start_next_probe(self):
        self.probe_worker = ProbeWorker(self.main.driver, self.config)
        self.probe_worker.progress.connect(lambda msg: self.main.log(msg))
        self.probe_worker.finished_probe.connect(self._on_probe_finished_multi)
        self.probe_worker.start()
    
    def _on_probe_finished_multi(self, success, pose, force, error_msg):
        if success:
            xyz = [pose[0], pose[1], pose[2]]
            self._probe_measurements.append(xyz)
            self.main.log(f"第 {self._probe_count + 1}/{self._probe_total} 次: Z = {xyz[2]*1000:.3f} mm")
        else:
            self.main.log(f"第 {self._probe_count + 1}/{self._probe_total} 次失败: {error_msg}")
        
        self._probe_count += 1
        
        if self._probe_count < self._probe_total:
            # 回退后继续下一次
            self._do_retract_silent()
            QTimer.singleShot(500, self._start_next_probe)
        else:
            # 完成所有测量
            self._finish_multi_probe()
    
    def _finish_multi_probe(self):
        self._set_buttons_enabled(True)
        
        if not self._probe_measurements:
            self.main.log("所有测量均失败")
            return
        
        # 计算平均值
        arr = np.array(self._probe_measurements)
        mean_xyz = arr.mean(axis=0).tolist()
        
        if len(self._probe_measurements) >= 2:
            std_z = arr[:, 2].std()
            self.main.log(f"测量完成: 平均 Z = {mean_xyz[2]*1000:.3f} mm, 标准差 = {std_z*1000:.3f} mm")
        
        # 添加标定点
        self.calibration_points.append(mean_xyz)
        idx = len(self.calibration_points)
        self.pt_list.addItem(f"[{idx}] X={mean_xyz[0]*1000:.2f}, Y={mean_xyz[1]*1000:.2f}, Z={mean_xyz[2]*1000:.2f} mm")
        self.main.log(f"已添加第 {idx} 个标定点")
        
        # 回退
        self._do_retract_silent()
    
    def _do_retract(self):
        if not self._check_connection():
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
        if self.probe_worker:
            self.probe_worker.stop()
            self.main.driver.speed_stop()
        self._set_buttons_enabled(True)
    
    def _clear_points(self):
        self.calibration_points = []
        self.pt_list.clear()
        self.txt_result.clear()
    
    def _delete_selected(self):
        row = self.pt_list.currentRow()
        if row >= 0:
            self.calibration_points.pop(row)
            self.pt_list.takeItem(row)
            # 重新编号
            for i in range(self.pt_list.count()):
                p = self.calibration_points[i]
                self.pt_list.item(i).setText(f"[{i+1}] X={p[0]*1000:.2f}, Y={p[1]*1000:.2f}, Z={p[2]*1000:.2f} mm")

    def _fit_plane(self):
        """拟合平面"""
        if len(self.calibration_points) < 3:
            QMessageBox.warning(self, "数据不足", "至少需要 3 个标定点！")
            return

        # 转换为 mm 单位供 fit_plane_feature 使用
        points_mm = [[p[0]*1000, p[1]*1000, p[2]*1000] for p in self.calibration_points]

        feat_str, log = self.main.print_lib.fit_plane_feature(points_mm)
        if feat_str:
            self.txt_result.setText("拟合成功!\n\n" + log)
            self.txt_result.append("\n=== URScript 代码 ===")
            self.txt_result.append(f"global feature1 = {feat_str}")
            QApplication.clipboard().setText(feat_str)
            self.main.log("自动标定成功，Feature 字符串已复制到剪贴板。")
        else:
            self.txt_result.setText("拟合失败\n" + log)


# ================= Tab 容器 =================
class CalibrationWidget(QWidget, ThemeAwareMixin):
    """平面标定 Tab 容器 - 包含手动标定和自动标定两个页面"""

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

        layout.addWidget(self.tab_widget)

    def on_theme_changed(self, theme_id: str):
        """主题变更时传递给子组件"""
        if hasattr(self, 'manual_widget'):
            self.manual_widget.on_theme_changed(theme_id)
        if hasattr(self, 'auto_widget'):
            self.auto_widget.on_theme_changed(theme_id)

    def update_live_tcp(self, tcp, joints):
        """更新实时 TCP 显示（供手动标定使用）"""
        if hasattr(self, 'manual_widget'):
            self.manual_widget.update_live_tcp(tcp, joints)
