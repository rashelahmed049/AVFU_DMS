import sqlite3
import os

DB_NAME = os.path.join(os.path.dirname(__file__), "dms.db")

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Check columns before
print("Before:")
cursor.execute("PRAGMA table_info(users)")
for row in cursor.fetchall():
    print(row)

print("\nAdding column...")

try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    conn.commit()
    print("✅ Column added successfully.")
except Exception as e:
    print("Error:", e)

# Check columns after
print("\nAfter:")
cursor.execute("PRAGMA table_info(users)")
for row in cursor.fetchall():
    print(row)

conn.close()