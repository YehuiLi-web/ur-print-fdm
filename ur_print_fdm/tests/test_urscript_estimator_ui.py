from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from ur_print_fdm.config.defaults import DEFAULTS


def test_defaults_disable_urscript_estimate_on_run_by_default() -> None:
    assert "urscript_estimate_on_run" in DEFAULTS.get("ui", {})
    assert DEFAULTS["ui"]["urscript_estimate_on_run"] is False


def test_main_window_has_script_estimate_menu_action() -> None:
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        tools_menu = None
        for act in win.menuBar().actions():
            if "工具" in act.text() and act.menu() is not None:
                tools_menu = act.menu()
                break
        assert tools_menu is not None

        script_menu = None
        for act in tools_menu.actions():
            if act.menu() is not None and act.text() == "脚本处理":
                script_menu = act.menu()
                break
        assert script_menu is not None

        assert any(a.text() == "脚本估算..." for a in script_menu.actions())
    finally:
        win.close()
        win.deleteLater()
        app.processEvents()

        import logging

        root = logging.getLogger()
        for h in list(root.handlers):
            if getattr(h, "name", None) == "ur_print_fdm_ui":
                root.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass


def test_preferences_dialog_exposes_urscript_estimate_toggle() -> None:
    app = QApplication.instance() or QApplication([])

    from PyQt6.QtWidgets import QCheckBox

    from ur_print_fdm.ui.widgets.preferences_dialog import PreferencesDialog

    dlg = PreferencesDialog()
    try:
        dlg._build_categories()
        dlg._rebuild_from_working_config()

        checkboxes = dlg.findChildren(QCheckBox)
        assert any(("URScript" in cb.text() and "估算" in cb.text()) for cb in checkboxes)
    finally:
        dlg.close()
        dlg.deleteLater()
        app.processEvents()
