import subprocess
import typer
from rich import print
from typing import Annotated


app = typer.Typer(help = 'Surge - A DevOps CLI Tool For System Monitoring and Production Reliability')

def run_cmd(cmd: str) -> str:
    """
    Helper function to abstract lengthy subprocess command implementation :D
    """

    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def get_load() -> tuple[float] | int:
    """
    Utilizes Linux uptime for system load metrics and to determine core utilization
    """

    uptime = run_cmd("uptime | awk -F'average:' '{print $2}'")
    averages = [float(x.replace(',', '')) for x in uptime.split()]
    cores = run_cmd('nproc')

    return averages, cores


def get_cpu() -> tuple[float]:
    """
    Uses top to find CPU utilization grouped by user, system, and idle percents.
    """
    top = run_cmd('top -bn1 | grep "Cpu(s)"').split(',')
    user = top[0].split()[-2]
    system = top[1].split()[0]
    idle = top[3].split()[0]

    return user, system, idle


def get_memory() -> tuple[float]:
    """
    Returns remaining memory by group using free.
    """
    free = run_cmd('free -m | grep Mem').split()
    total, used, free_mem = free[1], free[2], free[3]

    return total, used, free_mem


def get_disk() -> tuple[float]:
    """
    Returns disk usage with df.
    """
    df = run_cmd('df -h / | tail -1').split()
    size, used, available, percent = df[1], df[2], df[3], df[4]

    return size, used, available, percent


def get_io() -> tuple[float]:
    # TODO: implement with iostat
    pass


@app.command()
def monitor(
    load: Annotated[bool, typer.Option('-l', '--load', help = 'Show system load averages')] = True,
    cpu: Annotated[bool, typer.Option('-c', '--cpu', help = 'Show CPU usage')] = True,
    ram: Annotated[bool, typer.Option('-r', '--ram', help = 'Show RAM usage')] = True,
    disk: Annotated[bool, typer.Option('-d', '--disk', help = 'Show Disk usage')] = True,
    io: Annotated[bool, typer.Option('-o', '--io', help = 'Show Disk I/O statistics')] = True,
    interval: Annotated[int, typer.Option('-i', '--interval', help = 'Polling interval in seconds')] = 5,
    verbose: Annotated[bool, typer.Option('-v', '--verbose', help = 'Show detailed system metrics')] = False
):
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

        print('\n[bold]System Load Averages[/bold]')
        print('---------------------')

        if not verbose:
            print(f'Load avg (1m): {averages[0]}')
            print(f'Load avg (5m): {averages[1]}')
            print(f'Load avg (15m): {averages[2]}')
        else:
            print(f'Load avg (1m): {averages[0]:.2f} ({averages[0] / cores:.3f} per CPU)')
            print(f'Load avg (5m): {averages[1]:.2f} ({averages[1] / cores:.3f} per CPU)')
            print(f'Load avg (15m): {averages[2]:.2f} ({averages[2] / cores:.3f} per CPU)')
    
    if cpu:
        user, system, idle = get_cpu()
        print('\n[bold]CPU Utilization[/bold]')
        print('---------------------')
        print(f'User: {user}% | System: {system}% | Idle: {idle}%')
    
    if ram:
        total, used, free = get_memory()
        print('\n[bold]Memory Usage (MB)[/bold]')
        print('---------------------')
        print(f'Total: {total} | Used: {used} | Free: {free}')
    
    if disk:
        size, used, available, percent = get_disk()
        print('\n[bold]Disk Usage[/bold]')
        print('---------------------')
        print(f'Size: {size} | Used: {used} | Available: {available} | Usage: {percent}')

@app.command("network")
def network(
    url: Annotated[str | None, typer.Option("-u", "--url", help="HTTP URL to test (curl)", show_default=False)] = None,
    host: Annotated[str | None, typer.Option("-h", "--host", help="Host/IP for ping and traceroute", show_default=False)] = None,
    domain: Annotated[str | None, typer.Option("-d", "--domain", help="Domain for DNS lookup", show_default=False)] = None,
    requests: Annotated[int, typer.Option("-n", "--count", help="Number of ICMP echo requests")] = 5,
    dtype: Annotated[str, typer.Option("-t", "--type", help="DNS record type (A, AAAA, MX, TXT, etc.)")] = "A",
    sockets: Annotated[bool, typer.Option("--sockets", help="Show socket information (ss)")] = False,
    bw_server: Annotated[str | None, typer.Option("--bw-server", help="iperf3 server (optional)")] = None,
    bw_time: Annotated[int, typer.Option("--bw-time", help="iperf3 duration in seconds")] = 10,
    no_trace: Annotated[bool, typer.Option("--no-trace", help="Skip traceroute/mtr when --host is set")] = False,
):
    """
    Flexible network diagnostics: run only what you request.
    Provide one or more of: --host, --url, --domain, --sockets, --bw-server.
    """

    def header(title: str):
        print(f"\n[bold]{title}[/bold]")
        print("-" * len(title))

    # guard: require at least one section
    if not any([host, url, domain, sockets, bw_server]):
        print("[warn] Nothing to do. Provide at least one of: --host, --url, --domain, --sockets, --bw-server")
        raise typer.Exit(code=1)

    # ---- ping / traceroute ----
    if host:
        header("Ping")
        ping_out = run_cmd(f"ping -c {requests} {host}")
        print(ping_out or "[warn] ping not available or produced no output")

        if not no_trace:
            header("Traceroute")
            trace_out = run_cmd(f"traceroute {host}") or run_cmd(f"mtr -r {host}")
            print(trace_out or "[warn] traceroute/mtr not available or produced no output")

    # ---- http (curl) ----
    if url:
        header("HTTP (curl)")
        http_out = run_cmd(f"curl -s -i {url}")
        print(http_out or "[warn] curl not available or produced no output")

    # ---- dns ----
    if domain:
        header("DNS")
        dns_out = run_cmd(f"dig +short {domain} {dtype}") or run_cmd(f"nslookup -type={dtype} {domain}")
        print(dns_out or "[warn] dig/nslookup not available or produced no output")

    # ---- sockets (ss) ----
    if sockets:
        header("Sockets (ss)")
        ss_out = run_cmd("ss -tulwn")
        print(ss_out or "[warn] ss not available or produced no output")

    # ---- bandwidth (iperf3) ----
    if bw_server:
        header("Bandwidth (iperf3)")
        iperf_out = run_cmd(f"iperf3 -c {bw_server} -t {bw_time}")
        print(iperf_out or "[warn] iperf3 not available or produced no output")
        
if __name__ == "__main__":
    app()