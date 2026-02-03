from ur_print_fdm.ui import theme


def test_printing_notes_detail_html_uses_theme_tokens():
    theme.apply_app_theme(use_dark=False)

    from ur_print_fdm.ui.widgets import printing_notes_dialog as pnd

    note = {
        "id": "n1",
        "title": "Test Title",
        "category": "Cat",
        "content": "Line1\nLine2",
        "created_at": "2026-02-03",
        "updated_at": "2026-02-03",
    }
    html = pnd.render_note_detail_html(note)
    t = theme.current_tokens()

    assert t["text"] in html
    assert t["accent_link"] in html
    assert t["border_light"] in html
