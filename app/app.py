from flask import Flask, render_template, request, redirect, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "echoes-secret-key"

# ---------------- DATABASE CONNECTION ----------------


db = mysql.connector.connect(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    user=os.environ.get("MYSQL_USER", "root"),
    password=os.environ.get("MYSQL_PASSWORD", "Gcet@123"),
    database=os.environ.get("MYSQL_DATABASE", "echoes"),
    port=int(os.environ.get("MYSQL_PORT", 3306))
)


def init_db():
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

# ---------------- HOME PAGE ----------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            return redirect("/dashboard")

        return "❌ Incorrect email or password."
    
    return render_template("login.html")
from flask import Flask, render_template, request, redirect, session, send_from_directory, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# ---- FOR EMAIL (development version) ----
RESET_CODE = {}  # stores reset codes temporarily

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if not user:
            return render_template("forgot_password.html", error="❌ Email not found")

        # create reset code
        import random
        code = random.randint(100000, 999999)
        RESET_CODE[email] = code

        return render_template("enter_code.html", email=email, code=code)  # for now show directly

    return render_template("forgot_password.html")


@app.route("/reset-password/<email>", methods=["POST"])
def reset_password(email):
    entered_code = request.form["code"]
    new_password = request.form["password"]

    # Check code
    if email not in RESET_CODE or str(RESET_CODE[email]) != entered_code:
        return "❌ Invalid code"

    hashed = generate_password_hash(new_password)

    cursor = db.cursor()
    cursor.execute("UPDATE users SET password=%s WHERE email=%s", (hashed, email))
    db.commit()

    RESET_CODE.pop(email)
    return redirect("/login")

# ---------------- SIGNUP (HASH PASSWORD) ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            return render_template("signup.html", error="⚠️ Email already exists.")

        hashed_password = generate_password_hash(password)

        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
                       (name, email, hashed_password))
        db.commit()
        return redirect("/login")

    return render_template("signup.html")

# ---------------- DASHBOARD (SEARCH + TAG DISPLAY) ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    search = request.args.get("search")
    emotion_filter = request.args.get("emotion")
    tag_filter = request.args.get("tag")  # <-- NEW

    cursor = db.cursor(dictionary=True)

    query = """
    SELECT memories.*, emotions.emotion_name,
    GROUP_CONCAT(tags.tag_name SEPARATOR ', ') AS tag_list
    FROM memories
    LEFT JOIN emotions ON memories.emotion_id = emotions.emotion_id
    LEFT JOIN memory_tags ON memories.memory_id = memory_tags.memory_id
    LEFT JOIN tags ON memory_tags.tag_id = tags.tag_id
    WHERE memories.user_id = %s
    """
    values = [user_id]

    # 🔍 Text search filter
    if search:
        query += " AND (memories.title LIKE %s OR memories.content LIKE %s)"
        values += [f"%{search}%", f"%{search}%"]

    # 💙 Emotion dropdown filter
    if emotion_filter and emotion_filter != "all":
        query += " AND emotions.emotion_name=%s"
        values.append(emotion_filter)

    # 🏷️ Tag click filter
    if tag_filter:
        query += " AND tags.tag_name = %s"
        values.append(tag_filter)

    # 📌 Group by memory to avoid duplicate rows
    query += " GROUP BY memories.memory_id"

    cursor.execute(query, values)
    memories = cursor.fetchall()

    # List of emotions for dropdown menu
    cursor.execute("SELECT emotion_name FROM emotions")
    emotion_list = cursor.fetchall()

    # List of all tags for display / filters
    cursor.execute("SELECT tag_name FROM tags ORDER BY tag_name ASC")
    all_tags = cursor.fetchall()

    # ✨ Emoji Mapping
    emoji_map = {
        "happy": "😊", "sad": "😢", "bittersweet": "💫", "confused": "😶‍🌫",
        "angry": "🔥", "nostalgic": "✨", "lonely": "🌙", "hopeful": "🌻"
    }

    for m in memories:
        m["emoji"] = emoji_map.get((m["emotion_name"] or "").lower(), "✨")

    return render_template("memories.html",
                           memories=memories,
                           emotion_list=emotion_list,
                           all_tags=all_tags)  # <-- IMPORTANT


