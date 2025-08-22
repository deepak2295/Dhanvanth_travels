import mysql.connector
from mysql.connector import errorcode
from datetime import datetime

db_config = {
    'host': '34.72.197.29',
    'user': 'Deepak',
    'password': 'Deep@k80',
    'database': 'cab_booking_db'
}

def connect():
    """Establishes a connection to the MySQL database."""
    try:
        return mysql.connector.connect(**db_config, connection_timeout=10)
    except mysql.connector.Error as err:
        print(f"MySQL Connection Error: {err}")
        raise err

def execute_query(query, params=None, fetch=None, many=False, commit=False):
    """A helper function to execute database queries safely."""
    conn = None
    try:
        conn = connect()
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params or ())
        
        if commit:
            conn.commit()
            return cursor.lastrowid if "INSERT" in query.upper() else cursor.rowcount
        
        if fetch == 'one':
            return cursor.fetchone()
        elif fetch == 'all':
            return cursor.fetchall()
            
    except mysql.connector.Error as err:
        print(f"MySQL Query Error: {err}")
        return None
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# ---- USER ----
def get_user(phone):
    return execute_query("SELECT * FROM users WHERE phone=%s", (phone,), fetch='one')

def add_user(phone, name, password_hash, email):
    query = "INSERT INTO users (phone, name, password_hash, email) VALUES (%s, %s, %s, %s)"
    return execute_query(query, (phone, name, password_hash, email), commit=True)

def update_user(user_id, name, phone):
    return execute_query("UPDATE users SET name=%s, phone=%s WHERE id=%s", (name, phone, user_id), commit=True)

def delete_user(user_id):
    return execute_query("DELETE FROM users WHERE id=%s", (user_id,), commit=True)

def get_all_users():
    return execute_query("SELECT id, phone, name, email FROM users", fetch='all')

def update_user_name_by_phone(phone, name):
    return execute_query("UPDATE users SET name=%s WHERE phone=%s", (name, phone), commit=True)

def get_user_by_email(email):
    return execute_query("SELECT * FROM users WHERE email=%s", (email,), fetch='one')

def update_password_by_email(email, new_password_hash):
    query = "UPDATE users SET password_hash=%s WHERE email=%s"
    return execute_query(query, (new_password_hash, email), commit=True)

# ---- OWNER ----
def get_owner_by_email(email):
    return execute_query("SELECT * FROM owners WHERE email=%s", (email,), fetch='one')

def get_all_owner_phone_numbers():
    rows = execute_query("SELECT phone FROM owners WHERE phone IS NOT NULL", fetch='all')
    return [row['phone'] for row in rows] if rows else []

def add_owner(email, phone, name, password_hash):
    query = "INSERT INTO owners (email, phone, name, password_hash) VALUES (%s, %s, %s, %s)"
    return execute_query(query, (email, phone, name, password_hash), commit=True)

def get_all_owners():
    return execute_query("SELECT id, email, phone, name FROM owners", fetch='all')

def update_owner(owner_id, email, phone, name):
    query = "UPDATE owners SET email=%s, phone=%s, name=%s WHERE id=%s"
    return execute_query(query, (email, phone, name, owner_id), commit=True)

def delete_owner(owner_id):
    return execute_query("DELETE FROM owners WHERE id=%s", (owner_id,), commit=True)

def get_owner_by_phone(phone):
    return execute_query("SELECT id, email, phone, name FROM owners WHERE phone=%s", (phone,), fetch='one')

def update_password_by_email_for_owner(email, new_password_hash):
    query = "UPDATE owners SET password_hash=%s WHERE email=%s"
    return execute_query(query, (new_password_hash, email), commit=True)

# ---- DRIVER ----
def get_driver_by_id(driver_id):
    return execute_query("SELECT * FROM drivers WHERE id=%s", (driver_id,), fetch='one')

def add_driver(name, phone, car_id=None, status='free'):
    query = "INSERT INTO drivers (name, phone, car_id, status) VALUES (%s, %s, %s, %s)"
    return execute_query(query, (name, phone, car_id, status), commit=True)

def update_driver(driver_id, name, phone, car_id, status):
    query = "UPDATE drivers SET name=%s, phone=%s, car_id=%s, status=%s WHERE id=%s"
    return execute_query(query, (name, phone, car_id, status, driver_id), commit=True)

