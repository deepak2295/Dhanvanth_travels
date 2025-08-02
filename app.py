from flask import Flask, request, jsonify, render_template, redirect, url_for, Response, send_from_directory, session
import os
import sys
import json
import requests
import time
import threading
import random
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_cors import CORS
from twilio.rest import Client

# Determine the absolute path to the directory containing app.py
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# Add the base directory to the system path
sys.path.append(BASE_DIR)

# --- Local Module Imports ---
from utils.nlp import detect_intent, correct_location, extract_ride_id
from utils.maps import get_route_details, get_readable_address
from utils.invoice import generate_invoice, upload_media_to_whatsapp, send_invoice_pdf
from functools import wraps
from db import (
    get_user, add_user, update_user, delete_user, get_all_users,
    list_available_car_types as get_available_car_types,
    get_available_driver_and_car, assign_driver_to_ride, get_all_drivers, get_driver_by_id,
    add_driver, update_driver, delete_driver, update_driver_location,
    add_ride, update_ride, delete_ride, get_ride_by_id, complete_ride, get_all_rides,
    get_coupon, mark_coupon_used, get_all_coupons, add_coupon, update_coupon, delete_coupon,
    update_payment_status, get_latest_ride_id_by_phone, get_all_cars,
    add_car, update_car, delete_car,
    count_users, count_rides, count_drivers, count_vehicles,
    count_vehicles_on_ride, count_drivers_on_ride, calculate_revenue,
    count_pending_payments, get_revenue_by_period,
    get_all_locations, add_location, update_location, delete_location,
    get_all_pricing, add_pricing, update_pricing, delete_pricing,
    get_owner_by_email, get_prebooked_rides_for_assignment, get_rides_by_user_phone, update_user_name_by_phone,
    get_all_owner_phone_numbers, get_all_owners, add_owner, update_owner, delete_owner, get_owner_by_phone
)

# --- App Configuration ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.urandom(24)
CORS(app)
load_dotenv()

def owner_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_phone' not in session:
            return jsonify({"error": "Unauthorized access"}), 401
        
        # Check if the logged-in user is an owner
        user_phone = session['user_phone']
        all_owner_phones = get_all_owner_phone_numbers() # Assumes this db function is imported
        if user_phone not in all_owner_phones:
            return jsonify({"error": "Forbidden: Owner access required"}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# --- Environment Variables & Session Storage ---
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
RAZORPAY_BASE_URL = "https://api.razorpay.com/v1/payment_links"
RAZORPAY_API_KEY = os.getenv("RAZORPAY_API_KEY")
RAZORPAY_API_SECRET = os.getenv("RAZORPAY_API_SECRET")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
user_sessions = {}
SESSION_TIMEOUT_SECONDS = 300

# ==============================================================================
# --- WEB PORTAL & LOGIN API ---
# ==============================================================================

@app.route("/api/send_otp", methods=["POST"])
def send_otp():
    data = request.json
    phone_10_digit = data.get("phone")

    if not phone_10_digit or not phone_10_digit.isdigit() or len(phone_10_digit) != 10:
        return jsonify({"error": "Please enter a valid 10-digit phone number."}), 400

    full_phone = "91" + phone_10_digit
    user = get_user(full_phone)
    all_owner_phones = get_all_owner_phone_numbers()
    is_registered_owner = full_phone in all_owner_phones

    if not user and not is_registered_owner:
        return jsonify({"error": "This phone number is not registered with us."}), 404

    otp = random.randint(100000, 999999)
    user_sessions[full_phone] = {'otp': otp, 'otp_timestamp': time.time()}

    # --- Send OTP via Twilio SMS ---
    try:
        message_body = f"Your Dhanvanth Portal login OTP is: {otp}"
        recipient_number = f"+{full_phone}"

        message_instance = twilio_client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=recipient_number
        )
        print(f"OTP SMS sent to {recipient_number} with SID: {message_instance.sid}")
    except Exception as e:
        print(f"❌ Failed to send OTP SMS to {full_phone}: {e}")
        # Optionally, you could return an error if the SMS fails
        # return jsonify({"error": "Failed to send OTP. Please try again later."}), 500
    return jsonify({"message": "An OTP has been sent to your phone number."}), 200

