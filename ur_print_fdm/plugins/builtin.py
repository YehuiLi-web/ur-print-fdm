from __future__ import annotations

from importlib import import_module

from ur_print_fdm.plugins.registry import PluginRegistry


_BUILTIN_PLUGIN_SPECS: tuple[tuple[str, str], ...] = (
    ("register_estimator", "ur_print_fdm.estimators.simple_gcode:SimpleGCodeTimeEstimator"),
    ("register_sample_provider", "ur_print_fdm.samples.legacy_provider:LegacyCoreSampleProvider"),
    ("register_robot_backend", "ur_print_fdm.robots.ur_backend:URDriverBackendFactory"),
    ("register_gcode_converter", "ur_print_fdm.processes.gcode_planar_plugin:PlanarGCodeConverter"),
)


def _load_object(spec: str):
    module_name, object_name = spec.split(":", 1)
    module = import_module(module_name)
    return getattr(module, object_name)


def register_builtin_plugins(plugin_registry: PluginRegistry) -> None:
    for registrar_name, plugin_spec in _BUILTIN_PLUGIN_SPECS:
        registrar = getattr(plugin_registry, registrar_name)
        plugin_cls = _load_object(plugin_spec)
        registrar(plugin_cls())
