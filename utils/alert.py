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
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
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
