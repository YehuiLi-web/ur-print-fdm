from ur_print_fdm.release_info import (
    DEFAULT_RELEASE_NOTES_BODY,
    load_latest_release_notes_body,
    parse_release_notes_body,
)


def test_parse_release_notes_body_prefers_marker_section():
    text = "UR Print FDM 0.2.0\n\n构建时间: 2026-03-18 10:00:00 CST\n\n版本说明:\n- 修复安装路径\n- 新增模板\n"

    assert parse_release_notes_body(text) == "- 修复安装路径\n- 新增模板"


def test_parse_release_notes_body_returns_placeholder_for_blank_text():
    assert parse_release_notes_body(" \n ") == DEFAULT_RELEASE_NOTES_BODY


def test_load_latest_release_notes_body_returns_placeholder_when_missing(monkeypatch):
    monkeypatch.setattr("ur_print_fdm.release_info._candidate_release_notes_paths", lambda: [])

    assert load_latest_release_notes_body() == DEFAULT_RELEASE_NOTES_BODY
