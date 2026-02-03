from __future__ import annotations

from typing import Sequence

import ur_print_fdm.core.samples  # noqa: F401
from ur_print_fdm.core.sample_library_manager import SampleManager
from ur_print_fdm.samples.api import SampleBase


class LegacyCoreSampleProvider:
    id = "legacy_core_samples"
    title = "Legacy core samples provider"

    def get_samples(self) -> Sequence[SampleBase]:
        return SampleManager.get_all_samples()
