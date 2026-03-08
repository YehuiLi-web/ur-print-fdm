"""
Legacy compatibility module.

Production worker was migrated to `ui.workers.production_processor` so that the
`core` layer can be gradually decoupled from PyQt.
"""
import warnings

warnings.warn(
    "ur_print_fdm.core.processor is deprecated; import from ur_print_fdm.ui.workers.production_processor instead.",
    DeprecationWarning,
    stacklevel=2,
)

from ur_print_fdm.ui.workers.production_processor import ProductionProcessor  # noqa: F401

__all__ = ["ProductionProcessor"]
