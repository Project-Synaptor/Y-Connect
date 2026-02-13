"""Unit tests for LanguageDetector component"""

import pytest
from app.language_detector import LanguageDetector
from app.models import LanguageResult


class TestLanguageDetector:
    """Test suite for LanguageDetector class"""
    
    @pytest.fixture
    def detector(self):
        """Create a LanguageDetector instance for testing"""
        return LanguageDetector()
    
    def test_initialization(self, detector):
        """Test that LanguageDetector initializes correctly"""
        assert detector is not None
        assert len(detector.SUPPORTED_LANGUAGES) == 10
        assert detector.DEFAULT_LANGUAGE == "en"
    
    def test_supported_languages_count(self, detector):
        """Test that all 10 Indian languages are supported"""
        expected_languages = {"hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"}
        assert set(detector.SUPPORTED_LANGUAGES.keys()) == expected_languages
    
    def test_is_supported_language(self, detector):
        """Test is_supported_language method"""
        # Test supported languages
        assert detector.is_supported_language("hi") is True
        assert detector.is_supported_language("en") is True
        assert detector.is_supported_language("ta") is True
        assert detector.is_supported_language("te") is True
        assert detector.is_supported_language("bn") is True
        assert detector.is_supported_language("mr") is True
        assert detector.is_supported_language("gu") is True
        assert detector.is_supported_language("kn") is True
        assert detector.is_supported_language("ml") is True
        assert detector.is_supported_language("pa") is True
        
        # Test unsupported languages
        assert detector.is_supported_language("fr") is False
        assert detector.is_supported_language("es") is False
        assert detector.is_supported_language("zh") is False
        
        # Test case insensitivity
        assert detector.is_supported_language("HI") is True
        assert detector.is_supported_language("En") is True
    
    def test_get_language_name(self, detector):
        """Test get_language_name method"""
        assert detector.get_language_name("hi") == "Hindi"
        assert detector.get_language_name("en") == "English"
        assert detector.get_language_name("ta") == "Tamil"
        assert detector.get_language_name("te") == "Telugu"
        assert detector.get_language_name("bn") == "Bengali"
        assert detector.get_language_name("mr") == "Marathi"
        assert detector.get_language_name("gu") == "Gujarati"
        assert detector.get_language_name("kn") == "Kannada"
        assert detector.get_language_name("ml") == "Malayalam"
        assert detector.get_language_name("pa") == "Punjabi"
        
        # Test unsupported language
        assert detector.get_language_name("fr") == ""
    
    def test_detect_english(self, detector):
        """Test detection of English text"""
        text = "Hello, I am looking for government schemes"
        result = detector.detect_language(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence > 0.8
    
    def test_detect_hindi(self, detector):
        """Test detection of Hindi text"""
        text = "नमस्ते, मुझे सरकारी योजनाओं के बारे में जानकारी चाहिए"
        result = detector.detect_language(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "hi"
        assert result.language_name == "Hindi"
        assert result.confidence > 0.8
    
    def test_detect_tamil(self, detector):
        """Test detection of Tamil text"""
        text = "வணக்கம், எனக்கு அரசு திட்டங்கள் பற்றி தெரிந்து கொள்ள வேண்டும்"
        result = detector.detect_language(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "ta"
        assert result.language_name == "Tamil"
        assert result.confidence > 0.8
    
    def test_detect_telugu(self, detector):
        """Test detection of Telugu text"""
        text = "నమస్కారం, నాకు ప్రభుత్వ పథకాల గురించి తెలుసుకోవాలి"
        result = detector.detect_language(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "te"
        assert result.language_name == "Telugu"
        assert result.confidence > 0.8
    
    def test_detect_bengali(self, detector):
        """Test detection of Bengali text"""
        text = "নমস্কার, আমি সরকারি প্রকল্প সম্পর্কে জানতে চাই"
        result = detector.detect_language(text)
        
        assert isinstance(result, LanguageResult)
        assert result.language_code == "bn"
        assert result.language_name == "Bengali"
        assert result.confidence > 0.8
    
    def test_empty_text(self, detector):
        """Test handling of empty text"""
        result = detector.detect_language("")
        
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence == 0.0
    
    def test_very_short_text(self, detector):
        """Test handling of very short text (< 3 characters)"""
        result = detector.detect_language("hi")
        
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence == 0.3
    
    def test_whitespace_only(self, detector):
        """Test handling of whitespace-only text"""
        result = detector.detect_language("   ")
        
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence == 0.0
    
    def test_numbers_only(self, detector):
        """Test handling of numeric text"""
        result = detector.detect_language("123456")
        
        # Should default to English with low confidence
        assert result.language_code == "en"
        assert result.confidence < 0.8
    
    def test_mixed_language_text(self, detector):
        """Test handling of mixed language text"""
        # English with Hindi words
        text = "Hello नमस्ते how are you कैसे हो"
        result = detector.detect_language(text)
        
        # Should detect one of the supported languages
        assert result.language_code in detector.SUPPORTED_LANGUAGES
        assert isinstance(result, LanguageResult)
    
    def test_get_supported_languages(self, detector):
        """Test get_supported_languages method"""
        languages = detector.get_supported_languages()
        
        assert len(languages) == 10
        assert "hi" in languages
        assert "en" in languages
        assert languages["hi"] == "Hindi"
        assert languages["en"] == "English"
        
        # Verify it returns a copy (modifying shouldn't affect original)
        languages["test"] = "Test"
        assert "test" not in detector.SUPPORTED_LANGUAGES
    
    def test_result_model_validation(self, detector):
        """Test that returned LanguageResult passes Pydantic validation"""
        text = "This is a test message"
        result = detector.detect_language(text)
        
        # Should be a valid LanguageResult
        assert isinstance(result, LanguageResult)
        assert hasattr(result, "language_code")
        assert hasattr(result, "language_name")
        assert hasattr(result, "confidence")
        assert 0.0 <= result.confidence <= 1.0
    
    def test_special_characters(self, detector):
        """Test handling of text with special characters"""
        text = "Hello! @#$%^&*() How are you?"
        result = detector.detect_language(text)
        
        # Should still detect English
        assert result.language_code == "en"
        assert result.language_name == "English"
    
    def test_long_text(self, detector):
        """Test detection with longer text"""
        text = """
        The Government of India has launched several schemes for the welfare of citizens.
        These schemes cover various sectors including agriculture, education, health, and housing.
        Citizens can apply for these schemes through official government portals.
        """
        result = detector.detect_language(text)
        
        assert result.language_code == "en"
        assert result.language_name == "English"
        assert result.confidence > 0.9
