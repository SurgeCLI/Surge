import os
import subprocess
import typer

from pathlib import Path

from rich import box
from rich import print
from rich.columns import Columns
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from typing import Annotated

from config import config
from .merge import merge

from .prometheus import query_prometheus_metrics

try:
    config_data = config.load_config_file(Path('config/config.toml'))
except Exception:
    config_data = {}
    print(f"Check that a config.toml file is populated here: '{Path.home()}'")
    print('Common Problems: an API key is not set, or is invalid.')

app = typer.Typer(help='Surge - A DevOps CLI Tool For System Monitoring and Production Reliability')

console_config = config_data.get('console', {})

console = Console(
    force_terminal=console_config.get('force_color', True),
)

# Merges app.command() decorator w/ transposed merge() decorator
cmd = app.command


def app_command_with_merge(*args, **kwargs):
    decorator = cmd(*args, **kwargs)

    def wrapper(func):
        return decorator(merge()(func))

    return wrapper


app.command = app_command_with_merge


# In Prometheus/PromQL version, subprocess isn't required for system metrics


def run_cmd(cmd: str) -> str:
    """
    Helper function to abstract lengthy subprocess command implementation :D
    """

    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def get_load() -> tuple[list[float], int]:
    """
    Returns 1 minute, 5 minute, and 15 minute load averages and CPU core count
    """

    load_query = 'node_load1 or node_load5 or node_load15'
    results = query_prometheus_metrics(load_query)

    loads = {
        'node_load1': 0.0,
        'node_load5': 0.0,
        'node_load15': 0.0,
    }

    for item in results:
        name = item['metric'].get('__name__')
        value = float(item['value'][1])
        if name in loads:
            loads[name] = value

    cores_query = 'count(node_cpu_seconds_total{mode="idle"})'
    cores_result = query_prometheus_metrics(cores_query)
    cores = int(float(cores_result[0]['value'][1])) if cores_result else 1

    return [loads['node_load1'], loads['node_load5'], loads['node_load15']], cores


def get_cpu() -> tuple[float, float, float]:
    """
    Returns cpu percent utilization for user, system, and idle
    """

    query = """
        avg by (mode) (
    rate(node_cpu_seconds_total{mode=~"user|system|idle"}[5m])
    ) * 100
    """
    results = query_prometheus_metrics(query)

    cpu = {
        'user': 0.0,
        'system': 0.0,
        'idle': 0.0,
    }

    for item in results:
        mode = item['metric'].get('mode')
        value = float(item['value'][1])
        if mode in cpu:
            cpu[mode] = value

    return cpu['user'], cpu['system'], cpu['idle']


def get_memory() -> tuple[float, float, float]:
    """
    Returns memory usage in MB: total, used, and free
    """
    total_res = query_prometheus_metrics('node_memory_MemTotal_bytes')
    avail_res = query_prometheus_metrics('node_memory_MemAvailable_bytes')

    total_mb = float(total_res[0]['value'][1]) / 1024 / 1024 if total_res else 0.0
    free_mb = float(avail_res[0]['value'][1]) / 1024 / 1024 if avail_res else 0.0
    used_mb = max(total_mb - free_mb, 0.0)

    return total_mb, used_mb, free_mb


def get_disk() -> tuple[float, float, float, float]:
    """
    Returns disk usage in GB: size, used, available, and percent
    """

    size_query = """
        sum(
            max by (device) (
                node_filesystem_size_bytes{
                fstype!~"tmpfs|overlay|squashfs"
                }
            )
        )
    """

    avail_query = """
        sum(
            max by (device) (
                node_filesystem_avail_bytes{
                fstype!~"tmpfs|overlay|squashfs"
                }
            )
        )
    """

    size_res = query_prometheus_metrics(size_query)
    avail_res = query_prometheus_metrics(avail_query)

    size_gb = sum(float(item['value'][1]) for item in size_res) / 1024**3 if size_res else 0.0
    free_gb = sum(float(item['value'][1]) for item in avail_res) / 1024**3 if avail_res else 0.0
    used_gb = max(size_gb - free_gb, 0.0)
    percent = (used_gb / size_gb * 100) if size_gb else 0.0

    return size_gb, used_gb, free_gb, percent


