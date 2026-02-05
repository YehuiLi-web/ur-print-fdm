# core/driver.py
import time
import logging
import socket
import math
import threading
import os
import re

from ur_print_fdm.constants import DASHBOARD_PORT, SCRIPT_PORT
from ur_print_fdm.config import config_manager
from ur_print_fdm.core.script_sanitizer import sanitize_script_content
from ur_print_fdm.shared.net import is_valid_ip

# === 引入官方库 ===
# 我们尝试多种导入方式，以兼容不同的环境配置
try:
    from rtde_control import RTDEControlInterface
    from rtde_receive import RTDEReceiveInterface
    from dashboard_client import DashboardClient
except ImportError:
    try:
        # 备用导入方式 (针对某些特殊的 PYTHONPATH 设置)
        from rtde_control import RTDEControlInterface
        from rtde_receive import RTDEReceiveInterface
        from dashboard_client import DashboardClient
    except ImportError:
        RTDEControlInterface = None
        RTDEReceiveInterface = None
        DashboardClient = None
class URDriver:
    def __init__(self):
        self.rc = None # Control Interface (运动控制: moveL, moveJ, 脚本发送)
        self.rr = None # Receive Interface (数据读取: 位置, 速度, IO)
        self.db = None # Dashboard Client (系统控制: 暂停, 继续, 急停, 弹窗)

        self.connected = False
        self.ip_address = ""
        self.read_only = False # 标记是否处于只读模式
        self._lock = threading.RLock()  # 用于线程安全的可重入锁

        # === CB3 特性配置 ===
        self.FREQUENCY = 125.0  # CB3 控制频率 125Hz
        self.DT = 1.0 / self.FREQUENCY

    def connect(self, ip, log_callback=None):
        """
        连接机器人 (官方库重构版)
        连接顺序：
        1. Receive (30004) - 必须成功，用于读取状态。
        2. Dashboard (29999) - 必须成功，用于系统控制 (暂停/继续)。
        3. Control (30004) - 可选，失败则降级为只读模式。
        """
        # 验证IP地址
        if not is_valid_ip(ip):
            error_msg = f"无效的IP地址格式: {ip}"
            if log_callback:
                log_callback(error_msg)
            else:
                print(error_msg)
            return False

        def log(msg):
            if log_callback: log_callback(msg)
            else: print(msg)

        if RTDEReceiveInterface is None or DashboardClient is None:
            raise ImportError("请确保安装了 ur_rtde: pip install ur_rtde")

        # 获取锁以确保线程安全
        with self._lock:
            self.ip_address = ip
            log(f"[连接] 开始连接机器人 {ip} ...")

            # === 1. 连接数据接收端 (RTDE Receive) ===
            try:
                log("[RTDE] 连接数据接口 (RTDE Receive)...")
                self.rr = RTDEReceiveInterface(self.ip_address)
                if self.rr.isConnected():
                    self.connected = True
                    log("数据接口连接成功！")
                else:
                    raise ConnectionError("数据接口连接后立即断开")
            except Exception as e:
                log(f"数据接口连接失败: {e}")
                self.connected = False
                return False

            # === 2. 连接仪表盘服务 (Dashboard) ===
            # 官方 DashboardClient 会自动处理 CB3 的欢迎语握手，非常稳定
            try:
                log("连接仪表盘 (Dashboard)...")
                self.db = DashboardClient(self.ip_address)
                self.db.connect()
                if self.db.isConnected():
                    log("仪表盘服务连接成功！(支持暂停/继续)")
                else:
                    raise ConnectionError("仪表盘连接失败")
            except Exception as e:
                log(f"仪表盘连接失败: {e}")
                log("系统将无法使用【暂停/继续】功能，但仍可监视。")
                self.db = None
                # 注意：Dashboard 失败不阻断主流程，只是功能受限

            # === 3. 连接运动控制端 (RTDE Control) ===
            try:
                log("连接运动接口 (RTDE Control)...")
                # flags: UPLOAD_SCRIPT 用于发送自定义脚本
                self.rc = RTDEControlInterface(self.ip_address, RTDEControlInterface.FLAG_UPLOAD_SCRIPT)

                if self.rc.isConnected():
                    self.read_only = False
                    log("运动接口连接成功！(读写模式)")
                else:
                    raise ConnectionError("运动接口未就绪")
            except Exception as e:
                log(f"运动接口连接被拒绝 ({e})")
                log("提示：可能是机器人端连接数已满，请重启机器人。")
                log("已切换为【只读模式】，仅用于监视。")
                self.rc = None
                self.read_only = True

            return True

    def disconnect(self):
        """安全断开所有连接"""
        with self._lock:
            if self.rc:
                try: self.rc.disconnect()
                except Exception as e: logging.debug(f"断开控制接口时忽略异常: {e}")
            if self.rr:
                try: self.rr.disconnect()
                except Exception as e: logging.debug(f"断开接收接口时忽略异常: {e}")
            if self.db:
                try: self.db.disconnect()
                except Exception as e: logging.debug(f"断开仪表盘接口时忽略异常: {e}")

            self.rc = None
            self.rr = None
            self.db = None
            self.connected = False
            self.read_only = False

    # === FDM 打印专用功能 (CB3 优化) ===

    def sync_print_move(self, pose, speed=0.05, acceleration=0.5, extruder_active=False, blend_radius=0.0):
        """
        FDM 打印同步运动指令 (CB3 优化版)
        将挤出机 IO 控制与运动指令打包发送，确保严格同步。

        :param pose: [x,y,z,rx,ry,rz] 目标位姿
        :param speed: 打印速度 (m/s)
        :param acceleration: 加速度 (m/s^2)
        :param extruder_active: 挤出机状态 (True=挤出, False=回抽/停止)
        :param blend_radius: 交融半径 (m)，FDM 连续打印建议 > 0 (如 0.001)
        :return: True if sent successfully
        """
        with self._lock:
            if not self.rc or self.read_only or not self.connected:
                logging.error("无法发送打印指令：未连接或只读模式")
                return False

        # 构建原子操作脚本
        # 使用配置的挤出 DO 引脚（默认 0）
        # 注意：实际生产中可能需要控制 PWM 或 Modbus，此处以数字 IO 为例
        io_state = "True" if extruder_active else "False"
        do_pin = int(config_manager.get("printing.extruder_io_pin", 0) or 0)
        pose_str = f"p[{','.join(map(str, pose))}]"

        script = f"""
        def print_step():
            set_standard_digital_out({do_pin}, {io_state})
            movel({pose_str}, a={acceleration}, v={speed}, r={blend_radius})
        end
        """

        # 使用 sendCustomScript 发送
        try:
            return self.rc.sendCustomScript(script)
        except Exception as e:
            logging.error(f"发送打印指令失败: {e}")
            return False

    def stop_immediately(self):
        """
        FDM 专用急停 (优先切断挤出，保护模型)
        """
        logging.warning("执行 FDM 紧急停止...")

        # 1. 立即切断 IO (防止漏料)
        modbus_name = str(config_manager.get("printing.modbus_extruder", "MODBUS_1") or "").strip()
        do_pin = int(config_manager.get("printing.extruder_io_pin", 0) or 0)
        kill_lines = ["sec kill_io():\n"]
        if modbus_name:
            kill_lines.append(f'  modbus_set_output_register("{modbus_name}", 0)\n')
        kill_lines.append(f"  set_standard_digital_out({do_pin}, False)\n")
        kill_lines.append("end\n")
        kill_io_script = "".join(kill_lines)
        try:
            if self.rc and self.rc.isConnected():
                self.rc.sendCustomScript(kill_io_script)
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((self.ip_address, SCRIPT_PORT))
                s.sendall(kill_io_script.encode("utf-8"))
                s.close()
        except Exception:
            pass

        # 2. 调用标准停止
        self.stop()

        # 3. 再次确保 dashboard 停止
        if self.db:
            try: self.db.stop()
            except: pass

    # === 线程安全的状态访问器 ===
    def is_connected(self):
        """线程安全地检查是否已连接"""
        with self._lock:
            return self.connected

    def is_read_only(self):
        """线程安全地检查是否处于只读模式"""
        with self._lock:
            return self.read_only

    def get_ip_address(self):
        """线程安全地获取 IP 地址"""
        with self._lock:
            return self.ip_address

    # === 状态读取 ===
    def get_status(self):
        """返回 (TCP_Pose, Joint_Angles, TCP_Offset, Speed_Mag)"""
        # 获取引用副本以避免在锁内进行网络调用
        with self._lock:
            if not self.rr or not self.connected:
                return None, None, None, 0.0
            rr_ref = self.rr  # 获取引用副本

        try:
            # 现在在锁外检查连接状态
            if not rr_ref.isConnected():
                return None, None, None, 0.0

            tcp = rr_ref.getActualTCPPose()
            joints = rr_ref.getActualQ()

            # 计算速度模长
            speed_vec = rr_ref.getActualTCPSpeed()
            speed_mag = 0.0
            if speed_vec:
                speed_mag = math.sqrt(sum(x**2 for x in speed_vec[:3]))

            # 尝试获取 offset
            tcp_offset = [0.0]*6
            try:
                val = rr_ref.getTcpOffset()
                if val: tcp_offset = val
            except Exception as e:
                logging.debug(f"get_status: 获取TCP offset失败: {e}")

            return tcp, joints, tcp_offset, speed_mag
        except Exception as e:
            logging.error(f"get_status: 获取机器人状态失败: {e}")
            return None, None, None, 0.0

    # === 运动指令发送 ===
    def send_script(self, script_str):
        """
        发送并立即执行脚本。

        返回: (success: bool, warning: str | None)
            - success: 是否发送成功
            - warning: 警告信息（如检测到可能缺少函数调用）
        """
        warning = None
        func_name = None

        # 检测是否可能缺少函数调用（不自动追加，只警告）
        stripped_script = script_str.strip()
        if stripped_script.startswith("def "):
            match = re.match(r"def\s+(\w+)\s*\(", stripped_script)
            if match:
                func_name = match.group(1)
                # 检查脚本中是否包含对该函数的调用
                # 使用正则匹配独立的函数调用（不在 def 行内）
                call_pattern = rf"(?<!def\s)(?<!\w){re.escape(func_name)}\s*\(\s*\)"
                if not re.search(call_pattern, stripped_script):
                    warning = f"检测到脚本定义了函数 '{func_name}' 但可能未调用，脚本可能不会执行任何操作"
                    logging.warning(warning)

        sanitized_script = sanitize_script_content(script_str)

        with self._lock:
            if not self.connected or self.read_only or not self.rc:
                logging.error("无法发送：处于只读模式或未连接")
                return False, None
            rc_ref = self.rc

        try:
            logging.debug(f"发送脚本至控制器: {func_name if func_name else 'Raw Script'}")
            success = rc_ref.sendCustomScript(sanitized_script)
            return success, warning
        except Exception as e:
            logging.error(f"发送脚本异常: {e}")
            return False, None

    # === Dashboard 系统控制 (官方库实现) ===

    def pause(self):
        """暂停程序 (通过 Dashboard)"""
        if self.db and self.db.isConnected():
            try:
                self.db.pause()
                return True
            except Exception as e:
                logging.error(f"Dashboard pause failed: {e}")
        return False

    def resume(self):
        """继续程序 (通过 Dashboard)"""
        if self.db and self.db.isConnected():
            try:
                self.db.play() # Dashboard 的 play 指令即为继续
                return True
            except Exception as e:
                logging.error(f"Dashboard play/resume failed: {e}")
        return False

    def _ensure_dashboard_connection(self):
        """辅助函数：确保 Dashboard 连接可用"""
        if not self.db:
            # 尝试重新实例化
            try:
                logging.debug("_ensure_dashboard_connection: 重新实例化DashboardClient")
                self.db = DashboardClient(self.ip_address)
            except Exception as e:
                logging.warning(f"_ensure_dashboard_connection: 无法实例化DashboardClient: {e}")
                return False

        # 检查当前连接状态
        if not self.db.isConnected():
            try:
                logging.debug(f"_ensure_dashboard_connection: Dashboard当前状态: {self.db.isConnected()}")
                logging.debug("_ensure_dashboard_connection: 尝重新连接Dashboard...")
                self.db.connect()
                connected = self.db.isConnected()
                if connected:
                    logging.info(f"_ensure_dashboard_connection: Dashboard连接成功，状态: {self.db.isConnected()}")
                else:
                    logging.warning("_ensure_dashboard_connection: Dashboard连接失败")
                return connected
            except Exception as e:
                logging.warning(f"_ensure_dashboard_connection: Dashboard连接异常: {e}")
                return False
        return True

    def _dashboard_socket_command(self, command: str, *, timeout: float = 5.0) -> str | None:
        """Send a raw Dashboard (29999) command and return response string.

        Notes (CB3/URSim):
        - Dashboard is a text protocol. Each command is one line ending with `\\n`.
        - Responses vary across PolyScope versions; callers should parse defensively.
        """
        with self._lock:
            ip = str(self.ip_address or "").strip()
        if not ip:
            logging.error("dashboard: No IP address set")
            return None

        cmd = str(command or "").strip()
        if not cmd:
            return None

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(float(timeout))
        try:
            s.connect((ip, DASHBOARD_PORT))
            try:
                s.recv(1024)  # welcome
            except Exception:
                pass
            s.sendall((cmd + "\n").encode("utf-8"))
            return s.recv(4096).decode("utf-8", errors="replace").strip()
        except Exception as e:
            logging.error("dashboard socket command failed (%s): %s", cmd, e)
            return None
        finally:
            try:
                s.close()
            except Exception:
                pass

    def upload_program_file(self, local_file_path, remote_filename=None):
        """
        Upload a file to the robot program directory via SFTP.

        This is the correct mechanism for CB3/URSim when you want PolyScope to `load` a program/script
        and then control it via Dashboard (`play/pause/stop`).
        """
        if not self.ip_address:
            logging.error("upload_program_file: No IP address set")
            return False

        if remote_filename is None:
            remote_filename = os.path.basename(local_file_path)

        try:
            import paramiko

            remote_dir = str(
                config_manager.get("robot.sftp.remote_dir", "/home/ur/ursim-current/programs") or ""
            ).rstrip("/")
            username = str(config_manager.get("robot.sftp.username", "ur") or "ur")
            password = str(config_manager.get("robot.sftp.password", "easybot") or "easybot")
            port = int(config_manager.get("robot.sftp.port", 22) or 22)

            remote_path = f"{remote_dir}/{remote_filename}"

            transport = paramiko.Transport((self.ip_address, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(local_file_path, remote_path)
            sftp.close()
            transport.close()
            return True
        except Exception as e:
            logging.error(f"upload_program_file failed: {e}")
            return False

    def load_program(self, program_name):
        """
        Load a program from the robot's programs directory
        :param program_name: Program path (URSim/CB3 recommended: full path under programs dir)
        :return: True if successful, False otherwise
        """
        try:
            resp = self._dashboard_socket_command(f"load {program_name}", timeout=5.0)
            if resp is None:
                return False
            low = resp.lower()
            if any(k in low for k in ("error", "failed", "not found", "no such")):
                logging.error("load_program failed: %s", resp)
                return False
            return True
        except Exception as e:
            logging.error(f"load_program failed: {e}")
            return False

    def get_loaded_program(self):
        """
        Get the name of the currently loaded program
        :return: Program name or None
        """
        try:
            response = self._dashboard_socket_command("get loaded program", timeout=5.0) or ""
            # Parse response to extract program name
            if "loaded program:" in response.lower():
                return response.split(":")[1].strip()
            return None
        except Exception as e:
            logging.error(f"get_loaded_program failed: {e}")
            return None

    def reset_robot_state(self):
        """重置机器人状态，尝试恢复Dashboard功能"""
        logging.info("reset_robot_state: 尝试重置机器人状态...")

        # 使用锁确保线程安全
        with self._lock:
            # 断开所有连接并重新连接
            try:
                # 使用disconnect方法，它会安全地断开所有连接并清理变量
                self.disconnect()
            except Exception as e:
                logging.debug(f"reset_robot_state: 断开连接时忽略异常: {e}")

            # 重新连接
            try:
                self.connect(self.ip_address)
                logging.info("reset_robot_state: 重新连接成功")
                return True
            except Exception as e:
                logging.error(f"reset_robot_state: 重新连接失败: {e}")
                return False

    def stop(self):
        """强制停止 (Dashboard stop + 关闭挤出 + stopj)，尽量适配 CB3 只读模式。"""
        import threading

        def stop_with_timeout(func, timeout=2.0):
            """Execute a function with timeout"""
            result = [None]
            exception = [None]

            def target():
                try:
                    result[0] = func()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)

            if thread.is_alive():
                logging.warning("stop: Operation timed out")
                return False
            if exception[0]:
                logging.error(f"stop: Operation failed: {exception[0]}")
                return False
            return result[0]

        with self._lock:
            ip = str(self.ip_address or "").strip()
            db = self.db
            rc = self.rc

        if not ip:
            return False

        any_ok = False

        # 1. Dashboard stop with timeout
        if db and db.isConnected():
            try:
                res = stop_with_timeout(lambda: db.stop(), timeout=2.0)
                if res is not False:
                    any_ok = True
                    logging.info("Dashboard 停止指令已发送")
                else:
                    logging.warning("Dashboard 停止指令超时或失败")
            except Exception as e:
                logging.error(f"Dashboard 停止失败: {e}")

        # 2. IO kill (cut extrusion) with timeout
        modbus_name = str(config_manager.get("printing.modbus_extruder", "MODBUS_1") or "").strip()
        do_pin = int(config_manager.get("printing.extruder_io_pin", 0) or 0)
        kill_lines = ["sec kill_io():\n"]
        if modbus_name:
            kill_lines.append(f'  modbus_set_output_register("{modbus_name}", 0)\n')
        kill_lines.append(f"  set_standard_digital_out({do_pin}, False)\n")
        kill_lines.append("end\n")
        stop_script = "".join(kill_lines)

        try:
            if rc and rc.isConnected():
                res = stop_with_timeout(lambda: rc.sendCustomScript(stop_script), timeout=2.0)
                if res is not False:
                    any_ok = True
                    logging.debug("stop: 通过RTDE发送停止脚本")
                else:
                    logging.debug("stop: RTDE停止脚本发送超时或失败")
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((ip, SCRIPT_PORT))
                s.sendall(stop_script.encode("utf-8"))
                s.close()
                any_ok = True
                logging.debug("stop: 通过原始socket发送停止脚本")
        except Exception as e:
            logging.debug(f"stop: 发送停止脚本时忽略异常: {e}")

        # 3. Emergency stop (stopj) best-effort
        emergency_script = "sec emerg():\n  stopj(1.0)\nend\n"
        try:
            if rc and rc.isConnected():
                res = stop_with_timeout(lambda: rc.sendCustomScript(emergency_script), timeout=2.0)
                if res is not False:
                    any_ok = True
                    logging.debug("stop: 发送紧急停止命令")
                else:
                    logging.debug("stop: 紧急停止命令发送超时或失败")
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect((ip, SCRIPT_PORT))
                s.sendall(emergency_script.encode("utf-8"))
                s.close()
                any_ok = True
        except Exception as e:
            logging.debug(f"stop: 发送紧急停止命令时忽略异常: {e}")

        return any_ok

    def reconnect_control_interface(self, log_callback=None):
        """单独重连控制接口"""
        def log(msg):
            if log_callback: log_callback(msg)
            else: print(msg)

        with self._lock:
            if not self.ip_address: return False

            try:
                if self.rc:
                    try: self.rc.disconnect()
                    except: pass

                log("重连控制接口...")
                self.rc = RTDEControlInterface(self.ip_address, RTDEControlInterface.FLAG_UPLOAD_SCRIPT)
                if self.rc.isConnected():
                    self.read_only = False
                    log("控制接口恢复！")
                    return True
            except Exception as e:
                log(f"重连失败: {e}")
                self.read_only = True
                return False

    # === 新增：运动控制方法 (来自 RTDE Control API) ===

    def move_j(self, q, speed=1.05, acceleration=1.4, asynchronous=False):
        """
        Move to joint position (linear in joint-space)
        :param q: joint positions [6 values]
        :param speed: joint speed of leading axis [rad/s]
        :param acceleration: joint acceleration of leading axis [rad/s²]
        :param asynchronous: specify if move should be asynchronous
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot move_j: control interface not available")
                return False
        try:
            return self.rc.moveJ(q, speed, acceleration, asynchronous)
        except Exception as e:
            logging.error(f"move_j failed: {e}")
            return False

    def move_l(self, pose, speed=0.25, acceleration=1.2, asynchronous=False):
        """
        Move to position (linear in tool-space)
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param speed: tool speed [m/s]
        :param acceleration: tool acceleration [m/s²]
        :param asynchronous: specify if move should be asynchronous
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot move_l: control interface not available")
                return False
        try:
            return self.rc.moveL(pose, speed, acceleration, asynchronous)
        except Exception as e:
            logging.error(f"move_l failed: {e}")
            return False

    def move_j_ik(self, pose, speed=1.05, acceleration=1.4, asynchronous=False):
        """
        Move to pose (linear in joint-space) using inverse kinematics
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param speed: joint speed of leading axis [rad/s]
        :param acceleration: joint acceleration of leading axis [rad/s²]
        :param asynchronous: specify if move should be asynchronous
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot move_j_ik: control interface not available")
                return False
        try:
            return self.rc.moveJ_IK(pose, speed, acceleration, asynchronous)
        except Exception as e:
            logging.error(f"move_j_ik failed: {e}")
            return False

    def move_l_fk(self, q, speed=0.25, acceleration=1.2, asynchronous=False):
        """
        Move to position (linear in tool-space) from joint positions using forward kinematics
        :param q: joint positions [6 values]
        :param speed: tool speed [m/s]
        :param acceleration: tool acceleration [m/s²]
        :param asynchronous: specify if move should be asynchronous
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot move_l_fk: control interface not available")
                return False
        try:
            return self.rc.moveL_FK(q, speed, acceleration, asynchronous)
        except Exception as e:
            logging.error(f"move_l_fk failed: {e}")
            return False

    def servo_j(self, q, speed, acceleration, time, lookahead_time, gain):
        """
        Servo to position (linear in joint-space)
        :param q: joint positions [6 values]
        :param speed: joint speed [rad/s]
        :param acceleration: joint acceleration [rad/s²]
        :param time: time to the next point [s]
        :param lookahead_time: time [s], range [0.03, 0.2] smoothens the trajectory with lookahead
        :param gain: proportional gain for following target position, range [100, 2000]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot servo_j: control interface not available")
                return False
        try:
            return self.rc.servoJ(q, speed, acceleration, time, lookahead_time, gain)
        except Exception as e:
            logging.error(f"servo_j failed: {e}")
            return False

    def servo_l(self, pose, speed, acceleration, time, lookahead_time, gain):
        """
        Servo to position (linear in tool-space)
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param speed: tool speed [m/s]
        :param acceleration: tool acceleration [m/s²]
        :param time: time to the next point [s]
        :param lookahead_time: time [s], range [0.03, 0.2] smoothens the trajectory with lookahead
        :param gain: proportional gain for following target position, range [100, 2000]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot servo_l: control interface not available")
                return False
        try:
            return self.rc.servoL(pose, speed, acceleration, time, lookahead_time, gain)
        except Exception as e:
            logging.error(f"servo_l failed: {e}")
            return False

    def speed_j(self, qd, acceleration=0.5, time=0.0):
        """
        Joint speed - Accelerate linearly in joint space and continue with constant joint speed
        :param qd: joint speeds [6 values, rad/s]
        :param acceleration: joint acceleration [rad/s²]
        :param time: time [s] before the speed is ramped down to zero with acceleration, 0 = infinite
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot speed_j: control interface not available")
                return False
        try:
            return self.rc.speedJ(qd, acceleration, time)
        except Exception as e:
            logging.error(f"speed_j failed: {e}")
            return False

    def speed_l(self, xd, acceleration=0.25, time=0.0):
        """
        Tool speed - Accelerate linearly in Cartesian space and continue with constant tool speed
        :param xd: tool speed [x,y,z,rx,ry,rz] [6 values, m/s & rad/s]
        :param acceleration: tool acceleration [m/s²]
        :param time: time [s] before the speed is ramped down to zero with acceleration, 0 = infinite
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot speed_l: control interface not available")
                return False
        try:
            return self.rc.speedL(xd, acceleration, time)
        except Exception as e:
            logging.error(f"speed_l failed: {e}")
            return False

    def stop_j(self, a=2.0, asynchronous=False):
        """
        Stop (linear in joint space) - decelerate joint speeds to zero
        :param a: joint acceleration [rad/s²]
        :param asynchronous: specify if stop should be asynchronous
        :return: None
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot stop_j: control interface not available")
                return False
        try:
            self.rc.stopJ(a, asynchronous)
            return True
        except Exception as e:
            logging.error(f"stop_j failed: {e}")
            return False

    def stop_l(self, a=10.0, asynchronous=False):
        """
        Stop (linear in tool space) - decelerate tool speed to zero
        :param a: tool acceleration [m/s²]
        :param asynchronous: specify if stop should be asynchronous
        :return: None
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot stop_l: control interface not available")
                return False
        try:
            self.rc.stopL(a, asynchronous)
            return True
        except Exception as e:
            logging.error(f"stop_l failed: {e}")
            return False

    def servo_c(self, pose, speed=0.25, acceleration=1.2, blend=0.0):
        """
        Servo to position (circular in tool-space)
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param speed: tool speed [m/s]
        :param acceleration: tool acceleration [m/s²]
        :param blend: blend radius [m]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot servo_c: control interface not available")
                return False
        try:
            return self.rc.servoC(pose, speed, acceleration, blend)
        except Exception as e:
            logging.error(f"servo_c failed: {e}")
            return False

    def servo_stop(self, a=10.0):
        """
        Stop servo mode and decelerate the robot
        :param a: tool acceleration [m/s²]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot servo_stop: control interface not available")
                return False
        try:
            return self.rc.servoStop(a)
        except Exception as e:
            logging.error(f"servo_stop failed: {e}")
            return False

    def speed_stop(self, a=10.0):
        """
        Stop speed mode and decelerate the robot
        :param a: tool acceleration [m/s²]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot speed_stop: control interface not available")
                return False
        try:
            return self.rc.speedStop(a)
        except Exception as e:
            logging.error(f"speed_stop failed: {e}")
            return False

    # === 新增：力控和高级功能 ===

    def force_mode(self, task_frame, selection_vector, wrench, type, limits):
        """
        Set robot to be controlled in force mode
        :param task_frame: [x,y,z,rx,ry,rz] pose vector
        :param selection_vector: [x,y,z,rx,ry,rz] 6d vector of 0s and 1s defining which directions the robot is compliant in
        :param wrench: [x,y,z,rx,ry,rz] 6d vector of forces/torques to apply
        :param type: Type of compliance: 0=stiff, 1=selective compliance, 2=force/vision
        :param limits: [x,y,z,rx,ry,rz] 6d vector of maximum allowed deviations in compliance
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot force_mode: control interface not available")
                return False
        try:
            return self.rc.forceMode(task_frame, selection_vector, wrench, type, limits)
        except Exception as e:
            logging.error(f"force_mode failed: {e}")
            return False

    def force_mode_stop(self):
        """
        Reset robot mode from force mode to normal operation
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot force_mode_stop: control interface not available")
                return False
        try:
            return self.rc.forceModeStop()
        except Exception as e:
            logging.error(f"force_mode_stop failed: {e}")
            return False

    def force_mode_set_damping(self, damping):
        """
        Sets the damping parameter in force mode
        :param damping: Damping factor in range [0.0, 1.0]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot force_mode_set_damping: control interface not available")
                return False
        try:
            return self.rc.forceModeSetDamping(damping)
        except Exception as e:
            logging.error(f"force_mode_set_damping failed: {e}")
            return False

    def force_mode_set_gain_scaling(self, scaling):
        """
        Scales the gain in force mode
        :param scaling: Scaling factor in range [0.1, 10.0]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot force_mode_set_gain_scaling: control interface not available")
                return False
        try:
            return self.rc.forceModeSetGainScaling(scaling)
        except Exception as e:
            logging.error(f"force_mode_set_gain_scaling failed: {e}")
            return False

    def jog_start(self, speeds, feature=2, acc=0.5, custom_frame=[]):
        """
        Starts jogging with the given speed vector with respect to the given feature
        :param speeds: [x,y,z,rx,ry,rz] 6d velocity vector in m/s and rad/s
        :param feature: Reference frame (FEATURE_BASE=0, FEATURE_TOOL=1, FEATURE_CUSTOM=2)
        :param acc: Acceleration [m/s^2]
        :param custom_frame: [x,y,z,rx,ry,rz] pose vector for custom feature frame
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot jog_start: control interface not available")
                return False
        try:
            return self.rc.jogStart(speeds, feature, acc, custom_frame)
        except Exception as e:
            logging.error(f"jog_start failed: {e}")
            return False

    def jog_stop(self):
        """
        Stops jogging that has been started
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot jog_stop: control interface not available")
                return False
        try:
            return self.rc.jogStop()
        except Exception as e:
            logging.error(f"jog_stop failed: {e}")
            return False

    def teach_mode(self):
        """
        Set robot in freedrive mode (teach mode)
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot teach_mode: control interface not available")
                return False
        try:
            return self.rc.teachMode()
        except Exception as e:
            logging.error(f"teach_mode failed: {e}")
            return False

    def end_teach_mode(self):
        """
        Set robot back in normal position control mode after freedrive mode
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot end_teach_mode: control interface not available")
                return False
        try:
            return self.rc.endTeachMode()
        except Exception as e:
            logging.error(f"end_teach_mode failed: {e}")
            return False

    def freedrive_mode(self, free_axes=[1, 1, 1, 1, 1, 1], feature=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]):
        """
        Set robot in freedrive mode with specific axes freedom
        :param free_axes: [x,y,z,rx,ry,rz] 6d vector of 0s and 1s defining which axes are free
        :param feature: [x,y,z,rx,ry,rz] pose vector for the feature frame
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot freedrive_mode: control interface not available")
                return False
        try:
            return self.rc.freedriveMode(free_axes, feature)
        except Exception as e:
            logging.error(f"freedrive_mode failed: {e}")
            return False

    def end_freedrive_mode(self):
        """
        Set robot back in normal position control mode after freedrive mode
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot end_freedrive_mode: control interface not available")
                return False
        try:
            return self.rc.endFreedriveMode()
        except Exception as e:
            logging.error(f"end_freedrive_mode failed: {e}")
            return False

    # === 新增：TCP、负载和校准功能 ===

    def set_tcp(self, tcp_offset):
        """
        Sets the active TCP offset
        :param tcp_offset: [x,y,z,rx,ry,rz] TCP offset vector
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot set_tcp: control interface not available")
                return False
        try:
            return self.rc.setTcp(tcp_offset)
        except Exception as e:
            logging.error(f"set_tcp failed: {e}")
            return False

    def get_tcp_offset(self):
        """
        Gets the active TCP offset
        :return: [x,y,z,rx,ry,rz] TCP offset vector or None if failed
        """
        with self._lock:
            if not self.rr:
                logging.error("Cannot get_tcp_offset: receive interface not available")
                return None
        try:
            return self.rr.getTcpOffset()
        except Exception as e:
            logging.error(f"get_tcp_offset failed: {e}")
            return None

    def get_tcp_force(self):
        """
        Gets the TCP force/torque from the builtin force/torque sensor
        :return: [Fx, Fy, Fz, Mx, My, Mz] force/torque vector or None if failed
        """
        with self._lock:
            if not self.rr:
                logging.error("Cannot get_tcp_force: receive interface not available")
                return None
            rr_ref = self.rr
        try:
            return list(rr_ref.getActualTCPForce())
        except Exception as e:
            logging.error(f"get_tcp_force failed: {e}")
            return None

    def get_tcp_pose(self):
        """
        Gets the actual TCP pose
        :return: [x, y, z, rx, ry, rz] pose vector or None if failed
        """
        with self._lock:
            if not self.rr:
                logging.error("Cannot get_tcp_pose: receive interface not available")
                return None
            rr_ref = self.rr
        try:
            return list(rr_ref.getActualTCPPose())
        except Exception as e:
            logging.error(f"get_tcp_pose failed: {e}")
            return None

    def set_payload(self, mass, cog=[]):
        """
        Set payload
        :param mass: Mass in kilograms
        :param cog: [CoGx, CoGy, CoGz] Center of Gravity displacement, optional
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot set_payload: control interface not available")
                return False
        try:
            return self.rc.setPayload(mass, cog)
        except Exception as e:
            logging.error(f"set_payload failed: {e}")
            return False

    def set_target_payload(self, mass, cog=[], inertia=[]):
        """
        Sets the mass, center of gravity and the inertia matrix of the active payload
        :param mass: Mass in kilograms
        :param cog: [CoGx, CoGy, CoGz] Center of Gravity displacement, optional
        :param inertia: [Ixx,Ixy,Ixz,Iyy,Iyz,Izz] Inertia matrix, optional
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot set_target_payload: control interface not available")
                return False
        try:
            return self.rc.setTargetPayload(mass, cog, inertia)
        except Exception as e:
            logging.error(f"set_target_payload failed: {e}")
            return False

    def zero_ft_sensor(self):
        """
        Zeros the TCP force/torque measurement from the builtin force/torque sensor
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot zero_ft_sensor: control interface not available")
                return False
        try:
            return self.rc.zeroFtSensor()
        except Exception as e:
            logging.error(f"zero_ft_sensor failed: {e}")
            return False

    def set_gravity(self, direction):
        """
        Set the direction of the acceleration experienced by the robot
        :param direction: [x,y,z] 3d vector indicating the gravity direction
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot set_gravity: control interface not available")
                return False
        try:
            return self.rc.setGravity(direction)
        except Exception as e:
            logging.error(f"set_gravity failed: {e}")
            return False

    # === 新增：逆运动学和正运动学功能 ===

    def get_inverse_kinematics(self, pose, qnear=[], max_position_error=1e-10, max_orientation_error=1e-10):
        """
        Calculate the inverse kinematic transformation (tool space -> joint space)
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param qnear: [q1,q2,q3,q4,q5,q6] joint angles closest to the solution sought, optional
        :param max_position_error: Maximum allowed position error, optional
        :param max_orientation_error: Maximum allowed orientation error, optional
        :return: [q1,q2,q3,q4,q5,q6] joint angles or None if no solution found
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_inverse_kinematics: control interface not available")
                return None
        try:
            return self.rc.getInverseKinematics(pose, qnear, max_position_error, max_orientation_error)
        except Exception as e:
            logging.error(f"get_inverse_kinematics failed: {e}")
            return None

    def get_forward_kinematics(self, q=[], tcp_offset=[]):
        """
        Calculate the forward kinematic transformation (joint space -> tool space)
        :param q: [q1,q2,q3,q4,q5,q6] joint angles, uses current if empty
        :param tcp_offset: [x,y,z,rx,ry,rz] TCP offset, uses current if empty
        :return: [x,y,z,rx,ry,rz] pose vector or None if failed
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_forward_kinematics: control interface not available")
                return None
        try:
            return self.rc.getForwardKinematics(q, tcp_offset)
        except Exception as e:
            logging.error(f"get_forward_kinematics failed: {e}")
            return None

    def get_inverse_kinematics_has_solution(self, pose, qnear=[], max_position_error=1e-10, max_orientation_error=1e-10):
        """
        Check if get_inverse_kinematics has a solution and return boolean
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :param qnear: [q1,q2,q3,q4,q5,q6] joint angles closest to the solution sought, optional
        :param max_position_error: Maximum allowed position error, optional
        :param max_orientation_error: Maximum allowed orientation error, optional
        :return: Boolean indicating if a solution exists
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_inverse_kinematics_has_solution: control interface not available")
                return False
        try:
            return self.rc.getInverseKinematicsHasSolution(pose, qnear, max_position_error, max_orientation_error)
        except Exception as e:
            logging.error(f"get_inverse_kinematics_has_solution failed: {e}")
            return False

    # === 新增：姿态变换和运动规划功能 ===

    def pose_trans(self, p_from, p_from_to):
        """
        Pose transformation to move with respect to a tool or custom feature/frame
        :param p_from: [x,y,z,rx,ry,rz] initial pose
        :param p_from_to: [x,y,z,rx,ry,rz] transformation from initial to final pose
        :return: [x,y,z,rx,ry,rz] resulting pose vector or None if failed
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot pose_trans: control interface not available")
                return None
        try:
            return self.rc.poseTrans(p_from, p_from_to)
        except Exception as e:
            logging.error(f"pose_trans failed: {e}")
            return None

    def is_pose_within_safety_limits(self, pose):
        """
        Checks if the given pose is reachable and within safety limits
        :param pose: [x,y,z,rx,ry,rz] pose vector
        :return: Boolean indicating if pose is within safety limits
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot check pose safety: control interface not available")
                return False
        try:
            return self.rc.isPoseWithinSafetyLimits(pose)
        except Exception as e:
            logging.error(f"is_pose_within_safety_limits failed: {e}")
            return False

    def is_joints_within_safety_limits(self, q):
        """
        Checks if the given joint position is reachable and within safety limits
        :param q: [q1,q2,q3,q4,q5,q6] joint angles
        :return: Boolean indicating if joints are within safety limits
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot check joint safety: control interface not available")
                return False
        try:
            return self.rc.isJointsWithinSafetyLimits(q)
        except Exception as e:
            logging.error(f"is_joints_within_safety_limits failed: {e}")
            return False

    # === 新增：监控和诊断功能 ===

    def get_joint_torques(self):
        """
        Returns the torques of all joints
        :return: [t1,t2,t3,t4,t5,t6] joint torques vector or None if failed
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_joint_torques: control interface not available")
                return None
        try:
            return self.rc.getJointTorques()
        except Exception as e:
            logging.error(f"get_joint_torques failed: {e}")
            return None

    def get_actual_tool_flange_pose(self):
        """
        Returns the current measured tool flange pose
        :return: [x,y,z,rx,ry,rz] pose vector or None if failed
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_actual_tool_flange_pose: control interface not available")
                return None
        try:
            return self.rc.getActualToolFlangePose()
        except Exception as e:
            logging.error(f"get_actual_tool_flange_pose failed: {e}")
            return None

    def is_steady(self):
        """
        Checks if robot is fully at rest
        :return: Boolean indicating if robot is steady
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot check if steady: control interface not available")
                return False
        try:
            return self.rc.isSteady()
        except Exception as e:
            logging.error(f"is_steady failed: {e}")
            return False

    def move_until_contact(self, xd, direction=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], acceleration=0.5):
        """
        Move the robot until contact, with specified speed and contact detection direction
        :param xd: [x,y,z,rx,ry,rz] 6d vector of speed in m/s and rad/s
        :param direction: [x,y,z,rx,ry,rz] 6d vector of contact detection direction
        :param acceleration: acceleration [m/s²]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot move_until_contact: control interface not available")
                return False
        try:
            return self.rc.moveUntilContact(xd, direction, acceleration)
        except Exception as e:
            logging.error(f"move_until_contact failed: {e}")
            return False

    def get_freedrive_status(self):
        """
        Returns status of freedrive mode for current robot pose
        :return: Integer status code of freedrive mode
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_freedrive_status: control interface not available")
                return -1
        try:
            return self.rc.getFreedriveStatus()
        except Exception as e:
            logging.error(f"get_freedrive_status failed: {e}")
            return -1

    def get_step_time(self):
        """
        Returns the duration of the robot time step in seconds
        :return: Time step duration in seconds
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_step_time: control interface not available")
                return 0.0
        try:
            return self.rc.getStepTime()
        except Exception as e:
            logging.error(f"get_step_time failed: {e}")
            return 0.0

    def get_target_waypoint(self):
        """
        Returns the target waypoint of the active move
        :return: [x,y,z,rx,ry,rz] pose vector or None if no active move
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_target_waypoint: control interface not available")
                return None
        try:
            return self.rc.getTargetWaypoint()
        except Exception as e:
            logging.error(f"get_target_waypoint failed: {e}")
            return None

    # === 新增：安全和保护功能 ===

    def trigger_protective_stop(self):
        """
        Triggers a protective stop on the robot
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot trigger_protective_stop: control interface not available")
                return False
        try:
            return self.rc.triggerProtectiveStop()
        except Exception as e:
            logging.error(f"trigger_protective_stop failed: {e}")
            return False

    def set_watchdog(self, min_frequency=10.0):
        """
        Enable a watchdog for communication with specified minimum frequency
        :param min_frequency: Minimum expected communication frequency [Hz]
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot set_watchdog: control interface not available")
                return False
        try:
            return self.rc.setWatchdog(min_frequency)
        except Exception as e:
            logging.error(f"set_watchdog failed: {e}")
            return False

    def kick_watchdog(self):
        """
        Kicks the watchdog safeguarding communication
        :return: True if successful
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot kick_watchdog: control interface not available")
                return False
        try:
            return self.rc.kickWatchdog()
        except Exception as e:
            logging.error(f"kick_watchdog failed: {e}")
            return False

    def get_robot_status(self):
        """
        Returns robot status bits
        :return: Integer representing robot status
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_robot_status: control interface not available")
                return 0
        try:
            return self.rc.getRobotStatus()
        except Exception as e:
            logging.error(f"get_robot_status failed: {e}")
            return 0

    # === 新增：异步操作功能 ===

    def get_async_operation_progress(self):
        """
        Reads progress information for asynchronous operations
        :return: Progress percentage as integer (-1 if no operation running)
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot get_async_operation_progress: control interface not available")
                return -1
        try:
            return self.rc.getAsyncOperationProgress()
        except Exception as e:
            logging.error(f"get_async_operation_progress failed: {e}")
            return -1

    def is_program_running(self):
        """
        Returns true if a program is running on the controller
        :return: Boolean indicating if program is running
        """
        with self._lock:
            if not self.rc or self.read_only:
                logging.error("Cannot check if program running: control interface not available")
                return False
        try:
            return self.rc.isProgramRunning()
        except Exception as e:
            logging.error(f"is_program_running failed: {e}")
            return False
