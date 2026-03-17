"""Qt worker threads (legacy extracted from `core`)."""

from PyQt6.QtCore import QThread, pyqtSignal
import logging
import os
import time

from ur_print_fdm.config import config_manager
from ur_print_fdm.core.dashboard_driver import SimpleDashboardDriver
from ur_print_fdm.shared.logging_context import trace_context
from ur_print_fdm.shared.upload_preprocessor import prepare_upload_source
from ur_print_fdm.ui.workers.loader_binding import build_loader_binding_note


class ScriptSendThread(QThread):
    """专门负责发送脚本的线程，防止界面卡死"""
    result_signal = pyqtSignal(bool, str)  # 成功/失败, 消息

    def __init__(self, driver, script_content, *, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self.script_content = script_content
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.script_send")
        with trace_context(self.trace_id):
            try:
                logger.info("Sending script (%d chars)", len(self.script_content or ""))
                result = self.driver.send_script(self.script_content)

                # 兼容新旧返回值格式
                if isinstance(result, tuple):
                    success, warning = result
                else:
                    success, warning = bool(result), None

                if success:
                    if warning:
                        logger.warning(warning, extra={"ui_level": "WARN"})
                        self.result_signal.emit(True, f"脚本已发送。警告: {warning}")
                    else:
                        logger.info("脚本已发送至控制器。", extra={"ui_level": "SUCCESS"})
                        self.result_signal.emit(True, "脚本已发送至控制器。")
                else:
                    logger.error("脚本发送失败 (send_script 返回 False)。", extra={"ui_level": "ERROR"})
                    self.result_signal.emit(False, "脚本发送失败 (send_script 返回 False)。")
            except Exception as e:
                logger.exception("Script send raised exception: %s", e)
                self.result_signal.emit(False, f"发送失败: {e}")


class URScriptEstimateThread(QThread):
    """Estimate URScript time/material in a background thread."""

    result_signal = pyqtSignal(int, bool, object, str)  # run_id, ok, estimate, msg

    def __init__(
        self,
        run_id: int,
        script_content: str,
        *,
        current_tcp_pose=None,
        extruder_modbus_id: str = "MODBUS_1",
        trace_id: str | None = None,
    ):
        super().__init__()
        self.run_id = int(run_id)
        self.script_content = script_content or ""
        self.current_tcp_pose = current_tcp_pose
        self.extruder_modbus_id = str(extruder_modbus_id or "MODBUS_1")
        self.trace_id = trace_id

    def run(self) -> None:
        logger = logging.getLogger("ur_print_fdm.worker.urscript_estimate")
        with trace_context(self.trace_id):
            try:
                from ur_print_fdm.estimators.urscript import URScriptEstimateError, estimate_urscript

                estimate = estimate_urscript(
                    self.script_content,
                    current_tcp_pose=self.current_tcp_pose,
                    extruder_modbus_id=self.extruder_modbus_id,
                )
                self.result_signal.emit(self.run_id, True, estimate, "")
            except URScriptEstimateError as e:
                logger.warning("URScript estimate failed: %s", e, extra={"ui_level": "WARN"})
                self.result_signal.emit(self.run_id, False, None, str(e))
            except Exception as e:
                logger.exception("URScript estimate raised exception: %s", e)
                self.result_signal.emit(self.run_id, False, None, f"{type(e).__name__}: {e}")


class StopThread(QThread):
    """专门负责发送停止指令的线程，防止点击停止时界面卡死"""
    finished_signal = pyqtSignal(str) # 完成信号，带回日志消息

    def __init__(self, driver, *, preserve_control: bool = False, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self.preserve_control = bool(preserve_control)
        self._should_stop = False
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.stop")
        with trace_context(self.trace_id):
            try:
                if self.preserve_control:
                    success = self.driver.manual_stop()
                else:
                    success = self.driver.stop()
                if not self._should_stop:
                    if success is not False:
                        if self.preserve_control:
                            logger.info("机械臂原生停止指令已发送", extra={"ui_level": "SUCCESS"})
                            self.finished_signal.emit("机械臂原生停止指令已发送")
                        else:
                            logger.info("机械臂停止指令已发送", extra={"ui_level": "SUCCESS"})
                            self.finished_signal.emit("机械臂停止指令已发送")
                    else:
                        logger.warning("停止指令已发送，但可能未完全执行", extra={"ui_level": "WARN"})
                        self.finished_signal.emit("停止指令已发送，但可能未完全执行")
            except Exception as e:
                logger.exception("Stop raised exception: %s", e)
                if not self._should_stop:
                    self.finished_signal.emit(f"停止指令发送异常: {e}")

    def stop_gracefully(self):
        """请求线程优雅停止"""
        self._should_stop = True


class StopExtrusionThread(QThread):
    """专门负责发送停止挤出指令的线程，避免 UI 阻塞。"""

    finished_signal = pyqtSignal(str)

    def __init__(self, driver, *, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self._should_stop = False
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.stop_extrusion")
        with trace_context(self.trace_id):
            try:
                success = self.driver.stop_extrusion()
                if not self._should_stop:
                    if success is not False:
                        logger.info("挤出输出已关闭", extra={"ui_level": "SUCCESS"})
                        self.finished_signal.emit("挤出输出已关闭")
                    else:
                        logger.warning("停止挤出指令已发送，但可能未完全执行", extra={"ui_level": "WARN"})
                        self.finished_signal.emit("停止挤出指令已发送，但可能未完全执行")
            except Exception as e:
                logger.exception("Stop extrusion raised exception: %s", e)
                if not self._should_stop:
                    self.finished_signal.emit(f"停止挤出指令发送异常: {e}")

    def stop_gracefully(self):
        self._should_stop = True


class LinearMoveThread(QThread):
    """后台执行单次 move_l，避免 UI 阻塞。"""

    result_signal = pyqtSignal(bool, str, object)  # ok, message, target_pose

    def __init__(
        self,
        driver,
        target_pose,
        *,
        speed: float = 0.05,
        acceleration: float = 0.2,
        asynchronous: bool = False,
        trace_id: str | None = None,
    ):
        super().__init__()
        self.driver = driver
        self.target_pose = list(target_pose or [])
        self.speed = float(speed)
        self.acceleration = float(acceleration)
        self.asynchronous = bool(asynchronous)
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.linear_move")
        with trace_context(self.trace_id):
            try:
                ok = bool(
                    self.driver.move_l(
                        self.target_pose,
                        self.speed,
                        self.acceleration,
                        self.asynchronous,
                    )
                )
                if ok:
                    logger.info(
                        "Base jog move completed",
                        extra={"ui_level": "SUCCESS"},
                    )
                    self.result_signal.emit(True, "Base 点动完成", list(self.target_pose))
                else:
                    logger.warning(
                        "Base jog move failed",
                        extra={"ui_level": "WARN"},
                    )
                    self.result_signal.emit(False, "Base 点动失败", list(self.target_pose))
            except Exception as e:
                logger.exception("Linear move raised exception: %s", e)
                self.result_signal.emit(False, f"Base 点动异常: {e}", list(self.target_pose))


class ConnectionThread(QThread):
    """专门负责连接机器人的线程，防止点击连接时界面卡死"""
    result_signal = pyqtSignal(bool, str) # 成功/失败, 消息
    log_signal = pyqtSignal(str)  # legacy: prefer Python logging + UI handler

    def __init__(self, driver, ip, *, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self.ip = ip
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.connect")
        with trace_context(self.trace_id):
            def callback(msg: str):
                # Driver emits rich progress messages; log them for traceability.
                logger.info("%s", msg)

            try:
                logger.info("Connecting to robot: %s", self.ip)
                ok = bool(self.driver.connect(self.ip, log_callback=callback))
                if ok:
                    logger.info("已连接到 %s", self.ip, extra={"ui_level": "SUCCESS"})
                    self.result_signal.emit(True, f"已连接到 {self.ip}")
                else:
                    logger.error("连接失败: %s", self.ip, extra={"ui_level": "ERROR"})
                    self.result_signal.emit(False, "连接失败，请检查 IP 或网络设置。")
            except Exception as e:
                logger.exception("Connect raised exception: %s", e)
                self.result_signal.emit(False, f"连接异常: {e}")


class MonitorThread(QThread):
    """专门负责不断读取机器人状态的线程"""
    # 🆕 修改信号定义：增加一个 list 用于传递 tcp_offset
    # 🆕 修改信号定义：增加 speed (float)
    status_signal = pyqtSignal(list, list, list, float)
    snapshot_signal = pyqtSignal(object)

    def __init__(self, driver):
        super().__init__()
        self.driver = driver
        self._last_dashboard_probe_at = 0.0

    def run(self):
        while not self.isInterruptionRequested():
            now = time.monotonic()
            probe_dashboard = (now - self._last_dashboard_probe_at) >= 2.0
            if probe_dashboard:
                self._last_dashboard_probe_at = now

            try:
                snapshot = self.driver.probe_connection_snapshot(probe_dashboard=probe_dashboard)
            except Exception as e:
                logging.debug(f"MonitorThread: 探测连接状态时发生异常: {e}")
                snapshot = self.driver.get_connection_snapshot()

            self.snapshot_signal.emit(snapshot)

            if snapshot.can_monitor:
                try:
                    # 接收 4 个返回值
                    tcp, joints, offset, speed = self.driver.get_status()
                    if tcp and joints:
                        self.status_signal.emit(tcp, joints, offset, speed)
                except Exception as e:
                    logging.debug(f"MonitorThread: 获取状态时发生异常: {e}")
            self.msleep(100)


class ConnectionRepairThread(QThread):
    """完整修复连接：断开并重新建立 Receive / Dashboard / Control。"""

    result_signal = pyqtSignal(bool, str)

    def __init__(self, driver, ip: str | None = None, *, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self.ip = str(ip or "").strip()
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.repair")
        with trace_context(self.trace_id):
            try:
                logger.info("Repairing connection session")
                ok = bool(self.driver.repair_connection(self.ip or None))
                if ok:
                    logger.info("连接修复完成", extra={"ui_level": "SUCCESS"})
                    self.result_signal.emit(True, "连接修复完成")
                else:
                    logger.error("连接修复失败", extra={"ui_level": "ERROR"})
                    self.result_signal.emit(False, "连接修复失败")
            except Exception as e:
                logger.exception("Repair raised exception: %s", e)
                self.result_signal.emit(False, f"连接修复异常: {e}")


class DashboardCmdThread(QThread):
    """专门负责发送瞬间完成的 Dashboard 指令 (速度控制)"""
    # 新增：结果信号 (是否成功, 提示消息)
    result_signal = pyqtSignal(bool, str)

    def __init__(self, driver, cmd_type, value=None, *, trace_id: str | None = None):
        super().__init__()
        self.driver = driver
        self.cmd_type = cmd_type # 'speed'
        self.value = value
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.dashboard")
        success = False
        msg = ""

        with trace_context(self.trace_id):
            try:
                if self.cmd_type == 'speed':
                    logger.info("Setting speed slider: %s", self.value)
                    if self.driver.set_speed_slider(self.value):
                        success = True
                        msg = f"[速度] 已设为 {int(self.value*100)}%"
                    else:
                        msg = "速度设置失败"
                        logger.warning("Speed slider failed")

            except Exception as e:
                msg = f"指令异常: {e}"
                success = False
                logger.exception("Dashboard command failed: %s", e)

        self.result_signal.emit(success, msg)


class SFTPUploadThread(QThread):
    """专门负责通过 SFTP 上传文件的线程"""
    result_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int)  # 0-100

    def __init__(
        self,
        ip,
        local_path,
        remote_dir=None,
        remote_filename=None,
        *,
        also_upload_loader: bool = False,
        load_program_after_upload: bool = False,
        remote_loader_name: str | None = None,
        loader_urp_path: str | None = None,
        username=None,
        password=None,
        port=None,
        trace_id: str | None = None,
    ):
        super().__init__()
        self.ip = ip
        self.local_path = local_path
        self.remote_dir = remote_dir or config_manager.get("robot.sftp.remote_dir", "/home/ur/ursim-current/programs")
        self.remote_filename = remote_filename or os.path.basename(self.local_path)
        self.also_upload_loader = bool(also_upload_loader)
        self.load_program_after_upload = bool(load_program_after_upload)
        self.remote_loader_name = (
            remote_loader_name
            or config_manager.get("robot.dashboard.remote_loader_name", "remote_loader.script")
            or "remote_loader.script"
        )
        self.loader_urp_path = (
            loader_urp_path
            or config_manager.get("robot.dashboard.loader_urp_path", f"{self.remote_dir.rstrip('/')}/loader.urp")
            or f"{self.remote_dir.rstrip('/')}/loader.urp"
        )
        self.username = username or config_manager.get("robot.sftp.username", "ur")
        self.password = password or config_manager.get("robot.sftp.password", "easybot")
        self.port = int(port or config_manager.get("robot.sftp.port", 22))
        self.trace_id = trace_id

    @staticmethod
    def _dashboard_ok(resp: str | None) -> bool:
        if resp is None:
            return False
        low = str(resp).strip().lower()
        if not low:
            return True
        return not any(k in low for k in ("error", "failed", "not found", "no such", "not connected"))

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.sftp")
        try:
            import paramiko
            filename = self.remote_filename
            # 确保目录结尾有斜杠
            remote_dir = self.remote_dir.rstrip('/')

            remote_path_primary = f"{remote_dir}/{filename}"
            remote_path_loader = f"{remote_dir}/{self.remote_loader_name}"

            # 建立传输
            with trace_context(self.trace_id):
                logger.info(
                    "SFTP upload start: %s -> %s@%s:%s", os.path.basename(self.local_path), self.username, self.ip, remote_dir
                )

                transport = paramiko.Transport((self.ip, self.port))
                transport.connect(username=self.username, password=self.password)
                sftp = paramiko.SFTPClient.from_transport(transport)

                self.progress_signal.emit(0)

                def _cb(transferred: int, total: int) -> None:
                    if total <= 0:
                        return
                    pct = int((transferred / total) * 100)
                    self.progress_signal.emit(max(0, min(100, pct)))

                with prepare_upload_source(self.local_path) as upload_source:
                    if upload_source.normalized:
                        logger.info(
                            "Normalized text upload newlines to LF before SFTP: %s",
                            os.path.basename(self.local_path),
                        )

                    # 1) 主文件
                    sftp.put(upload_source.path, remote_path_primary, callback=_cb)

                    # 2) 可选：覆盖 remote_loader（用于生产模式）
                    if self.also_upload_loader:
                        self.progress_signal.emit(0)
                        sftp.put(upload_source.path, remote_path_loader, callback=_cb)

                sftp.close()
                transport.close()
                self.progress_signal.emit(100)

                load_resp = None
                if self.load_program_after_upload:
                    db = SimpleDashboardDriver()
                    try:
                        db.set_ip(self.ip)
                        load_resp = db.load_program(self.loader_urp_path)
                    finally:
                        try:
                            db.close()
                        except Exception:
                            pass

                    if not self._dashboard_ok(load_resp):
                        uploaded_paths = [f"- {remote_path_primary}"]
                        if self.also_upload_loader:
                            uploaded_paths.append(f"- {remote_path_loader}（用于 loader.urp）")
                        self.result_signal.emit(
                            False,
                            "文件上传成功，但加载失败：\n"
                            + "\n".join(uploaded_paths)
                            + f"\n- Dashboard 加载失败：{self.loader_urp_path}\n"
                            + f"- 响应：{load_resp}",
                        )
                        return

                logger.info("SFTP upload success: %s", filename)
                if self.load_program_after_upload:
                    message = ["上传并加载成功！", f"- {remote_path_primary}"]
                    if self.also_upload_loader:
                        message.append(f"- {remote_path_loader}（用于 loader.urp）")
                    message.append(f"- Dashboard 已加载：{self.loader_urp_path}")
                    if self.also_upload_loader:
                        message.append(f"- {build_loader_binding_note(self.loader_urp_path, self.remote_loader_name)}")
                    self.result_signal.emit(True, "\n".join(message))
                elif self.also_upload_loader:
                    self.result_signal.emit(
                        True,
                        "上传成功！\n"
                        f"- {remote_path_primary}\n"
                        f"- {remote_path_loader}（用于 loader.urp）\n"
                        f"- {build_loader_binding_note(self.loader_urp_path, self.remote_loader_name)}",
                    )
                else:
                    self.result_signal.emit(True, f"上传成功！\n- {remote_path_primary}")
        except ImportError:
            self.result_signal.emit(False, "上传失败: 缺少 paramiko 库")
        except Exception as e:
            logger.exception("SFTP upload failed: %s", e)
            self.result_signal.emit(False, f"SFTP 错误: {str(e)}")


class ProgramManagementThread(QThread):
    """Handle program upload, load, and management operations"""
    result_signal = pyqtSignal(bool, str)

    def __init__(self, driver, operation, *, trace_id: str | None = None, **kwargs):
        super().__init__()
        self.driver = driver
        self.operation = operation  # 'upload', 'load', 'get_loaded'
        self.kwargs = kwargs
        self.trace_id = trace_id

    def run(self):
        logger = logging.getLogger("ur_print_fdm.worker.program")
        success = False
        msg = ""

        with trace_context(self.trace_id):
            try:
                if self.operation == 'upload':
                    local_file = self.kwargs.get('local_file')
                    remote_name = self.kwargs.get('remote_name')
                    logger.info("Uploading program file: %s -> %s", local_file, remote_name)
                    if self.driver.upload_program_file(local_file, remote_name):
                        success = True
                        msg = f"程序文件已上传: {remote_name}"
                    else:
                        msg = f"程序文件上传失败: {remote_name}"

                elif self.operation == 'load':
                    program_name = self.kwargs.get('program_name')
                    logger.info("Loading program: %s", program_name)
                    if self.driver.load_program(program_name):
                        success = True
                        msg = f"程序已加载: {program_name}"
                    else:
                        msg = f"程序加载失败: {program_name}"

                elif self.operation == 'get_loaded':
                    loaded_program = self.driver.get_loaded_program()
                    if loaded_program:
                        success = True
                        msg = f"当前加载的程序: {loaded_program}"
                    else:
                        msg = "无法获取当前加载的程序"

            except Exception as e:
                msg = f"程序管理操作异常: {e}"
                success = False
                logger.exception("Program management failed: %s", e)

        self.result_signal.emit(success, msg)
