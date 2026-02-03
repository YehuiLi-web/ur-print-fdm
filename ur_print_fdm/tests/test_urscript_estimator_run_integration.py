from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from ur_print_fdm.config import config_manager


def _set_run_mode(win, mode: str) -> None:
    idx = win.run_mode_combo.findData(mode)
    assert idx >= 0
    win.run_mode_combo.setCurrentIndex(idx)

def _cleanup_ui_log_handler() -> None:
    import logging

    root = logging.getLogger()
    for h in list(root.handlers):
        if getattr(h, "name", None) == "ur_print_fdm_ui":
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass


def test_run_does_not_start_estimate_timer_when_disabled(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        _set_run_mode(win, "direct")

        # Make the app think we're connected and able to send scripts.
        monkeypatch.setattr(win.driver, "is_connected", lambda: True)
        monkeypatch.setattr(win.driver, "is_read_only", lambda: False)
        monkeypatch.setattr(win.driver, "send_script", lambda _s: True)

        editor, _ = win.dockable_editor.create_new_tab()
        editor.setPlainText("def a():\n  sleep(0.1)\nend\na()\n")

        called = {"value": False}

        def _start_print_timer(_estimated_total_seconds: int = 0):
            called["value"] = True

        monkeypatch.setattr(win.status_widget, "start_print_timer", _start_print_timer)

        # Ensure the toggle is OFF.
        original_get = config_manager.get

        def fake_get(key: str, default=None):
            if key == "ui.urscript_estimate_on_run":
                return False
            return original_get(key, default)

        monkeypatch.setattr(config_manager, "get", fake_get)

        win.run_current_script()
        assert called["value"] is False
    finally:
        t = getattr(win, "script_thread", None)
        if t is not None:
            t.wait(2000)
        win.close()
        win.deleteLater()
        app.processEvents()
        _cleanup_ui_log_handler()


def test_run_starts_estimate_timer_when_enabled(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        _set_run_mode(win, "direct")

        monkeypatch.setattr(win.driver, "is_connected", lambda: True)
        monkeypatch.setattr(win.driver, "is_read_only", lambda: False)
        monkeypatch.setattr(win.driver, "send_script", lambda _s: True)

        editor, _ = win.dockable_editor.create_new_tab()
        editor.setPlainText("def a():\n  movel(p[0,0,0,0,0,0], a=1.0, v=0.1)\nend\na()\n")

        called = {"value": False}

        def _start_print_timer(_estimated_total_seconds: int = 0):
            called["value"] = True

        monkeypatch.setattr(win.status_widget, "start_print_timer", _start_print_timer)

        original_get = config_manager.get

        def fake_get(key: str, default=None):
            if key == "ui.urscript_estimate_on_run":
                return True
            return original_get(key, default)

        monkeypatch.setattr(config_manager, "get", fake_get)

        win.run_current_script()
        assert called["value"] is True
    finally:
        t = getattr(win, "script_thread", None)
        if t is not None:
            t.wait(2000)
        win.close()
        win.deleteLater()
        app.processEvents()
        _cleanup_ui_log_handler()
