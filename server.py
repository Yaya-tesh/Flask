import json
import os
import logging
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Use environment variable for persistent storage location (if Railway supports volumes)
DATA_FILE = os.getenv("DATA_FILE", "data.json")

# Load data from file
def load_data():
    if not os.path.exists(DATA_FILE):  # Create file if it doesn't exist
        default_data = {"registered_users": {}, "pending_users": {}}
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data

    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"registered_users": {}, "pending_users": {}}

# Save data to file
def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Failed to save data: {e}")

# Initialize data
data = load_data()
registered_users = data["registered_users"]
pending_users = data["pending_users"]

admin_user = {"username": "admin", "password": "admin123"}  # Example admin credentials

# HTML Templates for Browser Access
dashboard_template = """
<h1>Admin Dashboard</h1>
<p>Welcome to the Admin Panel. Use the options below:</p>
<ul>
    <li><a href="/view_users">View Registered Users</a></li>
    <li><a href="/view_pending_users">View Pending Users</a></li>
</ul>
"""

@app.route('/')
def dashboard():
    return dashboard_template

@app.route('/view_users')
def view_users():
    if not registered_users:
        return "<h2>No registered users.</h2><a href='/'>Back to Dashboard</a>"
    return render_template_string("""
    <h2>Registered Users</h2>
    <ul>
        {% for cid, user in users.items() %}
            <li>
                Username: {{ user['username'] }}, Computer ID: {{ cid }}, App Version: {{ user['app_version'] }}
            </li>
        {% endfor %}
    </ul>
    <a href="/">Back to Dashboard</a>
    """, users=registered_users)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    computer_id = data.get('computer_id')
    app_version = data.get('app_version')

    if not username or not computer_id or not app_version:
        return jsonify({"error": "Missing data!"}), 400

    if computer_id in registered_users or computer_id in pending_users:
        return jsonify({"error": "User with this Computer ID already exists!"}), 400

    pending_users[computer_id] = {"username": username, "app_version": app_version}
    save_data({"registered_users": registered_users, "pending_users": pending_users})
    return jsonify({"message": "Registration request submitted and awaiting admin approval."})

@app.route('/approve_user', methods=['POST'])
def approve_user():
    computer_id = request.form.get('computer_id')

    if computer_id in pending_users:
        registered_users[computer_id] = pending_users.pop(computer_id)
        save_data({"registered_users": registered_users, "pending_users": pending_users})
        return jsonify({"message": f"User {registered_users[computer_id]['username']} approved successfully."})

    return jsonify({"error": "Computer ID not found in pending approvals."}), 404

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    computer_id = data.get('computer_id')

    if computer_id in registered_users:
        return jsonify({"message": f"User {registered_users[computer_id]['username']} is verified!"})
    return jsonify({"message": "Computer not registered!"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # Railway assigns this dynamically
    app.run(host='0.0.0.0', port=port)