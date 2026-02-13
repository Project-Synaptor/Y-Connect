"""Unit tests for ResponseGenerator"""

import pytest
from app.response_generator import ResponseGenerator
from app.models import Scheme, SchemeDocument, SchemeStatus, SchemeCategory, SchemeAuthority
from datetime import datetime


@pytest.fixture
def response_generator():
    """Create a ResponseGenerator instance"""
    return ResponseGenerator()


@pytest.fixture
def sample_scheme():
    """Create a sample scheme for testing"""
    return Scheme(
        scheme_id="test_scheme_001",
        scheme_name="PM-KISAN Scheme",
        scheme_name_translations={
            "hi": "पीएम-किसान योजना",
            "ta": "பிஎம்-கிசான் திட்டம்"
        },
        description="Financial support for farmers",
        description_translations={
            "hi": "किसानों के लिए वित्तीय सहायता",
            "ta": "விவசாயிகளுக்கு நிதி உதவி"
        },
        category=SchemeCategory.AGRICULTURE,
        authority=SchemeAuthority.CENTRAL,
        applicable_states=["ALL"],
        eligibility_criteria={
            "occupation": "farmer",
            "land_holding": "up to 2 hectares"
        },
        benefits="₹6000 per year in three installments",
        benefits_translations={
            "hi": "तीन किस्तों में प्रति वर्ष ₹6000",
            "ta": "மூன்று தவணைகளில் ஆண்டுக்கு ₹6000"
        },
        application_process="Apply online at pmkisan.gov.in",
        application_process_translations={
            "hi": "pmkisan.gov.in पर ऑनलाइन आवेदन करें",
            "ta": "pmkisan.gov.in இல் ஆன்லைனில் விண்ணப்பிக்கவும்"
        },
        official_url="https://pmkisan.gov.in",
        helpline_numbers=["155261", "011-24300606"],
        status=SchemeStatus.ACTIVE,
        start_date=datetime(2019, 2, 1),
        last_updated=datetime.utcnow()
    )


@pytest.fixture
def sample_scheme_document(sample_scheme):
    """Create a sample scheme document"""
    return SchemeDocument(
        document_id="doc_001",
        scheme_id=sample_scheme.scheme_id,
        scheme=sample_scheme,
        language="en",
        content="PM-KISAN provides financial support to farmers",
        document_type="overview",
        similarity_score=0.95
    )


class TestWelcomeMessage:
    """Tests for welcome message generation"""
    
    def test_welcome_message_english(self, response_generator):
        """Test welcome message in English"""
        message = response_generator.create_welcome_message("en")
        assert "Welcome to Y-Connect" in message
        assert "help" in message.lower()
        assert "🙏" in message
    
    def test_welcome_message_hindi(self, response_generator):
        """Test welcome message in Hindi"""
        message = response_generator.create_welcome_message("hi")
        assert "स्वागत" in message
        assert "🙏" in message
    
    def test_welcome_message_tamil(self, response_generator):
        """Test welcome message in Tamil"""
        message = response_generator.create_welcome_message("ta")
        assert "வரவேற்கிறோம்" in message
        assert "🙏" in message
    
    def test_welcome_message_unsupported_language_fallback(self, response_generator):
        """Test fallback to English for unsupported language"""
        message = response_generator.create_welcome_message("fr")
        assert "Welcome to Y-Connect" in message


class TestHelpMessage:
    """Tests for help message generation"""
    
    def test_help_message_english(self, response_generator):
        """Test help message in English"""
        message = response_generator.create_help_message("en")
        assert "How to use Y-Connect" in message
        assert "categories" in message.lower()
        assert "📚" in message
    
    def test_help_message_hindi(self, response_generator):
        """Test help message in Hindi"""
        message = response_generator.create_help_message("hi")
        assert "उपयोग" in message
        assert "📚" in message
    
    def test_help_message_unsupported_language_fallback(self, response_generator):
        """Test fallback to English for unsupported language"""
        message = response_generator.create_help_message("de")
        assert "How to use Y-Connect" in message


