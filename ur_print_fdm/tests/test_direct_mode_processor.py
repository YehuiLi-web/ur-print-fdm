from ur_print_fdm.ui.workers.direct_mode_processor import DirectModeProcessor


def test_direct_stop_script_does_not_cut_extrusion():
    processor = DirectModeProcessor("192.168.1.100")

    script = processor._build_stop_script()

    assert "stopj(2.0)" in script
    assert "modbus_set_output_register" not in script
    assert "set_standard_digital_out" not in script
