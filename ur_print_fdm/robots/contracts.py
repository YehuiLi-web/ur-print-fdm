from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RobotStatus:
    tcp: list[float]
    joints: list[float]
    tcp_offset: list[float]
    speed: float
    connected: bool
    read_only: bool


class RobotBackend(Protocol):
    id: str
    title: str

    def connect(self, ip: str) -> bool: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def is_read_only(self) -> bool: ...
    def get_status(self) -> RobotStatus: ...
    def send_script(self, script: str) -> bool: ...
    def stop(self) -> bool | None: ...

