"""Unit tests for data anonymization module"""

import pytest
from app.data_anonymization import (
    DataAnonymizer,
    SessionDataCleaner,
    hash_phone,
    anonymize_phone,
    redact_pii,
    sanitize_analytics
)


class TestDataAnonymizer:
    """Test DataAnonymizer class"""
    
    def test_hash_phone_number(self):
        """Test phone number hashing"""
        phone = "+1234567890"
        hashed = DataAnonymizer.hash_phone_number(phone)
        
        # Should return a hex string
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 64 hex characters
        
        # Same phone should produce same hash
        assert DataAnonymizer.hash_phone_number(phone) == hashed
        
        # Different phone should produce different hash
        assert DataAnonymizer.hash_phone_number("+9876543210") != hashed
    
    def test_hash_phone_number_with_salt(self):
        """Test phone number hashing with salt"""
        phone = "+1234567890"
        salt1 = "secret1"
        salt2 = "secret2"
        
        hash1 = DataAnonymizer.hash_phone_number(phone, salt1)
        hash2 = DataAnonymizer.hash_phone_number(phone, salt2)
        
        # Different salts should produce different hashes
        assert hash1 != hash2
    
    def test_anonymize_phone_for_display(self):
        """Test phone number anonymization for display"""
        # Standard phone number
        assert DataAnonymizer.anonymize_phone_for_display("+1234567890") == "****7890"
        
        # Phone without + prefix
        assert DataAnonymizer.anonymize_phone_for_display("1234567890") == "****7890"
        
        # Short phone number
        assert DataAnonymizer.anonymize_phone_for_display("123") == "****"
        
        # Empty string
        assert DataAnonymizer.anonymize_phone_for_display("") == "****"
        
        # None value
        assert DataAnonymizer.anonymize_phone_for_display(None) == "****"
    
    def test_redact_pii_from_text_phone(self):
        """Test PII redaction for phone numbers"""
        text = "Call me at +1234567890 or 9876543210"
        redacted = DataAnonymizer.redact_pii_from_text(text)
        
        assert "+1234567890" not in redacted
        assert "9876543210" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_pii_from_text_email(self):
        """Test PII redaction for email addresses"""
        text = "Email me at user@example.com"
        redacted = DataAnonymizer.redact_pii_from_text(text)
        
        assert "user@example.com" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_pii_from_text_aadhaar(self):
        """Test PII redaction for Aadhaar numbers"""
        text = "My Aadhaar is 1234 5678 9012"
        redacted = DataAnonymizer.redact_pii_from_text(text)
        
        assert "1234 5678 9012" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_pii_from_text_pan(self):
        """Test PII redaction for PAN numbers"""
        text = "My PAN is ABCDE1234F"
        redacted = DataAnonymizer.redact_pii_from_text(text)
        
        assert "ABCDE1234F" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_pii_from_text_multiple(self):
        """Test PII redaction with multiple PII types"""
        text = "Contact: +1234567890, email: user@example.com, PAN: ABCDE1234F"
        redacted = DataAnonymizer.redact_pii_from_text(text)
        
        assert "+1234567890" not in redacted
        assert "user@example.com" not in redacted
        assert "ABCDE1234F" not in redacted
        assert redacted.count("[REDACTED]") == 3
    
    def test_redact_pii_from_dict(self):
        """Test PII redaction from dictionary"""
        data = {
            "phone": "+1234567890",
            "email": "user@example.com",
            "message": "Hello world",
            "age": 30
        }
        
        redacted = DataAnonymizer.redact_pii_from_dict(data)
        
        assert redacted["phone"] == "[REDACTED]"
        assert redacted["email"] == "[REDACTED]"
        assert redacted["message"] == "Hello world"  # No PII in message
        assert redacted["age"] == 30  # Non-string field unchanged
    
    def test_redact_pii_from_dict_nested(self):
        """Test PII redaction from nested dictionary"""
        data = {
            "user": {
                "phone": "+1234567890",
                "name": "John Doe"
            },
            "query": "farmer schemes"
        }
        
        redacted = DataAnonymizer.redact_pii_from_dict(data)
        
        assert redacted["user"]["phone"] == "[REDACTED]"
        assert redacted["user"]["name"] == "[REDACTED]"
        assert redacted["query"] == "farmer schemes"
    
    def test_redact_pii_from_dict_with_list(self):
        """Test PII redaction from dictionary with list"""
        data = {
            "users": [
                {"phone": "+1234567890"},
                {"phone": "+9876543210"}
            ]
        }
        
        redacted = DataAnonymizer.redact_pii_from_dict(data)
        
        assert redacted["users"][0]["phone"] == "[REDACTED]"
        assert redacted["users"][1]["phone"] == "[REDACTED]"
    
    def test_sanitize_for_analytics(self):
        """Test data sanitization for analytics"""
        data = {
            "phone": "+1234567890",
            "language": "en",
            "message_type": "text",
            "query": "farmer schemes in Punjab",
            "user_context": {
                "age": 35,
                "occupation": "farmer",
                "phone": "+1234567890"
            }
        }
        
        sanitized = DataAnonymizer.sanitize_for_analytics(data)
        
        # Should not include phone
        assert "phone" not in sanitized
        
        # Should include safe fields
        assert sanitized["language"] == "en"
        assert sanitized["message_type"] == "text"
        
        # Should include derived metrics
        assert "query_length" in sanitized
        assert sanitized["query_length"] == len("farmer schemes in Punjab")
        assert sanitized["has_query"] is True
        assert sanitized["has_phone"] is True
        
        # Should include safe context only
        assert "user_context" in sanitized
        assert sanitized["user_context"]["age"] == 35
        assert sanitized["user_context"]["occupation"] == "farmer"
        assert "phone" not in sanitized["user_context"]
    
    def test_sanitize_for_analytics_custom_fields(self):
        """Test data sanitization with custom allowed fields"""
        data = {
            "phone": "+1234567890",
            "language": "en",
            "custom_field": "value"
        }
        
        sanitized = DataAnonymizer.sanitize_for_analytics(
            data,
            allowed_fields=["language", "custom_field"]
        )
        
        assert "phone" not in sanitized
        assert sanitized["language"] == "en"
        assert sanitized["custom_field"] == "value"
    
    def test_generate_session_id(self):
        """Test session ID generation"""
        phone = "+1234567890"
        session_id = DataAnonymizer.generate_session_id(phone)
        
        # Should have session: prefix
        assert session_id.startswith("session:")
        
        # Should be consistent
        assert DataAnonymizer.generate_session_id(phone) == session_id
        
        # Different phone should produce different session ID
        assert DataAnonymizer.generate_session_id("+9876543210") != session_id


