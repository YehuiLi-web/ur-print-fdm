from __future__ import annotations

from dataclasses import dataclass, field
import logging
from importlib import metadata
from typing import Any, Iterable

from ur_print_fdm.plugins.contracts import GCodeConverter, RobotBackendFactory, SampleProvider, TimeEstimator


def _iter_entry_points(group: str) -> Iterable[metadata.EntryPoint]:
    eps = metadata.entry_points()
    if hasattr(eps, "select"):
        return eps.select(group=group)
    return eps.get(group, [])


@dataclass
class PluginRegistry:
    estimators: dict[str, TimeEstimator] = field(default_factory=dict)
    sample_providers: dict[str, SampleProvider] = field(default_factory=dict)
    robot_backends: dict[str, RobotBackendFactory] = field(default_factory=dict)
    gcode_converters: dict[str, GCodeConverter] = field(default_factory=dict)

    @staticmethod
    def _safe_register(container: dict[str, Any], plugin: Any, *, kind: str) -> None:
        plugin_id = getattr(plugin, "id", None)
        if not isinstance(plugin_id, str) or not plugin_id:
            raise ValueError(f"Invalid {kind} plugin id: {plugin_id!r}")
        if plugin_id in container:
            logging.warning(
                "Plugin id conflict for %s '%s' (%s); keeping existing (%s).",
                kind,
                plugin_id,
                type(plugin).__name__,
                type(container[plugin_id]).__name__,
            )
            return
        container[plugin_id] = plugin

    def register_estimator(self, plugin: TimeEstimator) -> None:
        self._safe_register(self.estimators, plugin, kind="time_estimator")

    def register_sample_provider(self, plugin: SampleProvider) -> None:
        self._safe_register(self.sample_providers, plugin, kind="sample_provider")

    def register_robot_backend(self, plugin: RobotBackendFactory) -> None:
        self._safe_register(self.robot_backends, plugin, kind="robot_backend")

    def register_gcode_converter(self, plugin: GCodeConverter) -> None:
        self._safe_register(self.gcode_converters, plugin, kind="gcode_converter")

    def load_entry_points(self) -> list[str]:
        failures: list[str] = []

        for ep in _iter_entry_points("ur_print_fdm.time_estimators"):
            try:
                plugin = ep.load()()
                self.register_estimator(plugin)
            except Exception as e:
                failures.append(f"{ep.group}:{ep.name}")
                logging.exception("Failed to load %s entry point '%s': %s", ep.group, ep.name, e)

        for ep in _iter_entry_points("ur_print_fdm.sample_providers"):
            try:
                plugin = ep.load()()
                self.register_sample_provider(plugin)
            except Exception as e:
                failures.append(f"{ep.group}:{ep.name}")
                logging.exception("Failed to load %s entry point '%s': %s", ep.group, ep.name, e)

        for ep in _iter_entry_points("ur_print_fdm.robot_backends"):
            try:
                plugin = ep.load()()
                self.register_robot_backend(plugin)
            except Exception as e:
                failures.append(f"{ep.group}:{ep.name}")
                logging.exception("Failed to load %s entry point '%s': %s", ep.group, ep.name, e)

        for ep in _iter_entry_points("ur_print_fdm.gcode_converters"):
            try:
                plugin = ep.load()()
                self.register_gcode_converter(plugin)
            except Exception as e:
                failures.append(f"{ep.group}:{ep.name}")
                logging.exception("Failed to load %s entry point '%s': %s", ep.group, ep.name, e)

        return failures


registry = PluginRegistry()
