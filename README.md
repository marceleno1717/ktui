<div align="center">
  <h1>🚢 ktui</h1>
  <p><strong>An interactive terminal UI for building Kubernetes YAML manifests.</strong></p>
  
  <p>
    <a href="https://github.com/marceleno1717/ktui/actions/workflows/ci.yml"><img src="https://github.com/marceleno1717/ktui/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
    <a href="https://pypi.org/project/ktui/"><img src="https://img.shields.io/pypi/v/ktui" alt="PyPI version"></a>
    <a href="https://www.npmjs.com/package/@ktui/editor"><img src="https://img.shields.io/npm/v/@ktui/editor" alt="npm version"></a>
    <a href="https://pypi.org/project/ktui/"><img src="https://img.shields.io/pypi/pyversions/ktui" alt="Python Versions"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue.svg" alt="License"></a>
  </p>
</div>

---

## ⚡ Why ktui?

Tired of memorizing exact YAML structures, indentation rules, and valid fields for every Kubernetes resource? 

`ktui` solves this by giving you a dynamic, schema-driven terminal UI. It behaves like a modern web form inside your terminal. Pick a resource, fill in the fields you care about, use the interactive field picker to search for advanced properties, and preview or save the generated YAML. 

## ✨ Features

- 🏗️ **Schema-driven Forms**: Built-in definitions for core Kubernetes resources (Deployments, Pods, Services, ConfigMaps, RBAC, OpenShift Routes, etc.).
- 🔍 **Interactive Field Picker**: Don't see the field you need? Open the searchable field picker to dynamically mount new properties or entire field groups (like `spec.template.spec.containers`) into your form.
- ♻️ **Smart Merging**: Added fields are intelligently merged into their correct hierarchical sections—no duplicate categories or broken nesting.
- 👁️ **Live YAML Preview**: Press `p` at any time to instantly see the clean, formatted YAML you are building.
- 🎨 **Modern TUI**: Keyboard-first navigation, multiple themes (press `t` to cycle), and a responsive layout powered by [Textual](https://textual.textualize.io/).
- 💾 **Instant Save**: Save your generated manifests directly to your disk with a single keystroke.

## 🚀 Installation

`ktui` is distributed as both a Python package and a self-contained executable via npm.

### Option A: npm / npx (Recommended for JS/TS devs)
You don't even need Python installed! The npm package downloads a pre-compiled native binary for your OS (Linux, macOS, Windows).

```bash
# Run directly without installing
npx @ktui/editor

# Or install globally
npm install -g @ktui/editor
```

### Option B: pipx / pip (Recommended for Python devs)
Install via PyPI using `pipx` (to keep your environment clean):

```bash
pipx install ktui

# Or with pip
pip install ktui
```

## ⌨️ Usage & Keybindings

Simply run `ktui` in your terminal to start the application.

### Global
| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate focused lists |
| `Tab` / `Shift+Tab` | Move between form fields |
| `Enter` | Select resource / confirm |
| `p` | Preview YAML |
| `Ctrl+S` | Save YAML to file |
| `t` | Cycle application theme |
| `Esc` | Close modal / Go back |
| `q` | Quit |

### Field Picker (Press `Add Field` in forms)
| Key | Action |
|-----|--------|
| `/` | Focus search bar |
| `↑` / `↓` | Navigate available fields |
| `Enter` (on property) | Toggle individual field selection |
| `Enter` (on 📁 group) | Select / deselect all fields in that group |
| `Esc` | Cancel without adding |

## 🛠️ Development

If you want to contribute or build from source:

```bash
git clone https://github.com/marceleno1717/ktui.git
cd ktui

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start the app
ktui
```

## 📄 License

This project is licensed under the [PolyForm Noncommercial License 1.0.0](LICENSE).
