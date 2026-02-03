import sys
import logging

from PyQt6.QtWidgets import QApplication


def main() -> int:
    from ur_print_fdm.config import config_manager
    from ur_print_fdm.shared.logging_setup import setup_file_logging

    setup = setup_file_logging(config_manager)
    logging.getLogger("ur_print_fdm").info("Logging initialized (session=%s, dir=%s)", setup.session_id, setup.log_dir)

    from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
    from ur_print_fdm.samples.loader import load_samples

    bootstrap_plugins()
    load_samples()

    # UI entrypoint (shimmed during migration)
    from ur_print_fdm.ui.main_window import URPrintIDE

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = URPrintIDE()
    win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
