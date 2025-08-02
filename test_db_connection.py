from flask import Flask, request, jsonify
import sqlite3
import random
import time
import traceback

# --- Basic Flask App Setup ---
app = Flask(__name__)
DB_NAME = "cab_booking.db"
user_sessions = {}

# --- Database Functions (copied from db.py for this test) ---
def connect():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def get_user(phone):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, phone, name FROM users WHERE phone=?", (phone,))
    user = cur.fetchone()
    conn.close()
    return user

def get_all_owner_phone_numbers():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT phone FROM owners WHERE phone IS NOT NULL")
    phone_numbers = [row[0] for row in cur.fetchall()]
    conn.close()
    return phone_numbers

# --- The Failing Route ---
@app.route("/api/send_otp", methods=["POST"])
def send_otp():
    print("--- /api/send_otp route was hit ---")
    try:
        data = request.json
        phone_10_digit = data.get("phone")
        full_phone = "91" + phone_10_digit

        print(f"--- Checking for phone number: {full_phone} ---")

        user = get_user(full_phone)
        print(f"--- User check complete. Found user: {'Yes' if user else 'No'} ---")

        all_owner_phones = get_all_owner_phone_numbers()
        print(f"--- Owner check complete. Found {len(all_owner_phones)} owner(s) ---")

        is_registered_owner = full_phone in all_owner_phones

        if not user and not is_registered_owner:
            print("--- User not registered. Sending 404 response. ---")
            return jsonify({"error": "This phone number is not registered with us."}), 404

        otp = random.randint(100000, 999999)
        user_sessions[full_phone] = {'otp': otp, 'otp_timestamp': time.time()}

        print(f"--- OTP for {full_phone} is: {otp} ---")
        print("\n✅ SUCCESS: The route executed without crashing.")
        return jsonify({"message": "An OTP has been sent to your phone number."}), 200

    except Exception as e:
        print("\n❌ FAILURE: The Flask route crashed. Error traceback below:")
        print("-----------------------------------")
        traceback.print_exc()
        print("-----------------------------------")
        return jsonify({"error": str(e)}), 500

# --- Main Execution ---
if __name__ == "__main__":
    print(">>> STARTING MINIMAL FLASK SERVER FOR FINAL TEST <<<")
    # Running on port 5000 to avoid conflict with the main app
    app.run(port=5000, debug=True)