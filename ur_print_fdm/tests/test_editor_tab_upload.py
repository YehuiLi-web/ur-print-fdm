import os
from types import SimpleNamespace

from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.controllers.run_controller import RunController
from ur_print_fdm.ui.widgets.editor import DockableEditorWidget
from ur_print_fdm.ui.widgets.editor import manager as editor_manager
from ur_print_fdm.ui.widgets.upload_options_dialog import UploadOptionsDialog


def _set_editor_text(editor, text: str) -> None:
    setter = getattr(editor, "setText", None)
    if callable(setter):
        setter(text)
        return
    editor.setPlainText(text)


def test_editor_tab_context_menu_uploads_clicked_file(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    first = tmp_path / "first.script"
    second = tmp_path / "second.script"
    first.write_text("def first():\n  pass\n", encoding="utf-8")
    second.write_text("def second():\n  pass\n", encoding="utf-8")

    widget = DockableEditorWidget()
    try:
        widget.open_file_in_tab(str(first))
        widget.open_file_in_tab(str(second))

        received = []
        widget.upload_requested.connect(lambda files: received.append(files))

        first_index = next(
            index
            for index, path in widget.tab_paths.items()
            if os.path.normpath(path) == os.path.normpath(str(first))
        )
        menu = widget._build_tab_context_menu(first_index)
        upload_actions = [action for action in menu.actions() if action.text() == "上传到机器人"]

        assert len(upload_actions) == 1
        assert upload_actions[0].icon().isNull() is True
        assert "padding: 8px 18px 8px 16px;" in menu.styleSheet()

        upload_actions[0].trigger()

        assert received == [[os.path.normpath(str(first))]]
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_unsaved_editor_tab_does_not_offer_upload(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    widget = DockableEditorWidget()
    try:
        _, index = widget.create_new_tab()

        menu = widget._build_tab_context_menu(index)
        action_texts = [action.text() for action in menu.actions()]

        assert "上传到机器人" not in action_texts
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_opened_file_tab_keeps_extension_when_modified(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    script_path = tmp_path / "demo.script"
    script_path.write_text("def demo():\n  pass\n", encoding="utf-8")

    widget = DockableEditorWidget()
    try:
        widget.open_file_in_tab(str(script_path))

        idx = widget.tabs.currentIndex()
        editor = widget.get_current_editor()

        assert widget.tabs.tabText(idx) == "demo.script"

        _set_editor_text(editor, "def demo():\n  textmsg(\"changed\")\n")
        app.processEvents()

        assert widget.tabs.tabText(idx) == "● demo.script"
        assert widget.tab_modified[idx] is True
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_open_file_reuses_empty_untitled_tab(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    script_path = tmp_path / "reused.script"
    script_path.write_text("def reused():\n  pass\n", encoding="utf-8")

    widget = DockableEditorWidget()
    try:
        _, _ = widget.create_new_tab()
        before_count = widget.tabs.count()

        widget.open_file_in_tab(str(script_path))

        current_idx = widget.tabs.currentIndex()
        assert widget.tabs.count() == before_count
        assert widget.tabs.tabText(current_idx) == "reused.script"
        assert widget.tab_paths[current_idx] == os.path.normpath(str(script_path))
        assert widget.tab_modified[current_idx] is False
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_moving_tabs_keeps_modified_marker_on_same_editor(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    first = tmp_path / "first.script"
    second = tmp_path / "second.script"
    first.write_text("def first():\n  pass\n", encoding="utf-8")
    second.write_text("def second():\n  pass\n", encoding="utf-8")

    widget = DockableEditorWidget()
    try:
        widget.open_file_in_tab(str(first))
        first_editor = widget.get_current_editor()
        widget.open_file_in_tab(str(second))
        second_editor = widget.get_current_editor()

        widget.tabs.tabBar().moveTab(1, 0)
        app.processEvents()

        assert widget.tab_paths[0] == os.path.normpath(str(second))
        assert widget.tab_paths[1] == os.path.normpath(str(first))

        _set_editor_text(second_editor, "def second():\n  textmsg(\"edited\")\n")
        app.processEvents()

        assert widget.tabs.tabText(0) == "● second.script"
        assert widget.tabs.tabText(1) == "first.script"
        assert second_editor is not first_editor
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_get_current_editor_returns_none_on_welcome_tab(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    widget = DockableEditorWidget()
    try:
        assert widget.tabs.tabText(widget.tabs.currentIndex()) == "欢迎"
        assert widget.get_current_editor() is None
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_save_current_tab_updates_tab_metadata(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(editor_manager, "SESSION_FILE", str(tmp_path / "editor_session.json"))

    save_path = tmp_path / "saved.script"
    monkeypatch.setattr(
        editor_manager.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(save_path), "URScript Files (*.script)"),
    )

    widget = DockableEditorWidget()
    try:
        _, index = widget.create_new_tab()
        editor = widget.get_current_editor()
        _set_editor_text(editor, "def saved():\n  pass\n")
        app.processEvents()

        returned_path = widget.save_current_tab()

        assert returned_path == os.path.normpath(str(save_path))
        assert widget.tabs.tabText(index) == "saved.script"
        assert widget.tab_paths[index] == os.path.normpath(str(save_path))
        assert widget.tab_modified[index] is False
        assert save_path.read_text(encoding="utf-8") == "def saved():\n  pass\n"
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_run_controller_save_for_run_uses_editor_manager_save_api(tmp_path):
    calls = []

    class _DockableEditor:
        def __init__(self):
            self.tabs = SimpleNamespace(currentIndex=lambda: 0)
            self.tab_paths = {0: ""}

        def save_current_tab(self, **kwargs):
            calls.append(kwargs)
            return str(tmp_path / "queued.script")

    window = SimpleNamespace(
        get_current_editor=lambda: SimpleNamespace(toPlainText=lambda: "def a():\n  pass\n"),
        dockable_editor=_DockableEditor(),
        project_widget=SimpleNamespace(current_project_path=str(tmp_path)),
    )

    controller = RunController(window)

    assert controller._save_current_script_for_run() == str(tmp_path / "queued.script")
    assert calls == [{
        "prompt_title": "保存脚本以运行（生产模式）",
        "default_save_path": str(tmp_path / "新脚本.script"),
        "dialog_parent": window,
    }]


def test_upload_options_dialog_allows_single_file_load_action():
    app = QApplication.instance() or QApplication([])

    dialog = UploadOptionsDialog(file_count=1)
    try:
        assert dialog.upload_only_button is not None
        assert dialog.upload_and_load_button is not None
        assert dialog.header_icon_label is not None
        assert dialog.header_icon_label.pixmap() is not None
        assert dialog.actions_panel is not None
        assert isinstance(dialog.actions_panel.layout(), QHBoxLayout)
        assert dialog.upload_only_button.isDefault() is True
        assert dialog.upload_and_load_button.isEnabled() is True
        assert dialog.minimumHeight() == dialog.maximumHeight()
        assert dialog.minimumHeight() >= dialog.sizeHint().height()
        assert dialog.width() == 404

        dialog.upload_and_load_button.click()

        assert dialog.result_role() == UploadOptionsDialog.UploadAndLoad
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_upload_options_dialog_disables_load_action_for_multiple_files():
    app = QApplication.instance() or QApplication([])

    dialog = UploadOptionsDialog(file_count=3)
    try:
        assert dialog.upload_only_button is not None
        assert dialog.upload_and_load_button is not None
        assert dialog.actions_panel is not None
        assert isinstance(dialog.actions_panel.layout(), QHBoxLayout)
        assert dialog.upload_only_button.isEnabled() is True
        assert dialog.upload_and_load_button.isEnabled() is False

        dialog.reject()

        assert dialog.result_role() == UploadOptionsDialog.Cancel
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
