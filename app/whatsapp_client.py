"""WhatsApp Business API client for Y-Connect"""

import logging
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from collections import deque
import httpx
from app.config import get_settings
from app.models import OutgoingMessage, MessageType

logger = logging.getLogger(__name__)


class WhatsAppAPIError(Exception):
    """Exception raised for WhatsApp API errors"""
    pass


class MessageQueueItem:
    """Item in the failed message queue"""
    
    def __init__(
        self,
        to_phone: str,
        text_content: str,
        reply_to_message_id: Optional[str] = None,
        template_name: Optional[str] = None,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
        retry_count: int = 0,
        queued_at: Optional[datetime] = None
    ):
        self.to_phone = to_phone
        self.text_content = text_content
        self.reply_to_message_id = reply_to_message_id
        self.template_name = template_name
        self.language_code = language_code
        self.components = components
        self.retry_count = retry_count
        self.queued_at = queued_at or datetime.utcnow()
    
    def is_template(self) -> bool:
        """Check if this is a template message"""
        return self.template_name is not None


class WhatsAppClient:
    """Client for interacting with WhatsApp Business Cloud API"""
    
    def __init__(self, settings=None, max_retries: int = 3):
        """
        Initialize WhatsApp client
        
        Args:
            settings: Optional Settings object (defaults to get_settings())
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.settings = settings or get_settings()
        self.api_url = self.settings.whatsapp_api_url
        self.access_token = self.settings.whatsapp_access_token
        self.phone_number_id = self.settings.whatsapp_phone_number_id
        self.base_url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        # Retry configuration
        self.max_retries = max_retries
        self.retry_delays = [1, 2, 4]  # Exponential backoff in seconds
        
        # Failed message queue
        self.failed_message_queue: deque = deque()
        
        # HTTP client with timeout
        self.client = httpx.Client(timeout=30.0)
        
        logger.info(
            f"WhatsAppClient initialized with phone_number_id: {self.phone_number_id}, "
            f"max_retries: {self.max_retries}"
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for WhatsApp API requests
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _log_request(self, method: str, url: str, payload: Dict[str, Any]) -> None:
        """
        Log API request details
        
        Args:
            method: HTTP method
            url: Request URL
            payload: Request payload
        """
        # Sanitize payload for logging (remove sensitive data)
        safe_payload = payload.copy()
        if "to" in safe_payload:
            # Mask phone number for privacy
            phone = safe_payload["to"]
            safe_payload["to"] = f"{phone[:3]}***{phone[-4:]}" if len(phone) > 7 else "***"
        
        logger.info(f"WhatsApp API Request: {method} {url}")
        logger.debug(f"Request payload: {safe_payload}")
    
    def _log_response(self, response: httpx.Response) -> None:
        """
        Log API response details
        
        Args:
            response: HTTP response object
        """
        logger.info(f"WhatsApp API Response: Status {response.status_code}")
        logger.debug(f"Response body: {response.text}")
    
    def _should_retry(self, status_code: int) -> bool:
        """
        Determine if a request should be retried based on status code
        
        Args:
            status_code: HTTP status code
        
        Returns:
            True if request should be retried
        """
        # Retry on server errors (5xx) and rate limiting (429)
        # Don't retry on client errors (4xx) except 429
        return status_code >= 500 or status_code == 429
    
    def _execute_with_retry(
        self,
        operation: Callable[[], httpx.Response],
        operation_name: str
    ) -> httpx.Response:
        """
        Execute an operation with retry logic
        
        Args:
            operation: Callable that returns an httpx.Response
            operation_name: Name of the operation for logging
        
        Returns:
            HTTP response object
        
        Raises:
            WhatsAppAPIError: If all retry attempts fail
        """
        last_exception = None
        last_response = None
        
        for attempt in range(self.max_retries):
            try:
                response = operation()
                last_response = response
                
                # If successful, return immediately
                if response.status_code == 200:
                    if attempt > 0:
                        logger.info(
                            f"{operation_name} succeeded on attempt {attempt + 1}"
                        )
                    return response
                
                # Check if we should retry
                if not self._should_retry(response.status_code):
                    # Don't retry on client errors (except 429)
                    return response
                
                # Log retry attempt
                logger.warning(
                    f"{operation_name} failed with status {response.status_code}, "
                    f"attempt {attempt + 1}/{self.max_retries}"
                )
                
                # Wait before retrying (exponential backoff)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.info(f"Waiting {delay}s before retry...")
                    time.sleep(delay)
                
            except httpx.HTTPError as e:
                last_exception = e
                logger.warning(
                    f"{operation_name} HTTP error on attempt {attempt + 1}/{self.max_retries}: {str(e)}"
                )
                
                # Wait before retrying
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                    logger.info(f"Waiting {delay}s before retry...")
                    time.sleep(delay)
        
        # All retries exhausted
        if last_exception:
            raise WhatsAppAPIError(
                f"{operation_name} failed after {self.max_retries} attempts: {str(last_exception)}"
            )
        elif last_response and last_response.status_code != 200:
            # Return the last failed response so caller can handle it
            return last_response
        else:
            raise WhatsAppAPIError(
                f"{operation_name} failed after {self.max_retries} attempts"
            )
    
    def _queue_failed_message(self, queue_item: MessageQueueItem) -> None:
        """
        Add a failed message to the retry queue
        
        Args:
            queue_item: MessageQueueItem to queue
        """
        self.failed_message_queue.append(queue_item)
        logger.info(
            f"Message queued for later retry. Queue size: {len(self.failed_message_queue)}"
        )
    
    def get_queue_size(self) -> int:
        """
        Get the current size of the failed message queue
        
        Returns:
            Number of messages in the queue
        """
        return len(self.failed_message_queue)
    
    def process_queued_messages(self) -> Dict[str, int]:
        """
        Process all messages in the failed message queue
        
        Returns:
            Dictionary with counts: {"success": int, "failed": int, "requeued": int}
        """
        if not self.failed_message_queue:
            logger.info("No queued messages to process")
            return {"success": 0, "failed": 0, "requeued": 0}
        
        logger.info(f"Processing {len(self.failed_message_queue)} queued messages")
        
        success_count = 0
        failed_count = 0
        requeued_count = 0
        
        # Process all messages currently in queue
        queue_size = len(self.failed_message_queue)
        for _ in range(queue_size):
            item = self.failed_message_queue.popleft()
            
            try:
                if item.is_template():
                    self.send_template_message(
                        to_phone=item.to_phone,
                        template_name=item.template_name,
                        language_code=item.language_code,
                        components=item.components,
                        queue_on_failure=False  # Don't double-queue
                    )
                else:
                    self.send_message(
                        to_phone=item.to_phone,
                        text_content=item.text_content,
                        reply_to_message_id=item.reply_to_message_id,
                        queue_on_failure=False  # Don't double-queue
                    )
                
                success_count += 1
                logger.info(f"Queued message sent successfully")
                
            except WhatsAppAPIError as e:
                # Increment retry count
                item.retry_count += 1
                
                # Requeue if under max retries
                if item.retry_count < self.max_retries:
                    self.failed_message_queue.append(item)
                    requeued_count += 1
                    logger.warning(
                        f"Queued message failed, requeued (retry {item.retry_count}/{self.max_retries})"
                    )
                else:
                    failed_count += 1
                    logger.error(
                        f"Queued message permanently failed after {self.max_retries} retries"
                    )
        
        result = {
            "success": success_count,
            "failed": failed_count,
            "requeued": requeued_count
        }
        
        logger.info(f"Queue processing complete: {result}")
        return result
    
    def send_message(
        self,
        to_phone: str,
        text_content: str,
        reply_to_message_id: Optional[str] = None,
        queue_on_failure: bool = True
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp Business API with retry logic
        
        Args:
            to_phone: Recipient's phone number in international format (with +)
            text_content: Text message content
            reply_to_message_id: Optional message ID to reply to
            queue_on_failure: Whether to queue message on failure (default: True)
        
        Returns:
            API response dictionary containing message ID and status
        
        Raises:
            WhatsAppAPIError: If API request fails after all retries
        """
        # Remove + prefix if present (WhatsApp API expects without +)
        phone_number = to_phone.lstrip("+")
        
        # Construct payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": text_content
            }
        }
        
        # Add context for reply if provided
        if reply_to_message_id:
            payload["context"] = {
                "message_id": reply_to_message_id
            }
        
        # Log request
        self._log_request("POST", self.base_url, payload)
        
        try:
            # Execute with retry logic
            def make_request():
                return self.client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
            
            response = self._execute_with_retry(make_request, "send_message")
            
            # Log response
            self._log_response(response)
            
            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(
                    f"WhatsApp API error: {response.status_code} - {error_message}"
                )
                
                # Queue message for later retry if enabled
                if queue_on_failure:
                    queue_item = MessageQueueItem(
                        to_phone=to_phone,
                        text_content=text_content,
                        reply_to_message_id=reply_to_message_id
                    )
                    self._queue_failed_message(queue_item)
                
                raise WhatsAppAPIError(
                    f"Failed to send message: {response.status_code} - {error_message}"
                )
            
            # Parse response
            response_data = response.json()
            
            logger.info(
                f"Message sent successfully to {phone_number[:3]}***{phone_number[-4:]}"
            )
            
            return response_data
            
        except WhatsAppAPIError:
            # Re-raise WhatsAppAPIError (already logged and queued if needed)
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message: {str(e)}")
            
            # Queue message for later retry if enabled
            if queue_on_failure:
                queue_item = MessageQueueItem(
                    to_phone=to_phone,
                    text_content=text_content,
                    reply_to_message_id=reply_to_message_id
                )
                self._queue_failed_message(queue_item)
            
            raise WhatsAppAPIError(f"Unexpected error: {str(e)}")
    
    def send_template_message(
        self,
        to_phone: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict[str, Any]]] = None,
        queue_on_failure: bool = True
    ) -> Dict[str, Any]:
        """
        Send a template message via WhatsApp Business API with retry logic
        
        Template messages are pre-approved message formats used for
        notifications, welcome messages, etc.
        
        Args:
            to_phone: Recipient's phone number in international format (with +)
            template_name: Name of the approved template
            language_code: Language code for the template (default: "en")
            components: Optional list of template components (parameters, buttons, etc.)
            queue_on_failure: Whether to queue message on failure (default: True)
        
        Returns:
            API response dictionary containing message ID and status
        
        Raises:
            WhatsAppAPIError: If API request fails after all retries
        """
        # Remove + prefix if present
        phone_number = to_phone.lstrip("+")
        
        # Construct payload
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        # Add components if provided
        if components:
            payload["template"]["components"] = components
        
        # Log request
        self._log_request("POST", self.base_url, payload)
        
        try:
            # Execute with retry logic
            def make_request():
                return self.client.post(
                    self.base_url,
                    headers=self._get_headers(),
                    json=payload
                )
            
            response = self._execute_with_retry(make_request, "send_template_message")
            
            # Log response
            self._log_response(response)
            
            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_message = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(
                    f"WhatsApp API error: {response.status_code} - {error_message}"
                )
                
                # Queue message for later retry if enabled
                if queue_on_failure:
                    queue_item = MessageQueueItem(
                        to_phone=to_phone,
                        text_content="",  # Not used for templates
                        template_name=template_name,
                        language_code=language_code,
                        components=components
                    )
                    self._queue_failed_message(queue_item)
                
                raise WhatsAppAPIError(
                    f"Failed to send template message: {response.status_code} - {error_message}"
                )
            
            # Parse response
            response_data = response.json()
            
            logger.info(
                f"Template message '{template_name}' sent successfully to "
                f"{phone_number[:3]}***{phone_number[-4:]}"
            )
            
            return response_data
            
        except WhatsAppAPIError:
            # Re-raise WhatsAppAPIError (already logged and queued if needed)
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending template message: {str(e)}")
            
            # Queue message for later retry if enabled
            if queue_on_failure:
                queue_item = MessageQueueItem(
                    to_phone=to_phone,
                    text_content="",  # Not used for templates
                    template_name=template_name,
                    language_code=language_code,
                    components=components
                )
                self._queue_failed_message(queue_item)
            
            raise WhatsAppAPIError(f"Unexpected error: {str(e)}")
    
    def send_outgoing_message(self, message: OutgoingMessage) -> Dict[str, Any]:
        """
        Send an OutgoingMessage model via WhatsApp API
        
        Args:
            message: OutgoingMessage model instance
        
        Returns:
            API response dictionary
        
        Raises:
            WhatsAppAPIError: If API request fails
        """
        if message.message_type == MessageType.TEXT:
            return self.send_message(
                to_phone=message.to_phone,
                text_content=message.text_content,
                reply_to_message_id=message.reply_to_message_id
            )
        elif message.message_type == MessageType.TEMPLATE:
            # For template messages, extract template name from text_content
            # Format expected: "template:template_name"
            if message.text_content.startswith("template:"):
                template_name = message.text_content.split(":", 1)[1]
                return self.send_template_message(
                    to_phone=message.to_phone,
                    template_name=template_name
                )
            else:
                raise WhatsAppAPIError(
                    "Template message text_content must start with 'template:'"
                )
        else:
            raise WhatsAppAPIError(
                f"Unsupported message type: {message.message_type}"
            )
    
    def close(self) -> None:
        """Close the HTTP client"""
        self.client.close()
        logger.info("WhatsAppClient closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