class TestSessionDataCleaner:
    """Test SessionDataCleaner class"""
    
    def test_prepare_session_for_deletion(self):
        """Test session data preparation for deletion"""
        session_data = {
            "session_id": "session:abc123",
            "phone_number": "+1234567890",
            "language": "en",
            "conversation_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ],
            "user_context": {"age": 30, "occupation": "farmer"},
            "created_at": "2024-01-01T00:00:00",
            "last_active": "2024-01-01T12:00:00",
            "is_new_user": False
        }
        
        cleaned = SessionDataCleaner.prepare_session_for_deletion(session_data)
        
        # Should not include PII fields
        assert "phone_number" not in cleaned
        assert "session_id" not in cleaned
        assert "conversation_history" not in cleaned
        assert "user_context" not in cleaned
        
        # Should include safe metadata
        assert cleaned["language"] == "en"
        assert cleaned["message_count"] == 2
        assert cleaned["was_new_user"] is False
    
    def test_verify_pii_removed_dict(self):
        """Test PII verification for dictionary"""
        # Data with no PII
        safe_data = {
            "language": "en",
            "message_count": 5,
            "timestamp": "2024-01-01T00:00:00"
        }
        assert SessionDataCleaner.verify_pii_removed(safe_data) is True
        
        # Data with phone number
        unsafe_data = {
            "language": "en",
            "phone": "+1234567890"
        }
        assert SessionDataCleaner.verify_pii_removed(unsafe_data) is False
    
    def test_verify_pii_removed_string(self):
        """Test PII verification for string"""
        # Safe string
        assert SessionDataCleaner.verify_pii_removed("Hello world") is True
        
        # String with phone
        assert SessionDataCleaner.verify_pii_removed("Call +1234567890") is False
        
        # String with email
        assert SessionDataCleaner.verify_pii_removed("Email user@example.com") is False
    
    def test_verify_pii_removed_list(self):
        """Test PII verification for list"""
        # Safe list
        safe_list = ["en", "hi", "ta"]
        assert SessionDataCleaner.verify_pii_removed(safe_list) is True
        
        # List with PII
        unsafe_list = ["en", "+1234567890"]
        assert SessionDataCleaner.verify_pii_removed(unsafe_list) is False
    
    def test_verify_pii_removed_nested(self):
        """Test PII verification for nested structures"""
        # Nested safe data
        safe_nested = {
            "metadata": {
                "language": "en",
                "tags": ["agriculture", "education"]
            }
        }
        assert SessionDataCleaner.verify_pii_removed(safe_nested) is True
        
        # Nested unsafe data
        unsafe_nested = {
            "metadata": {
                "language": "en",
                "contact": "+1234567890"
            }
        }
        assert SessionDataCleaner.verify_pii_removed(unsafe_nested) is False


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_hash_phone(self):
        """Test hash_phone convenience function"""
        phone = "+1234567890"
        hashed = hash_phone(phone)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64
    
    def test_anonymize_phone(self):
        """Test anonymize_phone convenience function"""
        assert anonymize_phone("+1234567890") == "****7890"
    
    def test_redact_pii(self):
        """Test redact_pii convenience function"""
        text = "Call +1234567890"
        redacted = redact_pii(text)
        
        assert "+1234567890" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_sanitize_analytics(self):
        """Test sanitize_analytics convenience function"""
        data = {
            "phone": "+1234567890",
            "language": "en"
        }
        
        sanitized = sanitize_analytics(data)
        
        assert "phone" not in sanitized
        assert sanitized["language"] == "en"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_inputs(self):
        """Test handling of empty inputs"""
        assert DataAnonymizer.hash_phone_number("") == ""
        assert DataAnonymizer.anonymize_phone_for_display("") == "****"
        assert DataAnonymizer.redact_pii_from_text("") == ""
        assert DataAnonymizer.redact_pii_from_dict({}) == {}
        assert DataAnonymizer.sanitize_for_analytics({}) == {}
    
    def test_none_inputs(self):
        """Test handling of None inputs"""
        assert DataAnonymizer.anonymize_phone_for_display(None) == "****"
        assert DataAnonymizer.redact_pii_from_text(None) is None
        assert DataAnonymizer.redact_pii_from_dict(None) is None
    
    def test_special_characters(self):
        """Test handling of special characters in phone numbers"""
        # Phone with spaces and dashes
        phone = "+1 (234) 567-8900"
        anonymized = DataAnonymizer.anonymize_phone_for_display(phone)
        assert anonymized == "****8900"
    
    def test_international_phone_formats(self):
        """Test various international phone formats"""
        phones = [
            "+911234567890",  # India
            "+861234567890",  # China
            "+441234567890",  # UK
        ]
        
        for phone in phones:
            hashed = DataAnonymizer.hash_phone_number(phone)
            assert len(hashed) == 64
            
            anonymized = DataAnonymizer.anonymize_phone_for_display(phone)
            assert anonymized.endswith(phone[-4:])
