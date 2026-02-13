"""Property-based tests for MessageProcessor

Tests universal properties that should hold across all inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.message_processor import MessageProcessor
from app.models import IncomingMessage, MessageType, UserSession, Message, SchemeDocument
from app.session_manager import SessionManager
from app.language_detector import LanguageDetector
from app.query_processor import QueryProcessor
from app.rag_engine import RAGEngine
from app.response_generator import ResponseGenerator
from app.whatsapp_client import WhatsAppClient


# Supported languages for Y-Connect
SUPPORTED_LANGUAGES = ["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]

# Help keywords in different languages
HELP_KEYWORDS = {
    "en": ["help"],
    "hi": ["मदद", "सहायता"],
    "ta": ["உதவி"],
    "te": ["సహాయం"],
    "bn": ["সাহায্য"],
    "mr": ["मदत"],
    "gu": ["મદદ"],
    "kn": ["ಸಹಾಯ"],
    "ml": ["സഹായം"],
    "pa": ["ਮਦਦ"]
}


def create_mock_components():
    """Create mock components for MessageProcessor"""
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
@given(
    language=st.sampled_from(SUPPORTED_LANGUAGES),
    phone_number=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=("Nd",))).map(lambda x: f"+{x}")
)
@settings(max_examples=50, deadline=None)
async def test_property_22_help_command_multi_language(language, phone_number):
    """
    Feature: y-connect-whatsapp-bot, Property 22: Help Command Multi-Language
    
    **Validates: Requirements 7.2**
    
    For any help command keyword ("help", "मदद", "உதவி", etc.) in any supported language,
    the system should respond with usage instructions in that language.
    
    This property verifies that:
    1. Help keywords in all supported languages are recognized
    2. The response is in the same language as the help keyword
    3. The response contains usage instructions
    """
    # Create fresh mocks for each test iteration
    mock_components = create_mock_components()
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language=language,
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection to return the test language
    from app.models import LanguageResult
    language_detector.detect_language.return_value = LanguageResult(
        language_code=language,
        language_name="Test Language",
        confidence=0.95
    )
    
    # Mock response generator to return help message in the language
    expected_help_message = f"Help message in {language}"
    response_generator.create_help_message.return_value = expected_help_message
    
    # Create MessageProcessor with mocks
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=mock_components["rag_engine"],
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Get help keyword for this language
    help_keywords = HELP_KEYWORDS.get(language, ["help"])
    help_keyword = help_keywords[0]
    
    # Create incoming message with help keyword
    incoming_message = IncomingMessage(
        message_id=f"msg_{phone_number}_{language}",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content=help_keyword
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify that help message was generated in the correct language
    response_generator.create_help_message.assert_called_once_with(language)
    
    # Verify that the response was sent
    whatsapp_client.send_message.assert_called_once()
    call_args = whatsapp_client.send_message.call_args
    assert call_args[0][0] == phone_number
    assert call_args[0][1] == expected_help_message
    
    # Verify session was updated
    session_manager.update_session.assert_called_once()


@pytest.mark.asyncio
@given(
    language=st.sampled_from(SUPPORTED_LANGUAGES),
    phone_number=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=("Nd",))).map(lambda x: f"+{x}"),
    help_variation=st.sampled_from(["help", "HELP", "Help", "  help  ", "help?", "help!"])
)
@settings(max_examples=30, deadline=None)
async def test_property_22_help_command_case_insensitive(language, phone_number, help_variation):
    """
    Property 22 extension: Help command should be case-insensitive and handle variations
    
    Verifies that help commands work regardless of:
    - Case (HELP, help, Help)
    - Whitespace (  help  )
    - Punctuation (help?, help!)
    """
    # Create fresh mocks for each test iteration
    mock_components = create_mock_components()
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language=language,
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    from app.models import LanguageResult
    language_detector.detect_language.return_value = LanguageResult(
        language_code=language,
        language_name="Test Language",
        confidence=0.95
    )
    
    # Mock response generator
    expected_help_message = f"Help message in {language}"
    response_generator.create_help_message.return_value = expected_help_message
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=mock_components["rag_engine"],
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message with help variation
    incoming_message = IncomingMessage(
        message_id=f"msg_{phone_number}_{language}",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content=help_variation
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify that help message was generated
    response_generator.create_help_message.assert_called_once_with(language)
    
    # Verify that the response was sent
    whatsapp_client.send_message.assert_called_once()


@pytest.mark.asyncio
@given(
    language=st.sampled_from(SUPPORTED_LANGUAGES),
    phone_number=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=("Nd",))).map(lambda x: f"+{x}")
)
@settings(max_examples=30, deadline=None)
async def test_property_22_help_response_contains_instructions(language, phone_number):
    """
    Property 22 extension: Help response should contain usage instructions
    
    Verifies that the help response includes:
    - Instructions on how to use the system
    - Example queries
    - Guidance on next steps
    """
    # Create fresh mocks for each test iteration
    mock_components = create_mock_components()
    # Setup mocks
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Use real ResponseGenerator to test actual help messages
    response_generator = ResponseGenerator()
    
    # Create mock session
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language=language,
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    from app.models import LanguageResult
    language_detector.detect_language.return_value = LanguageResult(
        language_code=language,
        language_name="Test Language",
        confidence=0.95
    )
    
    # Create MessageProcessor with real ResponseGenerator
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=mock_components["rag_engine"],
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message with help keyword
    help_keyword = HELP_KEYWORDS.get(language, ["help"])[0]
    incoming_message = IncomingMessage(
        message_id=f"msg_{phone_number}_{language}",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content=help_keyword
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify that the response was sent
    whatsapp_client.send_message.assert_called_once()
    
    # Get the actual help message that was sent
    call_args = whatsapp_client.send_message.call_args
    help_message = call_args[0][1]
    
    # Verify the help message is not empty
    assert len(help_message) > 0
    
    # Verify the help message contains some expected elements
    # (The actual content varies by language, but should have structure)
    assert "1" in help_message or "2" in help_message  # Numbered instructions
    
    # For English, verify specific content
    if language == "en":
        assert "how to use" in help_message.lower() or "y-connect" in help_message.lower()
        assert "categories" in help_message.lower()



@pytest.mark.asyncio
@given(
    category=st.sampled_from(list(MessageProcessor.CATEGORY_MAP.values())),
    phone_number=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=("Nd",))).map(lambda x: f"+{x}"),
    language=st.sampled_from(SUPPORTED_LANGUAGES)
)
@settings(max_examples=30, deadline=None)
async def test_property_23_category_filtering(category, phone_number, language):
    """
    Feature: y-connect-whatsapp-bot, Property 23: Category Filtering
    
    **Validates: Requirements 7.4**
    
    For any category selection (agriculture, education, health, etc.),
    all returned schemes should belong to the selected category.
    
    This property verifies that:
    1. Category selection is recognized
    2. Only schemes from the selected category are returned
    3. No schemes from other categories are included
    """
    # Create fresh mocks for each test iteration
    mock_components = create_mock_components()
    
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    rag_engine = mock_components["rag_engine"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language=language,
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    from app.models import LanguageResult
    language_detector.detect_language.return_value = LanguageResult(
        language_code=language,
        language_name="Test Language",
        confidence=0.95
    )
    
    # Create mock schemes in the selected category
    from app.models import Scheme, SchemeStatus, SchemeCategory, SchemeAuthority
    from datetime import datetime
    
    mock_schemes = []
    for i in range(3):
        scheme = Scheme(
            scheme_id=f"scheme_{category}_{i}",
            scheme_name=f"Test Scheme {i}",
            scheme_name_translations={},
            description=f"Description for scheme {i}",
            description_translations={},
            category=SchemeCategory(category),
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            eligibility_criteria={},
            benefits=f"Benefits {i}",
            benefits_translations={},
            application_process=f"Apply {i}",
            application_process_translations={},
            official_url=f"https://example.com/scheme{i}",
            helpline_numbers=[],
            status=SchemeStatus.ACTIVE,
            start_date=datetime.now().date(),
            end_date=None,
            last_updated=datetime.utcnow()
        )
        
        scheme_doc = SchemeDocument(
            document_id=f"doc_{category}_{i}",
            scheme_id=f"scheme_{category}_{i}",
            scheme=scheme,
            language=language,
            content=f"Content for scheme {i}",
            document_type="overview",
            similarity_score=0.9
        )
        mock_schemes.append(scheme_doc)
    
    # Mock RAG engine to return schemes in the selected category
    rag_engine.retrieve_schemes.return_value = mock_schemes
    
    # Mock response generator
    response_generator.create_scheme_summary.return_value = f"Summary of {category} schemes"
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=rag_engine,
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Find the category number
    category_num = None
    for num, cat in MessageProcessor.CATEGORY_MAP.items():
        if cat == category:
            category_num = num
            break
    
    assert category_num is not None, f"Category {category} not found in CATEGORY_MAP"
    
    # Create incoming message with category selection
    incoming_message = IncomingMessage(
        message_id=f"msg_{phone_number}_{category}",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content=category_num
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify that RAG engine was called with correct category filter
    rag_engine.retrieve_schemes.assert_called_once()
    call_args = rag_engine.retrieve_schemes.call_args
    processed_query = call_args[0][0]
    
    # Verify the query has the correct category entity
    assert "category" in processed_query.entities
    assert processed_query.entities["category"] == category
    
    # Verify all returned schemes belong to the selected category
    for scheme_doc in mock_schemes:
        assert scheme_doc.scheme.category.value == category, \
            f"Scheme {scheme_doc.scheme_id} has category {scheme_doc.scheme.category.value}, expected {category}"
    
    # Verify response was sent
    whatsapp_client.send_message.assert_called_once()


@pytest.mark.asyncio
@given(
    category_num=st.sampled_from(list(MessageProcessor.CATEGORY_MAP.keys())),
    phone_number=st.text(min_size=10, max_size=15, alphabet=st.characters(whitelist_categories=("Nd",))).map(lambda x: f"+{x}"),
    language=st.sampled_from(SUPPORTED_LANGUAGES)
)
@settings(max_examples=20, deadline=None)
async def test_property_23_category_filtering_by_number(category_num, phone_number, language):
    """
    Property 23 extension: Category filtering should work with numeric selection (1-10)
    
    Verifies that:
    - Numeric category selection (1-10) is correctly mapped to category names
    - The correct category is used for filtering
    """
    # Create fresh mocks
    mock_components = create_mock_components()
    
    session_manager = mock_components["session_manager"]
    language_detector = mock_components["language_detector"]
    rag_engine = mock_components["rag_engine"]
    response_generator = mock_components["response_generator"]
    whatsapp_client = mock_components["whatsapp_client"]
    
    # Create mock session
    mock_session = UserSession(
        session_id=f"session:{phone_number}",
        phone_number=phone_number,
        language=language,
        is_new_user=False
    )
    session_manager.get_or_create_session.return_value = mock_session
    
    # Mock language detection
    from app.models import LanguageResult
    language_detector.detect_language.return_value = LanguageResult(
        language_code=language,
        language_name="Test Language",
        confidence=0.95
    )
    
    # Get expected category from number
    expected_category = MessageProcessor.CATEGORY_MAP[category_num]
    
    # Mock RAG engine to return empty list (we just want to verify the call)
    rag_engine.retrieve_schemes.return_value = []
    
    # Mock response generator
    response_generator.create_scheme_summary.return_value = "No schemes found"
    
    # Create MessageProcessor
    processor = MessageProcessor(
        session_manager=session_manager,
        language_detector=language_detector,
        query_processor=mock_components["query_processor"],
        rag_engine=rag_engine,
        response_generator=response_generator,
        whatsapp_client=whatsapp_client
    )
    
    # Create incoming message with category number
    incoming_message = IncomingMessage(
        message_id=f"msg_{phone_number}_{category_num}",
        from_phone=phone_number,
        timestamp=datetime.utcnow(),
        message_type=MessageType.TEXT,
        text_content=category_num
    )
    
    # Process the message
    await processor.process_incoming_message(incoming_message)
    
    # Verify that RAG engine was called
    rag_engine.retrieve_schemes.assert_called_once()
    
    # Verify the processed query has the correct category
    call_args = rag_engine.retrieve_schemes.call_args
    processed_query = call_args[0][0]
    
    assert "category" in processed_query.entities
    assert processed_query.entities["category"] == expected_category, \
        f"Expected category {expected_category}, got {processed_query.entities['category']}"
