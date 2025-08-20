from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, send_from_directory, session
import os
import sys
import json
import requests
import time
import threading
import random
import urllib.parse
import time
import traceback
import qrcode
import pytz
import smtplib
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_cors import CORS
from twilio.rest import Client
from email.message import EmailMessage

# Determine the absolute path to the directory containing app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Add the base directory to the system path
sys.path.append(BASE_DIR)

# --- Local Module Imports ---
from utils.nlp import detect_intent, correct_location, extract_ride_id
from utils.maps import get_route_details, get_readable_address
from utils.invoice import generate_invoice, send_invoice_pdf
from functools import wraps
from db import (
    manually_assign_driver, get_user, add_user, update_user, delete_user, get_all_users,
    list_available_car_types as get_available_car_types,
    get_available_driver_and_car, assign_driver_to_ride, get_all_drivers, get_driver_by_id, get_rate_for_car_type,
    add_driver, update_driver, delete_driver, update_driver_location,
    add_ride, update_ride, delete_ride, get_ride_by_id, complete_ride, get_all_rides, get_car_by_id,
    get_coupon, mark_coupon_used, get_all_coupons, add_coupon, update_coupon, delete_coupon,
    update_payment_status, get_latest_ride_id_by_phone, get_all_cars,
    add_car, update_car, delete_car,
    count_users, count_rides, count_drivers, count_vehicles,
    count_vehicles_on_ride, count_drivers_on_ride, calculate_revenue,
    count_pending_payments, get_revenue_by_period,
    get_all_locations, add_location, update_location, delete_location,
    get_all_pricing, add_pricing, update_pricing, delete_pricing,
    get_owner_by_email, get_prebooked_rides_for_assignment, get_rides_by_user_phone, update_user_name_by_phone,
    get_all_owner_phone_numbers, get_all_owners, add_owner, update_owner, delete_owner, get_owner_by_phone, get_setting, set_setting, connect, save_chat_session, get_chat_session, update_ride_status_and_time, complete_ride_and_free_resources,
    get_site_content, set_site_content, list_available_car_types, get_user_by_email, update_password_by_email, update_password_by_email_for_owner, get_available_cars_by_type, get_driver_by_phone, get_pricing_for_vehicle_type
)

# --- App Configuration ---
load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)
CORS(app)


def owner_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_phone' not in session:
            return jsonify({"error": "Unauthorized access"}), 401

        user_phone = session['user_phone']
        if user_phone not in get_all_owner_phone_numbers():
            return jsonify({"error": "Forbidden: Owner access required"}), 403

        return f(*args, **kwargs)
    return decorated_function

# --- Environment Variables & Session Storage ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")      
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
SESSION_TIMEOUT_SECONDS = 300
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
# In app.py, near the top

# Global variable to control the auto-assignment thread
AUTO_ASSIGNMENT_ENABLED = True
IST = pytz.timezone('Asia/Kolkata') 

# --- New Assignment API Endpoints ---
def generate_upi_string(amount, ride_id):
    """Generates a UPI payment string."""
    payee_vpa = "bejavadadeepak80-1@okhdfcbank"  # Your UPI ID
    payee_name = "Dhanvanth Tours and Travels"     # Your business name
    encoded_payee_name = urllib.parse.quote(payee_name)
    transaction_note = f"Payment for Ride #{ride_id}"
    encoded_transaction_note = urllib.parse.quote(transaction_note)

    upi_string = (
        f"upi://pay?pa={payee_vpa}&pn={encoded_payee_name}&am={amount:.2f}"
        f"&tn={encoded_transaction_note}&tr={ride_id}&cu=INR"
    )
    return upi_string

