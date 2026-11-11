# omada-api

A small command-line tool for the [TP-Link Omada](https://www.tp-link.com/uk/omada-sdn/) controller API. It reads the controller's own API description, so it can find and call any site-level endpoint, including the settings community clients leave out (WAN, DNS proxy, LAN DNS names, remote logging, and so on). Writes only show what they would send unless you add `--yes`.

It is built on [`tplink-omada-client`](https://pypi.org/project/tplink-omada-client/), which does the login and session handling, so it works with a controller username and password and needs no Open API app.

Tested against a software controller 6.3.0.111 managing an ER605 v2. Treat it as early (0.1): the controller's API is large and mostly undocumented in practice.

## Install

```
pipx install git+https://github.com/jburnhams/omada-api     # or: uv sync in a clone, then uv run omada-api
omada-api login home --url https://CONTROLLER:8043 --username USER --site "Site name"     # asks for the password
```
The login is saved in `~/.omada.cfg`, mode 600 (plain text, the same file and format `tplink-omada-client`'s `omada` command uses, so both share it). Use a dedicated controller user with the least role you need (Viewer to read, Editor to change). Most controllers have a self-signed certificate, so the certificate is not checked unless you pass `--verify-ssl` to `login`.

## Use

```
omada-api find remote logging            # search endpoints (site level) by words in the path or summary
omada-api schema patch remote-logging    # what it takes: parameters and body fields
omada-api get remote-logging             # GET (paged lists are read to the end)
omada-api patch remote-logging --json '{"remoteLog": {"enable": true, "host": "10.0.0.5", "port": 5514}}'          # dry run
omada-api patch remote-logging --json '...' --yes                                                                    # sends it
omada-api delete 'setting/lan/dns/{dnsId}' -p dnsId=abc123 --yes
```
Paths are relative to the site (`remote-logging`, not `/openapi/v1/<id>/sites/<id>/remote-logging`); the newest API version is used unless `--version v1` is given. Output is JSON with secret-looking values (`password`, `psk`, `token`, ...) replaced by `***`. A body with a field the endpoint's schema does not have is refused (a typo guard; `--force` overrides). The controller's API description is cached for a week under `~/.cache/omada-api` (`--refresh-spec` to refetch). Several logins: `-t NAME`.

See [docs/recipes.md](docs/recipes.md) for worked examples (DNS upstreams, DHCP reservations, static names, remote logging) and the quirks found on the way.

## Syslog receiver

`omada-api syslog` is a small receiver for the router's syslog: it listens on a UDP port (default 5514, no root needed), keeps one file a day under `~/.local/state/router-logs` (`<time> <sender> <message>`), accepts only LAN senders and deletes files older than `--keep-days` (60). It needs no login. Run it as a service ([contrib/omada-syslog.service](contrib/omada-syslog.service)), open the port in your firewall, then point the site at it:

```
omada-api patch remote-logging --json '{"remoteLog": {"enable": true, "host": "<this machine>", "port": 5514, "moreClientLog": false, "resource": 0}}' --yes
```
It is plain, unauthenticated UDP: keep it on the LAN.

## Notes

- Writes change a live network. A wrong WAN setting can cut the internet; check the result of every write, and keep a way to undo it.
- It reaches into two private attributes of `tplink-omada-client`'s session (`_api`, `_site_id`), which is why that dependency is pinned to `>=1.5.13,<1.6`.
- Not affiliated with TP-Link.

## Development

```
uv sync && scripts/check          # lockfile, ruff, pyright, ty, then the tests with coverage (`uv run pytest` for the tests alone)
```
MIT licensed.
