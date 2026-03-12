from PyQt6.QtWidgets import QApplication

from ur_print_fdm.shared.connection_state import ChannelState, ConnectionSnapshot, SessionPhase


def test_main_window_can_initialize_toolbar():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE
    from ur_print_fdm.ui.widgets.fused_combo_box import FusedComboBox
    from ur_print_fdm.ui.widgets.toolbar_mode_selector import ToolbarModeSelector

    win = URPrintIDE()
    try:
        assert win.btn_play_pause is not None
        assert win.btn_global_stop is not None
        assert win.btn_extrusion_stop is not None
        assert win.btn_repair_connection is not None
        assert isinstance(win.ip_combo, FusedComboBox)
        assert win.ip_combo.isEditable() is True
        assert win.run_mode_combo is not None
        assert isinstance(win.run_mode_combo, ToolbarModeSelector)
        assert win.run_mode_combo.property("ui_variant") == "mode_selector"
        assert win.run_mode_combo.currentData() in {"production", "direct"}
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


def test_main_window_connection_snapshot_controls_toolbar_state():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    try:
        win._apply_connection_snapshot(
            ConnectionSnapshot(
                phase=SessionPhase.ONLINE_DASHBOARD_ONLY,
                ip="192.168.1.100",
                receive=ChannelState.UP,
                control=ChannelState.STALE,
                dashboard=ChannelState.UP,
                control_reason="loader 接管",
            )
        )
        assert win.status_text_label.text() == "生产就绪"
        assert win.btn_connect.text() == "断开"
        assert win.btn_repair_connection.isEnabled() is True
        assert win.btn_play_pause.isEnabled() is True

        direct_index = win.run_mode_combo.findData("direct")
        win.run_mode_combo.setCurrentIndex(direct_index)
        win._apply_connection_snapshot(
            ConnectionSnapshot(
                phase=SessionPhase.ONLINE_MONITOR_ONLY,
                ip="192.168.1.100",
                receive=ChannelState.UP,
                control=ChannelState.STALE,
                dashboard=ChannelState.DOWN,
            )
        )
        assert win.status_text_label.text() == "仅监控"
        assert win.btn_play_pause.isEnabled() is True

        win._apply_connection_snapshot(
            ConnectionSnapshot(
                phase=SessionPhase.FAULTED,
                ip="192.168.1.100",
                receive=ChannelState.DOWN,
                control=ChannelState.DOWN,
                dashboard=ChannelState.DOWN,
                last_error="RTDE Receive disconnected",
            )
        )
        assert win.btn_connect.text() == "修复连接"
        assert win.btn_repair_connection.isEnabled() is True
        assert win.ip_combo.isEnabled() is True
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
