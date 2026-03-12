#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
力控探测法 - 平面标定测试程序 (优化版)

原理：
1. 机械臂末端缓慢向下移动
2. 实时监测 Z 方向的力 Fz
3. 当 |Fz| 超过阈值，说明接触到平面
4. 等待力稳定后记录 TCP 位置
5. 在不同位置重复，得到多个点
6. 最小二乘法拟合平面

优化功能：
- 多次测量取平均（提高精度）
- URSim 模拟模式（位置阈值代替力阈值）
- 力稳定检测（等待力稳定后记录）
- Z 偏移补偿
- 自动多点标定流程

适用于 UR5 CB3 系列（内置力矩传感器）
"""

import math
import time
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass, field

try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
except ImportError:
    print("错误: 请先安装 ur_rtde 库")
    print("  pip install ur_rtde")
    exit(1)


@dataclass
class CalibrationConfig:
    """标定配置参数"""
    # 探测参数（优化后的默认值）
    contact_force_threshold: float = 3.0    # 接触力阈值 (N) - 降低以提高灵敏度
    approach_speed: float = 0.005           # 探测速度 (m/s) - 5mm/s，更慢更准
    approach_accel: float = 0.05            # 加速度 (m/s²) - 降低以减少过冲
    max_approach_distance: float = 0.1      # 最大探测距离 (m)
    retract_distance: float = 0.02          # 接触后回退距离 (m)
    
    # 精度优化参数
    probe_repeat_count: int = 3             # 每点重复测量次数
    force_stable_threshold: float = 0.5     # 力稳定判定阈值 (N)
    force_stable_duration: float = 0.2      # 力稳定持续时间 (s)
    settle_time: float = 0.3                # 接触后稳定等待时间 (s)
    
    # Z 偏移补偿
    z_offset: float = 0.0                   # Z 偏移补偿 (m)，探针与喷嘴的高度差
    
    # URSim 模拟模式
    simulate_mode: bool = False             # 是否启用模拟模式
    simulate_contact_z: float = 0.0         # 模拟接触 Z 高度 (m)


@dataclass
class ProbeResult:
    """单次探测结果"""
    success: bool
    pose: Optional[List[float]] = None      # [x, y, z, rx, ry, rz]
    contact_force: float = 0.0              # 接触时的力 (N)
    error_msg: str = ""


@dataclass
class CalibrationPoint:
    """标定点（含多次测量）"""
    measurements: List[List[float]] = field(default_factory=list)  # 多次测量的 [x,y,z]
    
    @property
    def count(self) -> int:
        return len(self.measurements)
    
    @property
    def mean(self) -> Optional[List[float]]:
        if not self.measurements:
            return None
        arr = np.array(self.measurements)
        return arr.mean(axis=0).tolist()
    
    @property
    def std(self) -> Optional[List[float]]:
        if len(self.measurements) < 2:
            return None
        arr = np.array(self.measurements)
        return arr.std(axis=0).tolist()


class ForceCalibrationTester:
    """力控探测平面标定测试器 (优化版)"""

    def __init__(self):
        self.ip: str = ""
        self.rc: Optional[RTDEControlInterface] = None
        self.rr: Optional[RTDEReceiveInterface] = None
        
        # 配置
        self.config = CalibrationConfig()
        
        # 标定结果
        self.calibration_points: List[CalibrationPoint] = []
        
        # 当前正在采集的点
        self.current_point: Optional[CalibrationPoint] = None

    def log(self, msg: str, level: str = "INFO"):
        """打印带时间戳的日志"""
        ts = time.strftime("%H:%M:%S")
        prefix = {"INFO": "", "WARN": "⚠️ ", "ERROR": "❌ ", "SUCCESS": "✅ "}.get(level, "")
        print(f"[{ts}] {prefix}{msg}")

    # ==================== 连接管理 ====================

    def connect(self, ip: str) -> bool:
        """连接机器人"""
        self.ip = ip
        self.log(f"正在连接 {ip}...")

        try:
            # 先连接 Receive（只读，更稳定）
            self.log("  连接 RTDEReceiveInterface...")
            self.rr = RTDEReceiveInterface(ip)
            if not self.rr.isConnected():
                self.log("RTDEReceiveInterface 连接失败", "ERROR")
                return False
            self.log("RTDEReceiveInterface 已连接", "SUCCESS")

            # 再连接 Control
            self.log("  连接 RTDEControlInterface...")
            self.rc = RTDEControlInterface(ip)
            if not self.rc.isConnected():
                self.log("RTDEControlInterface 连接失败", "ERROR")
                return False
            self.log("RTDEControlInterface 已连接", "SUCCESS")

            return True

        except Exception as e:
            self.log(f"连接异常: {e}", "ERROR")
            return False

    def disconnect(self):
        """断开连接"""
        if self.rc:
            try:
                self.rc.disconnect()
            except:
                pass
            self.rc = None

        if self.rr:
            try:
                self.rr.disconnect()
            except:
                pass
            self.rr = None

        self.log("已断开连接")

    def is_connected(self) -> bool:
        """检查连接状态"""
        try:
            return (
                self.rc is not None
                and self.rr is not None
                and self.rc.isConnected()
                and self.rr.isConnected()
            )
        except:
            return False

    # ==================== 传感器读取 ====================

    def get_tcp_force(self) -> Optional[List[float]]:
        """获取 TCP 力/力矩 [Fx, Fy, Fz, Mx, My, Mz]"""
        if not self.rr:
            return None
        try:
            return list(self.rr.getActualTCPForce())
        except Exception as e:
            return None

    def get_tcp_pose(self) -> Optional[List[float]]:
        """获取 TCP 位姿 [x, y, z, rx, ry, rz]"""
        if not self.rr:
            return None
        try:
            return list(self.rr.getActualTCPPose())
        except Exception as e:
            return None

    def zero_ft_sensor(self) -> bool:
        """将力传感器归零（消除工具重力等偏置）"""
        if not self.rc:
            return False
        try:
            self.rc.zeroFtSensor()
            self.log("力传感器已归零", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"归零失败: {e}", "ERROR")
            return False

    # ==================== 探测动作 ====================

    def probe_down(self, timeout: float = 60.0) -> ProbeResult:
        """
        向下探测直到接触（优化版，含力稳定检测）
        """
        if not self.rc or not self.rr:
            return ProbeResult(False, error_msg="未连接")

        cfg = self.config
        
        # 获取当前位置
        start_pose = self.get_tcp_pose()
        if not start_pose:
            return ProbeResult(False, error_msg="无法获取当前位置")

        self.log(f"开始探测，起始 Z = {start_pose[2]*1000:.1f} mm")
        self.log(f"  速度: {cfg.approach_speed*1000:.1f} mm/s | 力阈值: {cfg.contact_force_threshold:.1f} N")
        
        if cfg.simulate_mode:
            self.log(f"  [模拟模式] 接触 Z = {cfg.simulate_contact_z*1000:.1f} mm", "WARN")

        t0 = time.time()
        force_history = []  # 用于力稳定检测

        try:
            # 速度向量 [vx, vy, vz, wx, wy, wz]
            speed_vec = [0, 0, -cfg.approach_speed, 0, 0, 0]

            while time.time() - t0 < timeout:
                # 获取当前状态
                force = self.get_tcp_force()
                current_pose = self.get_tcp_pose()
                
                if force is None or current_pose is None:
                    time.sleep(0.008)
                    continue

                fz = force[2]
                current_z = current_pose[2]

                # 检查是否已经移动太远
                moved_distance = start_pose[2] - current_z
                if moved_distance >= cfg.max_approach_distance:
                    self.rc.speedStop()
                    return ProbeResult(False, error_msg=f"已移动 {moved_distance*1000:.1f} mm，未检测到接触")

                # 接触检测
                contact_detected = False
                
                if cfg.simulate_mode:
                    # 模拟模式：用位置阈值
                    if current_z <= cfg.simulate_contact_z:
                        contact_detected = True
                else:
                    # 真实模式：用力阈值
                    if abs(fz) > cfg.contact_force_threshold:
                        contact_detected = True

                if contact_detected:
                    # 接触了！立即停止
                    self.rc.speedStop()
                    
                    # 等待稳定
                    self.log(f"检测到接触，等待稳定 {cfg.settle_time*1000:.0f} ms...")
                    time.sleep(cfg.settle_time)
                    
                    # 力稳定检测
                    stable_pose = self._wait_for_force_stable()
                    if stable_pose is None:
                        stable_pose = self.get_tcp_pose()
                    
                    stable_force = self.get_tcp_force()
                    contact_fz = stable_force[2] if stable_force else fz
                    
                    # 应用 Z 偏移补偿
                    if cfg.z_offset != 0:
                        stable_pose[2] += cfg.z_offset
                        self.log(f"  应用 Z 偏移: {cfg.z_offset*1000:.2f} mm")

                    self.log(f"接触位置: [{stable_pose[0]*1000:.2f}, {stable_pose[1]*1000:.2f}, {stable_pose[2]*1000:.2f}] mm", "SUCCESS")
                    self.log(f"  接触力: Fz = {contact_fz:.2f} N")
                    
                    return ProbeResult(True, pose=stable_pose, contact_force=contact_fz)

                # 发送速度命令（持续向下）
                self.rc.speedL(speed_vec, cfg.approach_accel, 0.1)
                time.sleep(0.008)  # 125 Hz

            # 超时
            self.rc.speedStop()
            return ProbeResult(False, error_msg="探测超时")

        except Exception as e:
            try:
                self.rc.speedStop()
            except:
                pass
            return ProbeResult(False, error_msg=f"探测异常: {e}")

    def _wait_for_force_stable(self, timeout: float = 2.0) -> Optional[List[float]]:
        """等待力稳定，返回稳定时的位姿"""
        cfg = self.config
        t0 = time.time()
        force_history = []
        
        while time.time() - t0 < timeout:
            force = self.get_tcp_force()
            if force:
                force_history.append((time.time(), force[2]))
                
                # 检查最近一段时间的力是否稳定
                recent = [(t, f) for t, f in force_history if time.time() - t < cfg.force_stable_duration]
                if len(recent) >= 5:
                    forces = [f for _, f in recent]
                    if max(forces) - min(forces) < cfg.force_stable_threshold:
                        return self.get_tcp_pose()
            
            time.sleep(0.02)
        
        return None

    def retract(self, distance: float = None) -> bool:
        """回退（向上抬起）"""
        if not self.rc:
            return False

        if distance is None:
            distance = self.config.retract_distance

        current_pose = self.get_tcp_pose()
        if not current_pose:
            return False

        target_pose = current_pose.copy()
        target_pose[2] += distance

        try:
            self.log(f"回退 {distance*1000:.1f} mm...")
            self.rc.moveL(target_pose, 0.1, 0.3)
            return True
        except Exception as e:
            self.log(f"回退失败: {e}", "ERROR")
            return False

    # ==================== 多次测量 ====================

    def probe_with_averaging(self) -> Optional[List[float]]:
        """
        多次探测取平均（提高精度）
        返回平均位置 [x, y, z] 或 None
        """
        cfg = self.config
        n = cfg.probe_repeat_count
        
        self.log(f"开始多次测量 (共 {n} 次)...")
        
        measurements = []
        
        for i in range(n):
            self.log(f"--- 第 {i+1}/{n} 次测量 ---")
            
            result = self.probe_down()
            if not result.success:
                self.log(f"第 {i+1} 次测量失败: {result.error_msg}", "ERROR")
                continue
            
            # 记录
            xyz = [result.pose[0], result.pose[1], result.pose[2]]
            measurements.append(xyz)
            self.log(f"  Z = {xyz[2]*1000:.3f} mm")
            
            # 回退准备下一次
            if i < n - 1:
                self.retract()
                time.sleep(0.3)
        
        if len(measurements) < 1:
            self.log("所有测量均失败", "ERROR")
            return None
        
        # 计算统计
        arr = np.array(measurements)
        mean_xyz = arr.mean(axis=0).tolist()
        
        if len(measurements) >= 2:
            std_xyz = arr.std(axis=0)
            self.log("=" * 40)
            self.log(f"测量完成 ({len(measurements)}/{n} 次成功)")
            self.log(f"  平均 Z: {mean_xyz[2]*1000:.3f} mm")
            self.log(f"  标准差: {std_xyz[2]*1000:.3f} mm")
            self.log(f"  最大偏差: {(arr[:,2].max() - arr[:,2].min())*1000:.3f} mm")
            self.log("=" * 40)
        else:
            self.log(f"测量完成 (仅 1 次)")
            self.log(f"  Z: {mean_xyz[2]*1000:.3f} mm")
        
        return mean_xyz

    # ==================== 标定流程 ====================

    def add_calibration_point_single(self, pose: List[float]):
        """添加单次测量的标定点"""
        point = [pose[0], pose[1], pose[2]]
        cp = CalibrationPoint(measurements=[point])
        self.calibration_points.append(cp)
        self.log(f"已添加第 {len(self.calibration_points)} 个标定点 (单次测量)")

    def add_calibration_point_averaged(self):
        """执行多次测量并添加标定点"""
        mean_xyz = self.probe_with_averaging()
        if mean_xyz:
            cp = CalibrationPoint(measurements=[mean_xyz])
            self.calibration_points.append(cp)
            self.log(f"已添加第 {len(self.calibration_points)} 个标定点 (多次平均)", "SUCCESS")
            self.retract()
            return True
        return False

    def clear_calibration_points(self):
        """清除所有标定点"""
        self.calibration_points = []
        self.log("已清除所有标定点")

    def get_calibration_xyz_list(self) -> List[List[float]]:
        """获取所有标定点的 [x,y,z] 列表"""
        result = []
        for cp in self.calibration_points:
            m = cp.mean
            if m:
                result.append(m)
        return result

    def fit_plane(self) -> Optional[Tuple[str, float]]:
        """
        用最小二乘法拟合平面
        返回: (feature_str, mean_error_mm) 或 None
        """
        points = self.get_calibration_xyz_list()
        if len(points) < 3:
            self.log("错误: 至少需要 3 个点才能拟合平面", "ERROR")
            return None

        P = np.asarray(points, dtype=float)

        # 1. 拟合平面 (SVD)
        centroid = P.mean(axis=0)
        Q = P - centroid
        U, S, Vt = np.linalg.svd(Q, full_matrices=False)
        normal = Vt[-1, :]
        normal = normal / np.linalg.norm(normal)

        # 强制法向朝上 (+Z)
        if np.dot(normal, np.array([0.0, 0.0, 1.0])) < 0:
            normal = -normal

        # 计算残差
        residuals = (P - centroid) @ normal
        mean_err = float(np.mean(np.abs(residuals)))
        max_err = float(np.max(np.abs(residuals)))

        # 2. 构建坐标系 (O-X-Y)
        O = P[0]
        X = P[1]

        z_axis = normal

        vx = X - O
        vx = vx - np.dot(vx, z_axis) * z_axis
        if np.linalg.norm(vx) < 1e-6:
            self.log("错误: O 点和 X 点重合或垂直于平面", "ERROR")
            return None
        x_axis = vx / np.linalg.norm(vx)

        y_axis = np.cross(z_axis, x_axis)
        y_axis = y_axis / np.linalg.norm(y_axis)

        # 3. 构建旋转矩阵
        R = np.column_stack((x_axis, y_axis, z_axis))

        def rotmat_to_axis_angle(R):
            tr = np.trace(R)
            theta = np.arccos(np.clip((tr - 1.0) / 2.0, -1.0, 1.0))
            if abs(theta) < 1e-6:
                return 0.0, 0.0, 0.0

            k = 1.0 / (2.0 * np.sin(theta))
            rx = (R[2, 1] - R[1, 2]) * k
            ry = (R[0, 2] - R[2, 0]) * k
            rz = (R[1, 0] - R[0, 1]) * k

            vec = np.array([rx, ry, rz])
            vec = vec / np.linalg.norm(vec) * theta
            return vec[0], vec[1], vec[2]

        rx, ry, rz = rotmat_to_axis_angle(R)
        tx, ty, tz = O

        feat_str = f"p[{tx:.6f}, {ty:.6f}, {tz:.6f}, {rx:.6f}, {ry:.6f}, {rz:.6f}]"

        # 计算平面倾斜角度
        tilt_angle = math.degrees(math.acos(np.dot(normal, [0, 0, 1])))

        print()
        self.log("=" * 55)
        self.log("              平面拟合结果")
        self.log("=" * 55)
        self.log(f"  标定点数: {len(P)}")
        self.log(f"  平均残差: {mean_err*1000:.3f} mm")
        self.log(f"  最大残差: {max_err*1000:.3f} mm")
        self.log(f"  平面倾斜: {tilt_angle:.2f}°")
        self.log("-" * 55)
        self.log(f"  Feature:")
        self.log(f"    {feat_str}")
        self.log("=" * 55)
        print()

        return feat_str, mean_err * 1000

    # ==================== 交互式界面 ====================

    def show_current_force(self):
        """实时显示力传感器读数"""
        self.log("实时显示力传感器 (按 Ctrl+C 停止)...")
        try:
            while True:
                force = self.get_tcp_force()
                pose = self.get_tcp_pose()
                if force and pose:
                    print(f"\r  Z={pose[2]*1000:+8.2f}mm  "
                          f"Fx={force[0]:+6.2f}  Fy={force[1]:+6.2f}  Fz={force[2]:+6.2f} N    ",
                          end="", flush=True)
                time.sleep(0.05)
        except KeyboardInterrupt:
            print()
            self.log("已停止显示")

    def show_status(self):
        """显示当前状态"""
        cfg = self.config
        
        print()
        self.log("=" * 50)
        self.log("                 当前状态")
        self.log("=" * 50)
        self.log(f"  连接: {'已连接 ✅' if self.is_connected() else '未连接 ❌'}")
        self.log(f"  模式: {'URSim 模拟' if cfg.simulate_mode else '真实力检测'}")

        if self.is_connected():
            pose = self.get_tcp_pose()
            if pose:
                self.log(f"  TCP: [{pose[0]*1000:.1f}, {pose[1]*1000:.1f}, {pose[2]*1000:.1f}] mm")

            force = self.get_tcp_force()
            if force:
                self.log(f"  力:  [Fx={force[0]:.1f}, Fy={force[1]:.1f}, Fz={force[2]:.1f}] N")

        self.log("-" * 50)
        self.log(f"  探测速度: {cfg.approach_speed*1000:.1f} mm/s")
        self.log(f"  力阈值: {cfg.contact_force_threshold:.1f} N")
        self.log(f"  重复次数: {cfg.probe_repeat_count}")
        self.log(f"  Z 偏移: {cfg.z_offset*1000:.2f} mm")
        self.log(f"  标定点数: {len(self.calibration_points)}")
        self.log("=" * 50)
        print()

    def list_calibration_points(self):
        """列出所有标定点"""
        points = self.get_calibration_xyz_list()
        if not points:
            self.log("没有标定点")
            return

        print()
        self.log(f"共 {len(points)} 个标定点:")
        self.log("-" * 50)
        for i, p in enumerate(points):
            self.log(f"  [{i+1}] X={p[0]*1000:8.2f}  Y={p[1]*1000:8.2f}  Z={p[2]*1000:8.2f} mm")
        self.log("-" * 50)
        print()

    def configure_params(self):
        """配置参数子菜单"""
        cfg = self.config
        
        while True:
            print("\n--- 参数配置 ---")
            print(f"  1 - 力阈值: {cfg.contact_force_threshold:.1f} N")
            print(f"  2 - 探测速度: {cfg.approach_speed*1000:.1f} mm/s")
            print(f"  3 - 重复测量次数: {cfg.probe_repeat_count}")
            print(f"  4 - Z 偏移补偿: {cfg.z_offset*1000:.2f} mm")
            print(f"  5 - URSim 模拟模式: {'开启' if cfg.simulate_mode else '关闭'}")
            if cfg.simulate_mode:
                print(f"  6 - 模拟接触 Z 高度: {cfg.simulate_contact_z*1000:.1f} mm")
            print()
            print("  P - 使用高精度预设 (3N, 5mm/s, 3次)")
            print("  F - 使用快速预设 (5N, 10mm/s, 1次)")
            print()
            print("  B - 返回主菜单")

            try:
                choice = input("\n请选择: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "B":
                break
            elif choice == "1":
                try:
                    val = float(input(f"力阈值 (N) [{cfg.contact_force_threshold}]: ").strip() or cfg.contact_force_threshold)
                    cfg.contact_force_threshold = val
                    self.log(f"力阈值已设为 {val} N")
                except:
                    pass
            elif choice == "2":
                try:
                    val = float(input(f"探测速度 (mm/s) [{cfg.approach_speed*1000}]: ").strip() or cfg.approach_speed*1000)
                    cfg.approach_speed = val / 1000.0
                    self.log(f"探测速度已设为 {val} mm/s")
                except:
                    pass
            elif choice == "3":
                try:
                    val = int(input(f"重复测量次数 [{cfg.probe_repeat_count}]: ").strip() or cfg.probe_repeat_count)
                    cfg.probe_repeat_count = max(1, val)
                    self.log(f"重复测量次数已设为 {cfg.probe_repeat_count}")
                except:
                    pass
            elif choice == "4":
                try:
                    val = float(input(f"Z 偏移 (mm) [{cfg.z_offset*1000}]: ").strip() or cfg.z_offset*1000)
                    cfg.z_offset = val / 1000.0
                    self.log(f"Z 偏移已设为 {val} mm")
                except:
                    pass
            elif choice == "5":
                cfg.simulate_mode = not cfg.simulate_mode
                self.log(f"URSim 模拟模式: {'开启' if cfg.simulate_mode else '关闭'}")
            elif choice == "6" and cfg.simulate_mode:
                try:
                    val = float(input(f"模拟接触 Z (mm) [{cfg.simulate_contact_z*1000}]: ").strip() or cfg.simulate_contact_z*1000)
                    cfg.simulate_contact_z = val / 1000.0
                    self.log(f"模拟接触 Z 已设为 {val} mm")
                except:
                    pass
            elif choice == "P":
                cfg.contact_force_threshold = 3.0
                cfg.approach_speed = 0.005
                cfg.probe_repeat_count = 3
                self.log("已应用高精度预设", "SUCCESS")
            elif choice == "F":
                cfg.contact_force_threshold = 5.0
                cfg.approach_speed = 0.01
                cfg.probe_repeat_count = 1
                self.log("已应用快速预设", "SUCCESS")

    def run_interactive(self):
        """交互式测试主循环"""
        print()
        print("=" * 60)
        print("       力控探测法 - 平面标定测试程序 (优化版)")
        print("       适用于 UR5 CB3 系列")
        print("=" * 60)
        print()
        print("  优化功能:")
        print("    - 多次测量取平均（提高精度）")
        print("    - 力稳定检测")
        print("    - URSim 模拟模式")
        print("    - Z 偏移补偿")
        print()

        while True:
            print("\n" + "=" * 40)
            print("              主菜单")
            print("=" * 40)
            print("  C - 连接机器人")
            print("  D - 断开连接")
            print("  S - 查看状态")
            print()
            print("  F - 实时显示力传感器")
            print("  Z - 力传感器归零")
            print()
            print("  P - 单次探测")
            print("  M - 多次探测取平均")
            print("  R - 回退")
            print()
            print("  A - 单次探测并添加标定点")
            print("  W - 多次探测并添加标定点 (推荐)")
            print("  L - 列出所有标定点")
            print("  X - 清除标定点")
            print("  T - 拟合平面")
            print()
            print("  O - 参数配置")
            print("  Q - 退出")
            print("=" * 40)

            try:
                choice = input("\n请选择: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "Q":
                break
            elif choice == "C":
                ip = input("输入机器人 IP [192.168.1.101]: ").strip()
                if not ip:
                    ip = "192.168.1.101"
                self.connect(ip)
            elif choice == "D":
                self.disconnect()
            elif choice == "S":
                self.show_status()
            elif choice == "F":
                if self.is_connected():
                    self.show_current_force()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "Z":
                if self.is_connected():
                    self.zero_ft_sensor()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "P":
                if self.is_connected():
                    self.probe_down()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "M":
                if self.is_connected():
                    self.probe_with_averaging()
                    self.retract()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "R":
                if self.is_connected():
                    self.retract()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "A":
                if self.is_connected():
                    result = self.probe_down()
                    if result.success:
                        self.add_calibration_point_single(result.pose)
                        self.retract()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "W":
                if self.is_connected():
                    self.add_calibration_point_averaged()
                else:
                    self.log("请先连接机器人", "WARN")
            elif choice == "L":
                self.list_calibration_points()
            elif choice == "X":
                self.clear_calibration_points()
            elif choice == "T":
                self.fit_plane()
            elif choice == "O":
                self.configure_params()
            else:
                self.log("无效选项")

        self.disconnect()
        print("\n再见！")


def main():
    tester = ForceCalibrationTester()
    tester.run_interactive()


if __name__ == "__main__":
    main()
