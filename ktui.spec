# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ktui.
Run from the repo root (same directory as this file):
  pyinstaller ktui.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["ktui/app.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Schema JSON
        ("ktui/data/k8s_schema.json",   "ktui/data"),
        # Textual CSS
        ("ktui/ui/styles/app.tcss",     "ktui/ui/styles"),
    ],
    hiddenimports=[
        "textual",
        "textual.app",
        "textual.widgets",
        "textual.containers",
        "textual.screen",
        "textual.binding",
        "textual.theme",
        "textual.reactive",
        "textual.css",
        "textual.css.query",
        "textual.driver",
        "textual.drivers.linux_driver",
        "textual.drivers.headless_driver",
        "ruamel.yaml",
        "ruamel.yaml.main",
        "pydantic",
        "ktui.app",
        "ktui.schema",
        "ktui.schema.loader",
        "ktui.schema.emitter",
        "ktui.ui",
        "ktui.ui.screens",
        "ktui.ui.screens.main_screen",
        "ktui.ui.screens.yaml_preview",
        "ktui.ui.screens.field_picker",
        "ktui.ui.screens.directory_picker",
        "ktui.ui.engine",
        "ktui.ui.engine.schema_form_builder",
        "ktui.ui.widgets",
        "ktui.ui.widgets.connection_panel",
        "ktui.ui.widgets.map_editor",
        "ktui.ui.widgets.list_editor",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "doctest", "pdb"],
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
    name="ktui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
