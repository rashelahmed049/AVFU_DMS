import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "dms.db")

print("Database:", DB_NAME)

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Count users
cursor.execute("SELECT COUNT(*) FROM users")
count = cursor.fetchone()[0]
print("Total users:", count)

# Show all users
cursor.execute("SELECT id, email, password, is_admin FROM users")
rows = cursor.fetchall()

print("\nRows:")
for row in rows:
    print(row)

conn.close()