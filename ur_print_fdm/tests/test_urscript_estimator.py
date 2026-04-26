from __future__ import annotations

from pathlib import Path

import pytest

from ur_print_fdm.estimators.urscript import estimate_urscript


def _load_repo_script(name: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "URscript" / name).read_text(encoding="utf-8", errors="replace")


def test_estimate_no_feature1_uses_current_tcp_pose() -> None:
    script = "\n".join(
        [
            "def a():",
            "  movel(p[0.1,0,0,0,0,0], a=1.0, v=0.1)",
            "end",
            "a()",
        ]
    )
    res = estimate_urscript(script, current_tcp_pose=[0, 0, 0, 0, 0, 0])
    assert res.total_time_s == pytest.approx(1.1, abs=1e-9)
    assert res.cf_filament_mm == pytest.approx(100.0, abs=1e-9)


def test_estimate_movej_counts_time_not_filament() -> None:
    script = "\n".join(
        [
            "def a():",
            "  movej(p[0.1,0,0,0,0,0], a=1.0, v=0.1)",
            "  movel(p[0.2,0,0,0,0,0], a=1.0, v=0.1)",
            "end",
            "a()",
        ]
    )
    res = estimate_urscript(script, current_tcp_pose=[0, 0, 0, 0, 0, 0])
    assert res.total_time_s > 0
    assert res.movej_time_s > 0
    assert res.cf_filament_mm == pytest.approx(100.0, abs=1e-9)


def test_estimate_repo_pingban_matches_reference() -> None:
    script = _load_repo_script("pingban.script")
    res = estimate_urscript(script)
    assert res.total_time_s == pytest.approx(10.685, abs=0.5)
    assert res.cf_filament_mm == pytest.approx(183.36, abs=1.0)
    assert res.extruder_filament_mm == pytest.approx(0.0, abs=1e-9)
    assert res.movej_time_s > 0.0


def test_estimate_repo_fiber_matches_reference() -> None:
    script = _load_repo_script("fiber.script")
    res = estimate_urscript(script)
    assert res.total_time_s == pytest.approx(18.765, abs=0.5)
    assert res.cf_filament_mm == pytest.approx(9.38, abs=0.5)
    assert res.extruder_filament_mm == pytest.approx(0.0, abs=1e-9)


def test_estimate_repo_vt350_matches_reference() -> None:
    script = _load_repo_script("VT350_v2_planar_part01_flag.script")
    res = estimate_urscript(script)
    assert res.total_time_s == pytest.approx(113.004, abs=0.5)
    assert res.cf_filament_mm == pytest.approx(830.32, abs=2.0)
    assert res.extruder_filament_mm == pytest.approx(106.12, abs=2.0)


def test_estimate_repo_cylinder_auto_calc_matches_reference() -> None:
    script = _load_repo_script("cylinder_auto_calc.script")
    res = estimate_urscript(script)
    assert res.total_time_s == pytest.approx(19414.009, abs=2.0)
    assert res.cf_filament_mm == pytest.approx(72771.44, abs=50.0)
    assert res.extruder_filament_mm == pytest.approx(21743.13, abs=50.0)
