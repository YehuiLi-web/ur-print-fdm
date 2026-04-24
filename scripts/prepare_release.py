from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
PYPROJECT_VERSION_RE = re.compile(r'(?m)^(version\s*=\s*")([^"]+)(")$')
PACKAGE_VERSION_RE = re.compile(r'(?m)^(__version__\s*=\s*")([^"]+)(")$')
INSTALLER_VERSION_RE = re.compile(r'(?m)^(#define MyAppVersion\s+")([^"]+)(")$')


@dataclass(frozen=True)
class ReleaseArtifacts:
    latest_notes_path: Path
    versioned_notes_path: Path
    runtime_notes_path: Path
    template_notes_path: Path


DEFAULT_NOTES_TEMPLATE = """1. 本次新增
- 

2. 本次优化
- 

3. 修复问题
- 

4. 升级提醒
- 无
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare release metadata for a local build.")
    parser.add_argument("--version", help="Version to build, for example 0.1.2")
    parser.add_argument("--notes", help="Release notes text for this build")
    parser.add_argument("--notes-file", help="Read release notes from a UTF-8 text file")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; keep the current version if --version is omitted",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root, mainly for tests",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    return "\n"


def write_text(path: Path, text: str, *, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\n", newline)
    path.write_text(normalized, encoding="utf-8", newline="")


def read_current_version(pyproject_path: Path) -> str:
    match = PYPROJECT_VERSION_RE.search(read_text(pyproject_path))
    if not match:
        raise ValueError(f"Could not find project version in {pyproject_path}")
    return match.group(2)


def validate_version(version: str) -> str:
    candidate = version.strip()
    if not candidate:
        raise ValueError("Version cannot be empty.")
    if not VERSION_PATTERN.fullmatch(candidate):
        raise ValueError("Version must look like 0.1.2 or 0.1.2-beta1.")
    return candidate


def replace_version(path: Path, pattern: re.Pattern[str], version: str) -> None:
    text = read_text(path)
    newline = detect_newline(text)
    updated_text, replacements = pattern.subn(rf"\g<1>{version}\g<3>", text, count=1)
    if replacements != 1:
        raise ValueError(f"Could not update version in {path}")
    write_text(path, updated_text, newline=newline)


def update_versions(root: Path, version: str) -> None:
    replace_version(root / "pyproject.toml", PYPROJECT_VERSION_RE, version)
    replace_version(root / "ur_print_fdm" / "__init__.py", PACKAGE_VERSION_RE, version)
    replace_version(root / "installer.iss", INSTALLER_VERSION_RE, version)


def sanitize_version_for_filename(version: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "_", version)


def normalize_notes(notes: str) -> str:
    cleaned = "\n".join(line.rstrip() for line in notes.splitlines()).strip()
    if cleaned:
        return cleaned
    return "本次构建未填写版本说明。"


def format_release_notes(version: str, notes: str) -> str:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    body = normalize_notes(notes)
    return "\n".join(
        [
            f"UR Print FDM {version}",
            "",
            f"构建时间: {timestamp}",
            "",
            "版本说明:",
            body,
            "",
        ]
    )


def ensure_release_notes_template(root: Path) -> Path:
    template_path = root / "release_notes" / "template.txt"
    if not template_path.exists():
        write_text(template_path, DEFAULT_NOTES_TEMPLATE)
    return template_path


def load_release_notes_template(root: Path) -> str:
    return read_text(ensure_release_notes_template(root))


def write_release_notes(version: str, notes: str, root: Path) -> ReleaseArtifacts:
    formatted_notes = format_release_notes(version, notes)
    safe_version = sanitize_version_for_filename(version)
    release_notes_dir = root / "release_notes"
    latest_path = release_notes_dir / "latest.txt"
    versioned_path = release_notes_dir / f"{safe_version}.txt"
    runtime_path = root / "ur_print_fdm" / "release_notes" / "latest.txt"
    template_path = ensure_release_notes_template(root)
    write_text(latest_path, formatted_notes)
    write_text(versioned_path, formatted_notes)
    write_text(runtime_path, formatted_notes)
    return ReleaseArtifacts(
        latest_notes_path=latest_path,
        versioned_notes_path=versioned_path,
        runtime_notes_path=runtime_path,
        template_notes_path=template_path,
    )


def prompt_for_version(current_version: str) -> str:
    response = input(f"请输入本次版本号 [{current_version}]: ").strip()
    return response or current_version


def prompt_for_notes(root: Path) -> str:
    template_text = load_release_notes_template(root)
    print("请输入本次版本说明，支持多行；单独输入 . 后结束。")
    print("第一行直接输入 . 或 /template，可直接套用 release_notes/template.txt 模板。")
    lines: list[str] = []
    while True:
        line = input()
        if line == ".":
            if not lines:
                return template_text
            return "\n".join(lines)
        if not lines and line.strip() == "/template":
            return template_text
        lines.append(line)


def resolve_notes(args: argparse.Namespace, root: Path) -> str:
    if args.notes_file:
        return read_text(Path(args.notes_file))
    if args.notes is not None:
        return args.notes
    if args.non_interactive:
        return ""
    return prompt_for_notes(root)


def prepare_release(root: Path, version: str, notes: str) -> ReleaseArtifacts:
    update_versions(root, version)
    return write_release_notes(version, notes, root)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    pyproject_path = root / "pyproject.toml"

    try:
        current_version = read_current_version(pyproject_path)
        version = validate_version(args.version or (current_version if args.non_interactive else prompt_for_version(current_version)))
        notes = resolve_notes(args, root)
        artifacts = prepare_release(root, version, notes)
    except KeyboardInterrupt:
        print("\n已取消发布准备。", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - keep CLI failures user-friendly
        print(f"[错误] {exc}", file=sys.stderr)
        return 1

    print(f"版本号已同步为: {version}")
    print(f"最新版本说明: {artifacts.latest_notes_path.relative_to(root)}")
    print(f"版本归档说明: {artifacts.versioned_notes_path.relative_to(root)}")
    print(f"运行时版本说明: {artifacts.runtime_notes_path.relative_to(root)}")
    print(f"版本说明模板: {artifacts.template_notes_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