def update_driver_location(driver_id, latitude, longitude):
    query = "UPDATE drivers SET last_latitude=%s, last_longitude=%s WHERE id=%s"
    return execute_query(query, (latitude, longitude, driver_id), commit=True)

def delete_driver(driver_id):
    return execute_query("DELETE FROM drivers WHERE id=%s", (driver_id,), commit=True)


def get_all_drivers(status=None):
    query = """
        SELECT 
            d.id, 
            d.name, 
            d.phone, 
            c.car_number as car_number,  -- CHANGE THIS LINE
            d.status, 
            d.car_id, 
            d.last_latitude, 
            d.last_longitude
        FROM drivers d LEFT JOIN cars c ON d.car_id = c.id
    """
    params = []
    if status:
        query += " WHERE d.status = %s"
        params.append(status)
    return execute_query(query, params, fetch='all')
# ---- CAR ----
def get_car_by_id(car_id):
    return execute_query("SELECT * FROM cars WHERE id=%s", (car_id,), fetch='one')

def add_car(car_number, model, car_type, rate, status='free'):
    query = "INSERT INTO cars (car_number, model, type, rate, status) VALUES (%s, %s, %s, %s, %s)"
    return execute_query(query, (car_number, model, car_type, rate, status), commit=True)

def update_car(car_id, car_number, model, car_type, rate, status):
    query = "UPDATE cars SET car_number=%s, model=%s, type=%s, rate=%s, status=%s WHERE id=%s"
    return execute_query(query, (car_number, model, car_type, rate, status, car_id), commit=True)

def delete_car(car_id):
    return execute_query("DELETE FROM cars WHERE id=%s", (car_id,), commit=True)

def list_available_car_types():
    rows = execute_query("SELECT DISTINCT type FROM cars WHERE status='free'", fetch='all')
    return [row['type'] for row in rows] if rows else []

def get_all_cars(status=None):
    query = "SELECT * FROM cars"
    params = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    return execute_query(query, params, fetch='all')


def get_rate_for_car_type(car_type):
    """
    Fetches the LOWEST price per km for a given vehicle type
    from all cars that are currently marked as 'free'.
    """
    query = "SELECT MIN(rate) as rate FROM cars WHERE type = %s AND status = 'free'"
    result = execute_query(query, (car_type,), fetch='one')
    
    return result['rate'] if result and result['rate'] is not None else None
    
# ---- RIDE ----
def add_ride(user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time, car_type):
    if start_time is None:
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
        INSERT INTO rides (user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time, car_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time, car_type)
    ride_id = execute_query(query, params, commit=True)

    if ride_id and status == 'ongoing' and driver_id and car_id:
        execute_query("UPDATE drivers SET status='busy' WHERE id=%s", (driver_id,), commit=True)
        execute_query("UPDATE cars SET status='busy' WHERE id=%s", (car_id,), commit=True)
    return ride_id

def update_ride(ride_id, user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time):
    query = """
        UPDATE rides SET user_phone=%s, pickup=%s, destination=%s, distance=%s, duration=%s, 
        fare=%s, car_id=%s, driver_id=%s, status=%s, payment_status=%s, start_time=%s, end_time=%s
        WHERE id=%s
    """
    params = (user_phone, pickup, destination, distance, duration, fare, car_id, driver_id, status, payment_status, start_time, end_time, ride_id)
    return execute_query(query, params, commit=True)

def delete_ride(ride_id):
    return execute_query("DELETE FROM rides WHERE id=%s", (ride_id,), commit=True)

def get_ride_by_id(ride_id):
    query = """
        SELECT
            r.*, u.name AS customer_name, d.name AS driver_name,
            c.model AS car_model, c.car_number
        FROM rides r
        LEFT JOIN users u ON r.user_phone = u.phone
        LEFT JOIN drivers d ON r.driver_id = d.id
        LEFT JOIN cars c ON r.car_id = c.id
        WHERE r.id = %s
    """
    return execute_query(query, (ride_id,), fetch='one')

