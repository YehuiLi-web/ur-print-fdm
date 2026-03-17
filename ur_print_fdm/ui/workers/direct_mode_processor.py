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
import math
import re
import socket
import threading
import time

from PyQt6.QtCore import QThread, pyqtSignal

from ur_print_fdm.constants import SCRIPT_PORT
from ur_print_fdm.shared.logging_context import trace_context
from ur_print_fdm.shared.net import is_valid_ip
from ur_print_fdm.shared.script_sanitizer import sanitize_script_content

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
    RUNTIME_STOPPING = 0
    RUNTIME_STOPPED = 1
    RUNTIME_PLAYING = 2
    RUNTIME_PAUSING = 3
    RUNTIME_PAUSED = 4
    RUNTIME_RESUMING = 5

    _DASHBOARD_ERROR_TOKENS = ("error", "failed", "failure", "not connected", "unable", "denied")
    _UNREADY_ROBOTMODE_TOKENS = (
        "power_off",
        "power off",
        "booting",
        "idle",
        "confirm_safety",
        "confirm safety",
        "backdrive",
        "no_controller",
        "no controller",
        "disconnected",
    )
    _BLOCKING_SAFETY_TOKENS = (
        "protective_stop",
        "protective stop",
        "safeguard_stop",
        "safeguard stop",
        "system_emergency_stop",
        "system emergency stop",
        "robot_emergency_stop",
        "robot emergency stop",
        "emergency_stop",
        "emergency stop",
        "violation",
        "fault",
        "recovery",
    )
    _RUN_CONFIRM_TIMEOUT_S = 1.6
    _RUN_CONFIRM_SPEED_THRESHOLD = 0.001
    _RUN_CONFIRM_POSE_DELTA_M = 0.0005

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
                self.disconnect_monitor()
                self.running = False
                self.finished_signal.emit()

    # -----------------------------
    # Internal: Run script
    # -----------------------------

    def _do_run_script(self) -> None:
        """Send script via 30002 port and confirm that execution actually starts."""
        if not self.script_content or not self.script_content.strip():
            self.script_sent_signal.emit(False, "Script content is empty")
            return

        script_text = sanitize_script_content(self.script_content)
        compatible = self._is_socket_program_compatible(script_text)
        if compatible:
            script_to_send = script_text if script_text.endswith("\n") else script_text + "\n"
        else:
            script_to_send = self._wrap_as_socket_program(script_text)
            self._log("检测到脚本不符合 30002 主程序格式，已自动包装为外层 def 程序。")

        dashboard_snapshot = self._collect_dashboard_snapshot()
        preflight_error = self._build_preflight_error(
            script_text,
            dashboard_snapshot,
            socket_program_compatible=compatible,
        )
        if preflight_error:
            self.script_sent_signal.emit(False, preflight_error)
            return

        preflight_warning = self._build_preflight_warning(script_text, dashboard_snapshot)
        if preflight_warning:
            self._log(preflight_warning)

        monitor_ready = self.connect_monitor()
        if monitor_ready:
            self._log("RTDE 监控可用，发送后将确认机器人是否进入运行态...")
        else:
            self._log("RTDE 监控不可用，将尝试通过 Dashboard 辅助确认运行态...")

        self._log("Sending script via 30002 port...")
        success = self._send_script_30002(script_to_send)

        if not success:
            self.script_sent_signal.emit(False, "Failed to send script")
            return

        self._log("30002 发送成功，正在等待机器人进入运行态...")
        confirmed, observations = self._wait_for_run_start(timeout_s=self._RUN_CONFIRM_TIMEOUT_S)
        if confirmed:
            reason = observations.get("reason") or "机器人已进入运行态"
            self._log(reason)
            self.script_sent_signal.emit(True, "脚本已发送，并确认机器人开始执行。")
            return

        diagnostic = self._build_unconfirmed_run_message(
            script_text,
            observations,
            dashboard_snapshot,
            monitor_ready=monitor_ready,
            socket_program_compatible=compatible,
        )
        self.script_sent_signal.emit(False, diagnostic)

    # -----------------------------
    # Internal: Run diagnostics
    # -----------------------------

    @classmethod
    def _dashboard_response_is_error(cls, response: str | None) -> bool:
        low = str(response or "").strip().lower()
        if not low:
            return False
        return any(token in low for token in cls._DASHBOARD_ERROR_TOKENS)

    @staticmethod
    def _dashboard_response_value(response: str | None) -> str:
        text = str(response or "").strip()
        if ":" in text:
            return text.split(":", 1)[1].strip()
        return text

    @staticmethod
    def _significant_lines(script_content: str) -> list[str]:
        return [line.rstrip() for line in str(script_content or "").splitlines() if line.strip()]

    @classmethod
    def _is_socket_program_compatible(cls, script_content: str) -> bool:
        lines = cls._significant_lines(script_content)
        if not lines:
            return False
        first = lines[0]
        last = lines[-1]
        return (first.startswith("def ") or first.startswith("sec ")) and last == "end"

    @classmethod
    def _wrap_as_socket_program(cls, script_content: str) -> str:
        body = str(script_content or "").strip("\n")
        if not body:
            return "def direct_socket_program():\nend\n"

        indented_lines = [f"  {line}" if line else "" for line in body.splitlines()]
        return "def direct_socket_program():\n" + "\n".join(indented_lines) + "\nend\n"

    @staticmethod
    def _detect_missing_entry_call(script_content: str) -> str | None:
        stripped_script = str(script_content or "").strip()
        if not stripped_script.startswith("def "):
            return None

        match = re.match(r"def\s+(\w+)\s*\(", stripped_script)
        if not match:
            return None

        func_name = match.group(1)
        call_pattern = rf"(?<!def\s)(?<!\w){re.escape(func_name)}\s*\("
        if re.search(call_pattern, stripped_script):
            return None
        return func_name

    def _dashboard_command(self, command: str, *, timeout: float = 0.25) -> str | None:
        cmd = str(command or "").strip()
        if not cmd:
            return None

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((self.ip, 29999))
            try:
                s.recv(1024)
            except Exception:
                pass
            s.sendall((cmd + "\n").encode("utf-8"))
            return s.recv(1024).decode("utf-8", errors="replace").strip()
        except Exception:
            return None
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _collect_dashboard_snapshot(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for key, command in (
            ("robot_mode", "robotmode"),
            ("safety_mode", "safetymode"),
            ("program_state", "programState"),
            ("running", "running"),
        ):
            response = self._dashboard_command(command)
            if response and not self._dashboard_response_is_error(response):
                snapshot[key] = self._dashboard_response_value(response)
        return snapshot

    @classmethod
    def _robot_mode_is_unready(cls, robot_mode: str | None) -> bool:
        low = str(robot_mode or "").strip().lower()
        if not low:
            return False
        return any(token in low for token in cls._UNREADY_ROBOTMODE_TOKENS)

    @classmethod
    def _safety_mode_blocks_run(cls, safety_mode: str | None) -> bool:
        low = str(safety_mode or "").strip().lower()
        if not low:
            return False
        return any(token in low for token in cls._BLOCKING_SAFETY_TOKENS)

    def _build_preflight_error(
        self,
        script_content: str,
        dashboard_snapshot: dict[str, str],
        *,
        socket_program_compatible: bool,
    ) -> str | None:
        missing_entry = None if socket_program_compatible else self._detect_missing_entry_call(script_content)
        if missing_entry:
            return (
                f"直连模式已取消：检测到脚本定义了函数 '{missing_entry}'，"
                "但没有看到入口调用，机器人很可能不会执行任何动作。"
            )

        safety_mode = dashboard_snapshot.get("safety_mode")
        if self._safety_mode_blocks_run(safety_mode):
            return f"直连模式已取消：机器人当前安全状态异常（{safety_mode}）。请先解除安全停机/弹窗。"

        robot_mode = dashboard_snapshot.get("robot_mode")
        if self._robot_mode_is_unready(robot_mode):
            return f"直连模式已取消：机器人当前模式未就绪（{robot_mode}）。"

        return None

    def _build_preflight_warning(self, script_content: str, dashboard_snapshot: dict[str, str]) -> str | None:
        warnings: list[str] = []

        running = str(dashboard_snapshot.get("running", "")).strip().lower()
        program_state = str(dashboard_snapshot.get("program_state", "")).strip().upper()
        if running == "true" or program_state in {"PLAYING", "PAUSED"}:
            warnings.append("检测到控制器当前已有程序在运行，30002 脚本会直接替换它。")

        if not dashboard_snapshot:
            warnings.append("Dashboard 诊断不可用，若发送后无动作请重点检查遥控模式与安全状态。")

        if not warnings:
            return None
        return " ".join(warnings)

    def _get_monitor_snapshot(self) -> dict[str, object]:
        snapshot: dict[str, object] = {
            "runtime_state": None,
            "speed": None,
            "pose": None,
        }
        with self._rr_lock:
            rr = self._rr

        if rr is None:
            return snapshot

        try:
            if not rr.isConnected():
                return snapshot
        except Exception:
            return snapshot

        try:
            snapshot["runtime_state"] = rr.getRuntimeState()
        except Exception:
            pass

        try:
            speed_vec = rr.getActualTCPSpeed()
            if speed_vec:
                snapshot["speed"] = math.sqrt(sum(float(v) ** 2 for v in speed_vec[:3]))
        except Exception:
            pass

        try:
            pose = rr.getActualTCPPose()
            if pose:
                snapshot["pose"] = [float(v) for v in pose[:6]]
        except Exception:
            pass

        return snapshot

    @staticmethod
    def _pose_delta_m(baseline_pose: object, current_pose: object) -> float | None:
        try:
            if baseline_pose is None or current_pose is None:
                return None
            base = list(baseline_pose)
            current = list(current_pose)
            if len(base) < 3 or len(current) < 3:
                return None
            return math.sqrt(sum((float(current[i]) - float(base[i])) ** 2 for i in range(3)))
        except Exception:
            return None

    @classmethod
    def _runtime_state_name(cls, runtime_state: object) -> str:
        mapping = {
            cls.RUNTIME_STOPPING: "STOPPING",
            cls.RUNTIME_STOPPED: "STOPPED",
            cls.RUNTIME_PLAYING: "PLAYING",
            cls.RUNTIME_PAUSING: "PAUSING",
            cls.RUNTIME_PAUSED: "PAUSED",
            cls.RUNTIME_RESUMING: "RESUMING",
            None: "UNKNOWN",
        }
        return mapping.get(runtime_state, str(runtime_state))

    def _wait_for_run_start(self, *, timeout_s: float) -> tuple[bool, dict[str, object]]:
        baseline = self._get_monitor_snapshot()
        observations: dict[str, object] = {
            "runtime_state": baseline.get("runtime_state"),
            "speed": baseline.get("speed"),
            "pose_delta": 0.0,
            "program_state": "",
            "running": "",
            "reason": "",
        }

        next_dashboard_probe_at = 0.0
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            if self._stop_requested.is_set():
                break

            current = self._get_monitor_snapshot()
            runtime_state = current.get("runtime_state")
            if runtime_state is not None:
                observations["runtime_state"] = runtime_state
                if runtime_state == self.RUNTIME_PLAYING:
                    observations["reason"] = "检测到 RTDE runtime_state=PLAYING。"
                    return True, observations

            speed = current.get("speed")
            if isinstance(speed, (int, float)):
                observations["speed"] = float(speed)
                if float(speed) > self._RUN_CONFIRM_SPEED_THRESHOLD:
                    observations["reason"] = f"检测到 TCP 速度 > {self._RUN_CONFIRM_SPEED_THRESHOLD:.4f} m/s。"
                    return True, observations

            pose_delta = self._pose_delta_m(baseline.get("pose"), current.get("pose"))
            if pose_delta is not None:
                observations["pose_delta"] = pose_delta
                if pose_delta > self._RUN_CONFIRM_POSE_DELTA_M:
                    observations["reason"] = f"检测到 TCP 位姿变化约 {pose_delta * 1000:.2f} mm。"
                    return True, observations

            now = time.time()
            if now >= next_dashboard_probe_at:
                next_dashboard_probe_at = now + 0.25
                program_state = self._dashboard_response_value(self._dashboard_command("programState"))
                running = self._dashboard_response_value(self._dashboard_command("running"))
                if program_state:
                    observations["program_state"] = program_state
                    if str(program_state).strip().upper() == "PLAYING":
                        observations["reason"] = "检测到 Dashboard programState=PLAYING。"
                        return True, observations
                if running:
                    observations["running"] = running
                    if str(running).strip().lower() == "true":
                        observations["reason"] = "检测到 Dashboard running=true。"
                        return True, observations

            time.sleep(0.1)

        return False, observations

    def _build_unconfirmed_run_message(
        self,
        script_content: str,
        observations: dict[str, object],
        dashboard_snapshot: dict[str, str],
        *,
        monitor_ready: bool,
        socket_program_compatible: bool,
    ) -> str:
        hints: list[str] = []

        missing_entry = None if socket_program_compatible else self._detect_missing_entry_call(script_content)
        if missing_entry:
            hints.append(f"脚本可能没有入口调用（检测到 def {missing_entry}(...) 但没有显式调用）")

        safety_mode = dashboard_snapshot.get("safety_mode")
        if self._safety_mode_blocks_run(safety_mode):
            hints.append(f"安全状态异常：{safety_mode}")

        robot_mode = dashboard_snapshot.get("robot_mode")
        if self._robot_mode_is_unready(robot_mode):
            hints.append(f"机器人模式未就绪：{robot_mode}")

        if not monitor_ready:
            hints.append("RTDE 监控确认不可用")
        else:
            runtime_name = self._runtime_state_name(observations.get("runtime_state"))
            hints.append(f"未观测到进入 PLAYING（最后运行态：{runtime_name}）")

        program_state = str(observations.get("program_state") or dashboard_snapshot.get("program_state") or "").strip()
        if program_state:
            hints.append(f"Dashboard programState={program_state}")

        running = str(observations.get("running") or dashboard_snapshot.get("running") or "").strip()
        if running:
            hints.append(f"Dashboard running={running}")

        if not hints:
            hints.append("常见原因是机器人不在遥控模式、示教器有安全弹窗/保护停机，或脚本很快结束。")
        else:
            hints.append("若以上状态都正常，请再检查机器人是否处于遥控模式。")

        return "脚本已发送，但未确认机器人开始执行。请检查：" + "；".join(hints)

    # -----------------------------
    # Internal: Stop
    # -----------------------------

    def _do_stop(self) -> None:
        """Stop robot: Send Dashboard stop and 30002 stopj in parallel for fastest response."""
        self._log("Stopping robot...")
        self.connect_monitor()

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
            try:
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass
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