# ... (The rest of your app.py code remains the same) ...

@app.route("/api/verify_otp", methods=["POST"])
def verify_otp():
    """
    Verifies the OTP and redirects to the appropriate dashboard (owner or user).
    """
    data = request.json
    phone_10_digit = data.get("phone")
    otp_received = data.get("otp")

    if not phone_10_digit or not otp_received:
        return jsonify({"error": "Phone number and OTP are required"}), 400

    full_phone = "91" + phone_10_digit

    if full_phone not in user_sessions or 'otp' not in user_sessions[full_phone]:
        return jsonify({"error": "Please request an OTP first."}), 400

    user_session_data = user_sessions[full_phone]
    stored_otp = user_session_data['otp']
    otp_timestamp = user_session_data['otp_timestamp']

    if time.time() - otp_timestamp > 300:  # 5 minute expiry
        del user_sessions[full_phone]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400

    if str(stored_otp) == str(otp_received):
        # OTP Correct. Log user in.
        session['user_phone'] = full_phone
        session.permanent = True

        # Clean up OTP data from memory
        del user_sessions[full_phone]

        # Determine if the user is an owner and set the redirect path
        all_owner_phones = get_all_owner_phone_numbers()
        if full_phone in all_owner_phones:
            # This is an owner, redirect to the main dashboard
            return jsonify({
                "message": "Owner login successful! Redirecting...",
                "redirect": url_for('dashboard_page')
            })
        else:
            # This is a regular user, redirect to the user portal
            return jsonify({
                "message": "Login successful! Redirecting...",
                "redirect": url_for('user_dashboard_page')
            })
    else:
        return jsonify({"error": "Invalid OTP."}), 401

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

