"""Verification script for database layer implementation"""

import sys
from datetime import datetime

print("="*60)
print("Database Layer Implementation Verification")
print("="*60)
print()

# Test imports
try:
    from app.database import DatabasePool, db_pool, init_database, check_connection
    from app.scheme_repository import SchemeRepository
    from app.session_store import RedisSessionStore, session_store
    from app.models import (
        Scheme, SchemeStatus, SchemeCategory, SchemeAuthority,
        UserSession, Message, MessageRole
    )
    print("✓ All database layer modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

# Test class instantiation
try:
    # Test DatabasePool singleton
    pool1 = DatabasePool()
    pool2 = DatabasePool()
    assert pool1 is pool2, "DatabasePool should be singleton"
    print("✓ DatabasePool singleton pattern works")
    
    # Test RedisSessionStore singleton
    store1 = RedisSessionStore()
    store2 = RedisSessionStore()
    assert store1 is store2, "RedisSessionStore should be singleton"
    print("✓ RedisSessionStore singleton pattern works")
except Exception as e:
    print(f"✗ Singleton pattern error: {e}")
    sys.exit(1)

# Test model creation
try:
    # Create a test scheme
    scheme = Scheme(
        scheme_id="test_001",
        scheme_name="Test Scheme",
        scheme_name_translations={"hi": "परीक्षण योजना"},
        description="Test description",
        description_translations={"hi": "परीक्षण विवरण"},
        category=SchemeCategory.AGRICULTURE,
        authority=SchemeAuthority.CENTRAL,
        applicable_states=["ALL"],
        eligibility_criteria={"age": "18+"},
        benefits="Test benefits",
        benefits_translations={"hi": "परीक्षण लाभ"},
        application_process="Apply online",
        application_process_translations={"hi": "ऑनलाइन आवेदन करें"},
        official_url="https://example.gov.in/test",
        helpline_numbers=["+911234567890"],
        status=SchemeStatus.ACTIVE,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2025, 12, 31)
    )
    print("✓ Scheme model created successfully")
    
    # Test scheme translation method
    translation = scheme.get_translation("scheme_name", "hi")
    assert translation == "परीक्षण योजना", "Translation should work"
    print("✓ Scheme translation method works")
    
    # Create a test session
    session = UserSession(
        session_id="session_001",
        phone_number="+919876543210",
        language="en",
        is_new_user=True
    )
    print("✓ UserSession model created successfully")
    
    # Test session methods
    message = Message(
        role=MessageRole.USER,
        content="Hello",
        language="en"
    )
    session.add_message(message)
    assert len(session.conversation_history) == 1, "Message should be added"
    print("✓ Session add_message method works")
    
    session.update_context({"age": 25, "location": "Delhi"})
    assert session.user_context["age"] == 25, "Context should be updated"
    print("✓ Session update_context method works")
    
    recent = session.get_recent_messages(count=5)
    assert len(recent) == 1, "Should get recent messages"
    print("✓ Session get_recent_messages method works")
    
except Exception as e:
    print(f"✗ Model creation error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test repository methods exist
try:
    assert hasattr(SchemeRepository, 'get_scheme_by_id'), "get_scheme_by_id should exist"
    assert hasattr(SchemeRepository, 'search_schemes'), "search_schemes should exist"
    assert hasattr(SchemeRepository, 'get_scheme_translations'), "get_scheme_translations should exist"
    assert hasattr(SchemeRepository, 'insert_scheme'), "insert_scheme should exist"
    assert hasattr(SchemeRepository, 'update_scheme'), "update_scheme should exist"
    assert hasattr(SchemeRepository, 'delete_scheme'), "delete_scheme should exist"
    print("✓ All SchemeRepository methods exist")
except AssertionError as e:
    print(f"✗ Repository method missing: {e}")
    sys.exit(1)

# Test session store methods exist
try:
    assert hasattr(session_store, 'store_session'), "store_session should exist"
    assert hasattr(session_store, 'get_session'), "get_session should exist"
    assert hasattr(session_store, 'update_session'), "update_session should exist"
    assert hasattr(session_store, 'delete_session'), "delete_session should exist"
    assert hasattr(session_store, 'session_exists'), "session_exists should exist"
    assert hasattr(session_store, 'get_session_ttl'), "get_session_ttl should exist"
    assert hasattr(session_store, 'check_connection'), "check_connection should exist"
    print("✓ All RedisSessionStore methods exist")
except AssertionError as e:
    print(f"✗ Session store method missing: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✓ Database layer implementation verification PASSED")
print("="*60)
print("\nImplemented components:")
print("  • PostgreSQL connection pool (app/database.py)")
print("  • Database schema initialization")
print("  • Scheme repository with CRUD operations (app/scheme_repository.py)")
print("  • Redis session store with TTL support (app/session_store.py)")
print("\nNote: Actual database connectivity tests require running PostgreSQL and Redis instances.")
print("      Use tests/test_database_layer.py with pytest for integration testing.")
