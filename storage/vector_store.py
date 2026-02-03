import os
import logging
from typing import Optional, List, Dict, Any
import uuid
import chromadb
from chromadb.config import Settings

from .models import Incident, IncidentCategory

logger = logging.getLogger(__name__)

# ChromaDB configuration
CHROMA_DIR = os.getenv('SURGE_CHROMA_DIR', 'data/chroma')
EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'


class VectorStore:
    """ChromaDB wrapper for incident semantic search"""

    def __init__(self, persistent_dir: str = CHROMA_DIR):
        """
        Initialize ChromaDB persistent client

        Args:
            persistent_dir: Directory for ChromaDB storage
        """
        os.makedirs(persistent_dir, exist_ok=True)

        settings = Settings(
            chroma_db_impl='duckdb+parquet',
            persist_directory=persistent_dir,
            anonymized_telemetry=False,
        )

        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(
            name='incidents',
            metadata={'hnsw:space': 'cosine'},
        )
        logger.info(f'Initialized ChromaDB at {persistent_dir}')

    def store_incident(self, incident: Incident) -> str:
        """
        Store incident embedding in vector DB

        Args:
            incident: Incident object with summary and metadata

        Returns:
            Vector ID assigned by ChromaDB
        """
        if not incident.vector_id:
            incident.vector_id = f'incident_{uuid.uuid4().hex[:12]}'

        metadata = {
            'category': incident.category.value,
            'severity': incident.severity.value,
            'tags': ','.join(incident.tags),
            'start_timestamp': incident.start_timestamp,
            'success': incident.success,
            'confidence_score': incident.confidence_score,
        }

        try:
            self.collection.add(
                ids=[incident.vector_id],
                documents=[incident.summary],
                metadatas=[metadata],
            )
            logger.info(f'Stored incident {incident.vector_id} in vector DB')
            return incident.vector_id
        except Exception as e:
            logger.error(f'Failed to store incident: {e}')
            raise

    def search_similar_incidents(
        self,
        query: str,
        category_filter: Optional[IncidentCategory] = None,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for similar incidents

        Args:
            query: Incident summary or description to search for
            category_filter: Optional category to filter by
            top_k: Number of results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of incident results with scores
        """
        try:
            # Build where filter if category specified
            where_filter = None
            if category_filter:
                where_filter = {'category': {'$eq': category_filter.value}}

            results = self.collection.query(
                query_texts=[query], n_results=top_k, where=where_filter, include=['documents', 'metadatas', 'distances']
            )

            # Convert distances to similarity scores from cosine dist
            incidents = []
            if results and results['documents']:
                for i, doc_id in enumerate(results['ids'][0]):
                    distance = results['distances'][0][i]
                    similarity_score = 1 - distance

                    if similarity_score >= score_threshold:
                        incidents.append({
                            'vector_id': doc_id,
                            'summary': results['documents'][0][i],
                            'metadata': results['metadatas'][0][i],
                            'similarity_score': similarity_score,
                        })

            logger.info(f'Found {len(incidents)} similar incidents for query')
            return incidents
        except Exception as e:
            logger.error(f'Search failed: {e}')
            return []

    def update_incident(self, incident: Incident) -> bool:
        """
        Update incident embedding (e.g., resolution added)

        Args:
            incident: Updated incident object

        Returns:
            Success status
        """
        if not incident.vector_id:
            logger.warning('Cannot update incident without vector_id')
            return False

        try:
            metadata = {
                'category': incident.category.value,
                'severity': incident.severity.value,
                'tags': ','.join(incident.tags),
                'start_timestamp': incident.start_timestamp,
                'success': incident.success,
                'confidence_score': incident.confidence_score,
            }

            self.collection.update(
                ids=[incident.vector_id],
                documents=[incident.summary],
                metadatas=[metadata],
            )
            logger.info(f'Updated incident {incident.vector_id}')
            return True
        except Exception as e:
            logger.error(f'Failed to update incident: {e}')
            return False

    def delete_incident(self, vector_id: str) -> bool:
        """Delete incident from vector DB"""
        try:
            self.collection.delete(ids=[vector_id])
            logger.info(f'Deleted incident {vector_id}')
            return True
        except Exception as e:
            logger.error(f'Failed to delete incident: {e}')
            return False

    def get_incident_count(self) -> int:
        """Get total number of incidents in vector DB"""
        return self.collection.count()

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            'total_incidents': self.collection.count(),
            'embedding_model': EMBEDDING_MODEL,
            'collection_name': self.collection.name,
        }
