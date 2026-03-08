from ur_print_fdm.plugins.builtin import register_builtin_plugins
from ur_print_fdm.plugins.registry import registry

_BOOTSTRAPPED = False


def bootstrap_plugins() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return

    register_builtin_plugins(registry)
    registry.load_entry_points()
    _BOOTSTRAPPED = True
