from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QMenu

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

        estimate_action = next((a for a in script_menu.actions() if a.text() == "脚本估算..."), None)
        assert estimate_action is not None
        assert not estimate_action.icon().isNull()
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


def test_file_explorer_context_menu_has_script_estimate_icon(tmp_path: Path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.resources.icon_manager import IconManager
    from ur_print_fdm.ui.widgets import file_explorer as file_explorer_module

    script_path = tmp_path / "demo.script"
    script_path.write_text("def demo():\n  pass\n", encoding="utf-8")

    monkeypatch.setattr(file_explorer_module.config_manager, "get", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(file_explorer_module.config_manager, "set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(file_explorer_module.config_manager, "save_config", lambda *_args, **_kwargs: None)

    widget = file_explorer_module.FileExplorerWidget()
    captured_actions = []
    try:
        widget.load_project(str(tmp_path))
        widget.show()
        app.processEvents()

        script_item = next(
            widget.root_item.child(i)
            for i in range(widget.root_item.childCount())
            if widget.root_item.child(i).data(0, Qt.ItemDataRole.UserRole) == str(script_path)
        )
        position = widget.tree.visualItemRect(script_item).center()

        def fake_exec(menu: QMenu, *_args, **_kwargs):
            captured_actions[:] = menu.actions()
            return None

        monkeypatch.setattr(QMenu, "exec", fake_exec)

        widget.show_context_menu(position if position != QPoint() else QPoint(4, 4))

        estimate_action = next((action for action in captured_actions if action.text() == "脚本估算..."), None)
        assert estimate_action is not None
        assert not estimate_action.icon().isNull()
        assert not IconManager.get_action_icon("script_estimate").isNull()
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


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