@app.route("/api/user/details", methods=["GET"])
def get_user_details():
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = get_user(session['user_phone'])
    if user:
         # The name 'John Doe' is a placeholder from init_db.py
        requires_name_update = user['name'] == 'John Doe'
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
@app.route("/api/user/book_ride", methods=["POST"])
def user_book_ride():
    if 'user_phone' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user_phone = session['user_phone']
    pickup = data.get('pickup')
    destination = data.get('destination')
    
    # 1. Validate locations and get route details
    route = get_route_details(pickup, destination)
    if 'error' in route:
        return jsonify({"error": route['error']}), 400

    # 2. Calculate fare (example calculation)
    try:
        distance_km = float(route['distance'].split()[0])
        fare = round(distance_km * 12.0, 2) # Assuming a rate of Rs. 12/km
        tax = round(fare * 0.05, 2)
        total_fare = fare + tax
    except (ValueError, IndexError):
        return jsonify({"error": "Could not calculate fare from route details."}), 500

    # 3. Add ride to the database with 'pending' payment status
    ride_id = add_ride(
        user_phone=user_phone,
        pickup=pickup,
        destination=destination,
        distance=route['distance'],
        duration=route['duration'],
        fare=fare,
        car_id=data.get('car_id'), # Assuming car_id might be passed, can be None
        driver_id=None, # Driver assigned later
        status='prebooked',
        payment_status='pending',
        start_time=f"{data.get('booking_date')} {data.get('booking_time')}:00",
    )

    if not ride_id:
        return jsonify({"error": "Failed to save the ride in the database."}), 500

    # 4. Create Razorpay payment link
    payment_link = create_payment_link(user_phone, total_fare)

    # 5. Return success response with the payment link
    return jsonify({
        "message": "Your ride has been booked successfully! Please complete the payment.",
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

# Drivers
@app.route("/api/drivers", methods=["GET"])
def api_drivers():
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
    data = request.json
    if update_driver(driver_id, data['name'], data['phone'], data.get('car_id'), data['status']):
        return jsonify({"message": "Driver updated successfully"}), 200
    return jsonify({"error": "Driver not found or failed to update"}), 404

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
            end_time=data.get('end_time')
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
    data = request.json
    existing_ride = get_ride_by_id(ride_id)
    if not existing_ride:
        return jsonify({"error": "Booking not found"}), 404

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

    if update_ride(ride_id, user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time):
        return jsonify({"message": "Booking updated successfully"}), 200
    return jsonify({"error": "Booking not found or failed to update"}), 404

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
        driver, car = get_available_driver_and_car(car_type, booking_datetime_str, estimated_end_time.strftime('%Y-%m-%d %H:%M:%S'))
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
        end_time=estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')
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


# Pricing (Placeholder CRUD)
@app.route("/api/pricing", methods=["GET"])
def api_pricing():
    pricing = get_all_pricing()
    return jsonify(pricing)

@app.route("/api/pricing", methods=["POST"])
def add_pricing_api():
    data = request.json
    pricing_id = add_pricing(data['vehicle_type'], data['model'], float(data['price_per_km']))
    if pricing_id:
        return jsonify({"message": "Pricing added successfully", "id": pricing_id}), 201
    return jsonify({"error": "Failed to add pricing"}), 400

@app.route("/api/pricing/<int:pricing_id>", methods=["PUT"])
def update_pricing_api(pricing_id):
    data = request.json
    if update_pricing(pricing_id, data['vehicle_type'], data['model'], float(data['price_per_km'])):
        return jsonify({"message": "Pricing updated successfully"}), 200
    return jsonify({"error": "Pricing not found or failed to update"}), 404

@app.route("/api/pricing/<int:pricing_id>", methods=["DELETE"])
def delete_pricing_api(pricing_id):
    if delete_pricing(pricing_id):
        return jsonify({"message": "Pricing deleted successfully"}), 200
    return jsonify({"error": "Pricing not found or failed to delete"}), 404

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

def assign_prebooked_rides_periodically():
    while True:
        # Check for rides pre-booked to start within the next 2 hours
        now = datetime.now()
        two_hours_from_now = now + timedelta(hours=2)

        rides_to_assign = get_prebooked_rides_for_assignment(now, two_hours_from_now)

        for ride in rides_to_assign:
            print(f"Attempting to assign driver for pre-booked ride ID: {ride['id']}")

            # Calculate estimated end time for availability check
            duration_minutes = float(ride['duration'].split()[0]) if 'duration' in ride and ride['duration'] else 30 # Default to 30 min if not available
            estimated_end_time = datetime.strptime(ride['start_time'], '%Y-%m-%d %H:%M:%S') + timedelta(minutes=duration_minutes)

            driver, car = get_available_driver_and_car(
                ride['car_type'],
                ride['start_time'],
                estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')
            )

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
        "text": {"body": message}
    }
    # Send the request to Meta's server
    response = requests.post(url, headers=headers, json=data)

    # --- NEW: Print the response from Meta ---
    print(f"--- WhatsApp API Response for {to} ---")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")
    print("---------------------------------------")

def send_button_message(to, body_text, buttons):
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
            "action": {"buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}} for b in buttons
            ]}
        }
    }
    requests.post(url, headers=headers, json=data)

def create_payment_link(phone, amount):
    auth = (RAZORPAY_API_KEY, RAZORPAY_API_SECRET)
    payload = {
        "amount": int(amount * 100),
        "currency": "INR",
        "accept_partial": False,
        "description": "Cab fare payment",
        "customer": {"contact": phone},
        "notify": {"sms": False, "email": False},
        "reminder_enable": True
    }
    res = requests.post(RAZORPAY_BASE_URL, auth=auth, json=payload)
    if res.status_code == 200:
        return res.json().get("short_url")
    return None

