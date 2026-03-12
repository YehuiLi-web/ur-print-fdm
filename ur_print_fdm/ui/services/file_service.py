from __future__ import annotations

import logging
from pathlib import Path

from ur_print_fdm.shared.operation_result import OperationResult


class FileService:
    def __init__(self) -> None:
        self._logger = logging.getLogger("ur_print_fdm.ui.file_service")

    def read_text(self, path: str | Path, *, encoding: str = "utf-8", action: str = "read") -> OperationResult:
        target = Path(path)
        try:
            text = target.read_text(encoding=encoding)
            return OperationResult.ok(f"{action} ok", payload=text, detail=str(target))
        except Exception as exc:
            self._logger.exception("File action failed: action=%s path=%s", action, target)
            return OperationResult.fail(
                f"{action} failed",
                detail=f"{target}: {type(exc).__name__}: {exc}",
            )

    def write_text(
        self,
        path: str | Path,
        content: str,
        *,
        encoding: str = "utf-8",
        ensure_parent: bool = True,
        action: str = "write",
    ) -> OperationResult:
        target = Path(path)
        try:
            if ensure_parent:
                target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding=encoding)
            return OperationResult.ok(f"{action} ok", payload=str(target), detail=str(target))
        except Exception as exc:
            self._logger.exception("File action failed: action=%s path=%s", action, target)
            return OperationResult.fail(
                f"{action} failed",
                detail=f"{target}: {type(exc).__name__}: {exc}",
            )


file_service = FileService()
