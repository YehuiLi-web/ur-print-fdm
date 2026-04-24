from __future__ import annotations

import sys
from pathlib import Path


DEFAULT_RELEASE_NOTES_BODY = "当前版本还没有附带版本说明。下次打包后，这里会显示本次更新内容。"
RELEASE_NOTES_MARKER = "版本说明:"


def _candidate_release_notes_paths() -> list[Path]:
    package_dir = Path(__file__).resolve().parent
    candidates = [
        package_dir / "release_notes" / "latest.txt",
        package_dir.parent / "release_notes" / "latest.txt",
        Path(sys.executable).resolve().parent / "Release Notes.txt",
    ]
    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def parse_release_notes_body(text: str) -> str:
    stripped_text = text.strip()
    if not stripped_text:
        return DEFAULT_RELEASE_NOTES_BODY

    lines = [line.rstrip() for line in stripped_text.splitlines()]
    for index, line in enumerate(lines):
        if line.strip() == RELEASE_NOTES_MARKER:
            body = "\n".join(lines[index + 1 :]).strip()
            if body:
                return body
            break
    return stripped_text


def load_latest_release_notes_body() -> str:
    for path in _candidate_release_notes_paths():
        if not path.exists():
            continue
        try:
            return parse_release_notes_body(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return DEFAULT_RELEASE_NOTES_BODY
