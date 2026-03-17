import pytest
from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.widgets.collapsible_status_dock import JointsContent, StatusWidget, TCPPoseContent


def test_tcp_pose_content_displays_rotation_in_radians_and_copies_pose_literal():
    app = QApplication.instance() or QApplication([])

    widget = TCPPoseContent()
    try:
        widget.update_data([0.123456, -0.2, 0.005, 1.23456, -2.5, 0.0314])

        assert widget.unit_labels[3].text() == "rad"
        assert widget.unit_labels[4].text() == "rad"
        assert widget.unit_labels[5].text() == "rad"
        assert widget.labels[0].text() == "123.46"
        assert widget.labels[1].text() == "-200.00"
        assert widget.labels[2].text() == "5.00"
        assert widget.labels[3].text() == "1.235"
        assert widget.labels[4].text() == "-2.500"
        assert widget.labels[5].text() == "0.031"

        widget._copy_all_coordinates()

        assert QApplication.clipboard().text() == (
            "p[0.123456, -0.200000, 0.005000, 1.234560, -2.500000, 0.031400]"
        )
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_joints_content_formats_signed_angles_and_can_clear():
    app = QApplication.instance() or QApplication([])

    widget = JointsContent()
    widget.show()
    app.processEvents()
    try:
        widget.update_data([0.0, 1.5708, -1.5708, 3.2, -3.2, 6.4])

        assert widget.rows[0].lbl_value.text() == "+0.00°"
        assert widget.rows[0].lbl_value.isHidden() is False
        assert widget.rows[0].lbl_joint_name.isHidden() is True
        assert widget.rows[1].lbl_value.text() == "+90.00°"
        assert widget.rows[2].lbl_value.text() == "-90.00°"
        assert widget.rows[3].lbl_value.text() == "+183.35°"
        assert widget.rows[4].lbl_value.text() == "-183.35°"
        assert widget.rows[5].lbl_value.text() == "+366.69°"
        assert widget.rows[5].gauge._angle_deg == pytest.approx(366.6929888837269, rel=1e-4)

        widget.clear_data()

        assert all(row.lbl_value.text() == "--" for row in widget.rows)
        assert all(row.lbl_value.isHidden() is False for row in widget.rows)
        assert all(row.gauge._angle_deg is None for row in widget.rows)
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_joints_content_adapts_value_column_width_to_current_text():
    app = QApplication.instance() or QApplication([])

    widget = JointsContent()
    widget.show()
    app.processEvents()
    try:
        widget.clear_data()
        placeholder_width = widget._value_column_width

        widget.update_data([0.0, 1.5708, -1.5708, 3.2, -3.2, 6.4])
        value_width = widget._value_column_width

        assert placeholder_width > 0
        assert value_width > placeholder_width
        assert widget.legend_right_spacer.width() == value_width + widget.rows[0].ROW_SPACING
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_status_widget_clear_live_data_resets_joint_and_tcp_views():
    app = QApplication.instance() or QApplication([])

    widget = StatusWidget()
    try:
        widget.update_status(
            [0.100, -0.200, 0.005, 1.1, -2.2, 0.3],
            [0.0, 1.0, -1.0, 0.5, -0.5, 0.25],
            [0.001, 0.002, 0.003, 0.1, 0.2, 0.3],
        )
        widget.update_tcp_speed(0.123)

        assert widget.sec_tcp.header_meta_label.text() == "123.0 mm/s"

        widget.clear_live_data()

        assert widget.sec_tcp.header_meta_label.text() == "--.- mm/s"
        assert all(row.lbl_value.text() == "--" for row in widget.joints.rows)
        assert all(row.lbl_value.isHidden() is False for row in widget.joints.rows)
        assert all(label.text() == "--" for label in widget.tcp_pose.labels)
        assert all(label.text() == "--" for label in widget.tcp_offset.labels)
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_status_widget_fuses_tcp_speed_into_tcp_pose_header():
    app = QApplication.instance() or QApplication([])

    widget = StatusWidget()
    try:
        assert "motion" not in widget._sections
        assert all(key != "motion" for key, _, _ in widget.PANEL_DEFS)
        assert widget.sec_tcp.header_meta_label.text() == "--.- mm/s"

        widget.update_velocity(84.25)
        assert widget.sec_tcp.header_meta_label.text() == "84.2 mm/s"
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_status_widget_exposes_base_move_card_and_emits_base_relative_steps():
    app = QApplication.instance() or QApplication([])

    widget = StatusWidget()
    captured = []
    widget.base_move_requested.connect(lambda dx, dy, dz: captured.append((dx, dy, dz)))
    try:
        assert "base_move" in widget._sections
        assert any(key == "base_move" for key, _, _ in widget.PANEL_DEFS)

        widget.set_base_move_availability(True, reason="Base 点动就绪")
        widget.base_move.buttons["x_pos"].click()
        widget.base_move.step_buttons[10.0].click()
        widget.base_move.buttons["z_neg"].click()

        assert captured[0] == (0.001, 0.0, 0.0)
        assert captured[1] == (0.0, 0.0, -0.01)
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()
