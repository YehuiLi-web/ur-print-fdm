from ur_print_fdm.plugins.bootstrap import bootstrap_plugins
from ur_print_fdm.plugins.registry import registry


def test_planar_gcode_converter_is_registered():
    bootstrap_plugins()
    assert "gcode_planar_v1" in registry.gcode_converters

