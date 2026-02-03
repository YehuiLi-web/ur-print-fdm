"""
Legacy compatibility module.

Prefer importing from `ur_print_fdm.config` instead of `src.config`.
"""

from ur_print_fdm.config.manager import ConfigManager, config_manager

__all__ = ["ConfigManager", "config_manager"]
