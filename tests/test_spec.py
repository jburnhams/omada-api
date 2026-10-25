import pytest

from omada_api import spec as S


def test_only_site_level_operations_are_listed_with_site_relative_paths(spec):
    paths = {(o.method, o.path, o.version) for o in S.ops(spec)}
    assert ("PATCH", "remote-logging", "v1") in paths and ("GET", "remote-logging", "v2") in paths
    assert not any("logs/events" in p for _, p, _ in paths)


def test_search_needs_every_term_in_the_path_or_the_summary(spec):
    ops = S.ops(spec)
    assert {o.path for o in S.search(ops, ["lan", "dns"])} == {"setting/lan/dns", "setting/lan/dns/{dnsId}"}
    assert [o.method for o in S.search(ops, ["REMOTE", "modify"])] == ["PATCH"]
    assert S.search(ops, ["nothing", "like", "this"]) == []


def test_find_takes_the_newest_version_unless_asked_and_suggests_near_misses(spec):
    ops = S.ops(spec)
    assert S.find(ops, "get", "remote-logging").version == "v2"
    assert S.find(ops, "get", "/remote-logging/", "v1").version == "v1"
    with pytest.raises(KeyError, match="did you mean"):
        S.find(ops, "put", "lan/dns")


def test_a_list_endpoint_with_page_and_pagesize_is_paged_and_path_params_are_kept(spec):
    ops = {(o.method, o.path): o for o in S.ops(spec)}
    assert ops[("GET", "setting/lan/dns")].paged and not ops[("GET", "remote-logging")].paged
    assert [p["name"] for p in ops[("DELETE", "setting/lan/dns/{dnsId}")].params] == ["dnsId"]


def test_describe_follows_refs_and_unknown_keys_are_reported(spec):
    op = S.find(S.ops(spec), "patch", "remote-logging")
    assert S.describe(spec, op.body) == ["remoteLog: object", "  enable: boolean - on", "  host: string", "  password: string"]
    assert S.unknown_keys(spec, op, {"remoteLog": {}, "oops": 1}) == ["oops"]
    assert S.unknown_keys(spec, S.find(S.ops(spec), "get", "remote-logging"), {"anything": 1}) == []      # no declared fields: nothing to check against
