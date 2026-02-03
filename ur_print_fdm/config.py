"""
Legacy compatibility module.

The application historically imported `config_manager` from the repository root:
`from config import config_manager`.

New code should import from `ur_print_fdm.config` instead.
"""

from ur_print_fdm.config.manager import ConfigManager, config_manager

__all__ = ["ConfigManager", "config_manager"]

