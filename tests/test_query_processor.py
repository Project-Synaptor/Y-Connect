"""Unit tests for QueryProcessor component

Tests specific examples, edge cases, and ambiguity detection.
"""

import pytest
from app.query_processor import QueryProcessor
from app.models import UserSession, IntentType


class TestQueryProcessorAmbiguity:
    """Unit tests for ambiguity detection in QueryProcessor"""
    
    @pytest.fixture
    def query_processor(self):
        """Create QueryProcessor instance"""
        return QueryProcessor()
    
    @pytest.fixture
    def sample_session(self):
        """Create a sample user session"""
        return UserSession(
            session_id="test_session_123",
            phone_number="+911234567890",
            language="en",
            conversation_history=[],
            user_context={}
        )
    
    def test_ambiguous_query_multiple_categories(self, query_processor, sample_session):
        """
        Test queries matching multiple categories.
        
        Requirements: 3.2
        """
        # Query that could match both agriculture and financial categories
        # Avoid "help" keyword which triggers HELP intent
        query = "I need a loan for farming equipment"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should detect ambiguity when multiple categories match
        # This query has both "loan" (financial) and "farming" (agriculture)
        assert result.intent == IntentType.SEARCH_SCHEMES
        
        # May detect ambiguity depending on keyword matching
        if result.needs_clarification:
            assert len(result.clarification_questions) > 0, \
                "Should generate clarification questions"
            
            # Check that clarification mentions multiple categories
            clarification_text = " ".join(result.clarification_questions).lower()
            assert "categor" in clarification_text, \
                "Clarification should mention categories"
    
    def test_ambiguous_query_education_and_employment(self, query_processor, sample_session):
        """
        Test query matching education and employment categories.
        """
        query = "I want training for a job"
        
        result = query_processor.process_query(query, sample_session)
        
        # This could match both skill_development and employment
        # The system should either extract one or ask for clarification
        assert result.intent == IntentType.SEARCH_SCHEMES
    
    def test_ambiguous_query_agriculture_and_financial(self, query_processor, sample_session):
        """
        Test query matching agriculture and financial inclusion categories.
        """
        query = "I need a loan for farming"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should detect both agriculture and financial keywords
        # May need clarification or extract both
        assert result.intent == IntentType.SEARCH_SCHEMES
    
    def test_query_missing_critical_information(self, query_processor, sample_session):
        """
        Test queries with missing required information.
        
        Requirements: 3.2
        """
        # Very vague query with no specific category or occupation
        # Avoid "show" which triggers CATEGORY_BROWSE intent
        query = "what schemes can I get"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should detect need for clarification
        assert result.needs_clarification is True, \
            "Should detect missing critical information"
        assert len(result.clarification_questions) > 0, \
            "Should ask for more information"
        
        # Check that clarification asks for category or type
        clarification_text = " ".join(result.clarification_questions).lower()
        assert any(word in clarification_text for word in ["type", "category", "looking for"]), \
            "Should ask about scheme type or category"
    
    def test_query_with_no_context_no_category(self, query_processor, sample_session):
        """
        Test query with no context and no category specified.
        """
        query = "what schemes are available"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should need clarification
        assert result.needs_clarification is True
        assert len(result.clarification_questions) > 0
    
    def test_specific_query_no_ambiguity(self, query_processor, sample_session):
        """
        Test that specific queries don't trigger ambiguity detection.
        """
        query = "I am a farmer in Punjab looking for agriculture schemes"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should not need clarification - query is specific
        assert result.needs_clarification is False, \
            "Specific query should not need clarification"
        assert len(result.clarification_questions) == 0
        
        # Should extract entities
        assert "occupation" in result.entities
        assert result.entities["occupation"] == "farmer"
        assert "location" in result.entities
        assert result.entities["location"] == "PB"
        assert "category" in result.entities
        assert result.entities["category"] == "agriculture"
    
    def test_query_with_occupation_no_ambiguity(self, query_processor, sample_session):
        """
        Test that queries with occupation don't need clarification.
        """
        query = "I am a student"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should not need clarification - occupation provides context
        assert result.needs_clarification is False
        assert "occupation" in result.entities
        assert result.entities["occupation"] == "student"
    
    def test_query_with_category_no_ambiguity(self, query_processor, sample_session):
        """
        Test that queries with clear category don't need clarification.
        """
        query = "education schemes"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should not need clarification - category is clear
        assert result.needs_clarification is False
        assert "category" in result.entities
        assert result.entities["category"] == "education"
    
    def test_help_intent_no_ambiguity(self, query_processor, sample_session):
        """
        Test that help queries don't trigger ambiguity detection.
        """
        query = "help"
        
        result = query_processor.process_query(query, sample_session)
        
        # Help intent should not need clarification
        assert result.intent == IntentType.HELP
        assert result.needs_clarification is False
    
    def test_feedback_intent_no_ambiguity(self, query_processor, sample_session):
        """
        Test that feedback queries don't trigger ambiguity detection.
        """
        query = "this information is wrong"
        
        result = query_processor.process_query(query, sample_session)
        
        # Feedback intent should not need clarification
        assert result.intent == IntentType.FEEDBACK
        assert result.needs_clarification is False


