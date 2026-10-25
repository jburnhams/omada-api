import json

import pytest

from omada_api import cli, config


class FakeSession:
    calls = []

    def __init__(self, target): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

    async def call(self, op, path, params, body):
        FakeSession.calls.append((op.method, path, params, body))
        return {"ok": True, "password": "secret"}


@pytest.fixture(autouse=True)
def fake(monkeypatch, spec):
    FakeSession.calls = []
    monkeypatch.setattr(cli, "Session", FakeSession)
    monkeypatch.setattr(cli.config, "load", lambda name=None: config.Target("t", "https://c", "u", "p", "Site", False))
    monkeypatch.setattr(cli.specmod, "fetch", lambda *a, **k: spec)


def run(*argv):
    cli.main(list(argv))


def test_a_write_without_yes_only_shows_what_it_would_send_and_masks_secrets(capsys):
    run("patch", "remote-logging", "--json", '{"remoteLog": {"password": "pw"}}')
    out = capsys.readouterr().out
    assert FakeSession.calls == [] and "DRY RUN" in out and "***" in out and '"pw"' not in out


def test_yes_sends_it_and_the_reply_is_masked(capsys):
    run("patch", "remote-logging", "--json", '{"remoteLog": {"enable": true}}', "--yes")
    assert FakeSession.calls == [("PATCH", "remote-logging", {}, {"remoteLog": {"enable": True}})]
    assert json.loads(capsys.readouterr().out) == {"ok": True, "password": "***"}


def test_a_get_is_sent_straight_away_with_its_query_parameters():
    run("get", "setting/lan/dns", "-p", "name=x")
    assert FakeSession.calls == [("GET", "setting/lan/dns", {"name": "x"}, None)]


def test_a_field_the_schema_does_not_have_is_refused_unless_forced():
    with pytest.raises(SystemExit, match="no field"):
        run("patch", "remote-logging", "--json", '{"remoteLogg": {}}', "--yes")
    assert FakeSession.calls == []
    run("patch", "remote-logging", "--json", '{"remoteLogg": {}}', "--yes", "--force")
    assert len(FakeSession.calls) == 1


def test_path_placeholders_come_from_p_and_are_not_sent_as_query_parameters():
    run("delete", "setting/lan/dns/{dnsId}", "-p", "dnsId=abc", "--yes")
    assert FakeSession.calls == [("DELETE", "setting/lan/dns/abc", {}, None)]
    with pytest.raises(SystemExit, match="dnsId"):
        run("delete", "setting/lan/dns/{dnsId}", "--yes")


def test_find_and_schema_print(capsys):
    run("find", "lan", "dns"); assert "setting/lan/dns" in capsys.readouterr().out
    run("schema", "patch", "remote-logging"); assert "enable: boolean" in capsys.readouterr().out
