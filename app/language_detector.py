"""Language detection component for Y-Connect WhatsApp Bot"""

from typing import Dict
import logging
from langdetect import detect, detect_langs, LangDetectException
from app.models import LanguageResult
from app.cache_manager import cache_manager
from app.metrics import metrics_tracker

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Detects the language of user messages with support for 10 Indian languages.
    
    Supported languages:
    - Hindi (hi)
    - English (en)
    - Tamil (ta)
    - Telugu (te)
    - Bengali (bn)
    - Marathi (mr)
    - Gujarati (gu)
    - Kannada (kn)
    - Malayalam (ml)
    - Punjabi (pa)
    """
    
    # Supported languages mapping: code -> full name
    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "hi": "Hindi",
        "en": "English",
        "ta": "Tamil",
        "te": "Telugu",
        "bn": "Bengali",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi"
    }
    
    # Minimum text length for reliable detection
    MIN_TEXT_LENGTH = 3
    
    # Default language when detection fails
    DEFAULT_LANGUAGE = "en"
    DEFAULT_LANGUAGE_NAME = "English"
    
    def __init__(self):
        """Initialize the LanguageDetector"""
        logger.info("LanguageDetector initialized with %d supported languages", 
                   len(self.SUPPORTED_LANGUAGES))
    
    def detect_language(self, text: str) -> LanguageResult:
        """
        Detect the language of input text (with caching).
        
        Args:
            text: User's message text
            
        Returns:
            LanguageResult with detected language code, name, and confidence
            
        Handles edge cases:
        - Very short text: Returns default language (English) with low confidence
        - Mixed languages: Returns the most probable supported language
        - Detection failure: Returns default language (English) with low confidence
        - Unsupported language: Returns default language (English) with low confidence
        """
        # Strip whitespace
        text = text.strip()
        
        # Handle empty text
        if not text:
            logger.warning("Empty text provided for language detection")
            return LanguageResult(
                language_code=self.DEFAULT_LANGUAGE,
                language_name=self.DEFAULT_LANGUAGE_NAME,
                confidence=0.0
            )
        
        # Handle very short text (less than MIN_TEXT_LENGTH characters)
        if len(text) < self.MIN_TEXT_LENGTH:
            logger.info("Text too short for reliable detection (length: %d), defaulting to %s",
                       len(text), self.DEFAULT_LANGUAGE)
            return LanguageResult(
                language_code=self.DEFAULT_LANGUAGE,
                language_name=self.DEFAULT_LANGUAGE_NAME,
                confidence=0.3  # Low confidence for very short text
            )
        
        # Try to get from cache first
        try:
            cached_result = cache_manager.get_cached_language_detection(text)
            if cached_result:
                logger.debug("Language detection cache hit")
                return LanguageResult(**cached_result)
        except Exception as e:
            logger.warning(f"Error retrieving language detection from cache: {e}")
        
        try:
            # Use detect_langs to get probabilities for all detected languages
            detected_langs = detect_langs(text)
            
            # Find the first supported language in the detection results
            for lang_prob in detected_langs:
                lang_code = lang_prob.lang
                confidence = lang_prob.prob
                
                # Check if this is a supported language
                if lang_code in self.SUPPORTED_LANGUAGES:
                    logger.info("Detected language: %s (%s) with confidence: %.2f",
                               lang_code, self.SUPPORTED_LANGUAGES[lang_code], confidence)
                    
                    result = LanguageResult(
                        language_code=lang_code,
                        language_name=self.SUPPORTED_LANGUAGES[lang_code],
                        confidence=confidence
                    )
                    
                    # Track language distribution metric
                    metrics_tracker.track_language(lang_code)
                    
                    # Cache the result
                    try:
                        cache_manager.cache_language_detection(
                            text, lang_code, self.SUPPORTED_LANGUAGES[lang_code], confidence
                        )
                    except Exception as e:
                        logger.warning(f"Error caching language detection: {e}")
                    
                    return result
            
            # If no supported language found, use the highest probability language
            # but return default language with low confidence
            if detected_langs:
                top_lang = detected_langs[0]
                logger.warning(
                    "Detected unsupported language: %s (confidence: %.2f), defaulting to %s",
                    top_lang.lang, top_lang.prob, self.DEFAULT_LANGUAGE
                )
            else:
                logger.warning("No language detected, defaulting to %s", self.DEFAULT_LANGUAGE)
            
            result = LanguageResult(
                language_code=self.DEFAULT_LANGUAGE,
                language_name=self.DEFAULT_LANGUAGE_NAME,
                confidence=0.5  # Medium-low confidence for unsupported language
            )
            
            # Cache the default result
            try:
                cache_manager.cache_language_detection(
                    text, self.DEFAULT_LANGUAGE, self.DEFAULT_LANGUAGE_NAME, 0.5
                )
            except Exception as e:
                logger.warning(f"Error caching language detection: {e}")
            
            return result
            
        except LangDetectException as e:
            # Handle detection errors (e.g., no features in text)
            logger.error("Language detection failed: %s, defaulting to %s", str(e), self.DEFAULT_LANGUAGE)
            return LanguageResult(
                language_code=self.DEFAULT_LANGUAGE,
                language_name=self.DEFAULT_LANGUAGE_NAME,
                confidence=0.0
            )
        except Exception as e:
            # Handle unexpected errors
            logger.error("Unexpected error in language detection: %s, defaulting to %s",
                        str(e), self.DEFAULT_LANGUAGE)
            return LanguageResult(
                language_code=self.DEFAULT_LANGUAGE,
                language_name=self.DEFAULT_LANGUAGE_NAME,
                confidence=0.0
            )
    
    def is_supported_language(self, lang_code: str) -> bool:
        """
        Check if a language code is supported.
        
        Args:
            lang_code: ISO 639-1 language code (e.g., 'hi', 'en', 'ta')
            
        Returns:
            True if the language is supported, False otherwise
        """
        return lang_code.lower() in self.SUPPORTED_LANGUAGES
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get all supported languages.
        
        Returns:
            Dictionary mapping language codes to language names
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    def get_language_name(self, lang_code: str) -> str:
        """
        Get the full name of a language from its code.
        
        Args:
            lang_code: ISO 639-1 language code
            
        Returns:
            Full language name, or empty string if not supported
        """
        return self.SUPPORTED_LANGUAGES.get(lang_code.lower(), "")
