from ur_print_fdm.estimators.sample_trajectory import trajectory_from_sample_params
from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
from ur_print_fdm.plugins.registry import registry


def test_flat_plate_estimate_is_reasonable():
    bootstrap_plugins()
    estimator = registry.estimators["simple_gcode_v1"]

    traj = trajectory_from_sample_params(
        "flat_plate",
        {"width": 20.0, "length": 100.0, "layers": 5, "speed": 16.0},
    )
    assert traj is not None
    result = estimator.estimate(traj)
    assert 620 <= result.total_time_s <= 650


def test_circular_ring_estimate_is_reasonable():
    bootstrap_plugins()
    estimator = registry.estimators["simple_gcode_v1"]

    traj = trajectory_from_sample_params(
        "circular_ring",
        {"diameter": 50.0, "layers": 10, "speed": 10.0},
    )
    assert traj is not None
    result = estimator.estimate(traj)
    assert 140 <= result.total_time_s <= 180

