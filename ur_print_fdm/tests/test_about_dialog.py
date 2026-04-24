from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QPushButton

from ur_print_fdm import __version__


def _cleanup_ui_log_handlers() -> None:
    import logging

    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "name", None) == "ur_print_fdm_ui":
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass


def test_about_dialog_exposes_updated_product_positioning():
    app = QApplication.instance() or QApplication([])

    with patch(
        "ur_print_fdm.ui.widgets.about_dialog.load_latest_release_notes_body",
        return_value="- 修复安装路径记忆\n- 新增版本说明展示",
    ):
        from ur_print_fdm.ui.widgets.about_dialog import AboutDialog

        dialog = AboutDialog()
        try:
            assert dialog.windowTitle() == "关于 ur-print-fdm"

            product_name = dialog.findChild(QLabel, "aboutProductName")
            assert product_name is not None
            assert product_name.text() == "ur-print-fdm"

            version_badge = dialog.findChild(QLabel, "aboutVersionBadge")
            assert version_badge is not None
            assert version_badge.text() == f"v{__version__}"

            subtitle = dialog.findChild(QLabel, "aboutSubtitle")
            assert subtitle is not None
            assert "打印控制" in subtitle.text()
            assert "轨迹执行" in subtitle.text()

            release_notes = dialog.findChild(QLabel, "aboutReleaseNotesBody")
            assert release_notes is not None
            assert "修复安装路径记忆" in release_notes.text()
            assert "新增版本说明展示" in release_notes.text()

            assert dialog.findChild(QFrame, "aboutHeroCard") is not None
            assert dialog.findChild(QFrame, "aboutReleaseNotesCard") is not None
            assert dialog.findChild(QFrame, "aboutInfoCard") is None
            assert dialog.findChild(QPushButton, "aboutConfirmButton") is None
            assert dialog.layout().count() == 2
        finally:
            dialog.close()
            dialog.deleteLater()
            app.processEvents()


def test_main_window_about_action_uses_about_dialog():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        with patch("ur_print_fdm.ui.main_window.AboutDialog") as about_dialog_cls:
            dialog = about_dialog_cls.return_value

            win._show_about_dialog()

            about_dialog_cls.assert_called_once_with(win)
            dialog.exec.assert_called_once_with()
    finally:
        win.close()
        win.deleteLater()
        app.processEvents()
        _cleanup_ui_log_handlers()
