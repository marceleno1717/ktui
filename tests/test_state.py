from ktui.ui.engine.state import get_nested, set_nested


def test_set_nested_dict():
    data = {}
    set_nested(data, ["a", "b", "c"], 42)
    assert data["a"]["b"]["c"] == 42

def test_set_nested_list():
    data = {}
    set_nested(data, ["a", "b[0]", "c"], 42)
    assert data["a"]["b"][0]["c"] == 42
    
def test_set_nested_list_append():
    data = {"a": {"b": [{"c": 1}]}}
    set_nested(data, ["a", "b[1]", "c"], 2)
    assert data["a"]["b"][1]["c"] == 2
    
def test_get_nested():
    data = {"a": {"b": [{"c": 42}]}}
    assert get_nested(data, ["a", "b[0]", "c"]) == 42
    assert get_nested(data, ["a", "b", "c"]) is None
