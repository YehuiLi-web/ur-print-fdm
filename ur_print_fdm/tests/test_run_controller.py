from __future__ import annotations

from types import SimpleNamespace

from ur_print_fdm.ui.controllers.run_controller import RunController


class _Driver:
    def __init__(self, *, connected: bool = True, read_only: bool = False, ip: str = "192.168.1.100"):
        self._connected = connected
        self._read_only = read_only
        self._ip = ip

    def is_connected(self) -> bool:
        return self._connected

    def is_read_only(self) -> bool:
        return self._read_only

    def get_ip_address(self) -> str:
        return self._ip


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
    def __init__(self, *, mode: str = "production"):
        self.driver = _Driver()
        self.run_mode_combo = _RunModeCombo(mode)
        self._single_run_processor = None
        self.processor = None
        self._direct_mode_processor = None
        self.stop_thread = None
        self.btn_play_pause = SimpleNamespace(setEnabled=lambda _enabled: None)
        self.btn_global_stop = SimpleNamespace(setEnabled=lambda _enabled: None)
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