# ---------------- FILE SERVING ----------------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ---------------- ADD MEMORY (TAGS INCLUDED) ----------------
@app.route("/add", methods=["GET", "POST"])
def add_memory():
    if "user_id" not in session:
        return redirect("/login")

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

        image = request.files.get("image")
        audio = request.files.get("audio")
        image_path = image.filename if image and image.filename else None
        audio_path = audio.filename if audio and audio.filename else None

        if image_path: image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_path))
        if audio_path: audio.save(os.path.join(app.config["UPLOAD_FOLDER"], audio_path))

        cursor.execute("""
            INSERT INTO memories (title, content, memory_date, user_id, emotion_id, image_path, audio_path)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (title, content, date, session["user_id"], emotion_id, image_path, audio_path))
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
            cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s,%s)", (memory_id, tag_id))
        db.commit()

        return redirect("/dashboard")

    return render_template("add_memory.html", tags=tags)

# ---------------- DELETE MEMORY ----------------
@app.route("/delete/<int:memory_id>")
def delete_memory(memory_id):
    if "user_id" not in session:
        return redirect("/login")
    cursor = db.cursor()
    cursor.execute("DELETE FROM memories WHERE memory_id=%s AND user_id=%s", (memory_id, session["user_id"]))
    db.commit()
    return redirect("/dashboard")

# ---------------- EDIT MEMORY (TAGS FIXED) ----------------
@app.route("/edit/<int:memory_id>", methods=["GET","POST"])
def edit_memory(memory_id):
    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM memories WHERE memory_id=%s AND user_id=%s", (memory_id, session["user_id"]))
    memory = cursor.fetchone()

    if not memory:
        return "❌ Memory not found."

    cursor.execute("SELECT * FROM tags")
    tags = cursor.fetchall()

    cursor.execute("SELECT tag_id FROM memory_tags WHERE memory_id=%s", (memory_id,))
    selected_tag_ids = [str(row["tag_id"]) for row in cursor.fetchall()]

    if request.method == "POST":
        new_title = request.form["title"]
        new_content = request.form["content"]
        new_date = request.form["date"]
        new_emotion = request.form["emotion"]

        if not new_emotion.isdigit():
            cursor.execute("INSERT INTO emotions (emotion_name) VALUES (%s)", (new_emotion,))
            db.commit()
            new_emotion = cursor.lastrowid

        image = request.files.get("image")
        audio = request.files.get("audio")

        image_path = image.filename if image and image.filename else memory["image_path"]
        audio_path = audio.filename if audio and audio.filename else memory["audio_path"]

        if image and image.filename: image.save(os.path.join(app.config["UPLOAD_FOLDER"], image_path))
        if audio and audio.filename: audio.save(os.path.join(app.config["UPLOAD_FOLDER"], audio_path))

        cursor.execute("""
            UPDATE memories
            SET title=%s, content=%s, memory_date=%s, emotion_id=%s,
                image_path=%s, audio_path=%s
            WHERE memory_id=%s AND user_id=%s
        """, (new_title, new_content, new_date, new_emotion, image_path, audio_path, memory_id, session["user_id"]))
        db.commit()

        # TAGS UPDATE
        cursor.execute("DELETE FROM memory_tags WHERE memory_id=%s", (memory_id,))
        selected_tags = request.form.getlist("selected_tags")
        new_tags = request.form.get("new_tags")

        if new_tags:
            for t in [x.strip() for x in new_tags.split(",") if x.strip()]:
                cursor.execute("INSERT INTO tags (tag_name) VALUES (%s)", (t,))
                db.commit()
                selected_tags.append(str(cursor.lastrowid))

        for tag_id in selected_tags:
            cursor.execute("INSERT INTO memory_tags (memory_id, tag_id) VALUES (%s,%s)", (memory_id, tag_id))
        db.commit()

        return redirect("/dashboard")

    return render_template("edit_memory.html", memory=memory, tags=tags, selected_tag_ids=selected_tag_ids)

# ---------------- WELCOME PAGE ----------------
@app.route("/welcome")
def welcome():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("welcome.html", name=session["name"])

# ---------------- RUN SERVER ----------------
try:
    init_db()
except Exception as e:
    print("DB init error:", e)



if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")

