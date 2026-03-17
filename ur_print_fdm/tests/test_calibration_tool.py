import math

import pytest
from PyQt6.QtWidgets import QApplication

from ur_print_fdm.core.print_lib import URPrintLib
from ur_print_fdm.ui.widgets.calibration import AutoCalibrationWidget


class _DummyDriver:
    def __init__(self):
        self.speed_stop_calls = 0

    def is_connected(self):
        return True

    def is_rtde_control_alive(self):
        return True, "ok"

    def get_tcp_pose(self):
        return [0.0, 0.0, 0.1, 0.0, 0.0, 0.0]

    def get_tcp_force(self):
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def move_l(self, pose, speed=0.1, acceleration=0.3):
        return True

    def speed_stop(self):
        self.speed_stop_calls += 1
        return True

    def zero_ft_sensor(self):
        return True

    def reconnect_control_interface(self, log_callback=None):
        return True

    def get_connection_snapshot(self):
        return None


class _DummyMain:
    def __init__(self):
        self.driver = _DummyDriver()
        self.print_lib = URPrintLib()
        self.logs = []

    def log(self, msg):
        self.logs.append(msg)


def test_fit_plane_feature_uses_explicit_reference_indices():
    lib = URPrintLib()
    points = [
        [0.0, 0.0, 0.0],
        [30.0, 30.0, 0.0],
        [100.0, 0.0, 0.0],
        [0.0, 100.0, 0.0],
    ]

    feat_str, log = lib.fit_plane_feature(points, origin_index=0, x_index=2, y_index=3)

    pose = lib.parse_pose_string(feat_str)
    assert pose[0:3] == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
    assert pose[3:6] == pytest.approx([0.0, 0.0, 0.0], abs=1e-6)
    assert "参考点: O=1, X=3, Y=4" in log


def test_fit_plane_feature_rejects_negative_y_reference():
    lib = URPrintLib()

    feat_str, log = lib.fit_plane_feature(
        [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [0.0, -100.0, 0.0]]
    )

    assert feat_str is None
    assert "负 Y 半轴" in log


def test_fit_plane_feature_rejects_collinear_points():
    lib = URPrintLib()

    feat_str, log = lib.fit_plane_feature(
        [[0.0, 0.0, 0.0], [100.0, 0.0, 0.0], [200.0, 0.0, 0.0]]
    )

    assert feat_str is None
    assert "近似共线" in log


def test_fit_plane_feature_handles_pi_rotation_without_nan():
    lib = URPrintLib()

    feat_str, _ = lib.fit_plane_feature(
        [[0.0, 0.0, 0.0], [-100.0, 0.0, 0.0], [0.0, -100.0, 0.0]]
    )

    pose = lib.parse_pose_string(feat_str)
    assert "nan" not in feat_str.lower()
    assert pose[0:3] == [0.0, 0.0, 0.0]
    assert pose[3] == pytest.approx(0.0, abs=1e-6)
    assert pose[4] == pytest.approx(0.0, abs=1e-6)
    assert abs(pose[5]) == pytest.approx(math.pi, abs=1e-6)


def test_auto_calibration_widget_delete_invalidates_feature_and_updates_refs():
    app = QApplication.instance() or QApplication([])
    widget = AutoCalibrationWidget(_DummyMain())
    try:
        widget.calibration_points = [
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
            [0.0, 0.1, 0.0],
        ]
        widget.reference_indices = {"origin": 0, "x": 1, "y": 2}
        widget._last_feature = "p[0,0,0,0,0,0]"
        widget.btn_save_to_lib.setEnabled(True)
        widget._refresh_point_list(selected_row=1)

        widget._delete_selected()

        assert widget.reference_indices == {"origin": 0, "x": None, "y": 1}
        assert widget._last_feature is None
        assert widget.btn_save_to_lib.isEnabled() is False
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_auto_calibration_widget_finish_multi_probe_assigns_pending_role():
    app = QApplication.instance() or QApplication([])
    main = _DummyMain()
    widget = AutoCalibrationWidget(main)
    try:
        widget._probe_measurements = [[0.1, 0.2, 0.3]]
        widget._probe_total = 1
        widget._pending_capture_role = "origin"

        widget._finish_multi_probe()

        assert widget.reference_indices["origin"] == 0
        assert widget.calibration_points == [[0.1, 0.2, 0.3]]
        assert "已将第 1 个点记录为原点" in main.logs
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_auto_calibration_widget_stop_cancels_pending_batch():
    app = QApplication.instance() or QApplication([])
    main = _DummyMain()
    widget = AutoCalibrationWidget(main)

    class _Worker:
        def __init__(self):
            self.stopped = False

        def stop(self):
            self.stopped = True

    try:
        worker = _Worker()
        widget.probe_worker = worker

        widget._stop_probe()
        widget._on_probe_finished_multi(False, [], 0.0, "用户取消")

        assert worker.stopped is True
        assert main.driver.speed_stop_calls == 1
        assert widget._next_probe_timer.isActive() is False
        assert "多次探测已取消" in main.logs
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()
