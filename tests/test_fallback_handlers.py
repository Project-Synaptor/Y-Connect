"""Unit tests for fallback handlers"""

import pytest
from unittest.mock import Mock, patch

from app.fallback_handlers import FallbackHandlers
from app.models import ProcessedQuery, SchemeDocument, Scheme, LanguageResult


class TestLanguageDetectionFallback:
    """
    Test language detection fallback
    Validates: Requirements 9.1
    """
    
    def test_fallback_returns_english_default(self):
        """Test that language detection fallback returns English"""
        text = "Some text in unknown language"
        
        result = FallbackHandlers.language_detection_fallback(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence < 1.0  # Low confidence indicates fallback
    
    def test_fallback_handles_empty_text(self):
        """Test that fallback handles empty text"""
        result = FallbackHandlers.language_detection_fallback("")
        
        assert result.language_code == "en"
    
    def test_fallback_handles_very_short_text(self):
        """Test that fallback handles very short text"""
        result = FallbackHandlers.language_detection_fallback("hi")
        
        assert result.language_code == "en"


class TestIntentExtractionFallback:
    """
    Test intent extraction fallback
    Validates: Requirements 9.2
    """
    
    def test_fallback_returns_rephrase_message_in_english(self):
        """Test that intent extraction fallback returns rephrase message in English"""
        text = "Some ambiguous query"
        
        result = FallbackHandlers.intent_extraction_fallback(text, "en")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "rephrase" in result.lower() or "understand" in result.lower()
        assert "example" in result.lower() or "try" in result.lower()
    
    def test_fallback_returns_localized_message_for_hindi(self):
        """Test that fallback returns Hindi message"""
        text = "कुछ अस्पष्ट प्रश्न"
        
        result = FallbackHandlers.intent_extraction_fallback(text, "hi")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Check for Hindi characters
        assert any('\u0900' <= c <= '\u097F' for c in result)
    
    def test_fallback_returns_localized_message_for_tamil(self):
        """Test that fallback returns Tamil message"""
        text = "சில தெளிவற்ற கேள்வி"
        
        result = FallbackHandlers.intent_extraction_fallback(text, "ta")
        
        assert isinstance(result, str)
        assert len(result) > 0
        # Check for Tamil characters
        assert any('\u0B80' <= c <= '\u0BFF' for c in result)
    
    def test_fallback_defaults_to_english_for_unsupported_language(self):
        """Test that fallback defaults to English for unsupported languages"""
        text = "Some query"
        
        result = FallbackHandlers.intent_extraction_fallback(text, "xx")
        
        assert isinstance(result, str)
        assert "rephrase" in result.lower() or "understand" in result.lower()
    
    def test_fallback_message_contains_examples(self):
        """Test that fallback message contains example queries"""
        result = FallbackHandlers.intent_extraction_fallback("query", "en")
        
        # Should contain bullet points or examples
        assert "•" in result or "example" in result.lower()


class TestRAGRetrievalFallback:
    """
    Test RAG retrieval fallback
    Validates: Requirements 9.3
    """
    
    def test_fallback_returns_empty_list_without_database(self):
        """Test that retrieval fallback returns empty list without database"""
        query = ProcessedQuery(
            original_text="farmer schemes",
            language="en",
            intent="search_schemes",
            entities={"occupation": "farmer"},
            needs_clarification=False,
            clarification_questions=[],
            search_vector=[]
        )
        
        result = FallbackHandlers.rag_retrieval_fallback(query, None)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_fallback_extracts_keywords_from_query(self):
        """Test that fallback extracts keywords from query"""
        query = ProcessedQuery(
            original_text="Show me farmer schemes in Punjab",
            language="en",
            intent="search_schemes",
            entities={"occupation": "farmer", "location": "Punjab"},
            needs_clarification=False,
            clarification_questions=[],
            search_vector=[]
        )
        
        keywords = FallbackHandlers._extract_keywords(query)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # Should include entity values
        assert "farmer" in keywords or "punjab" in keywords
    
    def test_fallback_filters_common_words(self):
        """Test that keyword extraction filters common words"""
        query = ProcessedQuery(
            original_text="I am a farmer and I need help",
            language="en",
            intent="search_schemes",
            entities={"occupation": "farmer"},
            needs_clarification=False,
            clarification_questions=[],
            search_vector=[]
        )
        
        keywords = FallbackHandlers._extract_keywords(query)
        
        # Common words should be filtered out
        common_words = ["i", "am", "a", "and", "the"]
        for word in common_words:
            assert word not in keywords
        
        # Important words should be kept
        assert "farmer" in keywords or "help" in keywords
    
    def test_fallback_limits_keyword_count(self):
        """Test that keyword extraction limits to 10 keywords"""
        long_text = " ".join([f"word{i}" for i in range(20)])
        query = ProcessedQuery(
            original_text=long_text,
            language="en",
            intent="search_schemes",
            entities={},
            needs_clarification=False,
            clarification_questions=[],
            search_vector=[]
        )
        
        keywords = FallbackHandlers._extract_keywords(query)
        
        assert len(keywords) <= 10


class TestLLMGenerationFallback:
    """
    Test LLM generation fallback
    Validates: Requirements 9.3
    """
    
    def test_fallback_returns_no_results_message_for_empty_list(self):
        """Test that fallback returns 'no results' message for empty scheme list"""
        result = FallbackHandlers.llm_generation_fallback([], "en")
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "couldn't find" in result.lower() or "no" in result.lower()
    
    def test_fallback_formats_single_scheme(self):
        """Test that fallback formats a single scheme correctly"""
        scheme = Scheme(
            scheme_id="test-1",
            scheme_name="Test Farmer Scheme",
            scheme_name_translations={},
            description="A test scheme for farmers",
            description_translations={},
            category="agriculture",
            authority="central",
            applicable_states=["ALL"],
            eligibility_criteria={},
            benefits="Financial assistance",
            benefits_translations={},
            application_process="Apply online",
            application_process_translations={},
            official_url="https://example.com",
            helpline_numbers=["1800-123-4567"],
            status="active"
        )
        
        scheme_doc = SchemeDocument(
            document_id="doc-1",
            scheme_id="test-1",
            scheme=scheme,
            language="en",
            content="Test content",
            document_type="overview",
            similarity_score=0.9
        )
        
        result = FallbackHandlers.llm_generation_fallback([scheme_doc], "en")
        
        assert isinstance(result, str)
        assert "Test Farmer Scheme" in result
        assert "example.com" in result or "official" in result.lower()
    
    def test_fallback_formats_multiple_schemes(self):
        """Test that fallback formats multiple schemes as a list"""
        schemes = []
        for i in range(3):
            scheme = Scheme(
                scheme_id=f"test-{i}",
                scheme_name=f"Test Scheme {i}",
                scheme_name_translations={},
                description=f"Description for scheme {i}",
                description_translations={},
                category="agriculture",
                authority="central",
                applicable_states=["ALL"],
                eligibility_criteria={},
                benefits="Benefits",
                benefits_translations={},
                application_process="Apply",
                application_process_translations={},
                official_url="https://example.com",
                helpline_numbers=[],
                status="active"
            )
            
            scheme_doc = SchemeDocument(
                document_id=f"doc-{i}",
                scheme_id=f"test-{i}",
                scheme=scheme,
                language="en",
                content="Content",
                document_type="overview",
                similarity_score=0.9
            )
            schemes.append(scheme_doc)
        
        result = FallbackHandlers.llm_generation_fallback(schemes, "en")
        
        assert isinstance(result, str)
        # Should contain numbered list
        assert "1." in result
        assert "2." in result
        assert "3." in result
        # Should contain scheme names
        assert "Test Scheme 0" in result
        assert "Test Scheme 1" in result
    
    def test_fallback_limits_scheme_list_to_five(self):
        """Test that fallback limits scheme list to 5 items"""
        schemes = []
        for i in range(10):
            scheme = Scheme(
                scheme_id=f"test-{i}",
                scheme_name=f"Test Scheme {i}",
                scheme_name_translations={},
                description=f"Description {i}",
                description_translations={},
                category="agriculture",
                authority="central",
                applicable_states=["ALL"],
                eligibility_criteria={},
                benefits="Benefits",
                benefits_translations={},
                application_process="Apply",
                application_process_translations={},
                official_url="https://example.com",
                helpline_numbers=[],
                status="active"
            )
            
            scheme_doc = SchemeDocument(
                document_id=f"doc-{i}",
                scheme_id=f"test-{i}",
                scheme=scheme,
                language="en",
                content="Content",
                document_type="overview",
                similarity_score=0.9
            )
            schemes.append(scheme_doc)
        
        result = FallbackHandlers.llm_generation_fallback(schemes, "en")
        
        # Should contain 1-5 but not 6-10
        assert "5." in result
        assert "6." not in result
    
    def test_fallback_returns_localized_no_results_message(self):
        """Test that 'no results' message is localized"""
        result_en = FallbackHandlers.llm_generation_fallback([], "en")
        result_hi = FallbackHandlers.llm_generation_fallback([], "hi")
        result_ta = FallbackHandlers.llm_generation_fallback([], "ta")
        
        # All should be different (localized)
        assert result_en != result_hi
        assert result_en != result_ta
        
        # Hindi should contain Devanagari characters
        assert any('\u0900' <= c <= '\u097F' for c in result_hi)
        
        # Tamil should contain Tamil characters
        assert any('\u0B80' <= c <= '\u0BFF' for c in result_ta)


class TestGetFallbackResponse:
    """Test the unified fallback response function"""
    
    def test_get_fallback_for_language_detection(self):
        """Test getting fallback response for language detection error"""
        result = FallbackHandlers.get_fallback_response("language_detection", "en")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_fallback_for_query_processing(self):
        """Test getting fallback response for query processing error"""
        context = {"text": "some query"}
        result = FallbackHandlers.get_fallback_response("query_processing", "en", context)
        
        assert isinstance(result, str)
        assert "rephrase" in result.lower() or "understand" in result.lower()
    
    def test_get_fallback_for_retrieval(self):
        """Test getting fallback response for retrieval error"""
        result = FallbackHandlers.get_fallback_response("retrieval", "en")
        
        assert isinstance(result, str)
        assert "couldn't find" in result.lower() or "no" in result.lower()
    
    def test_get_fallback_for_generation(self):
        """Test getting fallback response for generation error"""
        context = {"schemes": []}
        result = FallbackHandlers.get_fallback_response("generation", "en", context)
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_fallback_for_unknown_error_type(self):
        """Test getting fallback response for unknown error type"""
        result = FallbackHandlers.get_fallback_response("unknown", "en")
        
        assert isinstance(result, str)
        assert "wrong" in result.lower() or "try again" in result.lower()
    
    def test_get_fallback_handles_missing_context(self):
        """Test that get_fallback_response handles missing context gracefully"""
        result = FallbackHandlers.get_fallback_response("generation", "en", None)
        
        assert isinstance(result, str)
        assert len(result) > 0
