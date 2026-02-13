"""Error handling middleware and utilities for Y-Connect WhatsApp Bot"""

import re
import traceback
from typing import Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.logging_config import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """Handles errors and generates user-friendly messages"""
    
    @staticmethod
    def anonymize_phone(text: str) -> str:
        """
        Anonymize phone numbers in text for logging
        
        Args:
            text: Text that may contain phone numbers
            
        Returns:
            Text with phone numbers anonymized
        """
        # Pattern for phone numbers (international format)
        # Matches: +1234567890, +91-1234567890, +1 (234) 567-8900, etc.
        phone_pattern = r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        
        def replace_phone(match):
            phone = match.group(0)
            # Keep only last 4 digits
            if len(phone) >= 4:
                return f"****{phone[-4:]}"
            return "****"
        
        return re.sub(phone_pattern, replace_phone, text)
    
    @staticmethod
    def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
        """
        Generate user-friendly error message without exposing technical details
        
        Args:
            error: Exception that occurred
            include_details: Whether to include sanitized error details (for development)
            
        Returns:
            User-friendly error message
        """
        # Map exception types to user-friendly messages
        error_messages = {
            "ConnectionError": "We're having trouble connecting to our services. Please try again in a moment.",
            "TimeoutError": "The request took too long to process. Please try again.",
            "ValueError": "There was an issue processing your request. Please check your input and try again.",
            "KeyError": "Some required information is missing. Please try again.",
            "HTTPException": "There was an issue with the request. Please try again.",
            "ValidationError": "The information provided doesn't match the expected format. Please check and try again.",
        }
        
        # Get error type name
        error_type = type(error).__name__
        
        # Get base message
        base_message = error_messages.get(
            error_type,
            "Something went wrong while processing your request. Please try again later."
        )
        
        # Add sanitized details if requested (for development)
        if include_details:
            # Remove any stack traces, file paths, or internal component names
            error_str = str(error)
            # Remove file paths
            error_str = re.sub(r'/[^\s]+\.py', '[file]', error_str)
            # Remove line numbers
            error_str = re.sub(r'line \d+', 'line [N]', error_str)
            # Anonymize phone numbers
            error_str = ErrorHandler.anonymize_phone(error_str)
            
            return f"{base_message}\n\nDetails: {error_str[:100]}"
        
        return base_message
    
    @staticmethod
    def log_error(
        error: Exception,
        request_context: Optional[Dict[str, Any]] = None,
        user_phone: Optional[str] = None
    ) -> None:
        """
        Log error with request context and anonymized user information
        
        Args:
            error: Exception that occurred
            request_context: Additional context about the request
            user_phone: User's phone number (will be anonymized)
        """
        # Build log context
        log_context = {
            "error_type": type(error).__name__,
            "error_message": ErrorHandler.anonymize_phone(str(error)),
        }
        
        # Add anonymized phone number
        if user_phone:
            log_context["phone_number"] = user_phone  # Will be anonymized by CustomJsonFormatter
        
        # Add request context (anonymize any sensitive data)
        if request_context:
            sanitized_context = {}
            for key, value in request_context.items():
                if isinstance(value, str):
                    sanitized_context[key] = ErrorHandler.anonymize_phone(value)
                else:
                    sanitized_context[key] = value
            log_context["request_context"] = sanitized_context
        
        # Log error with stack trace
        logger.error(
            "Error occurred during request processing",
            extra=log_context,
            exc_info=True
        )
    
    @staticmethod
    def create_error_response(
        error: Exception,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        include_details: bool = False
    ) -> JSONResponse:
        """
        Create JSON error response for API
        
        Args:
            error: Exception that occurred
            status_code: HTTP status code
            include_details: Whether to include error details (for development)
            
        Returns:
            JSONResponse with error information
        """
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "message": ErrorHandler.sanitize_error_message(error, include_details),
                "error_type": type(error).__name__ if include_details else None
            }
        )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to catch all exceptions and generate user-friendly responses"""
    
    def __init__(self, app, include_error_details: bool = False):
        """
        Initialize error handling middleware
        
        Args:
            app: FastAPI application
            include_error_details: Whether to include error details in responses (for development)
        """
        super().__init__(app)
        self.include_error_details = include_error_details
        self.error_handler = ErrorHandler()
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and catch any exceptions
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from handler or error response
        """
        try:
            # Process request
            response = await call_next(request)
            return response
            
        except Exception as error:
            # Extract request context
            request_context = {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
            }
            
            # Try to extract phone number from request if it's a webhook
            user_phone = None
            if request.url.path == "/webhook" and request.method == "POST":
                try:
                    # Try to get phone from body (already consumed, so this won't work)
                    # We'll rely on the webhook handler to log phone numbers
                    pass
                except:
                    pass
            
            # Log error with context
            self.error_handler.log_error(
                error=error,
                request_context=request_context,
                user_phone=user_phone
            )
            
            # Determine status code
            if hasattr(error, 'status_code'):
                status_code = error.status_code
            elif isinstance(error, ValueError):
                status_code = status.HTTP_400_BAD_REQUEST
            elif isinstance(error, KeyError):
                status_code = status.HTTP_400_BAD_REQUEST
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Return error response
            return self.error_handler.create_error_response(
                error=error,
                status_code=status_code,
                include_details=self.include_error_details
            )


