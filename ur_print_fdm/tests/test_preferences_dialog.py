from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.widgets.preferences_dialog import PreferencesDialog


def test_preferences_dialog_can_rebuild_categories():
    app = QApplication.instance() or QApplication([])

    dlg = PreferencesDialog()
    dlg._build_categories()
    dlg._rebuild_from_working_config()

    assert dlg.pages.count() > 0

