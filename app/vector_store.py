"""Vector store integration for Y-Connect WhatsApp Bot using Qdrant"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import logging
import os
from dotenv import load_dotenv

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        MatchAny,
        Range,
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorDocument(BaseModel):
    """Model for vector documents stored in the vector database"""
    
    id: str = Field(..., description="Unique document ID")
    vector: List[float] = Field(..., description="Embedding vector")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata for filtering"
    )
    text_chunk: str = Field(..., description="Original text that was embedded")
    
    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is not empty"""
        if not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()
    
    @field_validator("vector")
    @classmethod
    def validate_vector(cls, v: List[float]) -> List[float]:
        """Validate vector dimensions"""
        if not v:
            raise ValueError("Vector cannot be empty")
        if len(v) not in [384, 768, 1024]:
            raise ValueError(
                f"Vector dimension {len(v)} not supported. "
                "Must be 384, 768, or 1024"
            )
        return v
    
    @field_validator("text_chunk")
    @classmethod
    def validate_text_chunk(cls, v: str) -> str:
        """Ensure text chunk is not empty"""
        if not v.strip():
            raise ValueError("Text chunk cannot be empty")
        return v.strip()


class VectorStoreClient:
    """Client for interacting with Qdrant vector database"""
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: Optional[str] = None,
        vector_size: int = 384,
    ):
        """
        Initialize Qdrant vector store client
        
        Args:
            url: Qdrant server URL (defaults to QDRANT_URL env var or config)
            api_key: Qdrant API key (defaults to QDRANT_API_KEY env var)
            collection_name: Collection name (defaults to config)
            vector_size: Dimension of embedding vectors (default: 384)
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "qdrant-client is not installed. "
                "Install it with: pip install qdrant-client"
            )
        
        # Force load the .env file from the project root
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        load_dotenv(env_path)
        
        settings = get_settings()
        
        # Get URL from parameter, env var, or config (in that order)
        self.url = url or os.getenv("QDRANT_URL") or settings.vector_db_url
        
        # Get API key from parameter or env var (in that order)
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        
        self.collection_name = collection_name or settings.vector_db_index_name
        self.vector_size = vector_size
        
        # Initialize Qdrant client with credentials
        self.client = QdrantClient(
            url="https://85607eaf-f950-4768-9509-dba27ce4384b.us-east-1-1.aws.cloud.qdrant.io",
            api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.4Ec8gmNMiTSXLCDu6Leb-kI1AAuvo4eYoWcgD6lbEbI"
        )
        
        logger.info(
            f"Initialized VectorStoreClient with collection: {self.collection_name}, "
            f"URL: {self.url}, "
            f"API key: {'***' if self.api_key else 'None'}"
        )
    
    def create_collection(self, vector_size: Optional[int] = None) -> None:
        """
        Create a new collection in Qdrant
        
        Args:
            vector_size: Dimension of vectors (defaults to instance vector_size)
        """
        size = vector_size or self.vector_size
        
        try:
            # Check if collection already exists
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"Collection {self.collection_name} already exists")
                return
            
            # Create collection with cosine distance metric
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=size,
                    distance=Distance.COSINE
                ),
            )
            logger.info(
                f"Created collection {self.collection_name} with vector size {size}"
            )
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
    
    def upsert_documents(self, documents: List[VectorDocument]) -> int:
        """
        Add or update documents in the vector store
        
        Args:
            documents: List of VectorDocument objects to upsert
            
        Returns:
            Number of documents upserted
        """
        if not documents:
            logger.warning("No documents to upsert")
            return 0
        
        try:
            # Convert VectorDocument objects to PointStruct
            points = []
            for doc in documents:
                point = PointStruct(
                    id=doc.id,
                    vector=doc.vector,
                    payload={
                        "text_chunk": doc.text_chunk,
                        **doc.metadata
                    }
                )
                points.append(point)
            
            # Upsert points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Upserted {len(documents)} documents to {self.collection_name}")
            return len(documents)
        
        except Exception as e:
            logger.error(f"Error upserting documents: {e}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of top results to return
            filters: Metadata filters (e.g., {"category": "agriculture", "status": "active"})
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            # Build filter conditions if provided
            filter_conditions = None
            if filters:
                filter_conditions = self._build_filter(filters)
            
            # Perform search
            search_results = self.client.query_points(
               collection_name=self.collection_name,
               query=query_vector,
               limit=top_k,
               query_filter=filter_conditions,
               score_threshold=score_threshold,
             ).points
            
            # Convert results to dict format
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "text_chunk": result.payload.get("text_chunk", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items()
                        if k != "text_chunk"
                    }
                })
            
            logger.info(
                f"Search returned {len(results)} results "
                f"(top_k={top_k}, filters={filters})"
            )
            return results
        
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    def delete_by_id(self, document_ids: List[str]) -> int:
        """
        Delete documents by their IDs
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            Number of documents deleted
        """
        if not document_ids:
            logger.warning("No document IDs provided for deletion")
            return 0
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=document_ids
            )
            
            logger.info(f"Deleted {len(document_ids)} documents from {self.collection_name}")
            return len(document_ids)
        
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise
    
    def delete_by_filter(self, filters: Dict[str, Any]) -> None:
        """
        Delete documents matching filter criteria
        
        Args:
            filters: Metadata filters for deletion
        """
        try:
            filter_conditions = self._build_filter(filters)
            
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=filter_conditions
            )
            
            logger.info(f"Deleted documents matching filters: {filters}")
        
        except Exception as e:
            logger.error(f"Error deleting documents by filter: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            return {
                "name": collection_info.config.params.vectors.size,
                "vector_size": collection_info.config.params.vectors.size,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            raise
    
    def _build_filter(self, filters: Dict[str, Any]) -> Filter:
        """
        Build Qdrant filter from dictionary
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Qdrant Filter object
        """
        conditions = []
        
        for key, value in filters.items():
            if isinstance(value, list):
                # Match any value in list
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchAny(any=value)
                    )
                )
            elif isinstance(value, dict):
                # Range filter (e.g., {"gte": 0.7})
                if "gte" in value or "lte" in value or "gt" in value or "lt" in value:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            range=Range(
                                gte=value.get("gte"),
                                lte=value.get("lte"),
                                gt=value.get("gt"),
                                lt=value.get("lt"),
                            )
                        )
                    )
            else:
                # Exact match
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
        
        return Filter(must=conditions) if conditions else None
    
    def close(self) -> None:
        """Close the Qdrant client connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("Closed VectorStoreClient connection")
