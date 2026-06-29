import sqlite3
import pandas as pd
import os

DB_NAME = "dms.db"

def export_to_excel():
    conn = sqlite3.connect(DB_NAME)

    df_login = pd.read_sql_query("""
        SELECT user_email, login_time, logout_time
        FROM login_sessions
        ORDER BY id DESC
    """, conn)

    df_activity = pd.read_sql_query("""
        SELECT user_email, action, item_name, details, timestamp
        FROM activity_logs
        ORDER BY id DESC
    """, conn)

    conn.close()

    file_path = os.path.join(os.path.dirname(__file__), "DMS_Audit_Report.xlsx")

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        df_login.to_excel(writer, sheet_name="Login_Sessions", index=False)
        df_activity.to_excel(writer, sheet_name="Activity_Logs", index=False)

    print("Excel generated at:", file_path)


export_to_excel()