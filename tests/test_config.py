import stat

import pytest

from omada_api import config


def test_a_saved_login_is_read_back_and_the_file_is_private(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PATH", tmp_path / "cfg")
    config.save("home", "https://x:8043", "user", "pw", "Site", False)
    t = config.load()
    assert (t.name, t.url, t.username, t.password, t.site, t.verify_ssl) == ("home", "https://x:8043", "user", "pw", "Site", False)
    assert stat.S_IMODE((tmp_path / "cfg").stat().st_mode) == 0o600
    assert config.names() == ["home"]


def test_no_login_says_how_to_make_one(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PATH", tmp_path / "none")
    with pytest.raises(SystemExit, match="omada-api login"):
        config.load()
