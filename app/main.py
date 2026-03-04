"""Main FastAPI application for Y-Connect WhatsApp Bot"""

from fastapi import FastAPI, Request, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response, JSONResponse
from twilio.twiml.messaging_response import MessagingResponse
from contextlib import asynccontextmanager
from typing import Dict, Any
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.config import get_settings
from app.logging_config import setup_logging, get_logger
from app.webhook_handler import WebhookHandler
from app.error_handler import ErrorHandlingMiddleware
from app.security_middleware import (
    HTTPSEnforcementMiddleware,
    SecureHeadersMiddleware,
    RateLimitMiddleware,
    get_secure_settings
)
from app.metrics import app_info, metrics_tracker
from app.alerting import alert_manager
from app.health_check import health_checker, HealthStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Get settings
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        app_name=settings.app_name,
        app_env=settings.app_env,
        log_level=settings.log_level
    )
    
    logger = get_logger(__name__)
    
    # Validate security settings
    try:
        security_settings = get_secure_settings()
        logger.info(
            "Security settings validated",
            extra={
                "enforce_https": security_settings["enforce_https"],
                "is_production": security_settings["is_production"]
            }
        )
    except ValueError as e:
        logger.error(f"Security settings validation failed: {e}")
        raise
    
    # Startup
    logger.info(
        "Starting Y-Connect WhatsApp Bot",
        extra={
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "version": "0.1.0",
            "https_enforced": settings.is_production
        }
    )
    
    # Set application info for metrics
    app_info.info({
        'version': '0.1.0',
        'environment': settings.app_env,
        'app_name': settings.app_name
    })
    
    yield
    
    # Shutdown
    logger.info("Shutting down Y-Connect WhatsApp Bot")


# Create FastAPI application
app = FastAPI(
    title="Y-Connect WhatsApp Bot",
    description="WhatsApp bot for discovering Indian government schemes",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add security middleware (HTTPS enforcement, secure headers, rate limiting)
    app.add_middleware(
        HTTPSEnforcementMiddleware,
        enforce_https=settings.is_production
    )
    
    app.add_middleware(SecureHeadersMiddleware)
    
    # Add rate limiting in production
    if settings.is_production:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=100,
            window_seconds=60
        )
    
    # Add error handling middleware
    app.add_middleware(
        ErrorHandlingMiddleware,
        include_error_details=settings.is_development
    )


@app.get("/")
async def root():
    """Root endpoint"""
    settings = get_settings()
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint
    
    Checks:
    - PostgreSQL database connectivity
    - Redis connectivity
    - Vector store connectivity
    
    Returns:
        200 if all components are healthy
        503 if any component is unhealthy
    """
    health_status = await health_checker.check_all()
    
    # Return 503 if unhealthy
    if health_status["status"] == HealthStatus.UNHEALTHY.value:
        return JSONResponse(
            content=health_status,
            status_code=503
        )
    
    return health_status


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint
    
    Returns:
        Prometheus-formatted metrics
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Initialize webhook handler
webhook_handler = WebhookHandler()


@app.get("/webhook")
async def webhook_verification(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """
    Webhook verification endpoint for WhatsApp Business API
    
    This endpoint is called by WhatsApp during webhook setup to verify
    that the webhook URL is valid and controlled by the application owner.
    
    Args:
        mode: Verification mode (should be "subscribe")
        token: Verification token that must match configured token
        challenge: Challenge string to echo back
        
    Returns:
        Plain text response with challenge string if verification succeeds
        
    Raises:
        HTTPException: 403 if verification fails
    """
    logger = get_logger(__name__)
    
    logger.info(
        "Webhook verification request",
        extra={
            "mode": mode,
            "token_provided": token is not None,
            "challenge_provided": challenge is not None
        }
    )
    
    # Verify webhook
    challenge_response = webhook_handler.verify_webhook(mode, token, challenge)
    
    # Return challenge as plain text
    return PlainTextResponse(content=challenge_response, status_code=200)


@app.post("/webhook")
async def webhook_message(request: Request):
    """
    Webhook endpoint for incoming WhatsApp messages
    
    This endpoint receives webhook events from WhatsApp Business API
    when users send messages to the bot.
    
    Args:
        request: FastAPI request object containing webhook payload
        
    Returns:
        JSON response acknowledging receipt
        
    Raises:
        HTTPException: 403 if signature verification fails
    """
    logger = get_logger(__name__)
    
    # Track request
    tracker = metrics_tracker.track_request(endpoint="/webhook", method="POST")
    is_error = False
    
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Get signature from header
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        # Verify signature
        if not webhook_handler.verify_signature(body, signature):
            logger.warning("Webhook signature verification failed")
            metrics_tracker.track_error(error_type="signature_verification", component="webhook")
            is_error = True
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature"
            )
        
        # Parse JSON payload
        try:
            payload: Dict[str, Any] = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            metrics_tracker.track_error(error_type="payload_parsing", component="webhook")
            is_error = True
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        # Handle message
        response = await webhook_handler.handle_message(payload)
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}")
        metrics_tracker.track_error(error_type="unexpected", component="webhook")
        is_error = True
        raise
    
    finally:
        # Finish tracking request
        tracker.finish_request(endpoint="/webhook", method="POST")
        
        # Track error for alerting
        alert_manager.track_request_error(is_error)

# --- TWILIO SANDBOX TESTING ENDPOINT ---

@app.post("/twilio")
async def twilio_webhook(request: Request):
    """
    Temporary webhook endpoint for Twilio Sandbox testing.
    Bypasses Meta's signature verification and parses Form Data.
    """
    logger = get_logger(__name__)
    
    try:
        # Twilio sends form data, NOT JSON
        form_data = await request.form()
        incoming_msg = form_data.get('Body', '')
        sender_number = form_data.get('From', '')
        
        logger.info(f"Twilio Sandbox received: '{incoming_msg}' from {sender_number}")

        # TEMPORARY: Echo response to prove it works
        # Later, you will pass 'incoming_msg' to your AI/RAG logic here
        twiml_response = MessagingResponse()
        reply = twiml_response.message()
        reply.body(f"Namaste from Y-Connect! We received your message: '{incoming_msg}'.")

        return Response(content=str(twiml_response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"Twilio webhook error: {e}")
        raise HTTPException(status_code=500, detail="Twilio processing failed")


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
