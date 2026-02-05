"""UI shim package for gradual migration into ur_print_fdm."""

__all__ = ["URPrintIDE"]


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "URPrintIDE":
        from ur_print_fdm.ui.main_window import URPrintIDE
        return URPrintIDE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
