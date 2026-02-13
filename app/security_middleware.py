"""Security middleware for Y-Connect WhatsApp Bot

Provides HTTPS enforcement, webhook signature validation, and secure headers.
"""

import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import get_settings

logger = logging.getLogger(__name__)


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS connections in production"""
    
    def __init__(self, app: ASGIApp, enforce_https: bool = True):
        """
        Initialize HTTPS enforcement middleware
        
        Args:
            app: ASGI application
            enforce_https: Whether to enforce HTTPS (should be True in production)
        """
        super().__init__(app)
        self.enforce_https = enforce_https
        
        if enforce_https:
            logger.info("HTTPS enforcement enabled")
        else:
            logger.warning("HTTPS enforcement disabled - only use in development!")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enforce HTTPS
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler or error response
        """
        # Skip HTTPS check for health check endpoint
        if request.url.path == "/health":
            return await call_next(request)
        
        # Check if HTTPS enforcement is enabled
        if self.enforce_https:
            # Check if request is over HTTPS
            # Note: In production behind a proxy, check X-Forwarded-Proto header
            is_https = (
                request.url.scheme == "https" or
                request.headers.get("X-Forwarded-Proto") == "https" or
                request.headers.get("X-Forwarded-Ssl") == "on"
            )
            
            if not is_https:
                logger.warning(
                    "HTTPS required but request received over HTTP",
                    extra={
                        "path": request.url.path,
                        "scheme": request.url.scheme,
                        "x_forwarded_proto": request.headers.get("X-Forwarded-Proto")
                    }
                )
                
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "HTTPS required",
                        "message": "This endpoint requires a secure HTTPS connection"
                    }
                )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app: ASGIApp):
        """
        Initialize secure headers middleware
        
        Args:
            app: ASGI application
        """
        super().__init__(app)
        logger.info("Secure headers middleware enabled")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Remove server header to avoid information disclosure
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


def validate_webhook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """
    Validate WhatsApp webhook signature
    
    Args:
        payload: Raw request body bytes
        signature: X-Hub-Signature-256 header value
        app_secret: WhatsApp app secret for HMAC verification
        
    Returns:
        True if signature is valid, False otherwise
        
    Raises:
        ValueError: If signature format is invalid
    """
    import hmac
    import hashlib
    
    if not signature:
        logger.warning("No signature provided in webhook request")
        return False
    
    # Signature format: sha256=<hash>
    if not signature.startswith("sha256="):
        logger.warning("Invalid signature format", extra={"signature": signature[:20]})
        raise ValueError("Invalid signature format - must start with 'sha256='")
    
    # Extract hash from signature
    expected_hash = signature[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC-SHA256
    computed_hash = hmac.new(
        app_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Compare hashes using constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(computed_hash, expected_hash)
    
    if not is_valid:
        logger.warning(
            "Webhook signature verification failed",
            extra={
                "expected_hash_prefix": expected_hash[:10] + "...",
                "computed_hash_prefix": computed_hash[:10] + "..."
            }
        )
    
    return is_valid


def get_secure_settings() -> dict:
    """
    Get security-related settings with validation
    
    Returns:
        Dictionary of security settings
        
    Raises:
        ValueError: If required security settings are missing
    """
    settings = get_settings()
    
    # Validate required security settings
    if not settings.whatsapp_app_secret or settings.whatsapp_app_secret == "":
        raise ValueError("WHATSAPP_APP_SECRET environment variable is required")
    
    if not settings.whatsapp_verify_token or settings.whatsapp_verify_token == "":
        raise ValueError("WHATSAPP_VERIFY_TOKEN environment variable is required")
    
    # Warn if using default/weak secrets in production
    if settings.is_production:
        if len(settings.whatsapp_app_secret) < 32:
            logger.warning(
                "WhatsApp app secret is too short for production use",
                extra={"length": len(settings.whatsapp_app_secret)}
            )
        
        if settings.whatsapp_verify_token == "your_verify_token_here":
            logger.error("Using default verify token in production - SECURITY RISK!")
            raise ValueError("Default verify token not allowed in production")
    
    return {
        "enforce_https": settings.is_production,
        "app_secret": settings.whatsapp_app_secret,
        "verify_token": settings.whatsapp_verify_token,
        "is_production": settings.is_production
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware (basic implementation)"""
    
    def __init__(self, app: ASGIApp, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiting middleware
        
        Args:
            app: ASGI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}  # Simple in-memory store (use Redis in production)
        
        logger.info(
            f"Rate limiting enabled: {max_requests} requests per {window_seconds} seconds"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client identifier (IP address or X-Forwarded-For)
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        
        # Simple rate limiting (in production, use Redis with sliding window)
        import time
        current_time = int(time.time())
        window_key = f"{client_ip}:{current_time // self.window_seconds}"
        
        # Increment request count
        if window_key not in self.request_counts:
            self.request_counts[window_key] = 0
        
        self.request_counts[window_key] += 1
        
        # Check if rate limit exceeded
        if self.request_counts[window_key] > self.max_requests:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "request_count": self.request_counts[window_key],
                    "path": request.url.path
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.max_requests} requests per {self.window_seconds} seconds"
                }
            )
        
        # Clean up old entries (simple cleanup)
        old_keys = [k for k in self.request_counts.keys() if not k.startswith(f"{client_ip}:{current_time // self.window_seconds}")]
        for key in old_keys[:100]:  # Clean up max 100 old entries per request
            del self.request_counts[key]
        
        return await call_next(request)


def setup_security_middleware(app, settings):
    """
    Setup all security middleware for the application
    
    Args:
        app: FastAPI application
        settings: Application settings
    """
    # Add HTTPS enforcement (only in production)
    app.add_middleware(
        HTTPSEnforcementMiddleware,
        enforce_https=settings.is_production
    )
    
    # Add secure headers
    app.add_middleware(SecureHeadersMiddleware)
    
    # Add rate limiting (adjust limits based on expected load)
    if settings.is_production:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=100,
            window_seconds=60
        )
    
    logger.info("Security middleware configured")
