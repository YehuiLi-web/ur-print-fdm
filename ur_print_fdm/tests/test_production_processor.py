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
