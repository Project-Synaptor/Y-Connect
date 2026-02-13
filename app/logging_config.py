"""Logging configuration for Y-Connect WhatsApp Bot"""

import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that anonymizes sensitive data"""
    
    def __init__(self, *args, app_name: str = "y-connect", app_env: str = "development", **kwargs):
        super().__init__(*args, **kwargs)
        self.app_name = app_name
        self.app_env = app_env
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to log record and anonymize PII"""
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["app"] = self.app_name
        log_record["environment"] = self.app_env
        
        # Anonymize phone numbers if present (multiple field names)
        phone_fields = ["phone_number", "from_phone", "to_phone", "phone"]
        for field in phone_fields:
            if field in log_record:
                log_record[field] = self._anonymize_phone(log_record[field])
        
        # Hash session IDs if present
        if "session_id" in log_record and isinstance(log_record["session_id"], str):
            # Only show first 16 characters of session ID
            log_record["session_id"] = log_record["session_id"][:16] + "..."
        
        # Redact PII from message content if present
        if "message" in log_record and isinstance(log_record["message"], str):
            log_record["message"] = self._redact_pii_from_text(log_record["message"])
        
        if "text_content" in log_record and isinstance(log_record["text_content"], str):
            log_record["text_content"] = self._redact_pii_from_text(log_record["text_content"])

    @staticmethod
    def _anonymize_phone(phone: str) -> str:
        """Anonymize phone number by showing only last 4 digits"""
        if not phone or not isinstance(phone, str):
            return "****"
        
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        if len(cleaned) < 4:
            return "****"
        
        return f"****{cleaned[-4:]}"
    
    @staticmethod
    def _redact_pii_from_text(text: str) -> str:
        """Redact PII patterns from text"""
        import re
        
        # Redact phone numbers
        text = re.sub(r'\+?\d{10,15}', '[PHONE]', text)
        
        # Redact email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Redact Aadhaar numbers
        text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR]', text)
        
        # Redact PAN numbers
        text = re.sub(r'\b[A-Z]{5}\d{4}[A-Z]\b', '[PAN]', text)
        
        return text


def setup_logging(app_name: str = "y-connect", app_env: str = "development", log_level: str = "INFO") -> None:
    """Configure application logging"""
    
    # Get log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Use JSON formatter for production, simple formatter for development
    is_production = app_env.lower() == "production"
    if is_production:
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s",
            timestamp=True,
            app_name=app_name,
            app_env=app_env
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set log levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "environment": app_env
        }
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module"""
    return logging.getLogger(name)
