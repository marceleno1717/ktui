# ktui

> An interactive terminal UI for building Kubernetes YAML manifests — schema-driven forms, field picker, and live preview.

---

## What it does

`ktui` is a terminal application that lets you interactively build Kubernetes resource manifests without memorising YAML structure. Pick a resource type, fill in only the fields you need, add optional fields through a searchable picker, and preview or save the generated YAML — all from your terminal.

**Key features:**
- Schema-driven forms for common Kubernetes resources (Deployment, Service, ConfigMap, RBAC, …)
- Searchable field picker with grouped categories — select individual fields or entire groups at once
- Added fields are intelligently merged into the correct section (no duplicate categories)
- Live YAML preview
- Theme switching (`t` to cycle)
- Clean keyboard-first navigation

---

## Requirements

- Python ≥ 3.12
- A terminal with UTF-8 support (minimum 80×24)
- Truecolor recommended but not required

---

## Installation

```bash
# From source (development)
git clone <repo-url>
cd ktui
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Run
ktui
```

---

## Keybindings

| Key | Action |
|-----|--------|
| `↑ / ↓` | Navigate list |
| `Enter` | Select resource / confirm |
| `p` | Preview YAML |
| `Ctrl+S` | Save YAML |
| `t` | Cycle theme |
| `Esc` | Close modal / go back |
| `q` | Quit |

**Inside Field Picker:**

| Key | Action |
|-----|--------|
| `↑ / ↓` | Navigate fields |
| `Enter` on leaf | Toggle field selection |
| `Enter` on 📁 group | Select / deselect all fields in group |
| `Esc` | Cancel without adding |

---

## Status

Early development — schemas and features are actively expanding.

---

## License

[PolyForm Noncommercial License 1.0.0](LICENSE)
