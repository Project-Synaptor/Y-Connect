"""Unit tests for SessionManager

Tests specific functionality and edge cases for session management.
"""

import pytest
from datetime import datetime, timedelta
import fakeredis
from redis.exceptions import RedisError

from app.session_manager import SessionManager
from app.models import Message, MessageRole, UserSession


@pytest.fixture
def fake_redis():
    """Provide a fake Redis client for testing"""
    return fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture
def session_manager(fake_redis):
    """Provide a SessionManager instance with fake Redis"""
    return SessionManager(redis_client=fake_redis)


def test_create_new_session(session_manager):
    """Test creating a new session for a user"""
    phone = "+911234567890"
    
    session = session_manager.get_or_create_session(phone)
    
    assert session is not None
    assert session.phone_number == phone
    assert session.is_new_user is True
    assert len(session.conversation_history) == 0
    assert len(session.user_context) == 0
    assert session.language == "en"  # Default language


def test_retrieve_existing_session(session_manager):
    """Test retrieving an existing session"""
    phone = "+911234567890"
    
    # Create session
    session1 = session_manager.get_or_create_session(phone)
    session1_id = session1.session_id
    
    # Retrieve same session
    session2 = session_manager.get_or_create_session(phone)
    
    assert session2.session_id == session1_id
    assert session2.phone_number == phone
    assert session2.is_new_user is False  # Not new anymore


def test_update_session_with_messages(session_manager):
    """Test updating session with new messages"""
    phone = "+911234567890"
    
    session = session_manager.get_or_create_session(phone)
    
    # Add a message
    user_message = Message(
        role=MessageRole.USER,
        content="Hello, I need help with schemes",
        language="en"
    )
    response = "Sure, I can help you with government schemes."
    
    session_manager.update_session(session.session_id, user_message, response)
    
    # Retrieve and verify
    updated_session = session_manager.get_session(phone)
    assert len(updated_session.conversation_history) == 2  # User + bot message
    assert updated_session.conversation_history[0].role == MessageRole.USER
    assert updated_session.conversation_history[0].content == user_message.content
    assert updated_session.conversation_history[1].role == MessageRole.ASSISTANT
    assert updated_session.conversation_history[1].content == response


def test_update_session_language(session_manager):
    """Test updating session language"""
    phone = "+911234567890"
    
    session = session_manager.get_or_create_session(phone)
    assert session.language == "en"
    
    # Update language
    session_manager.update_session_language(phone, "hi")
    
    # Verify
    updated_session = session_manager.get_session(phone)
    assert updated_session.language == "hi"


def test_update_session_context(session_manager):
    """Test updating session context"""
    phone = "+911234567890"
    
    session = session_manager.get_or_create_session(phone)
    
    # Update context
    context = {
        "age": 35,
        "occupation": "farmer",
        "location": "Punjab"
    }
    session_manager.update_session_context(phone, context)
    
    # Verify
    updated_session = session_manager.get_session(phone)
    assert updated_session.user_context["age"] == 35
    assert updated_session.user_context["occupation"] == "farmer"
    assert updated_session.user_context["location"] == "Punjab"


def test_delete_session(session_manager):
    """Test deleting a session"""
    phone = "+911234567890"
    
    # Create session
    session = session_manager.get_or_create_session(phone)
    assert session is not None
    
    # Delete session
    result = session_manager.delete_session(phone)
    assert result is True
    
    # Verify deletion
    retrieved_session = session_manager.get_session(phone)
    assert retrieved_session is None


def test_delete_nonexistent_session(session_manager):
    """Test deleting a session that doesn't exist"""
    phone = "+911234567890"
    
    result = session_manager.delete_session(phone)
    assert result is False


def test_clear_expired_sessions(session_manager, fake_redis):
    """Test clearing expired sessions"""
    phone1 = "+911234567890"
    phone2 = "+911234567891"
    
    # Create two sessions
    session1 = session_manager.get_or_create_session(phone1)
    session2 = session_manager.get_or_create_session(phone2)
    
    # Make session1 expired (>24 hours old)
    session1.last_active = datetime.utcnow() - timedelta(hours=25)
    session_json = session_manager._serialize_session(session1)
    fake_redis.setex(session1.session_id, session_manager.session_ttl, session_json)
    
    # Keep session2 active
    session2.last_active = datetime.utcnow() - timedelta(hours=1)
    session_json = session_manager._serialize_session(session2)
    fake_redis.setex(session2.session_id, session_manager.session_ttl, session_json)
    
    # Clear expired sessions
    cleared_count = session_manager.clear_expired_sessions()
    
    assert cleared_count == 1
    
    # Verify session1 is deleted
    assert session_manager.get_session(phone1) is None
    
    # Verify session2 still exists
    assert session_manager.get_session(phone2) is not None


