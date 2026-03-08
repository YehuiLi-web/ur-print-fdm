from __future__ import annotations

from ur_print_fdm.plugins.builtin import _load_object, register_builtin_plugins
from ur_print_fdm.plugins.registry import PluginRegistry


def test_load_object_resolves_symbol_from_spec():
    cls = _load_object("ur_print_fdm.estimators.simple_gcode:SimpleGCodeTimeEstimator")
    assert cls.__name__ == "SimpleGCodeTimeEstimator"


def test_register_builtin_plugins_registers_expected_ids():
    registry = PluginRegistry()

    register_builtin_plugins(registry)

    assert "simple_gcode_v1" in registry.estimators
    assert "legacy_core_samples" in registry.sample_providers
    assert "ur_rtde_cb3" in registry.robot_backends
    assert "gcode_planar_v1" in registry.gcode_converters
