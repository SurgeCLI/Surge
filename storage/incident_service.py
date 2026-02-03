import logging
import time
from typing import Optional, Dict, Any
from sqlalchemy.engine import Connection

from .models import SystemSnapshot, IncidentCategory, IncidentSeverity
from .recorder import (
    detect_anomalies,
    create_incident,
    find_similar_incidents,
    close_incident,
    store_system_metrics,
)

logger = logging.getLogger(__name__)

# Severity mapping based on thresholds
SEVERITY_MAPPING = {
    IncidentCategory.DNS_ERROR: IncidentSeverity.HIGH,
    IncidentCategory.MEMORY_SPIKE: IncidentSeverity.HIGH,
    IncidentCategory.MEMORY_LEAK: IncidentSeverity.CRITICAL,
    IncidentCategory.CPU_THROTTLE: IncidentSeverity.HIGH,
    IncidentCategory.DISK_FULL: IncidentSeverity.CRITICAL,
    IncidentCategory.IO_SATURATION: IncidentSeverity.HIGH,
    IncidentCategory.NETWORK_LATENCY: IncidentSeverity.MEDIUM,
    IncidentCategory.NETWORK_LOSS: IncidentSeverity.HIGH,
    IncidentCategory.LOAD_SPIKE: IncidentSeverity.MEDIUM,
    IncidentCategory.UNKNOWN: IncidentSeverity.LOW,
}

# Incident cooldown (seconds) - avoid creating duplicate incidents too quickly
INCIDENT_COOLDOWN = 300  # 5 minutes


class IncidentDetectionService:
    """Service for detecting and managing incidents"""

    def __init__(self):
        self.active_incidents: Dict[IncidentCategory, Dict[str, Any]] = {}
        self.last_incident_time: Dict[IncidentCategory, int] = {}

    def process_snapshot(
        self,
        conn: Connection,
        snapshot: SystemSnapshot,
        last_snapshot: Optional[SystemSnapshot] = None,
    ) -> Optional[int]:
        """
        Process system snapshot and detect anomalies

        Args:
            conn: Database connection
            snapshot: Current system metrics snapshot
            last_snapshot: Previous snapshot for trend analysis

        Returns:
            Incident ID if one was created, None otherwise
        """
        # Store the metric first
        store_system_metrics(conn, snapshot)

        # Detect anomalies
        anomaly_category = detect_anomalies(snapshot, last_snapshot)

        if not anomaly_category:
            return None

        # Check cooldown
        current_time = int(time.time())
        last_time = self.last_incident_time.get(anomaly_category, 0)

        if current_time - last_time < INCIDENT_COOLDOWN:
            logger.debug(f'Incident {anomaly_category.value} in cooldown')
            return None

        self.last_incident_time[anomaly_category] = current_time

        # Determine severity
        severity = SEVERITY_MAPPING.get(anomaly_category, IncidentSeverity.MEDIUM)

        # Create incident summary
        summary = self._create_incident_summary(snapshot, anomaly_category)

        # Check for similar past incidents
        similar_incidents = find_similar_incidents(
            conn,
            summary=summary,
            category=anomaly_category,
            top_k=3,
        )

        tags = ['auto-detected', anomaly_category.value.lower()]
        if similar_incidents:
            tags.append('has-similar-history')

        # Create incident
        incident_id = create_incident(
            conn,
            category=anomaly_category,
            severity=severity,
            summary=summary,
            snapshot=snapshot,
            tags=tags,
        )

        # Track active incident
        if incident_id:
            self.active_incidents[anomaly_category] = {
                'incident_id': incident_id,
                'start_time': current_time,
                'severity': severity,
                'similar_incidents': similar_incidents,
            }

            logger.warning(f'INCIDENT DETECTED: {anomaly_category.value} (Severity: {severity.value}, ID: {incident_id})')

        return incident_id

    def _create_incident_summary(
        self,
        snapshot: SystemSnapshot,
        category: IncidentCategory,
    ) -> str:
        """Create human-readable incident summary"""
        summaries = {
            IncidentCategory.MEMORY_SPIKE: (
                f'Memory usage spike detected: {snapshot.mem_util:.1f}% utilized. '
                f'Load averages: {snapshot.load_1m:.2f}, {snapshot.load_5m:.2f}, {snapshot.load_15m:.2f}. '
                f'Memory velocity: {snapshot.mem_velocity:.1f}%/min.'
            ),
            IncidentCategory.MEMORY_LEAK: (
                f'Rapid memory growth detected (velocity: {snapshot.mem_velocity:.1f}%/min). '
                f'Current usage: {snapshot.mem_util:.1f}%. '
                f'Potential memory leak suspected.'
            ),
            IncidentCategory.CPU_THROTTLE: (
                f'High CPU utilization: {snapshot.cpu_util:.1f}%. '
                f'Load: {snapshot.load_1m:.2f} (1m), {snapshot.load_5m:.2f} (5m), {snapshot.load_15m:.2f} (15m). '
                f'System may be experiencing throttling.'
            ),
            IncidentCategory.LOAD_SPIKE: (
                f'Load spike detected: 1m average ({snapshot.load_1m:.2f}) >> 5m average ({snapshot.load_5m:.2f}). '
                f'Potential sudden workload increase.'
            ),
            IncidentCategory.DISK_FULL: (f'Disk capacity critical: {snapshot.disk_util:.1f}% used. Immediate cleanup may be required.'),
        }

        return summaries.get(
            category,
            f'{category.value} detected. CPU: {snapshot.cpu_util:.1f}%, Memory: {snapshot.mem_util:.1f}%, Disk: {snapshot.disk_util:.1f}%',
        )

    def resolve_incident(
        self,
        conn: Connection,
        incident_category: IncidentCategory,
        resolution: str,
        success: bool = True,
        confidence_score: float = 0.0,
    ) -> bool:
        if incident_category not in self.active_incidents:
            logger.warning(f'No active incident for category {incident_category.value}')
            return False

        incident_data = self.active_incidents[incident_category]
        incident_id = incident_data['incident_id']

        success_result = close_incident(
            conn,
            incident_id,
            resolution,
            success,
            confidence_score,
        )

        if success_result:
            del self.active_incidents[incident_category]
            logger.info(f'Incident {incident_id} resolved')

        return success_result

    def get_active_incidents(self) -> Dict[IncidentCategory, Dict[str, Any]]:
        """Get all currently active incidents"""
        return self.active_incidents.copy()

    def get_incident_stats(self) -> Dict[str, Any]:
        """Get statistics about active incidents"""
        return {
            'total_active': len(self.active_incidents),
            'active_categories': [cat.value for cat in self.active_incidents.keys()],
            'critical_count': sum(1 for inc in self.active_incidents.values() if inc['severity'] == IncidentSeverity.CRITICAL),
            'high_count': sum(1 for inc in self.active_incidents.values() if inc['severity'] == IncidentSeverity.HIGH),
        }
