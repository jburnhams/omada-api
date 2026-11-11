"""omada-api: find, read and call endpoints of the Omada controller API. Writes only show what they would send unless given --yes."""

import argparse
import asyncio
import json
import re

from . import config
from . import spec as specmod
from . import syslog as syslogmod
from .client import Session, pretty
from .mask import mask


def _params(items):
    out = {}
    for item in items or []:
        k, _, v = item.partition("=")
        if not k or not _:
            raise SystemExit(f"parameter {item!r} must look like name=value")
        out[k] = v
    return out


def _fill(path: str, params: dict) -> str:
    """Fill {placeholders} in the path from -p name=value (and take those out of the query parameters)."""

    def sub(m):
        if m.group(1) not in params:
            raise SystemExit(f"the path needs a value for {{{m.group(1)}}}: add -p {m.group(1)}=...")
        return str(params.pop(m.group(1)))

    return re.sub(r"\{(\w+)\}", sub, path)


def _load(args):
    target = config.load(args.target)
    return target, specmod.fetch(target.url, target.verify_ssl, refresh=args.refresh_spec)


def cmd_login(a):
    config.save(a.name, a.url, a.username, config.prompt_password(), a.site, a.verify_ssl, default=True)
    print(f"saved login {a.name!r} in {config.PATH} (mode 600)")


def cmd_targets(a):
    for n in config.names():
        t = config.load(n)
        print(f"{n}  {t.url}  site {t.site}  user {t.username}")


def cmd_find(a):
    _, sp = _load(a)
    found = specmod.search(specmod.ops(sp), a.terms)
    for o in found[: a.limit]:
        print(f"{o.label():<70} {o.summary}")
    if len(found) > a.limit:
        print(f"... {len(found) - a.limit} more (add terms or --limit)")
    if not found:
        print("nothing found")


def cmd_schema(a):
    _, sp = _load(a)
    op = specmod.find(specmod.ops(sp), a.method, a.path, a.version)
    print(f"{op.method} /openapi/{op.version}/<omadacId>/sites/<siteId>/{op.path}\n{op.summary}")
    if op.params:
        print("\nparameters:")
        for p in op.params:
            print(
                f"  {p['name']} ({p['in']}{', required' if p['required'] else ''}): {p['type']} {p['description'][:100]}"
            )
    if op.body:
        print("\nrequest body (JSON):")
        print("\n".join("  " + l for l in specmod.describe(sp, op.body)))


def cmd_syslog(a):
    syslogmod.serve(a.port, a.dir, a.keep_days)


def cmd_call(a):
    target, sp = _load(a)
    op = specmod.find(specmod.ops(sp), a.method, a.path, a.version)
    params = _params(a.param)
    path = _fill(op.path, params)
    body = None
    if a.json is not None or a.json_file:
        body = json.loads(a.json if a.json is not None else open(a.json_file).read())
        bad = specmod.unknown_keys(sp, op, body)
        if bad and not a.force:
            raise SystemExit(
                f"{op.method} {op.path} has no field(s) {bad}; see `omada-api schema {op.method} {op.path}` (--force sends anyway)"
            )
    if op.method != "GET" and not a.yes:
        print(f"DRY RUN, nothing sent: {op.method} /openapi/{op.version}/<omadacId>/sites/{target.site}/{path}")
        if params:
            print("query:", pretty(params))
        if body is not None:
            print("body:", pretty(mask(body)))
        print("add --yes to send it")
        return

    async def go():
        async with Session(target) as s:
            return await s.call(op, path, params, body)

    try:
        result = asyncio.run(go())
    except Exception as e:  # the controller's errors come as exceptions with its message
        raise SystemExit(f"{type(e).__name__}: {e}") from e
    print(pretty(mask(result)))


def build_parser():
    ap = argparse.ArgumentParser(prog="omada-api", description=__doc__)
    ap.add_argument("-t", "--target", help="saved login to use (default: the default one)")
    ap.add_argument(
        "--refresh-spec",
        action="store_true",
        help="fetch the controller's API description again instead of using the weekly cache",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("login", help="save a login (asks for the password; stored mode 600 in ~/.omada.cfg)")
    p.add_argument("name")
    p.add_argument("--url", required=True)
    p.add_argument("--username", required=True)
    p.add_argument("--site", required=True)
    p.add_argument(
        "--verify-ssl",
        action="store_true",
        help="check the controller's certificate (off by default: most are self-signed)",
    )
    p.set_defaults(fn=cmd_login)
    sub.add_parser("targets", help="list saved logins").set_defaults(fn=cmd_targets)
    p = sub.add_parser("find", help="search endpoints (site-level) by words in the path or summary")
    p.add_argument("terms", nargs="+")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(fn=cmd_find)
    p = sub.add_parser("schema", help="what an endpoint takes: parameters and request body fields")
    p.add_argument("method")
    p.add_argument("path")
    p.add_argument("--version")
    p.set_defaults(fn=cmd_schema)
    p = sub.add_parser(
        "syslog",
        help="receive syslog from the router, switches and APs into one file per day (run it as a service; needs no login)",
    )
    p.add_argument("--port", type=int, default=5514, help="UDP port (default 5514, unprivileged)")
    p.add_argument("--dir", default="~/.local/state/router-logs")
    p.add_argument("--keep-days", type=int, default=60)
    p.set_defaults(fn=cmd_syslog)
    for m in ("get", "post", "put", "patch", "delete"):
        p = sub.add_parser(m, help=f"{m.upper()} a site-relative path, e.g. `{m} remote-logging`")
        p.add_argument("path")
        p.add_argument(
            "-p",
            "--param",
            action="append",
            help="name=value: a query parameter, or the value of a {placeholder} in the path",
        )
        p.add_argument("--version", help="v1, v2 or v3 (default: the newest the controller has for that path)")
        if m != "get":
            p.add_argument("--json", help="request body as JSON")
            p.add_argument("--json-file", help="request body from a file")
            p.add_argument(
                "--yes", action="store_true", help="actually send it (without this, only show what would be sent)"
            )
            p.add_argument(
                "--force", action="store_true", help="send even if the body has fields the schema does not list"
            )
        else:
            p.set_defaults(json=None, json_file=None, yes=True, force=False)
        p.set_defaults(fn=cmd_call, method=m)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
