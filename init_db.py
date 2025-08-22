import mysql.connector
from werkzeug.security import generate_password_hash

db_config = {
    'host': '34.72.197.29',
    'user': 'Deepak',
    'password': 'Deep@k80',
    'database': 'cab_booking_db'
}

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    print("✅ Successfully connected to MySQL database.")
    tables_to_drop = [
        'rides', 'chat_sessions', 'drivers', 'users', 'owners',
        'cars', 'coupons', 'settings', 'site_content','locations','pricing'
    ]
    for table in tables_to_drop:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"Dropped table {table} if it existed.")

    # Users table
    cursor.execute("""
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        phone VARCHAR(20) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )
    """)

    # Owners table
    cursor.execute("""
    CREATE TABLE owners (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(20) UNIQUE,
        name VARCHAR(255) NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )
    """)

    # Cars table
    cursor.execute("""
    CREATE TABLE cars (
        id INT AUTO_INCREMENT PRIMARY KEY,
        car_number VARCHAR(20) NOT NULL,
        model VARCHAR(100) NOT NULL,
        type VARCHAR(50) NOT NULL,
        rate DECIMAL(10, 2) NOT NULL,
        status VARCHAR(50) DEFAULT 'free'
    )
    """)

    # Drivers table with is_fixed flag
    cursor.execute("""
    CREATE TABLE drivers (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        car_id INT,
        status VARCHAR(50) DEFAULT 'free',
        last_latitude DECIMAL(10, 8),
        last_longitude DECIMAL(11, 8),
        is_fixed BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE SET NULL
    )
    """)

    # Rides table
    cursor.execute("""
    CREATE TABLE rides (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_phone VARCHAR(20) NOT NULL,
        car_type VARCHAR(50),
        pickup TEXT NOT NULL,
        destination TEXT NOT NULL,
        distance VARCHAR(50),
        duration VARCHAR(50),
        fare DECIMAL(10, 2) NOT NULL,
        start_time DATETIME,
        end_time DATETIME,
        driver_id INT,
        car_id INT,
        payment_status VARCHAR(50) DEFAULT 'pending',
        status VARCHAR(50) DEFAULT 'pending',
        enroute_to_pickup_time DATETIME,
        at_pickup_time DATETIME,
        trip_start_time DATETIME,
        FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
        FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE SET NULL
    )
    """)

    # Coupons table
    cursor.execute("""
    CREATE TABLE coupons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(50) UNIQUE NOT NULL,
        discount DECIMAL(10, 2) NOT NULL,
        used BOOLEAN DEFAULT FALSE
    )
    """)

    # Settings table
    cursor.execute("""
    CREATE TABLE settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        key_name VARCHAR(100) UNIQUE NOT NULL,
        value TEXT NOT NULL
    )
    """)
    # Chat sessions table
    cursor.execute("""
    CREATE TABLE chat_sessions (
        phone VARCHAR(20) PRIMARY KEY,
        state VARCHAR(100),
        new_user_name VARCHAR(255), 
        new_user_email VARCHAR(255), 
        booking_date VARCHAR(50),
        pickup TEXT,
        destination TEXT,
        car_type VARCHAR(50),
        route_distance DECIMAL(10, 2),
        route_duration VARCHAR(50),
        fare DECIMAL(10, 2),
        ride_status VARCHAR(50),
        start_time VARCHAR(50),
        end_time VARCHAR(50),
        ride_id INT,
        upi_string TEXT,
        invoice_total DECIMAL(10, 2),
        otp INT,
        otp_timestamp DECIMAL(20, 2)
    )
    """)

    # Site content table
    cursor.execute("""
    CREATE TABLE site_content (
        key_name VARCHAR(100) PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE locations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE
    )
    """)


    cursor.execute("""
    CREATE TABLE pricing (
        id INT AUTO_INCREMENT PRIMARY KEY,
        vehicle_type VARCHAR(50) NOT NULL UNIQUE,
        price_per_km DECIMAL(10, 2) NOT NULL
    )
    """)

    cursor.executemany(
        "INSERT INTO pricing (vehicle_type, price_per_km) VALUES (%s, %s)",
        [
            ('sedan', 12.00),
            ('suv', 15.00),
            ('compact', 10.00)
        ]
    )

    print("✅ All tables created successfully.")

    cursor.execute("INSERT INTO settings (key_name, value) VALUES (%s, %s)", ('assignment_mode', 'auto'))

    # Insert coupons
    cursor.executemany(
        "INSERT INTO coupons (id, code, discount, used) VALUES (%s, %s, %s, %s)",
        [
            (1, 'WELCOME10', 10.00, 0),
            (2, 'SAVE20', 20.00, 0),
            (3, 'OFF30', 30.00, 0)
        ]
    )

    # Insert site content
    cursor.execute("INSERT IGNORE INTO site_content (key_name, value) VALUES (%s, %s)",
                   ('about_us_content', 'Welcome to Dhanvanth Tours & Travels! [Admin: Please edit this content in the dashboard.]'))
    cursor.execute("INSERT IGNORE INTO site_content (key_name, value) VALUES (%s, %s)",
                   ('support_content', 'For support, please contact us at:\nEmail: support@dhanvanth.com\nPhone: +91 12345 67890\n\n[Admin: Please edit this content in the dashboard.]'))

    # Insert cars
    cursor.executemany(
        "INSERT INTO cars (id, car_number, model, type, rate, status) VALUES (%s, %s, %s, %s, %s, %s)",
        [
            (1, 'KA01AB1234', 'Maruti Dzire', 'sedan', 12.0, 'free'),
            (2, 'KA02CD5678', 'Toyota Innova', 'suv', 15.0, 'free'),
            (3, 'KA03EF9012', 'Hyundai Verna', 'sedan', 14.0, 'free')
        ]
    )

    # Insert drivers (Ramesh fixed to car 1)
    cursor.executemany(
        "INSERT INTO drivers (id, name, phone, car_id, status, last_latitude, last_longitude, is_fixed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        [
            (1, 'Ramesh', '919550954674', 1, 'free', 12.9716, 77.5946, 1), # <-- CHANGE TO YOUR DRIVER 1 TEST NUMBER
            (2, 'Suresh', '919550954673', None, 'free', 12.9352, 77.6245, 0), # <-- CHANGE TO YOUR DRIVER 2 TEST NUMBER
            (3, 'Mahesh', '919550954671', 2, 'free', 12.9260, 77.6762, 0)
        ]
    )

    hashed_password = generate_password_hash('password123')
    cursor.executemany(
        "INSERT INTO users (id, phone, name, email, password_hash) VALUES (%s, %s, %s, %s, %s)",
        [
            (1, '918519879924', 'John Doe', 'user@example.com', hashed_password),
            (2, '919876543211', 'Jane Smith', 'jane@example.com', hashed_password)
        ]
    )

    # Insert owner
    hashed_owner_password = generate_password_hash('owner123')
    cursor.execute(
        "INSERT INTO owners (id, email, phone, name, password_hash) VALUES (%s, %s, %s, %s, %s)",
        (1, 'bejavadadeepak80@gmail.com', '918519879924', 'Dhanvanth Admin', hashed_owner_password)
    )

    # Insert sample ride
    cursor.executemany(
        "INSERT INTO rides (id, user_phone, car_type, pickup, destination, distance, duration, fare, start_time, end_time, driver_id, car_id, payment_status, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            (1, '918519879924', 'sedan', 'Koramangala', 'Indiranagar', '8 km', '20 mins', 100.0, '2025-08-10 10:00:00', '2025-08-10 10:20:00', 1, 1, 'paid', 'completed')
        ]
    )

    print("✅ Dummy data inserted successfully.")

    conn.commit()

except mysql.connector.Error as err:
    print(f"❌ MySQL Error: {err}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("✅ Database initialized and MySQL connection closed.")