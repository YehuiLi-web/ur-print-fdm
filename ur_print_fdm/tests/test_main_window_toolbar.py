from PyQt6.QtWidgets import QApplication


def test_main_window_can_initialize_toolbar():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        assert win.btn_play_pause is not None
        assert win.btn_global_stop is not None
        assert win.run_mode_combo is not None
    finally:
        # Ensure Qt objects are cleaned up to avoid interpreter shutdown crashes on Windows.
        win.close()
        win.deleteLater()
        app.processEvents()

        # Avoid leaking the global UI log handler across tests.
        import logging

        root = logging.getLogger()
        for h in list(root.handlers):
            if getattr(h, "name", None) == "ur_print_fdm_ui":
                root.removeHandler(h)
                try:
                    h.close()
                except Exception:
                    pass
