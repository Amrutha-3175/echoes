from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "echoes-secret-key")

# --------------------------------------------------
# DATABASE CONNECTION (SAFE FOR RAILWAY)
# --------------------------------------------------

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        database=os.environ.get("MYSQL_DATABASE"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        connection_timeout=10
    )

# --------------------------------------------------
# DB INITIALIZATION
# --------------------------------------------------

def init_db():
    db = get_db()
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
        audio_path VARCHAR(255),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (emotion_id) REFERENCES emotions(emotion_id)
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
        tag_id INT,
        FOREIGN KEY (memory_id) REFERENCES memories(memory_id),
        FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
    )
    """)

    db.commit()
    cursor.close()
    db.close()

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
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

        return render_template("login.html", error="❌ Invalid credentials")

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        db = get_db()
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

    db = get_db()
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

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# --------------------------------------------------
# STARTUP
# --------------------------------------------------

with app.app_context():
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print("❌ DB init failed:", e)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=False
    )
