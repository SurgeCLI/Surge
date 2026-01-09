from sqlalchemy import insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from models import SystemSnapshot
from tables import system_metrics, incidents


def get_last_metric(conn: Connection) -> dict[str] | None:
    """
    Returns the last inserted row from system_metrics
    """
    query = select(system_metrics).order_by(system_metrics.c.timestamp.desc()).limit(1)
    result = conn.execute(query).fetchone()
    return dict(result) if result else None


def store_system_metrics(conn: Connection, snapshot: SystemSnapshot, mem_velocity: float, incident_id: int | None = None) -> dict:
    """
    Insert full row snapshot into system_metrics table
    """
    query = insert(system_metrics).values(
        timestamp=snapshot.timestamp,
        cpu_util=snapshot.cpu_util,
        mem_util=snapshot.mem_util,
        mem_velocity=mem_velocity,
        disk_util=snapshot.disk_util,
        incident_id=incident_id,
    )

    result = conn.execute(query)
    metric_id = int(result.inserted_primary_key[0])
    
    return {"metric_id": metric_id, "incident_id": incident_id}
