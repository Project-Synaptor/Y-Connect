"""Property-based tests for WhatsApp Business API client

Feature: y-connect-whatsapp-bot
"""

import pytest
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import httpx

from app.whatsapp_client import WhatsAppClient, WhatsAppAPIError
from app.config import Settings


# Custom strategies
@st.composite
def phone_number_strategy(draw):
    """Generate valid international phone numbers"""
    country_code = draw(st.integers(min_value=1, max_value=999))
    number = draw(st.integers(min_value=1000000, max_value=9999999999))
    return f"+{country_code}{number}"


@st.composite
def message_text_strategy(draw):
    """Generate valid message text (1-4096 characters)"""
    return draw(st.text(min_size=1, max_size=4096))


def create_mock_settings():
    """Create mock settings for testing"""
    settings = Mock(spec=Settings)
    settings.whatsapp_api_url = "https://graph.facebook.com/v18.0"
    settings.whatsapp_access_token = "test_token"
    settings.whatsapp_phone_number_id = "123456789"
    return settings


class TestWhatsAppClientProperties:
    """Property-based tests for WhatsAppClient"""
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy(),
        failure_count=st.integers(min_value=1, max_value=5)
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_api_retry_logic(
        self,
        phone,
        message,
        failure_count
    ):
        """
        Property 27: API Retry Logic
        
        For any WhatsApp API call that fails, the system should retry up to 3 times
        with exponential backoff before marking the message as failed.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock responses: all fail with server error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = '{"error": {"message": "Server error"}}'
            mock_response.json.return_value = {"error": {"message": "Server error"}}
            
            # Track number of attempts
            call_count = 0
            
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return mock_response
            
            client.client.post = mock_post
            
            # Mock time.sleep to speed up test
            with patch('app.whatsapp_client.time.sleep'):
                try:
                    client.send_message(
                        to_phone=phone,
                        text_content=message,
                        queue_on_failure=False
                    )
                except WhatsAppAPIError:
                    pass  # Expected to fail
            
            # Property: Should retry exactly 3 times (max_retries)
            assert call_count == 3, (
                f"Expected exactly 3 retry attempts, but got {call_count}"
            )
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy(),
        success_on_attempt=st.integers(min_value=1, max_value=3)
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_retry_stops_on_success(
        self,
        phone,
        message,
        success_on_attempt
    ):
        """
        Property 27: API Retry Logic (Success Case)
        
        For any WhatsApp API call that succeeds on retry N (where N <= 3),
        the system should stop retrying and return the successful response.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock responses: fail until success_on_attempt, then succeed
            call_count = 0
            
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count < success_on_attempt:
                    # Fail with server error
                    mock_response = Mock()
                    mock_response.status_code = 500
                    mock_response.text = '{"error": {"message": "Server error"}}'
                    mock_response.json.return_value = {"error": {"message": "Server error"}}
                    return mock_response
                else:
                    # Succeed
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "messages": [{"id": "wamid.test123"}]
                    }
                    return mock_response
            
            client.client.post = mock_post
            
            # Mock time.sleep to speed up test
            with patch('app.whatsapp_client.time.sleep'):
                result = client.send_message(
                    to_phone=phone,
                    text_content=message,
                    queue_on_failure=False
                )
            
            # Property: Should stop retrying after success
            assert call_count == success_on_attempt, (
                f"Expected {success_on_attempt} attempts before success, "
                f"but got {call_count}"
            )
            
            # Property: Should return successful response
            assert result["messages"][0]["id"] == "wamid.test123"
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy()
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_exponential_backoff(
        self,
        phone,
        message
    ):
        """
        Property 27: API Retry Logic (Exponential Backoff)
        
        For any WhatsApp API call that fails, the system should use
        exponential backoff delays: 1s, 2s, 4s between retries.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock responses: all fail
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = '{"error": {"message": "Server error"}}'
            mock_response.json.return_value = {"error": {"message": "Server error"}}
            
            client.client.post = Mock(return_value=mock_response)
            
            # Track sleep calls
            sleep_calls = []
            
            def mock_sleep(seconds):
                sleep_calls.append(seconds)
            
            with patch('app.whatsapp_client.time.sleep', side_effect=mock_sleep):
                try:
                    client.send_message(
                        to_phone=phone,
                        text_content=message,
                        queue_on_failure=False
                    )
                except WhatsAppAPIError:
                    pass  # Expected to fail
            
            # Property: Should use exponential backoff delays
            # With 3 attempts, there should be 2 sleep calls (between attempts)
            assert len(sleep_calls) == 2, (
                f"Expected 2 sleep calls between 3 attempts, but got {len(sleep_calls)}"
            )
            
            # Property: Delays should be [1, 2] (exponential backoff)
            expected_delays = [1, 2]
            assert sleep_calls == expected_delays, (
                f"Expected delays {expected_delays}, but got {sleep_calls}"
            )
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy(),
        status_code=st.integers(min_value=400, max_value=499).filter(lambda x: x != 429)
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_no_retry_on_client_errors(
        self,
        phone,
        message,
        status_code
    ):
        """
        Property 27: API Retry Logic (No Retry on Client Errors)
        
        For any WhatsApp API call that fails with a client error (4xx except 429),
        the system should NOT retry and should fail immediately.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock response: client error
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = '{"error": {"message": "Client error"}}'
            mock_response.json.return_value = {"error": {"message": "Client error"}}
            
            call_count = 0
            
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return mock_response
            
            client.client.post = mock_post
            
            # Should fail without retrying
            with pytest.raises(WhatsAppAPIError):
                client.send_message(
                    to_phone=phone,
                    text_content=message,
                    queue_on_failure=False
                )
            
            # Property: Should NOT retry on client errors (only 1 attempt)
            assert call_count == 1, (
                f"Expected no retries (1 attempt) for client error {status_code}, "
                f"but got {call_count} attempts"
            )
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy()
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_retry_on_rate_limit(
        self,
        phone,
        message
    ):
        """
        Property 27: API Retry Logic (Retry on Rate Limit)
        
        For any WhatsApp API call that fails with rate limiting (429),
        the system should retry up to 3 times with exponential backoff.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock response: rate limit error
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = '{"error": {"message": "Rate limit exceeded"}}'
            mock_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}
            
            call_count = 0
            
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return mock_response
            
            client.client.post = mock_post
            
            # Mock time.sleep to speed up test
            with patch('app.whatsapp_client.time.sleep'):
                try:
                    client.send_message(
                        to_phone=phone,
                        text_content=message,
                        queue_on_failure=False
                    )
                except WhatsAppAPIError:
                    pass  # Expected to fail
            
            # Property: Should retry on rate limit (429)
            assert call_count == 3, (
                f"Expected 3 retry attempts for rate limit error, but got {call_count}"
            )
    
    @given(
        phone=phone_number_strategy(),
        message=message_text_strategy()
    )
    @settings(
        max_examples=50,
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_property_27_message_queuing_on_failure(
        self,
        phone,
        message
    ):
        """
        Property 27: API Retry Logic (Message Queuing)
        
        For any WhatsApp API call that fails after all retries,
        the system should queue the message for later retry if queue_on_failure=True.
        
        Validates: Requirements 9.4
        """
        # Assume valid inputs
        assume(len(phone) >= 10)
        assume(len(message) >= 1)
        
        mock_settings = create_mock_settings()
        
        with patch('app.whatsapp_client.httpx.Client'):
            client = WhatsAppClient(settings=mock_settings, max_retries=3)
            
            # Mock response: all fail
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = '{"error": {"message": "Server error"}}'
            mock_response.json.return_value = {"error": {"message": "Server error"}}
            
            client.client.post = Mock(return_value=mock_response)
            
            # Mock time.sleep to speed up test
            with patch('app.whatsapp_client.time.sleep'):
                try:
                    client.send_message(
                        to_phone=phone,
                        text_content=message,
                        queue_on_failure=True
                    )
                except WhatsAppAPIError:
                    pass  # Expected to fail
            
            # Property: Message should be queued after all retries fail
            assert client.get_queue_size() == 1, (
                f"Expected 1 message in queue after failure, but got {client.get_queue_size()}"
            )
            
            # Property: Queued message should have correct details
            queued_item = client.failed_message_queue[0]
            assert queued_item.to_phone == phone
            assert queued_item.text_content == message
