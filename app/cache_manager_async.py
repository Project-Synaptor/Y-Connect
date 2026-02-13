"""Async caching layer for Y-Connect WhatsApp Bot using Redis"""

from typing import Optional, List, Dict, Any
import json
import logging
import hashlib

import aioredis
from aioredis import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AsyncCacheManager:
    """Async Redis-based caching for schemes, language detection, and embeddings"""
    
    _instance: Optional['AsyncCacheManager'] = None
    _client: Optional[Redis] = None
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
    
    async def _initialize_connection(self) -> None:
        """Create async Redis connection"""
        if self._initialized:
            return
        
        try:
            redis_url = settings.redis_url
            self._client = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Test connection
            await self._client.ping()
            
            self._initialized = True
            logger.info("Async cache manager Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for async caching: {e}")
            raise
    
    async def _ensure_initialized(self) -> None:
        """Ensure Redis connection is initialized"""
        if not self._initialized:
            await self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Async Redis client not initialized")
    
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
    
    async def cache_scheme(self, scheme_id: str, scheme_data: Dict[str, Any]) -> bool:
        """
        Cache scheme data (async)
        
        Args:
            scheme_id: Unique scheme identifier
            scheme_data: Scheme data dictionary
            
        Returns:
            True if caching successful, False otherwise
        """
        await self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            await self._client.setex(
                key,
                self.SCHEME_CACHE_TTL,
                json.dumps(scheme_data)
            )
            logger.debug(f"Cached scheme {scheme_id} with TTL {self.SCHEME_CACHE_TTL}s")
            return True
        except Exception as e:
            logger.error(f"Error caching scheme {scheme_id}: {e}")
            return False
    
    async def get_cached_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached scheme data (async)
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            Scheme data dictionary if found, None otherwise
        """
        await self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            cached_data = await self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for scheme {scheme_id}")
                return None
            
            logger.debug(f"Cache hit for scheme {scheme_id}")
            return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error retrieving cached scheme {scheme_id}: {e}")
            return None
    
    async def invalidate_scheme(self, scheme_id: str) -> bool:
        """
        Invalidate cached scheme data (async)
        
        Args:
            scheme_id: Unique scheme identifier
            
        Returns:
            True if invalidation successful, False otherwise
        """
        await self._ensure_initialized()
        
        key = f"{self.SCHEME_PREFIX}{scheme_id}"
        
        try:
            result = await self._client.delete(key)
            if result > 0:
                logger.info(f"Invalidated cache for scheme {scheme_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error invalidating scheme cache {scheme_id}: {e}")
            return False
    
    # Language detection caching methods
    
    async def cache_language_detection(
        self,
        text: str,
        language_code: str,
        language_name: str,
        confidence: float
    ) -> bool:
        """
        Cache language detection result (async)
        
        Args:
            text: Input text that was analyzed
            language_code: Detected language code
            language_name: Detected language name
            confidence: Detection confidence score
            
        Returns:
            True if caching successful, False otherwise
        """
        await self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.LANGUAGE_PREFIX}{text_hash}"
        
        result_data = {
            "language_code": language_code,
            "language_name": language_name,
            "confidence": confidence
        }
        
        try:
            await self._client.setex(
                key,
                self.LANGUAGE_CACHE_TTL,
                json.dumps(result_data)
            )
            logger.debug(f"Cached language detection for text hash {text_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error caching language detection: {e}")
            return False
    
    async def get_cached_language_detection(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached language detection result (async)
        
        Args:
            text: Input text to check
            
        Returns:
            Dictionary with language_code, language_name, and confidence if found, None otherwise
        """
        await self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.LANGUAGE_PREFIX}{text_hash}"
        
        try:
            cached_data = await self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for language detection {text_hash[:8]}...")
                return None
            
            logger.debug(f"Cache hit for language detection {text_hash[:8]}...")
            return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error retrieving cached language detection: {e}")
            return None
    
    # Embedding caching methods
    
    async def cache_embedding(self, text: str, embedding: List[float]) -> bool:
        """
        Cache embedding vector for text (async)
        
        Args:
            text: Input text that was embedded
            embedding: Embedding vector
            
        Returns:
            True if caching successful, False otherwise
        """
        await self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.EMBEDDING_PREFIX}{text_hash}"
        
        try:
            await self._client.setex(
                key,
                self.EMBEDDING_CACHE_TTL,
                json.dumps(embedding)
            )
            logger.debug(f"Cached embedding for text hash {text_hash[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Error caching embedding: {e}")
            return False
    
    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding vector (async)
        
        Args:
            text: Input text to check
            
        Returns:
            Embedding vector if found, None otherwise
        """
        await self._ensure_initialized()
        
        text_hash = self._generate_hash(text.lower().strip())
        key = f"{self.EMBEDDING_PREFIX}{text_hash}"
        
        try:
            cached_data = await self._client.get(key)
            
            if not cached_data:
                logger.debug(f"Cache miss for embedding {text_hash[:8]}...")
                return None
            
            logger.debug(f"Cache hit for embedding {text_hash[:8]}...")
            return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error retrieving cached embedding: {e}")
            return None
    
    # Batch operations
    
    async def cache_multiple_schemes(self, schemes: List[Dict[str, Any]]) -> int:
        """
        Cache multiple schemes in a pipeline for efficiency (async)
        
        Args:
            schemes: List of scheme dictionaries with 'scheme_id' key
            
        Returns:
            Number of schemes successfully cached
        """
        await self._ensure_initialized()
        
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
            
            results = await pipe.execute()
            success_count = sum(1 for r in results if r)
            
            logger.info(f"Cached {success_count}/{len(schemes)} schemes")
            return success_count
        except Exception as e:
            logger.error(f"Error caching multiple schemes: {e}")
            return 0
    
    # Cache statistics and management
    
    async def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics (async)
        
        Returns:
            Dictionary with counts of cached items by type
        """
        await self._ensure_initialized()
        
        try:
            scheme_keys = []
            language_keys = []
            embedding_keys = []
            
            async for key in self._client.scan_iter(f"{self.SCHEME_PREFIX}*"):
                scheme_keys.append(key)
            
            async for key in self._client.scan_iter(f"{self.LANGUAGE_PREFIX}*"):
                language_keys.append(key)
            
            async for key in self._client.scan_iter(f"{self.EMBEDDING_PREFIX}*"):
                embedding_keys.append(key)
            
            return {
                "schemes": len(scheme_keys),
                "language_detections": len(language_keys),
                "embeddings": len(embedding_keys),
                "total": len(scheme_keys) + len(language_keys) + len(embedding_keys)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"schemes": 0, "language_detections": 0, "embeddings": 0, "total": 0}
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache entries (async)
        
        Args:
            cache_type: Type of cache to clear ('schemes', 'language', 'embeddings', or None for all)
            
        Returns:
            Number of keys deleted
        """
        await self._ensure_initialized()
        
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
                    keys = []
                    async for key in self._client.scan_iter(pattern):
                        keys.append(key)
                    if keys:
                        total_deleted += await self._client.delete(*keys)
                
                logger.warning(f"Cleared {total_deleted} cache entries (all types)")
                return total_deleted
            
            keys = []
            async for key in self._client.scan_iter(pattern):
                keys.append(key)
            
            if not keys:
                logger.info(f"No cache entries found for type: {cache_type}")
                return 0
            
            count = await self._client.delete(*keys)
            logger.warning(f"Cleared {count} cache entries for type: {cache_type}")
            return count
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0
    
    async def check_connection(self) -> bool:
        """
        Check if Redis connection is working (async)
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not self._initialized:
            try:
                await self._initialize_connection()
            except Exception:
                return False
        
        if not self._client:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Async cache manager connection check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            logger.info("Async cache manager Redis connection closed")
            self._client = None
            self._initialized = False


# Global async cache manager instance
async_cache_manager = AsyncCacheManager()
