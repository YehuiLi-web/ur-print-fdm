from ur_print_fdm.ui.widgets.editor.urscript_metadata import (
    find_call_context,
    format_symbol_help,
    get_urscript_completions,
    get_urscript_symbol,
)


def test_urscript_completion_catalog_covers_extended_language_and_runtime_symbols():
    completions = set(get_urscript_completions())

    for item in (
        "sec",
        "pause",
        "sync",
        "rpc_factory",
        "make_list",
        "get_actual_tool_flange_pose",
        "modbus_set_output_register",
    ):
        assert item in completions

    movej = get_urscript_symbol("movej")
    assert movej is not None
    assert movej.docs_section == "运动指令"


def test_find_call_context_ignores_commas_inside_pose_and_list_literals():
    text = "movel(p[0.30, 0.10, 0.25, 0, 3.14159, 0], a = 0.5, v = 0.05)"
    offset = text.index("a = 0.5") + len("a = 0.5")

    context = find_call_context(text, offset)

    assert context is not None
    assert context.name == "movel"
    assert context.arg_index == 1


def test_find_call_context_tracks_nested_calls():
    text = "cfg = blend_move(a = pose_trans(feature, local_target), v = 0.2)"
    nested_offset = text.index("local_target") + len("local_target")
    outer_offset = text.index("v = 0.2") + len("v = 0.2")

    nested_context = find_call_context(text, nested_offset)
    outer_context = find_call_context(text, outer_offset)

    assert nested_context is not None
    assert nested_context.name == "pose_trans"
    assert nested_context.arg_index == 1

    assert outer_context is not None
    assert outer_context.name == "blend_move"
    assert outer_context.arg_index == 1


def test_find_call_context_ignores_function_definition_parentheses():
    text = "def blend_move(v = 0.25, a = 1.2):\n  return [v, a]\nend\n"
    offset = text.index("a = 1.2") + len("a = 1.2")

    assert find_call_context(text, offset) is None


def test_format_symbol_help_contains_summary_parameters_and_example():
    help_text = format_symbol_help("set_tcp")

    assert "用途: 设置 TCP 偏置" in help_text
    assert "参数:" in help_text
    assert "tcp_name = \"nozzle\"" in help_text
    assert "写法: set_tcp(p[0, 0, 0.12, 0, 0, 0])" in help_text


def test_code_editor_builds_call_tip_for_current_cursor():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui.widgets.editor.core import CodeEditor

    editor = CodeEditor()
    try:
        if not getattr(editor, "_is_qsci", False):
            return

        editor.setText("movej([0, 0, 0, 0, 0, 0], a = 1.0, v = 0.5)")
        anchor = "a = 1.0"
        offset = editor.text().index(anchor) + len(anchor)
        prefix = editor.text()[:offset]
        line = prefix.count("\n")
        column = len(prefix.rsplit("\n", 1)[-1])
        editor.setCursorPosition(line, column)

        tip_text = editor._build_call_tip_for_current_cursor()

        assert "movej(q, a = 1.4, v = 1.05, t = 0, r = 0)" in tip_text
        assert "当前参数 2/5: a = 1.4 - 关节加速度。" in tip_text
    finally:
        editor.deleteLater()
        app.processEvents()
