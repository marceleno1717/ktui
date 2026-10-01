import asyncio
from textual.widgets import ListView, ListItem, Button, Static, Input
from ktui.app import YAMLGeneratorApp

async def run_tests():
    app = YAMLGeneratorApp()
    async with app.run_test(headless=True, size=(120, 40)) as pilot:
        print("1. App started successfully.")
        
        lv = app.screen.query_one('#resource-list', ListView)
        items = list(lv.query(ListItem))
        dep = next(i for i in items if i.name == 'Deployment')
        lv.index = items.index(dep)
        lv.action_select_cursor()
        
        await pilot.pause(1.0)
        
        header = app.screen.query_one("#resource-header", Static)
        print("2. Resource selected and form loaded.")
        
        inputs = list(app.screen.query(Input))
        if inputs:
            name_input = inputs[0]
            name_input.focus()
            await pilot.press("t", "e", "s", "t", "-", "a", "p", "p")
            await pilot.pause(0.2)
            assert name_input.value == "test-app", f"Input value is {name_input.value}"
            print("3. Input typing works.")
            
        await pilot.click("#btn-preview")
        await pilot.pause(0.5)
        
        assert app.screen.__class__.__name__ == "YAMLPreviewScreen", f"Screen is {app.screen.__class__.__name__}"
        print("4. Preview screen loaded.")
        
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.screen.__class__.__name__ == "MainScreen", f"Screen is {app.screen.__class__.__name__}"
        print("5. Navigation stack works (Esc popped screen).")
        
        # --- Test FieldPicker Modal ---
        add_btn = app.screen.query_one(".schema-add-fields-btn", Button)
        add_btn.focus()
        await pilot.press("enter")
        await pilot.pause(0.5)
        assert app.screen.__class__.__name__ == "FieldPickerScreen", "FieldPicker did not open"
        print("6. FieldPicker modal opened.")
        
        # Test navigation/selection in FieldPicker
        tree = app.screen.query_one("#field-tree")
        tree.focus()
        # Go down twice and select
        await pilot.press("down", "down", "enter")
        await pilot.pause(0.2)
        
        # Click Add selected
        add_sel_btn = app.screen.query_one("#fp-add", Button)
        await pilot.click(add_sel_btn)
        await pilot.pause(0.5)
        
        assert app.screen.__class__.__name__ == "MainScreen", "Did not return to MainScreen"
        print("7. FieldPicker modal confirmed and closed.")
        
        # Test Quit binding on MainScreen
        await pilot.press("q")
        await pilot.pause(0.2)
        print("8. Pressed 'q' to quit.")
        
        print("All interaction tests passed successfully!")

asyncio.run(run_tests())
