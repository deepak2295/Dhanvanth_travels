from flask import Flask, request
import requests
import json
import os
from utils.nlp import detect_intent
from utils.alert import send_alert
from utils.maps import get_route_details
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

user_sessions = {}

def send_message(to, message):
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
    requests.post(url, headers=headers, json=data)

@app.route("/")
def home():
    return "✅ WhatsApp bot server is running."

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json()

        try:
            message = data['entry'][0]['changes'][0]['value']['messages'][0]
            text = message['text']['body']
            sender = message['from']
            intent = detect_intent(text)

            if sender not in user_sessions:
                user_sessions[sender] = {"pickup": None, "drop": None}

            session = user_sessions[sender]

            if intent == "book_ride":
                send_message(sender, "🚕 Please share your pickup location.")
            elif intent == "pickup_location":
                session["pickup"] = text
                send_message(sender, "📍 Got it. Now share your drop location.")
            elif intent == "drop_location":
                session["drop"] = text
                if session["pickup"]:
                    route = get_route_details(session["pickup"], session["drop"])
                    send_message(sender, f"🛣 From {session['pickup']} to {session['drop']}")
                    send_message(sender, f"📏 Distance: {route['distance']}, ETA: {route['eta']}")
                    send_message(sender, "✅ Type 'confirm' to book the cab.")
                else:
                    send_message(sender, "Please share pickup location first.")
            elif intent == "confirm_ride":
                if session["pickup"] and session["drop"]:
                    send_message(sender, "🎉 Booking confirmed! Driver is on the way.")
                    send_alert(sender, "🚖 Live tracking will be shared soon.")
                else:
                    send_message(sender, "⚠️ Please provide both pickup and drop locations first.")
            else:
                send_message(sender, "👋 Hello! Type 'book' to start a cab booking.")
        except Exception as e:
            print(f"❌ Error: {e}")
        return "ok", 200

if __name__ == "__main__":
    app.run(port=5000)
