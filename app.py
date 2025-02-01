import os
import json
import logging
from flask import Flask, request, jsonify, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database connection setup
def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {e}")
        raise

# Initialize database tables
def initialize_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                computer_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                app_version TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_users (
                computer_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                app_version TEXT NOT NULL
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Initialize database on startup
initialize_database()

# Example admin credentials
admin_user = {"username": "admin", "password": "admin123"}

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

@app.route('/')
def dashboard():
    return dashboard_template

@app.route('/view_users')
def view_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM registered_users")
        registered_users = cur.fetchall()
        cur.close()
        conn.close()

        if not registered_users:
            return "<h2>No registered users.</h2><a href='/'>Back to Dashboard</a>"

        return render_template_string("""
            <h2>Registered Users</h2>
            <ul>
                {% for user in users %}
                    <li>
                        Username: {{ user['username'] }}, Computer ID: {{ user['computer_id'] }}, App Version: {{ user['app_version'] }}
                        <form action="/unregister_user" method="post" style="display:inline;">
                            <input type="hidden" name="computer_id" value="{{ user['computer_id'] }}">
                            <button type="submit">Unregister</button>
                        </form>
                    </li>
                {% endfor %}
            </ul>
            <a href="/">Back to Dashboard</a>
        """, users=registered_users)

    except Exception as e:
        logger.error(f"Error in /view_users: {e}")
        return "An error occurred while fetching registered users.", 500

@app.route('/view_pending_users')
def view_pending_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM pending_users")
        pending_users = cur.fetchall()
        cur.close()
        conn.close()

        if not pending_users:
            return "<h2>No pending user approvals.</h2><a href='/'>Back to Dashboard</a>"

        return render_template_string("""
            <h2>Pending User Approvals</h2>
            <ul>
                {% for user in pending %}
                    <li>
                        Username: {{ user['username'] }}, Computer ID: {{ user['computer_id'] }}, App Version: {{ user['app_version'] }}
                        <form action="/approve_user" method="post" style="display:inline;">
                            <input type="hidden" name="computer_id" value="{{ user['computer_id'] }}">
                            <button type="submit">Approve</button>
                        </form>
                    </li>
                {% endfor %}
            </ul>
            <a href="/">Back to Dashboard</a>
        """, pending=pending_users)

    except Exception as e:
        logger.error(f"Error in /view_pending_users: {e}")
        return "An error occurred while fetching pending users.", 500

@app.route('/delete_user_form')
def delete_user_form():
    return """
        <h2>Delete a User</h2>
        <form action="/delete_user" method="post">
            Admin Username: <input type="text" name="admin_username" required><br>
            Admin Password: <input type="password" name="admin_password" required><br>
            Computer ID: <input type="text" name="computer_id" required><br>
            <button type="submit">Delete</button>
        </form>
        <a href="/">Back to Dashboard</a>
    """

@app.route('/delete_user', methods=['POST'])
def delete_user():
    admin_username = request.form.get('admin_username')
    admin_password = request.form.get('admin_password')
    computer_id = request.form.get('computer_id')

    if admin_username != admin_user['username'] or admin_password != admin_user['password']:
        return "Unauthorized access. <a href='/delete_user_form'>Try Again</a>", 403

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM registered_users WHERE computer_id = %s RETURNING username", (computer_id,))
        deleted_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if deleted_user:
            return f"User {deleted_user[0]} deleted successfully. <a href='/'>Back to Dashboard</a>"
        else:
            return f"Computer ID {computer_id} not found. <a href='/delete_user_form'>Try Again</a>", 404

    except Exception as e:
        logger.error(f"Error in /delete_user: {e}")
        return "An error occurred while deleting the user.", 500

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    computer_id = data.get('computer_id')
    app_version = data.get('app_version')

    if not username or not computer_id or not app_version:
        return jsonify({"error": "Missing data!"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT computer_id FROM registered_users WHERE computer_id = %s", (computer_id,))
        if cur.fetchone():
            return jsonify({"error": "User with this Computer ID already exists!"}), 400

        cur.execute("INSERT INTO pending_users (computer_id, username, app_version) VALUES (%s, %s, %s)",
                    (computer_id, username, app_version))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Registration request submitted and awaiting admin approval."})

    except Exception as e:
        logger.error(f"Error in /register: {e}")
        return jsonify({"error": "An error occurred during registration."}), 500

@app.route('/approve_user', methods=['POST'])
def approve_user():
    computer_id = request.form.get('computer_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM pending_users WHERE computer_id = %s", (computer_id,))
        user = cur.fetchone()

        if user:
            cur.execute("INSERT INTO registered_users (computer_id, username, app_version) VALUES (%s, %s, %s)", user)
            cur.execute("DELETE FROM pending_users WHERE computer_id = %s", (computer_id,))
            conn.commit()
            cur.close()
            conn.close()
            return f"User {user[1]} approved successfully. <a href='/view_users'>Back to Users</a>"
        else:
            return f"Computer ID {computer_id} not found in pending approvals. <a href='/view_pending_users'>Back</a>", 404

    except Exception as e:
        logger.error(f"Error in /approve_user: {e}")
        return "An error occurred while approving the user.", 500

@app.route('/unregister_user', methods=['POST'])
def unregister_user():
    computer_id = request.form.get('computer_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM registered_users WHERE computer_id = %s RETURNING username", (computer_id,))
        unregistered_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if unregistered_user:
            return f"User {unregistered_user[0]} unregistered successfully. <a href='/view_users'>Back</a>"
        else:
            return f"Computer ID {computer_id} not found. <a href='/view_users'>Back</a>", 404

    except Exception as e:
        logger.error(f"Error in /unregister_user: {e}")
        return "An error occurred while unregistering the user.", 500

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    computer_id = data.get('computer_id')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username FROM registered_users WHERE computer_id = %s", (computer_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            return jsonify({"message": f"User {user[0]} is verified!"})
        else:
            return jsonify({"message": "Computer not registered!"}), 404

    except Exception as e:
        logger.error(f"Error in /verify: {e}")
        return jsonify({"error": "An error occurred during verification."}), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Bind to Railway’s assigned port
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)