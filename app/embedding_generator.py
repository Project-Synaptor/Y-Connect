"""Embedding generation for Y-Connect WhatsApp Bot using sentence-transformers"""

from typing import List, Dict, Any
import logging
from functools import lru_cache

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from app.config import get_settings
from app.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using multilingual sentence transformers"""
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "cpu"
    ):
        """
        Initialize embedding generator
        
        Args:
            model_name: Name of the sentence-transformers model
            device: Device to run model on ('cpu' or 'cuda')
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install it with: pip install sentence-transformers"
            )
        
        self.model_name = model_name
        self.device = device
        
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.embedding_dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(
            f"Loaded embedding model with dimension: {self.embedding_dimension}"
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text (with caching)
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        text = text.strip()
        
        # Try to get from cache first
        try:
            cached_embedding = cache_manager.get_cached_embedding(text)
            if cached_embedding:
                logger.debug("Embedding cache hit")
                return cached_embedding
        except Exception as e:
            logger.warning(f"Error retrieving embedding from cache: {e}")
        
        try:
            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            # Convert to list of floats
            embedding_list = embedding.tolist()
            
            # Cache the embedding
            try:
                cache_manager.cache_embedding(text, embedding_list)
            except Exception as e:
                logger.warning(f"Error caching embedding: {e}")
            
            return embedding_list
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def batch_generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches
        
        Args:
            texts: List of input texts to embed
            batch_size: Number of texts to process in each batch
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("No texts provided for embedding generation")
            return []
        
        # Filter out empty texts
        valid_texts = [text.strip() for text in texts if text and text.strip()]
        
        if not valid_texts:
            raise ValueError("All provided texts are empty")
        
        try:
            # Generate embeddings in batches
            embeddings = self.model.encode(
                valid_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )
            
            # Convert to list of lists
            return [emb.tolist() for emb in embeddings]
        
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise
    
    def chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
        separator: str = " "
    ) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            chunk_size: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
            separator: Token separator (default: space for word-level chunking)
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # Split text into tokens (words)
        tokens = text.strip().split(separator)
        
        if len(tokens) <= chunk_size:
            # Text is small enough, return as single chunk
            return [text.strip()]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Get chunk of tokens
            end = start + chunk_size
            chunk_tokens = tokens[start:end]
            
            # Join tokens back into text
            chunk_text = separator.join(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start position with overlap
            start += chunk_size - overlap
            
            # Prevent infinite loop if overlap >= chunk_size
            if overlap >= chunk_size:
                break
        
        logger.info(
            f"Chunked text into {len(chunks)} chunks "
            f"(chunk_size={chunk_size}, overlap={overlap})"
        )
        return chunks
    
    def generate_embeddings_for_chunks(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """
        Chunk text and generate embeddings for each chunk
        
        Args:
            text: Input text to chunk and embed
            chunk_size: Maximum number of tokens per chunk
            overlap: Number of tokens to overlap between chunks
            batch_size: Batch size for embedding generation
            
        Returns:
            List of dictionaries with 'text' and 'embedding' keys
        """
        # Chunk the text
        chunks = self.chunk_text(text, chunk_size, overlap)
        
        if not chunks:
            return []
        
        # Generate embeddings for all chunks
        embeddings = self.batch_generate_embeddings(
            chunks,
            batch_size=batch_size,
            show_progress=False
        )
        
        # Combine chunks with their embeddings
        results = []
        for chunk_text, embedding in zip(chunks, embeddings):
            results.append({
                "text": chunk_text,
                "embedding": embedding
            })
        
        return results
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model
        
        Returns:
            Embedding dimension
        """
        return self.embedding_dimension


@lru_cache(maxsize=1)
def get_embedding_generator() -> EmbeddingGenerator:
    """
    Get cached embedding generator instance
    
    Returns:
        EmbeddingGenerator instance
    """
    settings = get_settings()
    
    # Use paraphrase-multilingual-MiniLM-L12-v2 for multilingual support
    # This model supports 50+ languages including all Indian languages
    # Embedding dimension: 384
    return EmbeddingGenerator(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device="cpu"  # Use CPU for compatibility; can be changed to "cuda" if GPU available
    )