def get_available_driver_and_car(car_type, start_time, end_time):
    driver_query = "SELECT * FROM drivers WHERE status = 'free' AND is_fixed = 0 LIMIT 1"
    car_query = "SELECT * FROM cars WHERE status = 'free' AND type = %s LIMIT 1"
    
    driver = execute_query(driver_query, fetch='one')
    car = execute_query(car_query, (car_type,), fetch='one')
    
    return driver, car

def assign_driver_to_ride(ride_id, driver_id, car_id):
    execute_query("UPDATE rides SET driver_id=%s, car_id=%s, status='ongoing' WHERE id=%s", (driver_id, car_id, ride_id), commit=True)
    execute_query("UPDATE drivers SET status='busy' WHERE id=%s", (driver_id,), commit=True)
    execute_query("UPDATE cars SET status='busy' WHERE id=%s", (car_id,), commit=True)
    return True

def get_all_rides(status=None):
    query = """
        SELECT
            r.id, u.name AS customer_name, d.name AS driver_name, r.pickup, r.destination,
            r.distance, r.duration, r.fare, r.status, r.payment_status, r.start_time, r.end_time,
            c.model AS car_model, c.car_number, r.user_phone, r.driver_id, r.car_id
        FROM rides r
        LEFT JOIN users u ON r.user_phone = u.phone
        LEFT JOIN drivers d ON r.driver_id = d.id
        LEFT JOIN cars c ON r.car_id = c.id
    """
    params = []
    if status:
        query += " WHERE r.status = %s"
        params.append(status)
    return execute_query(query, params, fetch='all')



def get_prebooked_rides_for_assignment():
    """Fetches all prebooked rides, regardless of time."""
    return execute_query("SELECT * FROM rides WHERE status='prebooked'", fetch='all')

def get_rides_by_user_phone(user_phone=None, status=None, unassigned_only=False):
    query = """
        SELECT
            r.*, d.name as driver_name, c.model as car_model, u.name as customer_name
        FROM rides r
        LEFT JOIN users u ON r.user_phone = u.phone
        LEFT JOIN drivers d ON r.driver_id = d.id
        LEFT JOIN cars c ON r.car_id = c.id
    """
    conditions = []
    params = []

    if user_phone:
        conditions.append("r.user_phone = %s")
        params.append(user_phone)
    if status:
        conditions.append("r.status = %s")
        params.append(status)
    if unassigned_only:
        conditions.append("r.driver_id IS NULL")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY r.start_time DESC"
    if user_phone:
        query += " LIMIT 2"
    
    return execute_query(query, tuple(params), fetch='all')

def update_ride_status_and_time(ride_id, new_status, timestamp_column, timestamp_value):
    valid_columns = ['enroute_to_pickup_time', 'at_pickup_time', 'trip_start_time', 'end_time']
    if timestamp_column not in valid_columns:
        raise ValueError("Invalid timestamp column name")
    
    query = f"UPDATE rides SET status=%s, {timestamp_column}=%s WHERE id=%s"
    return execute_query(query, (new_status, timestamp_value, ride_id), commit=True)

def complete_ride_and_free_resources(ride_id, end_time):
    ride = get_ride_by_id(ride_id)
    if ride:
        execute_query("UPDATE rides SET status='completed', end_time=%s WHERE id=%s", (end_time, ride_id), commit=True)
        if ride.get('driver_id'):
            execute_query("UPDATE drivers SET status='free' WHERE id=%s", (ride['driver_id'],), commit=True)
        if ride.get('car_id'):
            execute_query("UPDATE cars SET status='free' WHERE id=%s", (ride['car_id'],), commit=True)
    return True

def complete_ride(ride_id):
    """Original function name restored for compatibility. Marks ride as complete and frees resources."""
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return complete_ride_and_free_resources(ride_id, end_time)

# ---- PAYMENT & COUPON ----
def update_payment_status(ride_id, status):
    return execute_query("UPDATE rides SET payment_status = %s WHERE id = %s", (status, ride_id), commit=True)

def get_latest_ride_id_by_phone(phone):
    result = execute_query("SELECT id FROM rides WHERE user_phone = %s ORDER BY id DESC LIMIT 1", (phone,), fetch='one')
    return result['id'] if result else None

def get_all_coupons():
    return execute_query("SELECT * FROM coupons", fetch='all')

def get_coupon(code):
    return execute_query("SELECT * FROM coupons WHERE code = %s AND used = 0", (code,), fetch='one')

