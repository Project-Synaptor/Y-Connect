"""Fallback handlers for error scenarios in Y-Connect WhatsApp Bot"""

from typing import Optional, List, Dict, Any
from app.logging_config import get_logger
from app.models import ProcessedQuery, SchemeDocument, LanguageResult

logger = get_logger(__name__)


class FallbackHandlers:
    """Provides fallback mechanisms for various component failures"""
    
    @staticmethod
    def language_detection_fallback(text: str) -> LanguageResult:
        """
        Fallback for language detection failure - default to English
        
        Args:
            text: User's message text
            
        Returns:
            LanguageResult with English as default language
            
        Validates: Requirements 9.1
        """
        logger.warning(
            "Language detection failed, falling back to English",
            extra={"text_length": len(text)}
        )
        
        return LanguageResult(
            language_code="en",
            language_name="English",
            confidence=0.5  # Low confidence to indicate fallback
        )
    
    @staticmethod
    def intent_extraction_fallback(
        text: str,
        language: str = "en"
    ) -> str:
        """
        Fallback for intent extraction failure - ask user to rephrase
        
        Args:
            text: User's message text
            language: Detected language code
            
        Returns:
            Message asking user to rephrase with examples
            
        Validates: Requirements 9.2
        """
        logger.warning(
            "Intent extraction failed, asking user to rephrase",
            extra={"text_length": len(text), "language": language}
        )
        
        # Localized rephrase messages with examples
        rephrase_messages = {
            "en": (
                "I couldn't understand your query. Could you please rephrase it?\n\n"
                "Try asking like:\n"
                "• 'Show me farmer schemes'\n"
                "• 'Education help for students'\n"
                "• 'Health schemes for women'\n"
                "• 'Housing schemes in Punjab'\n\n"
                "Or type 'categories' to browse all schemes."
            ),
            "hi": (
                "मैं आपके प्रश्न को समझ नहीं सका। क्या आप इसे दोबारा बता सकते हैं?\n\n"
                "इस तरह पूछने का प्रयास करें:\n"
                "• 'किसान योजनाएं दिखाएं'\n"
                "• 'छात्रों के लिए शिक्षा सहायता'\n"
                "• 'महिलाओं के लिए स्वास्थ्य योजनाएं'\n"
                "• 'पंजाब में आवास योजनाएं'\n\n"
                "या सभी योजनाओं को देखने के लिए 'श्रेणियां' टाइप करें।"
            ),
            "ta": (
                "உங்கள் கேள்வியைப் புரிந்து கொள்ள முடியவில்லை. தயவுசெய்து மீண்டும் சொல்ல முடியுமா?\n\n"
                "இப்படி கேட்க முயற்சிக்கவும்:\n"
                "• 'விவசாயி திட்டங்களைக் காட்டு'\n"
                "• 'மாணவர்களுக்கு கல்வி உதவி'\n"
                "• 'பெண்களுக்கான சுகாதார திட்டங்கள்'\n"
                "• 'பஞ்சாபில் வீட்டுத் திட்டங்கள்'\n\n"
                "அல்லது அனைத்து திட்டங்களையும் பார்க்க 'வகைகள்' என தட்டச்சு செய்யவும்."
            ),
        }
        
        # Return localized message or English fallback
        return rephrase_messages.get(language, rephrase_messages["en"])
    
    @staticmethod
    def rag_retrieval_fallback(
        query: ProcessedQuery,
        scheme_database: Optional[Any] = None
    ) -> List[SchemeDocument]:
        """
        Fallback for RAG retrieval failure - use keyword-based search
        
        Args:
            query: Processed query with entities
            scheme_database: Database connection for keyword search
            
        Returns:
            List of schemes from keyword search (may be empty)
            
        Validates: Requirements 9.3
        """
        logger.warning(
            "Vector store retrieval failed, attempting keyword-based fallback",
            extra={
                "query_text": query.original_text[:100],
                "language": query.language
            }
        )
        
        # If no database connection, return empty list
        if not scheme_database:
            logger.error("No database connection available for keyword fallback")
            return []
        
        try:
            # Extract keywords from query
            keywords = FallbackHandlers._extract_keywords(query)
            
            # Perform keyword-based search in database
            # This would use PostgreSQL full-text search or LIKE queries
            # For now, return empty list as placeholder
            logger.info(
                "Keyword-based search attempted",
                extra={"keywords": keywords}
            )
            
            # TODO: Implement actual keyword search when database is available
            return []
            
        except Exception as e:
            logger.error(
                "Keyword-based fallback also failed",
                extra={"error": str(e)},
                exc_info=True
            )
            return []
    
    @staticmethod
    def _extract_keywords(query: ProcessedQuery) -> List[str]:
        """
        Extract keywords from query for fallback search
        
        Args:
            query: Processed query
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Add entities as keywords
        if query.entities:
            for key, value in query.entities.items():
                if value and isinstance(value, str):
                    keywords.append(value.lower())
        
        # Add words from original text (filter out common words)
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "i", "me", "my", "we", "you", "he", "she", "it", "they", "am", "is", "are"
        }
        
        words = query.original_text.lower().split()
        for word in words:
            # Remove punctuation
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word and clean_word not in common_words and len(clean_word) > 2:
                keywords.append(clean_word)
        
        return keywords[:10]  # Limit to top 10 keywords
    
    @staticmethod
    def llm_generation_fallback(
        retrieved_schemes: List[SchemeDocument],
        language: str = "en"
    ) -> str:
        """
        Fallback for LLM generation failure - use pre-formatted responses
        
        Args:
            retrieved_schemes: Schemes retrieved from vector store
            language: Target language for response
            
        Returns:
            Pre-formatted response without LLM generation
            
        Validates: Requirements 9.3
        """
        logger.warning(
            "LLM generation failed, using pre-formatted response",
            extra={
                "num_schemes": len(retrieved_schemes),
                "language": language
            }
        )
        
        # If no schemes retrieved, return "no results" message
        if not retrieved_schemes:
            return FallbackHandlers._no_results_message(language)
        
        # If one scheme, return formatted details
        if len(retrieved_schemes) == 1:
            return FallbackHandlers._format_single_scheme(retrieved_schemes[0], language)
        
        # If multiple schemes, return summary list
        return FallbackHandlers._format_scheme_list(retrieved_schemes, language)
    
    @staticmethod
    def _no_results_message(language: str) -> str:
        """Generate 'no results found' message in specified language"""
        messages = {
            "en": (
                "I couldn't find any schemes matching your query.\n\n"
                "Try:\n"
                "• Being more specific about your needs\n"
                "• Browsing by category (type 'categories')\n"
                "• Asking about a different topic\n\n"
                "Type 'help' for more guidance."
            ),
            "hi": (
                "मुझे आपके प्रश्न से मेल खाने वाली कोई योजना नहीं मिली।\n\n"
                "प्रयास करें:\n"
                "• अपनी आवश्यकताओं के बारे में अधिक विशिष्ट रहें\n"
                "• श्रेणी के अनुसार ब्राउज़ करें ('श्रेणियां' टाइप करें)\n"
                "• किसी अन्य विषय के बारे में पूछें\n\n"
                "अधिक मार्गदर्शन के लिए 'मदद' टाइप करें।"
            ),
            "ta": (
                "உங்கள் கேள்விக்கு பொருந்தும் திட்டங்கள் எதுவும் கிடைக்கவில்லை.\n\n"
                "முயற்சிக்கவும்:\n"
                "• உங்கள் தேவைகளைப் பற்றி மேலும் குறிப்பிட்டு சொல்லுங்கள்\n"
                "• வகை வாரியாக உலாவவும் ('வகைகள்' என தட்டச்சு செய்யவும்)\n"
                "• வேறு தலைப்பைப் பற்றி கேளுங்கள்\n\n"
                "மேலும் வழிகாட்டுதலுக்கு 'உதவி' என தட்டச்சு செய்யவும்."
            ),
        }
        
        return messages.get(language, messages["en"])
    
    @staticmethod
    def _format_single_scheme(scheme: SchemeDocument, language: str) -> str:
        """Format a single scheme without LLM generation"""
        # Get scheme details
        scheme_obj = scheme.scheme
        
        # Build response sections
        sections = []
        
        # Title
        sections.append(f"📋 {scheme_obj.scheme_name}\n")
        
        # Description
        if scheme_obj.description:
            sections.append(f"{scheme_obj.description[:200]}...\n")
        
        # Category
        if scheme_obj.category:
            sections.append(f"📂 Category: {scheme_obj.category.replace('_', ' ').title()}\n")
        
        # Authority
        if scheme_obj.authority:
            sections.append(f"🏛️ Authority: {scheme_obj.authority.replace('_', ' ').title()}\n")
        
        # Official link
        if scheme_obj.official_url:
            sections.append(f"🔗 More info: {scheme_obj.official_url}\n")
        
        # Helpline
        if scheme_obj.helpline_numbers:
            sections.append(f"📞 Helpline: {', '.join(scheme_obj.helpline_numbers)}\n")
        
        # Note about pre-formatted response
        note = {
            "en": "\n💡 For detailed information, please visit the official website.",
            "hi": "\n💡 विस्तृत जानकारी के लिए, कृपया आधिकारिक वेबसाइट पर जाएं।",
            "ta": "\n💡 விரிவான தகவலுக்கு, தயவுசெய்து அதிகாரப்பூர்வ இணையதளத்தைப் பார்வையிடவும்.",
        }
        sections.append(note.get(language, note["en"]))
        
        return "\n".join(sections)
    
    @staticmethod
    def _format_scheme_list(schemes: List[SchemeDocument], language: str) -> str:
        """Format multiple schemes as a list without LLM generation"""
        # Header
        headers = {
            "en": f"Found {len(schemes)} schemes:\n\n",
            "hi": f"{len(schemes)} योजनाएं मिलीं:\n\n",
            "ta": f"{len(schemes)} திட்டங்கள் கிடைத்தன:\n\n",
        }
        
        response = headers.get(language, headers["en"])
        
        # List schemes (max 5)
        for i, scheme in enumerate(schemes[:5], 1):
            scheme_obj = scheme.scheme
            response += f"{i}. {scheme_obj.scheme_name}\n"
            
            # Add brief description if available
            if scheme_obj.description:
                brief = scheme_obj.description[:80]
                response += f"   {brief}...\n"
            
            response += "\n"
        
        # Footer
        footers = {
            "en": "Reply with a number (1-5) for full details.\n\n💡 For best results, try again later when our AI is available.",
            "hi": "पूर्ण विवरण के लिए संख्या (1-5) के साथ उत्तर दें।\n\n💡 सर्वोत्तम परिणामों के लिए, जब हमारा AI उपलब्ध हो तो बाद में पुनः प्रयास करें।",
            "ta": "முழு விவரங்களுக்கு எண் (1-5) உடன் பதிலளிக்கவும்.\n\n💡 சிறந்த முடிவுகளுக்கு, எங்கள் AI கிடைக்கும் போது பின்னர் மீண்டும் முயற்சிக்கவும்.",
        }
        
        response += footers.get(language, footers["en"])
        
        return response
    
    @staticmethod
    def get_fallback_response(
        error_type: str,
        language: str = "en",
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get appropriate fallback response based on error type
        
        Args:
            error_type: Type of error (language_detection, query_processing, retrieval, generation, api)
            language: Language for response
            context: Additional context (e.g., retrieved schemes, query text)
            
        Returns:
            Fallback response message
        """
        if error_type == "language_detection":
            return FallbackHandlers.intent_extraction_fallback("", language)
        
        elif error_type == "query_processing":
            text = context.get("text", "") if context else ""
            return FallbackHandlers.intent_extraction_fallback(text, language)
        
        elif error_type == "retrieval":
            return FallbackHandlers._no_results_message(language)
        
        elif error_type == "generation":
            schemes = context.get("schemes", []) if context else []
            return FallbackHandlers.llm_generation_fallback(schemes, language)
        
        else:
            # Generic fallback
            messages = {
                "en": "Something went wrong. Please try again later or type 'help' for assistance.",
                "hi": "कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें या सहायता के लिए 'मदद' टाइप करें।",
                "ta": "ஏதோ தவறு நடந்தது. பிறகு மீண்டும் முயற்சிக்கவும் அல்லது உதவிக்கு 'உதவி' என தட்டச்சு செய்யவும்.",
            }
            return messages.get(language, messages["en"])
