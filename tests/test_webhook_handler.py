"""Tests for WebhookHandler"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from app.webhook_handler import WebhookHandler
from app.models import MessageType, IncomingMessage


class TestWebhookVerification:
    """Unit tests for webhook verification"""
    
    def test_valid_webhook_verification(self):
        """Test valid signature verification"""
        handler = WebhookHandler()
        
        # Test with correct mode and token
        challenge = handler.verify_webhook(
            mode="subscribe",
            token=handler.verify_token,
            challenge="test_challenge_123"
        )
        
        assert challenge == "test_challenge_123"
    
    def test_invalid_mode_verification(self):
        """Test invalid mode rejection"""
        handler = WebhookHandler()
        
        # Test with incorrect mode
        with pytest.raises(Exception):  # Should raise HTTPException
            handler.verify_webhook(
                mode="invalid_mode",
                token=handler.verify_token,
                challenge="test_challenge_123"
            )
    
    def test_invalid_token_verification(self):
        """Test invalid token rejection"""
        handler = WebhookHandler()
        
        # Test with incorrect token
        with pytest.raises(Exception):  # Should raise HTTPException
            handler.verify_webhook(
                mode="subscribe",
                token="wrong_token",
                challenge="test_challenge_123"
            )
    
    def test_signature_verification_valid(self):
        """Test valid signature verification"""
        handler = WebhookHandler()
        
        # Create a test payload
        payload = b'{"test": "data"}'
        
        # Generate valid signature
        import hmac
        import hashlib
        expected_hash = hmac.new(
            handler.app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_hash}"
        
        # Verify signature
        is_valid = handler.verify_signature(payload, signature)
        assert is_valid is True
    
    def test_signature_verification_invalid(self):
        """Test invalid signature rejection"""
        handler = WebhookHandler()
        
        # Create a test payload
        payload = b'{"test": "data"}'
        
        # Use wrong signature
        signature = "sha256=invalid_hash_12345"
        
        # Verify signature
        is_valid = handler.verify_signature(payload, signature)
        assert is_valid is False
    
    def test_signature_verification_missing(self):
        """Test missing signature rejection"""
        handler = WebhookHandler()
        
        # Create a test payload
        payload = b'{"test": "data"}'
        
        # No signature
        is_valid = handler.verify_signature(payload, "")
        assert is_valid is False
    
    def test_signature_verification_wrong_format(self):
        """Test wrong signature format rejection"""
        handler = WebhookHandler()
        
        # Create a test payload
        payload = b'{"test": "data"}'
        
        # Wrong format (missing sha256= prefix)
        signature = "invalid_format_hash"
        
        # Verify signature
        is_valid = handler.verify_signature(payload, signature)
        assert is_valid is False


class TestMessageExtraction:
    """Unit tests for message extraction from webhook payload"""
    
    def test_extract_text_message(self):
        """Test extracting a text message"""
        handler = WebhookHandler()
        
        # Sample WhatsApp webhook payload for text message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {},
                        "contacts": [{"profile": {"name": "Test User"}}],
                        "messages": [{
                            "from": "1234567890",
                            "id": "wamid.test123",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hello, I need help"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        message = handler.extract_message(payload)
        
        assert message is not None
        assert message.message_id == "wamid.test123"
        assert message.from_phone == "+1234567890"
        assert message.message_type == MessageType.TEXT
        assert message.text_content == "Hello, I need help"
    
    def test_extract_image_message(self):
        """Test extracting an image message"""
        handler = WebhookHandler()
        
        # Sample WhatsApp webhook payload for image message
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "id": "123456",
                "changes": [{
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {},
                        "contacts": [{"profile": {"name": "Test User"}}],
                        "messages": [{
                            "from": "1234567890",
                            "id": "wamid.test456",
                            "timestamp": "1234567890",
                            "type": "image",
                            "image": {"url": "https://example.com/image.jpg"}
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }
        
        message = handler.extract_message(payload)
        
        assert message is not None
        assert message.message_id == "wamid.test456"
        assert message.message_type == MessageType.IMAGE
        assert message.media_url == "https://example.com/image.jpg"
    
    def test_extract_message_no_entries(self):
        """Test handling payload with no entries"""
        handler = WebhookHandler()
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": []
        }
        
        message = handler.extract_message(payload)
        assert message is None
    
    def test_extract_message_wrong_object_type(self):
        """Test handling payload with wrong object type"""
        handler = WebhookHandler()
        
        payload = {
            "object": "instagram_account",
            "entry": []
        }
        
        message = handler.extract_message(payload)
        assert message is None


class TestMultimediaHandling:
    """Property test for multimedia message handling"""
    
    @given(
        message_type=st.sampled_from([
            MessageType.IMAGE,
            MessageType.AUDIO,
            MessageType.VIDEO,
            MessageType.DOCUMENT
        ]),
        phone_number=st.from_regex(r'^\+\d{10,15}$', fullmatch=True),
        media_url=st.from_regex(r'^https://[a-z]+\.com/[a-z]+\.(jpg|mp3|mp4|pdf)$', fullmatch=True)
    )
    def test_multimedia_message_acknowledgment(self, message_type, phone_number, media_url):
        """
        Feature: y-connect-whatsapp-bot, Property 3: Multimedia Message Handling
        
        For any non-text message (image, audio, video), the system should respond 
        with an acknowledgment message instructing the user to use text queries.
        
        Validates: Requirements 1.3
        """
        handler = WebhookHandler()
        
        # Create multimedia message
        incoming_message = IncomingMessage(
            message_id=f"wamid_{message_type.value}_test",
            from_phone=phone_number,
            timestamp=datetime.utcnow(),
            message_type=message_type,
            text_content="",
            media_url=media_url
        )
        
        # Handle multimedia message
        response = handler._handle_multimedia_message(incoming_message)
        
        # Verify acknowledgment message is returned
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Verify message instructs user to use text
        response_lower = response.lower()
        assert "text" in response_lower or "type" in response_lower
        
        # Verify message is polite (contains "thank" or similar)
        assert any(word in response_lower for word in ["thank", "however", "please"])
