from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperationResult:
    success: bool
    message: str = ""
    detail: str = ""
    payload: Any = None

    @classmethod
    def ok(cls, message: str = "", *, detail: str = "", payload: Any = None) -> "OperationResult":
        return cls(True, message=message, detail=detail, payload=payload)

    @classmethod
    def fail(cls, message: str, *, detail: str = "", payload: Any = None) -> "OperationResult":
        return cls(False, message=message, detail=detail, payload=payload)