def generate_user_error_message(error_type: str, language: str = "en") -> str:
    """
    Generate user-friendly error message in specified language
    
    Args:
        error_type: Type of error (language_detection, query_processing, retrieval, generation, api)
        language: Language code for the message
        
    Returns:
        Localized error message
    """
    # Error messages by type and language
    error_messages = {
        "language_detection": {
            "en": "I couldn't detect your language. Please specify your preferred language or continue in English.",
            "hi": "मैं आपकी भाषा का पता नहीं लगा सका। कृपया अपनी पसंदीदा भाषा बताएं या अंग्रेजी में जारी रखें।",
            "ta": "உங்கள் மொழியைக் கண்டறிய முடியவில்லை. தயவுசெய்து உங்கள் விருப்ப மொழியைக் குறிப்பிடவும் அல்லது ஆங்கிலத்தில் தொடரவும்.",
        },
        "query_processing": {
            "en": "I couldn't understand your query. Could you please rephrase it? For example: 'Show me farmer schemes' or 'Education help for students'",
            "hi": "मैं आपके प्रश्न को समझ नहीं सका। क्या आप इसे दोबारा बता सकते हैं? उदाहरण: 'किसान योजनाएं दिखाएं' या 'छात्रों के लिए शिक्षा सहायता'",
            "ta": "உங்கள் கேள்வியைப் புரிந்து கொள்ள முடியவில்லை. தயவுசெய்து மீண்டும் சொல்ல முடியுமா? உதாரணம்: 'விவசாயி திட்டங்களைக் காட்டு' அல்லது 'மாணவர்களுக்கு கல்வி உதவி'",
        },
        "retrieval": {
            "en": "I'm having trouble finding relevant schemes right now. Please try again in a moment or try a different query.",
            "hi": "मुझे अभी प्रासंगिक योजनाएं खोजने में परेशानी हो रही है। कृपया कुछ देर बाद पुनः प्रयास करें या कोई अन्य प्रश्न पूछें।",
            "ta": "தற்போது தொடர்புடைய திட்டங்களைக் கண்டறிவதில் சிக்கல் உள்ளது. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும் அல்லது வேறு கேள்வி கேட்கவும்.",
        },
        "generation": {
            "en": "I'm having trouble generating a response right now. Please try again in a moment.",
            "hi": "मुझे अभी प्रतिक्रिया उत्पन्न करने में परेशानी हो रही है। कृपया कुछ देर बाद पुनः प्रयास करें।",
            "ta": "தற்போது பதிலை உருவாக்குவதில் சிக்கல் உள்ளது. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
        },
        "api": {
            "en": "I'm having trouble connecting to our services. Please try again in a moment.",
            "hi": "मुझे हमारी सेवाओं से कनेक्ट करने में परेशानी हो रही है। कृपया कुछ देर बाद पुनः प्रयास करें।",
            "ta": "எங்கள் சேவைகளுடன் இணைவதில் சிக்கல் உள்ளது. சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
        },
        "default": {
            "en": "Something went wrong. Please try again later or type 'help' for assistance.",
            "hi": "कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें या सहायता के लिए 'मदद' टाइप करें।",
            "ta": "ஏதோ தவறு நடந்தது. பிறகு மீண்டும் முயற்சிக்கவும் அல்லது உதவிக்கு 'உதவி' என தட்டச்சு செய்யவும்.",
        }
    }
    
    # Get message for error type and language
    messages_for_type = error_messages.get(error_type, error_messages["default"])
    
    # Fallback to English if language not available
    return messages_for_type.get(language, messages_for_type.get("en", "Something went wrong. Please try again later."))
