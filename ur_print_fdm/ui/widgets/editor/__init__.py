try:
    from .core import CodeEditor
    from .manager import DockableEditorWidget
except ModuleNotFoundError as exc:
    if exc.name != "PyQt6":
        raise
    CodeEditor = None
    DockableEditorWidget = None

__all__ = ["CodeEditor", "DockableEditorWidget"]
