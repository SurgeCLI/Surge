import time
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection

from .models import SystemSnapshot, Incident, IncidentCategory, IncidentSeverity
from .tables import system_metrics, incidents, incident_categories, incident_embeddings
from .vector_store import VectorStore

logger = logging.getLogger(__name__)
vector_store = VectorStore()

# Thresholds for anomaly detection
MEMORY_SPIKE_THRESHOLD = 85.0       # % used
MEMORY_VELOCITY_THRESHOLD = 10.0    # % per minute
CPU_THROTTLE_THRESHOLD = 90.0       # % used
LOAD_SPIKE_FACTOR = 2.5             # multiplier of normal load


def get_last_metric(conn: Connection) -> Optional[dict]:
    """
    Returns the last inserted row from system_metrics
    """
    query = select(system_metrics).order_by(system_metrics.c.timestamp.desc()).limit(1)
    result = conn.execute(query).fetchone()
    return dict(result) if result else None


def store_system_metrics(conn: Connection, snapshot: SystemSnapshot, incident_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Insert full row snapshot into system_metrics table

    Args:
        conn: SQLAlchemy database connection
        snapshot: SystemSnapshot with all metrics
        incident_id: Optional incident ID to link metric to

    Returns:
        Dictionary with metric_id and incident_id
    """
    query = insert(system_metrics).values(
        timestamp=snapshot.timestamp,
        cpu_util=snapshot.cpu_util,
        mem_util=snapshot.mem_util,
        mem_velocity=snapshot.mem_velocity,
        disk_util=snapshot.disk_util,
        incident_id=incident_id,
    )

    result = conn.execute(query)
    metric_id = int(result.inserted_primary_key[0])
    logger.debug(f'Stored metric {metric_id}')

    return {'metric_id': metric_id, 'incident_id': incident_id}


def detect_anomalies(snapshot: SystemSnapshot, last_snapshot: Optional[SystemSnapshot] = None) -> Optional[IncidentCategory]:
    """
    Detect anomalies from metrics snapshot

    Args:
        snapshot: Current system snapshot
        last_snapshot: Previous snapshot for trend analysis

    Returns:
        IncidentCategory if anomaly detected, None otherwise
    """
    # Memory spike detection
    if snapshot.mem_util > MEMORY_SPIKE_THRESHOLD:
        return IncidentCategory.MEMORY_SPIKE

    # Memory velocity detection (rapid growth)
    if snapshot.mem_velocity > MEMORY_VELOCITY_THRESHOLD:
        return IncidentCategory.MEMORY_LEAK

    # CPU throttle detection
    if snapshot.cpu_util > CPU_THROTTLE_THRESHOLD:
        return IncidentCategory.CPU_THROTTLE

    # Load spike detection
    if snapshot.load_1m > (snapshot.load_5m * LOAD_SPIKE_FACTOR):
        return IncidentCategory.LOAD_SPIKE

    # Disk full detection
    if snapshot.disk_util > 95.0:
        return IncidentCategory.DISK_FULL

    return None


def create_incident(
    conn: Connection,
    category: IncidentCategory,
    severity: IncidentSeverity,
    summary: str,
    snapshot: SystemSnapshot,
    tags: Optional[List[str]] = None,
) -> int:
    """
    Create new incident record in SQLite and vector DB

    Args:
        conn: SQLAlchemy connection
        category: Incident category
        severity: Incident severity
        summary: Human-readable incident description
        snapshot: System snapshot at incident time
        tags: Optional list of tags

    Returns:
        Incident ID created in SQLite
    """
    current_time = int(time.time())

    # Ensure category exists in database
    _ensure_category(conn, category)

    # Get category ID
    cat_query = select(incident_categories).where(incident_categories.c.name == category.value)
    cat_result = conn.execute(cat_query).fetchone()
    category_id = cat_result[0] if cat_result else None

    if not category_id:
        logger.error(f'Failed to get category ID for {category.value}')
        return None

    # Insert incident
    incident_query = insert(incidents).values(
        category_id=category_id,
        start_timestamp=snapshot.timestamp,
        summary=summary,
        severity=severity.value,
        created_at=current_time,
        updated_at=current_time,
        tags=','.join(tags) if tags else '',
    )

    result = conn.execute(incident_query)
    incident_id = int(result.inserted_primary_key[0])

    # Create incident object for vector DB
    incident_obj = Incident(
        category=category,
        severity=severity,
        start_timestamp=snapshot.timestamp,
        summary=summary,
        tags=tags or [],
        created_at=current_time,
        updated_at=current_time,
    )

    # Store in vector DB and get vector ID
    try:
        vector_id = vector_store.store_incident(incident_obj)

        # Update incident with vector ID
        update_query = update(incidents).where(incidents.c.id == incident_id).values(vector_id=vector_id)
        conn.execute(update_query)

        # Store embedding metadata
        embed_query = insert(incident_embeddings).values(
            incident_id=incident_id,
            vector_id=vector_id,
            embedding_model='sentence-transformers/all-MiniLM-L6-v2',
            created_at=current_time,
        )
        conn.execute(embed_query)

        logger.info(f'Created incident {incident_id} (category: {category.value}, severity: {severity.value})')
    except Exception as e:
        logger.error(f'Failed to store incident in vector DB: {e}')

    return incident_id


def find_similar_incidents(
    conn: Connection,
    summary: str,
    category: Optional[IncidentCategory] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Find similar past incidents using semantic search

    Args:
        conn: SQLAlchemy connection
        summary: Current incident summary to match
        category: Optional category to filter by
        top_k: Number of results to return

    Returns:
        List of similar incidents with details
    """
    similar_vectors = vector_store.search_similar_incidents(
        query=summary,
        category_filter=category,
        top_k=top_k,
    )

    if not similar_vectors:
        return []

    # Fetch full incident details from SQLite
    incidents_list = []
    for vector_result in similar_vectors:
        vector_id = vector_result['vector_id']
        incident_query = select(incidents).where(incidents.c.vector_id == vector_id)
        incident_row = conn.execute(incident_query).fetchone()

        if incident_row:
            incidents_list.append({
                **dict(incident_row),
                'similarity_score': vector_result['similarity_score'],
            })

    return incidents_list


def close_incident(
    conn: Connection,
    incident_id: int,
    resolution: str,
    success: bool = True,
    confidence_score: float = 0.0,
) -> bool:
    """
    Mark incident as resolved

    Args:
        conn: SQLAlchemy connection
        incident_id: Incident to close
        resolution: Resolution description
        success: Whether resolution was successful
        confidence_score: AI confidence in fix (0-1)

    Returns:
        Success status
    """
    current_time = int(time.time())

    try:
        update_query = (
            update(incidents)
            .where(incidents.c.id == incident_id)
            .values(
                end_timestamp=int(time.time()),
                resolution=resolution,
                success=success,
                confidence_score=confidence_score,
                updated_at=current_time,
            )
        )
        conn.execute(update_query)

        # Get vector ID for update
        incident_query = select(incidents.c.vector_id).where(incidents.c.id == incident_id)
        vector_id = conn.execute(incident_query).scalar()

        # Update in vector DB
        if vector_id:
            # For now, just log the update
            logger.info(f'Updated incident {incident_id} with resolution')

        return True
    except Exception as e:
        logger.error(f'Failed to close incident: {e}')
        return False


def _ensure_category(conn: Connection, category: IncidentCategory) -> None:
    """Ensure incident category exists in database"""
    try:
        check_query = select(incident_categories).where(incident_categories.c.name == category.value)
        result = conn.execute(check_query).fetchone()

        if not result:
            insert_query = insert(incident_categories).values(
                name=category.value,
                description=f'Incident category: {category.value}',
            )
            conn.execute(insert_query)
            logger.info(f'Created incident category: {category.value}')
    except Exception as e:
        logger.warning(f'Error ensuring category exists: {e}')


def get_incident_history(conn: Connection, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve recent incident history

    Args:
        conn: SQLAlchemy connection
        limit: Maximum incidents to return

    Returns:
        List of recent incidents
    """
    query = select(incidents).order_by(incidents.c.start_timestamp.desc()).limit(limit)

    result = conn.execute(query).fetchall()
    return [dict(row) for row in result]
