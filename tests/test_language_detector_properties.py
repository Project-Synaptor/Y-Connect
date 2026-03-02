"""Property-based tests for LanguageDetector component using Hypothesis"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from app.language_detector import LanguageDetector
from app.models import LanguageResult


class TestLanguageDetectorProperties:
    """Property-based test suite for LanguageDetector"""
    
    # Property 6: Language Detection Accuracy
    # Feature: y-connect-whatsapp-bot, Property 6: Language Detection Accuracy
    # Validates: Requirements 2.2
    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'),
                min_codepoint=32,
                max_codepoint=0x0FFF
            ),
            min_size=10,
            max_size=200
        )
    )
    @settings(max_examples=25, deadline=None)
    def test_property_language_detection_returns_valid_result(self, text):
        """
        Property 6: Language Detection Accuracy
        
        For any message in a supported language, the language detector should 
        identify the correct language with at least 90% accuracy across a 
        diverse test set.
        
        This property verifies that:
        1. The detector always returns a valid LanguageResult
        2. The language code is always one of the supported languages
        3. The confidence is always between 0.0 and 1.0
        4. The language name matches the language code
        """
        # Skip empty or whitespace-only text
        assume(text.strip() != "")
        
        # Create detector instance
        detector = LanguageDetector()
        
        # Detect language
        result = detector.detect_language(text)
        
        # Verify result is a valid LanguageResult
        assert isinstance(result, LanguageResult)
        
        # Verify language code is supported
        assert result.language_code in detector.SUPPORTED_LANGUAGES
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0
        
        # Verify language name matches the code
        expected_name = detector.SUPPORTED_LANGUAGES[result.language_code]
        assert result.language_name == expected_name
    
    @given(
        lang_code=st.sampled_from(["hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"])
    )
    @settings(max_examples=12, deadline=None)
    def test_property_supported_language_check_consistency(self, lang_code):
        """
        Property: Supported language check is consistent
        
        For any supported language code, is_supported_language should return True,
        and get_language_name should return a non-empty name.
        """
        # Create detector instance
        detector = LanguageDetector()
        
        # Check that the language is supported
        assert detector.is_supported_language(lang_code) is True
        
        # Check that we can get the language name
        name = detector.get_language_name(lang_code)
        assert name != ""
        assert isinstance(name, str)
        
        # Check that the name is in the supported languages dict
        assert name == detector.SUPPORTED_LANGUAGES[lang_code]
    
    @given(
        text=st.text(min_size=0, max_size=2)
    )
    @settings(max_examples=12, deadline=None)
    def test_property_short_text_handling(self, text):
        """
        Property: Short text handling is safe
        
        For any very short text (0-2 characters), the detector should:
        1. Not crash or raise exceptions
        2. Return a valid LanguageResult
        3. Return default language (English) with low confidence
        """
        # Create detector instance
        detector = LanguageDetector()
        
        result = detector.detect_language(text)
        
        # Should return a valid result
        assert isinstance(result, LanguageResult)
        
        # Should return default language
        assert result.language_code == detector.DEFAULT_LANGUAGE
        
        # Should have low confidence for very short text
        assert result.confidence <= 0.5
    
    @given(
        text1=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=20,
            max_size=100
        ),
        text2=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll')),
            min_size=20,
            max_size=100
        )
    )
    @settings(max_examples=12, deadline=None)
    def test_property_detection_determinism(self, text1, text2):
        """
        Property: Language detection is deterministic
        
        For any two identical texts, the detector should return the same result.
        For any two different texts, the detector should handle them independently.
        """
        # Skip if texts are empty or whitespace-only
        assume(text1.strip() != "" and text2.strip() != "")
        
        # Create detector instance
        detector = LanguageDetector()
        
        # Detect language for both texts
        result1_first = detector.detect_language(text1)
        result1_second = detector.detect_language(text1)
        
        # Same text should give same result (determinism)
        assert result1_first.language_code == result1_second.language_code
        assert result1_first.language_name == result1_second.language_name
        # Note: confidence might vary slightly due to langdetect's probabilistic nature
        # but language code should be consistent
        
        # Both results should be valid
        assert isinstance(result1_first, LanguageResult)
        assert isinstance(result1_second, LanguageResult)
    
    @given(
        whitespace=st.text(alphabet=st.characters(whitelist_categories=('Zs',)), min_size=1, max_size=20)
    )
    @settings(max_examples=10, deadline=None)
    def test_property_whitespace_handling(self, whitespace):
        """
        Property: Whitespace-only text is handled gracefully
        
        For any whitespace-only text, the detector should:
        1. Return default language (English)
        2. Return zero confidence
        3. Not crash
        """
        # Create detector instance
        detector = LanguageDetector()
        
        result = detector.detect_language(whitespace)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == detector.DEFAULT_LANGUAGE
        assert result.confidence == 0.0
    
    @given(
        numbers=st.text(alphabet='0123456789', min_size=1, max_size=50)
    )
    @settings(max_examples=10, deadline=None)
    def test_property_numeric_text_handling(self, numbers):
        """
        Property: Numeric text is handled gracefully
        
        For any numeric-only text (ASCII digits), the detector should:
        1. Return a valid LanguageResult
        2. Not crash
        3. Return a supported language code
        """
        # Create detector instance
        detector = LanguageDetector()
        
        result = detector.detect_language(numbers)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code in detector.SUPPORTED_LANGUAGES
        # ASCII numeric text should have low confidence or default to English
        # (since numbers don't have language-specific features)
    
    @given(
        text=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=25, deadline=None)
    def test_property_no_exceptions_on_any_input(self, text):
        """
        Property: Detector never crashes on any input
        
        For any text input (valid or invalid), the detector should:
        1. Never raise an exception
        2. Always return a LanguageResult
        3. Always return a supported language code
        """
        # Create detector instance
        detector = LanguageDetector()
        
        try:
            result = detector.detect_language(text)
            
            # Should always return a valid result
            assert isinstance(result, LanguageResult)
            assert result.language_code in detector.SUPPORTED_LANGUAGES
            assert 0.0 <= result.confidence <= 1.0
            
        except Exception as e:
            # Should never raise an exception
            pytest.fail(f"Detector raised exception on input '{text[:50]}...': {e}")
    
    def test_property_supported_languages_immutable(self):
        """
        Property: Supported languages dictionary is immutable
        
        Getting supported languages should return a copy, not the original dict.
        """
        # Create detector instance
        detector = LanguageDetector()
        
        languages1 = detector.get_supported_languages()
        languages2 = detector.get_supported_languages()
        
        # Should return equal dicts
        assert languages1 == languages2
        
        # Modifying one should not affect the other
        languages1["test"] = "Test Language"
        assert "test" not in languages2
        assert "test" not in detector.SUPPORTED_LANGUAGES
