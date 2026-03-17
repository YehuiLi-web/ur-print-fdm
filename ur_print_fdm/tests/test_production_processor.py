import sys
import types
from pathlib import Path

from ur_print_fdm.ui.workers.production_processor import ProductionProcessor


class _Dashboard:
    def __init__(self):
        self.stop_calls = 0
        self.pause_calls = 0

    def stop(self):
        self.stop_calls += 1

    def pause(self):
        self.pause_calls += 1
        return "Paused"


class _FakeTransport:
    instances = []

    def __init__(self, address):
        self.address = address
        self.connected_with = None
        self.closed = False
        type(self).instances.append(self)

    def connect(self, username, password):
        self.connected_with = (username, password)

    def close(self):
        self.closed = True


class _FakeSFTPClient:
    instances = []

    def __init__(self, transport):
        self.transport = transport
        self.put_calls = []
        self.uploaded_payloads = []
        self.closed = False
        type(self).instances.append(self)

    @classmethod
    def from_transport(cls, transport):
        return cls(transport)

    def put(self, local_path, remote_path, callback=None):
        self.put_calls.append((local_path, remote_path))
        self.uploaded_payloads.append((remote_path, Path(local_path).read_bytes()))
        if callback is not None:
            callback(5, 10)
            callback(10, 10)

    def close(self):
        self.closed = True


def _install_fake_paramiko(monkeypatch):
    fake_paramiko = types.SimpleNamespace(
        Transport=_FakeTransport,
        SFTPClient=types.SimpleNamespace(from_transport=_FakeSFTPClient.from_transport),
    )
    monkeypatch.setitem(sys.modules, "paramiko", fake_paramiko)
    _FakeTransport.instances.clear()
    _FakeSFTPClient.instances.clear()


def test_normal_stop_request_does_not_cut_extrusion():
    processor = ProductionProcessor("192.168.1.10", 30002, ["demo.script"])
    dashboard = _Dashboard()
    called = {"kill": 0}

    processor._send_stop_extrusion_secondary = lambda: called.__setitem__("kill", called["kill"] + 1)
    processor._stop_event.set()

    processor._handle_abort_request(dashboard)

    assert dashboard.stop_calls == 1
    assert called["kill"] == 0


def test_emergency_abort_still_cuts_extrusion():
    processor = ProductionProcessor("192.168.1.10", 30002, ["demo.script"])
    dashboard = _Dashboard()
    called = {"kill": 0}

    processor._send_stop_extrusion_secondary = lambda: called.__setitem__("kill", called["kill"] + 1)
    processor.emergency_abort = True

    processor._handle_abort_request(dashboard)

    assert dashboard.stop_calls == 1
    assert called["kill"] == 1


def test_pause_request_does_not_cut_extrusion():
    processor = ProductionProcessor("192.168.1.10", 30002, ["demo.script"])
    dashboard = _Dashboard()
    called = {"kill": 0}

    processor._send_stop_extrusion_secondary = lambda: called.__setitem__("kill", called["kill"] + 1)
    processor.request_pause()

    processor._apply_control_requests(dashboard)

    assert dashboard.pause_calls == 1
    assert processor.paused is True
    assert called["kill"] == 0


def test_dual_sftp_upload_normalizes_crlf(monkeypatch, tmp_path):
    _install_fake_paramiko(monkeypatch)

    local_file = tmp_path / "demo.script"
    local_file.write_bytes(b"def demo():\r\n  pass\r\nend\r\n")

    processor = ProductionProcessor("192.168.1.10", 30002, [str(local_file)])
    processor.remote_dir = "/programs"
    processor.remote_loader_name = "remote_loader.script"

    assert processor._sftp_upload_dual(str(local_file)) is True

    uploaded = dict(_FakeSFTPClient.instances[0].uploaded_payloads)
    expected = b"def demo():\n  pass\nend\n"
    assert uploaded["/programs/demo.script"] == expected
    assert uploaded["/programs/remote_loader.script"] == expected
