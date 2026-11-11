"""A small syslog receiver (UDP): keeps what the router, switches and access points send as one file per day.

Point the site's remote logging at it (`omada-api patch remote-logging ...`, see docs/recipes.md). Each line is
`<local time> <sender address> <the message as sent>` in <dir>/YYYY-MM-DD.log; files older than `keep_days` are deleted when the day changes.
Only private (LAN) sender addresses are accepted. Plain UDP syslog is unauthenticated and unencrypted: keep it on the LAN.
"""

import datetime as dt
import ipaddress
import socket
import sys
import threading
from pathlib import Path


def accept(addr: str) -> bool:
    return ipaddress.ip_address(addr).is_private


def prune(directory: Path, keep_days: int, today: dt.date) -> list[str]:
    """Delete day files older than `keep_days`; returns the names removed. Other files are left alone."""
    gone = []
    for f in directory.glob("????-??-??.log"):
        try:
            day = dt.date.fromisoformat(f.stem)
        except ValueError:
            continue
        if (today - day).days > keep_days:
            f.unlink()
            gone.append(f.name)
    return gone


def line(now: dt.datetime, addr: str, data: bytes) -> str:
    text = data.decode("utf-8", errors="replace").replace("\r", " ").replace("\n", " ").strip()
    return f"{now:%Y-%m-%d %H:%M:%S} {addr} {text}\n"


def serve(
    port: int = 5514,
    directory: str | Path = "~/.local/state/router-logs",
    keep_days: int = 60,
    stop: threading.Event | None = None,
    bind: str = "0.0.0.0",  # noqa: S104  (the router sends from the LAN; the receiver must listen on every interface)
    ready: threading.Event | None = None,
) -> None:
    """Receive until `stop` is set (never, by default). `ready` is set once the socket is bound."""
    d = Path(directory).expanduser()
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    stop = stop or threading.Event()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((bind, port))
    s.settimeout(1)
    print(f"omada-api syslog: UDP {port} -> {d}", flush=True)
    if ready:
        ready.set()
    day, fh, dropped = None, None, 0
    try:
        while not stop.is_set():
            try:
                data, (addr, _) = s.recvfrom(65535)
            except TimeoutError:
                data = None
            now = dt.datetime.now()
            if now.date() != day:  # a new day: new file, and delete the old ones
                if fh:
                    fh.close()
                day = now.date()
                fh = open(d / f"{day:%Y-%m-%d}.log", "a", buffering=1)
                for name in prune(d, keep_days, day):
                    print(f"omada-api syslog: removed {name}", flush=True)
            if data is None:
                continue
            if not accept(addr):
                dropped += 1
                if dropped in (1, 100, 10000):
                    print(
                        f"omada-api syslog: ignored a message from non-LAN address {addr} ({dropped} so far)",
                        file=sys.stderr,
                        flush=True,
                    )
                continue
            if fh is None:  # cannot happen: the first pass opens today's file above; this narrows the type
                continue
            fh.write(line(now, addr, data))
    finally:
        s.close()
        if fh:
            fh.close()
