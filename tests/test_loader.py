from ktui.schema.loader import (
    get_all_resources,
    get_common_fields,
    get_leaf_field_paths,
    load_resource,
)


def test_get_all_resources():
    res = get_all_resources()
    assert len(res) >= 22
    assert any(r["kind"] == "Pod" for r in res)

def test_load_resource():
    pod = load_resource("Pod")
    assert pod is not None
    assert pod["kind"] == "Pod"
    assert pod["apiVersion"] == "v1"
    assert "fields" in pod

def test_get_common_fields():
    fields = get_common_fields("Pod")
    assert isinstance(fields, list)
    assert "spec.containers" in fields or "metadata.name" in fields

def test_get_leaf_field_paths():
    pod = load_resource("Pod")
    paths = get_leaf_field_paths(pod["fields"])
    assert len(paths) > 100
    # Check memoization
    paths2 = get_leaf_field_paths(pod["fields"])
    assert paths is paths2
