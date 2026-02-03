from ur_print_fdm.estimators.simple_gcode import SimpleGCodeTimeEstimator
from ur_print_fdm.processes.gcode_planar_plugin import PlanarGCodeConverter
from ur_print_fdm.plugins.registry import registry
from ur_print_fdm.robots.ur_backend import URDriverBackendFactory
from ur_print_fdm.samples.legacy_provider import LegacyCoreSampleProvider

_BOOTSTRAPPED = False


def bootstrap_plugins() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    registry.register_estimator(SimpleGCodeTimeEstimator())
    registry.register_sample_provider(LegacyCoreSampleProvider())
    registry.register_robot_backend(URDriverBackendFactory())
    registry.register_gcode_converter(PlanarGCodeConverter())
    registry.load_entry_points()
    _BOOTSTRAPPED = True
