from __future__ import annotations

from ur_print_fdm.config import config_manager
from ur_print_fdm.core.driver import URDriver


def test_manual_stop_uses_native_rtde_only():
    driver = URDriver()
    driver.rc = object()
    driver.connected = True
    driver.read_only = False
    calls: list[tuple] = []

    driver.speed_stop = lambda a=10.0: calls.append(("speed_stop", a)) or True
    driver.stop_l = lambda a=10.0, asynchronous=False: calls.append(("stop_l", a, asynchronous)) or True
    driver.stop_j = lambda a=2.0, asynchronous=False: calls.append(("stop_j", a, asynchronous)) or True

    assert driver.manual_stop() is True
    assert calls == [
        ("speed_stop", 10.0),
        ("stop_l", 10.0, False),
        ("stop_j", 2.0, False),
    ]


def test_stop_extrusion_uses_rtde_io_without_staling_when_modbus_disabled(monkeypatch):
    driver = URDriver()
    events: dict[str, object] = {"stale_reasons": []}

    class _IO:
        def setStandardDigitalOut(self, pin, value):
            events["native_io"] = (pin, value)
            return True

    values = {
        "printing.modbus_extruder": "",
        "printing.extruder_io_pin": 3,
    }

    monkeypatch.setattr(
        config_manager,
        "get",
        lambda key_path, default=None: values.get(key_path, default),
    )

    driver.rio = _IO()
    driver._send_secondary_script = lambda _script, timeout_s=0.5: events.__setitem__("script_sent", True) or True
    driver.mark_control_stale = lambda reason="": events["stale_reasons"].append(reason)

    assert driver.stop_extrusion() is True
    assert events["native_io"] == (3, False)
    assert "script_sent" not in events
    assert events["stale_reasons"] == []


def test_stop_extrusion_falls_back_to_secondary_script_for_modbus(monkeypatch):
    driver = URDriver()
    events: dict[str, object] = {"stale_reasons": []}

    class _IO:
        def setStandardDigitalOut(self, pin, value):
            events["native_io"] = (pin, value)
            return True

    values = {
        "printing.modbus_extruder": "MODBUS_1",
        "printing.extruder_io_pin": 5,
    }

    monkeypatch.setattr(
        config_manager,
        "get",
        lambda key_path, default=None: values.get(key_path, default),
    )

    def _send_secondary(script: str, timeout_s: float = 0.5):
        events["secondary_script"] = script
        events["timeout_s"] = timeout_s
        return True

    driver.rio = _IO()
    driver._send_secondary_script = _send_secondary
    driver.mark_control_stale = lambda reason="": events["stale_reasons"].append(reason)

    assert driver.stop_extrusion() is True
    assert events["native_io"] == (5, False)
    assert 'modbus_set_output_register("MODBUS_1", 0)' in str(events["secondary_script"])
    assert "set_standard_digital_out(5, False)" in str(events["secondary_script"])
    assert events["stale_reasons"] == ["停止挤出时 secondary script 接管了控制脚本"]
