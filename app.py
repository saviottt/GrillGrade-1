# app.py - FINAL DEPLOYMENT VERSION

import os
import smtplib
import mysql.connector
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

# --- CORRECTED: Read all credentials from Environment Variables for deployment ---
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

# ✅ FIX: Use the correct variable names to read from the environment
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
RECIPIENT_EMAIL = 'donsavio1one@gmail.com'

def get_db_connection():
    """Creates a MySQL database connection using environment variables."""
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
    return conn

def send_email(subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("Error: Email credentials not set in environment variables.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        server.quit()
        print(f"Email sent successfully: '{subject}'")
        return True
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
        return False

# --- API Routes (No changes needed below this line) ---

@app.route("/")
def home():
    return jsonify({"message": "Welcome to GrillGrade API 🚀. The booking system is active."})

@app.route('/book_table', methods=['POST'])
def book_table():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    try:
        name = data.get('name')
        guests = int(data.get('guests'))
        date = data.get('date')
        time = data.get('time')
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid input format."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) 
    
    try:
        check_seats_query = "SELECT SUM(guests) AS total_booked_seats FROM booking WHERE booking_date = %s AND booking_time = %s"
        cursor.execute(check_seats_query, (date, time))
        result = cursor.fetchone()
        total_booked_seats = result['total_booked_seats'] if result['total_booked_seats'] is not None else 0
        
        TOTAL_CAPACITY = 20
        if (total_booked_seats + guests) > TOTAL_CAPACITY:
            return jsonify({"message": f"Sorry, not enough seats available. Only {TOTAL_CAPACITY - total_booked_seats} seats left."}), 409

        find_table_query = """
            SELECT id, capacity FROM restaurant_table
            WHERE capacity >= %s AND id NOT IN (
                SELECT table_id FROM booking WHERE booking_date = %s AND booking_time = %s
            )
            ORDER BY capacity ASC
            LIMIT 1
        """
        cursor.execute(find_table_query, (guests, date, time))
        available_table = cursor.fetchone()

        if not available_table:
            return jsonify({"message": "Sorry, while seats are available, no single table can fit your party size."}), 409

        insert_query = "INSERT INTO booking (table_id, customer_name, guests, booking_date, booking_time) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (available_table['id'], name, guests, date, time))
        conn.commit()

        subject = f"New Table Booking from {name}"
        body = f"A new reservation has been confirmed: Name: {name}, Guests: {guests}, Date: {date}, Time: {time}, Table ID: {available_table['id']}"
        send_email(subject, body)
        return jsonify({"message": f"Table for {guests} booked successfully for {name}!"}), 201

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Database error: {err}")
        return jsonify({"message": "Could not process booking due to a server error."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    subject = f"New Food Order from {data.get('name')}"
    body = f"""
    Customer: {data.get('name')}
    Phone: {data.get('phone')}
    Address: {data.get('address')}
    Order: {data.get('orderDetails')}
    Total: ${data.get('totalPrice')}
    """
    if send_email(subject, body):
        return jsonify({"message": "Order received and email sent."}), 200
    else:
        return jsonify({"error": "Failed to send notification email."}), 500
