"""Data anonymization utilities for Y-Connect WhatsApp Bot

Provides functions to hash phone numbers, redact PII from analytics data,
and ensure session data cleanup on expiry.
"""

import hashlib
import re
from typing import Any, Dict, Optional, Union


class DataAnonymizer:
    """Handles data anonymization and PII redaction"""
    
    # PII patterns to detect and redact
    PII_PATTERNS = {
        'phone': r'\+?\d{10,15}',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',  # Indian Aadhaar number
        'pan': r'\b[A-Z]{5}\d{4}[A-Z]\b',  # Indian PAN card
        'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    }
    
    @staticmethod
    def hash_phone_number(phone_number: str, salt: str = "") -> str:
        """
        Hash phone number using SHA256 for privacy
        
        Args:
            phone_number: Phone number to hash
            salt: Optional salt for hashing (use app secret in production)
            
        Returns:
            Hashed phone number (hex digest)
            
        Example:
            >>> DataAnonymizer.hash_phone_number("+1234567890")
            'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'
        """
        if not phone_number:
            return ""
        
        # Combine phone number with salt
        data = f"{phone_number}{salt}".encode('utf-8')
        
        # Generate SHA256 hash
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()
    
    @staticmethod
    def anonymize_phone_for_display(phone_number: str) -> str:
        """
        Anonymize phone number for display/logging (shows only last 4 digits)
        
        Args:
            phone_number: Phone number to anonymize
            
        Returns:
            Anonymized phone number (e.g., "****1234")
            
        Example:
            >>> DataAnonymizer.anonymize_phone_for_display("+1234567890")
            '****7890'
        """
        if not phone_number or not isinstance(phone_number, str):
            return "****"
        
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        if len(cleaned) < 4:
            return "****"
        
        return f"****{cleaned[-4:]}"
    
    @staticmethod
    def redact_pii_from_text(text: str, replacement: str = "[REDACTED]") -> str:
        """
        Redact PII (phone numbers, emails, Aadhaar, PAN, etc.) from text
        
        Args:
            text: Text containing potential PII
            replacement: Replacement string for redacted PII
            
        Returns:
            Text with PII redacted
            
        Example:
            >>> DataAnonymizer.redact_pii_from_text("Call me at +1234567890")
            'Call me at [REDACTED]'
        """
        if not text:
            return text
        
        redacted_text = text
        
        # Apply each PII pattern
        for pii_type, pattern in DataAnonymizer.PII_PATTERNS.items():
            redacted_text = re.sub(pattern, replacement, redacted_text)
        
        return redacted_text
    
    @staticmethod
    def redact_pii_from_dict(
        data: Dict[str, Any],
        fields_to_redact: Optional[list] = None,
        replacement: str = "[REDACTED]"
    ) -> Dict[str, Any]:
        """
        Redact PII from dictionary (for analytics data)
        
        Args:
            data: Dictionary containing potential PII
            fields_to_redact: List of field names to redact (if None, redacts common PII fields)
            replacement: Replacement value for redacted fields
            
        Returns:
            Dictionary with PII redacted
            
        Example:
            >>> data = {"phone": "+1234567890", "message": "Hello"}
            >>> DataAnonymizer.redact_pii_from_dict(data)
            {'phone': '[REDACTED]', 'message': 'Hello'}
        """
        if not data:
            return data
        
        # Default fields to redact
        if fields_to_redact is None:
            fields_to_redact = [
                'phone', 'phone_number', 'from_phone', 'to_phone',
                'email', 'aadhaar', 'pan', 'credit_card',
                'name', 'address', 'user_id', 'session_id'
            ]
        
        # Create a copy to avoid modifying original
        redacted_data = data.copy()
        
        # Redact specified fields
        for field in fields_to_redact:
            if field in redacted_data:
                # Always replace with placeholder for PII fields
                redacted_data[field] = replacement
        
        # Recursively redact nested dictionaries
        for key, value in redacted_data.items():
            if isinstance(value, dict):
                redacted_data[key] = DataAnonymizer.redact_pii_from_dict(
                    value,
                    fields_to_redact,
                    replacement
                )
            elif isinstance(value, list):
                redacted_data[key] = [
                    DataAnonymizer.redact_pii_from_dict(item, fields_to_redact, replacement)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
        
        return redacted_data
    
    @staticmethod
    def sanitize_for_analytics(
        data: Dict[str, Any],
        allowed_fields: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Sanitize data for analytics by keeping only allowed fields and redacting PII
        
        Args:
            data: Raw data to sanitize
            allowed_fields: List of fields allowed in analytics (if None, uses default safe fields)
            
        Returns:
            Sanitized dictionary safe for analytics
            
        Example:
            >>> data = {"phone": "+1234567890", "language": "en", "query": "farmer schemes"}
            >>> DataAnonymizer.sanitize_for_analytics(data)
            {'language': 'en', 'query_length': 14, 'has_query': True}
        """
        if not data:
            return {}
        
        # Default safe fields for analytics
        if allowed_fields is None:
            allowed_fields = [
                'language', 'message_type', 'intent', 'category',
                'scheme_count', 'response_time', 'error_type',
                'timestamp', 'status'
            ]
        
        # Create sanitized dictionary with only allowed fields
        sanitized = {}
        
        for field in allowed_fields:
            if field in data:
                sanitized[field] = data[field]
        
        # Add derived safe metrics
        if 'query' in data or 'text_content' in data:
            query_text = data.get('query') or data.get('text_content', '')
            sanitized['query_length'] = len(query_text)
            sanitized['has_query'] = bool(query_text)
        
        # Indicate presence of phone without including it
        if any(field in data for field in ['phone_number', 'from_phone', 'to_phone', 'phone']):
            sanitized['has_phone'] = True
        
        if 'user_context' in data and isinstance(data['user_context'], dict):
            # Include only non-PII context
            safe_context = {}
            for key in ['age', 'occupation', 'category', 'state']:
                if key in data['user_context']:
                    safe_context[key] = data['user_context'][key]
            if safe_context:
                sanitized['user_context'] = safe_context
        
        return sanitized
    
    @staticmethod
    def generate_session_id(phone_number: str, salt: str = "") -> str:
        """
        Generate a privacy-preserving session ID from phone number
        
        Args:
            phone_number: User's phone number
            salt: Optional salt for hashing
            
        Returns:
            Session ID with 'session:' prefix
            
        Example:
            >>> DataAnonymizer.generate_session_id("+1234567890")
            'session:a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3'
        """
        hashed = DataAnonymizer.hash_phone_number(phone_number, salt)
        return f"session:{hashed}"


class SessionDataCleaner:
    """Handles session data cleanup on expiry"""
    
    @staticmethod
    def prepare_session_for_deletion(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare session data for deletion by removing all PII
        
        This is called before session expiry to ensure no PII remains.
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Cleaned session data with PII removed
        """
        if not session_data:
            return {}
        
        # Fields to completely remove
        fields_to_remove = [
            'phone_number', 'from_phone', 'to_phone',
            'conversation_history', 'user_context',
            'session_id'
        ]
        
        # Create a copy
        cleaned = session_data.copy()
        
        # Remove PII fields
        for field in fields_to_remove:
            if field in cleaned:
                del cleaned[field]
        
        # Keep only metadata for debugging (no PII)
        safe_metadata = {
            'language': cleaned.get('language'),
            'created_at': cleaned.get('created_at'),
            'last_active': cleaned.get('last_active'),
            'message_count': len(session_data.get('conversation_history', [])),
            'was_new_user': cleaned.get('is_new_user', False)
        }
        
        return safe_metadata
    
    @staticmethod
    def verify_pii_removed(data: Union[Dict, str, list]) -> bool:
        """
        Verify that PII has been removed from data
        
        Args:
            data: Data to verify (dict, string, or list)
            
        Returns:
            True if no PII detected, False otherwise
        """
        if isinstance(data, dict):
            # Check all values recursively
            for value in data.values():
                if not SessionDataCleaner.verify_pii_removed(value):
                    return False
            return True
        
        elif isinstance(data, list):
            # Check all items recursively
            for item in data:
                if not SessionDataCleaner.verify_pii_removed(item):
                    return False
            return True
        
        elif isinstance(data, str):
            # Check for PII patterns
            for pattern in DataAnonymizer.PII_PATTERNS.values():
                if re.search(pattern, data):
                    return False
            return True
        
        # Other types (int, float, bool, None) are safe
        return True


# Convenience functions for common operations

def hash_phone(phone_number: str) -> str:
    """Convenience function to hash phone number"""
    return DataAnonymizer.hash_phone_number(phone_number)


def anonymize_phone(phone_number: str) -> str:
    """Convenience function to anonymize phone for display"""
    return DataAnonymizer.anonymize_phone_for_display(phone_number)


def redact_pii(text: str) -> str:
    """Convenience function to redact PII from text"""
    return DataAnonymizer.redact_pii_from_text(text)


def sanitize_analytics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to sanitize data for analytics"""
    return DataAnonymizer.sanitize_for_analytics(data)
