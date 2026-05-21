import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
import mysql.connector


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")


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


load_local_env()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret")


def db_config(include_database=True):
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "qwzx12,."),
    }
    if include_database:
        config["database"] = os.getenv("DB_NAME", "student_db")
    return config


def get_db_connection(include_database=True):
    return mysql.connector.connect(**db_config(include_database=include_database))


def init_db():
    database = os.getenv("DB_NAME", "student_db")
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
            role VARCHAR(20) NOT NULL
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
                ("admin", "Admin@123", "admin"),
                ("student", "Student@123", "user"),
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


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = (
            "SELECT username, role FROM users "
            f"WHERE username = '{username}' AND password = '{password}' LIMIT 1"
        )
        cursor.execute(query)
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        return "Invalid credentials"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        role = request.form.get("role", "user")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO users (username, password, role) VALUES ('{username}', '{password}', '{role}')"
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

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
def admin_panel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        username = request.form.get("username", "")
        role = request.form.get("role", "")
        cursor.execute(f"UPDATE users SET role = '{role}' WHERE username = '{username}'")
        conn.commit()

    cursor.execute("SELECT username, role FROM users ORDER BY username")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("admin.html", username=session.get("username"), users=users)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return "No file selected"

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        filename = os.path.basename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return f"File {filename} uploaded successfully!"

    return render_template("upload.html")


@app.route("/student/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        course = request.form.get("course", "")
        year = request.form.get("year", "1")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO students (name, email, course, year) VALUES ('{name}', '{email}', '{course}', '{year}')"
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    return render_template("student_form.html", action="Add", student=None)


@app.route("/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT id, name, email, course, year FROM students WHERE id = {student_id}")
    student = cursor.fetchone()

    if not student:
        cursor.close()
        conn.close()
        return "Student not found", 404

    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        course = request.form.get("course", "")
        year = request.form.get("year", "1")
        cursor.execute(
            "UPDATE students "
            f"SET name = '{name}', email = '{email}', course = '{course}', year = '{year}' "
            f"WHERE id = {student_id}"
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.close()
    conn.close()
    return render_template("student_form.html", action="Edit", student=student)


@app.route("/student/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM students WHERE id = {student_id}")
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/api/students")
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
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("DEBUG", "True").lower() == "true",
        use_reloader=False,
    )