# --- START: MODIFIED handle_payment_option FUNCTION ---
def handle_payment_option(intent, session, phone):
    driver = session.get("driver")
    car = session.get("car")
    user_phone = phone
    ride_id = session.get("ride_id")

    if not ride_id:
        print("Error: ride_id not found in session for handle_payment_option")
        return

    # This part remains the same
    pickup_location = session.get("pickup")
    destination_location = session.get("destination")
    customer_name = get_user(phone)['name'] if get_user(phone) else "Customer"
    payment_link_placeholder = session.get("payment_link")

    # --- Logic for Online Payment ---
    if intent == "pay_online":
        if payment_link_placeholder:
            payment_message = (
                f"Dear Mr. {customer_name},\n\n"
                "This is a humble reminder for payment of fees to start your Trademark Registration process.\n\n"
                f"1) Click on BLUE Link to PAY: {payment_link_placeholder}\n\n"
                "2) Please send me the payment receipt once payment is done.\n\n"
                "Regards,\n"
                "Abhijit Shirpurkar\n"
                "Mobile: 09096989992\n\n"
                "Please TYPE and Send:\n"
                "CALL for a Call Back\n"
                "DONE after Payment"
            )
            send_message(phone, payment_message)
        update_payment_status(ride_id, "pending")
        session["state"] = "ride_confirmed"

        # Ride Confirmation for User & Driver
        if session["ride_status"] == "ongoing" and driver and car:
            send_message(phone, f"🚖 Ride confirmed!\nDriver: {driver['name']}\nPhone: {driver['phone']}\nCar: {car['model']} ({car['car_number']})")

            # --- START: New Driver Notification (Online Payment) ---
            driver_body_text = (
                f"📍 New Ride Assigned! (ID: {ride_id})\n\n"
                f"➡️ From: {pickup_location}\n"
                f"⬅️ To: {destination_location}\n"
                f"📞 Customer: {user_phone}\n"
                "💳 Payment: Online (Pending)"
            )
            buttons = [{"id": f"start_pickup_{ride_id}", "title": "Start Towards Pickup"}]
            send_button_message(driver['phone'], driver_body_text, buttons)
            # --- END: New Driver Notification (Online Payment) ---

        elif session["ride_status"] == "prebooked":
             send_message(phone, f"✅ Your pre-booking is confirmed! We will assign a driver and car 2 hours before your ride time ({datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p on %b %d')}) and send you the details.")

    # --- Logic for Cash Payment ---
    elif intent == "pay_cash":
        update_payment_status(ride_id, "cash")
        session["state"] = "ride_confirmed"

        if session["ride_status"] == "ongoing" and driver and car:
            fare = session.get("invoice_total", session.get("fare", 0))
            send_message(phone, f"🚖 Ride confirmed!\nDriver: {driver['name']}\nPhone: {driver['phone']}\nCar: {car['model']} ({car['car_number']})")

            # --- START: New Driver Notification (Cash Payment) ---
            driver_body_text = (
                f"📍 New Ride Assigned! (ID: {ride_id})\n\n"
                f"➡️ From: {pickup_location}\n"
                f"⬅️ To: {destination_location}\n"
                f"📞 Customer: {user_phone}\n"
                f"💰 Payment: Collect ₹{fare} in CASH"
            )
            buttons = [{"id": f"start_pickup_{ride_id}", "title": "Start Towards Pickup"}]
            send_button_message(driver['phone'], driver_body_text, buttons)
            # --- END: New Driver Notification (Cash Payment) ---

        elif session["ride_status"] == "prebooked":
            send_message(phone, f"✅ Your pre-booking is confirmed! We will assign a driver and car 2 hours before your ride time ({datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p on %b %d')}) and send you the details.")
# --- END: MODIFIED handle_payment_option FUNCTION ---


