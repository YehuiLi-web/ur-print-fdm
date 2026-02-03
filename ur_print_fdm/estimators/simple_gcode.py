from __future__ import annotations

import math

from ur_print_fdm.domain.trajectory import SegmentKind, Trajectory, TrajectorySegment
from ur_print_fdm.plugins.contracts import EstimateResult


def _mm_min_to_m_s(feed_mm_min: float) -> float:
    return max(0.0, float(feed_mm_min)) / 60.0 / 1000.0


class SimpleGCodeTimeEstimator:
    id = "simple_gcode_v1"
    title = "Simple G-code time estimator (constant speed)"

    def estimate(self, trajectory: Trajectory) -> EstimateResult:
        travel = 0.0
        printing = 0.0
        dwell = 0.0

        for seg in trajectory.segments:
            if seg.kind == SegmentKind.DWELL:
                dwell += max(0.0, seg.dwell_s)
                continue
            if seg.speed_m_s <= 0:
                continue
            t = max(0.0, seg.length_m) / seg.speed_m_s
            if seg.kind == SegmentKind.PRINT:
                printing += t
            else:
                travel += t

        total = travel + printing + dwell
        return EstimateResult(
            total_time_s=total,
            breakdown={"travel_s": travel, "print_s": printing, "dwell_s": dwell},
        )

    @staticmethod
    def trajectory_from_gcode_ops(ops: list[dict]) -> Trajectory:
        segments: list[TrajectorySegment] = []
        prev_x = 0.0
        prev_y = 0.0
        prev_z = 0.0
        for op in ops:
            if op.get("type") != "move":
                continue
            x = float(op["x"])
            y = float(op["y"])
            z = float(op["z"])

            start_x = float(op.get("x0", prev_x))
            start_y = float(op.get("y0", prev_y))
            start_z = float(op.get("z0", prev_z))

            length_m = math.sqrt((x - start_x) ** 2 + (y - start_y) ** 2 + (z - start_z) ** 2) / 1000.0
            prev_x, prev_y, prev_z = x, y, z

            feed = op.get("f", 0.0) or 0.0
            speed_m_s = _mm_min_to_m_s(feed) if feed else 0.05

            kind = SegmentKind.PRINT if op.get("is_print") else SegmentKind.TRAVEL
            segments.append(TrajectorySegment(kind=kind, length_m=length_m, speed_m_s=speed_m_s))

        return Trajectory(segments=tuple(segments))
