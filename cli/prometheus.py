import os
import requests

PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')

def query_prometheus_metrics(promql_query: str, endpoint: str = 'query', timeout: int = 5, **kwargs) -> list[dict]:
    """
        Query Prometheus metrics via PromQL.
    """
    try:
        response = requests.get(
            f'{PROMETHEUS_URL}/api/v1/{endpoint}',
            params = {'query': promql_query, **kwargs},
            timeout = timeout
        )
        response.raise_for_status()
        return response.json()['data']['result']
    except Exception as err:
        print(f'[red]Prometheus query failed:[/red] {err}')
        print(f'Query: {promql_query}')
        return []