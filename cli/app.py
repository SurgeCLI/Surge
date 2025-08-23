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
    Returns (averages, cores).
    provider: 'linux' or 'psutil' (if psutil is not available, falls back to linux)
    """

    uptime = run_cmd("uptime | awk -F'average:' '{print $2}'")
    averages = [float(x.replace(',', '')) for x in uptime.split()]
    cores = run_cmd('nproc')

    return averages, cores


def get_cpu() -> tuple:
    top = run_cmd('top -bn1')
    return top


@app.command()
def monitor(
    load: Annotated[bool, typer.Option('-l', '--load', help = 'Show system load averages')] = True,
    cpu: Annotated[bool, typer.Option('-c', '--cpu', help = 'Show CPU usage')] = True,
    ram: Annotated[bool, typer.Option('-r', '--ram', help = 'Show RAM usage')] = True,
    disk: Annotated[bool, typer.Option('-d', '--disk', help = 'Show Disk usage')] = True,
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

    # Load -> Captured by Linux subprocess of 'uptime'
    if load:
        # Psutil substitute: averages = psutil.getloadavg(), cores = psutil.cpu_count()

        averages, cores = get_load()

        print('System Load Averages')
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
        cpu_util = get_cpu()

        print('\nSystem CPU Utilization')
        print('----------------------')
    
        if not verbose:
            print(f'CPU: {cpu_util}')


    if verbose:
        print('Placeholder for verbose system metrics.')
    else:
        print('Placeholder for default system metrics')


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

if __name__ == "__main__":
    app()