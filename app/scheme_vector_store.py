"""High-level vector store operations for scheme documents"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import hashlib

from app.vector_store import VectorStoreClient, VectorDocument
from app.embedding_generator import get_embedding_generator
from app.models import Scheme, SchemeDocument
from app.config import get_settings

logger = logging.getLogger(__name__)


class SchemeVectorStore:
    """High-level interface for scheme document vector operations"""
    
    def __init__(
        self,
        vector_client: Optional[VectorStoreClient] = None,
    ):
        """
        Initialize scheme vector store
        
        Args:
            vector_client: VectorStoreClient instance (creates new if None)
        """
        settings = get_settings()
        
        # Initialize vector store client
        if vector_client is None:
            self.vector_client = VectorStoreClient(
                url=settings.vector_db_url,
                api_key=settings.vector_db_api_key,
                collection_name=settings.vector_db_index_name,
                vector_size=settings.vector_embedding_dimension,
            )
        else:
            self.vector_client = vector_client
        
        # Initialize embedding generator
        self.embedding_generator = get_embedding_generator()
        
        # Ensure collection exists
        try:
            self.vector_client.create_collection(
                vector_size=settings.vector_embedding_dimension
            )
        except Exception as e:
            logger.warning(f"Could not create collection: {e}")
        
        logger.info("Initialized SchemeVectorStore")
    
    def upsert_scheme_documents(
        self,
        scheme: Scheme,
        language: str = "en",
        chunk_size: int = 512,
        overlap: int = 50
    ) -> int:
        """
        Add or update scheme documents in vector store
        
        Args:
            scheme: Scheme object to index
            language: Language of the documents
            chunk_size: Maximum tokens per chunk
            overlap: Token overlap between chunks
            
        Returns:
            Number of document chunks created
        """
        try:
            # Get translated content or fall back to English
            scheme_name = scheme.get_translation("scheme_name", language)
            description = scheme.get_translation("description", language)
            benefits = scheme.get_translation("benefits", language)
            application_process = scheme.get_translation("application_process", language)
            
            # Create document sections
            documents_to_embed = []
            
            # Overview document
            overview_text = f"{scheme_name}\n\n{description}"
            documents_to_embed.append({
                "type": "overview",
                "text": overview_text
            })
            
            # Eligibility document
            if scheme.eligibility_criteria:
                eligibility_text = f"Eligibility for {scheme_name}:\n"
                for key, value in scheme.eligibility_criteria.items():
                    eligibility_text += f"- {key}: {value}\n"
                documents_to_embed.append({
                    "type": "eligibility",
                    "text": eligibility_text
                })
            
            # Benefits document
            benefits_text = f"Benefits of {scheme_name}:\n{benefits}"
            documents_to_embed.append({
                "type": "benefits",
                "text": benefits_text
            })
            
            # Application document
            application_text = f"How to apply for {scheme_name}:\n{application_process}"
            documents_to_embed.append({
                "type": "application",
                "text": application_text
            })
            
            # Generate embeddings and create vector documents
            vector_documents = []
            
            for doc_info in documents_to_embed:
                # Chunk the text
                chunks = self.embedding_generator.chunk_text(
                    doc_info["text"],
                    chunk_size=chunk_size,
                    overlap=overlap
                )
                
                # Generate embeddings for chunks
                embeddings = self.embedding_generator.batch_generate_embeddings(chunks)
                
                # Create vector documents
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    doc_id = self._generate_document_id(
                        scheme.scheme_id,
                        language,
                        doc_info["type"],
                        idx
                    )
                    
                    metadata = {
                        "scheme_id": scheme.scheme_id,
                        "scheme_name": scheme_name,
                        "scheme_name_local": scheme_name,
                        "category": scheme.category.value,
                        "authority": scheme.authority.value,
                        "state": scheme.applicable_states[0] if scheme.applicable_states else "ALL",
                        "applicable_states": scheme.applicable_states,
                        "status": scheme.status.value,
                        "last_updated": scheme.last_updated.isoformat(),
                        "language": language,
                        "document_type": doc_info["type"],
                        "chunk_index": idx,
                    }
                    
                    vector_doc = VectorDocument(
                        id=doc_id,
                        vector=embedding,
                        metadata=metadata,
                        text_chunk=chunk
                    )
                    vector_documents.append(vector_doc)
            
            # Upsert to vector store
            count = self.vector_client.upsert_documents(vector_documents)
            
            logger.info(
                f"Upserted {count} document chunks for scheme {scheme.scheme_id} "
                f"in language {language}"
            )
            return count
        
        except Exception as e:
            logger.error(f"Error upserting scheme documents: {e}")
            raise
    
    def search_schemes(
        self,
        query: str,
        top_k: int = 5,
        language: str = "en",
        filters: Optional[Dict[str, Any]] = None,
        confidence_threshold: Optional[float] = None
    ) -> List[SchemeDocument]:
        """
        Search for relevant schemes using semantic search
        
        Args:
            query: User query text
            top_k: Number of top results to return
            language: Query language
            filters: Metadata filters (category, state, status, etc.)
            confidence_threshold: Minimum similarity score
            
        Returns:
            List of SchemeDocument objects with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_generator.generate_embedding(query)
            
            # Add language filter if not already present
            if filters is None:
                filters = {}
            
            # Optionally filter by language (commented out to allow cross-language search)
            # filters["language"] = language
            
            # Search vector store
            results = self.vector_client.search(
                query_vector=query_embedding,
                top_k=top_k,
                filters=filters,
                score_threshold=confidence_threshold
            )
            
            # Convert results to SchemeDocument objects
            # Fetch full scheme details from database
            scheme_documents = []
            
            # Import here to avoid circular dependency
            from app.scheme_repository import SchemeRepository
            scheme_repo = SchemeRepository()
            
            for result in results:
                metadata = result["metadata"]
                scheme_id = metadata["scheme_id"]
                
                # Fetch full scheme from database
                scheme = scheme_repo.get_scheme_by_id(scheme_id)
                
                if not scheme:
                    logger.warning(f"Scheme {scheme_id} not found in database, skipping")
                    continue
                
                scheme_doc = SchemeDocument(
                    document_id=result.get("id", metadata.get("document_id", "")),
                    scheme_id=scheme_id,
                    scheme=scheme,
                    language=metadata["language"],
                    content=result["text_chunk"],
                    document_type=metadata.get("document_type", "overview"),
                    similarity_score=result["score"]
                )
                
                scheme_documents.append(scheme_doc)
            
            logger.info(
                f"Search returned {len(scheme_documents)} results for query: '{query[:50]}...'"
            )
            return scheme_documents
        
        except Exception as e:
            logger.error(f"Error searching schemes: {e}")
            raise
    
    def delete_scheme_documents(
        self,
        scheme_id: str,
        language: Optional[str] = None
    ) -> None:
        """
        Delete all documents for a scheme
        
        Args:
            scheme_id: Scheme ID to delete
            language: Optional language filter (deletes all languages if None)
        """
        try:
            filters = {"scheme_id": scheme_id}
            
            if language:
                filters["language"] = language
            
            self.vector_client.delete_by_filter(filters)
            
            logger.info(
                f"Deleted documents for scheme {scheme_id} "
                f"(language: {language or 'all'})"
            )
        
        except Exception as e:
            logger.error(f"Error deleting scheme documents: {e}")
            raise
    
    def update_scheme_documents(
        self,
        scheme: Scheme,
        languages: Optional[List[str]] = None
    ) -> int:
        """
        Update scheme documents in vector store
        
        Args:
            scheme: Updated scheme object
            languages: List of languages to update (defaults to all supported)
            
        Returns:
            Total number of document chunks updated
        """
        if languages is None:
            # Default to English and Hindi
            languages = ["en", "hi"]
        
        total_count = 0
        
        for language in languages:
            try:
                # Delete existing documents for this scheme and language
                self.delete_scheme_documents(scheme.scheme_id, language)
                
                # Re-index with updated content
                count = self.upsert_scheme_documents(scheme, language)
                total_count += count
            
            except Exception as e:
                logger.error(
                    f"Error updating scheme {scheme.scheme_id} "
                    f"for language {language}: {e}"
                )
                # Continue with other languages
        
        logger.info(
            f"Updated {total_count} document chunks for scheme {scheme.scheme_id}"
        )
        return total_count
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            return self.vector_client.get_collection_info()
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise
    
    def _generate_document_id(
        self,
        scheme_id: str,
        language: str,
        doc_type: str,
        chunk_index: int
    ) -> str:
        """
        Generate unique document ID
        
        Args:
            scheme_id: Scheme identifier
            language: Document language
            doc_type: Document type
            chunk_index: Chunk index
            
        Returns:
            Unique document ID
        """
        # Create deterministic ID based on scheme, language, type, and chunk
        id_string = f"{scheme_id}_{language}_{doc_type}_{chunk_index}"
        
        # Use hash for shorter IDs if needed
        # return hashlib.md5(id_string.encode()).hexdigest()
        
        return id_string
    
    def close(self) -> None:
        """Close vector store connection"""
        self.vector_client.close()
