# utils/alert.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN") # Note: This might be redundant if ACCESS_TOKEN is loaded in app.py directly
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID") # Note: This might be redundant if PHONE_NUMBER_ID is loaded in app.py directly

def send_alert(to, message):
    """
    Sends an alert message via WhatsApp using Meta Cloud API.
    """
    # Using ACCESS_TOKEN and PHONE_NUMBER_ID from app.py's global scope is often better
    # or pass them as arguments if this utility is used independently.
    # For now, assuming they are loaded via dotenv for this file as well.
    current_access_token = os.getenv("ACCESS_TOKEN") # Use the same ACCESS_TOKEN as app.py
    current_phone_number_id = os.getenv("PHONE_NUMBER_ID") # Use the same PHONE_NUMBER_ID as app.py

    if not current_access_token or not current_phone_number_id:
        print("❌ WhatsApp API credentials not found for sending alert.")
        return None

    url = f"https://graph.facebook.com/v18.0/{current_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {current_access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }

    print(f"📢 Sending alert to {to}: {message}")
    response = requests.post(url, headers=headers, json=data)
    print("✅ Status:", response.status_code)
    print("📝 Response:", response.text)
    return response
