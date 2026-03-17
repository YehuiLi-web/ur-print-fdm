from ur_print_fdm.ui.workers.direct_mode_processor import DirectModeProcessor


def test_direct_stop_script_does_not_cut_extrusion():
    processor = DirectModeProcessor("192.168.1.100")

    script = processor._build_stop_script()

    assert "stopj(2.0)" in script
    assert "modbus_set_output_register" not in script
    assert "set_standard_digital_out" not in script


def test_detect_missing_entry_call_returns_function_name():
    processor = DirectModeProcessor("192.168.1.100")

    missing = processor._detect_missing_entry_call(
        "def foo():\n"
        "  textmsg(\"demo\")\n"
        "end\n"
    )
    present = processor._detect_missing_entry_call(
        "def foo():\n"
        "  textmsg(\"demo\")\n"
        "end\n"
        "foo()\n"
    )

    assert missing == "foo"
    assert present is None


def test_build_preflight_error_blocks_missing_entry_and_safety_fault():
    processor = DirectModeProcessor("192.168.1.100")

    missing_entry_error = processor._build_preflight_error(
        "def foo():\n  textmsg(\"demo\")\nend\n",
        {},
        socket_program_compatible=False,
    )
    safety_error = processor._build_preflight_error(
        "textmsg(\"demo\")\n",
        {"safety_mode": "PROTECTIVE_STOP"},
        socket_program_compatible=False,
    )

    assert "foo" in str(missing_entry_error)
    assert "PROTECTIVE_STOP" in str(safety_error)

    compatible_ok = processor._build_preflight_error(
        "def foo():\n  textmsg(\"demo\")\nend\n",
        {},
        socket_program_compatible=True,
    )
    assert compatible_ok is None


def test_socket_program_compatibility_and_wrapping():
    processor = DirectModeProcessor("192.168.1.100")

    assert processor._is_socket_program_compatible("def foo():\n  textmsg(\"demo\")\nend\n") is True
    assert processor._is_socket_program_compatible(
        "global feature1 = p[0,0,0,0,0,0]\n"
        "def foo():\n"
        "  textmsg(\"demo\")\n"
        "end\n"
        "foo()\n"
    ) is False

    wrapped = processor._wrap_as_socket_program(
        "global feature1 = p[0,0,0,0,0,0]\n"
        "def foo():\n"
        "  textmsg(\"demo\")\n"
        "end\n"
        "foo()\n"
    )

    assert wrapped.startswith("def direct_socket_program():\n")
    assert wrapped.rstrip().endswith("end")
    assert "  global feature1" in wrapped


def test_build_unconfirmed_run_message_surfaces_diagnostic_clues():
    processor = DirectModeProcessor("192.168.1.100")

    message = processor._build_unconfirmed_run_message(
        "textmsg(\"demo\")\n",
        {
            "runtime_state": processor.RUNTIME_STOPPED,
            "program_state": "STOPPED",
            "running": "false",
        },
        {
            "robot_mode": "RUNNING",
            "safety_mode": "NORMAL",
        },
        monitor_ready=True,
        socket_program_compatible=False,
    )

    assert "未确认机器人开始执行" in message
    assert "STOPPED" in message
    assert "running=false" in message
    assert "遥控模式" in message
