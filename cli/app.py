import subprocess
import typer
from rich import print
from typing import Annotated
import os

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


@app.command()
def network(
    url: Annotated[str, typer.Argument(help = 'URL to test network/API metrics')],
    requests: Annotated[int, typer.Option('-n', '--count', help = 'Number of requests to send')] = 5
):
    """
    Run basic network/API tests with a number of requests.
    """
    print(f'Testing network connection to {url} with {requests} requests.')
    # TODO: Add http requests or use curl through subprocess


@app.command()
def ai(
    format: Annotated[str, typer.Option("--format", '-f',help='Data format: raw/structured/hybrid')] = "hybrid",
    verbosity: Annotated[str, typer.Option('--verbosity', '-v', help="Output detail: concise/normal/hybrid")] = 'normal',
    auto_fix: Annotated[bool, typer.Option("--auto-fix", help="Auto-execute safe fixes")] = False,
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
        from ai.ai_monitor import run_ai_monitor
        
        run_ai_monitor(
            data_format=format,
            verbosity=verbosity,
            auto_fix=auto_fix
        )
    except ImportError:
        print('[red]AI packages not installed[/red]')
        print('Run: pip install langchain langchain-google-genai rich')
    except Exception as e:
        print(f'[red]Error: {str(e)}[/red]')

if __name__ == "__main__":
    app()