"""The controller's own API description (`/v3/api-docs`): find endpoints, show what a request takes."""

import json
import os
import re
import ssl
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

SITE_OP = re.compile(r"^/openapi/(v\d+)/\{omadacId\}/sites/\{siteId\}/(.*)$")
METHODS = ("get", "put", "post", "patch", "delete")
SKIP_PARAMS = {"omadacId", "siteId", "Authorization"}


@dataclass
class Op:
    method: str  # GET, PATCH, ...
    version: str  # v1, v2, v3
    path: str  # relative to the site: 'remote-logging', 'setting/lan/dns/{dnsId}'
    summary: str
    params: list = field(default_factory=list)  # [{name, in, required, type, description}]
    body: dict | None = None  # the request body schema (may hold $refs)

    @property
    def paged(self) -> bool:
        return {"page", "pageSize"} <= {p["name"] for p in self.params}

    def label(self) -> str:
        return f"{self.method:<6} {self.path}" + ("" if self.version == "v1" else f"  ({self.version})")


def _cache_file(url: str) -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "omada-api"
    return base / (re.sub(r"[^A-Za-z0-9]+", "_", url) + ".json")


def fetch(url: str, verify_ssl: bool = True, max_age: float = 7 * 86400, refresh: bool = False) -> dict:
    """The spec of the controller at `url`, from a cache under ~/.cache/omada-api when it is recent (the controller is asked at most weekly)."""
    cache = _cache_file(url)
    if not refresh and cache.exists() and time.time() - cache.stat().st_mtime < max_age:
        return json.loads(cache.read_text())
    ctx = None if verify_ssl else ssl._create_unverified_context()  # noqa: S323  (--insecure is the caller's explicit choice: controllers ship self-signed certificates)
    with urllib.request.urlopen(url.rstrip("/") + "/v3/api-docs", context=ctx, timeout=30) as r:  # noqa: S310  (the URL is the controller address the user typed)
        data = r.read()
    spec = json.loads(data)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(data)
    return spec


def resolve(spec: dict, node: dict) -> dict:
    while isinstance(node, dict) and "$ref" in node:
        node = spec["components"]["schemas"][node["$ref"].split("/")[-1]]
    return node


def ops(spec: dict) -> list[Op]:
    """Every site-scoped operation (those under /sites/{siteId}/), the ones this tool calls."""
    out = []
    for path, item in spec.get("paths", {}).items():
        m = SITE_OP.match(path)
        if not m:
            continue
        for method in METHODS:
            o = item.get(method)
            if not o:
                continue
            params = [
                {
                    "name": p["name"],
                    "in": p.get("in"),
                    "required": p.get("required", False),
                    "type": (p.get("schema") or {}).get("type"),
                    "description": (p.get("description") or ""),
                }
                for p in (o.get("parameters") or []) + (item.get("parameters") or [])
                if p["name"] not in SKIP_PARAMS
            ]
            body = ((o.get("requestBody") or {}).get("content") or {}).get("application/json", {}).get("schema")
            out.append(Op(method.upper(), m.group(1), m.group(2), o.get("summary") or "", params, body))
    return sorted(out, key=lambda o: (o.path, o.method, o.version))


def search(all_ops: list[Op], terms: list[str]) -> list[Op]:
    """Operations whose path or summary contains every term (case-insensitive)."""
    terms = [t.lower() for t in terms]
    return [o for o in all_ops if all(t in f"{o.path} {o.summary}".lower() for t in terms)]


def find(all_ops: list[Op], method: str, path: str, version: str | None = None) -> Op:
    """The operation for METHOD and a site-relative PATH (the newest version unless `version` is given)."""
    path = path.strip("/")
    hits = [
        o
        for o in all_ops
        if o.method == method.upper() and o.path == path and (version is None or o.version == version)
    ]
    if not hits:
        near = [o.label() for o in all_ops if o.path == path or path in o.path][:8]
        raise KeyError(
            f"no {method.upper()} {path!r} in this controller's API"
            + ("; did you mean:\n  " + "\n  ".join(near) if near else "")
        )
    return max(hits, key=lambda o: o.version)


def describe(spec: dict, node: dict | None, depth: int = 3, indent: int = 0) -> list[str]:
    """The fields of a schema as indented `name: type description` lines."""
    lines = []
    node = resolve(spec, node or {})
    for name, raw in (node.get("properties") or {}).items():
        s = resolve(spec, raw)
        t = s.get("type") or "object"
        desc = re.sub(r"\s+", " ", (s.get("description") or raw.get("description") or "")).strip()[:140]
        lines.append(f"{'  ' * indent}{name}: {t}{' - ' + desc if desc else ''}")
        if depth > 1:
            inner = resolve(spec, s["items"]) if t == "array" and "items" in s else s
            if inner.get("properties"):
                lines += describe(spec, inner, depth - 1, indent + 1)
    return lines


def unknown_keys(spec: dict, op: Op, body: dict) -> list[str]:
    """Top-level keys of `body` that the operation's request schema does not have (typos), empty when it declares no fields."""
    allowed = set(resolve(spec, op.body or {}).get("properties") or {})
    return sorted(set(body) - allowed) if allowed and isinstance(body, dict) else []
