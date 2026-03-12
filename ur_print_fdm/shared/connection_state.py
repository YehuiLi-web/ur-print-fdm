from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChannelState(str, Enum):
    DOWN = "down"
    CONNECTING = "connecting"
    UP = "up"
    STALE = "stale"
    UNKNOWN = "unknown"


class SessionPhase(str, Enum):
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ONLINE_FULL = "online_full"
    ONLINE_DASHBOARD_ONLY = "online_dashboard_only"
    ONLINE_CONTROL_ONLY = "online_control_only"
    ONLINE_MONITOR_ONLY = "online_monitor_only"
    FAULTED = "faulted"
    DISCONNECTING = "disconnecting"
    REPAIRING = "repairing"


@dataclass(frozen=True)
class ConnectionSnapshot:
    phase: SessionPhase = SessionPhase.OFFLINE
    ip: str = ""
    receive: ChannelState = ChannelState.DOWN
    control: ChannelState = ChannelState.DOWN
    dashboard: ChannelState = ChannelState.DOWN
    last_error: str = ""
    control_reason: str = ""
    generation: int = 0

    @property
    def can_monitor(self) -> bool:
        return self.receive == ChannelState.UP

    @property
    def can_direct_control(self) -> bool:
        return self.receive == ChannelState.UP and self.control == ChannelState.UP

    @property
    def can_direct_run(self) -> bool:
        # Direct mode uses the 30002 port and only relies on the monitoring session
        # being established from the user's perspective.
        return self.receive == ChannelState.UP

    @property
    def can_production_run(self) -> bool:
        return self.receive == ChannelState.UP and self.dashboard == ChannelState.UP

    @property
    def can_pause_resume(self) -> bool:
        return self.dashboard == ChannelState.UP

    @property
    def can_stop(self) -> bool:
        return any(
            state == ChannelState.UP
            for state in (self.receive, self.control, self.dashboard)
        ) or (self.phase == SessionPhase.FAULTED and bool(self.ip))

    @property
    def is_online(self) -> bool:
        return self.phase not in {
            SessionPhase.OFFLINE,
            SessionPhase.CONNECTING,
            SessionPhase.DISCONNECTING,
            SessionPhase.REPAIRING,
            SessionPhase.FAULTED,
        }

    @property
    def is_busy(self) -> bool:
        return self.phase in {
            SessionPhase.CONNECTING,
            SessionPhase.DISCONNECTING,
            SessionPhase.REPAIRING,
        }

    @property
    def is_degraded(self) -> bool:
        return self.phase in {
            SessionPhase.ONLINE_DASHBOARD_ONLY,
            SessionPhase.ONLINE_CONTROL_ONLY,
            SessionPhase.ONLINE_MONITOR_ONLY,
            SessionPhase.FAULTED,
        }
