import copy
import json

from PyQt6.QtWidgets import QApplication

from ur_print_fdm.config import config_manager
from ur_print_fdm.config.defaults import DEFAULTS
from ur_print_fdm.config.manager import ConfigManager
from ur_print_fdm.ui.widgets.preferences_dialog import PreferencesDialog


def test_config_manager_migrates_legacy_real_robot_to_real_target(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "robot": {
                    "ip_addresses": ["192.168.0.88"],
                    "default_ip": "192.168.0.88",
                    "sftp": {
                        "port": 22,
                        "username": "root",
                        "password": "easybot",
                        "remote_dir": "/programs",
                    },
                    "dashboard": {
                        "loader_urp_path": "/programs/loader.urp",
                        "remote_loader_name": "remote_loader.script",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    cm = ConfigManager(config_path=config_file, defaults=copy.deepcopy(DEFAULTS))

    assert cm.get("robot.targets.active_id") == "real"
    assert cm.get("robot.targets.items.real.default_ip") == "192.168.0.88"
    assert cm.get("robot.targets.items.real.sftp.username") == "root"
    assert cm.get("robot.targets.items.virtual.sftp.username") == "ur"
    assert cm.get("robot.sftp.remote_dir") == "/programs"


def test_apply_dict_keeps_active_target_runtime_in_sync(tmp_path):
    cm = ConfigManager(config_path=tmp_path / "config.json", defaults=copy.deepcopy(DEFAULTS))
    data = cm.snapshot()

    data["robot"]["targets"]["active_id"] = "real"
    data["robot"]["ip_addresses"] = ["192.168.0.77"]
    data["robot"]["default_ip"] = "192.168.0.77"
    data["robot"]["sftp"]["username"] = "root"
    data["robot"]["sftp"]["password"] = "easybot"
    data["robot"]["sftp"]["remote_dir"] = "/programs"
    data["robot"]["dashboard"]["loader_urp_path"] = "/programs/custom_loader.urp"

    cm.apply_dict(data)

    assert cm.get("robot.targets.active_id") == "real"
    assert cm.get("robot.targets.items.real.default_ip") == "192.168.0.77"
    assert cm.get("robot.targets.items.real.sftp.remote_dir") == "/programs"
    assert cm.get("robot.targets.items.real.dashboard.loader_urp_path") == "/programs/custom_loader.urp"
    assert cm.get("robot.default_ip") == "192.168.0.77"


def test_preferences_dialog_switch_robot_target_preserves_each_profile():
    app = QApplication.instance() or QApplication([])
    original = config_manager.snapshot()

    try:
        dlg = PreferencesDialog()

        dlg._set("robot.sftp.password", "virtual-pass")
        dlg._switch_robot_target("real")
        assert dlg._get("robot.targets.active_id") == "real"
        assert dlg._get("robot.sftp.username") == "root"
        assert dlg._get("robot.sftp.remote_dir") == "/programs"
        assert dlg._get("robot.dashboard.loader_urp_path") == "/programs/loader.urp"

        dlg._set("robot.sftp.password", "real-pass")
        dlg._switch_robot_target("virtual")

        assert dlg._get("robot.targets.active_id") == "virtual"
        assert dlg._get("robot.sftp.username") == "ur"
        assert dlg._get("robot.sftp.password") == "virtual-pass"

        dlg._switch_robot_target("real")
        assert dlg._get("robot.sftp.password") == "real-pass"
    finally:
        config_manager.apply_dict(original)
