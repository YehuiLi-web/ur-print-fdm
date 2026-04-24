# -*- mode: python ; coding: utf-8 -*-
import os, sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Collect all ur_print_fdm submodules
hiddenimports = [
    # PyQt6 完整导入
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    # 项目核心模块
    'ur_print_fdm',
    'ur_print_fdm.plugins',
    'ur_print_fdm.samples',
    'ur_print_fdm.config',
    'ur_print_fdm.shared',
    'ur_print_fdm.ui',
    'ur_print_fdm.core',
    'ur_print_fdm.domain',
    'ur_print_fdm.processes',
    'ur_print_fdm.estimators',
    'ur_print_fdm.robots',
    # 第三方库可能需要的导入
    'rtde_control',
    'rtde_receive',
    'dashboard_client',
    'paramiko',
    'numpy',
]

hiddenimports += collect_submodules('ur_print_fdm')

# Project root
ROOT = os.path.abspath('.')

# 构建 datas 列表 - 使用正确格式 (src, dst)
datas = []
icons_dir = os.path.join(ROOT, 'ur_print_fdm', 'ui', 'resources', 'icons')
if os.path.exists(icons_dir):
    datas.append((icons_dir, os.path.join('ur_print_fdm', 'ui', 'resources', 'icons')))

help_center_dir = os.path.join(ROOT, 'ur_print_fdm', 'help_center', 'site')
if os.path.exists(help_center_dir):
    datas.append((help_center_dir, os.path.join('ur_print_fdm', 'help_center', 'site')))

help_center_content_dir = os.path.join(ROOT, 'ur_print_fdm', 'help_center', 'content')
if os.path.exists(help_center_content_dir):
    datas.append((help_center_content_dir, os.path.join('ur_print_fdm', 'help_center', 'content')))

release_notes_dir = os.path.join(ROOT, 'ur_print_fdm', 'release_notes')
if os.path.exists(release_notes_dir):
    datas.append((release_notes_dir, os.path.join('ur_print_fdm', 'release_notes')))

# URscript 目录
urscript_dir = os.path.join(ROOT, 'URscript')
if os.path.exists(urscript_dir):
    datas.append((urscript_dir, 'URscript'))

a = Analysis(
    [os.path.join(ROOT, 'ur_print_fdm', '__main__.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'pytest_qt', 'ruff', 'mypy', 'pre_commit'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UR Print FDM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                # GUI application, no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'app_icon.ico'),
    optimize=2,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='UR Print FDM',
)
