"""Message Processor orchestrator for Y-Connect WhatsApp Bot

Orchestrates the end-to-end message processing pipeline:
SessionManager → LanguageDetector → QueryProcessor → RAGEngine → ResponseGenerator
"""

import logging
from typing import Optional, List
from datetime import datetime

from app.models import (
    IncomingMessage, OutgoingMessage, Message, MessageType,
    IntentType, UserSession, SchemeDocument
)
from app.session_manager import SessionManager
from app.language_detector import LanguageDetector
from app.query_processor import QueryProcessor
from app.rag_engine import RAGEngine
from app.response_generator import ResponseGenerator
from app.whatsapp_client import WhatsAppClient
from app.config import get_settings

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orchestrates the complete message processing pipeline.
    
    Handles:
    - New user welcome messages
    - Help commands
    - Category browsing
    - Scheme detail requests
    - General scheme queries
    """
    
    # Category menu mapping
    CATEGORY_MAP = {
        "1": "agriculture",
        "2": "education",
        "3": "health",
        "4": "housing",
        "5": "women",
        "6": "senior_citizens",
        "7": "employment",
        "8": "financial_inclusion",
        "9": "social_welfare",
        "10": "skill_development"
    }
    
    # Category display names
    CATEGORY_NAMES = {
        "agriculture": "🌾 Agriculture",
        "education": "📚 Education",
        "health": "🏥 Health",
        "housing": "🏠 Housing",
        "women": "👩 Women",
        "senior_citizens": "👴 Senior Citizens",
        "employment": "💼 Employment",
        "financial_inclusion": "💰 Financial Inclusion",
        "social_welfare": "🤝 Social Welfare",
        "skill_development": "🎓 Skill Development"
    }
    
    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        language_detector: Optional[LanguageDetector] = None,
        query_processor: Optional[QueryProcessor] = None,
        rag_engine: Optional[RAGEngine] = None,
        response_generator: Optional[ResponseGenerator] = None,
        whatsapp_client: Optional[WhatsAppClient] = None
    ):
        """
        Initialize MessageProcessor with all required components
        
        Args:
            session_manager: SessionManager instance (creates new if None)
            language_detector: LanguageDetector instance (creates new if None)
            query_processor: QueryProcessor instance (creates new if None)
            rag_engine: RAGEngine instance (creates new if None)
            response_generator: ResponseGenerator instance (creates new if None)
            whatsapp_client: WhatsAppClient instance (creates new if None)
        """
        self.settings = get_settings()
        
        # Initialize components
        self.session_manager = session_manager or SessionManager()
        self.language_detector = language_detector or LanguageDetector()
        self.query_processor = query_processor or QueryProcessor()
        self.rag_engine = rag_engine or RAGEngine()
        self.response_generator = response_generator or ResponseGenerator()
        self.whatsapp_client = whatsapp_client or WhatsAppClient()
        
        logger.info("MessageProcessor initialized with all components")
    
    async def process_incoming_message(
        self,
        incoming_message: IncomingMessage
    ) -> None:
        """
        Process incoming message through the complete pipeline
        
        Args:
            incoming_message: Incoming message from WhatsApp
            
        This method orchestrates:
        1. Session management (get or create session)
        2. Language detection
        3. Special command handling (help, categories, etc.)
        4. Query processing
        5. RAG-based retrieval and generation
        6. Response formatting
        7. Message delivery via WhatsApp
        """
        try:
            # Step 1: Get or create user session
            session = self.session_manager.get_or_create_session(
                incoming_message.from_phone
            )
            
            logger.info(
                f"Processing message for user (is_new_user={session.is_new_user})"
            )
            
            # Step 2: Handle multimedia messages
            if incoming_message.message_type != MessageType.TEXT:
                response_text = self._handle_multimedia_message(
                    incoming_message,
                    session
                )
                await self._send_response(incoming_message.from_phone, response_text)
                return
            
            # Step 3: Detect language
            text = incoming_message.text_content.strip()
            language_result = self.language_detector.detect_language(text)
            
            # Update session language if different
            if session.language != language_result.language_code:
                self.session_manager.update_session_language(
                    incoming_message.from_phone,
                    language_result.language_code
                )
                session.language = language_result.language_code
            
            logger.info(
                f"Detected language: {language_result.language_name} "
                f"(confidence: {language_result.confidence:.2f})"
            )
            
            # Step 4: Handle new user welcome
            if session.is_new_user:
                welcome_message = self.response_generator.create_welcome_message(
                    session.language
                )
                await self._send_response(incoming_message.from_phone, welcome_message)
                
                # Mark user as no longer new
                session.is_new_user = False
                
                # If the message is just a greeting, stop here
                if self._is_greeting(text):
                    # Store the greeting in session
                    user_message = Message(
                        role="user",
                        content=text,
                        language=session.language
                    )
                    self.session_manager.update_session(
                        session.session_id,
                        user_message,
                        welcome_message
                    )
                    return
            
            # Step 5: Check for special commands
            command_response = await self._handle_special_commands(
                text,
                session,
                incoming_message
            )
            
            if command_response:
                # Special command was handled
                user_message = Message(
                    role="user",
                    content=text,
                    language=session.language
                )
                self.session_manager.update_session(
                    session.session_id,
                    user_message,
                    command_response
                )
                await self._send_response(incoming_message.from_phone, command_response)
                return
            
            # Step 6: Process query through main pipeline
            await self._process_query_pipeline(
                text,
                session,
                incoming_message.from_phone
            )
            
        except Exception as e:
            logger.error(
                f"Error processing message: {e}",
                exc_info=True
            )
            # Send error message to user
            error_message = self._get_error_message(session.language if 'session' in locals() else "en")
            await self._send_response(incoming_message.from_phone, error_message)
    
    async def _process_query_pipeline(
        self,
        text: str,
        session: UserSession,
        phone_number: str
    ) -> None:
        """
        Process query through the main RAG pipeline
        
        Args:
            text: User's query text
            session: User session
            phone_number: User's phone number
        """
        # Step 1: Process query to extract intent and entities
        processed_query = self.query_processor.process_query(text, session)
        
        # Update session context with extracted entities
        if processed_query.entities:
            self.session_manager.update_session_context(
                phone_number,
                processed_query.entities
            )
        
        # Step 2: Check if clarification is needed
        if processed_query.needs_clarification:
            clarification_message = "\n\n".join(processed_query.clarification_questions)
            
            # Store in session
            user_message = Message(
                role="user",
                content=text,
                language=session.language
            )
            self.session_manager.update_session(
                session.session_id,
                user_message,
                clarification_message
            )
            
            await self._send_response(phone_number, clarification_message)
            return
        
        # Step 3: Retrieve relevant schemes
        retrieved_schemes = self.rag_engine.retrieve_schemes(processed_query)
        
        logger.info(f"Retrieved {len(retrieved_schemes)} schemes for query")
        
        # Step 4: Generate response using LLM
        generated_response = await self.rag_engine.generate_response(
            processed_query,
            retrieved_schemes,
            session.language
        )
        
        # Step 5: Format response for WhatsApp
        if len(retrieved_schemes) > 1:
            # Multiple schemes - create summary
            response_text = self.response_generator.create_scheme_summary(
                retrieved_schemes,
                session.language
            )
            
            # Store schemes in session context for detail requests
            session.user_context["last_schemes"] = [
                doc.scheme_id for doc in retrieved_schemes[:10]
            ]
            self.session_manager.update_session_context(
                phone_number,
                {"last_schemes": session.user_context["last_schemes"]}
            )
        else:
            # Single scheme or generated response
            response_messages = self.response_generator.format_response(
                generated_response.text,
                retrieved_schemes,
                session.language
            )
            response_text = response_messages[0] if response_messages else generated_response.text
        
        # Step 6: Store in session
        user_message = Message(
            role="user",
            content=text,
            language=session.language
        )
        self.session_manager.update_session(
            session.session_id,
            user_message,
            response_text
        )
        
        # Step 7: Send response
        await self._send_response(phone_number, response_text)
    
    async def _handle_special_commands(
        self,
        text: str,
        session: UserSession,
        incoming_message: IncomingMessage
    ) -> Optional[str]:
        """
        Handle special commands (help, categories, scheme details)
        
        Args:
            text: User's message text
            session: User session
            incoming_message: Incoming message
            
        Returns:
            Response text if command was handled, None otherwise
        """
        text_lower = text.lower().strip()
        
        # Check for help command
        if self._is_help_command(text_lower):
            return self._handle_help_command(session.language)
        
        # Check for category menu request
        if self._is_category_command(text_lower):
            return self._handle_category_menu(session.language)
        
        # Check for category selection
        category = self._is_category_selection(text.strip())
        if category:
            return await self._handle_category_selection(category, session)
        
        # Check for scheme detail request
        scheme_num = self._is_scheme_detail_request(text.strip())
        if scheme_num is not None:
            return await self._handle_scheme_detail_request(scheme_num, session)
        
        return None
    
    def _handle_help_command(self, language: str) -> str:
        """
        Handle help command
        
        Args:
            language: User's language
            
        Returns:
            Help message in user's language
        """
        logger.info("Help command handled")
        return self.response_generator.create_help_message(language)
    
    def _handle_category_menu(self, language: str) -> str:
        """
        Handle category menu request
        
        Args:
            language: User's language
            
        Returns:
            Category menu message
        """
        logger.info("Category menu requested")
        
        # TODO: Localize category names based on language
        menu = "📋 Browse schemes by category:\n\n"
        
        for num, category in self.CATEGORY_MAP.items():
            display_name = self.CATEGORY_NAMES.get(category, category)
            menu += f"{num}. {display_name}\n"
        
        menu += "\nReply with number (1-10) to see schemes in that category."
        
        return menu
    
    async def _handle_category_selection(
        self,
        category: str,
        session: UserSession
    ) -> str:
        """
        Handle category selection
        
        Args:
            category: Selected category name
            session: User session
            
        Returns:
            Response with schemes in selected category
        """
        logger.info(f"Category selected: {category}")
        
        # Create a query for this category
        from app.models import ProcessedQuery
        
        processed_query = ProcessedQuery(
            original_text=f"Show me {category} schemes",
            language=session.language,
            intent=IntentType.CATEGORY_BROWSE,
            entities={"category": category},
            needs_clarification=False,
            clarification_questions=[]
        )
        
        # Retrieve schemes in this category
        retrieved_schemes = self.rag_engine.retrieve_schemes(processed_query, top_k=10)
        
        if not retrieved_schemes:
            return self._get_no_category_results_message(category, session.language)
        
        # Create summary
        return self.response_generator.create_scheme_summary(
            retrieved_schemes,
            session.language
        )
    
    async def _handle_scheme_detail_request(
        self,
        scheme_num: int,
        session: UserSession
    ) -> str:
        """
        Handle scheme detail request
        
        Args:
            scheme_num: Scheme number from summary list (1-10)
            session: User session
            
        Returns:
            Detailed scheme information
        """
        logger.info(f"Scheme detail requested: #{scheme_num}")
        
        # Get last schemes from session context
        last_schemes = session.user_context.get("last_schemes", [])
        
        if not last_schemes or scheme_num > len(last_schemes):
            return self._get_invalid_scheme_number_message(session.language)
        
        # Get scheme ID (scheme_num is 1-indexed)
        scheme_id = last_schemes[scheme_num - 1]
        
        # Retrieve scheme from database
        from app.scheme_repository import SchemeRepository
        scheme_repo = SchemeRepository()
        scheme = scheme_repo.get_scheme_by_id(scheme_id)
        
        if not scheme:
            return self._get_scheme_not_found_message(session.language)
        
        # Format scheme details
        return self.response_generator.format_scheme_details(scheme, session.language)
    
    def _handle_multimedia_message(
        self,
        incoming_message: IncomingMessage,
        session: UserSession
    ) -> str:
        """
        Handle multimedia messages with acknowledgment
        
        Args:
            incoming_message: Incoming multimedia message
            session: User session
            
        Returns:
            Acknowledgment message
        """
        logger.info(f"Multimedia message received: {incoming_message.message_type.value}")
        
        # Acknowledgment messages by type and language
        acknowledgments = {
            "en": {
                MessageType.IMAGE: "📷 Thank you for the image! However, I can only process text messages. Please describe your query in text.",
                MessageType.AUDIO: "🎤 Thank you for the audio! However, I can only process text messages. Please type your query.",
                MessageType.VIDEO: "🎥 Thank you for the video! However, I can only process text messages. Please type your query.",
                MessageType.DOCUMENT: "📄 Thank you for the document! However, I can only process text messages. Please type your query."
            },
            "hi": {
                MessageType.IMAGE: "📷 छवि के लिए धन्यवाद! हालांकि, मैं केवल टेक्स्ट संदेश संसाधित कर सकता हूं। कृपया अपनी क्वेरी टेक्स्ट में वर्णन करें।",
                MessageType.AUDIO: "🎤 ऑडियो के लिए धन्यवाद! हालांकि, मैं केवल टेक्स्ट संदेश संसाधित कर सकता हूं। कृपया अपनी क्वेरी टाइप करें।",
                MessageType.VIDEO: "🎥 वीडियो के लिए धन्यवाद! हालांकि, मैं केवल टेक्स्ट संदेश संसाधित कर सकता हूं। कृपया अपनी क्वेरी टाइप करें।",
                MessageType.DOCUMENT: "📄 दस्तावेज़ के लिए धन्यवाद! हालांकि, मैं केवल टेक्स्ट संदेश संसाधित कर सकता हूं। कृपया अपनी क्वेरी टाइप करें।"
            }
        }
        
        lang_acks = acknowledgments.get(session.language, acknowledgments["en"])
        return lang_acks.get(
            incoming_message.message_type,
            "Thank you for your message! However, I can only process text messages. Please type your query."
        )
    
    async def _send_response(self, phone_number: str, response_text: str) -> None:
        """
        Send response via WhatsApp
        
        Args:
            phone_number: Recipient phone number
            response_text: Response text to send
        """
        try:
            await self.whatsapp_client.send_message(phone_number, response_text)
            logger.info(f"Response sent successfully (length: {len(response_text)})")
        except Exception as e:
            logger.error(f"Error sending response: {e}", exc_info=True)
            raise
    
    def _is_help_command(self, text_lower: str) -> bool:
        """Check if text is a help command"""
        help_keywords = [
            "help", "मदद", "सहायता", "உதவி", "సహాయం", "সাহায্য",
            "मदत", "મદદ", "ಸಹಾಯ", "സഹായം", "ਮਦਦ"
        ]
        return text_lower in help_keywords
    
    def _is_category_command(self, text_lower: str) -> bool:
        """Check if text is a category browsing command"""
        category_keywords = [
            "categories", "category", "श्रेणी", "श्रेणियां", "வகைகள்",
            "వర్గాలు", "বিভাগ", "श्रेण्या", "શ્રેણીઓ", "ವರ್ಗಗಳು",
            "വിഭാഗങ്ങൾ", "ਸ਼੍ਰੇਣੀਆਂ", "menu", "browse"
        ]
        return text_lower in category_keywords
    
    def _is_category_selection(self, text: str) -> Optional[str]:
        """Check if text is a category selection (1-10)"""
        return self.CATEGORY_MAP.get(text)
    
    def _is_scheme_detail_request(self, text: str) -> Optional[int]:
        """Check if text is a scheme detail request"""
        import re
        
        # Try to parse as a number directly
        if text.isdigit():
            num = int(text)
            if 1 <= num <= 10:
                return num
        
        # Try to parse "details N" format
        match = re.match(
            r'^(?:details?|विवरण|விவரங்கள்|వివరాలు|বিবরণ|तपशील|વિગતો|ವಿವರಗಳು|വിശദാംശങ്ങൾ|ਵੇਰਵੇ)\s+(\d+)$',
            text,
            re.IGNORECASE
        )
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                return num
        
        return None
    
    def _is_greeting(self, text: str) -> bool:
        """Check if text is a simple greeting"""
        greetings = [
            "hi", "hello", "hey", "namaste", "नमस्ते", "வணக்கம்",
            "నమస్కారం", "নমস্কার", "नमस्कार", "નમસ્તે", "ನಮಸ್ಕಾರ",
            "നമസ്കാരം", "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "start", "begin"
        ]
        return text.lower().strip() in greetings
    
    def _get_error_message(self, language: str) -> str:
        """Get error message in specified language"""
        messages = {
            "en": "😔 Sorry, I encountered an error processing your request. Please try again or type 'help' for assistance.",
            "hi": "😔 क्षमा करें, आपके अनुरोध को संसाधित करते समय मुझे एक त्रुटि का सामना करना पड़ा। कृपया पुनः प्रयास करें या सहायता के लिए 'help' टाइप करें।"
        }
        return messages.get(language, messages["en"])
    
    def _get_no_category_results_message(self, category: str, language: str) -> str:
        """Get message when no schemes found in category"""
        messages = {
            "en": f"😔 Sorry, I couldn't find any schemes in the {category.replace('_', ' ')} category. Try browsing other categories or ask a specific question.",
            "hi": f"😔 क्षमा करें, मुझे {category.replace('_', ' ')} श्रेणी में कोई योजना नहीं मिली। अन्य श्रेणियों को ब्राउज़ करने का प्रयास करें या कोई विशिष्ट प्रश्न पूछें।"
        }
        return messages.get(language, messages["en"])
    
    def _get_invalid_scheme_number_message(self, language: str) -> str:
        """Get message for invalid scheme number"""
        messages = {
            "en": "😔 Sorry, that scheme number is not valid. Please select a number from the list I sent earlier, or ask a new question.",
            "hi": "😔 क्षमा करें, वह योजना संख्या मान्य नहीं है। कृपया मेरे द्वारा पहले भेजी गई सूची से एक संख्या चुनें, या एक नया प्रश्न पूछें।"
        }
        return messages.get(language, messages["en"])
    
    def _get_scheme_not_found_message(self, language: str) -> str:
        """Get message when scheme not found in database"""
        messages = {
            "en": "😔 Sorry, I couldn't find the details for that scheme. Please try asking a new question or browse categories.",
            "hi": "😔 क्षमा करें, मुझे उस योजना का विवरण नहीं मिला। कृपया एक नया प्रश्न पूछने या श्रेणियों को ब्राउज़ करने का प्रयास करें।"
        }
        return messages.get(language, messages["en"])
    
    async def close(self) -> None:
        """Close all resources"""
        await self.rag_engine.close()
        await self.whatsapp_client.close()
        logger.info("MessageProcessor resources closed")
