"""Async Redis-based session storage for Y-Connect WhatsApp Bot"""

from typing import Optional
import json
import logging
from datetime import datetime

import aioredis
from aioredis import Redis, ConnectionPool

from app.config import get_settings
from app.models import UserSession, Message

logger = logging.getLogger(__name__)
settings = get_settings()


class AsyncRedisSessionStore:
    """Async Redis-based session storage with TTL support"""
    
    _instance: Optional['AsyncRedisSessionStore'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[Redis] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection pool if not already initialized"""
        pass
    
    async def _initialize_connection(self) -> None:
        """Create async Redis connection pool and client"""
        if self._initialized:
            return
        
        try:
            # Create Redis client with connection pool
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
            logger.info(
                f"Async Redis connection established: "
                f"{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to async Redis: {e}")
            raise
    
    async def ensure_initialized(self) -> None:
        """Ensure Redis connection is initialized"""
        if not self._initialized:
            await self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Async Redis client not initialized")
    
    def _get_session_key(self, phone_number: str) -> str:
        """
        Generate Redis key for a user session
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Redis key string
        """
        return f"session:{phone_number}"
    
    async def store_session(self, session: UserSession) -> bool:
        """
        Store a user session in Redis with TTL (async)
        
        Args:
            session: UserSession object to store
            
        Returns:
            True if storage successful, False otherwise
        """
        await self.ensure_initialized()
        
        key = self._get_session_key(session.phone_number)
        
        try:
            # Convert session to JSON-serializable dict
            session_data = {
                'session_id': session.session_id,
                'phone_number': session.phone_number,
                'language': session.language,
                'conversation_history': [
                    {
                        'role': msg.role.value,
                        'content': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'language': msg.language
                    }
                    for msg in session.conversation_history
                ],
                'user_context': session.user_context,
                'created_at': session.created_at.isoformat(),
                'last_active': session.last_active.isoformat(),
                'is_new_user': session.is_new_user
            }
            
            # Store in Redis with TTL
            await self._client.setex(
                key,
                settings.redis_session_ttl,
                json.dumps(session_data)
            )
            
            logger.debug(f"Session stored for {session.phone_number} with TTL {settings.redis_session_ttl}s")
            return True
        except Exception as e:
            logger.error(f"Error storing session for {session.phone_number}: {e}")
            return False
    
    async def get_session(self, phone_number: str) -> Optional[UserSession]:
        """
        Retrieve a user session from Redis (async)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserSession object if found, None otherwise
        """
        await self.ensure_initialized()
        
        key = self._get_session_key(phone_number)
        
        try:
            session_json = await self._client.get(key)
            
            if not session_json:
                logger.debug(f"No session found for {phone_number}")
                return None
            
            # Parse JSON data
            session_data = json.loads(session_json)
            
            # Reconstruct UserSession object
            session = UserSession(
                session_id=session_data['session_id'],
                phone_number=session_data['phone_number'],
                language=session_data['language'],
                conversation_history=[
                    Message(
                        role=msg['role'],
                        content=msg['content'],
                        timestamp=datetime.fromisoformat(msg['timestamp']),
                        language=msg['language']
                    )
                    for msg in session_data['conversation_history']
                ],
                user_context=session_data['user_context'],
                created_at=datetime.fromisoformat(session_data['created_at']),
                last_active=datetime.fromisoformat(session_data['last_active']),
                is_new_user=session_data['is_new_user']
            )
            
            logger.debug(f"Session retrieved for {phone_number}")
            return session
        except Exception as e:
            logger.error(f"Error retrieving session for {phone_number}: {e}")
            return None
    
    async def update_session(self, session: UserSession) -> bool:
        """
        Update an existing session (async)
        
        Args:
            session: UserSession object to update
            
        Returns:
            True if update successful, False otherwise
        """
        return await self.store_session(session)
    
    async def delete_session(self, phone_number: str) -> bool:
        """
        Delete a user session from Redis (async)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if deletion successful, False otherwise
        """
        await self.ensure_initialized()
        
        key = self._get_session_key(phone_number)
        
        try:
            result = await self._client.delete(key)
            
            if result > 0:
                logger.info(f"Session deleted for {phone_number}")
                return True
            else:
                logger.debug(f"No session found to delete for {phone_number}")
                return False
        except Exception as e:
            logger.error(f"Error deleting session for {phone_number}: {e}")
            return False
    
    async def session_exists(self, phone_number: str) -> bool:
        """
        Check if a session exists for a phone number (async)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if session exists, False otherwise
        """
        await self.ensure_initialized()
        
        key = self._get_session_key(phone_number)
        
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking session existence for {phone_number}: {e}")
            return False
    
    async def get_session_ttl(self, phone_number: str) -> Optional[int]:
        """
        Get remaining TTL for a session (async)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Remaining TTL in seconds, None if session doesn't exist or error
        """
        await self.ensure_initialized()
        
        key = self._get_session_key(phone_number)
        
        try:
            ttl = await self._client.ttl(key)
            
            # TTL returns -2 if key doesn't exist, -1 if no expiry set
            if ttl < 0:
                return None
            
            return ttl
        except Exception as e:
            logger.error(f"Error getting TTL for {phone_number}: {e}")
            return None
    
    async def clear_all_sessions(self) -> int:
        """
        Clear all sessions (async, for testing/development only)
        
        WARNING: This will delete all session data!
        
        Returns:
            Number of sessions deleted
        """
        await self.ensure_initialized()
        
        try:
            # Find all session keys
            keys = []
            async for key in self._client.scan_iter("session:*"):
                keys.append(key)
            
            if not keys:
                logger.info("No sessions to clear")
                return 0
            
            # Delete all session keys
            count = await self._client.delete(*keys)
            logger.warning(f"Cleared {count} sessions from Redis")
            return count
        except Exception as e:
            logger.error(f"Error clearing all sessions: {e}")
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
            logger.error(f"Async Redis connection check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            logger.info("Async Redis connection closed")
            self._client = None
            self._initialized = False


# Global async session store instance
async_session_store = AsyncRedisSessionStore()
