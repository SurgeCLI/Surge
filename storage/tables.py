from sqlalchemy import Table, Column, Integer, Float, Text, Boolean, MetaData, ForeignKey, Index, String
from sqlalchemy import create_engine
import os

DB_URL = os.getenv('SURGE_DB_URL', 'sqlite:///app.db')
metadata = MetaData()
engine = create_engine(DB_URL, future=True)

# System metrics table - polled every minute
system_metrics = Table(
    'system_metrics',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('timestamp', Integer, nullable=False, index=True),
    Column('cpu_util', Float, nullable=False),
    Column('mem_util', Float, nullable=False),
    Column('mem_velocity', Float, nullable=False),
    Column('disk_util', Float, nullable=False),
    Column('incident_id', Integer, ForeignKey('incidents.id'), nullable=True),
)

# Incident categories for classification
incident_categories = Table(
    'incident_categories',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(50), unique=True, nullable=False),  # e.g., DNS_ERROR, MEMORY_SPIKE, CPU_THROTTLE
    Column('description', Text),
)

# Incident storage with SRE-relevant fields
incidents = Table(
    'incidents',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('category_id', Integer, ForeignKey('incident_categories.id'), nullable=False),
    Column('start_timestamp', Integer, nullable=False, index=True),
    Column('end_timestamp', Integer),
    Column('summary', Text, nullable=False),
    Column('resolution', Text),
    Column('root_cause', Text),
    Column('severity', String(20), nullable=False),  # CRITICAL, HIGH, MEDIUM, LOW
    Column('success', Boolean, default=False),
    Column('confidence_score', Float, default=0.0),  # 0.0-1.0, AI confidence in fix
    Column('tags', Text),  # JSON array of string tags
    Column('ai_suggestions', Text),  # JSON array of suggested fixes
    Column('vector_id', String(100), unique=True),  # ChromaDB document ID
    Column('created_at', Integer, nullable=False),
    Column('updated_at', Integer, nullable=False),
)

# Embedding metadata for vector DB integration
incident_embeddings = Table(
    'incident_embeddings',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('incident_id', Integer, ForeignKey('incidents.id'), nullable=False, unique=True),
    Column('vector_id', String(100), unique=True, nullable=False),  # ChromaDB ID
    Column('embedding_model', String(100), nullable=False),  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    Column('embedding_metadata', Text),  # JSON with additional search metadata
    Column('created_at', Integer, nullable=False),
)

# Create indexes for common queries
Index('idx_metrics_timestamp', system_metrics.c.timestamp)
Index('idx_metrics_incident', system_metrics.c.incident_id)
Index('idx_incidents_category', incidents.c.category_id)
Index('idx_incidents_start_ts', incidents.c.start_timestamp)
Index('idx_incidents_vector_id', incidents.c.vector_id)
Index('idx_embeddings_incident', incident_embeddings.c.incident_id)

metadata.create_all(engine)
