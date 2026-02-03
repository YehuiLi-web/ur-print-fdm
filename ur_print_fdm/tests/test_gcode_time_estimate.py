import textwrap

from ur_print_fdm.core import toolbox as ur_toolbox
from ur_print_fdm.estimators.simple_gcode import SimpleGCodeTimeEstimator
from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
from ur_print_fdm.plugins.registry import registry


def test_gcode_time_estimate(tmp_path):
    gcode = textwrap.dedent(
        """
        G1 X0 Y0 Z0 F600
        G1 X10 Y0 E1 F600
        G1 X10 Y10 E2 F600
        """
    ).strip()
    gpath = tmp_path / "a.gcode"
    gpath.write_text(gcode, encoding="utf-8")

    ops = ur_toolbox.parse_gcode(str(gpath))
    traj = SimpleGCodeTimeEstimator.trajectory_from_gcode_ops(ops)

    bootstrap_plugins()
    estimator = registry.estimators["simple_gcode_v1"]
    result = estimator.estimate(traj)

    # Two 10mm printed segments at 10mm/s => ~2s
    assert 1.5 <= result.total_time_s <= 2.5
