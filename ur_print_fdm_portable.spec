# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

ROOT = os.path.abspath(".")

hiddenimports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtSvg",
    "PyQt6.sip",
    "ur_print_fdm",
    "ur_print_fdm.plugins",
    "ur_print_fdm.samples",
    "ur_print_fdm.config",
    "ur_print_fdm.shared",
    "ur_print_fdm.ui",
    "ur_print_fdm.core",
    "ur_print_fdm.domain",
    "ur_print_fdm.processes",
    "ur_print_fdm.estimators",
    "ur_print_fdm.robots",
    "rtde_control",
    "rtde_receive",
    "dashboard_client",
    "paramiko",
    "numpy",
]

hiddenimports += collect_submodules("ur_print_fdm")

datas = []
icons_dir = os.path.join(ROOT, "ur_print_fdm", "ui", "resources", "icons")
if os.path.exists(icons_dir):
    datas.append((icons_dir, os.path.join("ur_print_fdm", "ui", "resources", "icons")))

urscript_dir = os.path.join(ROOT, "URscript")
if os.path.exists(urscript_dir):
    datas.append((urscript_dir, "URscript"))

a = Analysis(
    [os.path.join(ROOT, "ur_print_fdm", "__main__.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "pytest_qt", "ruff", "mypy", "pre_commit"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="UR Print FDM Portable",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "app_icon.ico"),
    optimize=2,
)
