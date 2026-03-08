from __future__ import annotations

from ur_print_fdm.core.driver import URDriver
from ur_print_fdm.robots.contracts import RobotBackend, RobotStatus, ScriptSendResult


class URDriverBackend:
    id = "ur_rtde_cb3"
    title = "Universal Robots (ur_rtde/RTDE + Dashboard)"

    def __init__(self) -> None:
        self._driver = URDriver()

    @property
    def driver(self) -> URDriver:
        return self._driver

    def connect(self, ip: str) -> bool:
        return bool(self._driver.connect(ip))

    def disconnect(self) -> None:
        self._driver.disconnect()

    def is_connected(self) -> bool:
        return bool(self._driver.is_connected())

    def is_read_only(self) -> bool:
        return bool(self._driver.is_read_only())

    def get_status(self) -> RobotStatus:
        tcp, joints, offset, speed = self._driver.get_status()
        return RobotStatus(
            tcp=list(tcp or []),
            joints=list(joints or []),
            tcp_offset=list(offset or []),
            speed=float(speed or 0.0),
            connected=self.is_connected(),
            read_only=self.is_read_only(),
        )

    def send_script(self, script: str) -> ScriptSendResult:
        result = self._driver.send_script(script)
        if isinstance(result, tuple):
            success, warning = result
            return bool(success), (str(warning) if warning is not None else None)
        return bool(result), None

    def stop(self) -> bool | None:
        return self._driver.stop()


class URDriverBackendFactory:
    id = "ur_rtde_cb3"
    title = "Universal Robots (URDriver)"

    def create(self) -> RobotBackend:
        return URDriverBackend()