def generate_payment_qr_code(upi_string, ride_id):
    """Creates a QR code image from a UPI string and returns the file path."""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(upi_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        qr_dir = os.path.join(BASE_DIR, 'qrcodes')
        os.makedirs(qr_dir, exist_ok=True)
        filepath = os.path.join(qr_dir, f"ride_{ride_id}.png")
        img.save(filepath)
        return filepath
    except Exception as e:
        print(f"❌ Error generating QR code image: {e}")
        return None

def send_image_message(to, media_id, caption=""):
    """Sends an image message using a media ID."""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": caption
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"--- WhatsApp API Response for Image Message to {to} ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    print("-----------------------------------------------------")

# app.py

# app.py
def send_email_otp(recipient_email, otp):
    """Sends a six-digit OTP to the specified email address."""
    msg = EmailMessage()
    msg['Subject'] = 'Your Verification Code'
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient_email
    msg.set_content(f"Hello,\n\nYour OTP is: {otp}\nThis code is valid for 5 minutes.\n\nThank you!")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def upload_media_to_whatsapp(filepath, phone_number_id, access_token):
    """
    Uploads a media file to WhatsApp's servers using the requests library
    and returns the media ID.
    """
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/media"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print(f"--- ⬆️ Attempting to upload media from: {filepath} ---")
    
    try:
        with open(filepath, 'rb') as f:
            files = {
                'file': (os.path.basename(filepath), f, 'image/png'),
                'messaging_product': (None, 'whatsapp')
            }
            response = requests.post(url, headers=headers, files=files)
        
        response.raise_for_status()
        result = response.json()
        media_id = result.get('id')
        
        print(f"✅ Media uploaded successfully. Response: {result}")
        return media_id

    except requests.exceptions.RequestException as e:
        print(f"❌ CRITICAL ERROR during media upload: {e}")
        if e.response is not None:
            print(f"    Status Code: {e.response.status_code}")
            print(f"    Response Body: {e.response.text}")
        return None
    
# In app.py, add these new routes

# In app.py

# REPLACE this route
@app.route("/api/forgot_password/send_otp", methods=["POST"])
def forgot_password_send_otp():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required."}), 400

    # --- NEW LOGIC ---
    # Check if the email belongs to an owner OR a user.
    is_owner = get_owner_by_email(email) is not None
    is_user = get_user_by_email(email) is not None

    if not is_owner and not is_user:
        # Send a generic message to prevent email enumeration
        return jsonify({"message": "If an account with that email exists, an OTP has been sent."}), 200

    otp = random.randint(100000, 999999)
    session['reset_otp'] = otp
    session['reset_email'] = email
    session['reset_otp_timestamp'] = time.time()
    session['is_owner_reset'] = is_owner # Store whether the user is an owner

    send_email_otp(email, otp)
    return jsonify({"message": "If an account with that email exists, an OTP has been sent."}), 200


# REPLACE this route
# In app.py, this is the CORRECT version you should keep

@app.route("/api/forgot_password/reset_password", methods=["POST"])
def reset_password():
    if not session.get('reset_otp_verified'):
        return jsonify({"error": "Please verify your OTP first."}), 403

    data = request.json
    new_password = data.get("password")
    email = session.get('reset_email')
    is_owner = session.get('is_owner_reset', False)

    if not all([new_password, email]):
        return jsonify({"error": "Session expired or password missing."}), 400

    new_password_hash = generate_password_hash(new_password)
    
    success = False
    if is_owner:
        success = update_password_by_email_for_owner(email, new_password_hash)
    else:
        success = update_password_by_email(email, new_password_hash)
    
    if success:
        session.pop('reset_otp', None)
        session.pop('reset_email', None)
        session.pop('reset_otp_timestamp', None)
        session.pop('reset_otp_verified', None)
        session.pop('is_owner_reset', None)
        
        return jsonify({"message": "Password has been reset successfully! You can now log in."}), 200
    else:
        return jsonify({"error": "Failed to update password."}), 500

@app.route("/api/forgot_password/verify_otp", methods=["POST"])
def forgot_password_verify_otp():
    data = request.json
    otp_received = data.get("otp")
    
    stored_otp = session.get('reset_otp')
    otp_timestamp = session.get('reset_otp_timestamp', 0)

    if time.time() - otp_timestamp > 300: # 5 minute expiry
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
        
    if stored_otp and str(stored_otp) == str(otp_received):
        session['reset_otp_verified'] = True # Flag that OTP is correct for reset
        return jsonify({"message": "OTP verified successfully."}), 200
    else:
        return jsonify({"error": "Invalid OTP."}), 401

@app.route("/api/public/car_types", methods=["GET"])
def get_public_car_types():
    try:
        # This uses an existing function in your db.py to get unique, available car types
        car_types = list_available_car_types()
        return jsonify(car_types)
    except Exception as e:
        print(f"Error fetching car types: {e}")
        return jsonify({"error": "Could not retrieve car types"}), 500


@app.route('/api/assignment/status', methods=['GET'])
@owner_login_required
def get_assignment_status():
    enabled = get_setting('auto_assignment_enabled')
    return jsonify({"auto_assignment_enabled": enabled})

@app.route('/api/assignment/toggle', methods=['POST'])
@owner_login_required
def toggle_assignment():
    data = request.json
    enabled = data.get('enabled', False)
    set_setting('auto_assignment_enabled', enabled)
    return jsonify({"message": f"Auto-assignment is now {'ON' if enabled else 'OFF'}", "enabled": enabled})

@app.route('/api/unassigned_rides', methods=['GET'])
@owner_login_required
def get_unassigned_rides():
    # This requires a new function in db.py (we will add this next)
    rides = get_rides_by_user_phone(status='prebooked', unassigned_only=True)
    return jsonify(rides)

@app.route('/api/available_drivers', methods=['GET'])
@owner_login_required
def get_available_drivers_api():
    # This requires a new function in db.py (we will add this next)
    drivers = get_all_drivers(status='free')
    return jsonify(drivers)

@app.route('/api/available_cars', methods=['GET'])
@owner_login_required
def get_available_cars_api():
    # This requires a new function in db.py (we will add this next)
    cars = get_all_cars(status='free')
    return jsonify(cars)

# app.py

# app.py

@app.route('/api/assign_ride_manually', methods=['POST'])
@owner_login_required
def assign_ride_manually():
    data = request.json
    ride_id = data.get('ride_id')
    driver_id = data.get('driver_id')
    car_id = data.get('car_id')

    if not all([ride_id, driver_id, car_id]):
        return jsonify({"error": "Ride ID, Driver ID, and Car ID are required."}), 400

    # --- FIX: Check if ride is already assigned BEFORE doing anything ---
    ride_before_assign = get_ride_by_id(ride_id)
    if not ride_before_assign:
        return jsonify({"error": "Ride not found"}), 404
    
    # If a driver_id already exists, it means the ride was already assigned.
    # Stop here to prevent sending a duplicate notification.
    if ride_before_assign.get('driver_id') is not None:
        print(f"Ride {ride_id} is already assigned. Skipping duplicate assignment.")
        return jsonify({"message": "This ride has already been assigned."})

    # If the ride is not yet assigned, proceed.
    assign_driver_to_ride(ride_id, driver_id, car_id)

    # --- Notify User and Driver ---
    ride = get_ride_by_id(ride_id)
    driver = get_driver_by_id(driver_id)
    car = get_car_by_id(car_id)

    if ride and driver and car:
        # Send notification to the user
        send_message(ride['user_phone'],
                     f"🎉 Your ride (ID: {ride['id']}) has been assigned!\n"
                     f"Driver: {driver['name']} ({driver['phone']})\n"
                     f"Car: {car['model']} ({car['car_number']})")
        
        # Send notification to the driver
        driver_body_text = (
            f"📍 New Assigned Ride! (ID: {ride_id})\n\n"
            f"➡️ From: {ride['pickup']}\n"
            f"⬅️ To: {ride['destination']}\n"
            f"👤 Customer: {ride['user_phone']}"
        )
        buttons = [{"id": f"start_pickup_{ride_id}", "title": "Start Towards Pickup"}]
        send_button_message(driver['phone'], driver_body_text, buttons)

    return jsonify({"message": "Driver assigned successfully and notifications sent."})
# ==============================================================================
# --- WEB PORTAL & LOGIN API ---
# ==============================================================================

# app.py

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # --- NEW LOGIC ---
    # Step 1: Check if the credentials match an owner first.
    owner = get_owner_by_email(email)
    if owner and check_password_hash(owner['password_hash'], password):
        # If it's a valid owner, log them in and redirect to the admin dashboard.
        session["user_phone"] = owner['phone']
        session.permanent = True
        return jsonify({
            "message": "Owner login successful!",
            "redirect": url_for('dashboard_page')
        })

    # Step 2: If not an owner, check if the credentials match a regular user.
    user = get_user_by_email(email)
    if user and check_password_hash(user['password_hash'], password):
        # If it's a valid user, log them in and redirect to the user portal.
        session["user_phone"] = user['phone']
        session.permanent = True
        return jsonify({
            "message": "Login successful!",
            "redirect": url_for('user_dashboard_page')
        })

    # Step 3: If neither matches, the login fails.
    return jsonify({"error": "Invalid email or password."}), 401

@app.route("/api/register/send_otp", methods=["POST"])
def register_send_otp():
    data = request.json
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email is required."}), 400
    if get_user_by_email(email):
        return jsonify({"error": "This email address is already registered."}), 409

    otp = random.randint(100000, 999999)
    session['registration_otp'] = otp
    session['registration_email'] = email
    session['otp_timestamp'] = time.time()

    if send_email_otp(email, otp):
        return jsonify({"message": "An OTP has been sent to your email."}), 200
    else:
        return jsonify({"error": "Failed to send OTP email."}), 500

@app.route("/api/register/verify_otp", methods=["POST"])
def register_verify_otp():
    data = request.json
    otp_received = data.get("otp")
    stored_otp = session.get('registration_otp')
    otp_timestamp = session.get('otp_timestamp', 0)

    if time.time() - otp_timestamp > 300: # 5 minute expiry
        return jsonify({"error": "OTP has expired."}), 400
        
    if stored_otp and str(stored_otp) == str(otp_received):
        session['otp_verified'] = True
        return jsonify({"message": "OTP verified successfully."}), 200
    else:
        return jsonify({"error": "Invalid OTP."}), 401

@app.route("/api/register/complete_profile", methods=["POST"])
def complete_profile():
    if not session.get('otp_verified'):
        return jsonify({"error": "Please verify your OTP first."}), 403

    data = request.json
    phone = data.get("phone")
    name = data.get("name")
    password = data.get("password")
    email = session.get('registration_email')

    if not all([phone, name, password, email]):
        return jsonify({"error": "Missing required information."}), 400

    password_hash = generate_password_hash(password)
    user_id = add_user(phone, name, password_hash, email)

    if user_id:
        session.pop('registration_otp', None)
        session.pop('registration_email', None)
        session.pop('otp_timestamp', None)
        session.pop('otp_verified', None)
        return jsonify({"message": "Account created successfully! You can now log in."}), 201
    else:
        return jsonify({"error": "This phone number may already be in use."}), 409


# --- Route for the Login Page (default route) ---
@app.route("/")
@app.route("/login")
def login_page():
    return render_template("login.html")

# In app.py, add these new routes

@app.route("/api/owners", methods=["GET"])
@owner_login_required
def api_get_owners():
    owners = get_all_owners()
    return jsonify(owners)

@app.route("/api/owners", methods=["POST"])
@owner_login_required
def api_add_owner():
    data = request.json
    if not data.get('password'):
        return jsonify({"error": "Password is required"}), 400
    
    password_hash = generate_password_hash(data['password'])
    owner_id = add_owner(data['email'], data['phone'], data['name'], password_hash)
    
    if owner_id:
        return jsonify({"message": "Owner added successfully", "id": owner_id}), 201
    return jsonify({"error": "Failed to add owner. Email or phone may already exist."}), 400

@app.route("/api/owners/<int:owner_id>", methods=["PUT"])
@owner_login_required
def api_update_owner(owner_id):
    data = request.json
    if update_owner(owner_id, data['email'], data['phone'], data['name']):
        return jsonify({"message": "Owner updated successfully"}), 200
    return jsonify({"error": "Owner not found or failed to update"}), 404

@app.route("/api/owners/<int:owner_id>", methods=["DELETE"])
@owner_login_required
def api_delete_owner(owner_id):
    # Get the currently logged-in owner's details
    logged_in_owner_phone = session.get('user_phone')
    logged_in_owner = get_owner_by_phone(logged_in_owner_phone)

    # Prevent an owner from deleting their own account
    if logged_in_owner and logged_in_owner['id'] == owner_id:
        return jsonify({"error": "You cannot delete your own account while logged in."}), 403

    # If it's not their own account, proceed with deletion
    if delete_owner(owner_id):
        return jsonify({"message": "Owner deleted successfully"}), 200
    return jsonify({"error": "Owner not found or failed to delete"}), 404

# --- Route for the Main Admin Dashboard Page ---
@app.route("/dashboard")
def dashboard_page():
    # Check if a user is logged in
    if 'user_phone' not in session:
        return redirect(url_for('login_page'))

    # Check if the logged-in user is an owner
    user_phone = session['user_phone']
    all_owner_phones = get_all_owner_phone_numbers()
    if user_phone not in all_owner_phones:
        # If a regular user tries to access, redirect them to their own portal
        return redirect(url_for('user_dashboard_page'))

    # If all checks pass, show the dashboard
    return render_template('index.html')

# --- Routes for User Portal ---
@app.route("/user/login")
def user_login_page():
    # This route is now deprecated in favor of the unified /login, but we redirect just in case
    return redirect(url_for('login_page'))

@app.route("/user/dashboard")
def user_dashboard_page():
    # Protect this route: only logged-in users can see it
    if 'user_phone' not in session:
        return redirect(url_for('login_page'))
    return render_template("user_portal.html")

# ---------------------- User Portal API ----------------------

# app.py

@app.route("/api/user/details", methods=["GET"])
def get_user_details():
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user = get_user(session['user_phone'])
    if user:
        # --- FIX: Check for 'New User' OR the old 'John Doe' placeholder ---
        requires_name_update = user['name'] in ['John Doe', 'New User']
        
        return jsonify({
            "name": user['name'],
            "phone": user['phone'],
            "requires_name_update": requires_name_update
        })
        
    return jsonify({"error": "User not found"}), 404


@app.route("/api/user/update_name", methods=["POST"])
def update_user_name():
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_phone = session['user_phone']
    data = request.json
    new_name = data.get('name')

    if not new_name or len(new_name) < 2:
        return jsonify({"error": "A valid name is required"}), 400

    if update_user_name_by_phone(user_phone, new_name):
        return jsonify({"message": "Name updated successfully!"}), 200
    else:
        return jsonify({"error": "Failed to update name"}), 500
    
# app.py

# New admin endpoint to get a single content piece
@app.route("/api/site_content/<key>", methods=["GET"])
@owner_login_required
def api_get_site_content(key):
    content = get_site_content(key)
    return jsonify({"key": key, "value": content})

# New admin endpoint to save a single content piece
@app.route("/api/site_content", methods=["POST"])
@owner_login_required
def api_set_site_content():
    data = request.json
    key = data.get('key')
    value = data.get('value')
    if not key or value is None:
        return jsonify({"error": "Key and value are required"}), 400
    set_site_content(key, value)
    return jsonify({"message": f"Content for '{key}' saved successfully."})

# New public endpoint for the user portal to fetch content
@app.route("/api/public/site_content", methods=["GET"])
def api_get_public_site_content():
    # Fetch the content, using the correct keys
    about = get_site_content('about_us_content')
    contact = get_site_content('support_content')
    return jsonify({
        "about_us": about,
        "contact_us": contact
    })

# In app.py

@app.route("/api/user/rides", methods=["GET"])
def get_user_rides():
    # This route must be protected
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    # Get the phone number from the session of the currently logged-in user
    user_phone = session['user_phone']
    
    # Fetch rides specifically for that phone number
    rides = get_rides_by_user_phone(user_phone)
    
    return jsonify(rides)

# In app.py

# REPLACE your existing user_book_ride function with this one
# In app.py, REPLACE the entire user_book_ride function with this corrected version

VPA = "your-merchant-vpa@okhdfcbank"  # Your UPI ID (Virtual Payment Address)
PAYEE_NAME = "Dhanvanth Tours and Travels" # Your business name

# app.py

# In app.py, REPLACE your entire existing user_book_ride function with this one
# In app.py, ADD THIS ENTIRE FUNCTION

def send_template_message(to, template_name, params):
    """Sends a pre-approved WhatsApp message template with multiple parameters."""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Create the parameters list for the API call
    parameters = [{"type": "text", "text": p} for p in params]
    
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": { "code": "en" },
            "components": [{
                "type": "body",
                "parameters": parameters
            }]
        }
    }
    response = requests.post(url, headers=headers, json=data)
    
    print(f"--- WhatsApp API Response for Template '{template_name}' to {to} ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    print("-----------------------------------------------------------------")

@app.route("/api/user/book_ride", methods=["POST"])
def user_book_ride():
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_phone = session['user_phone']
    pickup = data.get('pickup')
    destination = data.get('destination')
    car_type = data.get('car_type')
    booking_date = data.get('booking_date')
    booking_time = data.get('booking_time')

    # 1. Get user's name for personalizing the template
    user = get_user(user_phone)
    user_name = user.get('name', 'Customer') if user else 'Customer'

    # 2. Validate locations and get route details
    route = get_route_details(pickup, destination)
    if 'error' in route:
        return jsonify({"error": route['error']}), 400

    # 3. Calculate fare using dynamic pricing
    try:
        distance_km = float(route['distance'].split()[0])
        pricing_rule = get_pricing_for_vehicle_type(car_type)
        price_per_km = float(pricing_rule['price_per_km']) if pricing_rule else 12.0 # Fallback rate
        fare = round(distance_km * price_per_km, 2)
        total_fare = fare + round(fare * 0.05, 2) # Add 5% tax
    except (ValueError, IndexError, TypeError):
        return jsonify({"error": "Could not calculate fare from route details."}), 500

    # 4. Add ride to the database
    ride_id = add_ride(
        user_phone=user_phone, pickup=pickup, destination=destination,
        distance=route['distance'], duration=route['duration'], fare=fare,
        car_id=None, driver_id=None, status='prebooked', payment_status='pending',
        start_time=f"{booking_date} {booking_time}:00", end_time=None, car_type=car_type
    )

    if not ride_id:
        return jsonify({"error": "Failed to save the ride in the database."}), 500

    # 5. Send the pre-approved template to reliably start the WhatsApp conversation
    # IMPORTANT: Ensure 'ride_confirmation_details' is approved and is the correct name
    template_name = "user_msg" 
    template_params = [user_name, str(ride_id)] # Pass name for {{1}} and ride_id for {{2}}
    send_template_message(user_phone, template_name, template_params)

    # 6. Create the payment link for the frontend
    payment_link = create_payment_link(user_phone, total_fare, ride_id)

    # 7. Return the response to the user portal frontend
    return jsonify({
        "message": "Your ride has been booked! Please check your WhatsApp for confirmation and future updates or send hi to +91 9071252575",
        "ride_id": ride_id,
        "payment_link": payment_link
    }), 201


# ADD this new function to app.py
@app.route("/api/user/rides/<int:ride_id>/set_cash", methods=["POST"])
def set_cash_payment(ride_id):
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Update payment status in the database to 'cash'
    if update_payment_status(ride_id, 'cash'):
        return jsonify({"message": "Payment method set to Cash."}), 200
    return jsonify({"error": "Could not update payment method."}), 500


@app.route("/api/user/logout", methods=["POST"])
def user_logout():
    session.pop('user_phone', None) # Clear the user's session
    return jsonify({"message": "Logout successful."}), 200

# Route to serve static files (CSS, JS, images)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# ---------------------- Dashboard API ----------------------
@app.route("/api/dashboard_stats", methods=["GET"])
@owner_login_required
def dashboard_stats():
    stats = {
        "total_customers": count_users(),
        "total_drivers": count_drivers(),
        "total_vehicles": count_vehicles(),
        "ongoing_rides": count_rides(status="ongoing"),
        "vehicles_on_ride": count_vehicles_on_ride(),
        "drivers_on_ride": count_drivers_on_ride(),
        "total_bookings": count_rides(),
        "pre_bookings": count_rides(status="prebooked"),
        "revenue": calculate_revenue(),
        "payment_pendings": count_pending_payments()
    }
    return jsonify(stats)

# Revenue trend API endpoint
@owner_login_required 
@app.route("/api/revenue_trend", methods=["GET"])
def revenue_trend():
    period = request.args.get('period', 'monthly') # Default to 'monthly'
    data = get_revenue_by_period(period)
    return jsonify(data)

# --- CRUD Endpoints for Dashboard Tabs ---

# Customers
@app.route("/api/customers", methods=["GET"])
@owner_login_required
def api_customers():
    customers = get_all_users()
    return jsonify(customers)

@app.route("/api/customers", methods=["POST"])
def add_customer_api():
    data = request.json
    dummy_password_hash = generate_password_hash("default_customer_password")
    user_id = add_user(data['phone'], data['name'], dummy_password_hash)
    if user_id:
        return jsonify({"message": "Customer added successfully", "id": user_id}), 201
    return jsonify({"error": "Failed to add customer or phone already exists"}), 400

@app.route("/api/customers/<int:user_id>", methods=["PUT"])
def update_customer_api(user_id):
    data = request.json
    if update_user(user_id, data['name'], data['phone']):
        return jsonify({"message": "Customer updated successfully"}), 200
    return jsonify({"error": "Customer not found or failed to update"}), 404

@app.route("/api/customers/<int:user_id>", methods=["DELETE"])
def delete_customer_api(user_id):
    if delete_user(user_id):
        return jsonify({"message": "Customer deleted successfully"}), 200
    return jsonify({"error": "Customer not found or failed to delete"}), 404

@app.route("/api/drivers", methods=["GET"])
def api_get_drivers():
    drivers = get_all_drivers()
    return jsonify(drivers)




@app.route("/api/drivers", methods=["POST"])
def add_driver_api():
    data = request.json
    driver_id = add_driver(data['name'], data['phone'], data.get('car_id'), data.get('status', 'free'))
    if driver_id:
        return jsonify({"message": "Driver added successfully", "id": driver_id}), 201
    return jsonify({"error": "Failed to add driver"}), 400

@app.route("/api/drivers/<int:driver_id>", methods=["PUT"])
def update_driver_api(driver_id):
    # Step 1: First, check if the driver actually exists in the database.
    if not get_driver_by_id(driver_id):
        return jsonify({"error": "Driver not found"}), 404

    # Step 2: If the driver exists, proceed with processing the update data.
    data = request.json
    car_id = data.get('car_id')
    if car_id == '':
        car_id = None

    # Step 3: Perform the update. We no longer need to check the return value
    # because we already confirmed the driver exists.
    update_driver(driver_id, data['name'], data['phone'], car_id, data['status'])
    
    # Step 4: Confidently return a success message.
    return jsonify({"message": "Driver updated successfully"}), 200

@app.route("/api/drivers/<int:driver_id>", methods=["DELETE"])
def delete_driver_api(driver_id):
    if delete_driver(driver_id):
        return jsonify({"message": "Driver deleted successfully"}), 200
    return jsonify({"error": "Driver not found or failed to delete"}), 404

# Vehicles (Cars)
@app.route("/api/vehicles", methods=["GET"])
def api_vehicles():
    vehicles = get_all_cars()
    return jsonify(vehicles)

@app.route("/api/vehicles", methods=["POST"])
def add_vehicle_api():
    data = request.json
    car_id = add_car(data['car_number'], data['model'], data['type'], data['rate'], data.get('status', 'free'))
    if car_id:
        return jsonify({"message": "Vehicle added successfully", "id": car_id}), 201
    return jsonify({"error": "Failed to add vehicle"}), 400

@app.route("/api/vehicles/<int:car_id>", methods=["PUT"])
def update_vehicle_api(car_id):
    data = request.json
    if update_car(car_id, data['car_number'], data['model'], data['type'], data['rate'], data['status']):
        return jsonify({"message": "Vehicle updated successfully"}), 200
    return jsonify({"error": "Vehicle not found or failed to update"}), 404

@app.route("/api/vehicles/<int:car_id>", methods=["DELETE"])
def delete_vehicle_api(car_id):
    if delete_car(car_id):
        return jsonify({"message": "Vehicle deleted successfully"}), 200
    return jsonify({"error": "Vehicle not found or failed to delete"}), 404

# Bookings (Rides)
@app.route("/api/bookings", methods=["GET"])
def api_bookings():
    bookings = get_all_rides()
    return jsonify(bookings)

@app.route("/api/bookings", methods=["POST"])
def add_booking_api():
    data = request.json
    try:
        ride_id = add_ride(
            user_phone=data['user_phone'],
            pickup=data['pickup'],
            destination=data['destination'],
            distance=data.get('distance', ''),
            duration=data.get('duration', ''),
            fare=float(data['fare']),
            car_id=data.get('car_id'),
            driver_id=data.get('driver_id'),
            status=data.get('status', 'pending'),
            payment_status=data.get('payment_status', 'pending'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            car_type=data.get('car_type')
        )
        if ride_id:
            return jsonify({"message": "Booking added successfully", "id": ride_id}), 201
        return jsonify({"error": "Failed to add booking"}), 400
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid data type: {e}"}), 400

@app.route("/api/bookings/<int:ride_id>", methods=["PUT"])
def update_booking_api(ride_id):
    # Step 1: First, check if the booking actually exists.
    existing_ride = get_ride_by_id(ride_id)
    if not existing_ride:
        return jsonify({"error": "Booking not found"}), 404

    # Step 2: If it exists, proceed with the update.
    data = request.json
    user_phone = data.get('user_phone', existing_ride['user_phone'])
    pickup = data.get('pickup', existing_ride['pickup'])
    destination = data.get('destination', existing_ride['destination'])
    distance = data.get('distance', existing_ride['distance'])
    duration = data.get('duration', existing_ride['duration'])
    fare = float(data.get('fare', existing_ride['fare']))
    car_id = data.get('car_id', existing_ride['car_id'])
    driver_id = data.get('driver_id', existing_ride['driver_id'])
    status = data.get('status', existing_ride['status'])
    payment_status = data.get('payment_status', existing_ride['payment_status'])
    start_time = data.get('start_time', existing_ride['start_time'])
    end_time = data.get('end_time', existing_ride['end_time'])

    # Step 3: Perform the update and assume success because we know the booking exists.
    update_ride(ride_id, user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time)
    
    return jsonify({"message": "Booking updated successfully"}), 200

@app.route("/api/bookings/<int:ride_id>", methods=["DELETE"])
def delete_booking_api(ride_id):
    if delete_ride(ride_id):
        return jsonify({"message": "Booking deleted successfully"}), 200
    return jsonify({"error": "Booking not found or failed to delete"}), 404

# New API endpoint to download invoice PDF
@app.route("/api/rides/<int:ride_id>/invoice", methods=["GET"])
def download_invoice(ride_id):
    ride = get_ride_by_id(ride_id)
    if not ride:
        print(f"DEBUG: Ride with ID {ride_id} not found.")
        return jsonify({"error": "Ride not found"}), 404

    # Reconstruct invoice data (or fetch from a stored invoice record if available)
    invoice_data = {
        "invoice_no": ride['id'],
        "customer_name": ride['customer_name'] if ride['customer_name'] else "N/A",
        "customer_address": "C-904, ALEMBIC URBAN FOREST, CHANNASANDRA", # Assuming a default address for dashboard invoices
        "trips": [{"description": f"{ride['pickup']} -> {ride['destination']}", "amount": ride['fare']}],
        "subtotal": ride['fare'],
        "discount": 0.0, # Assuming no discount for dashboard invoice re-generation
        "coupon_code": "",
        "tax": round(ride['fare'] * 0.05, 2),
        "total": round(ride['fare'] * 1.05, 2),
        "date": datetime.strptime(ride['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y') if ride['start_time'] else datetime.now().strftime('%d/%m/%Y')
    }

    filename = f"invoice_{ride_id}.pdf"
    invoice_dir = os.path.join(BASE_DIR, 'invoices')
    os.makedirs(invoice_dir, exist_ok=True) # Ensure directory exists
    filepath = generate_invoice(invoice_data, filename=filename)

    print(f"DEBUG: Attempting to serve invoice from directory: {invoice_dir}")
    print(f"DEBUG: Attempting to serve invoice file: {filename}")

    # Check if the file actually exists before sending
    if not os.path.exists(filepath):
        print(f"ERROR: Invoice file not found at {filepath}")
        return jsonify({"error": "Invoice file not found on server."}), 500

    # Set appropriate headers for PDF download
    response = send_from_directory(directory=invoice_dir, path=filename, as_attachment=True)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "application/pdf"
    return response


@app.route("/api/assigned_bookings", methods=["GET"])
def api_assigned_bookings():
    assigned_bookings = get_all_rides(status='ongoing')
    return jsonify(assigned_bookings)

# Manual Booking API Endpoint
@app.route("/api/manual_booking", methods=["POST"])
def api_manual_booking():
    data = request.json
    user_phone = data.get('user_phone')
    pickup = data.get('pickup')
    destination = data.get('destination')
    car_type = data.get('car_type')
    booking_date_str = data.get('booking_date')
    booking_time_str = data.get('booking_time')

    if not all([user_phone, pickup, destination, car_type, booking_date_str, booking_time_str]):
        return jsonify({"error": "Missing required booking details"}), 400

    try:
        booking_datetime_str = f"{booking_date_str} {booking_time_str}:00"
        booking_datetime = datetime.strptime(booking_datetime_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"error": "Invalid date or time format. Use YYYY-MM-DD and HH:MM"}), 400

    if booking_datetime < datetime.now() - timedelta(minutes=5): # Allow a small buffer for current time
        return jsonify({"error": "Booking time cannot be in the past."}), 400

    route = get_route_details(pickup, destination)
    if not route:
        return jsonify({"error": "Could not find a route for the given locations."}), 400

    distance_value = float(route["distance"].split()[0])
    # Fetch pricing dynamically or use a default if no specific pricing table is implemented
    pricing = get_all_pricing()
    car_rate = 12.0 # Default rate if no specific pricing found
    for p in pricing:
        if p['vehicle_type'].lower() == car_type.lower():
            car_rate = p['price_per_km']
            break
    fare = round(distance_value * car_rate, 2)

    # Calculate estimated end time for availability checks
    duration_minutes = float(route['duration'].split()[0])
    estimated_end_time = booking_datetime + timedelta(minutes=duration_minutes)

    driver = None
    car = None
    ride_status = 'prebooked' # Default to prebooked for manual bookings, assigned later

    current_time_plus_2_hours = datetime.now() + timedelta(hours=2)

    if booking_datetime <= current_time_plus_2_hours: # Immediate assignment if within 2 hours
        if get_setting('auto_assignment_enabled'): # Use the correct setting function
            driver, car = get_available_driver_and_car(car_type, session.get("start_time"), session.get("end_time"))
        else:
            driver, car = None, None # Manual mode is handled correctly
        if driver and car:
            ride_status = 'ongoing'
        else:
            # If immediate assignment fails, still book as prebooked, driver will be assigned by thread
            print(f"Manual booking for {booking_datetime_str}: No immediate driver/car available for {car_type}. Will be prebooked.")
            driver_id_for_db = None
            car_id_for_db = None
            return jsonify({"error": f"No immediate driver/car available for {car_type}. Booking saved as pre-booked. Driver will be assigned closer to ride time."}), 400 # Indicate pre-booked scenario
    else:
        # It's a true pre-booking, driver/car will be assigned by the background thread
        driver_id_for_db = None
        car_id_for_db = None

    # Use actual driver/car IDs if assigned immediately, else None for prebooked
    driver_id_for_db = driver['id'] if driver else None
    car_id_for_db = car['id'] if car else None

    ride_id = add_ride(
        user_phone=user_phone,
        pickup=pickup,
        destination=destination,
        distance=route['distance'],
        duration=route['duration'],
        fare=fare,
        car_id=car_id_for_db,
        driver_id=driver_id_for_db,
        status=ride_status,
        payment_status='pending', # Manual bookings start as pending payment
        start_time=booking_datetime_str,
        end_time=estimated_end_time.strftime('%Y-%m-%d %H:%M:%S'),
        car_type=data.get('car_type')
    )

    if ride_id:
        # Send confirmation message for manual booking
        if ride_status == 'ongoing':
            send_message(user_phone,
                         f"🎉 Your ride (ID: {ride_id}) is confirmed and assigned!\n"
                         f"Driver: {driver['name']}\n"
                         f"Phone: {driver['phone']}\n"
                         f"Car: {car['model']} ({car['car_number']})\n"
                         f"Starting now from {pickup} to {destination}.")
        else: # Prebooked
            send_message(user_phone,
                         f"✅ Your pre-booking (ID: {ride_id}) for {booking_datetime.strftime('%I:%M %p on %b %d, %Y')} is confirmed!\n"
                         f"We will assign a driver and car 2 hours before your ride time and send you the details.")

        return jsonify({"message": "Manual booking added successfully", "id": ride_id}), 201
    return jsonify({"error": "Failed to add manual booking"}), 400

# In app.py, replace the old assign_driver function with this one.
# Make sure 'manually_assign_driver' is imported from db at the top of the file.

@app.route('/api/assign_driver', methods=['POST'])
def assign_driver():
    data = request.json
    driver_id = data.get("driver_id")
    car_id = data.get("car_id")
    ride_id = data.get("ride_id")

    if not all([driver_id, car_id, ride_id]):
        return jsonify({"error": "Driver, Car, and Ride IDs are required."}), 400

    # This correctly calls the function from your db.py file
    result = manually_assign_driver(driver_id, car_id, ride_id)

    if result and "error" in result:
        return jsonify(result), 400
    
    return jsonify({"message": "Driver assigned successfully"})


# Pricing (Placeholder CRUD)
@app.route("/api/pricing", methods=["GET"])
@owner_login_required
def api_pricing():
    pricing = get_all_pricing()
    return jsonify(pricing)

@app.route("/api/pricing", methods=["POST"])
@owner_login_required
def add_pricing_api():
    data = request.json
    try:
        pricing_id = add_pricing(data['vehicle_type'], float(data['price_per_km']))
        if pricing_id:
            return jsonify({"message": "Pricing rule added successfully", "id": pricing_id}), 201
        return jsonify({"error": "Failed to add pricing rule"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

@app.route("/api/pricing/<int:pricing_id>", methods=["PUT"])
@owner_login_required
def update_pricing_api(pricing_id):
    data = request.json
    if update_pricing(pricing_id, data['vehicle_type'], float(data['price_per_km'])):
        return jsonify({"message": "Pricing rule updated successfully"}), 200
    return jsonify({"error": "Pricing rule not found or failed to update"}), 404

@app.route("/api/pricing/<int:pricing_id>", methods=["DELETE"])
@owner_login_required
def delete_pricing_api(pricing_id):
    if delete_pricing(pricing_id):
        return jsonify({"message": "Pricing rule deleted successfully"}), 200
    return jsonify({"error": "Pricing rule not found or failed to delete"}), 404

# Coupons
@app.route("/api/coupons", methods=["GET"])
def api_coupons():
    coupons = get_all_coupons()
    return jsonify(coupons)

@app.route("/api/coupons", methods=["POST"])
def add_coupon_api():
    data = request.json
    coupon_id = add_coupon(data['code'], float(data['discount']))
    if coupon_id:
        return jsonify({"message": "Coupon added successfully", "id": coupon_id}), 201
    return jsonify({"error": "Failed to add coupon (code might exist)"}), 400

@app.route("/api/coupons/<string:coupon_code>", methods=["PUT"])
def update_coupon_api(coupon_code):
    data = request.json
    used_status = 1 if str(data.get('used', '0')).lower() in ['true', '1'] else 0
    if update_coupon(coupon_code, float(data['discount']), used_status):
        return jsonify({"message": "Coupon updated successfully"}), 200
    return jsonify({"error": "Coupon not found or failed to update"}), 404

@app.route("/api/coupons/<string:coupon_code>", methods=["DELETE"])
def delete_coupon_api(coupon_code):
    if delete_coupon(coupon_code):
        return jsonify({"message": "Coupon deleted successfully"}), 200
    return jsonify({"error": "Coupon not found or failed to delete"}), 404

# Locations (Placeholder CRUD)
@app.route("/api/locations", methods=["GET"])
def api_locations():
    locations = get_all_locations()
    return jsonify(locations)

@app.route("/api/locations", methods=["POST"])
def add_location_api():
    data = request.json
    location_id = add_location(data['name'])
    if location_id:
        return jsonify({"message": "Location added successfully", "id": location_id}), 201
    return jsonify({"error": "Failed to add location"}), 400

@app.route("/api/locations/<int:location_id>", methods=["PUT"])
def update_location_api(location_id):
    data = request.json
    if update_location(location_id, data['name']):
        return jsonify({"message": "Location updated successfully"}), 200
    return jsonify({"error": "Location not found or failed to update"}), 404


@app.route("/api/locations/<int:location_id>", methods=["DELETE"])
def delete_location_api(location_id):
    if delete_location(location_id):
        return jsonify({"message": "Location deleted successfully"}), 200
    return jsonify({"error": "Location not found or failed to delete"}), 404

# In app.py, add this new route

@app.route('/api/send_bulk_message', methods=['POST'])
def send_bulk_message():
    # In a real app, you should add a check here to ensure only an owner is logged in
    
    data = request.json
    message = data.get('message')
    recipients = data.get('recipients', [])
    method = data.get('method')

    if not all([message, recipients, method]):
        return jsonify({"error": "Missing message, recipients, or method."}), 400

    success_count = 0
    failure_count = 0

    for phone in recipients:
        try:
            if method == 'whatsapp':
                # This uses your existing function to send WhatsApp messages
                send_message(phone, message)
                success_count += 1
            
            elif method == 'sms':
                # --- Real SMS Sending with Twilio ---
                try:
                    # The recipient number must be in E.164 format (e.g., +918519879924)
                    # The database number already includes the country code.
                    recipient_number = f"+{phone}"

                    message_instance = twilio_client.messages.create(
                        body=message,
                        from_=TWILIO_PHONE_NUMBER,
                        to=recipient_number
                    )
                    print(f"SMS sent to {recipient_number} with SID: {message_instance.sid}")
                    success_count += 1
                except Exception as e:
                    print(f"❌ Failed to send SMS to {phone}: {e}")
                    failure_count += 1

        except Exception as e:
            print(f"Failed to send message to {phone}: {e}")
            failure_count += 1
    
    response_message = (
        f"Message sending process completed. "
        f"Successfully sent to {success_count} recipient(s). "
        f"Failed for {failure_count} recipient(s)."
    )
    
    return jsonify({"message": response_message}), 200

# --- New: Background thread for pre-booking assignment ---

# app.py

def assign_prebooked_rides_periodically():
    while True:
        # Check for rides pre-booked to start within the next 2 hours
        if not get_setting('auto_assignment_enabled'):
            print("Auto-assignment is OFF. Skipping assignment check.")
            time.sleep(60) # Sleep for a minute and check again
            continue
        print("Auto-assignment is ON. Checking for rides to assign...")
        now = datetime.now()
        two_hours_from_now = now + timedelta(hours=2)

        # This line will now work correctly with the updated db.py function
        rides_to_assign = get_prebooked_rides_for_assignment(now, two_hours_from_now)

        for ride in rides_to_assign:
            # ... (rest of your existing logic is fine)
            print(f"Attempting to assign driver for pre-booked ride ID: {ride['id']}")

            # Calculate estimated end time for availability check
            duration_minutes = float(ride['duration'].split()[0]) if 'duration' in ride and ride['duration'] else 30 # Default to 30 min if not available
            estimated_end_time = datetime.strptime(ride['start_time'], '%Y-%m-%d %H:%M:%S') + timedelta(minutes=duration_minutes)

            driver, car = get_available_driver_and_car(ride["car_type"], ride["start_time"], ride["end_time"])


            if driver and car:
                # Assign driver and update ride status to ongoing
                assign_driver_to_ride(ride['id'], driver['id'], car['id'])

                print(f"Assigned driver {driver['name']} ({driver['phone']}) and car {car['model']} ({car['car_number']}) to ride {ride['id']}")

                # Send notification to user
                send_message(ride['user_phone'],
                             f"🎉 Your pre-booked ride (ID: {ride['id']}) is confirmed!\n"
                             f"Driver: {driver['name']}\n"
                             f"Phone: {driver['phone']}\n"
                             f"Car: {car['model']} ({car['car_number']})\n"
                             f"Your ride starts at {datetime.strptime(ride['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p on %b %d')}.")

                # --- START: MODIFIED DRIVER NOTIFICATION ---
                ride_id = ride['id']
                body_text = (
                    f"📍 New Pre-Booked Ride! (ID: {ride_id})\n\n"
                    f"➡️ From: {ride['pickup']}\n"
                    f"⬅️ To: {ride['destination']}\n"
                    f"👤 Customer: {ride['user_phone']}\n"
                    f"⏰ Scheduled for: {datetime.strptime(ride['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p')}"
                )
                buttons = [{"id": f"start_pickup_{ride_id}", "title": "Start Towards Pickup"}]
                send_button_message(driver['phone'], body_text, buttons)
                # --- END: MODIFIED DRIVER NOTIFICATION ---


            else:
                print(f"Could not find available driver/car for pre-booked ride {ride['id']} at {ride['start_time']}. Will retry later.")

        time.sleep(300) # Check every 5 minutes (300 seconds)

# In app.py, replace the old send_message function
def send_button_message(to, body_text, buttons):
    """
    Sends an interactive WhatsApp button message.
    buttons = [{"id": "btn1", "title": "Yes"}, {"id": "btn2", "title": "No"}]
    """
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}}
                    for btn in buttons
                ]
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"--- WhatsApp API Response for Button Message to {to} ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    print("---------------------------------------------------------")
    return response.json()

def can_send_freeform(user_phone):
    """
    Returns True if we can send a free-form message (inside 24h window),
    otherwise requires a template.
    """
    session_data = get_chat_session(user_phone)  # you already store chat sessions
    if not session_data or not session_data.get("last_interaction"):
        return False  # new user
    try:
        last_time = datetime.fromisoformat(session_data["last_interaction"])
        return (datetime.utcnow() - last_time).total_seconds() <= 24 * 3600
    except Exception:
        return False



def send_message(to, body, template_name=""):
    """
    Sends a WhatsApp message. Falls back to template if user is new/outside 24h.
    """
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

    if can_send_freeform(to):
        # Free-form text allowed
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body}
        }
    else:
        # Use approved template (must exist in Business Manager)
        data = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": body}]
                    }
                ]
            }
        }

    response = requests.post(url, headers=headers, json=data)
    print(f"--- WhatsApp API Response for send_message to {to} ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    print("-----------------------------------------------------")
    return response.json()


# REPLACE the old Razorpay function with this one
def create_payment_link(phone, amount, ride_id):
    """
    Generates a UPI payment link that can be opened by Google Pay or any other UPI app.
    """
    # !!! IMPORTANT !!!
    # Replace these with your actual UPI merchant details.
    payee_vpa = "bejavadadeepak80-1@okhdfcbank"  # Your UPI ID (Virtual Payment Address)
    payee_name = "Dhanvanth Tours and Travels"     # Your business name

    # Sanitize the payee name for the URL
    encoded_payee_name = urllib.parse.quote(payee_name)
    
    # Create the transaction note
    transaction_note = f"Payment for Ride #{ride_id}"
    encoded_transaction_note = urllib.parse.quote(transaction_note)

    # Construct the UPI URL
    # tr = transaction reference ID (must be unique)
    # am = amount (up to two decimal places)
    # cu = currency (INR)
    upi_url = (
        f"upi://pay?pa={payee_vpa}&pn={encoded_payee_name}&am={amount:.2f}"
        f"&tn={encoded_transaction_note}&tr={ride_id}&cu=INR"
    )
    
    return upi_url

# --- START: MODIFIED handle_payment_option FUNCTION ---
# app.py

# REPLACE the entire function with this one
# app.py

# app.py

# app.py

# app.py

# app.py

# app.py

def handle_payment_option(intent, session, phone):
    print(f"DEBUG: Handling payment option '{intent}' for {phone}")
    ride_id = session.get("ride_id")
    if not ride_id:
        print(f"DEBUG: ERROR - ride_id not found in session for {phone}.")
        return

    payment_status = "cash" if intent == "pay_cash" else "pending"
    update_payment_status(ride_id, payment_status)

    confirmation_type = session.pop('confirmation_type', 'FUTURE_PREBOOKING') 

    if confirmation_type == 'IMMEDIATE_ASSIGNED':
        driver = session.pop('assigned_driver_details', None)
        car = session.pop('assigned_car_details', None)
        if driver and car:
            send_message(phone,
                         f"🎉 Your ride (ID: {ride_id}) is confirmed and assigned!\n"
                         f"Driver: {driver['name']} ({driver['phone']})\n"
                         f"Car: {car['model']} ({car['car_number']})")
            driver_body_text = (f"📍 New Assigned Ride! (ID: {ride_id})\n\n➡️ From: {session['pickup']}\n⬅️ To: {session['destination']}\n👤 Customer: {phone}")
            buttons = [{"id": f"start_pickup_{ride_id}", "title": "Start Towards Pickup"}]
            send_button_message(driver['phone'], driver_body_text, buttons)

    elif confirmation_type == 'MANUAL_ASSIGNMENT':
        send_message(phone, f"✅ Your ride (ID: {ride_id}) is confirmed! An operator will assign a driver to you shortly and you will receive the details in another message.")

    else: # FUTURE_PREBOOKING
        # --- THIS IS THE CORRECTED LINE ---
        # It now correctly parses the timezone-aware date format from the session.
        ride_time_formatted = datetime.fromisoformat(session['start_time']).strftime('%I:%M %p on %b %d')
        
        send_message(phone,
                     f"✅ Your pre-booking is confirmed! We will assign a driver and car 2 hours before your ride time ({ride_time_formatted}) and send you the details.")

    # Online payment logic
    if intent == "pay_online":
        print(f"DEBUG: Entered 'pay_online' block for ride {ride_id}.")
        upi_string = session.get("upi_string")
        total_fare = session.get("invoice_total")

        if not all([upi_string, total_fare]):
            print(f"DEBUG: ERROR - Missing payment details for ride {ride_id}. UPI: {upi_string}, Fare: {total_fare}")
            send_message(phone, "Sorry, there was an error retrieving your payment details. Please contact support.")
            return

        # Attempt to send QR Code
        print(f"DEBUG: Attempting to generate and send QR code for ride {ride_id}.")
        qr_code_filepath = None
        try:
            qr_code_filepath = generate_payment_qr_code(upi_string, ride_id)
            if qr_code_filepath and os.path.exists(qr_code_filepath):
                print(f"DEBUG: QR code generated at {qr_code_filepath}")
                media_id = upload_media_to_whatsapp(qr_code_filepath, PHONE_NUMBER_ID, ACCESS_TOKEN)
                if media_id:
                    print(f"DEBUG: Media uploaded successfully. Media ID: {media_id}")
                    customer_name = get_user(phone).get('name', "Customer")
                    caption = f"Dear {customer_name},\nPlease scan the QR code to pay ₹{total_fare:.2f} for Ride #{ride_id}."
                    send_image_message(phone, media_id, caption=caption)
                else:
                    print(f"DEBUG: ERROR - Failed to upload media to WhatsApp for ride {ride_id}.")
            else:
                print(f"DEBUG: ERROR - Failed to generate QR code file for ride {ride_id}.")
        except Exception as e:
            print(f"DEBUG: CRITICAL ERROR during QR code process for ride {ride_id}: {e}")
        finally:
            if qr_code_filepath and os.path.exists(qr_code_filepath):
                os.remove(qr_code_filepath)

        # Always send the text link
        print(f"DEBUG: Sending text-based UPI link for ride {ride_id}.")
        send_message(phone, f"For your convenience, you can also pay using this direct link:\n{upi_string}")
        
    session["state"] = "ride_confirmed"
    save_chat_session(phone, session)
# app.py

# app.py

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Token mismatch", 403

    if request.method == "POST":
        data = request.get_json()
        try:
            value = data['entry'][0]['changes'][0]['value']
            if 'statuses' in value or 'messages' not in value:
                return "ok", 200

            msg = value['messages'][0]
            phone = msg['from']
            payload = msg.get('interactive', {}).get('button_reply', {}).get('id')
            text = msg.get('text', {}).get('body', '').strip()

            # --- 1. DRIVER WORKFLOW ---
            driver = get_driver_by_phone(phone)
            if driver:
                driver_intent = payload or text
                
                if driver_intent.startswith("start_pickup_"):
                    ride_id = extract_ride_id(driver_intent)
                    update_ride_status_and_time(ride_id, 'enroute_pickup', 'enroute_to_pickup_time', datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'))
                    ride = get_ride_by_id(ride_id)
                    send_message(ride['user_phone'], f"🚗 Your driver, {driver['name']}, is on the way!")
                    send_button_message(driver['phone'], "✅ Great! Please notify the user when you have arrived.", [{"id": f"reached_pickup_{ride_id}", "title": "I Have Arrived"}])
                
                elif driver_intent.startswith("reached_pickup_"):
                    ride_id = extract_ride_id(driver_intent)
                    update_ride_status_and_time(ride_id, 'at_pickup', 'at_pickup_time', datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'))
                    ride = get_ride_by_id(ride_id)
                    send_button_message(driver['phone'], "👍 You have arrived. Please confirm when the customer is in the car.", [{"id": f"start_trip_{ride_id}", "title": "Start Trip"}])
                    send_message(ride['user_phone'], "📍 Your driver has arrived at the pickup location.")

                elif driver_intent.startswith("start_trip_"):
                    ride_id = extract_ride_id(driver_intent)
                    update_ride_status_and_time(ride_id, 'in_progress', 'trip_start_time', datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'))
                    ride = get_ride_by_id(ride_id)
                    send_button_message(driver['phone'], "Please collect payment from the customer before ending the ride.", [{"id": f"payment_done_{ride_id}", "title": "Payment Done"}])
                    send_message(ride['user_phone'], f"▶️ Your ride to {ride['destination']} has started. Enjoy!")

                elif driver_intent.startswith("payment_done_"):
                    ride_id = extract_ride_id(driver_intent)
                    update_payment_status(ride_id, 'paid')
                    send_button_message(driver['phone'], "✅ Payment confirmed. You can now end the trip.", [{"id": f"end_ride_{ride_id}", "title": "End Ride"}])

                elif driver_intent.startswith("end_ride_"):
                    ride_id = extract_ride_id(driver_intent)
                    complete_ride_and_free_resources(ride_id, datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'))
                    ride = get_ride_by_id(ride_id)
                    send_message(driver['phone'], f"🏁 Ride #{ride_id} completed successfully. Thank you!")
                    send_message(ride['user_phone'], f"Thank you for riding with us! Your trip to {ride['destination']} is complete.")
                
                return "ok", 200

            # --- 2. CUSTOMER WORKFLOW ---
            user = get_user(phone)
            session = get_chat_session(phone) or {"state": "awaiting_intent"}

            # --- 2a. New User Registration ---
            if not user:
                if session.get("state") not in ["awaiting_new_user_name", "awaiting_new_user_email", "awaiting_email_otp"]:
                    session["state"] = "awaiting_new_user_name"
                    send_message(phone, "👋 Welcome to Dhanvanth Tours & Travels! To get started, please tell me your full name.")
                
                elif session.get("state") == "awaiting_new_user_name":
                    user_name = text.strip()
                    if len(user_name) < 2:
                        send_message(phone, "That name seems too short. Please enter a valid full name.")
                    else:
                        session["new_user_name"] = user_name
                        session["state"] = "awaiting_new_user_email"
                        send_message(phone, f"Thanks, {user_name}! Now, what's your email address? We'll send a code to verify it.")
                
                elif session.get("state") == "awaiting_new_user_email":
                    email = text.strip().lower()
                    if "@" not in email or "." not in email:
                        send_message(phone, "That doesn't look like a valid email. Please enter a correct email address.")
                    elif get_user_by_email(email):
                        send_message(phone, "This email is already registered. Please try a different one.")
                    else:
                        otp = random.randint(100000, 999999)
                        if send_email_otp(email, otp):
                            session.update({"new_user_email": email, "otp": otp, "otp_timestamp": time.time(), "state": "awaiting_email_otp"})
                            send_message(phone, f"We've sent a 6-digit verification code to {email}. Please enter it here.")
                        else:
                            send_message(phone, "Sorry, I couldn't send a verification email right now. Please try again.")
                
                elif session.get("state") == "awaiting_email_otp":
                    user_otp = text.strip()
                    if time.time() - session.get("otp_timestamp", 0) > 300:
                        session["state"] = "awaiting_new_user_email"
                        send_message(phone, "That OTP has expired. Let's try again. What's your email address?")
                    elif str(session.get("otp")) == user_otp:
                        add_user(phone=phone, name=session["new_user_name"], email=session["new_user_email"], password_hash=generate_password_hash("default_password_from_bot"))
                        send_message(phone, "✅ Verification successful! Your account is now registered.")
                        session = {"state": "awaiting_intent"}
                        send_button_message(phone, "What would you like to do next?", [{"id": "book_ride", "title": "Book Ride"}, {"id": "check_booking", "title": "My Booking"}, {"id": "fare_info", "title": "Fare Info"}])
                    else:
                        send_message(phone, "That code is incorrect. Please check your email and try again.")
                
                save_chat_session(phone, session)
                return "ok", 200

            # --- 2b. Existing User Conversation Flow ---
            intent = detect_intent(text, session.get("state", ""))
            if payload:
                if payload.startswith("car_"): intent = "car_selection"
                elif payload.startswith("date_"): intent = "booking_date_option_selection"
                else: intent = payload

            # --- Main Menu & General Intents ---
            if intent == "greeting" or (intent == "unknown" and session.get("state") == "awaiting_intent"):
                send_button_message(phone, "👋 Welcome back. What would you like to do?", [{"id": "book_ride", "title": "Book Ride"}, {"id": "check_booking", "title": "My Booking"}, {"id": "fare_info", "title": "Fare Info"}])
                session["state"] = "awaiting_intent"

            elif intent == "check_booking":
                rides = get_rides_by_user_phone(user_phone=phone)
                message = "You have no recent bookings." if not rides else "Here are your last two bookings:\n"
                for ride in rides:
                    ride_time = ride['start_time'].strftime('%d %b, %Y at %I:%M %p')
                    message += f"\n--- Ride ID: {ride['id']} ---\nFrom: {ride['pickup']}\nTo: {ride['destination']}\nDate: {ride_time}\nStatus: {ride['status'].title()}\n"
                send_message(phone, message)
                send_button_message(phone, "What would you like to do next?", [{"id": "book_ride", "title": "Book Another Ride"}, {"id": "fare_info", "title": "Fare Info"}])
                session["state"] = "awaiting_intent"

            elif intent == "fare_info":
                pricing_rules = get_all_pricing()
                message = "Fare information is currently unavailable." if not pricing_rules else "Our current per-kilometer rates are:\n"
                for rule in pricing_rules:
                    message += f"\n- *{rule['vehicle_type'].title()}*: ₹{rule['price_per_km']:.2f}/km"
                message += "\n\n*Note: Final fare may include taxes and tolls.*"
                send_message(phone, message)
                send_button_message(phone, "What would you like to do next?", [{"id": "book_ride", "title": "Book Ride"}, {"id": "check_booking", "title": "My Booking"}])
                session["state"] = "awaiting_intent"

            # --- Booking Flow ---
            elif intent == "book_ride":
                session["state"] = "awaiting_booking_date_option"
                send_button_message(phone, "🗓️ When would you like to book your ride?", [{"id": "date_today", "title": "Today"}, {"id": "date_tomorrow", "title": "Tomorrow"}])

            elif intent == "booking_date_option_selection" and session.get("state") == "awaiting_booking_date_option":
                today = datetime.now(IST).date()
                session["booking_date"] = today.isoformat() if payload == "date_today" else (today + timedelta(days=1)).isoformat()
                session["state"] = "awaiting_booking_time"
                send_message(phone, "⏰ What time? (e.g., 10:30 PM or 22:30)")
            
            elif session.get("state") == "awaiting_booking_time":
                try:
                    booking_time_str = text.upper()
                    booking_time = datetime.strptime(booking_time_str, "%I:%M %p").time() if "AM" in booking_time_str or "PM" in booking_time_str else datetime.strptime(booking_time_str, "%H:%M").time()
                    booking_datetime = IST.localize(datetime.strptime(session["booking_date"], "%Y-%m-%d").replace(hour=booking_time.hour, minute=booking_time.minute))
                    
                    if booking_datetime < datetime.now(IST):
                        booking_datetime += timedelta(days=1)
                        session["booking_date"] = booking_datetime.date().isoformat()

                    if booking_datetime < datetime.now(IST):
                        send_message(phone, "❌ That time is still in the past. Please enter a future time.")
                    else:
                        session["start_time"] = booking_datetime.isoformat()
                        session["state"] = "awaiting_pickup"
                        send_message(phone, "📍 Please send detailed pickup location./n example: /n > send your current location directly /n > building number, street name, locality")
                except ValueError:
                    send_message(phone, "❌ Invalid time format. Please use HH:MM AM/PM or 24-hour format.")

            elif session.get("state") == "awaiting_pickup":
                session["pickup"] = correct_location(text)
                session["state"] = "awaiting_destination"
                send_message(phone, "🏁 please provide detailed drop location /n example: /n building number, street name, locality")
            
            elif session.get("state") == "awaiting_destination":
                session["destination"] = correct_location(text)
                car_types = get_available_car_types()
                if not car_types:
                    send_message(phone, "🚧 No cars available right now.")
                    session["state"] = "awaiting_intent"
                else:
                    session["state"] = "awaiting_car_type"
                    pricing_info = "\n".join([f"- {p['vehicle_type'].title()}: ₹{p['price_per_km']:.2f}/km" for p in get_all_pricing() if p['vehicle_type'] in car_types])
                    btns = [{"id": f"car_{c.lower()}", "title": c.title()} for c in car_types]
                    send_button_message(phone, f"🚗 Choose your car type:\n\n{pricing_info}", btns)

            elif intent == "car_selection" and session.get("state") == "awaiting_car_type":
                car_type = payload.replace("car_", "")
                pricing = get_pricing_for_vehicle_type(car_type)
                if not pricing:
                    send_message(phone, "Sorry, pricing is not available for that car type.")
                else:
                    route = get_route_details(session.get("pickup"), session.get("destination"))
                    if 'error' in route:
                        send_message(phone, route['error'])
                    else:
                        distance_value = float(route["distance"].split()[0])
                        fare = round(distance_value * float(pricing['price_per_km']), 2)
                        session.update({"car_type": car_type, "route_distance": distance_value, "route_duration": route.get('duration'), "fare": fare, "state": "awaiting_confirmation"})
                        confirmation_text = f"Great! Here are your ride details:\n\n🚗 **Vehicle Type:** {car_type.title()}\n🛣️ **Route:** {session.get('pickup')} -> {session.get('destination')}\n📏 **Distance:** {route.get('distance')}\n⏱️ **Duration:** {route.get('duration')}\n💰 **Estimated Fare:** ₹{fare:.2f}\n\nPlease confirm to proceed."
                        send_message(phone, confirmation_text)
                        send_button_message(phone, "✅ Confirm booking?", [{"id": "final_confirm_ride", "title": "Confirm"}])

            elif intent == "final_confirm_ride" and session.get("state") == "awaiting_confirmation":
                booking_datetime = datetime.fromisoformat(session["start_time"])
                is_auto_assign_enabled = get_setting('auto_assignment_enabled') # Use the correct setting function

                now_in_ist = datetime.now(IST)
                cutoff_time = (now_in_ist.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).replace(hour=4)
                is_immediate_ride = booking_datetime < cutoff_time

                ride_status, driver_id_for_db, car_id_for_db = "prebooked", None, None
                
                if is_immediate_ride:
                    if is_auto_assign_enabled:
                        driver, car = get_available_driver_and_car(session.get("car_type"), session.get("start_time"), (booking_datetime + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"))
                        if driver and car:
                            ride_status, driver_id_for_db, car_id_for_db = "assigned", driver['id'], car['id']
                            session.update({'confirmation_type': 'IMMEDIATE_ASSIGNED', 'assigned_driver_details': driver, 'assigned_car_details': car})
                        else:
                            send_message(phone, "We're sorry, but all of our cabs are currently busy. Please try again later.")
                            session["state"] = "awaiting_intent"
                            save_chat_session(phone, session)
                            return "ok", 200
                    else: # Manual Mode
                        session['confirmation_type'] = 'MANUAL_ASSIGNMENT'
                else: # Future Pre-Booking
                    session['confirmation_type'] = 'FUTURE_PREBOOKING'
                
                final_car_id = car_id_for_db if car_id_for_db is not None else session.get("specific_car_id")

                ride_id = add_ride(user_phone=phone, pickup=session["pickup"], destination=session["destination"], distance=f'{session["route_distance"]} km', duration=session["route_duration"], fare=session["fare"], car_id=final_car_id, driver_id=driver_id_for_db, status=ride_status, payment_status="pending", start_time=booking_datetime.strftime('%Y-%m-%d %H:%M:%S'), end_time=None, car_type=session.get("car_type"))
                
                total_fare = float(session['fare']) * 1.05
                session.update({"upi_string": generate_upi_string(total_fare, ride_id), "ride_id": ride_id, "invoice_total": total_fare, "state": "awaiting_payment_option"})
                send_button_message(phone, "💳 Choose your payment mode:", [{"id": "pay_online", "title": "Online"}, {"id": "pay_cash", "title": "Cash"}])

            elif intent in ["pay_online", "pay_cash"] and session.get("state") == "awaiting_payment_option":
                handle_payment_option(intent, session, phone)

            # --- Fallback for unrecognized input ---
            else:
                current_state = session.get("state")
                if "awaiting" in current_state:
                    expected_input = current_state.replace("awaiting_", "").replace("_", " ")
                    send_message(phone, f"I'm sorry, I didn't understand that. I'm currently waiting for the {expected_input}. Could you please provide it?")
                else:
                    send_button_message(phone, "I'm not sure how to help with that. Here are the main options:", [{"id": "book_ride", "title": "Book Ride"}, {"id": "check_booking", "title": "My Booking"}, {"id": "fare_info", "title": "Fare Info"}])

            save_chat_session(phone, session)
            return "ok", 200

        except Exception:
            traceback.print_exc()
            return "ok", 200


if __name__ == "__main__":
    # Start the pre-booking assignment thread
    assignment_thread = threading.Thread(target=assign_prebooked_rides_periodically)
    assignment_thread.daemon = True # Allow the main program to exit even if this thread is running
    assignment_thread.start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)