"""Render the redesigned auto calibration UI for visual review."""

from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog, QLabel, QTabWidget, QVBoxLayout, QWidget

from ur_print_fdm.ui.theme_manager import get_theme_manager
from ur_print_fdm.ui.widgets.calibration import AutoCalibrationWidget


class FakeDriver:
    def is_connected(self):
        return True

    def get_tcp_pose(self):
        return [0.3184, -0.1428, 0.1265, 3.1410, 0.0120, -0.0860]

    def get_tcp_force(self):
        return [0.04, -0.11, 1.62, 0.0, 0.0, 0.0]

    def zero_ft_sensor(self):
        return True

    def is_rtde_control_alive(self):
        return True, "ok"

    def move_l(self, pose, speed, accel):
        return True

    def speed_stop(self):
        return True


class FakePrintLib:
    def fit_plane_feature(self, *args, **kwargs):
        return None, ""


class FakeMain:
    def __init__(self):
        self.driver = FakeDriver()
        self.print_lib = FakePrintLib()

    def log(self, message):
        print(message)


def make_placeholder(text: str) -> QWidget:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.addStretch()
    label = QLabel(text)
    label.setStyleSheet("color: #7d7d7d;")
    layout.addWidget(label)
    layout.addStretch()
    return page


def populate_preview(widget: AutoCalibrationWidget) -> None:
    widget.spin_force_threshold.setValue(2.5)
    widget.spin_speed.setValue(4.0)
    widget.spin_repeat.setValue(1)
    widget.spin_z_offset.setValue(0.2)

    widget.calibration_points = [
        [0.3184, -0.1428, 0.0210],
        [0.3484, -0.1428, 0.0212],
        [0.3184, -0.1128, 0.0209],
        [0.3385, -0.1272, 0.0211],
    ]
    widget.reference_indices = {"origin": 0, "x": 1, "y": 2}
    widget._refresh_point_list(selected_row=3)
    widget._last_feature = "p[0.3184,-0.1428,0.0211,3.1410,0.0120,-0.0860]"
    widget.btn_save_to_lib.setEnabled(True)
    widget.txt_result.setPlainText(
        "feature1 = p[0.3184,-0.1428,0.0211,3.1410,0.0120,-0.0860]\n\n"
        "残差: 0.018 mm\n"
        "倾角: 0.41 deg"
    )
    widget._update_live_display()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    get_theme_manager().set_theme("dark")

    main_window = FakeMain()
    dialog = QDialog()
    dialog.setWindowTitle("平面标定")
    dialog.resize(1040, 760)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    tabs = QTabWidget()
    tabs.addTab(make_placeholder("手动标定预留"), "手动标定")

    auto_widget = AutoCalibrationWidget(main_window)
    populate_preview(auto_widget)
    tabs.addTab(auto_widget, "自动标定 (力控)")
    tabs.addTab(make_placeholder("Feature 库预留"), "Feature 库")
    tabs.setCurrentWidget(auto_widget)
    layout.addWidget(tabs)

    dialog.show()
    app.processEvents()
    app.processEvents()

    output_path = Path("/mnt/e/Project/manual_checks/calibration_auto_redesign_preview.png")
    dialog.grab().save(str(output_path))
    print(output_path)

    dialog.close()
    dialog.deleteLater()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
