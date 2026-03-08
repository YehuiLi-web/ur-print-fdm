from __future__ import annotations

import warnings

from ur_print_fdm.shared.script_sanitizer import sanitize_script_content

warnings.warn(
    "ur_print_fdm.core.script_sanitizer is deprecated; use ur_print_fdm.shared.script_sanitizer instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["sanitize_script_content"]
