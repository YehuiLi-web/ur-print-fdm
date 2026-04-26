import sys
import types
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from ur_print_fdm.ui.workers import threads


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


class _FakeDashboard:
    instances = []
    next_response = "Loading program: /programs/loader.urp"

    def __init__(self):
        self.ip = None
        self.load_calls = []
        self.closed = False
        type(self).instances.append(self)

    def set_ip(self, ip):
        self.ip = ip

    def load_program(self, program_name):
        self.load_calls.append(program_name)
        return type(self).next_response

    def close(self):
        self.closed = True


def test_sftp_upload_thread_can_upload_and_load(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    _install_fake_paramiko(monkeypatch)
    _FakeDashboard.instances.clear()
    _FakeDashboard.next_response = "Loading program: /programs/loader.urp"
    monkeypatch.setattr(threads, "SimpleDashboardDriver", _FakeDashboard)

    local_file = tmp_path / "demo.script"
    local_file.write_text("def demo():\n  pass\n", encoding="utf-8")

    worker = threads.SFTPUploadThread(
        "192.168.1.10",
        str(local_file),
        remote_dir="/programs",
        remote_filename="demo.script",
        also_upload_loader=True,
        load_program_after_upload=True,
        remote_loader_name="remote_loader.script",
        loader_urp_path="/programs/loader.urp",
        username="root",
        password="easybot",
        port=22,
    )

    results = []
    worker.result_signal.connect(lambda success, message: results.append((success, message)))
    worker.run()
    app.processEvents()

    assert results and results[-1][0] is True
    assert "上传并加载成功" in results[-1][1]
    assert "- /programs/demo.script" in results[-1][1]
    assert "- /programs/remote_loader.script" in results[-1][1]
    assert "- Dashboard 已加载：/programs/loader.urp" in results[-1][1]

    assert len(_FakeSFTPClient.instances) == 1
    put_calls = _FakeSFTPClient.instances[0].put_calls
    assert [remote_path for _local_path, remote_path in put_calls] == [
        "/programs/demo.script",
        "/programs/remote_loader.script",
    ]
    uploaded = dict(_FakeSFTPClient.instances[0].uploaded_payloads)
    assert uploaded["/programs/demo.script"] == b"def demo():\n  pass\n"
    assert uploaded["/programs/remote_loader.script"] == b"def demo():\n  pass\n"
    assert len(_FakeDashboard.instances) == 1
    assert _FakeDashboard.instances[0].ip == "192.168.1.10"
    assert _FakeDashboard.instances[0].load_calls == ["/programs/loader.urp"]


def test_sftp_upload_thread_reports_dashboard_load_failure(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    _install_fake_paramiko(monkeypatch)
    _FakeDashboard.instances.clear()
    _FakeDashboard.next_response = "File not found: /programs/loader.urp"
    monkeypatch.setattr(threads, "SimpleDashboardDriver", _FakeDashboard)

    local_file = tmp_path / "demo.script"
    local_file.write_text("def demo():\n  pass\n", encoding="utf-8")

    worker = threads.SFTPUploadThread(
        "192.168.1.10",
        str(local_file),
        remote_dir="/programs",
        remote_filename="demo.script",
        also_upload_loader=True,
        load_program_after_upload=True,
        remote_loader_name="remote_loader.script",
        loader_urp_path="/programs/loader.urp",
    )

    results = []
    worker.result_signal.connect(lambda success, message: results.append((success, message)))
    worker.run()
    app.processEvents()

    assert results and results[-1][0] is False
    assert "文件上传成功，但加载失败" in results[-1][1]
    assert "Dashboard 加载失败：/programs/loader.urp" in results[-1][1]


def test_sftp_upload_thread_normalizes_crlf_before_upload(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    _install_fake_paramiko(monkeypatch)

    local_file = tmp_path / "demo.script"
    local_file.write_bytes(b'def demo():\r\n  textmsg("hi")\r\nend\r\n')

    worker = threads.SFTPUploadThread(
        "192.168.1.10",
        str(local_file),
        remote_dir="/programs",
        remote_filename="demo.script",
    )

    results = []
    worker.result_signal.connect(lambda success, message: results.append((success, message)))
    worker.run()
    app.processEvents()

    assert results and results[-1][0] is True
    uploaded = dict(_FakeSFTPClient.instances[0].uploaded_payloads)
    assert uploaded["/programs/demo.script"] == b'def demo():\n  textmsg("hi")\nend\n'
    assert b"\r" not in uploaded["/programs/demo.script"]
