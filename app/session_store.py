"""Redis-based session storage for Y-Connect WhatsApp Bot"""

from typing import Optional
import json
import logging
from datetime import datetime

import redis
from redis.connection import ConnectionPool

from app.config import get_settings
from app.models import UserSession, Message

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisSessionStore:
    """Redis-based session storage with TTL support"""
    
    _instance: Optional['RedisSessionStore'] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern to ensure single Redis connection pool"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Redis connection pool if not already initialized"""
        # Don't auto-initialize to allow lazy loading
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
                decode_responses=True,  # Automatically decode bytes to strings
                max_connections=50,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            
            self._initialized = True
            logger.info(
                f"Redis connection established: "
                f"{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            )
        except redis.RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _get_session_key(self, phone_number: str) -> str:
        """
        Generate Redis key for a user session
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Redis key string
        """
        return f"session:{phone_number}"
    
    def store_session(self, session: UserSession) -> bool:
        """
        Store a user session in Redis with TTL
        
        Args:
            session: UserSession object to store
            
        Returns:
            True if storage successful, False otherwise
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
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
            self._client.setex(
                key,
                settings.redis_session_ttl,
                json.dumps(session_data)
            )
            
            logger.debug(f"Session stored for {session.phone_number} with TTL {settings.redis_session_ttl}s")
            return True
        except redis.RedisError as e:
            logger.error(f"Error storing session for {session.phone_number}: {e}")
            return False
        except (TypeError, ValueError) as e:
            logger.error(f"Error serializing session data: {e}")
            return False
    
    def get_session(self, phone_number: str) -> Optional[UserSession]:
        """
        Retrieve a user session from Redis
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserSession object if found, None otherwise
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
        key = self._get_session_key(phone_number)
        
        try:
            session_json = self._client.get(key)
            
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
        except redis.RedisError as e:
            logger.error(f"Error retrieving session for {phone_number}: {e}")
            return None
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error deserializing session data for {phone_number}: {e}")
            return None
    
    def update_session(self, session: UserSession) -> bool:
        """
        Update an existing session (same as store_session with refreshed TTL)
        
        Args:
            session: UserSession object to update
            
        Returns:
            True if update successful, False otherwise
        """
        return self.store_session(session)
    
    def delete_session(self, phone_number: str) -> bool:
        """
        Delete a user session from Redis
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
        key = self._get_session_key(phone_number)
        
        try:
            result = self._client.delete(key)
            
            if result > 0:
                logger.info(f"Session deleted for {phone_number}")
                return True
            else:
                logger.debug(f"No session found to delete for {phone_number}")
                return False
        except redis.RedisError as e:
            logger.error(f"Error deleting session for {phone_number}: {e}")
            return False
    
    def session_exists(self, phone_number: str) -> bool:
        """
        Check if a session exists for a phone number
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if session exists, False otherwise
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
        key = self._get_session_key(phone_number)
        
        try:
            return self._client.exists(key) > 0
        except redis.RedisError as e:
            logger.error(f"Error checking session existence for {phone_number}: {e}")
            return False
    
    def get_session_ttl(self, phone_number: str) -> Optional[int]:
        """
        Get remaining TTL for a session
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Remaining TTL in seconds, None if session doesn't exist or error
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
        key = self._get_session_key(phone_number)
        
        try:
            ttl = self._client.ttl(key)
            
            # TTL returns -2 if key doesn't exist, -1 if no expiry set
            if ttl < 0:
                return None
            
            return ttl
        except redis.RedisError as e:
            logger.error(f"Error getting TTL for {phone_number}: {e}")
            return None
    
    def clear_all_sessions(self) -> int:
        """
        Clear all sessions (for testing/development only)
        
        WARNING: This will delete all session data!
        
        Returns:
            Number of sessions deleted
        """
        if not self._initialized:
            self._initialize_connection()
        
        if not self._client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            # Find all session keys
            keys = self._client.keys("session:*")
            
            if not keys:
                logger.info("No sessions to clear")
                return 0
            
            # Delete all session keys
            count = self._client.delete(*keys)
            logger.warning(f"Cleared {count} sessions from Redis")
            return count
        except redis.RedisError as e:
            logger.error(f"Error clearing all sessions: {e}")
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
            logger.error(f"Redis connection check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close Redis connection pool"""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection pool closed")
            self._client = None
            self._pool = None


# Global session store instance
session_store = RedisSessionStore()
