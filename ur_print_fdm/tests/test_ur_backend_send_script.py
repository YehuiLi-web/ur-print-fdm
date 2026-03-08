from __future__ import annotations

from ur_print_fdm.robots.ur_backend import URDriverBackend


class _FakeDriver:
    def __init__(self, result):
        self._result = result

    def send_script(self, _script: str):
        return self._result


def test_send_script_preserves_failure_tuple():
    backend = URDriverBackend()
    backend._driver = _FakeDriver((False, None))

    success, warning = backend.send_script("demo")

    assert success is False
    assert warning is None


def test_send_script_preserves_warning_tuple():
    backend = URDriverBackend()
    backend._driver = _FakeDriver((True, "possible missing call"))

    success, warning = backend.send_script("demo")

    assert success is True
    assert warning == "possible missing call"


def test_send_script_supports_legacy_bool_return():
    backend = URDriverBackend()
    backend._driver = _FakeDriver(True)

    success, warning = backend.send_script("demo")

    assert success is True
    assert warning is None
