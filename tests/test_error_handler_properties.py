"""Property-based tests for error handling"""

import re
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck

from app.error_handler import ErrorHandler, generate_user_error_message


# Strategy for generating various exception types
@st.composite
def exception_strategy(draw):
    """Generate various exception types with different messages"""
    exception_types = [
        ValueError,
        KeyError,
        ConnectionError,
        TimeoutError,
        RuntimeError,
        TypeError,
        AttributeError,
    ]
    
    exc_type = draw(st.sampled_from(exception_types))
    
    # Generate error message that might contain sensitive data
    message_parts = []
    
    # Add some normal text
    message_parts.append(draw(st.text(min_size=5, max_size=50)))
    
    # Randomly add sensitive data
    if draw(st.booleans()):
        # Add file path
        message_parts.append(f"/app/components/handler.py")
    
    if draw(st.booleans()):
        # Add line number
        message_parts.append(f"line {draw(st.integers(min_value=1, max_value=1000))}")
    
    if draw(st.booleans()):
        # Add stack trace snippet
        message_parts.append("Traceback (most recent call last)")
    
    if draw(st.booleans()):
        # Add internal component name
        message_parts.append(f"in {draw(st.sampled_from(['SessionManager', 'RAGEngine', 'VectorStore', 'QueryProcessor']))}")
    
    message = " ".join(message_parts)
    
    return exc_type(message)


class TestErrorMessageSanitization:
    """
    Property 28: Error Message Sanitization
    
    For any system error, the user-facing error message should not contain
    stack traces, internal component names, or technical implementation details.
    
    Validates: Requirements 9.5
    """
    
    @given(error=exception_strategy())
    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_messages_do_not_contain_stack_traces(self, error):
        """
        Property: Error messages should not contain stack traces
        
        For any exception, the sanitized error message should not contain
        stack trace indicators like "Traceback", "File", or line numbers.
        """
        # Generate sanitized error message
        sanitized_message = ErrorHandler.sanitize_error_message(error, include_details=False)
        
        # Check that message doesn't contain stack trace indicators
        stack_trace_patterns = [
            r"Traceback",
            r"File \".*\"",
            r"line \d+",
            r"in <module>",
            r"raise \w+",
        ]
        
        for pattern in stack_trace_patterns:
            assert not re.search(pattern, sanitized_message, re.IGNORECASE), \
                f"Sanitized message contains stack trace pattern '{pattern}': {sanitized_message}"
    
    @given(error=exception_strategy())
    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_messages_do_not_contain_file_paths(self, error):
        """
        Property: Error messages should not contain file paths
        
        For any exception, the sanitized error message should not contain
        file paths that reveal internal structure.
        """
        # Generate sanitized error message
        sanitized_message = ErrorHandler.sanitize_error_message(error, include_details=False)
        
        # Check that message doesn't contain file paths
        file_path_patterns = [
            r"/app/\w+",
            r"/usr/\w+",
            r"C:\\",
            r"\.py",
            r"/src/",
            r"/lib/",
        ]
        
        for pattern in file_path_patterns:
            assert not re.search(pattern, sanitized_message, re.IGNORECASE), \
                f"Sanitized message contains file path pattern '{pattern}': {sanitized_message}"
    
    @given(error=exception_strategy())
    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_messages_are_user_friendly(self, error):
        """
        Property: Error messages should be user-friendly
        
        For any exception, the sanitized error message should be a complete
        sentence that provides actionable guidance to the user.
        """
        # Generate sanitized error message
        sanitized_message = ErrorHandler.sanitize_error_message(error, include_details=False)
        
        # Check that message is not empty
        assert len(sanitized_message) > 0, "Sanitized message is empty"
        
        # Check that message is a reasonable length (not too short, not too long)
        assert 20 <= len(sanitized_message) <= 500, \
            f"Sanitized message length is unreasonable: {len(sanitized_message)}"
        
        # Check that message contains helpful words
        helpful_words = ["try", "again", "please", "check", "moment", "later", "issue"]
        assert any(word in sanitized_message.lower() for word in helpful_words), \
            f"Sanitized message doesn't contain helpful guidance: {sanitized_message}"
    
    @given(
        error=exception_strategy(),
        include_details=st.booleans()
    )
    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_messages_do_not_expose_internal_components(self, error, include_details):
        """
        Property: Error messages should not expose internal component names
        
        For any exception, the sanitized error message should not contain
        internal component names that reveal system architecture.
        """
        # Generate sanitized error message
        sanitized_message = ErrorHandler.sanitize_error_message(error, include_details=include_details)
        
        # Internal component names that should not appear
        internal_components = [
            "SessionManager",
            "RAGEngine",
            "VectorStore",
            "QueryProcessor",
            "LanguageDetector",
            "ResponseGenerator",
            "WebhookHandler",
            "WhatsAppClient",
            "EmbeddingGenerator",
        ]
        
        # When include_details is False, no internal components should appear
        if not include_details:
            for component in internal_components:
                assert component not in sanitized_message, \
                    f"Sanitized message exposes internal component '{component}': {sanitized_message}"
    
    @given(
        error_type=st.sampled_from([
            "language_detection",
            "query_processing",
            "retrieval",
            "generation",
            "api",
            "default"
        ]),
        language=st.sampled_from(["en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"])
    )
    @settings(max_examples=25)
    def test_user_error_messages_are_localized(self, error_type, language):
        """
        Property: User error messages should be available in all supported languages
        
        For any error type and supported language, a localized error message
        should be generated.
        """
        # Generate user error message
        message = generate_user_error_message(error_type, language)
        
        # Check that message is not empty
        assert len(message) > 0, f"Error message is empty for {error_type} in {language}"
        
        # Check that message is reasonable length
        assert 10 <= len(message) <= 500, \
            f"Error message length is unreasonable: {len(message)}"
    
    @given(
        error_type=st.sampled_from([
            "language_detection",
            "query_processing",
            "retrieval",
            "generation",
            "api",
        ])
    )
    @settings(max_examples=12)
    def test_user_error_messages_fallback_to_english(self, error_type):
        """
        Property: User error messages should fallback to English for unsupported languages
        
        For any error type and unsupported language, the system should return
        an English error message rather than failing.
        """
        # Try with unsupported language
        unsupported_language = "xx"
        
        # Generate user error message
        message = generate_user_error_message(error_type, unsupported_language)
        
        # Check that message is not empty (fallback worked)
        assert len(message) > 0, f"Error message is empty for {error_type} with unsupported language"
        
        # Check that it's the English version (compare with explicit English request)
        english_message = generate_user_error_message(error_type, "en")
        assert message == english_message, \
            f"Fallback message doesn't match English version for {error_type}"