def add_coupon(code, discount):
    return execute_query("INSERT INTO coupons (code, discount) VALUES (%s, %s)", (code, discount), commit=True)

def update_coupon(code, discount, used):
    return execute_query("UPDATE coupons SET discount=%s, used=%s WHERE code=%s", (discount, used, code), commit=True)

def delete_coupon(code):
    return execute_query("DELETE FROM coupons WHERE code=%s", (code,), commit=True)

def mark_coupon_used(code):
    return execute_query("UPDATE coupons SET used = 1 WHERE code = %s", (code,), commit=True)

# ---- DASHBOARD & STATS ----
def count_users():
    result = execute_query("SELECT COUNT(*) as count FROM users", fetch='one')
    return result['count'] if result else 0

def count_rides(status=None):
    query = "SELECT COUNT(*) as count FROM rides"
    params = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    result = execute_query(query, params, fetch='one')
    return result['count'] if result else 0

def count_drivers():
    result = execute_query("SELECT COUNT(*) as count FROM drivers", fetch='one')
    return result['count'] if result else 0
    
def count_vehicles():
    result = execute_query("SELECT COUNT(*) as count FROM cars", fetch='one')
    return result['count'] if result else 0

def count_vehicles_on_ride():
    result = execute_query("SELECT COUNT(*) as count FROM cars WHERE status='busy'", fetch='one')
    return result['count'] if result else 0

def count_drivers_on_ride():
    result = execute_query("SELECT COUNT(*) as count FROM drivers WHERE status='busy'", fetch='one')
    return result['count'] if result else 0
    
def calculate_revenue():
    result = execute_query("SELECT SUM(fare) as total FROM rides WHERE payment_status='paid'", fetch='one')
    return result['total'] if result and result['total'] else 0

def count_pending_payments():
    result = execute_query("SELECT COUNT(*) as count FROM rides WHERE payment_status='pending'", fetch='one')
    return result['count'] if result else 0

def get_revenue_by_period(period='monthly'):
    if period == 'weekly':
        label_format = "DATE_FORMAT(start_time, '%Y-%u')"
    elif period == 'yearly':
        label_format = "DATE_FORMAT(start_time, '%Y')"
    else:
        label_format = "DATE_FORMAT(start_time, '%Y-%m')"

    query = f"""
        SELECT {label_format} AS period_label, SUM(fare) AS revenue
        FROM rides WHERE payment_status='paid' AND start_time IS NOT NULL
        GROUP BY period_label ORDER BY period_label
    """
    return execute_query(query, fetch='all')
    
# ---- SETTINGS & CONTENT ----
def get_setting(key):
    result = execute_query("SELECT value FROM settings WHERE `key_name`=%s", (key,), fetch='one')
    if result:
        val = result['value']
        if val.lower() in ['true', 'false']:
            return val.lower() == 'true'
        return val
    return None

def set_setting(key, value):
    if isinstance(value, bool):
        value = 'true' if value else 'false'
    query = """
        INSERT INTO settings (key_name, value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE value = VALUES(value)
    """
    return execute_query(query, (key, value), commit=True)

def get_site_content(key):
    result = execute_query("SELECT value FROM site_content WHERE key_name=%s", (key,), fetch='one')
    return result['value'] if result else ""

def set_site_content(key, value):
    query = """
        INSERT INTO site_content (key_name, value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE value = VALUES(value)
    """
    return execute_query(query, (key, value), commit=True)

# ---- CHAT SESSION ----
def get_chat_session(phone):
    return execute_query("SELECT * FROM chat_sessions WHERE phone=%s", (phone,), fetch='one')


