from ktui.schema.emitter import _clean, emit_yaml_from_dict


def test_clean_removes_empty():
    data = {
        "metadata": {"name": "test", "labels": {}},
        "spec": {"containers": [], "replicas": 1},
        "empty_str": ""
    }
    cleaned = _clean(data)
    assert cleaned == {"metadata": {"name": "test"}, "spec": {"replicas": 1}}

def test_emit_yaml_from_dict():
    data = {"kind": "Pod", "apiVersion": "v1", "metadata": {"name": "x"}}
    yaml_str = emit_yaml_from_dict(data)
    assert "kind: Pod" in yaml_str
    assert "apiVersion: v1" in yaml_str
    assert "  name: x" in yaml_str
