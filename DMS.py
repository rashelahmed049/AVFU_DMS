from flask import Flask, render_template, request, redirect, session, flash, send_file, url_for
from werkzeug.utils import secure_filename
import os
import sqlite3
from datetime import datetime
import time
import pandas as pd
import shutil
import mammoth

ALLOWED_FILE = os.path.join(os.path.dirname(__file__), "AVFU_CVSC_All_Teachers.xlsx")

DB_NAME = os.path.join(os.path.dirname(__file__), "dms.db")
print("DMS Database:", DB_NAME)

from display_activity import (
    init_db,
    create_user,
    get_user_password,
    login_user,
    logout_user,
    add_activity,
    get_all_activity,
    get_filtered_activity,
    get_all_users,
    make_admin,
    verify_admin
)
app = Flask(__name__)
app.secret_key = "dms_secret"
init_db()

# =========================
# ADMIN CONFIGURATION
# =========================

ADMIN_ALLOWED_IPS = [
    "127.0.0.1",   # Localhost
    "::1"          # IPv6 Localhost
]

# =========================
# BASE PATHS
# =========================
BASE_DIR = os.path.abspath(r"G:\Rasel\Projects\Python_Project\DMS\uploads")
TRASH_DIR = os.path.abspath(r"G:\Rasel\Projects\Python_Project\DMS\trash")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(TRASH_DIR, exist_ok=True)

def get_allowed_emails():
    df = pd.read_excel(ALLOWED_FILE)
    return set(df["email"].str.strip().str.lower())
# =========================
# PATH SAFETY HELPERS
# =========================
def normalize_path(p: str) -> str:
    if not p:
        return ""
    return p.replace("\\", "/").lstrip("/").strip()


def safe_path(relative_path: str = "") -> str:
    relative_path = normalize_path(relative_path)
    target = os.path.abspath(os.path.join(BASE_DIR, relative_path))

    if not target.startswith(BASE_DIR):
        raise Exception("Invalid path access blocked")

    return target


# =========================
# LOGIN
# =========================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        stored_password = get_user_password(email)

        if stored_password and stored_password == password:
            session["user"] = email
            login_user(email)
            add_activity(
                email,
                "LOGIN",
                details=f"IP={request.remote_addr}"
            )
            return redirect("/dashboard")

        flash("Invalid Email or Password", "error")
        return redirect("/")

    return render_template("DMS_Login.html")
ADMIN_ALLOWED_IPS = [
    "127.0.0.1",
    "::1",
    # "192.168.1.10"   # Add your PC's LAN IP if needed
]

# =========================
# ADMIN LOGIN
# =========================
@app.route("/admin-login", methods=["POST"])
def admin_login():

    # Allow only your PC
    if request.remote_addr not in ADMIN_ALLOWED_IPS:
        return """
        <script>
            alert("Only Administrator can access.");
            window.history.back();
        </script>
        """

    email = request.form["email"].strip().lower()
    password = request.form["password"].strip()

    # Verify admin from database
    if verify_admin(email, password):

        session["admin"] = email

        flash("Administrator login successful.", "success")

        return redirect("/activity")

    return """
    <script>
        alert("Invalid Administrator credentials.");
        window.history.back();
    </script>
    """

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        confirm = request.form["confirm"].strip()

        # 🔥 STEP 1: load allowed emails
        allowed_emails = get_allowed_emails()

        # 🔴 BLOCK if email not in Excel
        if email not in allowed_emails:
            flash("You are not authorized to register!", "error")
            return redirect("/register")

        if password != confirm:
            flash("Passwords do not match!", "error")
            return redirect("/register")

        if get_user_password(email):
            flash("User already exists!", "error")
            return redirect("/register")

        create_user(email, password)

        flash("Registration successful! Please login.", "success")
        return redirect("/")
    
    return render_template("DMS_Register.html")


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.args.get("path", ""))
    current_dir = safe_path(path)

    items = []

    if os.path.exists(current_dir):
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)

            items.append({
                "name": item,
                "is_dir": os.path.isdir(item_path)
            })

    add_activity(
        session["user"],
        "OPEN_DASHBOARD",
        details=f"Path={path}"
    )

    logs = get_all_activity()

    return render_template(
        "DMS_File_Explorer.html",
        user=session["user"],
        items=items,
        path=path,
        logs=logs
    )


# =========================
# CREATE FOLDER
# =========================
@app.route("/create_folder", methods=["POST"])
def create_folder():
    if "user" not in session:
        return redirect("/")

    folder_name = secure_filename(request.form["folder_name"])
    path = normalize_path(request.form.get("path", ""))

    target_dir = safe_path(os.path.join(path, folder_name))
    os.makedirs(target_dir, exist_ok=True)

    add_activity(
        session["user"],
        "CREATE_FOLDER",
        folder_name,
        f"Path={path}"
    )

    return redirect(f"/dashboard?path={path}")


# =========================
# UPLOAD FILE
# =========================
@app.route('/upload', methods=['POST'])
def upload():
    path = request.form.get('path', '')
    files = request.files.getlist('file')

    upload_folder = os.path.join(BASE_DIR, path)

    os.makedirs(upload_folder, exist_ok=True)

    for file in files:
        if file.filename != '':
            save_path = os.path.join(upload_folder, file.filename)
            file.save(save_path)

            # 🔥 ADD LOG HERE
            add_activity(
                session["user"],
                "UPLOAD_FILE",
                file.filename,
                f"Path={path}"
            )

    return redirect(url_for('dashboard', path=path))


