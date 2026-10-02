# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ktui.
Run from the repo root (same directory as this file):
  pyinstaller ktui.spec
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Automatically find all textual hidden imports and data files (like CSS)
import os
import textual
textual_hidden = collect_submodules("textual")
textual_datas = collect_data_files("textual")

widgets_dir = os.path.join(os.path.dirname(textual.__file__), "widgets")
for f in os.listdir(widgets_dir):
    if f.endswith(".py") and f != "__init__.py":
        textual_hidden.append(f"textual.widgets.{f[:-3]}")

a = Analysis(
    ["src/ktui/app.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # Schema JSON
        ("src/ktui/data/k8s_schema.json",   "ktui/data"),
        # Textual CSS
        ("src/ktui/ui/styles/app.tcss",     "ktui/ui/styles"),
        ("src/ktui/ui/styles/app.tcss",     "ui/styles"), # For PyInstaller __main__ resolution
    ] + textual_datas,
    hiddenimports=[
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
    ] + textual_hidden,
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