def get_top_processes(n: int = 5):
    def fetch_top(sort_by: str):
        result = run_cmd(f'ps aux --sort=-{sort_by} | head -n {n + 1}').splitlines()
        headers = result[0].split()
        ps = []
        for line in result[1:]:
            parts = line.split(None, len(headers) - 1)
            ps.append(dict(zip(headers, parts)))
        return ps

    top_cpu = fetch_top('%cpu')
    top_mem = fetch_top('%mem')
    return top_cpu, top_mem


# Currently facing issues with Windows (+Maybe Mac?) Docker Desktop
def get_top_containers(n: int = 5):
    cpu_query = f"""
        topk(
            {n},
            sum by (container) (
                rate(container_cpu_usage_seconds_total{{container!="",container!="POD"}}[5m])
            )
        )
    """
    results = query_prometheus_metrics(cpu_query)

    containers = []
    for item in results:
        name = item['metric'].get('container', 'unknown')
        cpu = float(item['value'][1])
        containers.append((name, cpu))

    return containers


def create_table(title: str, title_style: str = 'bold cyan', header_style: str = 'bold cyan') -> Table:
    return Table(
        title=title,
        title_style=title_style,
        header_style=header_style,
        expand=False,
        pad_edge=False,
        show_lines=True,
        box=box.ROUNDED,
        border_style='grey37',
        style='grey50',
    )


@app.command()
def monitor(
    load: Annotated[bool, typer.Option('-l', '--load', help='Show system load averages')] = True,
    cpu: Annotated[bool, typer.Option('-c', '--cpu', help='Show CPU usage')] = True,
    ram: Annotated[bool, typer.Option('-r', '--ram', help='Show RAM usage')] = True,
    disk: Annotated[bool, typer.Option('-d', '--disk', help='Show Disk usage')] = True,
    process: Annotated[int, typer.Option('-p', '--ps', '--process', help='Show the top n processes by CPU and RAM')] = 5,
    containers: Annotated[bool, typer.Option('-o', '--cont', '--containers', help='Show top n containers by CPU')] = 5,
    verbose: Annotated[bool, typer.Option('-v', '--verbose', help='Show detailed system metrics')] = False,
):
    """
    Summary of all system metrics, including utilization of CPU, Memory, Network, and I/O.
    """

    panels = []

    if load:
        averages, cores = get_load()

        table = create_table('')

        table.add_column('Interval', justify='center')
        table.add_column('Load', justify='center')
        if verbose:
            table.add_column('Per CPU Util', justify='center')
            table.add_column('Status', justify='center')

        intervals = ['1 Minute', '5 Minutes', '15 Minutes']

        for i, interval in enumerate(intervals):
            load_val = averages[i]
            if verbose:
                per_cpu = load_val / cores

                if per_cpu < 0.7:
                    status = '[green]OK[/green]'
                elif per_cpu < 1.0:
                    status = '[yellow]High System Load[/yellow]'
                else:
                    status = '[bold red]System Likely Overloaded[/bold red]'

                table.add_row(interval, f'{load_val:.2f}', f'{per_cpu:.3f}', status)
            else:
                table.add_row(interval, f'{load_val:.2f}')

        panels.append(
            Panel(
                table,
                title='[bold cyan]System Load Averages[/bold cyan]',
                border_style='cyan',
            )
        )

    if cpu:
        user, system, idle = get_cpu()
        table = create_table('')
        table.add_column('User (%)', justify='center')
        table.add_column('System (%)', justify='center')
        table.add_column('Idle (%)', justify='center')
        table.add_column('Status', justify='center')

        used = float(user) + float(system)
        total = used + float(idle)
        usage = (used / total) * 100

        if usage >= 85:
            status = '[red]Critical CPU Usage[/red]'
        elif usage >= 70:
            status = '[yellow]High CPU Usage[/yellow]'
        else:
            status = '[green]OK[/green]'

        table.add_row(f'{user:.2f}', f'{system:.2f}', f'{idle:.2f}', status)
        panels.append(Panel(table, title='[bold cyan]CPU Usage[/bold cyan]', border_style='cyan'))

    if ram:
        total, used, free = get_memory()
        table = create_table('')
        table.add_column('Total (MB)', justify='center')
        table.add_column('Used (MB)', justify='center')
        table.add_column('Free (MB)', justify='center')
        table.add_column('Status', justify='center')

        if (float(used) / float(total)) * 100 >= 85:
            status = '[yellow]High Memory Usage[/yellow]'
        else:
            status = '[green]OK[/green]'

        table.add_row(f'{total:.0f}', f'{used:.0f}', f'{free:.0f}', status)
        panels.append(Panel(table, title='[bold cyan]Memory Usage[/bold cyan]', border_style='cyan'))

    if disk:
        size, used, available, percent = get_disk()
        table = create_table('')
        table.add_column('Size (GB)', justify='center')
        table.add_column('Used (GB)', justify='center')
        table.add_column('Available (GB)', justify='center')
        table.add_column('Usage %', justify='center')
        table.add_row(f'{round(size)}', f'{round(used)}', f'{round(available)}', f'{percent:.2f}')
        panels.append(Panel(table, title='[bold cyan]Disk Usage[/bold cyan]', border_style='cyan'))

    if process:
        list_cpu, _ = get_top_processes(process)

        table = create_table('')
        table.add_column('PID', justify='center')
        table.add_column('CPU (%)', justify='center')
        table.add_column('MEM (%)', justify='center')
        table.add_column('Command', justify='center')

        for proc in list_cpu:
            cmd = proc['COMMAND']
            cmd = cmd[:27] + '...' if len(cmd) > 30 else cmd
            table.add_row(proc['PID'], proc['%CPU'], proc['%MEM'], cmd)

        panels.append(
            Panel(
                table,
                title=f'[bold yellow]Top {process} Processes by CPU[/bold yellow]',
                border_style='yellow',
            )
        )

    if containers:
        top_containers = get_top_containers(process)

        table = create_table('')
        table.add_column('Container', justify='center')
        table.add_column('CPU (%)', justify='center')

        for name, cpu in top_containers:
            cname = name[:27] + '...' if len(name) > 30 else name
            table.add_row(cname, f'{cpu:.2f}')

        panels.append(
            Panel(
                table,
                title=f'[bold yellow]Top {containers} Containers by CPU[/bold yellow]',
                border_style='yellow',
            )
        )

    columns = Columns(panels)
    dashboard = Panel(columns, title='Monitoring Dashboard', border_style='bold green')
    console.print(dashboard)


