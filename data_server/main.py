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

def send_slack_sos_message(message_text: str):
    """Send a message to the Slack SOS webhook. Returns (ok, error_message)."""
    slack_webhook_url = os.environ.get('SLACK_SOS_WEBHOOK')
    if not slack_webhook_url:
        return False, 'SLACK_SOS_WEBHOOK environment variable not set'

    payload = {'text': message_text}
    try:
        response = requests.post(slack_webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        return True, None
    except requests.exceptions.RequestException as e:
        return False, str(e)

def log_sos_event(experiment_id: str, source: str, message: str):
    """Insert an SOS event record for auditing/rate limiting. Best-effort; exceptions bubble up."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sos_events (experiment_id, source, message)
                VALUES (%s, %s, %s)
                """,
                (experiment_id, source, message),
            )
        conn.commit()
    finally:
        conn.close()

def maybe_send_auto_sos(experiment_id: str):
    """Send an SOS for this experiment if one hasn't been sent in the last 24 hours."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM sos_events
                WHERE experiment_id = %s
                  AND created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (experiment_id,),
            )
            recent = cur.fetchone()

        if recent:
            return False  # rate-limited

    finally:
        conn.close()

    # Not rate-limited; send and log
    message_text = f"🚨 Water detected for experiment {experiment_id}. Please help. 🚨"
    ok, err = send_slack_sos_message(message_text)
    if ok:
        try:
            log_sos_event(experiment_id, 'auto', message_text)
        except Exception:
            # Best-effort logging; do not raise to caller
            pass
    return ok

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
                                  ph, battery_level, tds, turbidity, water_detected)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (data['experiment_id'], data['temperature_1'], data['temperature_2'], data['temperature_3'], 
              data['temperature_4'], data['ph'], data['battery_level'], 
              data['tds'], data['turbidity'], data['water_detected']))
    conn.commit()
    conn.close()
    # Trigger auto SOS if water is detected, rate-limited per experiment
    try:
        if data.get('water_detected'):
            experiment_id = data.get('experiment_id', 'unknown')
            maybe_send_auto_sos(experiment_id)
    except Exception:
        # Do not fail the data ingestion if SOS flow has issues
        pass

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
    # Allow optional experiment_id for logging/audit
    body = request.get_json(silent=True) or {}
    experiment_id = body.get('experiment_id', 'unknown')
    message_text = body.get('message', '🚨 I am drowning. Please help. 🚨')

    ok, err = send_slack_sos_message(message_text)
    if ok:
        try:
            log_sos_event(experiment_id, 'manual', message_text)
        except Exception:
            pass
        return jsonify({'status': 'success', 'message': 'SOS sent to Slack'})
    else:
        return jsonify({'error': f'Failed to send SOS to Slack: {err}'}), 500

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    print("🌊 GLAS Store Server Starting...")
    print("📊 Database initialized")
    print(f"🚀 Server running on http://localhost:{os.environ.get('PORT', 5000)}")
    
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 5000))
