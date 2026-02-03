from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SegmentKind(str, Enum):
    TRAVEL = "travel"
    PRINT = "print"
    DWELL = "dwell"


@dataclass(frozen=True)
class TrajectorySegment:
    kind: SegmentKind
    length_m: float = 0.0
    speed_m_s: float = 0.0
    dwell_s: float = 0.0


@dataclass(frozen=True)
class Trajectory:
    segments: tuple[TrajectorySegment, ...]

    def total_length_m(self) -> float:
        return sum(s.length_m for s in self.segments)

