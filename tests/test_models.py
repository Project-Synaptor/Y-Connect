"""Unit tests for Pydantic models"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    IncomingMessage,
    OutgoingMessage,
    Message,
    MessageType,
    MessageRole,
    LanguageResult,
    UserSession,
    Scheme,
    SchemeDocument,
    ProcessedQuery,
    SchemeStatus,
    SchemeCategory,
    SchemeAuthority,
    IntentType,
)


class TestIncomingMessage:
    """Tests for IncomingMessage model"""
    
    def test_valid_incoming_message(self):
        """Test creating a valid incoming message"""
        msg = IncomingMessage(
            message_id="msg_123",
            from_phone="+919876543210",
            text_content="Hello, I need help with schemes"
        )
        assert msg.message_id == "msg_123"
        assert msg.from_phone == "+919876543210"
        assert msg.message_type == MessageType.TEXT
        assert msg.text_content == "Hello, I need help with schemes"
    
    def test_invalid_phone_number(self):
        """Test that invalid phone numbers are rejected"""
        with pytest.raises(ValidationError):
            IncomingMessage(
                message_id="msg_123",
                from_phone="9876543210",  # Missing +
                text_content="Hello"
            )
    
    def test_empty_text_for_text_message(self):
        """Test that empty text is rejected for text messages"""
        with pytest.raises(ValidationError):
            IncomingMessage(
                message_id="msg_123",
                from_phone="+919876543210",
                message_type=MessageType.TEXT,
                text_content=""
            )


class TestOutgoingMessage:
    """Tests for OutgoingMessage model"""
    
    def test_valid_outgoing_message(self):
        """Test creating a valid outgoing message"""
        msg = OutgoingMessage(
            to_phone="+919876543210",
            text_content="Here are the schemes for you"
        )
        assert msg.to_phone == "+919876543210"
        assert msg.message_type == MessageType.TEXT
        assert msg.text_content == "Here are the schemes for you"
    
    def test_message_too_long(self):
        """Test that messages exceeding WhatsApp limit are rejected"""
        with pytest.raises(ValidationError):
            OutgoingMessage(
                to_phone="+919876543210",
                text_content="x" * 5000  # Exceeds 4096 limit
            )


class TestMessage:
    """Tests for Message model"""
    
    def test_valid_message(self):
        """Test creating a valid message"""
        msg = Message(
            role=MessageRole.USER,
            content="Show me farmer schemes",
            language="hi"
        )
        assert msg.role == MessageRole.USER
        assert msg.content == "Show me farmer schemes"
        assert msg.language == "hi"
    
    def test_invalid_language_code(self):
        """Test that unsupported language codes are rejected"""
        with pytest.raises(ValidationError):
            Message(
                role=MessageRole.USER,
                content="Hello",
                language="fr"  # French not supported
            )


class TestLanguageResult:
    """Tests for LanguageResult model"""
    
    def test_valid_language_result(self):
        """Test creating a valid language result"""
        result = LanguageResult(
            language_code="hi",
            language_name="Hindi",
            confidence=0.95
        )
        assert result.language_code == "hi"
        assert result.language_name == "Hindi"
        assert result.confidence == 0.95
    
    def test_confidence_bounds(self):
        """Test that confidence is bounded between 0 and 1"""
        with pytest.raises(ValidationError):
            LanguageResult(
                language_code="hi",
                language_name="Hindi",
                confidence=1.5  # Exceeds 1.0
            )


class TestUserSession:
    """Tests for UserSession model"""
    
    def test_valid_user_session(self):
        """Test creating a valid user session"""
        session = UserSession(
            session_id="sess_123",
            phone_number="+919876543210",
            language="en"
        )
        assert session.session_id == "sess_123"
        assert session.phone_number == "+919876543210"
        assert session.language == "en"
        assert session.is_new_user is True
        assert len(session.conversation_history) == 0
    
    def test_add_message(self):
        """Test adding messages to session"""
        session = UserSession(
            session_id="sess_123",
            phone_number="+919876543210"
        )
        msg = Message(
            role=MessageRole.USER,
            content="Hello"
        )
        session.add_message(msg)
        assert len(session.conversation_history) == 1
        assert session.conversation_history[0].content == "Hello"
    
    def test_update_context(self):
        """Test updating user context"""
        session = UserSession(
            session_id="sess_123",
            phone_number="+919876543210"
        )
        session.update_context({"age": 30, "occupation": "farmer"})
        assert session.user_context["age"] == 30
        assert session.user_context["occupation"] == "farmer"


class TestScheme:
    """Tests for Scheme model"""
    
    def test_valid_scheme(self):
        """Test creating a valid scheme"""
        scheme = Scheme(
            scheme_id="PM-KISAN",
            scheme_name="PM-KISAN",
            description="Direct income support to farmers",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Rs. 6000 per year",
            application_process="Apply online at pmkisan.gov.in",
            official_url="https://pmkisan.gov.in"
        )
        assert scheme.scheme_id == "PM-KISAN"
        assert scheme.category == SchemeCategory.AGRICULTURE
        assert scheme.status == SchemeStatus.ACTIVE
    
    def test_invalid_url(self):
        """Test that invalid URLs are rejected"""
        with pytest.raises(ValidationError):
            Scheme(
                scheme_id="TEST",
                scheme_name="Test Scheme",
                description="Test",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test",
                application_process="Test",
                official_url="invalid-url"  # Missing http(s)://
            )
    
    def test_end_date_validation(self):
        """Test that end date must be after start date"""
        with pytest.raises(ValidationError):
            Scheme(
                scheme_id="TEST",
                scheme_name="Test Scheme",
                description="Test",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test",
                application_process="Test",
                official_url="https://example.com",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2023, 12, 31)  # Before start date
            )
    
    # Task 2.4: Unit tests for scheme model validation
    
    def test_required_field_scheme_id(self):
        """Test that scheme_id is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "scheme_id" in str(exc_info.value)
    
    def test_required_field_scheme_name(self):
        """Test that scheme_name is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "scheme_name" in str(exc_info.value)
    
    def test_required_field_description(self):
        """Test that description is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "description" in str(exc_info.value)
    
    def test_required_field_benefits(self):
        """Test that benefits is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "benefits" in str(exc_info.value)
    
    def test_required_field_application_process(self):
        """Test that application_process is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                official_url="https://example.com"
            )
        assert "application_process" in str(exc_info.value)
    
    def test_required_field_official_url(self):
        """Test that official_url is required"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process"
            )
        assert "official_url" in str(exc_info.value)
    
    def test_empty_scheme_id(self):
        """Test that empty scheme_id is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="   ",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "Scheme ID cannot be empty" in str(exc_info.value)
    
    def test_empty_scheme_name(self):
        """Test that empty scheme_name is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="   ",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "Required text field cannot be empty" in str(exc_info.value)
    
    def test_empty_description(self):
        """Test that empty description is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="   ",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com"
            )
        assert "Required text field cannot be empty" in str(exc_info.value)
    
    def test_date_validation_end_before_start(self):
        """Test that end_date before start_date is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com",
                start_date=datetime(2024, 6, 1),
                end_date=datetime(2024, 5, 31)
            )
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_date_validation_end_equals_start(self):
        """Test that end_date equal to start_date is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com",
                start_date=datetime(2024, 6, 1, 10, 0, 0),
                end_date=datetime(2024, 6, 1, 10, 0, 0)
            )
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_date_validation_valid_dates(self):
        """Test that valid start and end dates are accepted"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        assert scheme.start_date == datetime(2024, 1, 1)
        assert scheme.end_date == datetime(2024, 12, 31)
    
    def test_date_validation_only_start_date(self):
        """Test that only start_date without end_date is valid"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            start_date=datetime(2024, 1, 1)
        )
        assert scheme.start_date == datetime(2024, 1, 1)
        assert scheme.end_date is None
    
    def test_date_validation_only_end_date(self):
        """Test that only end_date without start_date is valid"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            end_date=datetime(2024, 12, 31)
        )
        assert scheme.start_date is None
        assert scheme.end_date == datetime(2024, 12, 31)
    
    def test_status_enum_active(self):
        """Test that ACTIVE status is valid"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            status=SchemeStatus.ACTIVE
        )
        assert scheme.status == SchemeStatus.ACTIVE
    
    def test_status_enum_expired(self):
        """Test that EXPIRED status is valid"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            status=SchemeStatus.EXPIRED
        )
        assert scheme.status == SchemeStatus.EXPIRED
    
    def test_status_enum_upcoming(self):
        """Test that UPCOMING status is valid"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com",
            status=SchemeStatus.UPCOMING
        )
        assert scheme.status == SchemeStatus.UPCOMING
    
    def test_status_enum_invalid(self):
        """Test that invalid status values are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            Scheme(
                scheme_id="TEST-001",
                scheme_name="Test Scheme",
                description="Test description",
                category=SchemeCategory.AGRICULTURE,
                authority=SchemeAuthority.CENTRAL,
                applicable_states=["ALL"],
                benefits="Test benefits",
                application_process="Test process",
                official_url="https://example.com",
                status="invalid_status"
            )
        assert "status" in str(exc_info.value).lower()
    
    def test_status_default_value(self):
        """Test that status defaults to ACTIVE"""
        scheme = Scheme(
            scheme_id="TEST-001",
            scheme_name="Test Scheme",
            description="Test description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            application_process="Test process",
            official_url="https://example.com"
        )
        assert scheme.status == SchemeStatus.ACTIVE


class TestSchemeDocument:
    """Tests for SchemeDocument model"""
    
    def test_valid_scheme_document(self):
        """Test creating a valid scheme document"""
        scheme = Scheme(
            scheme_id="PM-KISAN",
            scheme_name="PM-KISAN",
            description="Direct income support to farmers",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Rs. 6000 per year",
            application_process="Apply online",
            official_url="https://pmkisan.gov.in"
        )
        doc = SchemeDocument(
            document_id="doc_123",
            scheme_id="PM-KISAN",
            scheme=scheme,
            content="This scheme provides direct income support to farmers",
            document_type="overview",
            similarity_score=0.85
        )
        assert doc.document_id == "doc_123"
        assert doc.scheme_id == "PM-KISAN"
        assert doc.similarity_score == 0.85


class TestProcessedQuery:
    """Tests for ProcessedQuery model"""
    
    def test_valid_processed_query(self):
        """Test creating a valid processed query"""
        query = ProcessedQuery(
            original_text="Show me farmer schemes in Punjab",
            language="en",
            intent=IntentType.SEARCH_SCHEMES
        )
        assert query.original_text == "Show me farmer schemes in Punjab"
        assert query.intent == IntentType.SEARCH_SCHEMES
        assert query.needs_clarification is False
    
    def test_add_entity(self):
        """Test adding entities to query"""
        query = ProcessedQuery(
            original_text="I am a farmer",
            language="en"
        )
        query.add_entity("occupation", "farmer")
        assert query.has_entity("occupation")
        assert query.get_entity("occupation") == "farmer"
    
    def test_search_vector_validation(self):
        """Test that search vector dimensions are validated"""
        with pytest.raises(ValidationError):
            ProcessedQuery(
                original_text="Test query",
                search_vector=[0.1, 0.2]  # Invalid dimension
            )
