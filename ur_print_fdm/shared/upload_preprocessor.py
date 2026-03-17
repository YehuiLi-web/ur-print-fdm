from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator

from ur_print_fdm.shared.script_sanitizer import sanitize_script_content

_NORMALIZED_TEXT_SUFFIXES = frozenset({".script", ".txt", ".gcode", ".urscript"})


@dataclass(frozen=True)
class PreparedUploadSource:
    path: str
    normalized: bool = False


@contextmanager
def prepare_upload_source(local_path: str | os.PathLike[str]) -> Iterator[PreparedUploadSource]:
    source_path = Path(local_path)
    base_source = PreparedUploadSource(path=str(source_path), normalized=False)

    if source_path.suffix.lower() not in _NORMALIZED_TEXT_SUFFIXES:
        yield base_source
        return

    try:
        raw = source_path.read_bytes()
    except Exception:
        yield base_source
        return

    if b"\r" not in raw and b"\x00" not in raw:
        yield base_source
        return

    try:
        original_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        yield base_source
        return

    normalized_text = sanitize_script_content(original_text)
    if normalized_text == original_text:
        yield base_source
        return

    temp_path = None
    try:
        suffix = source_path.suffix or ".tmp"
        prefix = f"{source_path.stem or 'upload'}_"
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            suffix=suffix,
            prefix=prefix,
            delete=False,
        ) as handle:
            handle.write(normalized_text)
            temp_path = handle.name
        yield PreparedUploadSource(path=temp_path, normalized=True)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
