import os
import requests
from dotenv import load_dotenv

# Load environment variables from your .env file
load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def send_template_message(to, template_name, language_code, params=None):
    """A dedicated function to send a specific WhatsApp template."""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    components = []
    if params:
        parameters = [{"type": "text", "text": p} for p in params]
        components.append({ "type": "body", "parameters": parameters })

    data = {
        "messaging_product": "whatsapp", "to": to, "type": "template",
        "template": {
            "name": template_name,
            "language": { "code": language_code },
            "components": components
        }
    }

    if not components:
        del data["template"]["components"]

    response = requests.post(url, headers=headers, json=data)

    print(f"--- Testing Language Code: '{language_code}' ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

if __name__ == "__main__":
    # --- EDITED AS REQUESTED ---
    # The new user's phone number is now set for the test.
    phone_to_test = "919618822953"
    template_to_test = "ride_confirmation_details"

    # --- RUNNING TESTS ---
    test_params = ["Test Customer", "123"]

    # Test 1: Using "en"
    send_template_message(phone_to_test, template_to_test, "en", params=test_params)

    print("\n" + "="*50 + "\n")

    # Test 2: Using "en_US"
    send_template_message(phone_to_test, template_to_test, "en_US", params=test_params)