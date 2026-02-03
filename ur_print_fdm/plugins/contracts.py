from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from ur_print_fdm.domain.trajectory import Trajectory
from ur_print_fdm.samples.api import SampleBase


@dataclass(frozen=True)
class EstimateResult:
    total_time_s: float
    breakdown: dict[str, float]


class TimeEstimator(Protocol):
    id: str
    title: str

    def estimate(self, trajectory: Trajectory) -> EstimateResult: ...


class SampleProvider(Protocol):
    id: str
    title: str

    def get_samples(self) -> Sequence[SampleBase]: ...


class RobotBackendFactory(Protocol):
    id: str
    title: str

    def create(self) -> object: ...


class GCodeConverter(Protocol):
    id: str
    title: str

    def parse(self, gcode_path: str) -> list[dict]: ...
    def convert(self, gcode_path: str, out_path: str, params: dict) -> bool: ...
