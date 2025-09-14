# app.py - FIXED VERSION

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

# Database configuration from environment variables
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

# Email configuration from environment variables
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'donsavio1one@gmail.com')

def get_db_connection():
    """Creates a MySQL database connection using environment variables."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            autocommit=False  # Explicitly set autocommit to False
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def send_email(subject, body):
    """Send email notification."""
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

@app.route("/")
def home():
    """Health check endpoint."""
    return jsonify({"message": "Welcome to GrillGrade API 🚀. The booking system is active."})

@app.route('/book_table', methods=['POST'])
def book_table():
    """Handle table booking requests."""
    data = request.get_json()
    
    # Validate input data
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ['name', 'guests', 'date', 'time']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        name = str(data.get('name')).strip()
        guests = int(data.get('guests'))
        date = data.get('date')
        time = data.get('time')
        
        # Validate guests count
        if guests <= 0 or guests > 20:
            return jsonify({"error": "Number of guests must be between 1 and 20"}), 400
            
    except (ValueError, TypeError) as e:
        return jsonify({"error": "Invalid input format"}), 400

    # Get database connection
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check available seats for the given date and time
        check_seats_query = """
            SELECT SUM(guests) AS total_booked_seats 
            FROM booking 
            WHERE booking_date = %s AND booking_time = %s
        """
        cursor.execute(check_seats_query, (date, time))
        result = cursor.fetchone()
        total_booked_seats = result['total_booked_seats'] if result['total_booked_seats'] is not None else 0
        
        TOTAL_CAPACITY = 20
        available_seats = TOTAL_CAPACITY - total_booked_seats
        
        if guests > available_seats:
            return jsonify({
                "error": f"Not enough seats available. Only {available_seats} seats remaining for this time slot."
            }), 409

        # Find suitable table
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
            return jsonify({
                "error": "No suitable table available for your party size at this time."
            }), 409

        # Insert booking
        insert_query = """
            INSERT INTO booking (table_id, customer_name, guests, booking_date, booking_time) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (available_table['id'], name, guests, date, time))
        conn.commit()

        # Send confirmation email
        subject = f"New Table Booking - {name}"
        body = f"""
New Reservation Confirmed:

Customer Name: {name}
Number of Guests: {guests}
Date: {date}
Time: {time}
Table ID: {available_table['id']}
Table Capacity: {available_table['capacity']}

Booking confirmed successfully!
        """
        
        send_email(subject, body)
        
        return jsonify({
            "message": f"Table successfully booked for {guests} guests on {date} at {time}!",
            "booking_details": {
                "customer_name": name,
                "guests": guests,
                "date": date,
                "time": time,
                "table_id": available_table['id']
            }
        }), 201

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Database error: {err}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        conn.rollback()
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/place_order', methods=['POST'])
def place_order():
    """Handle food order requests."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Validate required fields
    required_fields = ['name', 'phone', 'address', 'orderDetails', 'totalPrice']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    try:
        name = str(data.get('name')).strip()
        phone = str(data.get('phone')).strip()
        address = str(data.get('address')).strip()
        order_details = data.get('orderDetails')
        total_price = float(data.get('totalPrice'))
        
        if total_price <= 0:
            return jsonify({"error": "Invalid total price"}), 400
            
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input format"}), 400
    
    # Prepare email content
    subject = f"New Food Order - {name}"
    body = f"""
New Food Order Received:

Customer Details:
- Name: {name}
- Phone: {phone}
- Address: {address}

Order Details:
{order_details}

Total Amount: ${total_price:.2f}

Please process this order promptly.
    """
    
    # Send email notification
    if send_email(subject, body):
        return jsonify({
            "message": "Order received successfully! You will be contacted shortly.",
            "order_summary": {
                "customer_name": name,
                "total_price": total_price
            }
        }), 200
    else:
        return jsonify({"error": "Order received but email notification failed"}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
