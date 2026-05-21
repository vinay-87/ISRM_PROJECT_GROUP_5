from functools import wraps
import os
import re
import secrets
import time

import bcrypt
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
import mysql.connector
from mysql.connector import Error as MySQLError
from werkzeug.utils import secure_filename

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    Limiter = None

    def get_remote_address():
        return "127.0.0.1"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
LOGIN_ATTEMPTS = {}
LOGIN_LIMIT = 5
LOGIN_WINDOW_SECONDS = 60


def load_local_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def project_path(path):
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


load_local_env()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
app.config.update(
    UPLOAD_FOLDER=project_path(os.getenv("UPLOAD_FOLDER", UPLOAD_FOLDER)),
    AUDIT_LOG_PATH=project_path(os.getenv("AUDIT_LOG_PATH", os.path.join(BASE_DIR, "instance", "audit.log"))),
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    RATE_LIMIT_ENABLED=os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true",
)

if Limiter:
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
        enabled=False,
    )
else:
    class NoopLimiter:
        def limit(self, _rule):
            def decorator(view):
                return view

            return decorator

    limiter = NoopLimiter()


def db_config(include_database=True):
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
    }
    if include_database:
        config["database"] = os.getenv("DB_NAME", "student_db_secure")
    return config


def get_db_connection(include_database=True):
    return mysql.connector.connect(**db_config(include_database=include_database))


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, stored_hash):
    if not stored_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def init_db():
    database = os.getenv("DB_NAME", "student_db_secure")
    conn = get_db_connection(include_database=False)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}`")
    cursor.close()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            CHECK (role IN ('admin', 'user'))
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            email VARCHAR(150) NOT NULL,
            course VARCHAR(120) NOT NULL,
            year INT NOT NULL
        )
        """
    )
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
            [
                ("admin", hash_password("Admin@123"), "admin"),
                ("student", hash_password("Student@123"), "user"),
            ],
        )
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO students (name, email, course, year) VALUES (%s, %s, %s, %s)",
            [
                ("Asha Mehta", "asha.mehta@example.edu", "Information Security", 3),
                ("Rohan Singh", "rohan.singh@example.edu", "Data Science", 2),
                ("Mira Kapoor", "mira.kapoor@example.edu", "Software Engineering", 4),
            ],
        )
    conn.commit()
    cursor.close()
    conn.close()


def generate_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf_token():
    form_token = request.form.get("csrf_token", "")
    return bool(form_token) and secrets.compare_digest(form_token, session.get("csrf_token", ""))


def csrf_protect():
    if request.method == "POST" and not validate_csrf_token():
        return "Invalid request token", 400
    return None


def client_key():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "local").split(",")[0].strip()


def login_is_rate_limited():
    if not app.config.get("RATE_LIMIT_ENABLED", True):
        return False
    now = time.time()
    key = client_key()
    attempts = [attempt for attempt in LOGIN_ATTEMPTS.get(key, []) if now - attempt < LOGIN_WINDOW_SECONDS]
    LOGIN_ATTEMPTS[key] = attempts
    return len(attempts) >= LOGIN_LIMIT


def record_failed_login():
    if app.config.get("RATE_LIMIT_ENABLED", True):
        LOGIN_ATTEMPTS.setdefault(client_key(), []).append(time.time())


def clear_failed_logins():
    LOGIN_ATTEMPTS.pop(client_key(), None)


def audit_event(action, actor, detail):
    os.makedirs(os.path.dirname(app.config["AUDIT_LOG_PATH"]), exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(app.config["AUDIT_LOG_PATH"], "a", encoding="utf-8") as audit_file:
        audit_file.write(f"{timestamp} | {actor or 'anonymous'} | {action} | {detail}\n")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_strong_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"[0-9]", password)
        and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            return "Access denied", 403
        return view(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_security_helpers():
    return {"csrf_token": generate_csrf_token}


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            return csrf_error
        if login_is_rate_limited():
            return "Too many login attempts. Please wait and try again.", 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username, password, role FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and verify_password(password, user["password"]):
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            generate_csrf_token()
            clear_failed_logins()
            return redirect(url_for("dashboard"))

        record_failed_login()
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            return csrf_error

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Username is required.", "error")
            return render_template("register.html"), 400
        if not is_strong_password(password):
            flash("Use at least 8 characters with upper, lower, number, and special character.", "error")
            return render_template("register.html"), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')",
                (username, hash_password(password)),
            )
            conn.commit()
        except MySQLError:
            flash("That username is already registered.", "error")
            return render_template("register.html"), 409
        finally:
            cursor.close()
            conn.close()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, course, year FROM students ORDER BY id")
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"],
        students=students,
    )


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_panel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            cursor.close()
            conn.close()
            return csrf_error

        username = request.form.get("username", "").strip()
        role = request.form.get("role", "").strip()
        if role not in {"admin", "user"}:
            cursor.close()
            conn.close()
            return "Invalid role", 400
        cursor.execute("UPDATE users SET role = %s WHERE username = %s", (role, username))
        conn.commit()
        audit_event("role_update", session.get("username"), f"{username} -> {role}")
        flash(f"Updated role for {username}.", "success")

    cursor.execute("SELECT username, role FROM users ORDER BY username")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("admin.html", username=session.get("username"), users=users)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            return csrf_error

        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No file selected.", "error")
            return render_template("upload.html"), 400

        if not allowed_file(file.filename):
            flash("File type not allowed.", "error")
            return render_template("upload.html"), 400

        filename = secure_filename(file.filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        audit_event("file_upload", session.get("username"), filename)
        flash(f"Uploaded {filename} successfully.", "success")
        return redirect(url_for("upload"))

    return render_template("upload.html")


@app.route("/student/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            return csrf_error

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        year = request.form.get("year", "").strip()

        if not all([name, email, course, year]) or not year.isdigit():
            flash("Enter a valid name, email, course, and numeric year.", "error")
            return render_template("student_form.html", action="Add", student=None), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, email, course, year) VALUES (%s, %s, %s, %s)",
            (name, email, course, int(year)),
        )
        conn.commit()
        cursor.close()
        conn.close()
        audit_event("student_add", session.get("username"), email)
        return redirect(url_for("dashboard"))

    return render_template("student_form.html", action="Add", student=None)


@app.route("/student/edit/<int:student_id>", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, course, year FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        return "Student not found", 404

    if request.method == "POST":
        csrf_error = csrf_protect()
        if csrf_error:
            cursor.close()
            conn.close()
            return csrf_error

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        course = request.form.get("course", "").strip()
        year = request.form.get("year", "").strip()

        if not all([name, email, course, year]) or not year.isdigit():
            cursor.close()
            conn.close()
            flash("Enter a valid name, email, course, and numeric year.", "error")
            return render_template("student_form.html", action="Edit", student=student), 400

        cursor.execute(
            "UPDATE students SET name = %s, email = %s, course = %s, year = %s WHERE id = %s",
            (name, email, course, int(year), student_id),
        )
        conn.commit()
        cursor.close()
        conn.close()
        audit_event("student_edit", session.get("username"), f"student_id={student_id}")
        return redirect(url_for("dashboard"))

    cursor.close()
    conn.close()
    return render_template("student_form.html", action="Edit", student=student)


@app.route("/student/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    csrf_error = csrf_protect()
    if csrf_error:
        return csrf_error

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()
    audit_event("student_delete", session.get("username"), f"student_id={student_id}")
    flash("Student record deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/api/students")
@admin_required
def api_students():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, course, year FROM students ORDER BY id")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({"students": students})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5001")),
        debug=os.getenv("DEBUG", "False").lower() == "true",
        use_reloader=False,
    )
