import sqlite3
from werkzeug.security import generate_password_hash # Import for hashing passwords

conn = sqlite3.connect('cab_booking.db')
cursor = conn.cursor()

# Drop tables if they exist (for fresh start)
cursor.execute("DROP TABLE IF EXISTS users")
cursor.execute("DROP TABLE IF EXISTS drivers")
cursor.execute("DROP TABLE IF EXISTS cars")
cursor.execute("DROP TABLE IF EXISTS rides")
cursor.execute("DROP TABLE IF EXISTS coupons")
cursor.execute("DROP TABLE IF EXISTS owners")

# Users table
cursor.execute('''
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL
)
''')

# Owners table (MODIFIED: Added phone column)
cursor.execute('''
CREATE TABLE owners (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL
)
''')

# Cars table
cursor.execute('''
CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    car_number TEXT NOT NULL,
    model TEXT NOT NULL,
    type TEXT NOT NULL,
    rate REAL NOT NULL,
    status TEXT DEFAULT 'free'
)
''')

# Drivers table
cursor.execute('''
CREATE TABLE drivers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    car_id INTEGER,
    status TEXT DEFAULT 'free',
    last_latitude REAL,
    last_longitude REAL,
    FOREIGN KEY (car_id) REFERENCES cars(id)
)
''')

# Rides table
cursor.execute('''
CREATE TABLE rides (
    id SERIAL PRIMARY KEY,
    user_phone TEXT NOT NULL,
    pickup TEXT NOT NULL,
    destination TEXT NOT NULL,
    distance TEXT,
    duration TEXT,
    fare REAL NOT NULL,
    start_time TEXT,
    end_time TEXT,
    driver_id INTEGER,
    car_id INTEGER,
    payment_status TEXT DEFAULT 'pending',
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (driver_id) REFERENCES drivers(id),
    FOREIGN KEY (car_id) REFERENCES cars(id)
)
''')

# Coupons table
cursor.execute('''
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    discount REAL NOT NULL,
    used INTEGER DEFAULT 0
)
''')

# Insert test coupons
cursor.executemany('''
INSERT INTO coupons (code, discount, used) VALUES (?, ?, ?);
''', [('WELCOME10', 10, 0), ('SAVE20', 20, 0), ('OFF30', 30, 0)])

# Insert dummy cars
cursor.executemany('''
INSERT INTO cars (car_number, model, type, rate, status)
VALUES (?, ?, ?, ?, ?);
''', [
    ('KA01AB1234', 'Maruti Dzire', 'sedan', 12.0, 'free'),
    ('KA02CD5678', 'Toyota Innova', 'suv', 15.0, 'free')
])

# Insert dummy drivers
cursor.executemany('''
INSERT INTO drivers (name, phone, car_id, status, last_latitude, last_longitude)
VALUES (?, ?, ?, ?, ?, ?);
''', [('Ramesh', '919550954674', 1, 'free', 12.9716, 77.5946)])

# Insert dummy users
hashed_password_for_demo = generate_password_hash('password123')
cursor.executemany('''
INSERT INTO users (phone, name, password_hash)
VALUES (?, ?, ?);
''', [
    ('918519879924', 'John Doe', hashed_password_for_demo),
    ('919876543211', 'Jane Smith', hashed_password_for_demo),
    ('919550954674', 'Owner User', hashed_password_for_demo) # Add owner's phone as a user
])

# Insert dummy owner (MODIFIED: Added phone number)
hashed_owner_password = generate_password_hash('owner123')
cursor.execute('''
INSERT INTO owners (email, phone, name, password_hash)
VALUES (?, ?, ?, ?);
''', ('owner@dhanvanth.com', '919550954674', 'Dhanvanth Admin', hashed_owner_password))

# Insert dummy rides
cursor.executemany('''
INSERT INTO rides (user_phone, pickup, destination, fare, status)
VALUES (?, ?, ?, ?, ?);
''', [('918519879924', 'Koramangala', 'Indiranagar', 100.0, 'completed')])

conn.commit()
conn.close()
print("Database initialized with tables and dummy data.")