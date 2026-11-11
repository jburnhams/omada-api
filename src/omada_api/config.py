"""The login: ~/.omada.cfg, the same file and format `tplink-omada-client`'s own `omada` command uses, so the two share one login."""

import getpass
import os
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

PATH = Path(os.environ.get("OMADA_CFG", Path.home() / ".omada.cfg"))
PREFIX = "controller:"


@dataclass
class Target:
    name: str
    url: str
    username: str
    password: str
    site: str
    verify_ssl: bool


def _read() -> ConfigParser:
    cp = ConfigParser()
    if PATH.exists():
        cp.read(PATH)
    return cp


def names() -> list[str]:
    return [s[len(PREFIX) :] for s in _read().sections() if s.startswith(PREFIX)]


def load(name: str | None = None) -> Target:
    cp = _read()
    name = name or (cp["cli"].get("default_target") if "cli" in cp else None) or (names() or [None])[0]
    if not name or f"{PREFIX}{name}" not in cp:
        raise SystemExit(
            f"no saved login{f' called {name!r}' if name else ''}: run `omada-api login NAME --url URL --username USER --site SITE`"
        )
    s = cp[f"{PREFIX}{name}"]
    return Target(
        name, s["url"], s["username"], s["password"], s["site"], s.get("verify_ssl", "True").lower() == "true"
    )


def save(name: str, url: str, username: str, password: str, site: str, verify_ssl: bool, default: bool = True) -> None:
    """Write the login, mode 600 (the file holds the password in plain text)."""
    cp = _read()
    cp[f"{PREFIX}{name}"] = {
        "url": url,
        "username": username,
        "password": password,
        "site": site,
        "verify_ssl": str(verify_ssl),
    }
    if default:
        cp["cli"] = {"default_target": name}
    old = os.umask(0o077)
    try:
        with open(PATH, "w") as f:
            cp.write(f)
    finally:
        os.umask(old)
    os.chmod(PATH, 0o600)


def prompt_password() -> str:
    return getpass.getpass("Password: ")
