from __future__ import annotations

import math
from typing import Any

from ur_print_fdm.domain.trajectory import SegmentKind, Trajectory, TrajectorySegment


def trajectory_from_sample_params(sample_id: str, params: dict[str, Any]) -> Trajectory | None:
    """
    Build a coarse Trajectory IR from legacy sample parameters.

    Designed for "good enough" UI estimates until each sample/process provides
    a dedicated estimator.
    """

    if sample_id == "flat_plate":
        width_mm = float(params["width"])
        length_mm = float(params["length"])
        layers = int(params["layers"])
        speed_mm_s = float(params["speed"])

        if layers <= 0 or speed_mm_s <= 0 or length_mm <= 0 or width_mm <= 0:
            return None

        line_width_mm = 1.0
        lines = max(1, int(width_mm / line_width_mm))

        total_print_len_m = (lines * layers * length_mm) / 1000.0
        speed_m_s = speed_mm_s / 1000.0

        # Legacy script sleeps `corner_wait = 0.1` once per line
        dwell_s = lines * layers * 0.1

        return Trajectory(
            segments=(
                TrajectorySegment(kind=SegmentKind.PRINT, length_m=total_print_len_m, speed_m_s=speed_m_s),
                TrajectorySegment(kind=SegmentKind.DWELL, dwell_s=dwell_s),
            )
        )

    if sample_id == "circular_ring":
        diameter_mm = float(params["diameter"])
        layers = int(params["layers"])
        speed_mm_s = float(params["speed"])

        if layers <= 0 or speed_mm_s <= 0 or diameter_mm <= 0:
            return None

        circumference_mm = math.pi * diameter_mm
        total_print_len_m = (circumference_mm * layers) / 1000.0
        speed_m_s = speed_mm_s / 1000.0

        return Trajectory(
            segments=(TrajectorySegment(kind=SegmentKind.PRINT, length_m=total_print_len_m, speed_m_s=speed_m_s),)
        )

    return None

