"""Unit tests for WhatsApp Business API client"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import httpx

from app.whatsapp_client import (
    WhatsAppClient,
    WhatsAppAPIError,
    MessageQueueItem
)
from app.models import OutgoingMessage, MessageType
from app.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings for testing"""
    settings = Mock(spec=Settings)
    settings.whatsapp_api_url = "https://graph.facebook.com/v18.0"
    settings.whatsapp_access_token = "test_token"
    settings.whatsapp_phone_number_id = "123456789"
    return settings


@pytest.fixture
def whatsapp_client(mock_settings):
    """Create WhatsApp client with mock settings"""
    with patch('app.whatsapp_client.httpx.Client'):
        client = WhatsAppClient(settings=mock_settings, max_retries=3)
        return client


class TestWhatsAppClient:
    """Test WhatsAppClient class"""
    
    def test_initialization(self, mock_settings):
        """Test client initialization"""
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            assert client.api_url == "https://graph.facebook.com/v18.0"
            assert client.access_token == "test_token"
            assert client.phone_number_id == "123456789"
            assert client.max_retries == 3
            assert client.retry_delays == [1, 2, 4]
            assert len(client.failed_message_queue) == 0
    
    def test_get_headers(self, whatsapp_client):
        """Test header generation"""
        headers = whatsapp_client._get_headers()
        
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
    
    def test_should_retry_server_error(self, whatsapp_client):
        """Test retry logic for server errors (5xx)"""
        assert whatsapp_client._should_retry(500) is True
        assert whatsapp_client._should_retry(502) is True
        assert whatsapp_client._should_retry(503) is True
    
    def test_should_retry_rate_limit(self, whatsapp_client):
        """Test retry logic for rate limiting (429)"""
        assert whatsapp_client._should_retry(429) is True
    
    def test_should_not_retry_client_error(self, whatsapp_client):
        """Test no retry for client errors (4xx except 429)"""
        assert whatsapp_client._should_retry(400) is False
        assert whatsapp_client._should_retry(401) is False
        assert whatsapp_client._should_retry(404) is False
    
    def test_should_not_retry_success(self, whatsapp_client):
        """Test no retry for successful responses"""
        assert whatsapp_client._should_retry(200) is False
        assert whatsapp_client._should_retry(201) is False
    
    def test_send_message_success(self, whatsapp_client):
        """Test successful message sending"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "1234567890", "wa_id": "1234567890"}],
            "messages": [{"id": "wamid.test123"}]
        }
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Send message
        result = whatsapp_client.send_message(
            to_phone="+1234567890",
            text_content="Test message"
        )
        
        # Verify result
        assert result["messages"][0]["id"] == "wamid.test123"
        
        # Verify API call
        whatsapp_client.client.post.assert_called_once()
        call_args = whatsapp_client.client.post.call_args
        
        assert "1234567890" in str(call_args)  # Phone without +
        assert call_args[1]["json"]["type"] == "text"
        assert call_args[1]["json"]["text"]["body"] == "Test message"
    
    def test_send_message_with_reply(self, whatsapp_client):
        """Test sending message as a reply"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Send message with reply
        whatsapp_client.send_message(
            to_phone="+1234567890",
            text_content="Reply message",
            reply_to_message_id="wamid.original123"
        )
        
        # Verify context was added
        call_args = whatsapp_client.client.post.call_args
        payload = call_args[1]["json"]
        
        assert "context" in payload
        assert payload["context"]["message_id"] == "wamid.original123"
    
    def test_send_message_retry_on_server_error(self, whatsapp_client):
        """Test retry logic on server error"""
        # Mock responses: first two fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = '{"error": {"message": "Server error"}}'
        mock_response_fail.json.return_value = {"error": {"message": "Server error"}}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(
            side_effect=[mock_response_fail, mock_response_fail, mock_response_success]
        )
        
        # Mock time.sleep to speed up test
        with patch('app.whatsapp_client.time.sleep'):
            result = whatsapp_client.send_message(
                to_phone="+1234567890",
                text_content="Test message"
            )
        
        # Verify success after retries
        assert result["messages"][0]["id"] == "wamid.test123"
        assert whatsapp_client.client.post.call_count == 3
    
    def test_send_message_queue_on_failure(self, whatsapp_client):
        """Test message queuing on failure"""
        # Mock all attempts failing
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"error": {"message": "Server error"}}'
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Mock time.sleep to speed up test
        with patch('app.whatsapp_client.time.sleep'):
            with pytest.raises(WhatsAppAPIError):
                whatsapp_client.send_message(
                    to_phone="+1234567890",
                    text_content="Test message",
                    queue_on_failure=True
                )
        
        # Verify message was queued
        assert whatsapp_client.get_queue_size() == 1
        
        queued_item = whatsapp_client.failed_message_queue[0]
        assert queued_item.to_phone == "+1234567890"
        assert queued_item.text_content == "Test message"
    
    def test_send_message_no_queue_on_failure(self, whatsapp_client):
        """Test message not queued when queue_on_failure=False"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"error": {"message": "Server error"}}'
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        with patch('app.whatsapp_client.time.sleep'):
            with pytest.raises(WhatsAppAPIError):
                whatsapp_client.send_message(
                    to_phone="+1234567890",
                    text_content="Test message",
                    queue_on_failure=False
                )
        
        # Verify message was NOT queued
        assert whatsapp_client.get_queue_size() == 0
    
    def test_send_template_message_success(self, whatsapp_client):
        """Test successful template message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Send template message
        result = whatsapp_client.send_template_message(
            to_phone="+1234567890",
            template_name="welcome_message",
            language_code="en"
        )
        
        # Verify result
        assert result["messages"][0]["id"] == "wamid.test123"
        
        # Verify API call
        call_args = whatsapp_client.client.post.call_args
        payload = call_args[1]["json"]
        
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "welcome_message"
        assert payload["template"]["language"]["code"] == "en"
    
    def test_send_template_message_with_components(self, whatsapp_client):
        """Test template message with components"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "John"}
                ]
            }
        ]
        
        # Send template message with components
        whatsapp_client.send_template_message(
            to_phone="+1234567890",
            template_name="personalized_welcome",
            language_code="en",
            components=components
        )
        
        # Verify components were included
        call_args = whatsapp_client.client.post.call_args
        payload = call_args[1]["json"]
        
        assert "components" in payload["template"]
        assert payload["template"]["components"] == components
    
    def test_send_outgoing_message_text(self, whatsapp_client):
        """Test sending OutgoingMessage with text type"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        message = OutgoingMessage(
            to_phone="+1234567890",
            message_type=MessageType.TEXT,
            text_content="Test message"
        )
        
        result = whatsapp_client.send_outgoing_message(message)
        
        assert result["messages"][0]["id"] == "wamid.test123"
    
    def test_send_outgoing_message_template(self, whatsapp_client):
        """Test sending OutgoingMessage with template type"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        message = OutgoingMessage(
            to_phone="+1234567890",
            message_type=MessageType.TEMPLATE,
            text_content="template:welcome_message"
        )
        
        result = whatsapp_client.send_outgoing_message(message)
        
        assert result["messages"][0]["id"] == "wamid.test123"
    
    def test_send_outgoing_message_invalid_template_format(self, whatsapp_client):
        """Test error on invalid template format"""
        message = OutgoingMessage(
            to_phone="+1234567890",
            message_type=MessageType.TEMPLATE,
            text_content="invalid_format"
        )
        
        with pytest.raises(WhatsAppAPIError, match="must start with 'template:'"):
            whatsapp_client.send_outgoing_message(message)
    
    def test_send_outgoing_message_unsupported_type(self, whatsapp_client):
        """Test error on unsupported message type"""
        message = OutgoingMessage(
            to_phone="+1234567890",
            message_type=MessageType.IMAGE,
            text_content="Test"
        )
        
        with pytest.raises(WhatsAppAPIError, match="Unsupported message type"):
            whatsapp_client.send_outgoing_message(message)
    
    def test_process_queued_messages_success(self, whatsapp_client):
        """Test processing queued messages successfully"""
        # Add messages to queue
        whatsapp_client.failed_message_queue.append(
            MessageQueueItem(
                to_phone="+1234567890",
                text_content="Message 1"
            )
        )
        whatsapp_client.failed_message_queue.append(
            MessageQueueItem(
                to_phone="+0987654321",
                text_content="Message 2"
            )
        )
        
        # Mock successful responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Process queue
        result = whatsapp_client.process_queued_messages()
        
        # Verify results
        assert result["success"] == 2
        assert result["failed"] == 0
        assert result["requeued"] == 0
        assert whatsapp_client.get_queue_size() == 0
    
    def test_process_queued_messages_with_failures(self, whatsapp_client):
        """Test processing queued messages with some failures"""
        # Add message to queue
        whatsapp_client.failed_message_queue.append(
            MessageQueueItem(
                to_phone="+1234567890",
                text_content="Message 1",
                retry_count=0
            )
        )
        
        # Mock failing response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"error": {"message": "Server error"}}'
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Process queue
        with patch('app.whatsapp_client.time.sleep'):
            result = whatsapp_client.process_queued_messages()
        
        # Verify message was requeued
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["requeued"] == 1
        assert whatsapp_client.get_queue_size() == 1
    
    def test_process_queued_messages_permanent_failure(self, whatsapp_client):
        """Test processing queued messages with permanent failures"""
        # Add message with max retries already reached
        whatsapp_client.failed_message_queue.append(
            MessageQueueItem(
                to_phone="+1234567890",
                text_content="Message 1",
                retry_count=3  # Already at max retries
            )
        )
        
        # Mock failing response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = '{"error": {"message": "Server error"}}'
        mock_response.json.return_value = {"error": {"message": "Server error"}}
        
        whatsapp_client.client.post = Mock(return_value=mock_response)
        
        # Process queue
        with patch('app.whatsapp_client.time.sleep'):
            result = whatsapp_client.process_queued_messages()
        
        # Verify message was permanently failed
        assert result["success"] == 0
        assert result["failed"] == 1
        assert result["requeued"] == 0
        assert whatsapp_client.get_queue_size() == 0
    
    def test_process_queued_messages_empty_queue(self, whatsapp_client):
        """Test processing empty queue"""
        result = whatsapp_client.process_queued_messages()
        
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["requeued"] == 0
    
    def test_context_manager(self, mock_settings):
        """Test context manager usage"""
        with patch('app.whatsapp_client.httpx.Client') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_class.return_value = mock_client_instance
            
            with WhatsAppClient(settings=mock_settings) as client:
                assert client is not None
            
            # Verify close was called
            mock_client_instance.close.assert_called_once()


class TestMessageQueueItem:
    """Test MessageQueueItem class"""
    
    def test_initialization_text_message(self):
        """Test initialization for text message"""
        item = MessageQueueItem(
            to_phone="+1234567890",
            text_content="Test message"
        )
        
        assert item.to_phone == "+1234567890"
        assert item.text_content == "Test message"
        assert item.template_name is None
        assert item.retry_count == 0
        assert item.is_template() is False
    
    def test_initialization_template_message(self):
        """Test initialization for template message"""
        item = MessageQueueItem(
            to_phone="+1234567890",
            text_content="",
            template_name="welcome_message",
            language_code="en"
        )
        
        assert item.to_phone == "+1234567890"
        assert item.template_name == "welcome_message"
        assert item.language_code == "en"
        assert item.is_template() is True
    
    def test_queued_at_default(self):
        """Test default queued_at timestamp"""
        before = datetime.utcnow()
        item = MessageQueueItem(
            to_phone="+1234567890",
            text_content="Test"
        )
        after = datetime.utcnow()
        
        assert before <= item.queued_at <= after