def save_chat_session(phone, data):
    query = """
        INSERT INTO chat_sessions (
            phone, state, new_user_name, new_user_email, booking_date, pickup, destination, 
            car_type, route_distance, route_duration, fare, ride_status, start_time, 
            end_time, ride_id, upi_string, invoice_total, otp, otp_timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            state=VALUES(state),
            new_user_name=VALUES(new_user_name),
            new_user_email=VALUES(new_user_email),
            booking_date=VALUES(booking_date),
            pickup=VALUES(pickup),
            destination=VALUES(destination),
            car_type=VALUES(car_type),
            route_distance=VALUES(route_distance),
            route_duration=VALUES(route_duration),
            fare=VALUES(fare),
            ride_status=VALUES(ride_status),
            start_time=VALUES(start_time),
            end_time=VALUES(end_time),
            ride_id=VALUES(ride_id),
            upi_string=VALUES(upi_string),
            invoice_total=VALUES(invoice_total),
            otp=VALUES(otp),
            otp_timestamp=VALUES(otp_timestamp);
    """
    params = (
        phone, data.get("state"), data.get("new_user_name"), data.get("new_user_email"),
        data.get("booking_date"), data.get("pickup"), data.get("destination"), 
        data.get("car_type"), data.get("route_distance"), data.get("route_duration"), 
        data.get("fare"), data.get("ride_status"), data.get("start_time"), 
        data.get("end_time"), data.get("ride_id"), data.get("upi_string"), 
        data.get("invoice_total"), data.get("otp"), data.get("otp_timestamp")
    )
    return execute_query(query, params, commit=True)

# ---- PLACEHOLDERS ----
def get_all_locations():
    """Fetches all locations from the database."""
    return execute_query("SELECT * FROM locations ORDER BY name", fetch='all')

def add_location(name):
    """Adds a new location to the database."""
    query = "INSERT INTO locations (name) VALUES (%s)"
    return execute_query(query, (name,), commit=True)

def update_location(location_id, name):
    """Updates an existing location's name."""
    query = "UPDATE locations SET name=%s WHERE id=%s"
    return execute_query(query, (name, location_id), commit=True)

def delete_location(location_id):
    """Deletes a location from the database."""
    query = "DELETE FROM locations WHERE id=%s"
    return execute_query(query, (location_id,), commit=True)

def get_all_pricing():
    """Fetches all pricing rules from the database."""
    return execute_query("SELECT * FROM pricing ORDER BY vehicle_type", fetch='all')

def add_pricing(vehicle_type, price_per_km):
    """Adds a new pricing rule to the database."""
    query = "INSERT INTO pricing (vehicle_type, price_per_km) VALUES (%s, %s)"
    return execute_query(query, (vehicle_type, price_per_km), commit=True)

def update_pricing(pricing_id, vehicle_type, price_per_km):
    """Updates an existing pricing rule."""
    query = "UPDATE pricing SET vehicle_type=%s, price_per_km=%s WHERE id=%s"
    return execute_query(query, (vehicle_type, price_per_km, pricing_id), commit=True)

def delete_pricing(pricing_id):
    """Deletes a pricing rule from the database."""
    return execute_query("DELETE FROM pricing WHERE id=%s", (pricing_id,), commit=True)

def manually_assign_driver(driver_id, car_id, ride_id):
    """Assigns a driver and car to a ride, checking for fixed-driver constraints."""
    driver = execute_query("SELECT is_fixed, car_id FROM drivers WHERE id = %s", (driver_id,), fetch='one')

    if driver and driver.get("is_fixed") and driver.get("car_id") is not None and driver.get("car_id") != int(car_id):
        return {"error": "This driver is permanently assigned to another car."}

    execute_query("UPDATE rides SET driver_id = %s, car_id = %s, status = 'assigned' WHERE id = %s", (driver_id, car_id, ride_id), commit=True)
    execute_query("UPDATE drivers SET status = 'busy', car_id = %s WHERE id = %s", (car_id, driver_id), commit=True)
    execute_query("UPDATE cars SET status = 'busy' WHERE id = %s", (car_id,), commit=True)
    
    return {"success": True}

def get_available_cars_by_type(car_type):
    """Fetches all cars of a specific type that are currently marked as 'free'."""
    query = "SELECT id, model, car_number, rate FROM cars WHERE type = %s AND status = 'free'"
    return execute_query(query, (car_type,), fetch='all')

def get_driver_by_phone(phone):
    """Fetches a driver's details by their phone number."""
    return execute_query("SELECT * FROM drivers WHERE phone=%s", (phone,), fetch='one')

def get_pricing_for_vehicle_type(vehicle_type):
    """Fetches the pricing rule for a specific vehicle type."""
    return execute_query("SELECT * FROM pricing WHERE vehicle_type = %s", (vehicle_type,), fetch='one')