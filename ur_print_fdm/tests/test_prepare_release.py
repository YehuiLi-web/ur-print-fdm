from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "prepare_release.py"


def load_prepare_release_module():
    spec = importlib.util.spec_from_file_location("prepare_release", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fixture_files(root: Path) -> None:
    (root / "ur_print_fdm").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "ur-print-fdm"\nversion = "0.1.1"\n',
        encoding="utf-8",
    )
    (root / "ur_print_fdm" / "__init__.py").write_text(
        '__all__ = ["__version__"]\n\n__version__ = "0.1.1"\n',
        encoding="utf-8",
    )
    (root / "installer.iss").write_text(
        '#define MyAppName "UR Print FDM"\n#define MyAppVersion "0.1.1"\n',
        encoding="utf-8",
    )


def test_prepare_release_updates_versions_and_notes(tmp_path):
    module = load_prepare_release_module()
    write_fixture_files(tmp_path)

    artifacts = module.prepare_release(tmp_path, "0.2.0", "- 修复安装路径\n- 新增版本说明")

    assert 'version = "0.2.0"' in (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert '__version__ = "0.2.0"' in (tmp_path / "ur_print_fdm" / "__init__.py").read_text(encoding="utf-8")
    assert '#define MyAppVersion "0.2.0"' in (tmp_path / "installer.iss").read_text(encoding="utf-8")

    latest_notes = artifacts.latest_notes_path.read_text(encoding="utf-8")
    archived_notes = artifacts.versioned_notes_path.read_text(encoding="utf-8")
    runtime_notes = artifacts.runtime_notes_path.read_text(encoding="utf-8")
    assert "UR Print FDM 0.2.0" in latest_notes
    assert "- 修复安装路径" in latest_notes
    assert latest_notes == archived_notes
    assert latest_notes == runtime_notes
    assert artifacts.template_notes_path.read_text(encoding="utf-8").startswith("1. 本次新增")


def test_normalize_notes_uses_placeholder_when_empty():
    module = load_prepare_release_module()

    assert module.normalize_notes(" \n ") == "本次构建未填写版本说明。"
