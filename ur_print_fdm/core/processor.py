"""
Legacy compatibility module.

Production worker was migrated to `ui.workers.production_processor` so that the
`core` layer can be gradually decoupled from PyQt.
"""

from ur_print_fdm.ui.workers.production_processor import ProductionProcessor  # noqa: F401

__all__ = ["ProductionProcessor"]
