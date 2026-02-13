"""Tests for configuration management"""

import pytest
from app.config import Settings


def test_settings_default_values():
    """Test that settings have sensible defaults"""
    # Create settings without environment variables
    settings = Settings(
        whatsapp_access_token="test_token",
        whatsapp_phone_number_id="test_id",
        whatsapp_verify_token="test_verify",
        whatsapp_app_secret="test_secret",
        llm_api_key="test_llm_key",
        vector_db_api_key="test_vector_key",
        vector_db_environment="test_env",
        postgres_password="test_password"
    )
    
    assert settings.app_name == "y-connect-whatsapp-bot"
    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.max_message_length == 1600
    assert settings.rag_top_k_results == 5
    assert settings.session_expiry_hours == 24


def test_postgres_url_construction():
    """Test PostgreSQL URL is constructed correctly"""
    settings = Settings(
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="testdb",
        whatsapp_access_token="test",
        whatsapp_phone_number_id="test",
        whatsapp_verify_token="test",
        whatsapp_app_secret="test",
        llm_api_key="test",
        vector_db_api_key="test",
        vector_db_environment="test"
    )
    
    expected_url = "postgresql://testuser:testpass@localhost:5432/testdb"
    assert settings.postgres_url == expected_url


def test_redis_url_without_password():
    """Test Redis URL construction without password"""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password=None,
        whatsapp_access_token="test",
        whatsapp_phone_number_id="test",
        whatsapp_verify_token="test",
        whatsapp_app_secret="test",
        llm_api_key="test",
        vector_db_api_key="test",
        vector_db_environment="test",
        postgres_password="test"
    )
    
    expected_url = "redis://localhost:6379/0"
    assert settings.redis_url == expected_url


def test_redis_url_with_password():
    """Test Redis URL construction with password"""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password="secret",
        whatsapp_access_token="test",
        whatsapp_phone_number_id="test",
        whatsapp_verify_token="test",
        whatsapp_app_secret="test",
        llm_api_key="test",
        vector_db_api_key="test",
        vector_db_environment="test",
        postgres_password="test"
    )
    
    expected_url = "redis://:secret@localhost:6379/0"
    assert settings.redis_url == expected_url


def test_environment_detection():
    """Test environment detection properties"""
    dev_settings = Settings(
        app_env="development",
        whatsapp_access_token="test",
        whatsapp_phone_number_id="test",
        whatsapp_verify_token="test",
        whatsapp_app_secret="test",
        llm_api_key="test",
        vector_db_api_key="test",
        vector_db_environment="test",
        postgres_password="test"
    )
    
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False
    
    prod_settings = Settings(
        app_env="production",
        whatsapp_access_token="test",
        whatsapp_phone_number_id="test",
        whatsapp_verify_token="test",
        whatsapp_app_secret="test",
        llm_api_key="test",
        vector_db_api_key="test",
        vector_db_environment="test",
        postgres_password="test"
    )
    
    assert prod_settings.is_production is True
    assert prod_settings.is_development is False
