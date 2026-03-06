"""
Example: How to integrate Y-Connect pipeline with your Twilio/WhatsApp webhook

This shows how to use the pipeline in your FastAPI webhook handler
"""

from fastapi import FastAPI, Request
from app.yconnect_pipeline import process_whatsapp_message

app = FastAPI()


@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Example webhook handler for Twilio WhatsApp messages
    
    This is a simplified example showing how to integrate the Y-Connect pipeline
    """
    # Parse incoming webhook payload
    payload = await request.json()
    
    # Extract message and phone number from Twilio/WhatsApp payload
    # Adjust these based on your actual webhook structure
    try:
        # For WhatsApp Business API (Meta)
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])
        
        if messages:
            message = messages[0]
            incoming_msg = message.get("text", {}).get("body", "")
            phone_number = message.get("from", "")
            
            # Process through Y-Connect pipeline
            response_text = await process_whatsapp_message(
                user_message=incoming_msg,
                phone_number=phone_number
            )
            
            # Send response back (you'll need to implement this based on your setup)
            # await send_whatsapp_message(phone_number, response_text)
            
            return {"status": "success", "response": response_text}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# SIMPLE INTEGRATION FOR YOUR EXISTING main.py
# ============================================================================

"""
Add this to your existing main.py webhook handler:

from app.yconnect_pipeline import process_whatsapp_message

@app.post("/webhook")
async def webhook_message(request: Request):
    # ... your existing webhook verification code ...
    
    # Parse payload
    payload = await request.json()
    
    # Extract message and phone
    incoming_msg = extract_message_from_payload(payload)  # Your existing function
    phone_number = extract_phone_from_payload(payload)    # Your existing function
    
    # Process through Y-Connect pipeline (THIS IS THE ONLY LINE YOU NEED!)
    response_text = await process_whatsapp_message(incoming_msg, phone_number)
    
    # Send response back to user
    await send_whatsapp_reply(phone_number, response_text)  # Your existing function
    
    return {"status": "ok"}
"""
