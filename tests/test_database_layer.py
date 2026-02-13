"""Tests for database layer implementation"""

import pytest
from datetime import datetime
from app.models import Scheme, SchemeStatus, SchemeCategory, SchemeAuthority, UserSession, Message, MessageRole
from app.database import db_pool, init_database, check_connection, drop_all_tables
from app.scheme_repository import SchemeRepository
from app.session_store import session_store


class TestDatabaseConnection:
    """Test PostgreSQL database connection"""
    
    def test_database_connection(self):
        """Test that database connection is working"""
        assert check_connection(), "Database connection should be successful"
    
    def test_database_initialization(self):
        """Test database schema initialization"""
        # This should not raise any exceptions
        init_database()
        assert check_connection(), "Database should be accessible after initialization"


class TestSchemeRepository:
    """Test scheme database operations"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Setup: Initialize database
        init_database()
        yield
        # Teardown: Clean up test data (optional)
    
    def test_insert_and_get_scheme(self):
        """Test inserting and retrieving a scheme"""
        scheme = Scheme(
            scheme_id="test_scheme_001",
            scheme_name="Test Agriculture Scheme",
            description="A test scheme for farmers",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Financial assistance for farmers",
            application_process="Apply online at official website",
            official_url="https://example.gov.in/scheme",
            status=SchemeStatus.ACTIVE
        )
        
        # Insert scheme
        result = SchemeRepository.insert_scheme(scheme)
        assert result, "Scheme insertion should succeed"
        
        # Retrieve scheme
        retrieved = SchemeRepository.get_scheme_by_id("test_scheme_001")
        assert retrieved is not None, "Scheme should be retrievable"
        assert retrieved.scheme_name == "Test Agriculture Scheme"
        assert retrieved.category == SchemeCategory.AGRICULTURE
        
        # Cleanup
        SchemeRepository.delete_scheme("test_scheme_001")
    
    def test_search_schemes_by_category(self):
        """Test searching schemes by category"""
        # Insert test schemes
        scheme1 = Scheme(
            scheme_id="test_edu_001",
            scheme_name="Education Scheme 1",
            description="Education scheme",
            category=SchemeCategory.EDUCATION,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Education benefits",
            application_process="Apply online",
            official_url="https://example.gov.in/edu1",
            status=SchemeStatus.ACTIVE
        )
        
        scheme2 = Scheme(
            scheme_id="test_health_001",
            scheme_name="Health Scheme 1",
            description="Health scheme",
            category=SchemeCategory.HEALTH,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Health benefits",
            application_process="Apply online",
            official_url="https://example.gov.in/health1",
            status=SchemeStatus.ACTIVE
        )
        
        SchemeRepository.insert_scheme(scheme1)
        SchemeRepository.insert_scheme(scheme2)
        
        # Search by category
        education_schemes = SchemeRepository.search_schemes(category="education")
        assert len(education_schemes) >= 1, "Should find at least one education scheme"
        assert all(s.category == SchemeCategory.EDUCATION for s in education_schemes)
        
        # Cleanup
        SchemeRepository.delete_scheme("test_edu_001")
        SchemeRepository.delete_scheme("test_health_001")
    
    def test_update_scheme(self):
        """Test updating a scheme"""
        # Insert test scheme
        scheme = Scheme(
            scheme_id="test_update_001",
            scheme_name="Original Name",
            description="Original description",
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Original benefits",
            application_process="Original process",
            official_url="https://example.gov.in/original",
            status=SchemeStatus.ACTIVE
        )
        
        SchemeRepository.insert_scheme(scheme)
        
        # Update scheme
        updates = {
            "scheme_name": "Updated Name",
            "description": "Updated description"
        }
        result = SchemeRepository.update_scheme("test_update_001", updates)
        assert result, "Scheme update should succeed"
        
        # Verify update
        updated = SchemeRepository.get_scheme_by_id("test_update_001")
        assert updated.scheme_name == "Updated Name"
        assert updated.description == "Updated description"
        
        # Cleanup
        SchemeRepository.delete_scheme("test_update_001")
    
    def test_get_scheme_translations(self):
        """Test retrieving scheme translations"""
        # Insert scheme with translations
        scheme = Scheme(
            scheme_id="test_trans_001",
            scheme_name="Test Scheme",
            scheme_name_translations={"hi": "परीक्षण योजना", "ta": "சோதனை திட்டம்"},
            description="Test description",
            description_translations={"hi": "परीक्षण विवरण"},
            category=SchemeCategory.AGRICULTURE,
            authority=SchemeAuthority.CENTRAL,
            applicable_states=["ALL"],
            benefits="Test benefits",
            benefits_translations={"hi": "परीक्षण लाभ"},
            application_process="Test process",
            application_process_translations={"hi": "परीक्षण प्रक्रिया"},
            official_url="https://example.gov.in/test",
            status=SchemeStatus.ACTIVE
        )
        
        SchemeRepository.insert_scheme(scheme)
        
        # Get Hindi translations
        translations = SchemeRepository.get_scheme_translations("test_trans_001", "hi")
        assert translations is not None
        assert translations["scheme_name"] == "परीक्षण योजना"
        assert translations["description"] == "परीक्षण विवरण"
        
        # Get Tamil translations (partial - should fall back to English for missing)
        translations_ta = SchemeRepository.get_scheme_translations("test_trans_001", "ta")
        assert translations_ta is not None
        assert translations_ta["scheme_name"] == "சோதனை திட்டம்"
        assert translations_ta["description"] == "Test description"  # Fallback to English
        
        # Cleanup
        SchemeRepository.delete_scheme("test_trans_001")


class TestRedisSessionStore:
    """Test Redis session storage"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Setup: Clear any existing test sessions
        yield
        # Teardown: Clean up test sessions
        session_store.delete_session("+919876543210")
        session_store.delete_session("+919876543211")
    
    def test_redis_connection(self):
        """Test that Redis connection is working"""
        assert session_store.check_connection(), "Redis connection should be successful"
    
    def test_store_and_retrieve_session(self):
        """Test storing and retrieving a session"""
        session = UserSession(
            session_id="test_session_001",
            phone_number="+919876543210",
            language="en",
            is_new_user=True
        )
        
        # Store session
        result = session_store.store_session(session)
        assert result, "Session storage should succeed"
        
        # Retrieve session
        retrieved = session_store.get_session("+919876543210")
        assert retrieved is not None, "Session should be retrievable"
        assert retrieved.session_id == "test_session_001"
        assert retrieved.phone_number == "+919876543210"
        assert retrieved.language == "en"
    
    def test_session_with_conversation_history(self):
        """Test storing session with conversation history"""
        session = UserSession(
            session_id="test_session_002",
            phone_number="+919876543211",
            language="hi"
        )
        
        # Add messages to conversation history
        session.add_message(Message(
            role=MessageRole.USER,
            content="Hello",
            language="en"
        ))
        session.add_message(Message(
            role=MessageRole.ASSISTANT,
            content="Hi! How can I help you?",
            language="en"
        ))
        
        # Store session
        session_store.store_session(session)
        
        # Retrieve and verify
        retrieved = session_store.get_session("+919876543211")
        assert retrieved is not None
        assert len(retrieved.conversation_history) == 2
        assert retrieved.conversation_history[0].content == "Hello"
        assert retrieved.conversation_history[1].role == MessageRole.ASSISTANT
    
    def test_update_session(self):
        """Test updating an existing session"""
        session = UserSession(
            session_id="test_session_003",
            phone_number="+919876543210",
            language="en"
        )
        
        # Store initial session
        session_store.store_session(session)
        
        # Update session
        session.language = "hi"
        session.user_context = {"age": 25, "location": "Delhi"}
        result = session_store.update_session(session)
        assert result, "Session update should succeed"
        
        # Verify update
        retrieved = session_store.get_session("+919876543210")
        assert retrieved.language == "hi"
        assert retrieved.user_context["age"] == 25
    
    def test_delete_session(self):
        """Test deleting a session"""
        session = UserSession(
            session_id="test_session_004",
            phone_number="+919876543210",
            language="en"
        )
        
        # Store session
        session_store.store_session(session)
        assert session_store.session_exists("+919876543210")
        
        # Delete session
        result = session_store.delete_session("+919876543210")
        assert result, "Session deletion should succeed"
        assert not session_store.session_exists("+919876543210")
    
    def test_session_ttl(self):
        """Test session TTL functionality"""
        session = UserSession(
            session_id="test_session_005",
            phone_number="+919876543210",
            language="en"
        )
        
        # Store session
        session_store.store_session(session)
        
        # Check TTL
        ttl = session_store.get_session_ttl("+919876543210")
        assert ttl is not None, "TTL should be set"
        assert ttl > 0, "TTL should be positive"
        assert ttl <= 86400, "TTL should not exceed 24 hours"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