@app.route("/razorpay_webhook", methods=["POST"])
def razorpay_webhook():
    data = request.get_json()
    if data.get("event") == "payment_link.paid":
        customer_contact = data["payload"]["payment"]["entity"]["contact"]
        
        # --- START: FIX for Phone Number Format ---
        print(f"DEBUG: Raw contact from Razorpay: {customer_contact}")
        
        # Remove the '+' to match the format in the database
        normalized_contact = customer_contact.replace('+', '')
        print(f"DEBUG: Normalized contact for DB search: {normalized_contact}")
        
        # Use the normalized number for the database query
        ride_id = get_latest_ride_id_by_phone(normalized_contact)
        # --- END: FIX for Phone Number Format ---

        if ride_id:
            update_payment_status(ride_id, "paid")
            # Send confirmation to the normalized number
            send_message(normalized_contact, "✅ Payment received successfully. Thank you!")
            send_message(normalized_contact, "🎉 Ride is fully paid. Enjoy your journey!")
        else:
            print(f"Warning: Could not find ride for phone {normalized_contact} to update payment status.")
            
    return "OK", 200

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
            if 'messages' not in value:
                return "ok", 200

            msg = value['messages'][0]
            phone = msg['from']
            name = value['contacts'][0]['profile']['name']

            payload = None
            text = ""
            if msg.get('type') == 'interactive':
                payload = msg['interactive']['button_reply']['id']
                text = msg['interactive']['button_reply']['title']
            elif msg.get('text'):
                text = msg.get('text', {}).get('body', '').strip()

            # --- START: Enhanced Debugging ---
            print(f"\n--- NEW WEBHOOK REQUEST at {datetime.now()} ---")
            print(f"DEBUG: From Phone: {phone}")
            print(f"DEBUG: Message Text: '{text}'")
            print(f"DEBUG: Message Payload: {payload}")
            # --- END: Enhanced Debugging ---

            # --- START: MODIFIED DRIVER RIDE COMPLETION LOGIC ---
            all_drivers = get_all_drivers()
            driver_phones = {d['phone']: d['id'] for d in all_drivers}

            if phone in driver_phones:
                # Driver interaction logic was here. It has been removed.
                # The system will still SEND messages to drivers, but it will no longer
                # process incoming messages FROM them.
                print(f"DEBUG: Message from a driver phone ({phone}). Ignoring as per new logic.")
                return "ok", 200
            # --- END: MODIFIED DRIVER RIDE COMPLETION LOGIC ---
            # --- Handle Location Messages ---
            if msg.get('type') == 'location':
                latitude = msg['location']['latitude']
                longitude = msg['location']['longitude']
                readable_address = get_readable_address(latitude, longitude)

                session = user_sessions.get(phone, {}) # Get session safely

                if not readable_address:
                    send_message(phone, "Sorry, I couldn't resolve that location to an address. Please type your pickup location instead.")
                    return "ok", 200

                # If user sends a location at the start OR when we're asking for a pickup,
                # assume it's the pickup location and move to the next step.
                current_state = session.get("state")
                if current_state in [None, "new_user", "awaiting_intent", "awaiting_pickup"]:
                    session["pickup"] = readable_address
                    session["state"] = "awaiting_destination"
                    user_sessions[phone] = session
                    send_message(phone, f"📍 Got it! Your pickup location is: **{readable_address}**.\n\nNow, please send your destination.")
                else:
                    # Handle cases where a location is sent unexpectedly (e.g., when asked for car type)
                    send_message(phone, f"Thanks for sharing your location, but I'm currently waiting for other information. Let's continue with the current step.")

                return "ok", 200


            # --- START: NEW USER REGISTRATION LOGIC ---
            user = get_user(phone)
            session = user_sessions.get(phone, {}) # Get session safely

            if not user:
                # Check if we are already waiting for a name
                if session.get("state") == "awaiting_new_user_name":
                    # User has sent their name
                    user_name = text.strip()
                    if len(user_name) < 2:
                        send_message(phone, "That name seems too short. Please enter a valid name.")
                        return "ok", 200

                    # Add user to the database with a dummy password
                    dummy_password_hash = generate_password_hash("default_password_from_bot")
                    add_user(phone, user_name, dummy_password_hash)

                    send_message(phone, f"Thanks, {user_name}! You are now registered.")
                    # Now, present the main menu
                    send_button_message(phone, "👋 Welcome to RideBot. What would you like to do? ", [
                        {"id": "book_ride", "title": "Book Ride"},
                        {"id": "check_booking", "title": "My Booking"},
                        {"id": "fare_info", "title": "Fare Info"}
                    ])
                    # Update session state
                    session["state"] = "awaiting_intent"
                    user_sessions[phone] = session
                    return "ok", 200
                else:
                    # This is a brand new user. Ask for their name.
                    session["state"] = "awaiting_new_user_name"
                    user_sessions[phone] = session
                    send_message(phone, "👋 Welcome to RideBot! I see you're new here. What's your name?")
                    return "ok", 200
            # --- END: NEW USER REGISTRATION LOGIC ---


            if phone not in user_sessions:
                user_sessions[phone] = {"state": "awaiting_intent"}
            session = user_sessions[phone]

            intent = detect_intent(text, session.get("state", ""))
            print(f"DEBUG: Detected intent: {intent} for text: '{text}' in state: {session.get('state')}") # Debug print
            if payload:
                if payload.startswith("car_"): intent = "car_selection"
                elif payload.startswith("date_"): intent = "booking_date_option_selection" # New intent for date option
                else: intent = payload

            # Handle greeting intent specifically or any unknown intent from a user in the 'awaiting_intent' state
            if intent == "greeting" or (intent == "unknown" and session.get("state") == "awaiting_intent"):
                send_button_message(phone, "👋 Welcome to RideBot. What would you like to do? ", [
                    {"id": "book_ride", "title": "Book Ride"},
                    {"id": "check_booking", "title": "My Booking"},
                    {"id": "fare_info", "title": "Fare Info"}
                ])
                session["state"] = "awaiting_intent" # Reset state after greeting
                return "ok", 200

            # Only proceed if intent is NOT 'unknown' AND not a greeting (already handled)
            # Or if it's an unknown intent but the state is expecting a specific input
            if intent == "book_ride":
                session.update({"state": "awaiting_booking_date_option"})
                send_button_message(phone, "🗓️ When would you like to book your ride?", [
                    {"id": "date_today", "title": "Today"},
                    {"id": "date_tomorrow", "title": "Tomorrow"},
                    {"id": "date_pick", "title": "Pick a Date"}
                ])

            elif intent == "booking_date_option_selection" and session["state"] == "awaiting_booking_date_option":
                today = datetime.now().date()
                if payload == "date_today":
                    session["booking_date"] = today.isoformat()
                    session["state"] = "awaiting_booking_time"
                    send_message(phone, "⏰ What time would you like your ride? (e.g., 10:30 AM, 14:00)")
                elif payload == "date_tomorrow":
                    tomorrow = today + timedelta(days=1)
                    session["booking_date"] = tomorrow.isoformat()
                    session["state"] = "awaiting_booking_time"
                    send_message(phone, "⏰ What time would you like your ride? (e.g., 10:30 AM, 14:00)")
                elif payload == "date_pick":
                    session["state"] = "awaiting_specific_date"
                    send_message(phone, "📅 Please enter the date for your ride (YYYY-MM-DD):")
                else:
                    send_message(phone, "Please choose a valid option for the date.")

            elif session["state"] == "awaiting_specific_date":
                try:
                    booking_date = datetime.strptime(text, "%Y-%m-%d").date()
                    if booking_date < datetime.now().date():
                        send_message(phone, "❌ You cannot book a ride in the past. Please enter a future date (YYYY-MM-DD):")
                    else:
                        session["booking_date"] = booking_date.isoformat()
                        session["state"] = "awaiting_booking_time"
                        send_message(phone, "⏰ What time would you like your ride? (e.g., 10:30 AM, 14:00)")
                except ValueError:
                    send_message(phone, "❌ Invalid date format. Please use YYYY-MM-DD (e.g., 2025-07-25):")

            elif session["state"] == "awaiting_booking_time":
                try:
                    booking_time = datetime.strptime(text.upper(), "%I:%M %p").time() if "AM" in text.upper() or "PM" in text.upper() else datetime.strptime(text, "%H:%M").time()

                    booking_datetime = datetime.strptime(session["booking_date"], "%Y-%m-%d").replace(
                        hour=booking_time.hour, minute=booking_time.minute, second=booking_time.second
                    )

                    if booking_datetime < datetime.now():
                        send_message(phone, "❌ You cannot book a ride in the past. Please enter a future time:")
                    else:
                        session["start_time"] = booking_datetime.strftime("%Y-%m-%d %H:%M:%S")
                        session["state"] = "awaiting_pickup"
                        send_message(phone, "📍 Got it! Now, please send your pickup location.")
                except ValueError:
                    send_message(phone, "❌ Invalid time format. Please use HH:MM (e.g., 10:30, 14:00) or HH:MM AM/PM (e.g., 10:30 AM):")

            elif session["state"] == "awaiting_pickup":
                session["pickup"] = correct_location(text) # Corrected function call
                session["state"] = "awaiting_destination"
                send_message(phone, "🏁 Send your destination.")

            elif session["state"] == "awaiting_destination":
                session["destination"] = correct_location(text) # Corrected function call
                cars = get_available_car_types()
                if not cars:
                    send_message(phone, "🚧 No cars available right now.")
                    session["state"] = "awaiting_intent"
                else:
                    session["state"] = "awaiting_car_type"
                    btns = [{"id": f"car_{c.lower()}", "title": c.title()} for c in cars]
                    send_button_message(phone, "🚗 Choose your car:", btns)

            elif intent == "car_selection" and session["state"] == "awaiting_car_type":
                car_type = payload.replace("car_", "")

                # Determine if it's a pre-booking based on scheduled start time
                is_prebooking = False
                current_time_plus_2_hours = datetime.now() + timedelta(hours=2)

                if "start_time" in session:
                    try:
                        scheduled_start_time = datetime.strptime(session["start_time"], "%Y-%m-%d %H:%M:%S")
                        if scheduled_start_time > current_time_plus_2_hours:
                            is_prebooking = True
                    except ValueError:
                        pass # Invalid start_time, treat as immediate booking

                driver = None
                car = None
                ride_status = 'prebooked' if is_prebooking else 'ongoing' # Default status

                route = get_route_details(session["pickup"], session["destination"])
                if 'error' in route:
                    # Send the specific error message (e.g., "location is outside our service area") to the user
                    send_message(phone, route['error'])
                    # Reset the conversation to ask for the pickup location again
                    send_message(phone, "Please provide a new pickup location within Bengaluru.")
                    session["state"] = "awaiting_pickup"
                    return "ok", 200

                distance_value = float(route["distance"].split()[0])
                fare = round(distance_value * float(get_all_pricing()[0]['price_per_km']), 2) # Assuming first pricing for now

                # Calculate estimated end time for availability check and storage
                duration_minutes = float(route['duration'].split()[0])
                estimated_end_time = datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S') + timedelta(minutes=duration_minutes)
                session["end_time"] = estimated_end_time.strftime('%Y-%m-%d %H:%M:%S')

                if not is_prebooking: # For immediate bookings, assign driver now
                    driver, car = get_available_driver_and_car(car_type, session['start_time'], session['end_time'])
                    if not driver:
                        send_message(phone, "❌ No driver/car found for immediate booking at this time. Try another type or book for later.")
                        session["state"] = "awaiting_intent" # Reset state
                        return "ok", 200
                    # For immediate booking, status is ongoing, already set above

                # If it's a pre-booking, driver/car will be assigned later (remain None)
                session.update({
                    "car_type": car_type, # Store car type for later assignment
                    "driver": driver, # Will be None for pre-booking, assigned for immediate
                    "car": car,       # Will be None for pre-booking, assigned for immediate
                    "ride_status": ride_status # Store the determined status
                })

                session.update({
                    "route": route,
                    "fare": fare,
                    "state": "awaiting_confirmation"
                })

                send_message(phone, f"🛣 {session['pickup']} -> {session['destination']}")
                send_message(phone, f"📏 {route['distance']} | ⏱️ {route['duration']} | ₹{fare}")

                if is_prebooking:
                    send_message(phone, f"🗓️ Your ride is scheduled for {datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p on %b %d')}.")
                    send_button_message(phone, "✅ Confirm pre-booking?", [{"id": "confirm_ride", "title": "Confirm"}])
                else:
                    send_button_message(phone, "✅ Confirm booking?", [{"id": "confirm_ride", "title": "Confirm"}])


            elif intent == "confirm_ride" and session["state"] == "awaiting_confirmation":
                session["state"] = "ready_for_invoice"
                # Directly proceed to invoice generation, no coupon section
                return webhook() # Re-call webhook to process the next state immediately

            elif session["state"] == "ready_for_invoice":
                # Determine initial driver/car_id based on whether it's a pre-booking
                initial_driver_id = session["driver"]["id"] if session.get("driver") else None
                initial_car_id = session["car"]["id"] if session.get("car") else None

                ride_id = add_ride(
                    phone, session["pickup"], session["destination"],
                    session["route"]["distance"], session["route"]["duration"],
                    session["fare"],
                    initial_car_id,
                    initial_driver_id,
                    status=session["ride_status"], # Use the determined status (ongoing or prebooked)
                    payment_status="pending", # Initial payment status
                    start_time=session.get("start_time"), # Pass scheduled start time if pre-booking
                    end_time=session.get("end_time") # Pass estimated end time
                )

                invoice_data = {
                    "invoice_no": ride_id,
                    "customer_name": user['name'], # Use user's name from DB
                    "customer_address": "C-904, ALEMBIC URBAN FOREST, CHANNASANDRA",
                    "trips": [{"description": f"{session['pickup']} -> {session['destination']}", "amount": session['fare']}],
                    "subtotal": session['fare'],

                    "discount": 0.0, # Removed coupon, so discount is 0
                    "coupon_code": "", # Removed coupon
                    "tax": round(session['fare'] * 0.05, 2),
                    "total": round(session['fare'] * 1.05, 2),
                    "date": datetime.strptime(session['start_time'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y') # Set invoice date
                }

                invoice_path = generate_invoice(invoice_data, filename=f"invoice_{ride_id}.pdf")
                media_id = upload_media_to_whatsapp(invoice_path, PHONE_NUMBER_ID, ACCESS_TOKEN)
                if media_id:
                    send_invoice_pdf(phone, media_id, f"invoice_{ride_id}.pdf", PHONE_NUMBER_ID, ACCESS_TOKEN)

                session["payment_link"] = create_payment_link(phone, invoice_data["total"]) # Generate payment link now
                session["ride_id"] = ride_id
                session["invoice_total"] = invoice_data["total"]
                session["state"] = "awaiting_payment_option"
                send_button_message(phone, "💳 Choose payment mode:", [
                    {"id": "pay_online", "title": "Online"},
                    {"id": "pay_cash", "title": "Cash"}
                ])


            elif intent in ["pay_online", "pay_cash"] and session["state"] == "awaiting_payment_option":
                 handle_payment_option(intent, session, phone)


            else: # Fallback for unhandled intents or initial greeting after a session reset
                send_button_message(phone, "👋 Welcome to RideBot. What would you like to do? ", [
                    {"id": "book_ride", "title": "Book Ride"},
                    {"id": "check_booking", "title": "My Booking"},
                    {"id": "fare_info", "title": "Fare Info"}
                ])
                session["state"] = "awaiting_intent" # Ensure state is set for next interaction
        except Exception as e:
            import traceback
            traceback.print_exc()
        return "ok", 200

if __name__ == "__main__":
    # Start the pre-booking assignment thread
    assignment_thread = threading.Thread(target=assign_prebooked_rides_periodically)
    assignment_thread.daemon = True # Allow the main program to exit even if this thread is running
    assignment_thread.start()

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)