from ur_print_fdm.core.script_sanitizer import sanitize_script_content


def test_sanitize_script_content_normalizes_newlines_and_strips_nul():
    raw = "def a():\r\n  textmsg(\"hi\")\x00\r\nend\r\n"
    out = sanitize_script_content(raw)
    assert "\r" not in out
    assert "\x00" not in out
    assert "def a():\n" in out
