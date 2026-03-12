"""Direct mode processor - Pure 30002 port script execution.

This processor uses only the 30002 (Secondary Client) port for script execution,
avoiding RTDE Control Interface blocking issues.

Features:
- Non-blocking script send via 30002 port
- Stop via 30002 port (stopj script)
- Stop detection via RTDE Receive (runtime_state) with Dashboard fallback
"""

from __future__ import annotations

import logging
import socket
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from ur_print_fdm.constants import SCRIPT_PORT
from ur_print_fdm.shared.logging_context import trace_context
from ur_print_fdm.shared.net import is_valid_ip

# Optional RTDE for status monitoring
try:
    from rtde_receive import RTDEReceiveInterface
    HAS_RTDE = True
except ImportError:
    RTDEReceiveInterface = None
    HAS_RTDE = False


class DirectModeProcessor(QThread):
    """Direct mode processor using pure 30002 port for script execution.

    This is a simplified processor that only handles:
    - Running a script (send via 30002)
    - Stopping (send stopj via 30002, verify via RTDE/Dashboard)

    No pause/resume support in direct mode.
    """

    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    error_signal = pyqtSignal(str)
    # Script sent successfully (non-blocking, doesn't mean execution finished)
    script_sent_signal = pyqtSignal(bool, str)
    # Stop completed signal
    stop_completed_signal = pyqtSignal(bool, str)

    # Runtime states from RTDE
    RUNTIME_STOPPED = 1
    RUNTIME_PLAYING = 2

    def __init__(
        self,
        ip: str,
        script_content: str | None = None,
        *,
        trace_id: str | None = None,
    ) -> None:
        super().__init__()

        if not is_valid_ip(ip):
            raise ValueError(f"Invalid IP address: {ip}")

        self.ip = ip
        self.script_content = script_content
        self.trace_id = trace_id

        # State flags
        self.running = False
        self._stop_requested = threading.Event()
        self._action: str = "run"  # "run" or "stop"

        # RTDE Receive for status monitoring (optional)
        self._rr: RTDEReceiveInterface | None = None
        self._rr_lock = threading.Lock()

    # -----------------------------
    # Public API
    # -----------------------------

    def set_action_run(self, script_content: str) -> None:
        """Set action to run a script."""
        self._action = "run"
        self.script_content = script_content

    def set_action_stop(self) -> None:
        """Set action to stop."""
        self._action = "stop"

    def request_stop(self) -> None:
        """Request to stop the current operation."""
        self._stop_requested.set()

    def connect_monitor(self) -> bool:
        """Connect RTDE Receive interface for status monitoring."""
        if not HAS_RTDE:
            self._log("RTDE not available, status monitoring disabled")
            return False

        with self._rr_lock:
            if self._rr is not None:
                return self._rr.isConnected()

            try:
                self._log(f"Connecting RTDE Receive to {self.ip}...")
                self._rr = RTDEReceiveInterface(self.ip)
                if self._rr.isConnected():
                    self._log("RTDE Receive connected")
                    return True
                else:
                    self._log("RTDE Receive connection failed")
                    self._rr = None
                    return False
            except Exception as e:
                self._log(f"RTDE Receive connection error: {e}")
                self._rr = None
                return False

    def disconnect_monitor(self) -> None:
        """Disconnect RTDE Receive interface."""
        with self._rr_lock:
            if self._rr is not None:
                try:
                    self._rr.disconnect()
                except Exception:
                    pass
                self._rr = None

    # -----------------------------
    # QThread entrypoint
    # -----------------------------

    def run(self) -> None:
        logger = logging.getLogger("ur_print_fdm.direct_mode")
        with trace_context(self.trace_id):
            self.running = True
            self._stop_requested.clear()

            try:
                if self._action == "run":
                    self._do_run_script()
                elif self._action == "stop":
                    self._do_stop()
                else:
                    self.error_signal.emit(f"Unknown action: {self._action}")
            except Exception as e:
                logger.exception("DirectModeProcessor error: %s", e)
                self.error_signal.emit(f"Direct mode error: {type(e).__name__}: {e}")
            finally:
                self.running = False
                self.finished_signal.emit()

    # -----------------------------
    # Internal: Run script
    # -----------------------------

    def _do_run_script(self) -> None:
        """Send script via 30002 port (non-blocking)."""
        if not self.script_content or not self.script_content.strip():
            self.error_signal.emit("Script content is empty")
            self.script_sent_signal.emit(False, "Script content is empty")
            return

        self._log("Sending script via 30002 port...")
        success = self._send_script_30002(self.script_content)

        if success:
            self._log("Script sent successfully (non-blocking)")
            self.script_sent_signal.emit(True, "Script sent successfully")
        else:
            self._log("Failed to send script")
            self.script_sent_signal.emit(False, "Failed to send script")

    # -----------------------------
    # Internal: Stop
    # -----------------------------

    def _do_stop(self) -> None:
        """Stop robot: Send Dashboard stop and 30002 stopj in parallel for fastest response."""
        self._log("Stopping robot...")

        # 并行发送两个停止命令，减少延迟
        import concurrent.futures

        stop_script = self._build_stop_script()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # 同时发送 Dashboard stop 和 30002 stopj
            future_dashboard = executor.submit(self._try_dashboard_stop_fast)
            future_30002 = executor.submit(self._send_script_30002, stop_script, 1.0)

            # 等待两个都完成（最多1秒）
            try:
                concurrent.futures.wait(
                    [future_dashboard, future_30002],
                    timeout=1.0
                )
            except Exception:
                pass

        self._log("Stop commands sent")

        # 验证停止（可选，不影响停止时机）
        stopped = self._wait_for_stop(timeout_s=2.0)
        if stopped:
            self._log("Robot stopped successfully")
            self.stop_completed_signal.emit(True, "Robot stopped")
        else:
            self._log("Stop commands sent (verification timeout)")
            self.stop_completed_signal.emit(True, "Stop commands sent")

    def _try_dashboard_stop_fast(self) -> bool:
        """Fast Dashboard stop - minimal blocking."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)  # 短超时
            s.connect((self.ip, 29999))
            # 跳过欢迎消息读取，直接发送stop
            s.sendall(b"stop\n")
            s.close()
            return True
        except Exception as e:
            self._log(f"Dashboard stop: {e}")
            return False

    def _build_stop_script(self) -> str:
        """Build a normal direct-mode stop script without altering extrusion."""
        lines = [
            "def direct_stop():",
            "  stopj(2.0)",
        ]
        lines.append("end")
        lines.append("direct_stop()")
        return "\n".join(lines)

    def _wait_for_stop(self, timeout_s: float = 3.0) -> bool:
        """Wait for robot to stop, checking via RTDE."""
        with self._rr_lock:
            rr = self._rr

        if rr is None:
            # No RTDE, can't verify
            return False

        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self._stop_requested.is_set():
                return False

            try:
                if not rr.isConnected():
                    return False

                runtime_state = rr.getRuntimeState()
                # STOPPED = 1
                if runtime_state == self.RUNTIME_STOPPED:
                    return True

                # Also check speed
                speed_vec = rr.getActualTCPSpeed()
                if speed_vec:
                    speed_mag = (speed_vec[0]**2 + speed_vec[1]**2 + speed_vec[2]**2) ** 0.5
                    if speed_mag < 0.001:
                        # Robot is stationary
                        return True

            except Exception as e:
                self._log(f"RTDE check error: {e}")
                return False

            time.sleep(0.1)

        return False

    def _try_dashboard_stop(self) -> None:
        """Try to stop via Dashboard (29999) as fallback."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect((self.ip, 29999))
            # Read welcome
            try:
                s.recv(1024)
            except Exception:
                pass
            # Send stop
            s.sendall(b"stop\n")
            try:
                s.recv(1024)
            except Exception:
                pass
            s.close()
            self._log("Dashboard stop sent")
        except Exception as e:
            self._log(f"Dashboard stop failed: {e}")

    # -----------------------------
    # Internal: 30002 socket
    # -----------------------------

    def _send_script_30002(self, script: str, timeout: float = 2.0) -> bool:
        """Send script via 30002 port (non-blocking, returns immediately after send)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((self.ip, SCRIPT_PORT))
            s.sendall(script.encode("utf-8"))
            s.close()
            return True
        except Exception as e:
            self._log(f"30002 send error: {e}")
            return False

    # -----------------------------
    # Logging
    # -----------------------------

    def _log(self, msg: str) -> None:
        """Log message and emit signal."""
        logger = logging.getLogger("ur_print_fdm.direct_mode")
        logger.info(msg)
        self.log_signal.emit(msg)
