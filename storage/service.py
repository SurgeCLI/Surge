"""
Storage service daemon - collects metrics and detects incidents
"""

import os
import time
import logging

from sqlalchemy import create_engine

from .metrics import collect_system_snapshot, calculate_mem_velocity
from .incident_service import IncidentDetectionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv('SURGE_DB_URL', 'sqlite:///app.db')
engine = create_engine(DB_URL, future=True)
incident_service = IncidentDetectionService()

# Track last snapshot for trend analysis
last_snapshot = None


def run_engine() -> None:
    """
    Main loop: collect metrics, calculate velocity, detect incidents
    Runs approximately every 60 seconds
    """
    global last_snapshot

    with engine.begin() as conn:
        # Collect current metrics
        snapshot = collect_system_snapshot()

        # Calculate memory velocity (change rate)
        snapshot.mem_velocity = calculate_mem_velocity(conn, snapshot.mem_util, snapshot.timestamp)

        # Detect anomalies and create incidents if needed
        incident_id = incident_service.process_snapshot(conn, snapshot, last_snapshot)

        if incident_id:
            logger.info(f'New incident created: {incident_id}')

        # Track for next iteration
        last_snapshot = snapshot


def get_active_incidents():
    """Get current active incidents"""
    return incident_service.get_active_incidents()


def get_incident_stats():
    """Get incident statistics"""
    return incident_service.get_incident_stats()


if __name__ == '__main__':
    logger.info('Starting Surge storage daemon...')
    logger.info(f'Database: {DB_URL}')

    while True:
        try:
            run_engine()
        except Exception as e:
            logger.error(f'Storage daemon error: {e}', exc_info=True)

        time.sleep(60)  # Run every 60 seconds
