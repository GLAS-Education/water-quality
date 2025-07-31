import os
import psycopg2
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from functools import wraps

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
API_KEY = os.environ.get('API_KEY')

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Authorization header missing'}), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Invalid authorization format. Use Bearer token'}), 401
        
        token = auth_header.split(' ')[1]
        
        if token != API_KEY:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def init_db():
    """Initialize database with schema"""
    conn = psycopg2.connect(DATABASE_URL)
    with open('schema.sql', 'r') as f:
        with conn.cursor() as cur:
            cur.execute(f.read())
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

# API Endpoints
@app.route('/api/main', methods=['POST'])
@require_api_key
def add_main_data():
    """Add main sensor data"""
    data = request.json
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO main_data (experiment_id, temperature_1, temperature_2, temperature_3, temperature_4, 
                                  ph, battery_level, tds, turbidity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['experiment_id'], data['temperature_1'], data['temperature_2'], data['temperature_3'], 
              data['temperature_4'], data['ph'], data['battery_level'], 
              data['tds'], data['turbidity']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/wake', methods=['POST'])
@require_api_key
def add_wake_data():
    """Add wake sensor data"""
    data = request.json
    
    # Parse rotation data string into individual values
    rotation_values = [float(x.strip()) for x in data['rotation_data'].split(',')]
    
    if len(rotation_values) != 16:
        return jsonify({'error': 'Rotation data must contain exactly 16 comma-separated values'}), 400
    
    yaw, pitch, roll, ax, ay, az, gx, gy, gz, qx, qy, qz, qw, lax, lay, laz = rotation_values
    
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute('''
            INSERT INTO wake_data (experiment_id, yaw, pitch, roll, ax, ay, az, gx, gy, gz, 
                                  qx, qy, qz, qw, lax, lay, laz, hydrophone_reading, water_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['experiment_id'], yaw, pitch, roll, ax, ay, az, gx, gy, gz, qx, qy, qz, qw, lax, lay, laz,
              data['hydrophone_reading'], data['water_level']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/dead', methods=['POST'])
@require_api_key
def send_sos():
    """Send SOS message to Slack webhook"""
    slack_webhook_url = os.environ.get('SLACK_SOS_WEBHOOK')
    
    if not slack_webhook_url:
        return jsonify({'error': 'SLACK_SOS_WEBHOOK environment variable not set'}), 500
    
    # Slack webhook payload
    message_payload = {
        'text': '🚨 I am drowning. Please help. 🚨'
    }
    
    try:
        # Send POST request to Slack webhook
        response = requests.post(slack_webhook_url, json=message_payload, timeout=10)
        response.raise_for_status()
        
        return jsonify({'status': 'success', 'message': 'SOS sent to Slack'})
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to send SOS to Slack: {str(e)}'}), 500

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    print("🌊 GLAS Store Server Starting...")
    print("📊 Database initialized")
    print("🚀 Server running on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
