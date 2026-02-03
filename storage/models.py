from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional, List
import json
import time


class IncidentCategory(Enum):
    """SRE incident categories for classification"""

    DNS_ERROR = 'DNS_ERROR'
    MEMORY_SPIKE = 'MEMORY_SPIKE'
    MEMORY_LEAK = 'MEMORY_LEAK'
    CPU_THROTTLE = 'CPU_THROTTLE'
    DISK_FULL = 'DISK_FULL'
    IO_SATURATION = 'IO_SATURATION'
    NETWORK_LATENCY = 'NETWORK_LATENCY'
    NETWORK_LOSS = 'NETWORK_LOSS'
    LOAD_SPIKE = 'LOAD_SPIKE'
    UNKNOWN = 'UNKNOWN'


class IncidentSeverity(Enum):
    """Incident severity levels"""

    CRITICAL = 'CRITICAL'
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'


@dataclass(frozen=True)
class SystemSnapshot:
    """Represents a single system metrics snapshot"""

    timestamp: int
    cpu_util: float
    mem_util: float
    disk_util: float
    load_1m: float
    load_5m: float
    load_15m: float
    mem_velocity: float = 0.0
    raw_uptime: Optional[str] = None
    raw_free: Optional[str] = None
    raw_df: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class IncidentMetadata:
    """Metadata for storing with incident in vector DB"""

    category: IncidentCategory
    severity: IncidentSeverity
    tags: List[str] = field(default_factory=list)
    metrics_context: dict = field(default_factory=dict)  # CPU, MEM, DISK at incident time

    def to_json(self) -> str:
        return json.dumps({
            'category': self.category.value,
            'severity': self.severity.value,
            'tags': self.tags,
            'metrics_context': self.metrics_context,
        })


@dataclass
class Incident:
    """Represents a detected incident"""

    category: IncidentCategory
    severity: IncidentSeverity
    start_timestamp: int
    summary: str
    resolution: Optional[str] = None
    root_cause: Optional[str] = None
    end_timestamp: Optional[int] = None
    success: bool = False
    confidence_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    ai_suggestions: List[str] = field(default_factory=list)
    vector_id: Optional[str] = None
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self):
        return asdict(self)

    def to_vector_db_doc(self) -> dict:
        """Convert to ChromaDB document format"""
        return {
            'id': self.vector_id or str(self.created_at),
            'document': self.summary,
            'metadata': {
                'category': self.category.value,
                'severity': self.severity.value,
                'tags': self.tags,
                'start_timestamp': self.start_timestamp,
                'confidence_score': self.confidence_score,
                'success': self.success,
            },
        }
