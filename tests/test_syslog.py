import datetime as dt
import socket
import threading
import time

from omada_api import cli, syslog


def test_a_message_becomes_one_line_with_time_and_sender():
    now = dt.datetime(2026, 10, 25, 9, 30, 5)
    assert syslog.line(now, "192.168.0.1", b"<134>Router: up\r\nsecond line\n") == "2026-10-25 09:30:05 192.168.0.1 <134>Router: up  second line\n"
    assert "�" in syslog.line(now, "x", b"bad \xff byte")                      # not valid UTF-8: kept, with a replacement character


def test_only_private_senders_are_accepted():
    assert syslog.accept("192.168.0.1") and syslog.accept("10.1.2.3") and syslog.accept("127.0.0.1")
    assert not syslog.accept("8.8.8.8")


def test_prune_removes_only_old_day_files(tmp_path):
    for n in ("2026-01-01.log", "2026-10-20.log", "2026-10-25.log", "notes.txt", "x-y-z.log"):
        (tmp_path / n).write_text("")
    gone = syslog.prune(tmp_path, 60, dt.date(2026, 10, 25))
    assert gone == ["2026-01-01.log"] and sorted(p.name for p in tmp_path.iterdir()) == ["2026-10-20.log", "2026-10-25.log", "notes.txt", "x-y-z.log"]


def test_the_receiver_writes_what_it_gets_to_todays_file(tmp_path):
    stop, ready = threading.Event(), threading.Event()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    t = threading.Thread(target=syslog.serve, kwargs=dict(port=port, directory=tmp_path, keep_days=60, stop=stop, bind="127.0.0.1", ready=ready))
    t.start()
    try:
        assert ready.wait(5)
        c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); c.sendto(b"<14>hello from the router", ("127.0.0.1", port)); c.close()
        f = tmp_path / f"{dt.date.today():%Y-%m-%d}.log"
        for _ in range(50):
            if f.exists() and "hello" in f.read_text():
                break
            time.sleep(0.1)
        assert f.read_text().endswith("127.0.0.1 <14>hello from the router\n")
    finally:
        stop.set(); t.join(5)


def test_the_syslog_command_needs_no_login(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli.syslogmod, "serve", lambda port, d, keep: seen.update(port=port, dir=d, keep=keep))
    monkeypatch.setattr(cli.config, "load", lambda *a: (_ for _ in ()).throw(AssertionError("no login should be read")))
    cli.main(["syslog", "--port", "6000", "--keep-days", "7"])
    assert seen == dict(port=6000, dir="~/.local/state/router-logs", keep=7)