# =========================
# DOWNLOAD FILE
# =========================
@app.route("/download")
def download():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.args.get("path", ""))
    filename = request.args.get("file")

    file_path = safe_path(os.path.join(path, filename))

    if not os.path.exists(file_path):
        flash("File not found", "error")
        return redirect(f"/dashboard?path={path}")

    add_activity(
        session["user"],
        "DOWNLOAD_FILE",
        filename,
        f"Path={path}"
    )

    return send_file(file_path, as_attachment=True)


# =========================
# RENAME FILE
# =========================
@app.route("/rename", methods=["POST"])
def rename():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.form.get("path", ""))
    old_name = secure_filename(request.form.get("old_name"))
    new_name = secure_filename(request.form.get("new_name"))

    old_path = safe_path(os.path.join(path, old_name))
    new_path = safe_path(os.path.join(path, new_name))

    if not os.path.exists(old_path):
        flash("File not found", "error")
        return redirect(f"/dashboard?path={path}")

    os.rename(old_path, new_path)

    add_activity(
        session["user"],
        "RENAME",
        old_name,
        f"New Name={new_name}"
    )

    return redirect(f"/dashboard?path={path}")


# =========================
# VIEW FILE (TEXT ONLY)
# =========================
from docx import Document

@app.route("/view")
def view():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.args.get("path", ""))
    filename = request.args.get("file")

    file_path = safe_path(os.path.join(path, filename))

    if not os.path.exists(file_path):
        return "File not found", 404

    ext = filename.lower()

    # ======================
    # PDF
    # ======================
    if ext.endswith(".pdf"):
        return send_file(file_path)

    # ======================
    # IMAGES
    # ======================
    if ext.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
        return f"""
        <html>
        <body style="text-align:center;">
            <img src="/download?path={path}&file={filename}" style="max-width:90%;margin-top:20px;">
        </body>
        </html>
        """

    # ======================
    # EXCEL
    # ======================
    if ext.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file_path)
        return df.to_html(classes="table table-bordered", index=False)

    # ======================
    # WORD (.docx only)
    # ======================
    if filename.lower().endswith(".docx"):
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value

    # ======================
    # TEXT FILES
    # ======================
    if ext.endswith((".txt", ".py", ".log", ".csv")):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return f"<pre style='padding:20px'>{content}</pre>"

    # ======================
    # FALLBACK
    # ======================
    return send_file(file_path, as_attachment=True)
        
@app.route("/download_folder")
def download_folder():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.args.get("path", ""))
    folder = request.args.get("folder")

    folder_path = safe_path(os.path.join(path, folder))

    if not os.path.exists(folder_path):
        flash("Folder not found", "error")
        return redirect(f"/dashboard?path={path}")

    # Create zip name
    zip_name = f"{folder}_{int(time.time())}"
    zip_full_path = os.path.join(TRASH_DIR, zip_name)

    # Create zip (WITHOUT .zip extension added automatically)
    shutil.make_archive(zip_full_path, 'zip', folder_path)

    zip_file = zip_full_path + ".zip"

    add_activity(
        session["user"],
        "DOWNLOAD_FOLDER",
        folder,
        f"Path={path}"
    )

    return send_file(zip_file, as_attachment=True)


@app.route("/delete")
def delete():
    if "user" not in session:
        return redirect("/")

    path = normalize_path(request.args.get("path", ""))
    filename = request.args.get("file")

    src = safe_path(os.path.join(path, filename))

    if not os.path.exists(src):
        flash("File not found", "error")
        return redirect(f"/dashboard?path={path}")

    # create unique filename in trash
    base_name, ext = os.path.splitext(filename)
    timestamp = int(time.time())

    new_filename = f"{base_name}_{timestamp}{ext}"
    dst = os.path.join(TRASH_DIR, new_filename)

    os.rename(src, dst)

    add_activity(
        session["user"],
        "DELETE_FILE",
        filename,
        f"Moved to Trash as {new_filename}"
    )

    return redirect(f"/dashboard?path={path}")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    user = session.get("user")

    if user:
        logout_user(user)
        add_activity(
            user,
            "LOGOUT"
        )

    session.clear()
    return redirect("/")



@app.route("/activity")
def activity():

    if "admin" not in session:
        flash("Administrator access required.", "error")
        return redirect("/dashboard")

    user = request.args.get("user", "").strip()

    action = request.args.get("action", "").strip()

    filename = request.args.get("filename", "").strip()

    from_date = request.args.get("from_date", "").strip()

    to_date = request.args.get("to_date", "").strip()

    logs = get_filtered_activity(
        user,
        action,
        filename,
        from_date,
        to_date
    )

    users = get_all_users()

    return render_template(
        "DMS_admin_dashboard.html",
        logs=logs,
        users=users,
        user=session["admin"]
    )
    
  
if __name__ == "__main__":
    print("DMS Database:", os.path.abspath(DB_NAME))
    app.run(host="0.0.0.0", port=5000, debug=True)