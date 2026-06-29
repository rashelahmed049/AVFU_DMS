import sqlite3
from datetime import datetime
import os
import pandas as pd

DB_NAME = os.path.join(os.path.dirname(__file__), "dms.db")


# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
            )
            """)
        # Add admin column if database already exists
    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_admin INTEGER DEFAULT 0
        """)
    except:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS login_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        login_time TEXT,
        logout_time TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        action TEXT,
        item_name TEXT,
        details TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================
# USER FUNCTIONS
# =========================
def create_user(email, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO users (email, password)
        VALUES (?, ?)
    """, (email.strip().lower(), password.strip()))

    conn.commit()
    conn.close()


def get_user_password(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT password FROM users WHERE email=?
    """, (email.strip().lower(),))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None
# =========================
# ADMIN FUNCTIONS
# =========================

def make_admin(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET is_admin = 1
        WHERE email = ?
    """, (email.strip().lower(),))

    conn.commit()
    conn.close()


def verify_admin(email, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        WHERE email = ?
        AND password = ?
        AND is_admin = 1
    """, (
        email.strip().lower(),
        password.strip()
    ))

    admin = cursor.fetchone()

    conn.close()

    return admin is not None
    


# =========================
# LOGIN / LOGOUT TRACKING
# =========================
def login_user(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO login_sessions (user_email, login_time)
        VALUES (?, ?)
    """, (email, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def logout_user(email):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE login_sessions
        SET logout_time=?
        WHERE user_email=?
        AND logout_time IS NULL
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), email))

    conn.commit()
    conn.close()


# =========================
# ACTIVITY LOGGING
# =========================
def add_activity(user, action, item_name="", details=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Create HUMAN readable message
    description = ""

    if action == "LOGIN":
        description = f"{user} logged into the system"

    elif action == "LOGOUT":
        description = f"{user} logged out of the system"

    elif action == "UPLOAD_FILE":
        description = f"{user} uploaded file '{item_name}' to {details}"

    elif action == "DELETE_FILE":
        description = f"{user} deleted file '{item_name}' (moved to trash)"

    elif action == "CREATE_FOLDER":
        description = f"{user} created folder '{item_name}' in {details}"

    elif action == "RENAME":
        description = f"{user} renamed file '{item_name}' ({details})"

    elif action == "DOWNLOAD_FILE":
        description = f"{user} downloaded file '{item_name}'"

    elif action == "VIEW_FILE":
        description = f"{user} viewed file '{item_name}'"

    else:
        description = f"{user} performed {action} on {item_name} ({details})"

    cursor.execute("""
        INSERT INTO activity_logs
        (user_email, action, item_name, details, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user,
        action,
        item_name,
        description,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_all_activity():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_email, action, item_name, timestamp
        FROM activity_logs
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


# =========================
# EXCEL EXPORT
# =========================
def export_to_excel():
    conn = sqlite3.connect(DB_NAME)

    df_login = pd.read_sql_query("""
        SELECT id, user_email, login_time, logout_time
        FROM login_sessions
        ORDER BY id DESC
    """, conn)

    df_activity = pd.read_sql_query("""
        SELECT id, user_email, action, item_name, details, timestamp
        FROM activity_logs
        ORDER BY id DESC
    """, conn)

    conn.close()

    output_file = os.path.join(
        os.path.dirname(__file__),
        "DMS_Audit_Report.xlsx"
    )

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_login.to_excel(writer, sheet_name="Login_Sessions", index=False)
        df_activity.to_excel(writer, sheet_name="Activity_Logs", index=False)

    print("Excel report generated at:", output_file)
def get_filtered_activity(user="", action="", filename="", from_date="", to_date=""):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = """
        SELECT
            user_email,
            action,
            item_name,
            timestamp
        FROM activity_logs
        WHERE 1=1
    """

    params = []

    # User Email
    if user:
        query += " AND user_email LIKE ?"
        params.append(f"%{user}%")

    # Action
    if action:
        query += " AND action = ?"
        params.append(action)

    # Filename
    if filename:
        query += " AND item_name LIKE ?"
        params.append(f"%{filename}%")

    # From Date
    if from_date:
        query += " AND DATE(timestamp) >= DATE(?)"
        params.append(from_date)

    # To Date
    if to_date:
        query += " AND DATE(timestamp) <= DATE(?)"
        params.append(to_date)

    query += " ORDER BY timestamp DESC"

    cursor.execute(query, params)

    logs = cursor.fetchall()

    conn.close()

    return logs

def get_all_users():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT user_email
        FROM activity_logs
        ORDER BY user_email
    """)

    users = [row[0] for row in cursor.fetchall()]

    conn.close()

    return users

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    init_db()
    export_to_excel()