def test_session_id_generation_consistency(session_manager):
    """Test that same phone number generates same session ID"""
    phone = "+911234567890"
    
    session_id1 = session_manager._generate_session_id(phone)
    session_id2 = session_manager._generate_session_id(phone)
    
    assert session_id1 == session_id2


def test_session_id_uniqueness(session_manager):
    """Test that different phone numbers generate different session IDs"""
    phone1 = "+911234567890"
    phone2 = "+911234567891"
    
    session_id1 = session_manager._generate_session_id(phone1)
    session_id2 = session_manager._generate_session_id(phone2)
    
    assert session_id1 != session_id2


def test_session_serialization_deserialization(session_manager):
    """Test session serialization and deserialization"""
    phone = "+911234567890"
    
    # Create session with data
    session = session_manager.get_or_create_session(phone)
    session.language = "hi"
    session.user_context = {"age": 30, "location": "Delhi"}
    session.add_message(Message(
        role=MessageRole.USER,
        content="Test message",
        language="hi"
    ))
    
    # Serialize
    session_json = session_manager._serialize_session(session)
    
    # Deserialize
    deserialized_session = session_manager._deserialize_session(session_json)
    
    assert deserialized_session.phone_number == session.phone_number
    assert deserialized_session.language == session.language
    assert deserialized_session.user_context == session.user_context
    assert len(deserialized_session.conversation_history) == len(session.conversation_history)
    assert deserialized_session.conversation_history[0].content == session.conversation_history[0].content


def test_update_nonexistent_session_raises_error(session_manager):
    """Test that updating a nonexistent session raises ValueError"""
    phone = "+911234567890"
    session_id = session_manager._generate_session_id(phone)
    
    message = Message(
        role=MessageRole.USER,
        content="Test",
        language="en"
    )
    
    with pytest.raises(ValueError, match="Session not found"):
        session_manager.update_session(session_id, message, "Response")


def test_update_language_nonexistent_session_raises_error(session_manager):
    """Test that updating language for nonexistent session raises ValueError"""
    phone = "+911234567890"
    
    with pytest.raises(ValueError, match="Session not found"):
        session_manager.update_session_language(phone, "hi")


def test_update_context_nonexistent_session_raises_error(session_manager):
    """Test that updating context for nonexistent session raises ValueError"""
    phone = "+911234567890"
    
    with pytest.raises(ValueError, match="Session not found"):
        session_manager.update_session_context(phone, {"age": 30})


def test_check_connection(session_manager):
    """Test Redis connection check"""
    result = session_manager.check_connection()
    assert result is True


def test_multiple_message_updates(session_manager):
    """Test multiple message updates to same session"""
    phone = "+911234567890"
    
    session = session_manager.get_or_create_session(phone)
    
    # Add multiple messages
    for i in range(5):
        message = Message(
            role=MessageRole.USER,
            content=f"Message {i}",
            language="en"
        )
        response = f"Response {i}"
        session_manager.update_session(session.session_id, message, response)
    
    # Verify all messages are stored
    updated_session = session_manager.get_session(phone)
    assert len(updated_session.conversation_history) == 10  # 5 user + 5 bot messages
    
    # Verify order is preserved
    for i in range(5):
        user_msg_idx = i * 2
        bot_msg_idx = i * 2 + 1
        assert updated_session.conversation_history[user_msg_idx].content == f"Message {i}"
        assert updated_session.conversation_history[bot_msg_idx].content == f"Response {i}"


def test_session_ttl_refresh_on_access(session_manager, fake_redis):
    """Test that accessing a session refreshes its TTL"""
    phone = "+911234567890"
    
    # Create session
    session = session_manager.get_or_create_session(phone)
    session_id = session.session_id
    
    # Get initial TTL
    initial_ttl = fake_redis.ttl(session_id)
    
    # Access session again (should refresh TTL)
    session_manager.get_or_create_session(phone)
    
    # Get new TTL
    new_ttl = fake_redis.ttl(session_id)
    
    # New TTL should be close to the configured session_ttl
    assert new_ttl >= initial_ttl - 5  # Allow 5 second tolerance


def test_clear_expired_sessions_with_no_sessions(session_manager):
    """Test clearing expired sessions when no sessions exist"""
    cleared_count = session_manager.clear_expired_sessions()
    assert cleared_count == 0


def test_clear_expired_sessions_with_invalid_data(session_manager, fake_redis):
    """Test clearing expired sessions with invalid JSON data"""
    # Add invalid session data
    fake_redis.set("session:invalid123", "invalid json data")
    
    # Should handle gracefully and delete invalid session
    cleared_count = session_manager.clear_expired_sessions()
    assert cleared_count == 1
    
    # Verify invalid session was deleted
    assert not fake_redis.exists("session:invalid123")
