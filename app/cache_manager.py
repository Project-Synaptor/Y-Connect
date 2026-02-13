"""Caching layer for Y-Connect WhatsApp Bot using Redis"""

from typing import Optional, List, Dict, Any
import json
import logging
import hashlib
from datetime import timedelta

import redis
from redis.connection import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CacheManager:
    """Redis-based caching for schemes, language detection, and embeddings"""
    
    _instance: Optional['CacheManager'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _initialized: bool = False
    
    # Cache TTLs (in seconds)
    SCHEME_CACHE_TTL = 3600  # 1 hour for schemes
    EMBEDDING_CACHE_TTL = 86400  # 24 hours for embeddings
    LANGUAGE_CACHE_TTL = 86400  # 24 hours for language detection
    
    # Cache key prefixes
    SCHEME_PREFIX = "cache:scheme:"
    EMBEDDING_PREFIX = "cache:embedding:"
    LANGUAGE_PREFIX = "cache:language:"
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection pool if not already initialized"""
        pass
    
    def _initialize_connection(self) -> None:
        """Create Redis connection pool and client"""
        if self._initialized:
            return
        
        try:
            # Create connection pool
            self._pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password if settings.redis_password else None,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            
            self._initialized = True
            logger.info("Cache manager Redis connection established")
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis for caching: {e}")
            raise
    
    def _ensure_initialized(self) -> None:
        """Ensure Redis connection is initialized"""
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
    
    def _generate_hash(self, text: str) -> str:
        """
        Generate a hash for text to use as cache key
        
        Args:
            text: Input text to hash
            
        Returns:
            SHA256 hash of the text
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    # Scheme caching methods
    
    def cache_scheme(self, scheme_id: str, scheme_data: Dict[str, Any]) -> bool:
        """
        Cache scheme data
        
        Args:
            scheme_id: Unique scheme identifier
            scheme_data: Scheme data dictionary
            
        Returns:
            True if caching successful, False otherwise
        """
        self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            self._client.setex(
                key,
                self.SCHEME_CACHE_TTL,
                json.dumps(scheme_data)
            )
            logger.debug(f"Cached scheme {scheme_id} with TTL {self.SCHEME_CACHE_TTL}s")
            return True
        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error(f"Error caching scheme {scheme_id}: {e}")
            return False
    
    def get_cached_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached scheme data
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            Scheme data dictionary if found, None otherwise
        """
        self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            cached_data = self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for scheme {scheme_id}")
                return None
            
            logger.debug(f"Cache hit for scheme {scheme_id}")
            return json.loads(cached_data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached scheme {scheme_id}: {e}")
            return None
    
    def invalidate_scheme(self, scheme_id: str) -> bool:
        """
        Invalidate cached scheme data
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            True if invalidation successful, False otherwise
        """
        self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            result = self._client.delete(key)
            if result > 0:
                logger.info(f"Invalidated cache for scheme {scheme_id}")
                return True
            return False
        except redis.RedisError as e:
            logger.error(f"Error invalidating scheme cache {scheme_id}: {e}")
            return False
    
    # Language detection caching methods
    
    def cache_language_detection(
        self,
        text: str,
        language_code: str,
        language_name: str,
        confidence: float
    ) -> bool:
        """
        Cache language detection result
        
        Args:
            text: Input text that was analyzed
            language_code: Detected language code
            language_name: Detected language name
            confidence: Detection confidence score
            
        Returns:
            True if caching successful, False otherwise
        """
        self._ensure_initialized()
        
        # Generate hash of text for cache key
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.LANGUAGE_PREFIX}{text_hash}"
        
        result_data = {
            "language_code": language_code,
            "language_name": language_name,
            "confidence": confidence
        }
        
        try:
            self._client.setex(
                key,
                self.LANGUAGE_CACHE_TTL,
                json.dumps(result_data)
            )
            logger.debug(f"Cached language detection for text hash {text_hash[:8]}...")
            return True
        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error(f"Error caching language detection: {e}")
            return False
    
    def get_cached_language_detection(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached language detection result
        
        Args:
            text: Input text to check
            
        Returns:
            Dictionary with language_code, language_name, and confidence if found, None otherwise
        """
        self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.LANGUAGE_PREFIX}{text_hash}"
        
        try:
            cached_data = self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for language detection {text_hash[:8]}...")
                return None
            
            logger.debug(f"Cache hit for language detection {text_hash[:8]}...")
            return json.loads(cached_data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached language detection: {e}")
            return None
    
    # Embedding caching methods
    
    def cache_embedding(self, text: str, embedding: List[float]) -> bool:
        """
        Cache embedding vector for text
        
        Args:
            text: Input text that was embedded
            embedding: Embedding vector
            
        Returns:
            True if caching successful, False otherwise
        """
        self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.EMBEDDING_PREFIX}{text_hash}"
        
        try:
            self._client.setex(
                key,
                self.EMBEDDING_CACHE_TTL,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding for text hash {text_hash[:8]}...")
            return True
        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding vector
        
        Args:
            text: Input text to check
            
        Returns:
            Embedding vector if found, None otherwise
        """
        self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.EMBEDDING_PREFIX}{text_hash}"
        
        try:
            cached_data = self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for embedding {text_hash[:8]}...")
                return None
            
            logger.debug(f"Cache hit for embedding {text_hash[:8]}...")
            return json.loads(cached_data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            return None
    
    # Batch operations
    
    def cache_multiple_schemes(self, schemes: List[Dict[str, Any]]) -> int:
        """
        Cache multiple schemes in a pipeline for efficiency
        
        Args:
            schemes: List of scheme dictionaries with 'scheme_id' key
            
        Returns:
            Number of schemes successfully cached
        """
        self._ensure_initialized()
        
        if not schemes:
            return 0
        
        try:
            pipe = self._client.pipeline()
            
            for scheme in schemes:
                scheme_id = scheme.get('scheme_id')
                if not scheme_id:
                    continue
                
                key = f"{self.SCHEME_PREFIX}{scheme_id}"
                pipe.setex(key, self.SCHEME_CACHE_TTL, json.dumps(scheme))
            
            results = pipe.execute()
            success_count = sum(1 for r in results if r)
            
            logger.info(f"Cached {success_count}/{len(schemes)} schemes")
            return success_count
        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error(f"Error caching multiple schemes: {e}")
            return 0
    
    # Cache statistics and management
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with counts of cached items by type
        """
        self._ensure_initialized()
        
        try:
            scheme_count = len(self._client.keys(f"{self.SCHEME_PREFIX}*"))
            language_count = len(self._client.keys(f"{self.LANGUAGE_PREFIX}*"))
            embedding_count = len(self._client.keys(f"{self.EMBEDDING_PREFIX}*"))
            
            return {
                "schemes": scheme_count,
                "language_detections": language_count,
                "embeddings": embedding_count,
                "total": scheme_count + language_count + embedding_count
            }
        except redis.RedisError as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"schemes": 0, "language_detections": 0, "embeddings": 0, "total": 0}
    
    def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache entries
        
        Args:
            cache_type: Type of cache to clear ('schemes', 'language', 'embeddings', or None for all)
            
        Returns:
            Number of keys deleted
        """
        self._ensure_initialized()
        
        try:
            if cache_type == "schemes":
                pattern = f"{self.SCHEME_PREFIX}*"
            elif cache_type == "language":
                pattern = f"{self.LANGUAGE_PREFIX}*"
            elif cache_type == "embeddings":
                pattern = f"{self.EMBEDDING_PREFIX}*"
            else:
                # Clear all cache types
                patterns = [
                    f"{self.SCHEME_PREFIX}*",
                    f"{self.LANGUAGE_PREFIX}*",
                    f"{self.EMBEDDING_PREFIX}*"
                ]
                total_deleted = 0
                for pattern in patterns:
                    keys = self._client.keys(pattern)
                    if keys:
                        total_deleted += self._client.delete(*keys)
                
                logger.warning(f"Cleared {total_deleted} cache entries (all types)")
                return total_deleted
            
            keys = self._client.keys(pattern)
            if not keys:
                logger.info(f"No cache entries found for type: {cache_type}")
                return 0
            
            count = self._client.delete(*keys)
            logger.warning(f"Cleared {count} cache entries for type: {cache_type}")
            return count
        except redis.RedisError as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    def check_connection(self) -> bool:
        """
        Check if Redis connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not self._initialized:
            try:
                self._initialize_connection()
            except redis.RedisError:
                return False
        
        if not self._client:
            return False
        
        try:
            self._client.ping()
            return True
        except redis.RedisError as e:
            logger.error(f"Cache manager connection check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close Redis connection pool"""
        if self._pool:
            self._pool.disconnect()
            logger.info("Cache manager Redis connection pool closed")
            self._client = None
            self._pool = None


# Global cache manager instance
cache_manager = CacheManager()
