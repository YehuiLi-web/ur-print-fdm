from __future__ import annotations

from types import SimpleNamespace

from ur_print_fdm.shared.connection_state import ChannelState, ConnectionSnapshot, SessionPhase
from ur_print_fdm.ui.controllers.run_controller import RunController
from ur_print_fdm.ui.widgets.styled_message_box import StyledMessageBox


class _Driver:
    def __init__(
        self,
        *,
        connected: bool = True,
        read_only: bool = False,
        ip: str = "192.168.1.100",
        snapshot: ConnectionSnapshot | None = None,
    ):
        self._connected = connected
        self._read_only = read_only
        self._ip = ip
        self._snapshot = snapshot

    def is_connected(self) -> bool:
        return self._connected

    def is_read_only(self) -> bool:
        return self._read_only

    def get_ip_address(self) -> str:
        return self._ip

    def get_connection_snapshot(self):
        return self._snapshot


class _RunModeCombo:
    def __init__(self, mode: str):
        self._mode = mode

    def currentData(self):
        return self._mode

    def findData(self, _value):
        return 0

    def setCurrentIndex(self, _index):
        return None


class _Window:
    def __init__(self, *, mode: str = "production", driver: _Driver | None = None):
        self.driver = driver or _Driver()
        self.run_mode_combo = _RunModeCombo(mode)
        self._single_run_processor = None
        self.processor = None
        self._direct_mode_processor = None
        self.stop_thread = None
        self.extrusion_stop_thread = None
        self.btn_play_pause = SimpleNamespace(setEnabled=lambda _enabled: None)
        self.btn_global_stop = SimpleNamespace(setEnabled=lambda _enabled: None)
        self.btn_extrusion_stop = SimpleNamespace(setEnabled=lambda _enabled: None)
        self.logs: list[tuple[str, str]] = []

    def get_current_editor(self):
        return SimpleNamespace(toPlainText=lambda: "text")

    def _start_urscript_estimate_on_run(self, _script_content: str, *, trace_id: str | None = None):
        return trace_id

    def _on_direct_mode_script_sent(self, _success: bool, _message: str):
        return None

    def _on_direct_mode_finished(self):
        return None

    def log(self, message: str, level: str = "INFO"):
        self.logs.append((level, message))

    def on_extrusion_stop_finished(self, _message: str):
        return None

    def on_extrusion_stop_timeout(self):
        return None


def test_run_current_script_routes_to_production():
    window = _Window(mode="production")
    controller = RunController(window)
    called = {"save": 0, "start": None}

    controller._save_current_script_for_run = lambda: called.__setitem__("save", called["save"] + 1) or "demo.script"
    controller._start_single_run_production = lambda path: called.__setitem__("start", path)

    controller.run_current_script()

    assert called["save"] == 1
    assert called["start"] == "demo.script"


def test_stop_current_script_routes_to_direct_mode():
    window = _Window(mode="direct")
    controller = RunController(window)
    called = {"stop_direct": 0}

    controller.stop_direct_mode = lambda: called.__setitem__("stop_direct", called["stop_direct"] + 1)

    controller.stop_current_script()

    assert called["stop_direct"] == 1


def test_stop_extrusion_starts_dedicated_thread(monkeypatch):
    window = _Window(mode="production")
    controller = RunController(window)
    called = {"started": 0, "timer_started": 0}

    class _Signal:
        def connect(self, _callback):
            return None

    class _Thread:
        def __init__(self, driver, *, trace_id=None):
            called["driver"] = driver
            called["trace_id"] = trace_id
            self.finished_signal = _Signal()
            self.finished = _Signal()

        def isRunning(self):
            return False

        def start(self):
            called["started"] += 1

        def deleteLater(self):
            return None

    class _Timer:
        def setSingleShot(self, _value):
            return None

        def timeout(self):
            return None

        def start(self, _ms):
            called["timer_started"] += 1

        def stop(self):
            return None

    class _TimerSignal:
        def connect(self, _callback):
            return None

    timer = _Timer()
    timer.timeout = _TimerSignal()

    monkeypatch.setattr("ur_print_fdm.ui.controllers.run_controller.StopExtrusionThread", _Thread)
    monkeypatch.setattr("ur_print_fdm.ui.controllers.run_controller.QTimer", lambda: timer)

    controller.stop_extrusion()

    assert called["started"] == 1
    assert called["timer_started"] == 1
    assert window.extrusion_stop_thread is not None


def test_stop_current_script_active_production_prefers_normal_stop(monkeypatch):
    window = _Window(mode="production")
    controller = RunController(window)
    called = {"stop": 0, "emergency": 0}

    class _Processor:
        def isRunning(self):
            return True

        def stop(self):
            called["stop"] += 1

        def emergency_stop_action(self):
            called["emergency"] += 1

    monkeypatch.setattr(
        "ur_print_fdm.ui.controllers.run_controller.StyledMessageBox.question",
        lambda *_args: StyledMessageBox.Yes,
    )

    controller._get_active_production_processor = lambda: _Processor()
    controller.stop_current_script()

    assert called["stop"] == 1
    assert called["emergency"] == 0


def test_run_current_script_blocks_production_when_dashboard_is_unavailable(monkeypatch):
    snapshot = ConnectionSnapshot(
        phase=SessionPhase.ONLINE_MONITOR_ONLY,
        ip="192.168.1.100",
        receive=ChannelState.UP,
        control=ChannelState.STALE,
        dashboard=ChannelState.DOWN,
    )
    window = _Window(mode="production", driver=_Driver(snapshot=snapshot))
    controller = RunController(window)
    called = {"warning": 0, "save": 0}

    controller._save_current_script_for_run = lambda: called.__setitem__("save", called["save"] + 1) or "demo.script"
    monkeypatch.setattr(
        "ur_print_fdm.ui.controllers.run_controller.StyledMessageBox.warning",
        lambda *_args: called.__setitem__("warning", called["warning"] + 1),
    )

    controller.run_current_script()

    assert called["warning"] == 1
    assert called["save"] == 0


def test_run_current_script_allows_direct_mode_with_monitor_only_snapshot(monkeypatch):
    snapshot = ConnectionSnapshot(
        phase=SessionPhase.ONLINE_MONITOR_ONLY,
        ip="192.168.1.100",
        receive=ChannelState.UP,
        control=ChannelState.STALE,
        dashboard=ChannelState.DOWN,
    )
    window = _Window(mode="direct", driver=_Driver(snapshot=snapshot))
    controller = RunController(window)
    started = {"count": 0}

    class _Signal:
        def connect(self, _callback):
            return None

    class _Processor:
        def __init__(self, *_args, **_kwargs):
            self.log_signal = _Signal()
            self.script_sent_signal = _Signal()
            self.finished_signal = _Signal()
            self.error_signal = _Signal()

        def isRunning(self):
            return False

        def set_action_run(self, _script):
            return None

        def start(self):
            started["count"] += 1

    monkeypatch.setattr("ur_print_fdm.ui.controllers.run_controller.DirectModeProcessor", _Processor)

    controller.run_current_script()

    assert started["count"] == 1
