"""Property-based tests for Pydantic models

Feature: y-connect-whatsapp-bot
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta

from app.models import (
    IncomingMessage,
    OutgoingMessage,
    Message,
    MessageType,
    MessageRole,
    LanguageResult,
    UserSession,
)


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


# Property 20: Message Length Constraint
@given(
    phone=phone_number_strategy(),
    text=st.text(min_size=1, max_size=1600).filter(lambda x: x.strip())
)
def test_property_20_message_length_constraint(phone, text):
    """
    Feature: y-connect-whatsapp-bot, Property 20: Message Length Constraint
    
    For any generated response, each individual message should be at most 
    1600 characters in length.
    
    Validates: Requirements 6.4
    
    Note: This tests the OutgoingMessage model's ability to accept messages
    up to 1600 characters (the recommended WhatsApp limit for bot responses).
    The actual message splitting logic will be tested in the ResponseGenerator.
    """
    # Messages up to 1600 characters should be valid
    msg = OutgoingMessage(
        to_phone=phone,
        text_content=text
    )
    assert len(msg.text_content) <= 1600
    assert msg.to_phone == phone


@given(
    phone=phone_number_strategy(),
    text=st.text(min_size=1601, max_size=4096).filter(lambda x: x.strip())
)
def test_message_length_between_1600_and_4096(phone, text):
    """
    Test that messages between 1600 and 4096 characters are accepted
    by the model (WhatsApp allows up to 4096), but the application
    should split them before sending.
    """
    # Messages between 1600 and 4096 should still be valid for the model
    msg = OutgoingMessage(
        to_phone=phone,
        text_content=text
    )
    assert 1600 < len(msg.text_content) <= 4096


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    phone=phone_number_strategy(),
    language=language_code_strategy(),
    messages=st.lists(
        st.builds(
            Message,
            role=st.sampled_from([MessageRole.USER, MessageRole.ASSISTANT]),
            content=st.text(min_size=1, max_size=500).filter(lambda x: x.strip()),
            language=language_code_strategy()
        ),
        min_size=0,
        max_size=50
    )
)
def test_session_message_history_integrity(session_id, phone, language, messages):
    """
    Property: Session message history should maintain order and integrity
    
    For any sequence of messages added to a session, the conversation history
    should preserve the exact order and content of all messages.
    """
    session = UserSession(
        session_id=session_id,
        phone_number=phone,
        language=language
    )
    
    # Add all messages
    for msg in messages:
        session.add_message(msg)
    
    # Verify all messages are present in order
    assert len(session.conversation_history) == len(messages)
    for i, msg in enumerate(messages):
        assert session.conversation_history[i].content == msg.content
        assert session.conversation_history[i].role == msg.role


@given(
    phone=phone_number_strategy(),
    text=st.text(min_size=1, max_size=500)
)
def test_incoming_message_phone_validation(phone, text):
    """
    Property: All incoming messages must have valid phone numbers
    
    For any incoming message, the phone number should be in valid
    international format.
    """
    msg = IncomingMessage(
        message_id=f"msg_{hash(phone)}",
        from_phone=phone,
        text_content=text
    )
    
    # Phone number should start with + and contain only digits after
    assert msg.from_phone.startswith("+")
    assert msg.from_phone[1:].isdigit()
    assert 11 <= len(msg.from_phone) <= 16  # + plus 10-15 digits


@given(
    lang_code=language_code_strategy(),
    confidence=st.floats(min_value=0.0, max_value=1.0)
)
def test_language_detection_confidence_bounds(lang_code, confidence):
    """
    Property: Language detection confidence must be bounded
    
    For any language detection result, the confidence score should be
    between 0.0 and 1.0 inclusive.
    """
    # Map language codes to names
    lang_names = {
        "hi": "Hindi", "en": "English", "ta": "Tamil", "te": "Telugu",
        "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
        "ml": "Malayalam", "pa": "Punjabi"
    }
    
    result = LanguageResult(
        language_code=lang_code,
        language_name=lang_names[lang_code],
        confidence=confidence
    )
    
    assert 0.0 <= result.confidence <= 1.0
    assert result.language_code in lang_names
    assert result.language_name == lang_names[lang_code]


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    phone=phone_number_strategy(),
    context_updates=st.lists(
        st.dictionaries(
            keys=st.sampled_from(["age", "occupation", "location", "income", "category"]),
            values=st.one_of(
                st.integers(min_value=18, max_value=100),
                st.text(min_size=1, max_size=50)
            ),
            min_size=1,
            max_size=5
        ),
        min_size=1,
        max_size=10
    )
)
def test_session_context_accumulation(session_id, phone, context_updates):
    """
    Property: Session context should accumulate information
    
    For any sequence of context updates, the session should retain all
    information from previous updates while adding new information.
    """
    session = UserSession(
        session_id=session_id,
        phone_number=phone
    )
    
    all_keys = set()
    for update in context_updates:
        session.update_context(update)
        all_keys.update(update.keys())
    
    # All keys from all updates should be present in final context
    for key in all_keys:
        assert key in session.user_context
