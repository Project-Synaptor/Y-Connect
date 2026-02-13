"""Session Manager for Y-Connect WhatsApp Bot

Manages user conversation sessions using Redis for storage with 24-hour TTL.
Handles session creation, updates, and cleanup with PII anonymization.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import redis
from redis.exceptions import RedisError

from app.config import get_settings
from app.models import UserSession, Message
from app.data_anonymization import DataAnonymizer, SessionDataCleaner

logger = logging.getLogger(__name__)
settings = get_settings()


class SessionManager:
    """Manages user conversation sessions with Redis backend"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize SessionManager
        
        Args:
            redis_client: Optional Redis client instance (for testing)
        """
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        
        self.session_ttl = settings.redis_session_ttl
        logger.info(
            f"SessionManager initialized with Redis at "
            f"{settings.redis_host}:{settings.redis_port}"
        )
    
    def _generate_session_id(self, phone_number: str) -> str:
        """
        Generate a unique session ID from phone number using secure hashing
        
        Args:
            phone_number: User's phone number
            
        Returns:
            Hashed session ID for privacy
        """
        # Use DataAnonymizer for consistent hashing with app secret as salt
        return DataAnonymizer.generate_session_id(
            phone_number,
            salt=settings.whatsapp_app_secret
        )
    
    def _serialize_session(self, session: UserSession) -> str:
        """
        Serialize UserSession to JSON string
        
        Args:
            session: UserSession object
            
        Returns:
            JSON string representation
        """
        # Convert to dict and handle datetime serialization
        session_dict = session.model_dump()
        
        # Convert datetime objects to ISO format strings
        session_dict['created_at'] = session.created_at.isoformat()
        session_dict['last_active'] = session.last_active.isoformat()
        
        # Convert conversation history messages
        for msg in session_dict['conversation_history']:
            msg['timestamp'] = msg['timestamp'].isoformat()
        
        return json.dumps(session_dict)
    
    def _deserialize_session(self, session_json: str) -> UserSession:
        """
        Deserialize JSON string to UserSession
        
        Args:
            session_json: JSON string representation
            
        Returns:
            UserSession object
        """
        session_dict = json.loads(session_json)
        
        # Convert ISO format strings back to datetime objects
        session_dict['created_at'] = datetime.fromisoformat(session_dict['created_at'])
        session_dict['last_active'] = datetime.fromisoformat(session_dict['last_active'])
        
        # Convert conversation history message timestamps
        for msg in session_dict['conversation_history']:
            msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
        
        return UserSession(**session_dict)
    
    def get_or_create_session(self, phone_number: str) -> UserSession:
        """
        Retrieve existing session or create new one
        
        Args:
            phone_number: User's WhatsApp phone number
            
        Returns:
            UserSession object with conversation history
            
        Raises:
            RedisError: If Redis connection fails
        """
        session_id = self._generate_session_id(phone_number)
        
        try:
            # Try to get existing session
            session_json = self.redis_client.get(session_id)
            
            if session_json:
                # Existing session found
                session = self._deserialize_session(session_json)
                session.is_new_user = False
                session.last_active = datetime.utcnow()
                
                # Update session in Redis with refreshed TTL
                self.redis_client.setex(
                    session_id,
                    self.session_ttl,
                    self._serialize_session(session)
                )
                
                logger.info(f"Retrieved existing session for user (session_id: {session_id[:16]}...)")
                return session
            else:
                # Create new session
                session = UserSession(
                    session_id=session_id,
                    phone_number=phone_number,
                    is_new_user=True
                )
                
                # Store in Redis with TTL
                self.redis_client.setex(
                    session_id,
                    self.session_ttl,
                    self._serialize_session(session)
                )
                
                logger.info(f"Created new session for user (session_id: {session_id[:16]}...)")
                return session
                
        except RedisError as e:
            logger.error(f"Redis error in get_or_create_session: {e}")
            raise
    
    def update_session(self, session_id: str, message: Message, response: str) -> None:
        """
        Update session with new message and response
        
        Args:
            session_id: Unique session identifier
            message: User's message
            response: Bot's response
            
        Raises:
            RedisError: If Redis connection fails
            ValueError: If session not found
        """
        try:
            # Get existing session
            session_json = self.redis_client.get(session_id)
            
            if not session_json:
                raise ValueError(f"Session not found: {session_id}")
            
            session = self._deserialize_session(session_json)
            
            # Add user message
            session.add_message(message)
            
            # Add bot response
            response_message = Message(
                role="assistant",
                content=response,
                language=message.language
            )
            session.add_message(response_message)
            
            # Update last_active timestamp
            session.last_active = datetime.utcnow()
            
            # Save updated session with refreshed TTL
            self.redis_client.setex(
                session_id,
                self.session_ttl,
                self._serialize_session(session)
            )
            
            logger.debug(f"Updated session {session_id[:16]}... with new messages")
            
        except RedisError as e:
            logger.error(f"Redis error in update_session: {e}")
            raise
    
    def clear_expired_sessions(self) -> int:
        """
        Remove sessions inactive for >24 hours with PII cleanup
        
        This is a background task that should be run periodically.
        Redis TTL handles automatic expiration, but this method can be used
        for manual cleanup or verification. Ensures all PII is removed before deletion.
        
        Returns:
            Number of sessions cleared
            
        Raises:
            RedisError: If Redis connection fails
        """
        try:
            # Get all session keys
            session_keys = self.redis_client.keys("session:*")
            
            cleared_count = 0
            current_time = datetime.utcnow()
            
            for key in session_keys:
                try:
                    session_json = self.redis_client.get(key)
                    if not session_json:
                        continue
                    
                    session = self._deserialize_session(session_json)
                    
                    # Check if session is expired (>24 hours inactive)
                    time_since_active = current_time - session.last_active
                    if time_since_active > timedelta(hours=24):
                        # Prepare session for deletion (remove PII)
                        session_dict = session.model_dump()
                        cleaned_metadata = SessionDataCleaner.prepare_session_for_deletion(session_dict)
                        
                        # Verify PII is removed
                        if not SessionDataCleaner.verify_pii_removed(cleaned_metadata):
                            logger.error(
                                f"PII still present in session after cleanup: {key[:24]}...",
                                extra={"session_key": key[:24]}
                            )
                        
                        # Delete session from Redis
                        self.redis_client.delete(key)
                        cleared_count += 1
                        
                        # Log cleanup with anonymized info
                        logger.info(
                            "Cleared expired session with PII cleanup",
                            extra={
                                "session_key": key[:24] + "...",
                                "inactive_hours": time_since_active.total_seconds() / 3600,
                                "message_count": cleaned_metadata.get('message_count', 0)
                            }
                        )
                        
                except (json.JSONDecodeError, ValueError) as e:
                    # Invalid session data, delete it
                    logger.warning(f"Deleting invalid session {key[:24]}...: {e}")
                    self.redis_client.delete(key)
                    cleared_count += 1
            
            if cleared_count > 0:
                logger.info(f"Cleared {cleared_count} expired sessions with PII cleanup")
            
            return cleared_count
            
        except RedisError as e:
            logger.error(f"Redis error in clear_expired_sessions: {e}")
            raise
    
    def get_session(self, phone_number: str) -> Optional[UserSession]:
        """
        Get existing session without creating a new one
        
        Args:
            phone_number: User's phone number
            
        Returns:
            UserSession if exists, None otherwise
        """
        session_id = self._generate_session_id(phone_number)
        
        try:
            session_json = self.redis_client.get(session_id)
            if session_json:
                return self._deserialize_session(session_json)
            return None
        except RedisError as e:
            logger.error(f"Redis error in get_session: {e}")
            raise
    
    def delete_session(self, phone_number: str) -> bool:
        """
        Delete a session (for testing or manual cleanup)
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if session was deleted, False if not found
        """
        session_id = self._generate_session_id(phone_number)
        
        try:
            result = self.redis_client.delete(session_id)
            if result > 0:
                logger.info(f"Deleted session for user (session_id: {session_id[:16]}...)")
                return True
            return False
        except RedisError as e:
            logger.error(f"Redis error in delete_session: {e}")
            raise
    
    def update_session_language(self, phone_number: str, language: str) -> None:
        """
        Update the detected language for a session
        
        Args:
            phone_number: User's phone number
            language: Detected language code
            
        Raises:
            ValueError: If session not found
        """
        session_id = self._generate_session_id(phone_number)
        
        try:
            session_json = self.redis_client.get(session_id)
            if not session_json:
                raise ValueError(f"Session not found for phone: {phone_number}")
            
            session = self._deserialize_session(session_json)
            session.language = language
            session.last_active = datetime.utcnow()
            
            # Save updated session
            self.redis_client.setex(
                session_id,
                self.session_ttl,
                self._serialize_session(session)
            )
            
            logger.debug(f"Updated language to {language} for session {session_id[:16]}...")
            
        except RedisError as e:
            logger.error(f"Redis error in update_session_language: {e}")
            raise
    
    def update_session_context(self, phone_number: str, context_updates: dict) -> None:
        """
        Update user context in session
        
        Args:
            phone_number: User's phone number
            context_updates: Dictionary of context updates
            
        Raises:
            ValueError: If session not found
        """
        session_id = self._generate_session_id(phone_number)
        
        try:
            session_json = self.redis_client.get(session_id)
            if not session_json:
                raise ValueError(f"Session not found for phone: {phone_number}")
            
            session = self._deserialize_session(session_json)
            session.update_context(context_updates)
            
            # Save updated session
            self.redis_client.setex(
                session_id,
                self.session_ttl,
                self._serialize_session(session)
            )
            
            logger.debug(f"Updated context for session {session_id[:16]}...")
            
        except RedisError as e:
            logger.error(f"Redis error in update_session_context: {e}")
            raise
    
    def check_connection(self) -> bool:
        """
        Check if Redis connection is working
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            return self.redis_client.ping()
        except RedisError as e:
            logger.error(f"Redis connection check failed: {e}")
            return False
