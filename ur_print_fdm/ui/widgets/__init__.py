"""Widget package for ur_print_fdm UI."""

__all__ = ["FileExplorerWidget", "StatusWidget"]


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "StatusWidget":
        from ur_print_fdm.ui.widgets.collapsible_status_dock import StatusWidget
        return StatusWidget
    if name == "FileExplorerWidget":
        from ur_print_fdm.ui.widgets.file_explorer import FileExplorerWidget
        return FileExplorerWidget
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