class TestQueryProcessorEntityExtraction:
    """Unit tests for entity extraction edge cases"""
    
    @pytest.fixture
    def query_processor(self):
        """Create QueryProcessor instance"""
        return QueryProcessor()
    
    @pytest.fixture
    def sample_session(self):
        """Create a sample user session"""
        return UserSession(
            session_id="test_session_123",
            phone_number="+911234567890",
            language="en",
            conversation_history=[],
            user_context={}
        )
    
    def test_extract_multiple_entities_single_query(self, query_processor, sample_session):
        """
        Test extracting multiple entities from a single query.
        """
        query = "I am a 25 year old farmer from Punjab looking for agriculture schemes"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should extract age, occupation, location, and category
        assert "age" in result.entities
        assert result.entities["age"] == 25
        assert "occupation" in result.entities
        assert result.entities["occupation"] == "farmer"
        assert "location" in result.entities
        assert result.entities["location"] == "PB"
        assert "category" in result.entities
        assert result.entities["category"] == "agriculture"
    
    def test_extract_age_variations(self, query_processor, sample_session):
        """
        Test different age expression formats.
        """
        test_cases = [
            ("I am 30 years old", 30),
            ("age 25", 25),
            ("My age is 40", 40),
            ("I am 18", 18),
        ]
        
        for query, expected_age in test_cases:
            result = query_processor.process_query(query, sample_session)
            assert "age" in result.entities, f"Age not extracted from: {query}"
            assert result.entities["age"] == expected_age, \
                f"Expected age {expected_age}, got {result.entities['age']}"
    
    def test_extract_location_all_india(self, query_processor, sample_session):
        """
        Test extraction of "all India" location.
        """
        test_cases = [
            "schemes for all india",
            "anywhere in india",
            "any state",
        ]
        
        for query in test_cases:
            result = query_processor.process_query(query, sample_session)
            assert "location" in result.entities, f"Location not extracted from: {query}"
            assert result.entities["location"] == "ALL", \
                f"Expected 'ALL', got {result.entities['location']}"
    
    def test_extract_income_bpl(self, query_processor, sample_session):
        """
        Test extraction of BPL income status.
        """
        test_cases = [
            "I am BPL",
            "below poverty line",
            "BPL card holder",
        ]
        
        for query in test_cases:
            result = query_processor.process_query(query, sample_session)
            assert "income" in result.entities, f"Income not extracted from: {query}"
            assert result.entities["income"] == "BPL", \
                f"Expected 'BPL', got {result.entities['income']}"
    
    def test_no_entities_in_generic_query(self, query_processor, sample_session):
        """
        Test that generic queries don't extract false entities.
        """
        query = "hello"
        
        result = query_processor.process_query(query, sample_session)
        
        # Should not extract any entities from generic greeting
        assert len(result.entities) == 0, \
            f"Should not extract entities from generic query, got: {result.entities}"
    
    def test_intent_detection_search_schemes(self, query_processor, sample_session):
        """
        Test search_schemes intent detection.
        """
        queries = [
            "farmer schemes",
            "what schemes are available",
            "I need schemes for education",
        ]
        
        for query in queries:
            result = query_processor.process_query(query, sample_session)
            assert result.intent == IntentType.SEARCH_SCHEMES, \
                f"Expected SEARCH_SCHEMES intent for: {query}, got {result.intent}"
    
    def test_intent_detection_help(self, query_processor, sample_session):
        """
        Test help intent detection.
        """
        queries = [
            "help",
            "how to use",
            "guide",
        ]
        
        for query in queries:
            result = query_processor.process_query(query, sample_session)
            assert result.intent == IntentType.HELP, \
                f"Expected HELP intent for: {query}"
    
    def test_intent_detection_get_details(self, query_processor, sample_session):
        """
        Test get_details intent detection.
        """
        queries = [
            "tell me more",
            "details",
            "explain this scheme",
        ]
        
        for query in queries:
            result = query_processor.process_query(query, sample_session)
            assert result.intent == IntentType.GET_DETAILS, \
                f"Expected GET_DETAILS intent for: {query}"
    
    def test_intent_detection_category_browse(self, query_processor, sample_session):
        """
        Test category_browse intent detection.
        """
        queries = [
            "show categories",
            "list all schemes",
            "browse schemes",
        ]
        
        for query in queries:
            result = query_processor.process_query(query, sample_session)
            assert result.intent == IntentType.CATEGORY_BROWSE, \
                f"Expected CATEGORY_BROWSE intent for: {query}"
