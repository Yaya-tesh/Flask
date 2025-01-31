import json
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# File to store persistent data
DATA_FILE = "data.json"

# Load data from file
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"registered_users": {}, "pending_users": {}}

# Save data to file
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

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
    <li><a href="/delete_user_form">Delete a User</a></li>
</ul>
"""
view_users_template = """
<h2>Registered Users</h2>
<ul>
    {% for cid, user in users.items() %}
        <li>
            Username: {{ user['username'] }}, Computer ID: {{ cid }}, App Version: {{ user['app_version'] }}
            <form action="/unregister_user" method="post" style="display:inline;">
                <input type="hidden" name="computer_id" value="{{ cid }}">
                <button type="submit">Unregister</button>
            </form>
        </li>
    {% endfor %}
</ul>
<a href="/">Back to Dashboard</a>
"""
view_pending_users_template = """
<h2>Pending User Approvals</h2>
<ul>
    {% for cid, user in pending.items() %}
        <li>
            Username: {{ user['username'] }}, Computer ID: {{ cid }}, App Version: {{ user['app_version'] }}
            <form action="/approve_user" method="post" style="display:inline;">
                <input type="hidden" name="computer_id" value="{{ cid }}">
                <button type="submit">Approve</button>
            </form>
        </li>
    {% endfor %}
</ul>
<a href="/">Back to Dashboard</a>
"""
delete_user_form_template = """
<h2>Delete a User</h2>
<form action="/delete_user" method="post">
    Admin Username: <input type="text" name="admin_username" required><br>
    Admin Password: <input type="password" name="admin_password" required><br>
    Computer ID: <input type="text" name="computer_id" required><br>
    <button type="submit">Delete</button>
</form>
<a href="/">Back to Dashboard</a>
"""

@app.route('/')
def dashboard():
    return dashboard_template

@app.route('/view_users')
def view_users():
    if not registered_users:
        return "<h2>No registered users.</h2><a href='/'>Back to Dashboard</a>"
    return render_template_string(view_users_template, users=registered_users)

@app.route('/view_pending_users')
def view_pending_users():
    if not pending_users:
        return "<h2>No pending user approvals.</h2><a href='/'>Back to Dashboard</a>"
    return render_template_string(view_pending_users_template, pending=pending_users)

@app.route('/delete_user_form')
def delete_user_form():
    return delete_user_form_template

@app.route('/delete_user', methods=['POST'])
def delete_user():
    admin_username = request.form.get('admin_username')
    admin_password = request.form.get('admin_password')
    computer_id = request.form.get('computer_id')

    if admin_username != admin_user['username'] or admin_password != admin_user['password']:
        return "Unauthorized access. <a href='/delete_user_form'>Try Again</a>", 403

    if computer_id in registered_users:
        deleted_user = registered_users.pop(computer_id)
        save_data({"registered_users": registered_users, "pending_users": pending_users})
        return f"User {deleted_user['username']} deleted successfully. <a href='/'>Back to Dashboard</a>"
    return f"Computer ID {computer_id} not found. <a href='/delete_user_form'>Try Again</a>", 404

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
        return f"User {registered_users[computer_id]['username']} approved successfully. <a href='/view_users'>Back to Users</a>"

    return f"Computer ID {computer_id} not found in pending approvals. <a href='/view_pending_users'>Back</a>", 404

@app.route('/unregister_user', methods=['POST'])
def unregister_user():
    computer_id = request.form.get('computer_id')

    if computer_id in registered_users:
        unregistered_user = registered_users.pop(computer_id)
        save_data({"registered_users": registered_users, "pending_users": pending_users})
        return f"User {unregistered_user['username']} unregistered successfully. <a href='/view_users'>Back</a>"

    return f"Computer ID {computer_id} not found. <a href='/view_users'>Back</a>", 404

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    computer_id = data.get('computer_id')

    if computer_id in registered_users:
        return jsonify({"message": f"User {registered_users[computer_id]['username']} is verified!"})
    return jsonify({"message": "Computer not registered!"}), 404

if __name__ == '__main__':
    # Bind to all network interfaces and use port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)