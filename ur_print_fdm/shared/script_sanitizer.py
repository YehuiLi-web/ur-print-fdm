from __future__ import annotations

import re

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def sanitize_script_content(script_content: str) -> str:
    """
    Normalize URScript text before sending.

    Note: this is **not** a security sandbox. It does not attempt to validate or
    restrict URScript capabilities. It only removes problematic control
    characters (e.g. NUL) and normalizes line endings to avoid transport/issues.
    """

    text = script_content.replace("\r\n", "\n").replace("\r", "\n")
    return _CONTROL_CHARS_RE.sub("", text)
