"""Render the about dialog to a temp image for visual inspection."""

from pathlib import Path
import tempfile

from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.theme_manager import get_theme_manager
from ur_print_fdm.ui.widgets.about_dialog import AboutDialog


def main() -> int:
    app = QApplication.instance() or QApplication([])
    get_theme_manager().set_theme("dark")

    dialog = AboutDialog()
    dialog.show()
    app.processEvents()
    app.processEvents()

    output_path = Path(tempfile.gettempdir()) / "about_dialog_preview.png"
    dialog.grab().save(str(output_path))
    print(output_path)

    dialog.close()
    dialog.deleteLater()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
