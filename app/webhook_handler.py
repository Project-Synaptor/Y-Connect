"""Webhook handler for WhatsApp Business API integration"""

import hmac
import hashlib
import time
import uuid
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logging_config import get_logger
from app.models import IncomingMessage, MessageType
from app.load_monitor import LoadMonitor
from app.message_queue import MessageQueue, QueuedMessage

logger = get_logger(__name__)


class WebhookVerification(BaseModel):
    """Model for webhook verification request"""
    mode: str = Field(..., alias="hub.mode")
    token: str = Field(..., alias="hub.verify_token")
    challenge: str = Field(..., alias="hub.challenge")


class WebhookHandler:
    """Handles WhatsApp webhook events and verification"""
    
    def __init__(self):
        """Initialize webhook handler with settings"""
        self.settings = get_settings()
        self.verify_token = self.settings.whatsapp_verify_token
        self.app_secret = self.settings.whatsapp_app_secret
        
        # Initialize load monitoring and queue management
        try:
            self.load_monitor = LoadMonitor()
            self.message_queue = MessageQueue()
        except Exception as e:
            logger.error(f"Failed to initialize load monitoring/queue: {e}")
            # Set to None to handle gracefully
            self.load_monitor = None
            self.message_queue = None
        
    def verify_webhook(self, mode: str, token: str, challenge: str) -> str:
        """
        Verify webhook during initial setup
        
        Args:
            mode: Verification mode (should be "subscribe")
            token: Verification token from WhatsApp
            challenge: Challenge string to echo back
            
        Returns:
            Challenge string if verification succeeds
            
        Raises:
            HTTPException: If verification fails
        """
        logger.info(
            "Webhook verification request received",
            extra={"mode": mode, "token_match": token == self.verify_token}
        )
        
        # Verify mode and token
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verification successful")
            return challenge
        
        logger.warning(
            "Webhook verification failed",
            extra={"mode": mode, "expected_mode": "subscribe"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook verification failed"
        )
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using app secret
        
        Args:
            payload: Raw request body bytes
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            logger.warning("No signature provided in webhook request")
            return False
        
        # Signature format: sha256=<hash>
        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format", extra={"signature": signature})
            return False
        
        # Extract hash from signature
        expected_hash = signature[7:]  # Remove "sha256=" prefix
        
        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            self.app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare hashes
        is_valid = hmac.compare_digest(computed_hash, expected_hash)
        
        if not is_valid:
            logger.warning(
                "Signature verification failed",
                extra={
                    "expected_hash": expected_hash[:10] + "...",
                    "computed_hash": computed_hash[:10] + "..."
                }
            )
        
        return is_valid
    
    def extract_message(self, webhook_payload: Dict[str, Any]) -> Optional[IncomingMessage]:
        """
        Extract message content and sender info from webhook payload
        
        Args:
            webhook_payload: Raw webhook data from WhatsApp API
            
        Returns:
            IncomingMessage object or None if not a message event
        """
        try:
            # WhatsApp webhook structure:
            # {
            #   "object": "whatsapp_business_account",
            #   "entry": [{
            #     "id": "...",
            #     "changes": [{
            #       "value": {
            #         "messaging_product": "whatsapp",
            #         "metadata": {...},
            #         "contacts": [{...}],
            #         "messages": [{
            #           "from": "1234567890",
            #           "id": "wamid.xxx",
            #           "timestamp": "1234567890",
            #           "type": "text",
            #           "text": {"body": "Hello"}
            #         }]
            #       },
            #       "field": "messages"
            #     }]
            #   }]
            # }
            
            # Validate object type
            if webhook_payload.get("object") != "whatsapp_business_account":
                logger.debug(
                    "Webhook payload is not for WhatsApp Business Account",
                    extra={"object": webhook_payload.get("object")}
                )
                return None
            
            # Extract entry
            entries = webhook_payload.get("entry", [])
            if not entries:
                logger.debug("No entries in webhook payload")
                return None
            
            # Get first entry
            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                logger.debug("No changes in webhook entry")
                return None
            
            # Get first change
            change = changes[0]
            value = change.get("value", {})
            
            # Extract messages
            messages = value.get("messages", [])
            if not messages:
                logger.debug("No messages in webhook change")
                return None
            
            # Get first message
            message_data = messages[0]
            
            # Extract message fields
            message_id = message_data.get("id")
            from_phone = message_data.get("from")
            timestamp_str = message_data.get("timestamp")
            message_type_str = message_data.get("type", "text")
            
            # Validate required fields
            if not message_id or not from_phone:
                logger.warning(
                    "Missing required fields in message",
                    extra={"message_id": message_id, "from_phone": from_phone}
                )
                return None
            
            # Add + prefix to phone number if not present
            if not from_phone.startswith("+"):
                from_phone = f"+{from_phone}"
            
            # Parse timestamp
            from datetime import datetime
            if timestamp_str:
                timestamp = datetime.fromtimestamp(int(timestamp_str))
            else:
                timestamp = datetime.utcnow()
            
            # Map message type
            message_type = self._map_message_type(message_type_str)
            
            # Extract content based on type
            text_content = ""
            media_url = None
            
            if message_type == MessageType.TEXT:
                text_data = message_data.get("text", {})
                text_content = text_data.get("body", "")
            elif message_type in [MessageType.IMAGE, MessageType.AUDIO, MessageType.VIDEO, MessageType.DOCUMENT]:
                # Extract media URL from respective field
                media_data = message_data.get(message_type_str, {})
                media_url = media_data.get("url") or media_data.get("link")
            
            # Create IncomingMessage
            incoming_message = IncomingMessage(
                message_id=message_id,
                from_phone=from_phone,
                timestamp=timestamp,
                message_type=message_type,
                text_content=text_content,
                media_url=media_url
            )
            
            logger.info(
                "Message extracted from webhook",
                extra={
                    "message_id": message_id,
                    "from_phone": self._anonymize_phone(from_phone),
                    "message_type": message_type.value
                }
            )
            
            return incoming_message
            
        except Exception as e:
            logger.error(
                "Error extracting message from webhook payload",
                extra={"error": str(e)},
                exc_info=True
            )
            return None
    
    def _map_message_type(self, whatsapp_type: str) -> MessageType:
        """
        Map WhatsApp message type to internal MessageType enum
        
        Args:
            whatsapp_type: Message type from WhatsApp API
            
        Returns:
            MessageType enum value
        """
        type_mapping = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "audio": MessageType.AUDIO,
            "video": MessageType.VIDEO,
            "document": MessageType.DOCUMENT,
        }
        return type_mapping.get(whatsapp_type.lower(), MessageType.TEXT)
    
    def _anonymize_phone(self, phone: str) -> str:
        """
        Anonymize phone number for logging
        
        Args:
            phone: Phone number to anonymize
            
        Returns:
            Anonymized phone number (shows only last 4 digits)
        """
        if len(phone) > 4:
            return f"***{phone[-4:]}"
        return "****"
    
    def _is_help_command(self, text: str) -> bool:
        """
        Check if message is a help command in any supported language
        
        Args:
            text: Message text to check
            
        Returns:
            True if message is a help command
        """
        text_lower = text.lower().strip()
        
        # Help keywords in different languages
        help_keywords = [
            "help", "मदद", "सहायता", "உதவி", "సహాయం", "সাহায্য",
            "मदत", "મદદ", "ಸಹಾಯ", "സഹായം", "ਮਦਦ"
        ]
        
        return text_lower in help_keywords
    
    def _is_category_command(self, text: str) -> bool:
        """
        Check if message is a category browsing command
        
        Args:
            text: Message text to check
            
        Returns:
            True if message is a category command
        """
        text_lower = text.lower().strip()
        
        # Category keywords in different languages
        category_keywords = [
            "categories", "category", "श्रेणी", "श्रेणियां", "வகைகள்",
            "వర్గాలు", "বিভাগ", "श्रेण्या", "શ્રેણીઓ", "ವರ್ಗಗಳು",
            "വിഭാഗങ്ങൾ", "ਸ਼੍ਰੇਣੀਆਂ"
        ]
        
        return text_lower in category_keywords
    
    def _is_category_selection(self, text: str) -> Optional[str]:
        """
        Check if message is a category selection (e.g., "1" for agriculture)
        
        Args:
            text: Message text to check
            
        Returns:
            Category name if valid selection, None otherwise
        """
        text_stripped = text.strip()
        
        # Category mapping (number to category)
        category_map = {
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
        
        return category_map.get(text_stripped)
    
    def _is_scheme_detail_request(self, text: str) -> Optional[int]:
        """
        Check if message is a scheme detail request (e.g., "details 2" or just "2")
        
        Args:
            text: Message text to check
            
        Returns:
            Scheme number if valid request, None otherwise
        """
        text_stripped = text.strip()
        
        # Try to parse as a number directly
        if text_stripped.isdigit():
            num = int(text_stripped)
            if 1 <= num <= 10:  # Valid scheme numbers from summary list
                return num
        
        # Try to parse "details N" format
        import re
        match = re.match(r'^(?:details?|विवरण|விவரங்கள்|వివరాలు|বিবরণ|तपशील|વિગતો|ವಿವರಗಳು|വിശദാംശങ്ങൾ|ਵੇਰਵੇ)\s+(\d+)$', text_stripped, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 10:
                return num
        
        return None
    
    async def route_message(self, incoming_message: IncomingMessage) -> str:
        """
        Route message to appropriate handler based on type and content
        
        Args:
            incoming_message: Incoming message to route
            
        Returns:
            Response text to send back to user
        """
        # Handle multimedia messages
        if incoming_message.message_type != MessageType.TEXT:
            return self._handle_multimedia_message(incoming_message)
        
        # Get text content
        text = incoming_message.text_content.strip()
        
        # Check for help command
        if self._is_help_command(text):
            return self._handle_help_command(incoming_message)
        
        # Check for category browsing
        if self._is_category_command(text):
            return self._handle_category_menu(incoming_message)
        
        # Check for category selection
        category = self._is_category_selection(text)
        if category:
            return self._handle_category_selection(incoming_message, category)
        
        # Check for scheme detail request
        scheme_num = self._is_scheme_detail_request(text)
        if scheme_num is not None:
            return self._handle_scheme_detail_request(incoming_message, scheme_num)
        
        # Default: route to main processing pipeline
        return await self._handle_text_message(incoming_message)
    
    def _handle_multimedia_message(self, incoming_message: IncomingMessage) -> str:
        """
        Handle multimedia messages with acknowledgment
        
        Args:
            incoming_message: Incoming multimedia message
            
        Returns:
            Acknowledgment message in English (default)
        """
        logger.info(
            "Multimedia message received",
            extra={
                "message_type": incoming_message.message_type.value,
                "from_phone": self._anonymize_phone(incoming_message.from_phone)
            }
        )
        
        # Acknowledgment messages by type
        acknowledgments = {
            MessageType.IMAGE: "📷 Thank you for the image! However, I can only process text messages. Please describe your query in text.",
            MessageType.AUDIO: "🎤 Thank you for the audio! However, I can only process text messages. Please type your query.",
            MessageType.VIDEO: "🎥 Thank you for the video! However, I can only process text messages. Please type your query.",
            MessageType.DOCUMENT: "📄 Thank you for the document! However, I can only process text messages. Please type your query."
        }
        
        return acknowledgments.get(
            incoming_message.message_type,
            "Thank you for your message! However, I can only process text messages. Please type your query."
        )
    
    def _handle_help_command(self, incoming_message: IncomingMessage) -> str:
        """
        Handle help command
        
        Args:
            incoming_message: Incoming message with help command
            
        Returns:
            Help message (will use ResponseGenerator in future)
        """
        logger.info(
            "Help command received",
            extra={"from_phone": self._anonymize_phone(incoming_message.from_phone)}
        )
        
        # TODO: Use ResponseGenerator.create_help_message() with detected language
        # For now, return English help message
        return (
            "📚 How to use Y-Connect:\n\n"
            "1️⃣ Ask about schemes:\n"
            "   \"Show me farmer schemes\"\n"
            "   \"Education help for students\"\n\n"
            "2️⃣ Provide your details:\n"
            "   \"I am a farmer in Punjab\"\n"
            "   \"I am 65 years old\"\n\n"
            "3️⃣ Browse by category:\n"
            "   Type 'categories' to see all\n\n"
            "4️⃣ Get scheme details:\n"
            "   Reply with number from list\n\n"
            "💡 Tip: The more details you share, the better I can help!\n\n"
            "Type 'categories' to browse schemes."
        )
    
    def _handle_category_menu(self, incoming_message: IncomingMessage) -> str:
        """
        Handle category menu request
        
        Args:
            incoming_message: Incoming message requesting category menu
            
        Returns:
            Category menu message
        """
        logger.info(
            "Category menu requested",
            extra={"from_phone": self._anonymize_phone(incoming_message.from_phone)}
        )
        
        # TODO: Localize based on detected language
        return (
            "📋 Browse schemes by category:\n\n"
            "1. 🌾 Agriculture\n"
            "2. 📚 Education\n"
            "3. 🏥 Health\n"
            "4. 🏠 Housing\n"
            "5. 👩 Women\n"
            "6. 👴 Senior Citizens\n"
            "7. 💼 Employment\n"
            "8. 💰 Financial Inclusion\n"
            "9. 🤝 Social Welfare\n"
            "10. 🎓 Skill Development\n\n"
            "Reply with number (1-10) to see schemes in that category."
        )
    
    def _handle_category_selection(self, incoming_message: IncomingMessage, category: str) -> str:
        """
        Handle category selection
        
        Args:
            incoming_message: Incoming message with category selection
            category: Selected category name
            
        Returns:
            Response message (placeholder for now)
        """
        logger.info(
            "Category selected",
            extra={
                "from_phone": self._anonymize_phone(incoming_message.from_phone),
                "category": category
            }
        )
        
        # TODO: Integrate with RAG engine to retrieve schemes by category
        return (
            f"You selected: {category.replace('_', ' ').title()}\n\n"
            "This feature will retrieve schemes from this category. "
            "Integration with RAG engine coming soon!"
        )
    
    def _handle_scheme_detail_request(self, incoming_message: IncomingMessage, scheme_num: int) -> str:
        """
        Handle scheme detail request
        
        Args:
            incoming_message: Incoming message with scheme detail request
            scheme_num: Scheme number from summary list
            
        Returns:
            Response message (placeholder for now)
        """
        logger.info(
            "Scheme detail requested",
            extra={
                "from_phone": self._anonymize_phone(incoming_message.from_phone),
                "scheme_number": scheme_num
            }
        )
        
        # TODO: Retrieve scheme details from session context and format response
        return (
            f"You requested details for scheme #{scheme_num}\n\n"
            "This feature will show full scheme details. "
            "Integration with session manager and response generator coming soon!"
        )
    
    async def _handle_text_message(self, incoming_message: IncomingMessage) -> str:
        """
        Handle regular text message through main processing pipeline
        
        Args:
            incoming_message: Incoming text message
            
        Returns:
            Response message (placeholder for now)
        """
        logger.info(
            "Text message routed to main pipeline",
            extra={
                "from_phone": self._anonymize_phone(incoming_message.from_phone),
                "text_length": len(incoming_message.text_content)
            }
        )
        
        # TODO: Integrate with full processing pipeline:
        # 1. SessionManager.get_or_create_session()
        # 2. LanguageDetector.detect_language()
        # 3. QueryProcessor.process_query()
        # 4. RAGEngine.retrieve_schemes() and generate_response()
        # 5. ResponseGenerator.format_response()
        # 6. WhatsAppClient.send_message()
        
        return (
            "Thank you for your message! I'm processing your query.\n\n"
            "Full integration with language detection, query processing, "
            "and RAG engine coming soon!"
        )
    
    async def handle_message(self, webhook_payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Process incoming WhatsApp webhook events
        
        Args:
            webhook_payload: Raw webhook data from WhatsApp API
            
        Returns:
            HTTP 200 response to acknowledge receipt
        """
        logger.info("Webhook message received")
        
        # Extract message from payload
        incoming_message = self.extract_message(webhook_payload)
        
        if not incoming_message:
            logger.debug("No valid message found in webhook payload")
            return {"status": "ok", "message": "No message to process"}
        
        # Log message receipt
        logger.info(
            "Processing incoming message",
            extra={
                "message_id": incoming_message.message_id,
                "from_phone": self._anonymize_phone(incoming_message.from_phone),
                "message_type": incoming_message.message_type.value
            }
        )
        
        # Check system load and queue if overloaded
        if self.load_monitor and self.message_queue:
            # Increment active requests
            self.load_monitor.increment_active_requests()
            start_time = time.time()
            
            try:
                # Check if system is overloaded
                if self.load_monitor.is_overloaded():
                    # Queue the message
                    queued_msg = QueuedMessage(
                        message_id=incoming_message.message_id,
                        phone_number=incoming_message.from_phone,
                        message_text=incoming_message.text_content or "",
                        language="en",  # Will be detected when processed
                        queued_at=time.time()
                    )
                    
                    if self.message_queue.queue_message(queued_msg):
                        # Get estimated wait time
                        wait_time = self.message_queue.get_estimated_wait_time()
                        
                        # Send wait time notification
                        wait_msg = self.load_monitor.get_wait_time_message(
                            wait_time,
                            language="en"  # Default to English, will improve with language detection
                        )
                        
                        logger.info(
                            "Message queued due to overload",
                            extra={
                                "message_id": incoming_message.message_id,
                                "queue_depth": self.message_queue.get_queue_depth(),
                                "estimated_wait": wait_time
                            }
                        )
                        
                        # Send wait notification to user
                        try:
                            from app.whatsapp_client import WhatsAppClient
                            whatsapp_client = WhatsAppClient()
                            whatsapp_client.send_message(
                                to_phone=incoming_message.from_phone,
                                text_content=wait_msg
                            )
                        except Exception as e:
                            logger.error(f"Failed to send wait notification: {e}")
                        
                        return {
                            "status": "queued",
                            "message": "Message queued due to high load"
                        }
                
                # Process message normally
                response_text = await self.route_message(incoming_message)
                
                # Record response time
                response_time = time.time() - start_time
                self.load_monitor.record_response_time(response_time)
                
                logger.info(
                    "Message routed successfully",
                    extra={
                        "message_id": incoming_message.message_id,
                        "response_length": len(response_text),
                        "response_time": response_time
                    }
                )
                
                # TODO: Send response via WhatsAppClient (will be integrated in task 13)
                # For now, just log the response
                logger.debug(f"Response to send: {response_text[:100]}...")
                
            except Exception as e:
                logger.error(
                    "Error routing message",
                    extra={
                        "message_id": incoming_message.message_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Don't fail the webhook - just log the error
            finally:
                # Decrement active requests
                self.load_monitor.decrement_active_requests()
        else:
            # Fallback: process without load monitoring
            try:
                response_text = await self.route_message(incoming_message)
                
                logger.info(
                    "Message routed successfully",
                    extra={
                        "message_id": incoming_message.message_id,
                        "response_length": len(response_text)
                    }
                )
                
                # TODO: Send response via WhatsAppClient (will be integrated in task 13)
                # For now, just log the response
                logger.debug(f"Response to send: {response_text[:100]}...")
                
            except Exception as e:
                logger.error(
                    "Error routing message",
                    extra={
                        "message_id": incoming_message.message_id,
                        "error": str(e)
                    },
                    exc_info=True
                )
                # Don't fail the webhook - just log the error
        
        return {
            "status": "ok",
            "message": "Message received and processed"
        }
