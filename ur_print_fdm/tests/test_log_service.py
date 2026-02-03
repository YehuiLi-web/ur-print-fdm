from ur_print_fdm.ui.services.log_service import LogService


class _StubScrollBar:
    def __init__(self):
        self.set_calls = 0
        self.last_value = None

    def maximum(self):
        return 123

    def setValue(self, v):
        self.set_calls += 1
        self.last_value = v


class _StubDocument:
    def __init__(self):
        self.max_block_count = None

    def setMaximumBlockCount(self, n: int) -> None:
        self.max_block_count = int(n)


class _StubConsole:
    def __init__(self):
        self._doc = _StubDocument()
        self._sb = _StubScrollBar()
        self.appended: list[str] = []

    def document(self):
        return self._doc

    def verticalScrollBar(self):
        return self._sb

    def append(self, html: str) -> None:
        self.appended.append(html)


def test_log_service_can_update_max_lines_and_auto_scroll():
    console = _StubConsole()
    svc = LogService(console, max_lines=10, auto_scroll=True)
    assert console._doc.max_block_count == 10

    svc.log("hi", "INFO")
    assert console._sb.set_calls == 1

    svc.set_auto_scroll(False)
    svc.log("hi2", "INFO")
    assert console._sb.set_calls == 1

    svc.set_max_lines(1234)
    assert console._doc.max_block_count == 1234

    svc.set_max_lines(None)
    assert console._doc.max_block_count == 0


def test_log_service_uses_current_theme_text_color_for_info():
    from ur_print_fdm.ui import theme

    console = _StubConsole()
    svc = LogService(console, max_lines=10, auto_scroll=False)

    theme.apply_app_theme(use_dark=False)  # light theme
    svc.log("hello", "INFO")
    assert console.appended
    html = console.appended[-1]
    assert theme.current_tokens()["text"] in html
    assert "#FFFFFF" not in html
