# utils/alert.py

import requests
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN") 
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID") 

def send_alert(to, message):
    """
    Sends an alert message via WhatsApp using Meta Cloud API.
    """
    current_access_token = os.getenv("ACCESS_TOKEN") 
    current_phone_number_id = os.getenv("PHONE_NUMBER_ID") 

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
