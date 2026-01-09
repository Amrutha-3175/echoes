from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "echoes-secret-key")

# ==================================================
# DATABASE CONNECTION HELPERS (RAILWAY SAFE)
# ==================================================

def get_server_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        autocommit=True
    )

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        database="echoes",
        port=int(os.environ.get("MYSQL_PORT", 3306))
    )

# ==================================================
# DATABASE INITIALIZATION
# ==================================================

def init_db():
    server = get_server_connection()
    cursor = server.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS echoes")
    cursor.close()
    server.close()

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(150) UNIQUE,
        password VARCHAR(255)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emotions (
        emotion_id INT AUTO_INCREMENT PRIMARY KEY,
        emotion_name VARCHAR(50)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        memory_id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(200),
        content TEXT,
        memory_date DATE,
        user_id INT,
        emotion_id INT,
        image_path VARCHAR(255),
        audio_path VARCHAR(255)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        tag_id INT AUTO_INCREMENT PRIMARY KEY,
        tag_name VARCHAR(50)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory_tags (
        memory_id INT,
        tag_id INT
    )
    """)

    db.commit()
    cursor.close()
    db.close()

# ==================================================
# ROUTES
# ==================================================

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        email = request.form["email"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            return render_template("signup.html", error="Email already exists")

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
            (name, email, password)
        )
        db.commit()
        cursor.close()
        db.close()

        return redirect("/login")

    return render_template("signup.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT memories.*, emotions.emotion_name,
    GROUP_CONCAT(tags.tag_name SEPARATOR ', ') AS tag_list
    FROM memories
    LEFT JOIN emotions ON memories.emotion_id = emotions.emotion_id
    LEFT JOIN memory_tags ON memories.memory_id = memory_tags.memory_id
    LEFT JOIN tags ON memory_tags.tag_id = tags.tag_id
    WHERE memories.user_id=%s
    GROUP BY memories.memory_id
    """, (session["user_id"],))

    memories = cursor.fetchall()

    cursor.execute("SELECT emotion_name FROM emotions")
    emotion_list = cursor.fetchall()

    cursor.execute("SELECT tag_name FROM tags ORDER BY tag_name")
    all_tags = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "memories.html",
        memories=memories,
        emotion_list=emotion_list,
        all_tags=all_tags
    )

# ---------------- ADD MEMORY (ONLY ONE VERSION) ----------------
@app.route("/add", methods=["GET", "POST"])
def add_memory():
    if "user_id" not in session:
        return redirect("/login")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tags")
    tags = cursor.fetchall()

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        date = request.form["date"]
        emotion_input = request.form["emotion"]

        if emotion_input.isdigit():
            emotion_id = int(emotion_input)
        else:
            cursor.execute("INSERT INTO emotions (emotion_name) VALUES (%s)", (emotion_input,))
            db.commit()
            emotion_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO memories (title, content, memory_date, user_id, emotion_id)
        VALUES (%s,%s,%s,%s,%s)
        """, (title, content, date, session["user_id"], emotion_id))
        db.commit()

        memory_id = cursor.lastrowid

        selected_tags = request.form.getlist("selected_tags")
        new_tags = request.form.get("new_tags")

        if new_tags:
            for t in [x.strip() for x in new_tags.split(",") if x.strip()]:
                cursor.execute("INSERT INTO tags (tag_name) VALUES (%s)", (t,))
                db.commit()
                selected_tags.append(str(cursor.lastrowid))

        for tag_id in selected_tags:
            cursor.execute(
                "INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s,%s)",
                (memory_id, tag_id)
            )
        db.commit()

        cursor.close()
        db.close()
        return redirect("/dashboard")

    cursor.close()
    db.close()
    return render_template("add_memory.html", tags=tags)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ==================================================
# STARTUP
# ==================================================

try:
    init_db()
    print("✅ Database ready")
except Exception as e:
    print("❌ DB init error:", e)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=False
    )
