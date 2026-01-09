import os
import time

from sqlalchemy import create_engine

from .metrics import collect_system_snapshot, calculate_mem_velocity
from .recorder import store_system_metrics


DB_URL = os.getenv('SURGE_DB_URL', 'sqlite:///app.db')
engine = create_engine(DB_URL, future=True)


def run_engine():
    with engine.begin() as conn:
        snapshot = collect_system_snapshot()
        snapshot.mem_velocity = calculate_mem_velocity(conn, snapshot.mem_util, snapshot.timestamp)
        incident_id = 0 # Add function
        store_system_metrics(conn, snapshot, incident_id)
    
if __name__ == '__main__':
    while True:
        try:
            run_engine()
        except Exception as e:
            print(f'[red]Storage daemon error: {e}[/red]')
        time.sleep(1)
