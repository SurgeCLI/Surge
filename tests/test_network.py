import click
from typer.testing import CliRunner

import cli.app as appmod

runner = CliRunner()


def run_cmd_spy_factory():
    calls = []

    def _spy(cmd: str):
        calls.append(cmd)
        if cmd.startswith("ping "):
            return "5 packets transmitted, 5 received, 0% packet loss\nrtt min/avg/max/mdev = 10/11/12/0.3 ms"
        if cmd.startswith("traceroute "):
            return "traceroute to host\n1 a\n2 b\n3 c"
        if cmd.startswith("mtr -r "):
            return "Start: mtr report\n1. a\n2. b"
        if cmd.startswith("curl -s -o /dev/null"):
            return "HTTP 200 | total 0.123s | connect 0.010s | ttfb 0.050s\n"
        if cmd.startswith("curl -s -I "):
            return "HTTP/1.1 200 OK\nServer: test\n"
        if cmd.startswith("dig +short "):
            return "93.184.216.34\n"
        if cmd.startswith("nslookup "):
            return "Server: 8.8.8.8\nName: example.com\nAddress: 93.184.216.34\n"
        if cmd.startswith("ss -tulwn"):
            return "Netid State  Local Address:Port  Peer Address:Port\n"
        return ""

    _spy.calls = calls
    return _spy


def test_network_runs_all_sections(monkeypatch, capsys):
    spy = run_cmd_spy_factory()
    monkeypatch.setattr(appmod, "run_cmd", spy)
    appmod.network(
        url="http://example.com", host="1.1.1.1", domain="example.com", sockets=True
    )
    out = capsys.readouterr().out
    assert "Ping" in out
    assert "Traceroute" in out
    assert "HTTP (curl)" in out
    assert "DNS" in out
    assert "Sockets (ss)" in out
    assert "HTTP 200 | total" in out


def test_empty_flags_fail_fast(monkeypatch):
    spy = run_cmd_spy_factory()
    monkeypatch.setattr(appmod, "run_cmd", spy)
    # url vacío debe fallar con exit_code 2 (click.exceptions.Exit)
    try:
        appmod.network(url="", host=None, domain=None, sockets=False)
        assert False, "Expected click.exceptions.Exit"
    except click.exceptions.Exit as e:
        assert e.exit_code == 2


def test_traceroute_then_mtr_fallback(monkeypatch, capsys):
    def run_cmd_fake(cmd: str):
        if cmd.startswith("ping "):
            return "5 packets transmitted, 5 received, 0% packet loss\nrtt min/avg/max/mdev = 10/11/12/0.3 ms"
        if cmd.startswith("traceroute "):
            return ""  # force fallback
        if cmd.startswith("mtr -r "):
            return "Start: mtr report\n1. a\n2. b"
        return ""

    monkeypatch.setattr(appmod, "run_cmd", run_cmd_fake)
    appmod.network(host="1.1.1.1")
    out = capsys.readouterr().out
    assert "mtr report" in out


def test_cli_invocation_smoke(monkeypatch):
    spy = run_cmd_spy_factory()
    monkeypatch.setattr(appmod, "run_cmd", spy)
    result = runner.invoke(
        appmod.app,
        [
            "network",
            "-u",
            "http://example.com",
            "-h",
            "1.1.1.1",
            "-d",
            "example.com",
            "--sockets",
        ],
    )
    assert result.exit_code == 0
    assert "HTTP (curl)" in result.stdout
