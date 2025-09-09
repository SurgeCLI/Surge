import os
import subprocess
import typer
from pathlib import Path
from rich import print
from typing import Annotated

from config.config import load_config_file

try:
    config = load_config_file()
except Exception:
    print(f'Check that a config.toml file is populated here: {repr(Path('config/toml'))}')
    print(f'Common Problems: an API key is not set, or is invalid.')

app = typer.Typer(
    help="Surge - A DevOps CLI Tool For System Monitoring and Production Reliability"
)


def run_cmd(cmd: str) -> str:
    """
    Helper function to abstract lengthy subprocess command implementation :D
    """

    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    ).stdout.strip()


def get_load() -> tuple[float] | int:
    """
    Utilizes Linux uptime for system load metrics and to determine core utilization
    """

    uptime = run_cmd("uptime | awk -F'average:' '{print $2}'")
    averages = [float(x.replace(",", "")) for x in uptime.split()]
    cores = float(run_cmd("nproc"))

    return averages, cores


def get_cpu() -> tuple[float]:
    """
    Uses top to find CPU utilization grouped by user, system, and idle percents.
    """
    top = run_cmd('top -bn1 | grep "Cpu(s)"').split(",")
    user = top[0].split()[-2]
    system = top[1].split()[0]
    idle = top[3].split()[0]

    return user, system, idle


def get_memory() -> tuple[float]:
    """
    Returns remaining memory by group using free.
    """
    free = run_cmd("free -m | grep Mem").split()
    total, used, free_mem = free[1], free[2], free[3]

    return total, used, free_mem


def get_disk() -> tuple[float]:
    """
    Returns disk usage with df.
    """
    df = run_cmd("df -h / | tail -1").split()
    size, used, available, percent = df[1], df[2], df[3], df[4]

    return size, used, available, percent


def get_io() -> tuple[float]:
    # TODO: implement with iostat
    pass


@app.command()
def monitor(
    load: Annotated[
        bool, typer.Option("-l", "--load", help="Show system load averages")
    ] = True,
    cpu: Annotated[bool, typer.Option("-c", "--cpu", help="Show CPU usage")] = True,
    ram: Annotated[bool, typer.Option("-r", "--ram", help="Show RAM usage")] = True,
    disk: Annotated[bool, typer.Option("-d", "--disk", help="Show Disk usage")] = True,
    io: Annotated[
        bool, typer.Option("-o", "--io", help="Show Disk I/O statistics")
    ] = True,
    interval: Annotated[
        int, typer.Option("-i", "--interval", help="Polling interval in seconds")
    ] = 5,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="Show detailed system metrics")
    ] = False,
):
    if interval <= 0:
        raise typer.BadParameter("Interval must be a positive integer.")

    """
    Summary of all system metrics, including utilization of CPU, Memory, Network, and I/O.
    """

    # TODO: Add category specific metrics using subprocess, psutil, or similar
    # General structure example:
    # if cpu:
    #   ...
    #   if verbose:
    #       ...

    if load:
        averages, cores = get_load()

        print("\n[bold]System Load Averages[/bold]")
        print("---------------------")

        if not verbose:
            print(f"Load avg (1m): {averages[0]}")
            print(f"Load avg (5m): {averages[1]}")
            print(f"Load avg (15m): {averages[2]}")
        else:
            print(
                f"Load avg (1m): {averages[0]:.2f} ({averages[0] / cores:.3f} per CPU)"
            )
            print(
                f"Load avg (5m): {averages[1]:.2f} ({averages[1] / cores:.3f} per CPU)"
            )
            print(
                f"Load avg (15m): {averages[2]:.2f} ({averages[2] / cores:.3f} per CPU)"
            )

    if cpu:
        user, system, idle = get_cpu()
        print("\n[bold]CPU Utilization[/bold]")
        print("---------------------")
        print(f"User: {user}% | System: {system}% | Idle: {idle}%")

    if ram:
        total, used, free = get_memory()
        print("\n[bold]Memory Usage (MB)[/bold]")
        print("---------------------")
        print(f"Total: {total} | Used: {used} | Free: {free}")

    if disk:
        size, used, available, percent = get_disk()
        print("\n[bold]Disk Usage[/bold]")
        print("---------------------")
        print(
            f"Size: {size} | Used: {used} | Available: {available} | Usage: {percent}"
        )


