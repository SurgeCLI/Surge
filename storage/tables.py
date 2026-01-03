from sqlalchemy import create_engine, Table, Column, Integer, Float, Text, Boolean, MetaData, ForeignKey, Index

engine = create_engine('sqlite:///app.db', future=True)
metadata = MetaData()

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

incidents = Table(
    'incidents',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('start_timestamp', Integer, nullable=False),
    Column('end_timestamp', Integer),
    Column('summary', Text),
    Column('resolution', Text),
    Column('severity', Text),
    Column('success', Boolean, default=False),
    Column('vector_id', Text),
)

Index('index_metrics_incident', system_metrics.c.incident_id)
metadata.create_all(engine)
