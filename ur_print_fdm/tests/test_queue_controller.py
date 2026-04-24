from types import SimpleNamespace

from ur_print_fdm.shared.operation_result import OperationResult
from ur_print_fdm.ui.controllers.queue_controller import QueueController


class _Item:
    def __init__(self, text: str):
        self._text = text

    def text(self) -> str:
        return self._text


class _QueueList:
    def __init__(self, items=None, selected_indices=None):
        self._items = [str(item) for item in (items or [])]
        self._selected_indices = list(selected_indices or [])
        self.enabled = True

    def count(self):
        return len(self._items)

    def item(self, index):
        return _Item(self._items[index])

    def addItem(self, value):
        self._items.append(str(value))

    def selectedItems(self):
        return [_Item(self._items[index]) for index in self._selected_indices]

    def row(self, item):
        return self._items.index(item.text())

    def takeItem(self, index):
        self._items.pop(index)

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


class _Button:
    def __init__(self):
        self.enabled = True
        self.checked = False
        self.text = ""

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)

    def setChecked(self, checked):
        self.checked = bool(checked)

    def setText(self, text):
        self.text = text


class _Combo:
    def __init__(self, text):
        self._text = text
        self.enabled = True

    def currentText(self):
        return self._text

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


class _Check:
    def __init__(self, checked=True):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _Window:
    def __init__(self, ip="192.168.1.10", queue_items=None):
        self.queue_dialog = SimpleNamespace(
            btn_start_batch=_Button(),
            btn_stop_batch=_Button(),
            btn_pause_batch=_Button(),
        )
        self.queue_list = _QueueList(queue_items or [])
        self.ip_combo = _Combo(ip)
        self.chk_watchdog = _Check(True)
        self.run_mode_combo = _Combo(ip)
        self.btn_start_batch = _Button()
        self.btn_stop_batch = _Button()
        self._active_production_trace_id = None
        self.logs = []
        self.processor = None
        self.pause_state = None
        self.reset_pause_called = False
        self.refresh_called = False

    def log(self, message, level="INFO"):
        self.logs.append((level, message))

    def _set_play_pause_state(self, state):
        self.pause_state = state

    def _reset_global_pause_button(self):
        self.reset_pause_called = True

    def _refresh_global_run_enabled(self):
        self.refresh_called = True

    def _on_single_run_file_progress(self, value):
        self.last_progress = value

    def _on_production_error(self, error, trace_id):
        self.last_error = (error, trace_id)


def test_start_production_rejects_empty_queue(monkeypatch):
    window = _Window(queue_items=[])
    controller = QueueController(window)
    warnings = []

    monkeypatch.setattr(
        "ur_print_fdm.ui.controllers.queue_controller.StyledMessageBox.warning",
        lambda *args: warnings.append(args[2]),
    )

    result = controller.start_production(window.queue_list, True, None)

    assert result.success is False
    assert result.message == "empty queue"
    assert warnings


def test_start_production_rejects_invalid_ip(monkeypatch):
    window = _Window(ip="bad-ip", queue_items=["demo.script"])
    controller = QueueController(window)
    warnings = []

    monkeypatch.setattr(
        "ur_print_fdm.ui.controllers.queue_controller.StyledMessageBox.warning",
        lambda *args: warnings.append(args[2]),
    )

    result = controller.start_production(window.queue_list, True, None)

    assert result.success is False
    assert result.message == "invalid ip"
    assert warnings


def test_on_prod_finished_dialog_resets_queue_dialog_buttons():
    window = _Window(queue_items=["demo.script"])
    controller = QueueController(window)

    window.queue_dialog.btn_start_batch.setEnabled(False)
    window.queue_dialog.btn_stop_batch.setEnabled(True)
    window.queue_dialog.btn_pause_batch.setEnabled(True)
    window.queue_dialog.btn_pause_batch.setChecked(True)
    window._active_production_trace_id = None

    controller.on_prod_finished_dialog()

    assert window.queue_dialog.btn_start_batch.enabled is True
    assert window.queue_dialog.btn_stop_batch.enabled is False
    assert window.queue_dialog.btn_pause_batch.enabled is False
    assert window.queue_dialog.btn_pause_batch.checked is False
    assert window.reset_pause_called is True
    assert window.refresh_called is True


def test_save_selected_script_returns_failure_for_missing_selection(monkeypatch):
    window = _Window(queue_items=["demo.script"])
    window.queue_list = _QueueList(["demo.script"], selected_indices=[])
    controller = QueueController(window)
    warnings = []

    monkeypatch.setattr(
        "ur_print_fdm.ui.controllers.queue_controller.StyledMessageBox.warning",
        lambda *args: warnings.append(args[2]),
    )

    result = controller.save_selected_script(window.queue_list)

    assert result == OperationResult.fail("no queue selection")
    assert warnings