@app.command("network")
def network(
    url: Annotated[
        str | None,
        typer.Option("-u", "--url", help="HTTP URL to test (curl)", show_default=False),
    ] = None,
    host: Annotated[
        str | None,
        typer.Option(
            "-h", "--host", help="Host/IP for ping and traceroute", show_default=False
        ),
    ] = None,
    domain: Annotated[
        str | None,
        typer.Option(
            "-d", "--domain", help="Domain for DNS lookup", show_default=False
        ),
    ] = None,
    requests: Annotated[
        int, typer.Option("-n", "--count", help="Number of ICMP echo requests")
    ] = 5,
    dtype: Annotated[
        str,
        typer.Option("-t", "--type", help="DNS record type (A, AAAA, MX, TXT, etc.)"),
    ] = "A",
    sockets: Annotated[
        bool, typer.Option("--sockets", help="Show socket information (ss)")
    ] = False,
    no_trace: Annotated[
        bool, typer.Option("--no-trace", help="Skip traceroute/mtr when --host is set")
    ] = False,
):
    """
    Flexible network diagnostics: run only what you request.
    Provide one or more of: --host, --url, --domain, --sockets.
    """

    def header(title: str):
        print(f"\n[bold]{title}[/bold]")
        print("-" * len(title))

    def warn(msg: str):
        print(f"[warn] {msg}")

    def normalize_url(u: str) -> str:
        return u if u.startswith(("http://", "https://")) else f"http://{u}"

    def curl_brief(u: str) -> str:
        fmt = "HTTP %{http_code} | total %{time_total}s | connect %{time_connect}s | ttfb %{time_starttransfer}s\n"
        return run_cmd(f'curl -s -o /dev/null -w "{fmt}" {u}')

    def summarize_ping(out: str) -> str:
        lines = out.splitlines()
        sent = loss = avg = None
        for ln in lines:
            if "packets transmitted" in ln and "packet loss" in ln:
                parts = ln.replace(",", "").split()
                try:
                    sent = int(parts[0])
                    loss = parts[6]
                except Exception:
                    pass
            if "rtt min/avg/max" in ln or "round-trip min/avg/max" in ln:
                try:
                    avg = ln.split("=")[1].split("/")[1].strip()
                except Exception:
                    pass
        bits = []

        if sent is not None:
            bits.append(f"sent={sent}")
        if loss is not None:
            bits.append(f"loss={loss}")
        if avg is not None:
            bits.append(f"avg_rtt_ms={avg}")

        return " | ".join(bits) if bits else (out.strip()[:200] if out else "")

    def summarize_trace(out: str, max_lines: int = 12) -> str:
        lines = [line for line in out.splitlines() if line.strip()]
        if len(lines) <= max_lines:
            return out
        return "\n".join(lines[:6] + ["..."] + lines[-6:])

    # --- validate empty values FIRST ---
    if host is not None and not str(host).strip():
        warn("--host was provided but empty")
        raise typer.Exit(code=2)
    if url is not None and not str(url).strip():
        warn("--url was provided but empty")
        raise typer.Exit(code=2)
    if domain is not None and not str(domain).strip():
        warn("--domain was provided but empty")
        raise typer.Exit(code=2)

    # --- then require at least one section ---
    if not any([host, url, domain, sockets]):
        warn(
            "Nothing to do. Provide at least one of: --host, --url, --domain, --sockets"
        )
        raise typer.Exit(code=1)

    # ---- ping / traceroute (or mtr -r fallback) ----
    if host:
        header("Ping")
        ping_out = run_cmd(f"ping -c {requests} {host}")
        print(
            summarize_ping(ping_out)
            if ping_out
            else "[warn] ping not available or produced no output"
        )

        if not no_trace:
            header("Traceroute")
            trace_out = run_cmd(f"traceroute {host}") or run_cmd(f"mtr -r {host}")
            print(
                summarize_trace(trace_out)
                if trace_out
                else "[warn] traceroute/mtr not available or produced no output"
            )

    # ---- http (curl) ----
    if url:
        header("HTTP (curl)")
        u = normalize_url(url)
        print(curl_brief(u))
        headers = run_cmd(f"curl -s -I {u}")
        print(
            headers.strip()
            if headers
            else "[warn] curl not available or produced no output"
        )

    # ---- dns ----
    if domain:
        header("DNS")
        dns_out = run_cmd(f"dig +short {domain} {dtype}") or run_cmd(
            f"nslookup -type={dtype} {domain}"
        )
        print(
            dns_out.strip()
            if dns_out
            else "[warn] dig/nslookup not available or produced no output"
        )

    # ---- sockets (ss) ----
    if sockets:
        header("Sockets (ss)")
        ss_out = run_cmd("ss -tulwn")
        print(ss_out or "[warn] ss not available or produced no output")


@app.command()
def ai(
    format: Annotated[
        str, typer.Option("--format", "-f", help="Data format: raw/structured/hybrid")
    ] = "hybrid",
    verbosity: Annotated[
        str,
        typer.Option("--verbosity", "-v", help="Output detail: concise/normal/hybrid"),
    ] = "normal",
    auto_fix: Annotated[
        bool, typer.Option("--auto-fix", help="Auto-execute safe fixes")
    ] = False,
):
    """
    Using Gemini 2.5 Flash for now for simple AI suggestions and reading through machine metrics
    giving suggest fixes upon user confirmations
    """

    if not os.getenv("GEMINI_API_KEY"):
        print("[red]Error: GEMINI_API_KEY is empty[/red]")
        print('Set it with: export GEMINI_API_KEY="your api key"')
        return

    try:
        from ai.ai_monitor import run_ai_monitor

        run_ai_monitor(data_format=format, verbosity=verbosity, auto_fix=auto_fix)
    except ImportError:
        print("[red]AI packages not installed[/red]")
        print("Run: pip install langchain langchain-google-genai rich")
    except Exception as err:
        print(f"[red]Error: {str(err)}[/red]")


if __name__ == "__main__":
    app()
