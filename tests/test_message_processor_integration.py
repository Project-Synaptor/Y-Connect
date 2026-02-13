"""Integration tests for MessageProcessor end-to-end flow

Tests complete flow: webhook → processing → response
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.message_processor import MessageProcessor
from app.models import (
    IncomingMessage, MessageType, UserSession, Message,
    LanguageResult, ProcessedQuery, IntentType, SchemeDocument,
    Scheme, SchemeStatus, SchemeCategory, SchemeAuthority
)
from app.session_manager import SessionManager
from app.language_detector import LanguageDetector
from app.query_processor import QueryProcessor
from app.rag_engine import RAGEngine, GeneratedResponse
from app.response_generator import ResponseGenerator
from app.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_components():
    """Create mock components for integration tests"""
    session_manager = MagicMock(spec=SessionManager)
    language_detector = MagicMock(spec=LanguageDetector)
    query_processor = MagicMock(spec=QueryProcessor)
    rag_engine = MagicMock(spec=RAGEngine)
    response_generator = MagicMock(spec=ResponseGenerator)
    
    # Create async mock for WhatsAppClient
    whatsapp_client = MagicMock(spec=WhatsAppClient)
    whatsapp_client.send_message = AsyncMock()
    
    return {
        "session_manager": session_manager,
        "language_detector": language_detector,
        "query_processor": query_processor,
        "rag_engine": rag_engine,
        "response_generator": response_generator,
        "whatsapp_client": whatsapp_client
    }


@pytest.mark.asyncio
async def test_complete_flow_webhook_to_response(mock_components):
    """
    Test complete flow: webhook → processing → response
    
    **Validates: Requirements 1.1, 7.1, 3.5**
    
    Verifies the end-to-end message processing pipeline:
    1. Incoming message is received
    2. Session is created/retrieved
    3. Language is detected
    4. Query is processed
    5. Schemes are retrieved
    6. Response is generated
    7. Response is sent via WhatsApp
    """
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    query_processor = mock_components["query_processor"]
    rag_engine = mock_components["rag_engine"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    phone_number = "+1234567890"
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language="en",
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    language_detector.detect_language.return_value = LanguageResult(
        language_code="en",
        language_name="English",
        confidence=0.95
    )
    
    # Mock query processing
    processed_query = ProcessedQuery(
        original_text="Show me farmer schemes",
        language="en",
        intent=IntentType.SEARCH_SCHEMES,
        entities={"category": "agriculture"},
        needs_clarification=False,
        clarification_questions=[]
    )
    query_processor.process_query.return_value = processed_query
    
    # Mock scheme retrieval
    mock_scheme = Scheme(
        scheme_id="scheme_001",
        scheme_name="PM-KISAN",
        scheme_name_translations={},
        description="Farmer income support scheme",
        description_translations={},
        category=SchemeCategory.AGRICULTURE,
        authority=SchemeAuthority.CENTRAL,
        applicable_states=["ALL"],
        eligibility_criteria={"occupation": "farmer"},
        benefits="₹6000 per year",
        benefits_translations={},
        application_process="Apply online",
        application_process_translations={},
        official_url="https://pmkisan.gov.in",
        helpline_numbers=["1800-123-4567"],
        status=SchemeStatus.ACTIVE,
        start_date=datetime.now().date(),
        end_date=None,
        last_updated=datetime.utcnow()
    )
    
    mock_scheme_doc = SchemeDocument(
        document_id="doc_001",
        scheme_id="scheme_001",
        scheme=mock_scheme,
        language="en",
        content="PM-KISAN provides income support to farmers",
        document_type="overview",
        similarity_score=0.95
    )
    
    rag_engine.retrieve_schemes.return_value = [mock_scheme_doc]
    
    # Mock response generation
    generated_response = GeneratedResponse(
        text="Here is information about PM-KISAN scheme...",
        sources=[mock_scheme_doc],
        language="en",
        confidence=0.95
    )
    rag_engine.generate_response = AsyncMock(return_value=generated_response)
    
    # Mock response formatting
    response_generator.format_response.return_value = [generated_response.text]
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=query_processor,
        rag_engine=rag_engine,
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message
    incoming_message = IncomingMessage(
        message_id="msg_001",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content="Show me farmer schemes"
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify the complete flow
    session_manager.get_or_create_session.assert_called_once_with(phone_number)
    language_detector.detect_language.assert_called_once()
    query_processor.process_query.assert_called_once()
    rag_engine.retrieve_schemes.assert_called_once()
    rag_engine.generate_response.assert_called_once()
    response_generator.format_response.assert_called_once()
    whatsapp_client.send_message.assert_called_once()
    
    # Verify session was updated
    session_manager.update_session.assert_called_once()


@pytest.mark.asyncio
async def test_new_user_onboarding_flow(mock_components):
    """
    Test new user onboarding flow
    
    **Validates: Requirements 7.1**
    
    Verifies that:
    1. New users receive a welcome message
    2. Welcome message is in the detected language
    3. Session is marked as not new after welcome
    """
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session for new user
    phone_number = "+9876543210"
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language="hi",
        is_new_user=True  # New user
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    language_detector.detect_language.return_value = LanguageResult(
        language_code="hi",
        language_name="Hindi",
        confidence=0.95
    )
    
    # Mock welcome message
    welcome_message = "नमस्ते! Y-Connect में आपका स्वागत है!"
    response_generator.create_welcome_message.return_value = welcome_message
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=mock_components["rag_engine"],
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message (greeting)
    incoming_message = IncomingMessage(
        message_id="msg_002",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content="नमस्ते"
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify welcome message was created in Hindi
    response_generator.create_welcome_message.assert_called_once_with("hi")
    
    # Verify welcome message was sent
    whatsapp_client.send_message.assert_called_once()
    call_args = whatsapp_client.send_message.call_args
    assert call_args[0][0] == phone_number
    assert call_args[0][1] == welcome_message
    
    # Verify session was updated
    session_manager.update_session.assert_called_once()


@pytest.mark.asyncio
async def test_multi_turn_conversation_flow(mock_components):
    """
    Test multi-turn conversation flow
    
    **Validates: Requirements 3.5**
    
    Verifies that:
    1. Context from previous messages is maintained
    2. Entities from earlier messages are used in later queries
    3. Session context is updated correctly
    """
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    query_processor = mock_components["query_processor"]
    rag_engine = mock_components["rag_engine"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session with some context
    phone_number = "+1122334455"
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language="en",
        is_new_user=False,
        user_context={"occupation": "farmer", "location": "PB"}  # Context from previous message
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    language_detector.detect_language.return_value = LanguageResult(
        language_code="en",
        language_name="English",
        confidence=0.95
    )
    
    # Mock query processing - should use context from session
    processed_query = ProcessedQuery(
        original_text="Show me schemes for me",
        language="en",
        intent=IntentType.SEARCH_SCHEMES,
        entities={
            "occupation": "farmer",  # From session context
            "location": "PB",  # From session context
            "age": 45  # New entity from current query
        },
        needs_clarification=False,
        clarification_questions=[]
    )
    query_processor.process_query.return_value = processed_query
    
    # Mock scheme retrieval
    mock_scheme = Scheme(
        scheme_id="scheme_002",
        scheme_name="Punjab Farmer Scheme",
        scheme_name_translations={},
        description="Scheme for Punjab farmers",
        description_translations={},
        category=SchemeCategory.AGRICULTURE,
        authority=SchemeAuthority.CENTRAL,
        applicable_states=["PB"],
        eligibility_criteria={"occupation": "farmer"},
        benefits="Financial support",
        benefits_translations={},
        application_process="Apply online",
        application_process_translations={},
        official_url="https://example.com",
        helpline_numbers=[],
        status=SchemeStatus.ACTIVE,
        start_date=datetime.now().date(),
        end_date=None,
        last_updated=datetime.utcnow()
    )
    
    mock_scheme_doc = SchemeDocument(
        document_id="doc_002",
        scheme_id="scheme_002",
        scheme=mock_scheme,
        language="en",
        content="Scheme content",
        document_type="overview",
        similarity_score=0.9
    )
    rag_engine.retrieve_schemes.return_value = [mock_scheme_doc]
    
    # Mock response generation
    generated_response = GeneratedResponse(
        text="Based on your profile as a farmer in Punjab...",
        sources=[mock_scheme_doc],
        language="en",
        confidence=0.9
    )
    rag_engine.generate_response = AsyncMock(return_value=generated_response)
    
    # Mock response formatting
    response_generator.format_response.return_value = [generated_response.text]
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=query_processor,
        rag_engine=rag_engine,
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message
    incoming_message = IncomingMessage(
        message_id="msg_003",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content="Show me schemes for me"
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify query processor was called with session (which has context)
    query_processor.process_query.assert_called_once()
    call_args = query_processor.process_query.call_args
    assert call_args[0][1].user_context == {"occupation": "farmer", "location": "PB"}
    
    # Verify session context was updated with new entities
    session_manager.update_session_context.assert_called()
    
    # Verify response was sent
    whatsapp_client.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling_in_pipeline(mock_components):
    """
    Test error handling in the processing pipeline
    
    Verifies that:
    1. Errors are caught gracefully
    2. User receives an error message
    3. System doesn't crash
    """
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    query_processor = mock_components["query_processor"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    phone_number = "+5544332211"
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language="en",
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    language_detector.detect_language.return_value = LanguageResult(
        language_code="en",
        language_name="English",
        confidence=0.95
    )
    
    # Mock query processor to raise an exception
    query_processor.process_query.side_effect = Exception("Query processing failed")
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=query_processor,
        rag_engine=mock_components["rag_engine"],
        response_generator=mock_components["response_generator"],
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message
    incoming_message = IncomingMessage(
        message_id="msg_004",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content="Test query"
    )
    
    # Process the message - should not raise exception
    await processor.process_incoming_message(incoming_message)
    
    # Verify error message was sent to user
    whatsapp_client.send_message.assert_called_once()
    call_args = whatsapp_client.send_message.call_args
    assert call_args[0][0] == phone_number
    # Error message should contain apology or error indication
    assert "sorry" in call_args[0][1].lower() or "error" in call_args[0][1].lower()
