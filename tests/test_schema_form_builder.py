from ktui.ui.engine.schema_form_builder import decode_path, encode_path


def test_encode_decode_path():
    path = "spec.template.spec.containers[0].resources.requests"
    encoded = encode_path(path)
    assert encoded.startswith("sf_")
    assert "__" in encoded
    
    decoded = decode_path(encoded)
    assert decoded == ["spec", "template", "spec", "containers[0]", "resources", "requests"]

def test_decode_invalid():
    assert decode_path("invalid_id") is None
