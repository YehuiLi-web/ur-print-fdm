"""Production queue runner implemented as a Qt worker.

This project targets UR5 CB3 (PolyScope 3.x) behavior.

For reliable **pause / resume**, the program should run inside PolyScope, controlled via the
Dashboard server (port 29999). The recommended production workflow is:

1) Maintain a robot-side `loader.urp` program that executes `remote_loader.script`.
2) For each local script file, upload twice via SFTP:
   - original filename (for archive/debug)
   - fixed name `remote_loader.script` (consumed by `loader.urp`)
3) Dashboard:
   - `load /home/ur/ursim-current/programs/loader.urp`
   - `play` / `pause` / `stop`
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from ur_print_fdm.config import config_manager
from ur_print_fdm.constants import DEFAULT_MODBUS_EXTRUDER
from ur_print_fdm.core.dashboard_driver import SimpleDashboardDriver
from ur_print_fdm.shared.logging_context import trace_context
from ur_print_fdm.shared.net import is_valid_ip


class ProductionProcessor(QThread):
    """SFTP upload + Dashboard load/play queue runner (CB3-friendly)."""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)  # (current index, total)
    file_progress_signal = pyqtSignal(int)  # 0-100 for current upload
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)

    def __init__(
        self,
        ip: str,
        script_port: int,
        script_paths: list[str],
        do_index: int | None = None,  # kept for compatibility; not used in this mode
        watchdog_enable: bool = True,  # reserved for future
        *,
        trace_id: str | None = None,
    ) -> None:
        super().__init__()

        if not is_valid_ip(ip):
            raise ValueError(f"无效的 IP 地址格式: {ip}")

        self.ip = ip
        self.script_port = int(script_port)
        self.script_paths = list(script_paths or [])
        self.do_index = do_index
        self.watchdog_enable = bool(watchdog_enable)
        self.trace_id = trace_id

        # State flags
        self.running = False
        self.paused = False
        self.emergency_abort = False

        # Control requests (thread-safe)
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._resume_event = threading.Event()

        # Dashboard program path
        remote_dir = str(
            config_manager.get("robot.sftp.remote_dir", "/home/ur/ursim-current/programs") or ""
        ).rstrip("/")
        self.remote_dir = remote_dir
        self.loader_urp_path = str(
            config_manager.get("robot.dashboard.loader_urp_path", f"{remote_dir}/loader.urp")
            or f"{remote_dir}/loader.urp"
        )
        self.remote_loader_name = str(
            config_manager.get("robot.dashboard.remote_loader_name", "remote_loader.script")
            or "remote_loader.script"
        )

        # SFTP params
        self.sftp_port = int(config_manager.get("robot.sftp.port", 22) or 22)
        self.sftp_username = str(config_manager.get("robot.sftp.username", "ur") or "ur")
        self.sftp_password = str(config_manager.get("robot.sftp.password", "easybot") or "easybot")

        # Best-effort safety params (used for stop/emergency stop)
        self.modbus_extruder = str(
            config_manager.get("printing.modbus_extruder", DEFAULT_MODBUS_EXTRUDER)
            or DEFAULT_MODBUS_EXTRUDER
        )
        self.extruder_do_pin = int(config_manager.get("printing.extruder_io_pin", 0) or 0)

    # -----------------------------
    # Public control API (UI thread)
    # -----------------------------

    def request_pause(self) -> None:
        self._pause_event.set()
        self._resume_event.clear()

    def request_resume(self) -> None:
        self._resume_event.set()
        self._pause_event.clear()

    def stop(self) -> None:
        """Request stop (abort queue)."""
        self.running = False
        self._stop_event.set()

    def emergency_stop_action(self) -> None:
        """Emergency stop: stop program + cut extrusion, and abort queue."""
        self.emergency_abort = True
        self.running = False
        self._stop_event.set()

        # Best-effort immediate stop (do not block UI thread).
        threading.Thread(target=self._emergency_stop_now, daemon=True).start()

    # -----------------------------
    # QThread entrypoint
    # -----------------------------

    def run(self) -> None:
        logger = logging.getLogger("ur_print_fdm.production")
        with trace_context(self.trace_id):
            self.running = True
            self.paused = False
            self.emergency_abort = False
            self._stop_event.clear()
            self._pause_event.clear()
            self._resume_event.clear()

            if not self.script_paths:
                self.error_signal.emit("队列为空：没有可执行的脚本。")
                self.finished_signal.emit()
                return

            db = SimpleDashboardDriver()
            db.set_ip(self.ip)

            try:
                total = len(self.script_paths)

                for idx, local_path in enumerate(self.script_paths):
                    if self._should_abort():
                        break

                    self.progress_signal.emit(idx + 1, total)

                    if not os.path.isfile(local_path):
                        self.error_signal.emit(f"脚本文件不存在：{local_path}")
                        break

                    filename = os.path.basename(local_path)
                    logger.info("Queue item %d/%d: %s", idx + 1, total, filename)

                    # 1) Upload (dual: original + remote_loader.script)
                    if not self._sftp_upload_dual(local_path):
                        break

                    if self._should_abort():
                        break

                    # 2) Load loader.urp (full path, URSim style)
                    resp = db.load_program(self.loader_urp_path)
                    if not self._dashboard_ok(resp):
                        self.error_signal.emit(
                            f"Dashboard 加载失败：{self.loader_urp_path}\n响应：{resp}\n"
                            "请检查：loader.urp 是否存在、路径是否正确、机器人是否有弹窗/保护停机。"
                        )
                        break

                    # 3) Play
                    resp = db.play()
                    if not self._dashboard_ok(resp):
                        self.error_signal.emit(
                            f"Dashboard 运行失败（play）：{resp}\n"
                            "请检查：机器人是否处于可运行状态、是否有弹窗/保护停机、是否已正确加载 loader.urp。"
                        )
                        break

                    # 4) Wait for program start
                    if not self._wait_for_start(db, timeout_s=20.0):
                        self.error_signal.emit("程序未开始运行（超时），请检查机器人模式/保护停机/弹窗。")
                        break

                    # 5) Wait for finish, applying pause/resume/stop requests
                    finished_ok = self._wait_for_finish(db)
                    if not finished_ok:
                        break

                    time.sleep(0.2)

            except Exception as e:
                logger.exception("ProductionProcessor raised: %s", e)
                self.error_signal.emit(f"生产线程异常: {type(e).__name__}: {e}")
            finally:
                try:
                    db.close()
                except Exception:
                    pass
                self.finished_signal.emit()

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _should_abort(self) -> bool:
        return bool(self._stop_event.is_set() or self.emergency_abort or self.isInterruptionRequested())

    def _dashboard_ok(self, resp: str | None) -> bool:
        if resp is None:
            return False
        low = str(resp).strip().lower()
        if not low:
            return True
        if any(k in low for k in ("error", "failed", "failure", "not found", "no such", "denied")):
            return False
        return True

    def _wait_for_start(self, db: SimpleDashboardDriver, *, timeout_s: float) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self._should_abort():
                return False

            self._apply_control_requests(db)

            state = db.program_state()
            if state in ("PLAYING", "PAUSED"):
                return True

            running = db.running()
            if running is True:
                return True

            time.sleep(0.2)
        return False

    def _wait_for_finish(self, db: SimpleDashboardDriver) -> bool:
        while True:
            if self._should_abort():
                self._stop_program_and_kill(db)
                return False

            self._apply_control_requests(db)

            state = db.program_state()
            if state == "STOPPED":
                return True
            if state in ("PLAYING", "PAUSED"):
                time.sleep(0.2)
                continue

            # Fallback: running?
            running = db.running()
            if running is False:
                return True

            time.sleep(0.2)

    def _apply_control_requests(self, db: SimpleDashboardDriver) -> None:
        if self._pause_event.is_set() and not self.paused:
            resp = db.pause()
            if self._dashboard_ok(resp):
                self.paused = True
                # CB3: program pause will freeze URScript, but DO/Modbus outputs may remain latched.
                # Best-effort: cut extrusion on pause to avoid oozing / overheating.
                try:
                    self._send_stop_extrusion_secondary()
                except Exception:
                    pass
            self._pause_event.clear()

        if self._resume_event.is_set() and self.paused:
            resp = db.play()
            if self._dashboard_ok(resp):
                self.paused = False
            self._resume_event.clear()

    def _stop_program_and_kill(self, db: SimpleDashboardDriver) -> None:
        try:
            db.stop()
        except Exception:
            pass
        try:
            self._send_stop_extrusion_secondary()
        except Exception:
            pass

    def _sftp_upload_dual(self, local_path: str) -> bool:
        logger = logging.getLogger("ur_print_fdm.production")
        try:
            import paramiko
        except Exception:
            self.error_signal.emit("缺少依赖 paramiko，无法使用 SFTP 上传。")
            return False

        filename = os.path.basename(local_path)
        remote_original = f"{self.remote_dir}/{filename}"
        remote_loader = f"{self.remote_dir}/{self.remote_loader_name}"

        self.file_progress_signal.emit(0)

        try:
            transport = paramiko.Transport((self.ip, self.sftp_port))
            transport.connect(username=self.sftp_username, password=self.sftp_password)
            sftp = paramiko.SFTPClient.from_transport(transport)

            def _cb(transferred: int, total: int) -> None:
                if total <= 0:
                    return
                pct = int((transferred / total) * 100)
                self.file_progress_signal.emit(max(0, min(100, pct)))

            logger.info("SFTP upload: %s -> %s", filename, self.remote_dir)
            sftp.put(local_path, remote_original, callback=_cb)
            self.file_progress_signal.emit(0)
            sftp.put(local_path, remote_loader, callback=_cb)

            sftp.close()
            transport.close()

            self.file_progress_signal.emit(100)
            return True
        except Exception as e:
            logger.exception("SFTP upload failed: %s", e)
            self.error_signal.emit(f"SFTP 上传失败: {type(e).__name__}: {e}")
            return False

    def _send_stop_extrusion_secondary(self) -> None:
        script = (
            "sec kill_io():\n"
            f"  modbus_set_output_register(\"{self.modbus_extruder}\", 0)\n"
            f"  set_standard_digital_out({self.extruder_do_pin}, False)\n"
            "end\n"
        )
        self._send_secondary(script)

    def _send_emergency_secondary(self) -> None:
        script = (
            "sec emerg():\n"
            "  stopj(2.0)\n"
            f"  modbus_set_output_register(\"{self.modbus_extruder}\", 0)\n"
            f"  set_standard_digital_out({self.extruder_do_pin}, False)\n"
            "end\n"
        )
        self._send_secondary(script)

    def _send_secondary(self, script: str) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.5)
        try:
            s.connect((self.ip, self.script_port))
            s.sendall(script.encode("utf-8"))
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _emergency_stop_now(self) -> None:
        # 1) Dashboard stop (new socket for safety)
        try:
            db = SimpleDashboardDriver()
            db.set_ip(self.ip)
            db.send("stop")
            db.close()
        except Exception:
            pass

        # 2) Best-effort motion+extruder kill via 30002
        try:
            self._send_emergency_secondary()
        except Exception:
            pass