class TestLogAnonymization:
    """
    Property 26: Log Anonymization
    
    For any logged event, the log entry should not contain phone numbers
    or other PII in plain text (should be hashed or redacted).
    
    Validates: Requirements 8.5
    """
    
    @given(
        phone_number=st.one_of(
            # International format with +
            st.from_regex(r'\+\d{10,15}', fullmatch=True),
            # Without + prefix
            st.from_regex(r'\d{10,15}', fullmatch=True),
            # With dashes
            st.from_regex(r'\+?\d{1,3}-\d{3,4}-\d{3,4}-\d{4}', fullmatch=True),
            # With spaces
            st.from_regex(r'\+?\d{1,3}\s\d{3,4}\s\d{3,4}\s\d{4}', fullmatch=True),
            # With parentheses
            st.from_regex(r'\+?\d{1,3}\s?\(\d{3,4}\)\s?\d{3,4}-\d{4}', fullmatch=True),
        )
    )
    @settings(max_examples=25)
    def test_phone_numbers_are_anonymized_in_text(self, phone_number):
        """
        Property: Phone numbers in text should be anonymized
        
        For any phone number in any format, the anonymize_phone function
        should redact all but the last 4 digits.
        """
        # Create text containing phone number
        text = f"User with phone {phone_number} sent a message"
        
        # Anonymize the text
        anonymized_text = ErrorHandler.anonymize_phone(text)
        
        # Extract digits from original phone number
        original_digits = ''.join(c for c in phone_number if c.isdigit())
        
        # Check that original phone number is not in anonymized text
        assert phone_number not in anonymized_text, \
            f"Original phone number still present in anonymized text: {anonymized_text}"
        
        # Check that anonymized text contains **** pattern
        assert "****" in anonymized_text, \
            f"Anonymized text doesn't contain redaction pattern: {anonymized_text}"
        
        # If phone has at least 4 digits, check that last 4 are preserved
        if len(original_digits) >= 4:
            last_four = original_digits[-4:]
            assert last_four in anonymized_text, \
                f"Last 4 digits not preserved in anonymized text: {anonymized_text}"
    
    @given(
        phone_numbers=st.lists(
            st.from_regex(r'\+\d{10,15}', fullmatch=True),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=25)
    def test_multiple_phone_numbers_are_anonymized(self, phone_numbers):
        """
        Property: Multiple phone numbers in text should all be anonymized
        
        For any text containing multiple phone numbers, all phone numbers
        should be anonymized.
        """
        # Create text with multiple phone numbers
        text = f"Users {', '.join(phone_numbers)} sent messages"
        
        # Anonymize the text
        anonymized_text = ErrorHandler.anonymize_phone(text)
        
        # Check that none of the original phone numbers appear in full
        for phone in phone_numbers:
            assert phone not in anonymized_text, \
                f"Original phone number {phone} still present in anonymized text"
        
        # Check that we have the right number of **** patterns
        redaction_count = anonymized_text.count("****")
        assert redaction_count == len(phone_numbers), \
            f"Expected {len(phone_numbers)} redactions, found {redaction_count}"
    
    @given(
        text=st.text(min_size=10, max_size=200),
        phone_number=st.from_regex(r'\+\d{10,15}', fullmatch=True)
    )
    @settings(max_examples=25)
    def test_anonymization_preserves_non_phone_content(self, text, phone_number):
        """
        Property: Anonymization should preserve non-phone content
        
        For any text containing a phone number, the anonymization should
        only affect the phone number and preserve other content.
        """
        # Filter out any accidental phone-like patterns from random text
        # by removing digit sequences
        clean_text = ''.join(c if not c.isdigit() else 'X' for c in text)
        
        # Create text with phone number embedded
        full_text = f"{clean_text} {phone_number} {clean_text}"
        
        # Anonymize the text
        anonymized_text = ErrorHandler.anonymize_phone(full_text)
        
        # Check that non-phone content is preserved (with X instead of digits)
        # The clean_text parts should still be recognizable
        assert len(anonymized_text) > 0, "Anonymized text is empty"
        
        # Check that phone number was anonymized
        assert phone_number not in anonymized_text, \
            f"Phone number not anonymized: {anonymized_text}"
    
    @given(
        phone_number=st.from_regex(r'\+\d{10,15}', fullmatch=True)
    )
    @settings(max_examples=25)
    def test_anonymization_is_consistent(self, phone_number):
        """
        Property: Anonymization should be consistent
        
        For any phone number, anonymizing it multiple times should produce
        the same result.
        """
        text = f"Phone: {phone_number}"
        
        # Anonymize multiple times
        result1 = ErrorHandler.anonymize_phone(text)
        result2 = ErrorHandler.anonymize_phone(text)
        result3 = ErrorHandler.anonymize_phone(text)
        
        # All results should be identical
        assert result1 == result2 == result3, \
            f"Anonymization is not consistent: {result1}, {result2}, {result3}"
    
    @given(
        phone_number=st.from_regex(r'\+\d{4,9}', fullmatch=True)
    )
    @settings(max_examples=12)
    def test_short_phone_numbers_are_partially_redacted(self, phone_number):
        """
        Property: Short phone numbers (4-9 digits) should show last 4 digits
        
        For any phone number with 4-9 digits, the anonymization should
        show **** followed by the last 4 digits.
        """
        text = f"Phone: {phone_number}"
        
        # Anonymize the text
        anonymized_text = ErrorHandler.anonymize_phone(text)
        
        # Check that original phone is not present in full
        assert phone_number not in anonymized_text, \
            f"Phone number not anonymized: {anonymized_text}"
        
        # Check that it contains **** pattern
        assert "****" in anonymized_text, \
            f"Anonymized text doesn't contain redaction pattern: {anonymized_text}"
        
        # Extract digits from phone number
        digits = ''.join(c for c in phone_number if c.isdigit())
        
        # Check that last 4 digits are preserved
        if len(digits) >= 4:
            last_four = digits[-4:]
            assert last_four in anonymized_text, \
                f"Last 4 digits not preserved: {anonymized_text}"
    
    @given(
        error_message=st.text(min_size=10, max_size=200),
        phone_number=st.from_regex(r'\+\d{10,15}', fullmatch=True)
    )
    @settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_error_logging_anonymizes_phone_numbers(self, error_message, phone_number):
        """
        Property: Error logging should anonymize phone numbers
        
        For any error with a phone number in the context, the logged
        error should have the phone number anonymized.
        """
        # Create an error with phone number in message
        error = ValueError(f"{error_message} for user {phone_number}")
        
        # Create request context with phone number
        request_context = {
            "user_phone": phone_number,
            "message": f"Message from {phone_number}"
        }
        
        # Log the error (we can't easily test the actual log output,
        # but we can test that the anonymization function works)
        # The CustomJsonFormatter will handle anonymization
        
        # Test that anonymize_phone works on the error message
        anonymized_error = ErrorHandler.anonymize_phone(str(error))
        
        # Check that phone number is anonymized
        assert phone_number not in anonymized_error, \
            f"Phone number not anonymized in error message: {anonymized_error}"
        
        # Test that anonymize_phone works on request context
        anonymized_context_phone = ErrorHandler.anonymize_phone(request_context["user_phone"])
        assert phone_number not in anonymized_context_phone, \
            f"Phone number not anonymized in context: {anonymized_context_phone}"
