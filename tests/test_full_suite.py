"""
Full TUI interaction test suite — ktui
Per TUI skill testing-tuis.md: startup, resource selection, input typing,
YAML preview, FieldPicker (leaf + group select/deselect), field merge,
Esc cancel, quit binding.
"""

from textual.widgets import Button, Input, ListItem, ListView, Tree

from ktui.app import YAMLGeneratorApp
from ktui.ui.engine.schema_form_builder import FieldSection
from ktui.ui.widgets.list_editor import ListEditor
from ktui.ui.widgets.map_editor import MapEditor

PASS = "✓"
FAIL = "✗"
results = []


def check(label, cond, detail=""):
    status = PASS if cond else FAIL
    results.append((status, label, detail))
    print(f"  {status}  {label}" + (f" — {detail}" if detail else ""))
    return cond


def count_form_widgets(screen):
    """Count all interactive form widgets: Input + MapEditor + ListEditor."""
    return (
        len(list(screen.query(Input)))
        + len(list(screen.query(MapEditor)))
        + len(list(screen.query(ListEditor)))
    )


import pytest


@pytest.mark.asyncio
async def test_full_generate_session():
    print("\n═══ ktui Full Test Suite ═══\n")
    app = YAMLGeneratorApp()
    async with app.run_test(headless=True, size=(160, 50)) as pilot:

        # ── 1. Startup ──────────────────────────────────────────────────────
        print("1. Startup")
        check("App title is ktui", app.TITLE == "ktui")
        check("MainScreen is active", app.screen.__class__.__name__ == "MainScreen")
        check("Resource list visible", bool(app.screen.query("#resource-list")))

        # ── 2. Resource selection ────────────────────────────────────────────
        print("\n2. Resource selection")
        lv = app.screen.query_one("#resource-list", ListView)
        items = list(lv.query(ListItem))
        dep = next((i for i in items if i.name == "Deployment"), None)
        check("Deployment exists in list", dep is not None)
        if dep:
            lv.index = items.index(dep)
            lv.action_select_cursor()
            await pilot.pause(0.8)
        check("Form widgets mounted", count_form_widgets(app.screen) > 0)

        # ── 3. Input typing ──────────────────────────────────────────────────
        print("\n3. Input typing")
        inputs = list(app.screen.query(Input))
        if inputs:
            name_input = inputs[0]
            name_input.focus()
            await pilot.press("t", "e", "s", "t", "-", "a", "p", "p")
            await pilot.pause(0.2)
            check("Can type in name field", name_input.value == "test-app",
                  f"value={name_input.value!r}")

        # ── 4. YAML Preview modal ────────────────────────────────────────────
        print("\n4. YAML Preview modal")
        await pilot.click("#btn-preview")
        await pilot.pause(0.4)
        check("YAMLPreviewScreen opened",
              app.screen.__class__.__name__ == "YAMLPreviewScreen")
        await pilot.press("escape")
        await pilot.pause(0.2)
        check("Esc returns to MainScreen",
              app.screen.__class__.__name__ == "MainScreen")

        # ── 5. FieldPicker — leaf selection ──────────────────────────────────
        print("\n5. FieldPicker — leaf selection")
        widgets_before = count_form_widgets(app.screen)
        add_btn = app.screen.query_one(".schema-add-fields-btn", Button)
        add_btn.focus()
        await pilot.press("enter")
        await pilot.pause(0.5)
        check("FieldPickerScreen opened",
              app.screen.__class__.__name__ == "FieldPickerScreen")

        tree = app.screen.query_one("#field-tree", Tree)
        tree.focus()
        # down → GROUP(metadata), down → leaf(metadata.annotations), enter → select
        await pilot.press("down", "down", "enter")
        await pilot.pause(0.2)
        selected_count = len(app.screen._selected)
        check("Leaf field selected", selected_count > 0,
              f"selected={selected_count}")

        # Confirm FieldPicker
        add_sel_btn = app.screen.query_one("#fp-add", Button)
        await pilot.click(add_sel_btn)
        await pilot.pause(0.6)
        check("FieldPicker confirmed → MainScreen",
              app.screen.__class__.__name__ == "MainScreen")
        widgets_after = count_form_widgets(app.screen)
        check("New widgets added after confirm",
              widgets_after > widgets_before,
              f"before={widgets_before} after={widgets_after}")

        # ── 6. FieldPicker — group select / deselect ─────────────────────────
        print("\n6. FieldPicker — group select / deselect")
        add_btn = app.screen.query_one(".schema-add-fields-btn", Button)
        add_btn.focus()
        await pilot.press("enter")
        await pilot.pause(0.5)

        tree = app.screen.query_one("#field-tree", Tree)
        tree.focus()
        # Navigate to the first GROUP node
        await pilot.press("down")
        await pilot.pause(0.1)
        node = tree.cursor_node
        attempts = 0
        while node and (not node.data or node.data[0] != "GROUP") and attempts < 10:
            await pilot.press("down")
            await pilot.pause(0.05)
            node = tree.cursor_node
            attempts += 1

        if node and node.data and node.data[0] == "GROUP":
            before_sel = len(app.screen._selected)
            await pilot.press("enter")          # select all
            await pilot.pause(0.2)
            after_sel = len(app.screen._selected)
            check("Group enter selects all children", after_sel > before_sel,
                  f"before={before_sel} after={after_sel}")

            await pilot.press("enter")          # deselect all
            await pilot.pause(0.2)
            after_desel = len(app.screen._selected)
            check("Group re-enter deselects children", after_desel < after_sel,
                  f"after_desel={after_desel}")
        else:
            check("Group node reachable by keyboard", False, "no GROUP node found")

        await pilot.press("escape")
        await pilot.pause(0.2)
        check("Esc cancels FieldPicker",
              app.screen.__class__.__name__ == "MainScreen")

        # ── 7. Fields merged into correct section ────────────────────────────
        print("\n7. Merged field sections")
        sections = {
            getattr(s, "_title", None): s
            for s in app.screen.query(FieldSection)
        }
        check("spec FieldSection exists", "spec" in sections,
              f"sections={list(sections.keys())}")
        check("metadata FieldSection exists", "metadata" in sections,
              f"sections={list(sections.keys())}")

        # ── 8. Quit binding ──────────────────────────────────────────────────
        print("\n8. Quit binding")
        await pilot.press("q")
        await pilot.pause(0.2)
        print("  ✓  'q' pressed without crash")

    # ── Summary ──────────────────────────────────────────────────────────────


