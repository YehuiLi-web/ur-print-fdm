from PyQt6.QtWidgets import QApplication


def test_log_display_scrollbar_is_hidden_until_hover():
    app = QApplication.instance() or QApplication([])

    from ur_print_fdm.ui import theme
    from ur_print_fdm.ui.widgets.log_display import LogTextEdit

    console = LogTextEdit()
    try:
        scrollbar = console.verticalScrollBar()
        base_bg = theme.current_tokens()["bg_secondary"]

        assert console._scrollbar_visible is False
        assert f"background: {base_bg}" in scrollbar.styleSheet()
        assert "width: 6px" in scrollbar.styleSheet()

        console._set_scrollbar_visibility(True)

        assert console._scrollbar_visible is True
        assert theme.current_tokens()["scroll_handle"] in scrollbar.styleSheet()

        console._set_scrollbar_visibility(False)

        assert console._scrollbar_visible is False
        assert f"background: {base_bg}" in scrollbar.styleSheet()
    finally:
        console.close()
        console.deleteLater()
        app.processEvents()
