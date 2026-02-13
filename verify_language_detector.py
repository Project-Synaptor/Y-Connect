"""Verification script for LanguageDetector component"""

from app.language_detector import LanguageDetector


def main():
    """Demonstrate LanguageDetector functionality"""
    detector = LanguageDetector()
    
    print("=" * 60)
    print("Y-Connect Language Detector Verification")
    print("=" * 60)
    print()
    
    # Test cases in different languages
    test_cases = [
        ("Hello, I need help with government schemes", "English"),
        ("नमस्ते, मुझे सरकारी योजनाओं की जानकारी चाहिए", "Hindi"),
        ("வணக்கம், எனக்கு அரசு திட்டங்கள் தேவை", "Tamil"),
        ("నమస్కారం, నాకు ప్రభుత్వ పథకాలు కావాలి", "Telugu"),
        ("নমস্কার, আমার সরকারি প্রকল্প দরকার", "Bengali"),
        ("नमस्कार, मला सरकारी योजना हवी आहे", "Marathi"),
        ("નમસ્તે, મને સરકારી યોજનાઓ જોઈએ છે", "Gujarati"),
        ("ನಮಸ್ಕಾರ, ನನಗೆ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಬೇಕು", "Kannada"),
        ("ഹലോ, എനിക്ക് സർക്കാർ പദ്ധതികൾ വേണം", "Malayalam"),
        ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਨੂੰ ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਚਾਹੀਦੀਆਂ ਹਨ", "Punjabi"),
    ]
    
    print("Testing language detection for 10 Indian languages:")
    print()
    
    for text, expected_lang in test_cases:
        result = detector.detect_language(text)
        print(f"Text: {text[:50]}...")
        print(f"Expected: {expected_lang}")
        print(f"Detected: {result.language_name} ({result.language_code})")
        print(f"Confidence: {result.confidence:.2f}")
        print("-" * 60)
    
    print()
    print("Testing edge cases:")
    print()
    
    # Edge cases
    edge_cases = [
        ("", "Empty text"),
        ("hi", "Very short text"),
        ("   ", "Whitespace only"),
        ("123456", "Numbers only"),
        ("Hello नमस्ते", "Mixed languages"),
    ]
    
    for text, description in edge_cases:
        result = detector.detect_language(text)
        print(f"Case: {description}")
        print(f"Text: '{text}'")
        print(f"Detected: {result.language_name} ({result.language_code})")
        print(f"Confidence: {result.confidence:.2f}")
        print("-" * 60)
    
    print()
    print("Supported languages:")
    for code, name in sorted(detector.get_supported_languages().items()):
        print(f"  {code}: {name}")
    
    print()
    print("=" * 60)
    print("Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
