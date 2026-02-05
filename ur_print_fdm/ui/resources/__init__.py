"""UI resources for ur_print_fdm."""

__all__ = ["IconManager"]


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "IconManager":
        from ur_print_fdm.ui.resources.icon_manager import IconManager
        return IconManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
