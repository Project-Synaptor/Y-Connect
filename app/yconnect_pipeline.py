"""
Y-Connect Pipeline Integration
Simple interface for processing WhatsApp messages through the RAG pipeline
"""

import logging
from typing import Optional
from app.language_detector import LanguageDetector
from app.query_processor import QueryProcessor
from app.rag_engine import RAGEngine
from app.session_manager import SessionManager

logger = logging.getLogger(__name__)


class YConnectPipeline:
    """
    Complete Y-Connect pipeline for processing WhatsApp messages
    
    Handles:
    1. Language detection
    2. Session management
    3. Query processing
    4. RAG retrieval
    5. Response generation
    """
    
    def __init__(self):
        """Initialize all pipeline components"""
        self.language_detector = LanguageDetector()
        self.query_processor = QueryProcessor()
        self.rag_engine = RAGEngine()
        self.session_manager = SessionManager()
        
        logger.info("Initialized YConnectPipeline")
    
    async def process_message(
        self,
        user_message: str,
        phone_number: str
    ) -> str:
        """
        Process incoming WhatsApp message and return response
        
        Args:
            user_message: The text message from user
            phone_number: User's phone number (for session management)
            
        Returns:
            Generated response text ready to send back
        """
        try:
            # 1. Detect language
            language_result = self.language_detector.detect_language(user_message)
            language = language_result.language_code
            
            logger.info(
                f"Processing message from {phone_number[:5]}... in {language}"
            )
            
            # 2. Get or create user session
            session = self.session_manager.get_or_create_session(
                phone_number=phone_number
            )
            
            # 3. Process query (extract intent and entities)
            processed_query = self.query_processor.process_query(
                 user_message,
                 session
)
            
            # 4. Retrieve relevant schemes using RAG
            retrieved_docs = self.rag_engine.retrieve_schemes(
                query=processed_query,
                top_k=5
            )
            
            # 5. Generate response using AWS Bedrock Nova Lite
            generated_response = await self.rag_engine.generate_response(
                query=processed_query,
                retrieved_docs=retrieved_docs,
                language=language
            )
            
            # 6. Update session with new message and response
            from app.models import Message, MessageRole
            
            user_message_obj = Message(
                role=MessageRole.USER,
                content=user_message,
                language=language
            )
            
            self.session_manager.update_session(
                session_id=session.session_id,
                message=user_message_obj,
                response=generated_response.text
            )
            
            # 7. Update user context with extracted entities
            if processed_query.entities:
                self.session_manager.update_session_context(
                    phone_number=phone_number,
                    context_updates=processed_query.entities
                )
            
            logger.info(
                f"Generated response for {phone_number[:5]}... "
                f"({len(generated_response.text)} chars, "
                f"{len(retrieved_docs)} sources)"
            )
            
            return generated_response.text
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Return error message in detected language
            error_messages = {
                "en": "Sorry, I encountered an error processing your request. Please try again.",
                "hi": "क्षमा करें, आपके अनुरोध को संसाधित करने में मुझे एक त्रुटि का सामना करना पड़ा। कृपया पुन: प्रयास करें।",
                "ta": "மன்னிக்கவும், உங்கள் கோரிக்கையை செயலாக்குவதில் பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
                "te": "క్షమించండి, మీ అభ్యర్థనను ప్రాసెస్ చేయడంలో నాకు లోపం ఎదురైంది. దయచేసి మళ్లీ ప్రయత్నించండి.",
                "bn": "দুঃখিত, আপনার অনুরোধ প্রক্রিয়া করতে আমি একটি ত্রুটির সম্মুখীন হয়েছি। অনুগ্রহ করে আবার চেষ্টা করুন।",
                "mr": "क्षमस्व, तुमची विनंती प्रक्रिया करताना मला त्रुटी आली. कृपया पुन्हा प्रयत्न करा.",
                "gu": "માફ કરશો, તમારી વિનંતી પર પ્રક્રિયા કરતી વખતે મને ભૂલ આવી. કૃપા કરીને ફરી પ્રયાસ કરો.",
                "kn": "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಲ್ಲಿ ನಾನು ದೋಷವನ್ನು ಎದುರಿಸಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
                "ml": "ക്ഷമിക്കണം, നിങ്ങളുടെ അഭ്യർത്ഥന പ്രോസസ്സ് ചെയ്യുന്നതിൽ എനിക്ക് പിശക് നേരിട്ടു. ദയവായി വീണ്ടും ശ്രമിക്കുക.",
                "pa": "ਮਾਫ਼ ਕਰਨਾ, ਤੁਹਾਡੀ ਬੇਨਤੀ ਦੀ ਪ੍ਰਕਿਰਿਆ ਕਰਨ ਵਿੱਚ ਮੈਨੂੰ ਇੱਕ ਗਲਤੀ ਦਾ ਸਾਹਮਣਾ ਕਰਨਾ ਪਿਆ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।"
            }
            
            # Try to detect language for error message
            try:
                lang_result = self.language_detector.detect_language(user_message)
                return error_messages.get(lang_result.language_code, error_messages["en"])
            except:
                return error_messages["en"]
    
    async def close(self):
        """Cleanup resources"""
        await self.rag_engine.close()
        logger.info("Closed YConnectPipeline")


# Global pipeline instance (singleton pattern)
_pipeline_instance: Optional[YConnectPipeline] = None


def get_pipeline() -> YConnectPipeline:
    """
    Get or create the global pipeline instance
    
    Returns:
        YConnectPipeline instance
    """
    global _pipeline_instance
    
    if _pipeline_instance is None:
        _pipeline_instance = YConnectPipeline()
    
    return _pipeline_instance


async def process_whatsapp_message(user_message: str, phone_number: str) -> str:
    """
    Simple function to process WhatsApp message through Y-Connect pipeline
    
    Args:
        user_message: The incoming WhatsApp message text
        phone_number: User's phone number in international format
        
    Returns:
        Response text to send back to user
        
    Example:
        >>> response = await process_whatsapp_message(
        ...     "मुझे किसान योजनाएं दिखाओ",
        ...     "+919876543210"
        ... )
        >>> print(response)
        "यहाँ किसानों के लिए योजनाएं हैं: 1. PM-KISAN..."
    """
    pipeline = get_pipeline()
    return await pipeline.process_message(user_message, phone_number)