@app.command('network')
def network(
    url: Annotated[str | None, typer.Option('-u', '--url', help='HTTP URL to test (curl)', show_default=False)] = None,
    host: Annotated[str | None, typer.Option('-h', '--host', help='Host/IP for ping and traceroute', show_default=False)] = None,
    domain: Annotated[str | None, typer.Option('-d', '--domain', help='Domain for DNS lookup', show_default=False)] = None,
    requests: Annotated[int, typer.Option('-n', '--count', help='Number of ICMP echo requests')] = 5,
    dtype: Annotated[str, typer.Option('-t', '--type', help='DNS record type (A, AAAA, MX, TXT, etc.)')] = 'A',
    sockets: Annotated[bool, typer.Option('--sockets', help='Show socket information (ss)')] = False,
    no_trace: Annotated[bool, typer.Option('--no-trace', help='Skip traceroute/mtr when --host is set')] = False,
):
    """
    Flexible network diagnostics: run only what you request.
    Provide one or more of: --host, --url, --domain, --sockets.
    """

    def header(title: str):
        print(f'\n[bold]{title}[/bold]')
        print('-' * len(title))

    def warn(msg: str):
        print(f'[warn] {msg}')

    def normalize_url(u: str) -> str:
        return u if u.startswith(('http://', 'https://')) else f'http://{u}'

    def curl_brief(u: str) -> str:
        fmt = 'HTTP %{http_code} | total %{time_total}s | connect %{time_connect}s | ttfb %{time_starttransfer}s\n'
        return run_cmd(f'curl -s -o /dev/null -w "{fmt}" {u}')

    def summarize_ping(out: str) -> str:
        lines = out.splitlines()
        sent = loss = avg = None
        for ln in lines:
            if 'packets transmitted' in ln and 'packet loss' in ln:
                parts = ln.replace(',', '').split()
                try:
                    sent = int(parts[0])
                    loss = parts[6]
                except Exception:
                    pass
            if 'rtt min/avg/max' in ln or 'round-trip min/avg/max' in ln:
                try:
                    avg = ln.split('=')[1].split('/')[1].strip()
                except Exception:
                    pass
        bits = []

        if sent is not None:
            bits.append(f'sent={sent}')
        if loss is not None:
            bits.append(f'loss={loss}')
        if avg is not None:
            bits.append(f'avg_rtt_ms={avg}')

        return ' | '.join(bits) if bits else (out.strip()[:200] if out else '')

    def summarize_trace(out: str, max_lines: int = 12) -> str:
        lines = [line for line in out.splitlines() if line.strip()]
        if len(lines) <= max_lines:
            return out
        return '\n'.join(lines[:6] + ['...'] + lines[-6:])

    # --- validate empty values FIRST ---
    if host is not None and not str(host).strip():
        warn('--host was provided but empty')
        raise typer.Exit(code=2)
    if url is not None and not str(url).strip():
        warn('--url was provided but empty')
        raise typer.Exit(code=2)
    if domain is not None and not str(domain).strip():
        warn('--domain was provided but empty')
        raise typer.Exit(code=2)

    # --- then require at least one section ---
    if not any([host, url, domain, sockets]):
        warn('Nothing to do. Provide at least one of: --host, --url, --domain, --sockets')
        raise typer.Exit(code=1)

    # ---- ping / traceroute (or mtr -r fallback) ----
    if host:
        header('Ping')
        ping_out = run_cmd(f'ping -c {requests} {host}')
        print(summarize_ping(ping_out) if ping_out else '[warn] ping not available or produced no output')

        if not no_trace:
            header('Traceroute')
            trace_out = run_cmd(f'traceroute {host}') or run_cmd(f'mtr -r {host}')
            print(summarize_trace(trace_out) if trace_out else '[warn] traceroute/mtr not available or produced no output')

    # ---- http (curl) ----
    if url:
        header('HTTP (curl)')
        u = normalize_url(url)
        print(curl_brief(u))
        headers = run_cmd(f'curl -s -I {u}')
        print(headers.strip() if headers else '[warn] curl not available or produced no output')

    # ---- dns ----
    if domain:
        header('DNS')
        dns_out = run_cmd(f'dig +short {domain} {dtype}') or run_cmd(f'nslookup -type={dtype} {domain}')
        print(dns_out.strip() if dns_out else '[warn] dig/nslookup not available or produced no output')

    # ---- sockets (ss) ----
    if sockets:
        header('Sockets (ss)')
        ss_out = run_cmd('ss -tulwn')
        print(ss_out or '[warn] ss not available or produced no output')


@app.command()
def ai(
    format: Annotated[str, typer.Option('--format', '-f', help='Data format: raw/structured/hybrid')] = 'hybrid',
    verbosity: Annotated[str, typer.Option('--verbosity', '-v', help='Output detail: concise/normal/hybrid')] = 'normal',
    auto_fix: Annotated[bool, typer.Option('--auto-fix', help='Auto-execute safe fixes')] = False,
):
    """
    Using Gemini 2.5 Flash for now for simple AI suggestions and reading through machine metrics
    giving suggest fixes upon user confirmations
    """

    if not os.getenv('GEMINI_API_KEY'):
        print('[red]Error: GEMINI_API_KEY is empty[/red]')
        print('Set it with: export GEMINI_API_KEY="your api key"')
        return

    try:
        from ai.ai_monitor import run_ai_monitor  # noqa: E402

        run_ai_monitor(data_format=format, verbosity=verbosity, auto_fix=auto_fix)
    except ImportError:
        print('[red]AI packages not installed[/red]')
        print('Run: pip install langchain langchain-google-genai rich')
    except Exception as err:
        print(f'[red]Error: {str(err)}[/red]')


if __name__ == '__main__':
    app()
