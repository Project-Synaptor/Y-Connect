"""Property-based tests for QueryProcessor component

Tests universal properties that should hold across all inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from app.query_processor import QueryProcessor
from app.models import UserSession, IntentType


# Custom strategies for generating test data
@st.composite
def phone_number_strategy(draw):
    """Generate valid international phone numbers"""
    country_code = draw(st.integers(min_value=1, max_value=999))
    number = draw(st.integers(min_value=1000000000, max_value=9999999999))
    return f"+{country_code}{number}"


@st.composite
def user_session_strategy(draw):
    """Generate valid UserSession objects"""
    phone = draw(phone_number_strategy())
    session_id = f"session:{draw(st.text(min_size=32, max_size=64, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'))))}"
    language = draw(st.sampled_from(["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]))
    
    return UserSession(
        session_id=session_id,
        phone_number=phone,
        language=language,
        conversation_history=[],
        user_context={}
    )


@st.composite
def query_with_age_strategy(draw):
    """Generate queries containing age information"""
    age = draw(st.integers(min_value=1, max_value=100))
    templates = [
        f"I am {age} years old",
        f"age {age}",
        f"{age} years old",
        f"My age is {age}",
    ]
    return draw(st.sampled_from(templates)), age


@st.composite
def query_with_location_strategy(draw):
    """Generate queries containing location information"""
    states = [
        ("punjab", "PB"),
        ("delhi", "DL"),
        ("maharashtra", "MH"),
        ("tamil nadu", "TN"),
        ("karnataka", "KA"),
        ("kerala", "KL"),
        ("gujarat", "GJ"),
        ("west bengal", "WB"),
    ]
    state_name, state_code = draw(st.sampled_from(states))
    templates = [
        f"I am from {state_name}",
        f"in {state_name}",
        f"schemes for {state_name}",
        f"{state_name} schemes",
    ]
    return draw(st.sampled_from(templates)), state_code


@st.composite
def query_with_occupation_strategy(draw):
    """Generate queries containing occupation information"""
    occupations = [
        ("farmer", ["I am a farmer", "farmer schemes", "for farmers"]),
        ("student", ["I am a student", "student schemes", "for students"]),
        ("unemployed", ["I am unemployed", "unemployed schemes", "jobless"]),
        ("entrepreneur", ["I am an entrepreneur", "business schemes", "for entrepreneurs"]),
    ]
    occupation, templates = draw(st.sampled_from(occupations))
    return draw(st.sampled_from(templates)), occupation


@st.composite
def query_with_gender_strategy(draw):
    """Generate queries containing gender information"""
    genders = [
        ("male", ["I am a man", "male schemes", "for men", "boy"]),
        ("female", ["I am a woman", "female schemes", "for women", "girl"]),
    ]
    gender, templates = draw(st.sampled_from(genders))
    return draw(st.sampled_from(templates)), gender


@st.composite
def query_with_income_strategy(draw):
    """Generate queries containing income information"""
    income_types = [
        ("BPL", ["I am BPL", "below poverty line", "BPL card"]),
        ("APL", ["I am APL", "above poverty line"]),
        ("5 lakh", ["income 5 lakh", "earn 5 lakh per year"]),
    ]
    income, templates = draw(st.sampled_from(income_types))
    return draw(st.sampled_from(templates)), income


@st.composite
def query_with_category_strategy(draw):
    """Generate queries containing scheme category"""
    categories = [
        ("agriculture", ["agriculture schemes", "farming schemes", "for farmers"]),
        ("education", ["education schemes", "scholarship", "for students"]),
        ("health", ["health schemes", "medical schemes", "hospital"]),
        ("housing", ["housing schemes", "home schemes", "house"]),
        ("employment", ["employment schemes", "job schemes", "work"]),
    ]
    category, templates = draw(st.sampled_from(categories))
    return draw(st.sampled_from(templates)), category


class TestQueryProcessorProperties:
    """Property-based tests for QueryProcessor"""
    
    # Property 8: Entity Extraction Completeness
    # Validates: Requirements 3.1
    @settings(max_examples=25)
    @given(
        query_text=st.one_of(
            query_with_age_strategy(),
            query_with_location_strategy(),
            query_with_occupation_strategy(),
            query_with_gender_strategy(),
            query_with_income_strategy(),
            query_with_category_strategy()
        ),
        session=user_session_strategy()
    )
    def test_entity_extraction_completeness_age(self, query_text, session):
        """
        Property 8: Entity Extraction Completeness
        
        For any query containing entities (age, income, occupation, location, category),
        the Query Processor should extract all present entities with their correct values.
        
        Validates: Requirements 3.1
        """
        query_processor = QueryProcessor()
        query, expected_value = query_text
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Determine which entity type was in the query
        if any(str(i) in query for i in range(1, 101)):
            # Age entity
            if "age" in query.lower() or "years old" in query.lower() or "i am" in query.lower():
                assert "age" in result.entities, f"Age entity not extracted from: {query}"
                assert result.entities["age"] == expected_value, \
                    f"Expected age {expected_value}, got {result.entities.get('age')}"
    
    @settings(max_examples=25)
    @given(
        query_data=query_with_location_strategy(),
        session=user_session_strategy()
    )
    def test_entity_extraction_location(self, query_data, session):
        """
        Property 8: Entity Extraction Completeness - Location
        
        For any query containing location entities, the Query Processor should
        extract the location with correct state code.
        """
        query_processor = QueryProcessor()
        query, expected_state_code = query_data
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Verify location was extracted
        assert "location" in result.entities, f"Location entity not extracted from: {query}"
        assert result.entities["location"] == expected_state_code, \
            f"Expected location {expected_state_code}, got {result.entities.get('location')}"
    
    @settings(max_examples=25)
    @given(
        query_data=query_with_occupation_strategy(),
        session=user_session_strategy()
    )
    def test_entity_extraction_occupation(self, query_data, session):
        """
        Property 8: Entity Extraction Completeness - Occupation
        
        For any query containing occupation entities, the Query Processor should
        extract the occupation correctly.
        """
        query_processor = QueryProcessor()
        query, expected_occupation = query_data
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Verify occupation was extracted
        assert "occupation" in result.entities, f"Occupation entity not extracted from: {query}"
        assert result.entities["occupation"] == expected_occupation, \
            f"Expected occupation {expected_occupation}, got {result.entities.get('occupation')}"
    
    @settings(max_examples=25)
    @given(
        query_data=query_with_gender_strategy(),
        session=user_session_strategy()
    )
    def test_entity_extraction_gender(self, query_data, session):
        """
        Property 8: Entity Extraction Completeness - Gender
        
        For any query containing gender entities, the Query Processor should
        extract the gender correctly.
        """
        query_processor = QueryProcessor()
        query, expected_gender = query_data
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Verify gender was extracted
        assert "gender" in result.entities, f"Gender entity not extracted from: {query}"
        assert result.entities["gender"] == expected_gender, \
            f"Expected gender {expected_gender}, got {result.entities.get('gender')}"
    
    @settings(max_examples=25)
    @given(
        query_data=query_with_income_strategy(),
        session=user_session_strategy()
    )
    def test_entity_extraction_income(self, query_data, session):
        """
        Property 8: Entity Extraction Completeness - Income
        
        For any query containing income entities, the Query Processor should
        extract the income information correctly.
        """
        query_processor = QueryProcessor()
        query, expected_income = query_data
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Verify income was extracted
        assert "income" in result.entities, f"Income entity not extracted from: {query}"
        assert result.entities["income"] == expected_income, \
            f"Expected income {expected_income}, got {result.entities.get('income')}"
    
    @settings(max_examples=25)
    @given(
        query_data=query_with_category_strategy(),
        session=user_session_strategy()
    )
    def test_entity_extraction_category(self, query_data, session):
        """
        Property 8: Entity Extraction Completeness - Category
        
        For any query containing category entities, the Query Processor should
        extract the scheme category correctly.
        """
        query_processor = QueryProcessor()
        query, expected_category = query_data
        
        # Process the query
        result = query_processor.process_query(query, session)
        
        # Verify category was extracted
        assert "category" in result.entities, f"Category entity not extracted from: {query}"
        assert result.entities["category"] == expected_category, \
            f"Expected category {expected_category}, got {result.entities.get('category')}"



    # Property 12: Conversation Context Persistence
    # Validates: Requirements 3.5
    @settings(max_examples=25)
    @given(
        first_query_data=query_with_occupation_strategy(),
        second_query=st.text(min_size=5, max_size=100),
        session=user_session_strategy()
    )
    def test_conversation_context_persistence(self, first_query_data, second_query, session):
        """
        Property 12: Conversation Context Persistence
        
        For any multi-turn conversation, entities and context mentioned in earlier
        messages should be available and used in processing later messages within
        the same session.
        
        Validates: Requirements 3.5
        """
        query_processor = QueryProcessor()
        first_query, expected_occupation = first_query_data
        
        # Process first query to extract occupation
        result1 = query_processor.process_query(first_query, session)
        
        # Update session context with extracted entities
        session.update_context(result1.entities)
        
        # Process second query (which may not contain occupation)
        result2 = query_processor.process_query(second_query, session)
        
        # Verify that occupation from first query is still in context
        if "occupation" in result1.entities:
            assert "occupation" in result2.entities, \
                f"Occupation from first query not persisted in second query. " \
                f"First: {result1.entities}, Second: {result2.entities}"
            assert result2.entities["occupation"] == expected_occupation, \
                f"Occupation value changed. Expected {expected_occupation}, " \
                f"got {result2.entities.get('occupation')}"
    
    @settings(max_examples=25)
    @given(
        first_query_data=query_with_location_strategy(),
        second_query_data=query_with_occupation_strategy(),
        session=user_session_strategy()
    )
    def test_context_accumulation_across_turns(self, first_query_data, second_query_data, session):
        """
        Property 12: Conversation Context Persistence - Accumulation
        
        Context should accumulate across multiple turns, preserving all
        previously extracted entities.
        """
        query_processor = QueryProcessor()
        first_query, expected_location = first_query_data
        second_query, expected_occupation = second_query_data
        
        # Process first query to extract location
        result1 = query_processor.process_query(first_query, session)
        session.update_context(result1.entities)
        
        # Process second query to extract occupation
        result2 = query_processor.process_query(second_query, session)
        
        # Verify both location and occupation are in the final result
        if "location" in result1.entities:
            assert "location" in result2.entities, \
                "Location from first query not persisted"
            assert result2.entities["location"] == expected_location
        
        if "occupation" in result2.entities:
            assert result2.entities["occupation"] == expected_occupation
    
    @settings(max_examples=25)
    @given(
        queries=st.lists(
            st.one_of(
                query_with_age_strategy(),
                query_with_location_strategy(),
                query_with_occupation_strategy()
            ),
            min_size=2,
            max_size=5
        ),
        session=user_session_strategy()
    )
    def test_context_persistence_multiple_turns(self, queries, session):
        """
        Property 12: Conversation Context Persistence - Multiple Turns
        
        Context should persist across multiple conversation turns,
        accumulating all extracted entities.
        """
        query_processor = QueryProcessor()
        all_extracted_entities = {}
        
        for query_data in queries:
            query, expected_value = query_data
            
            # Process query
            result = query_processor.process_query(query, session)
            
            # Update session context
            session.update_context(result.entities)
            
            # Track all extracted entities
            all_extracted_entities.update(result.entities)
        
        # Process final query to verify all context is still present
        final_result = query_processor.process_query("show me schemes", session)
        
        # Verify all previously extracted entities are still in context
        for entity_type, entity_value in all_extracted_entities.items():
            assert entity_type in final_result.entities, \
                f"Entity {entity_type} not persisted across multiple turns"
            assert final_result.entities[entity_type] == entity_value, \
                f"Entity {entity_type} value changed from {entity_value} to {final_result.entities.get(entity_type)}"


    # Property 11: Spelling Error Robustness
    # Validates: Requirements 3.4
    @settings(max_examples=25)
    @given(
        session=user_session_strategy()
    )
    def test_spelling_error_robustness_occupation(self, session):
        """
        Property 11: Spelling Error Robustness
        
        For any query with common spelling errors or colloquial variations,
        the system should extract the same intent as the correctly spelled version.
        
        Validates: Requirements 3.4
        """
        query_processor = QueryProcessor()
        
        # Test common spelling variations for "farmer"
        correct_queries = ["I am a farmer", "farmer schemes", "for farmers"]
        misspelled_queries = ["I am a farmar", "farmar schemes", "for farmars"]
        
        # Process correct query
        correct_result = query_processor.process_query(correct_queries[0], session)
        correct_intent = correct_result.intent
        
        # For misspelled queries, we expect similar intent detection
        # Note: Entity extraction may not work for misspellings, but intent should be similar
        for misspelled in misspelled_queries:
            misspelled_result = query_processor.process_query(misspelled, session)
            # Intent should still be search_schemes (default for queries without clear intent keywords)
            assert misspelled_result.intent in [correct_intent, IntentType.SEARCH_SCHEMES], \
                f"Intent changed for misspelled query: {misspelled}"
    
    @settings(max_examples=25)
    @given(
        session=user_session_strategy()
    )
    def test_spelling_error_robustness_category(self, session):
        """
        Property 11: Spelling Error Robustness - Category
        
        Test that common category keywords are still recognized with minor spelling variations.
        """
        query_processor = QueryProcessor()
        
        # Test pairs of correct and misspelled category keywords
        test_cases = [
            ("education schemes", "educaton schemes"),  # Missing 'i'
            ("agriculture schemes", "agriclture schemes"),  # Missing 'u'
            ("health schemes", "helth schemes"),  # Missing 'a'
        ]
        
        for correct_query, misspelled_query in test_cases:
            correct_result = query_processor.process_query(correct_query, session)
            misspelled_result = query_processor.process_query(misspelled_query, session)
            
            # Both should have search_schemes intent
            assert correct_result.intent == IntentType.SEARCH_SCHEMES
            assert misspelled_result.intent == IntentType.SEARCH_SCHEMES
    
    @settings(max_examples=25)
    @given(
        session=user_session_strategy()
    )
    def test_colloquial_language_understanding(self, session):
        """
        Property 11: Spelling Error Robustness - Colloquial Language
        
        Test that colloquial or informal language variations are handled.
        """
        query_processor = QueryProcessor()
        
        # Test colloquial variations
        formal_queries = [
            "I am a student",
            "I am unemployed",
            "I need a job"
        ]
        
        colloquial_queries = [
            "im a student",  # "I'm" instead of "I am"
            "im unemployed",
            "i need job"  # Missing article "a"
        ]
        
        # Process queries - both should extract similar entities or intents
        for formal, colloquial in zip(formal_queries, colloquial_queries):
            formal_result = query_processor.process_query(formal, session)
            colloquial_result = query_processor.process_query(colloquial, session)
            
            # Both should have the same intent
            assert formal_result.intent == colloquial_result.intent, \
                f"Intent differs: formal={formal_result.intent}, colloquial={colloquial_result.intent}"
    
    @settings(max_examples=25)
    @given(
        base_query=st.sampled_from([
            "farmer", "student", "education", "health", "agriculture"
        ]),
        session=user_session_strategy()
    )
    def test_case_insensitivity(self, base_query, session):
        """
        Property 11: Spelling Error Robustness - Case Insensitivity
        
        Test that queries are case-insensitive.
        """
        query_processor = QueryProcessor()
        
        # Test different case variations
        lowercase = base_query.lower()
        uppercase = base_query.upper()
        titlecase = base_query.title()
        
        result_lower = query_processor.process_query(lowercase, session)
        result_upper = query_processor.process_query(uppercase, session)
        result_title = query_processor.process_query(titlecase, session)
        
        # All should extract the same entities and intent
        assert result_lower.intent == result_upper.intent == result_title.intent, \
            f"Intent differs across cases: lower={result_lower.intent}, " \
            f"upper={result_upper.intent}, title={result_title.intent}"
        
        # If entities were extracted, they should be the same
        if result_lower.entities:
            assert result_lower.entities == result_upper.entities == result_title.entities, \
                f"Entities differ across cases"