class TestSchemeSummary:
    """Tests for scheme summary generation"""
    
    def test_scheme_summary_single_scheme(self, response_generator, sample_scheme_document):
        """Test summary with single scheme"""
        summary = response_generator.create_scheme_summary([sample_scheme_document], "en")
        assert "Found 1 scheme for you" in summary
        assert "PM-KISAN" in summary
        assert "Reply with number" in summary
    
    def test_scheme_summary_multiple_schemes(self, response_generator, sample_scheme_document):
        """Test summary with multiple schemes"""
        schemes = [sample_scheme_document] * 3
        summary = response_generator.create_scheme_summary(schemes, "en")
        assert "Found 3 schemes for you" in summary
        assert "1." in summary
        assert "2." in summary
        assert "3." in summary
    
    def test_scheme_summary_hindi(self, response_generator, sample_scheme_document):
        """Test summary in Hindi"""
        summary = response_generator.create_scheme_summary([sample_scheme_document], "hi")
        assert "योजना" in summary
        assert "पीएम-किसान" in summary
    
    def test_scheme_summary_empty_list(self, response_generator):
        """Test summary with no schemes"""
        summary = response_generator.create_scheme_summary([], "en")
        assert "couldn't find any schemes" in summary
        assert "😔" in summary
    
    def test_scheme_summary_limits_to_10(self, response_generator, sample_scheme_document):
        """Test that summary limits to 10 schemes"""
        schemes = [sample_scheme_document] * 15
        summary = response_generator.create_scheme_summary(schemes, "en")
        assert "10." in summary
        assert "11." not in summary


class TestSchemeDetails:
    """Tests for detailed scheme formatting"""
    
    def test_format_scheme_details_english(self, response_generator, sample_scheme):
        """Test formatting scheme details in English"""
        details = response_generator.format_scheme_details(sample_scheme, "en")
        assert "PM-KISAN Scheme" in details
        assert "📋" in details
        assert "✅ Eligibility:" in details
        assert "💰 Benefits:" in details
        assert "📝 How to Apply:" in details
        assert "🔗" in details
        assert "pmkisan.gov.in" in details
        assert "📞 Helpline:" in details
    
    def test_format_scheme_details_hindi(self, response_generator, sample_scheme):
        """Test formatting scheme details in Hindi"""
        details = response_generator.format_scheme_details(sample_scheme, "hi")
        assert "पीएम-किसान योजना" in details
        assert "पात्रता:" in details
        assert "लाभ:" in details
    
    def test_format_scheme_details_tamil(self, response_generator, sample_scheme):
        """Test formatting scheme details in Tamil"""
        details = response_generator.format_scheme_details(sample_scheme, "ta")
        assert "பிஎம்-கிசான் திட்டம்" in details
        assert "தகுதி:" in details


class TestMessageSplitting:
    """Tests for message splitting logic"""
    
    def test_split_message_short_text(self, response_generator):
        """Test that short messages are not split"""
        short_text = "This is a short message."
        result = response_generator.split_message(short_text)
        assert len(result) == 1
        assert result[0] == short_text
    
    def test_split_message_long_text(self, response_generator):
        """Test that long messages are split"""
        long_text = "A" * 2000  # Exceeds MAX_MESSAGE_LENGTH
        result = response_generator.split_message(long_text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= response_generator.MAX_MESSAGE_LENGTH
    
    def test_split_at_section_break(self, response_generator):
        """Test splitting at double newline (section break)"""
        text = "Section 1 content here.\n\n" + "B" * 1500
        result = response_generator.split_message(text)
        assert len(result) >= 1
        # First chunk should end at section break if possible
        if len(result) > 1:
            assert result[0].endswith("Section 1 content here.")
    
    def test_split_at_newline(self, response_generator):
        """Test splitting at single newline"""
        lines = ["Line " + str(i) + " content here." for i in range(100)]
        text = "\n".join(lines)
        result = response_generator.split_message(text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= response_generator.MAX_MESSAGE_LENGTH
    
    def test_split_at_sentence(self, response_generator):
        """Test splitting at sentence boundary"""
        sentences = ["Sentence " + str(i) + " content here. " for i in range(100)]
        text = "".join(sentences)
        result = response_generator.split_message(text)
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= response_generator.MAX_MESSAGE_LENGTH
    
    def test_split_preserves_content(self, response_generator):
        """Test that splitting preserves all content"""
        long_text = "Word " * 500
        result = response_generator.split_message(long_text)
        rejoined = " ".join(result)
        # Content should be preserved (allowing for whitespace normalization)
        assert rejoined.replace("  ", " ").strip() == long_text.strip()


class TestFormatResponse:
    """Tests for response formatting"""
    
    def test_format_response_short(self, response_generator, sample_scheme_document):
        """Test formatting short response"""
        short_text = "Here is your scheme information."
        result = response_generator.format_response(short_text, [sample_scheme_document], "en")
        assert len(result) == 1
        assert result[0] == short_text
    
    def test_format_response_long(self, response_generator, sample_scheme_document):
        """Test formatting long response"""
        long_text = "Information " * 300
        result = response_generator.format_response(long_text, [sample_scheme_document], "en")
        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= response_generator.MAX_MESSAGE_LENGTH
