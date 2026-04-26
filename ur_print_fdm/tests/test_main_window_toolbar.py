import time

from PyQt6.QtWidgets import QApplication, QSizePolicy

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
        assert win.btn_save is None
        assert win.btn_save_script is None
        assert win.btn_connect.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert win.btn_play_pause.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert win.btn_global_stop.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert win.btn_extrusion_stop.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert win.btn_upload.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
        assert win.toolbarControlGroup.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed
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
        assert win.btn_connect.text() == "修复"
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


def test_main_window_project_dock_uses_file_explorer_minimum_width():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE
    from ur_print_fdm.ui.widgets.file_explorer import FileExplorerWidget

    win = URPrintIDE()
    win.show()
    app.processEvents()
    try:
        assert win.project_widget.minimumWidth() == FileExplorerWidget.COMPACT_MINIMUM_WIDTH
        assert win.dock_project.minimumWidth() == FileExplorerWidget.COMPACT_MINIMUM_WIDTH
        assert win.dock_project.width() >= FileExplorerWidget.COMPACT_MINIMUM_WIDTH
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


def test_main_window_base_move_request_uses_current_tcp_pose():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.main_window import URPrintIDE

    win = URPrintIDE()
    calls = {}
    snapshot = ConnectionSnapshot(
        phase=SessionPhase.ONLINE_FULL,
        ip="192.168.1.100",
        receive=ChannelState.UP,
        control=ChannelState.UP,
        dashboard=ChannelState.UP,
    )
    try:
        win.driver.is_rtde_control_alive = lambda: (True, "ok")
        win.driver.get_tcp_pose = lambda: [0.100, -0.200, 0.300, 1.0, -2.0, 0.5]
        win.driver.get_connection_snapshot = lambda: snapshot
        win.driver.probe_connection_snapshot = lambda probe_dashboard=False: snapshot

        def _move_l(target, speed=0.25, acceleration=1.2, asynchronous=False):
            calls["target"] = list(target)
            calls["speed"] = speed
            calls["acceleration"] = acceleration
            calls["asynchronous"] = asynchronous
            return True

        win.driver.move_l = _move_l
        win._apply_connection_snapshot(snapshot)

        win._on_base_move_requested(0.001, 0.0, 0.0)

        deadline = time.monotonic() + 1.0
        while win.base_move_thread is not None and time.monotonic() < deadline:
            app.processEvents()

        assert calls["target"] == [0.101, -0.200, 0.300, 1.0, -2.0, 0.5]
        assert calls["speed"] == win.BASE_MOVE_SPEED_M_S
        assert calls["acceleration"] == win.BASE_MOVE_ACCEL_M_S2
        assert calls["asynchronous"] is False
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
