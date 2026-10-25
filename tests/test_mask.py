from omada_api.mask import mask


def test_secret_looking_values_are_hidden_and_the_rest_is_kept():
    out = mask({"name": "wan1", "password": "hunter2", "psk": "abc", "pin": "1234", "nested": [{"clientSecret": "s", "id": "x"}], "token": "", "enable": False})
    assert out == {"name": "wan1", "password": "***", "psk": "***", "pin": "***", "nested": [{"clientSecret": "***", "id": "x"}], "token": "", "enable": False}


def test_the_original_is_not_changed():
    d = {"password": "p"}
    mask(d)
    assert d == {"password": "p"}
