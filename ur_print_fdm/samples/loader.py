from __future__ import annotations

from ur_print_fdm.core.sample_library_manager import SampleManager
from ur_print_fdm.plugins.registry import registry
from ur_print_fdm.samples.api import SampleBase

_LOADED = False


def load_samples() -> None:
    global _LOADED
    if _LOADED:
        return

    for provider in registry.sample_providers.values():
        for sample in provider.get_samples():
            if isinstance(sample, SampleBase):
                SampleManager.register(sample)

    _LOADED = True
