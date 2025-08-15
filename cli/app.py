import typer
from rich import print
from typing import Annotated

app = typer.Typer(help = 'Surge - A DevOps CLI Tool For System Monitoring and Production Reliability')

@app.command()
def monitor(
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
