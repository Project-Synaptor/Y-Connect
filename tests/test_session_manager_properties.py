"""Property-based tests for SessionManager

Feature: y-connect-whatsapp-bot
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
import fakeredis

from app.session_manager import SessionManager
from app.models import Message, MessageRole, UserSession


# Custom strategies
@st.composite
def phone_number_strategy(draw):
    """Generate valid international phone numbers"""
    country_code = draw(st.integers(min_value=1, max_value=999))
    number = draw(st.integers(min_value=1000000000, max_value=9999999999))
    return f"+{country_code}{number}"


@st.composite
def language_code_strategy(draw):
    """Generate valid language codes from supported languages"""
    languages = ["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
    return draw(st.sampled_from(languages))


@st.composite
def user_message_strategy(draw):
    """Generate valid USER Message objects"""
    return Message(
        role=MessageRole.USER,  # Only USER messages
        content=draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip())),
        language=draw(language_code_strategy())
    )


# Property 4: Session Isolation
@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=2,
        max_size=10,
        unique=True
    ),
    messages_per_session=st.lists(
        st.lists(user_message_strategy(), min_size=1, max_size=5),
        min_size=2,
        max_size=10
    )
)
@settings(max_examples=25, deadline=None)
def test_property_4_session_isolation(phone_numbers, messages_per_session):
    """
    Feature: y-connect-whatsapp-bot, Property 4: Session Isolation
    
    For any set of concurrent user sessions, messages and context from one 
    session should never appear in another session's conversation history 
    or responses.
    
    Validates: Requirements 1.4
    """
    # Ensure we have matching number of message lists
    assume(len(phone_numbers) == len(messages_per_session))
    
    # Create SessionManager with fake Redis for testing
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create sessions for all phone numbers
    sessions = {}
    for phone in phone_numbers:
        session = session_manager.get_or_create_session(phone)
        sessions[phone] = session
    
    # Add messages to each session
    for phone, messages in zip(phone_numbers, messages_per_session):
        session = sessions[phone]
        for msg in messages:
            # Simulate adding message and response
            response = f"Response to: {msg.content[:20]}"
            session_manager.update_session(
                session.session_id,
                msg,
                response
            )
    
    # Verify session isolation: each session should only contain its own messages
    for i, phone in enumerate(phone_numbers):
        # Retrieve session from Redis
        retrieved_session = session_manager.get_session(phone)
        assert retrieved_session is not None
        
        # Get expected messages for this session
        expected_messages = messages_per_session[i]
        
        # Each message generates 2 entries: user message + bot response
        expected_count = len(expected_messages) * 2
        assert len(retrieved_session.conversation_history) == expected_count
        
        # Verify session isolation by checking message count and content match
        # Sessions are isolated if:
        # 1. Each session has exactly the messages we added to it
        # 2. The total count matches expected count
        # 3. Message order is preserved
        
        user_messages_in_session = [
            m for m in retrieved_session.conversation_history 
            if m.role == MessageRole.USER
        ]
        
        # Should have exactly the number of user messages we added
        assert len(user_messages_in_session) == len(expected_messages)
        
        # Verify message order and content match
        for idx, expected_msg in enumerate(expected_messages):
            assert user_messages_in_session[idx].content == expected_msg.content
            assert user_messages_in_session[idx].language == expected_msg.language



@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=2,
        max_size=5,
        unique=True
    ),
    contexts=st.lists(
        st.dictionaries(
            keys=st.sampled_from(["age", "occupation", "location", "income"]),
            values=st.one_of(
                st.integers(min_value=18, max_value=100),
                st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
            ),
            min_size=1,
            max_size=4
        ),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=25, deadline=None)
def test_session_context_isolation(phone_numbers, contexts):
    """
    Property: Session context isolation
    
    For any set of concurrent sessions with different user contexts,
    each session should maintain its own context without cross-contamination.
    
    Validates: Requirements 1.4
    """
    # Ensure we have matching number of contexts
    assume(len(phone_numbers) == len(contexts))
    
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create sessions and update contexts
    for phone, context in zip(phone_numbers, contexts):
        session = session_manager.get_or_create_session(phone)
        session_manager.update_session_context(phone, context)
    
    # Verify each session has only its own context
    for i, phone in enumerate(phone_numbers):
        retrieved_session = session_manager.get_session(phone)
        assert retrieved_session is not None
        
        expected_context = contexts[i]
        
        # All keys from expected context should be present
        for key, value in expected_context.items():
            assert key in retrieved_session.user_context
            assert retrieved_session.user_context[key] == value
        
        # Context from other sessions should not be present
        # (unless they happen to have the same key-value pairs)
        for j, other_phone in enumerate(phone_numbers):
            if i != j:
                other_context = contexts[j]
                # Check that unique keys from other contexts are not present
                for key, value in other_context.items():
                    if key not in expected_context:
                        # This key should not be in current session
                        assert key not in retrieved_session.user_context or \
                               retrieved_session.user_context[key] != value


@given(
    phone=phone_number_strategy(),
    language1=language_code_strategy(),
    language2=language_code_strategy()
)
@settings(max_examples=25, deadline=None)
def test_session_language_isolation(phone, language1, language2):
    """
    Property: Session language updates should not affect other sessions
    
    For any session language update, only that specific session should
    reflect the language change.
    """
    assume(language1 != language2)
    
    # Create two different phone numbers
    phone1 = phone
    phone2 = phone[:-1] + ("0" if phone[-1] != "0" else "1")
    
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create two sessions
    session1 = session_manager.get_or_create_session(phone1)
    session2 = session_manager.get_or_create_session(phone2)
    
    # Update language for first session
    session_manager.update_session_language(phone1, language1)
    
    # Update language for second session
    session_manager.update_session_language(phone2, language2)
    
    # Verify each session has its own language
    retrieved_session1 = session_manager.get_session(phone1)
    retrieved_session2 = session_manager.get_session(phone2)
    
    assert retrieved_session1.language == language1
    assert retrieved_session2.language == language2
    assert retrieved_session1.language != retrieved_session2.language


@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=3,
        max_size=10,
        unique=True
    )
)
@settings(max_examples=12, deadline=None)
def test_concurrent_session_creation(phone_numbers):
    """
    Property: Concurrent session creation should maintain isolation
    
    For any set of phone numbers, creating sessions concurrently should
    result in unique, isolated sessions for each phone number.
    """
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create all sessions
    sessions = {}
    for phone in phone_numbers:
        session = session_manager.get_or_create_session(phone)
        sessions[phone] = session
    
    # Verify all sessions are unique
    session_ids = [s.session_id for s in sessions.values()]
    assert len(session_ids) == len(set(session_ids)), "Session IDs are not unique"
    
    # Verify each session has correct phone number
    for phone, session in sessions.items():
        assert session.phone_number == phone
    
    # Verify sessions can be retrieved independently
    for phone in phone_numbers:
        retrieved = session_manager.get_session(phone)
        assert retrieved is not None
        assert retrieved.phone_number == phone
        assert retrieved.session_id == sessions[phone].session_id



# Property 24: PII Deletion After Session Expiry
@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=1,
        max_size=5,
        unique=True
    ),
    messages=st.lists(user_message_strategy(), min_size=1, max_size=3),
    contexts=st.dictionaries(
        keys=st.sampled_from(["age", "occupation", "location", "income", "name"]),
        values=st.one_of(
            st.integers(min_value=18, max_value=100),
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
        ),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=25, deadline=None)
def test_property_24_pii_deletion_after_session_expiry(phone_numbers, messages, contexts):
    """
    Feature: y-connect-whatsapp-bot, Property 24: PII Deletion After Session Expiry
    
    For any expired session, no personally identifiable information 
    (phone numbers, extracted personal details) should remain in any 
    storage system.
    
    Validates: Requirements 8.1, 8.2
    
    Note: This test simulates session expiry by manually setting last_active
    to >24 hours ago and then running the cleanup process.
    """
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create sessions with PII
    for phone in phone_numbers:
        session = session_manager.get_or_create_session(phone)
        
        # Add messages (contains conversation data)
        for msg in messages:
            response = f"Response to: {msg.content[:20]}"
            session_manager.update_session(session.session_id, msg, response)
        
        # Add context (contains PII like age, name, location)
        session_manager.update_session_context(phone, contexts)
    
    # Verify sessions exist with PII
    for phone in phone_numbers:
        session = session_manager.get_session(phone)
        assert session is not None
        assert session.phone_number == phone
        assert len(session.conversation_history) > 0
        assert len(session.user_context) > 0
    
    # Simulate session expiry by modifying last_active to >24 hours ago
    for phone in phone_numbers:
        session = session_manager.get_session(phone)
        session.last_active = datetime.utcnow() - timedelta(hours=25)
        
        # Save the modified session back to Redis
        session_json = session_manager._serialize_session(session)
        fake_redis.setex(
            session.session_id,
            session_manager.session_ttl,
            session_json
        )
    
    # Run cleanup to delete expired sessions
    cleared_count = session_manager.clear_expired_sessions()
    
    # Verify that sessions were cleared
    assert cleared_count == len(phone_numbers), \
        f"Expected {len(phone_numbers)} sessions to be cleared, but {cleared_count} were cleared"
    
    # Verify that no PII remains in storage
    for phone in phone_numbers:
        session = session_manager.get_session(phone)
        assert session is None, \
            f"Session for {phone} should be deleted but still exists"
        
        # Verify the session key doesn't exist in Redis
        session_id = session_manager._generate_session_id(phone)
        assert not fake_redis.exists(session_id), \
            f"Session key {session_id} should not exist in Redis"


@given(
    phone=phone_number_strategy(),
    messages=st.lists(user_message_strategy(), min_size=1, max_size=5),
    context=st.dictionaries(
        keys=st.sampled_from(["age", "occupation", "location", "income", "name", "email"]),
        values=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=25, deadline=None)
def test_pii_not_deleted_before_expiry(phone, messages, context):
    """
    Property: PII should be retained for active sessions
    
    For any session that has not expired (last_active < 24 hours ago),
    all PII and conversation data should be retained.
    
    Validates: Requirements 1.4, 8.1
    """
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create session with PII
    session = session_manager.get_or_create_session(phone)
    
    # Add messages
    for msg in messages:
        response = f"Response: {msg.content[:20]}"
        session_manager.update_session(session.session_id, msg, response)
    
    # Add context
    session_manager.update_session_context(phone, context)
    
    # Simulate time passing but less than 24 hours (e.g., 12 hours)
    session = session_manager.get_session(phone)
    session.last_active = datetime.utcnow() - timedelta(hours=12)
    
    # Save the modified session
    session_json = session_manager._serialize_session(session)
    fake_redis.setex(
        session.session_id,
        session_manager.session_ttl,
        session_json
    )
    
    # Run cleanup
    cleared_count = session_manager.clear_expired_sessions()
    
    # Session should NOT be cleared (it's not expired yet)
    assert cleared_count == 0, "No sessions should be cleared for active sessions"
    
    # Verify session still exists with all data
    retrieved_session = session_manager.get_session(phone)
    assert retrieved_session is not None
    assert retrieved_session.phone_number == phone
    assert len(retrieved_session.conversation_history) == len(messages) * 2  # user + bot messages
    assert len(retrieved_session.user_context) == len(context)
    
    # Verify all context keys are present
    for key in context.keys():
        assert key in retrieved_session.user_context


@given(
    phone=phone_number_strategy()
)
@settings(max_examples=12, deadline=None)
def test_session_id_anonymization(phone):
    """
    Property: Session IDs should be anonymized (hashed)
    
    For any phone number, the session ID should not contain the 
    phone number in plain text (should be hashed for privacy).
    
    Validates: Requirements 8.1, 8.5
    """
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create session
    session = session_manager.get_or_create_session(phone)
    
    # Verify session ID does not contain phone number in plain text
    # Remove the '+' and check if digits appear in session_id
    phone_digits = phone.replace("+", "")
    assert phone_digits not in session.session_id, \
        f"Session ID should not contain phone number in plain text"
    
    # Verify session ID is a hash (contains 'session:' prefix and hex characters)
    assert session.session_id.startswith("session:"), \
        "Session ID should have 'session:' prefix"
    
    # The hash part should be hexadecimal (SHA256 produces 64 hex chars)
    hash_part = session.session_id.replace("session:", "")
    assert len(hash_part) == 64, "Session ID should contain SHA256 hash (64 chars)"
    assert all(c in "0123456789abcdef" for c in hash_part), \
        "Session ID hash should be hexadecimal"


@given(
    phone=phone_number_strategy(),
    ttl_seconds=st.integers(min_value=10, max_value=100)
)
@settings(max_examples=12, deadline=None)
def test_redis_ttl_enforcement(phone, ttl_seconds):
    """
    Property: Redis TTL should enforce automatic session expiry
    
    For any session stored in Redis, the TTL mechanism should
    automatically delete the session after the configured time.
    
    Validates: Requirements 1.5, 8.2
    
    Note: This test verifies TTL is set correctly. Actual expiry
    is handled by Redis automatically.
    """
    # Create SessionManager with fake Redis and custom TTL
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Override TTL for testing
    original_ttl = session_manager.session_ttl
    session_manager.session_ttl = ttl_seconds
    
    try:
        # Create session
        session = session_manager.get_or_create_session(phone)
        session_id = session.session_id
        
        # Verify session exists
        assert fake_redis.exists(session_id)
        
        # Check TTL is set correctly (allow some tolerance for execution time)
        ttl = fake_redis.ttl(session_id)
        assert ttl > 0, "TTL should be set"
        assert ttl <= ttl_seconds, f"TTL should be <= {ttl_seconds}"
        assert ttl >= ttl_seconds - 5, f"TTL should be close to {ttl_seconds}"
        
        # Simulate TTL expiry by deleting the key (fakeredis doesn't auto-expire)
        fake_redis.delete(session_id)
        
        # Verify session no longer exists
        assert not fake_redis.exists(session_id)
        retrieved_session = session_manager.get_session(phone)
        assert retrieved_session is None
        
    finally:
        # Restore original TTL
        session_manager.session_ttl = original_ttl


# Property 5: Session Expiration and Privacy
@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=1,
        max_size=10,
        unique=True
    ),
    messages_per_session=st.lists(
        st.lists(user_message_strategy(), min_size=1, max_size=5),
        min_size=1,
        max_size=10
    ),
    contexts=st.lists(
        st.dictionaries(
            keys=st.sampled_from(["age", "occupation", "location", "income", "name", "email"]),
            values=st.one_of(
                st.integers(min_value=18, max_value=100),
                st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
            ),
            min_size=1,
            max_size=5
        ),
        min_size=1,
        max_size=10
    ),
    hours_inactive=st.integers(min_value=24, max_value=72)
)
@settings(max_examples=25, deadline=None)
def test_property_5_session_expiration_and_privacy(
    phone_numbers, messages_per_session, contexts, hours_inactive
):
    """
    Feature: y-connect-whatsapp-bot, Property 5: Session Expiration and Privacy
    
    For any user session inactive for 24 hours or more, all session data 
    including conversation history and user context should be deleted from storage.
    
    Validates: Requirements 1.5, 8.2
    """
    # Ensure we have matching number of message lists and contexts
    assume(len(phone_numbers) == len(messages_per_session))
    assume(len(phone_numbers) == len(contexts))
    
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Create sessions with full data (messages and context)
    session_ids = []
    for phone, messages, context in zip(phone_numbers, messages_per_session, contexts):
        # Create session
        session = session_manager.get_or_create_session(phone)
        session_ids.append(session.session_id)
        
        # Add messages (conversation history)
        for msg in messages:
            response = f"Response to: {msg.content[:20]}"
            session_manager.update_session(session.session_id, msg, response)
        
        # Add user context (PII)
        session_manager.update_session_context(phone, context)
    
    # Verify all sessions exist with complete data
    for phone, messages, context in zip(phone_numbers, messages_per_session, contexts):
        session = session_manager.get_session(phone)
        assert session is not None, f"Session should exist for {phone}"
        assert session.phone_number == phone
        assert len(session.conversation_history) == len(messages) * 2  # user + bot messages
        assert len(session.user_context) >= len(context)
        
        # Verify conversation history contains actual data
        assert all(msg.content for msg in session.conversation_history), \
            "All messages should have content"
        
        # Verify user context contains actual data
        for key in context.keys():
            assert key in session.user_context, f"Context key {key} should exist"
    
    # Simulate sessions being inactive for >= 24 hours
    for phone in phone_numbers:
        session = session_manager.get_session(phone)
        session.last_active = datetime.utcnow() - timedelta(hours=hours_inactive)
        
        # Save the modified session back to Redis
        session_json = session_manager._serialize_session(session)
        fake_redis.setex(
            session.session_id,
            session_manager.session_ttl,
            session_json
        )
    
    # Run the cleanup process to delete expired sessions
    cleared_count = session_manager.clear_expired_sessions()
    
    # Verify that all expired sessions were cleared
    assert cleared_count == len(phone_numbers), \
        f"Expected {len(phone_numbers)} sessions to be cleared, but {cleared_count} were cleared"
    
    # Verify complete data deletion: no session data should remain
    for phone, session_id in zip(phone_numbers, session_ids):
        # 1. Session should not be retrievable via get_session
        session = session_manager.get_session(phone)
        assert session is None, \
            f"Session for {phone} should be deleted but still retrievable"
        
        # 2. Session key should not exist in Redis
        assert not fake_redis.exists(session_id), \
            f"Session key {session_id} should not exist in Redis"
        
        # 3. No keys matching the session pattern should exist
        matching_keys = fake_redis.keys(f"*{phone}*")
        assert len(matching_keys) == 0, \
            f"No keys containing phone number should exist, found: {matching_keys}"
    
    # Verify Redis is clean (no session keys remain)
    all_session_keys = fake_redis.keys("session:*")
    assert len(all_session_keys) == 0, \
        f"All session keys should be deleted, but {len(all_session_keys)} remain"


@given(
    phone_numbers=st.lists(
        phone_number_strategy(),
        min_size=2,
        max_size=5,
        unique=True
    ),
    messages=st.lists(user_message_strategy(), min_size=1, max_size=3),
    context=st.dictionaries(
        keys=st.sampled_from(["age", "occupation", "location"]),
        values=st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        min_size=1,
        max_size=3
    )
)
@settings(max_examples=25, deadline=None)
def test_selective_session_expiration(phone_numbers, messages, context):
    """
    Property: Only expired sessions should be deleted
    
    For any set of sessions where some are expired (>= 24 hours inactive) 
    and some are active (< 24 hours inactive), only the expired sessions 
    should be deleted while active sessions remain intact.
    
    Validates: Requirements 1.5, 8.2
    """
    assume(len(phone_numbers) >= 2)
    
    # Create SessionManager with fake Redis
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    session_manager = SessionManager(redis_client=fake_redis)
    
    # Split phone numbers into expired and active groups
    mid_point = len(phone_numbers) // 2
    expired_phones = phone_numbers[:mid_point]
    active_phones = phone_numbers[mid_point:]
    
    # Create all sessions with data
    for phone in phone_numbers:
        session = session_manager.get_or_create_session(phone)
        
        # Add messages
        for msg in messages:
            response = f"Response: {msg.content[:20]}"
            session_manager.update_session(session.session_id, msg, response)
        
        # Add context
        session_manager.update_session_context(phone, context)
    
    # Set expired sessions to >24 hours inactive
    for phone in expired_phones:
        session = session_manager.get_session(phone)
        session.last_active = datetime.utcnow() - timedelta(hours=25)
        session_json = session_manager._serialize_session(session)
        fake_redis.setex(session.session_id, session_manager.session_ttl, session_json)
    
    # Set active sessions to <24 hours inactive
    for phone in active_phones:
        session = session_manager.get_session(phone)
        session.last_active = datetime.utcnow() - timedelta(hours=12)
        session_json = session_manager._serialize_session(session)
        fake_redis.setex(session.session_id, session_manager.session_ttl, session_json)
    
    # Run cleanup
    cleared_count = session_manager.clear_expired_sessions()
    
    # Verify only expired sessions were cleared
    assert cleared_count == len(expired_phones), \
        f"Expected {len(expired_phones)} expired sessions to be cleared"
    
    # Verify expired sessions are deleted
    for phone in expired_phones:
        session = session_manager.get_session(phone)
        assert session is None, f"Expired session for {phone} should be deleted"
    
    # Verify active sessions still exist with all data
    for phone in active_phones:
        session = session_manager.get_session(phone)
        assert session is not None, f"Active session for {phone} should still exist"
        assert session.phone_number == phone
        assert len(session.conversation_history) == len(messages) * 2
        assert len(session.user_context) >= len(context)
        
        # Verify data integrity
        for key in context.keys():
            assert key in session.user_context
