from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.widgets.collapsible_status_dock import TCPPoseContent


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
