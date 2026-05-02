from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        project_id INTEGER,
        assigned_to INTEGER,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()
init_db()
app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

        conn = sqlite3.connect("database.db")
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["role"] = user[3]
            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/create_project", methods=["POST"])
def create_project():
    if session.get("role") != "Admin":
        return "Unauthorized"

    name = request.form["name"]

    if not name:
        return redirect("/dashboard")

    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

@app.route("/create_task", methods=["POST"])
def create_task():
    if session.get("role") != "Admin":
        return "Unauthorized"

    title = request.form.get("title")
    project_id = request.form.get("project_id")
    assigned_to = request.form.get("assigned_to")

    if not title or not project_id or not assigned_to:
        return "Missing data"

    conn = sqlite3.connect("database.db")
    conn.execute("""
        INSERT INTO tasks (title, project_id, assigned_to, status)
        VALUES (?, ?, ?, 'Pending')
    """, (title, project_id, assigned_to))
    conn.commit()
    conn.close()

    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    if session["role"] == "Admin":
        tasks = conn.execute("""
            SELECT tasks.*, projects.name AS project_name, users.username
            FROM tasks
            JOIN projects ON tasks.project_id = projects.id
            JOIN users ON tasks.assigned_to = users.id
        """).fetchall()
    else:
        tasks = conn.execute("""
            SELECT tasks.*, projects.name AS project_name, users.username
            FROM tasks
            JOIN projects ON tasks.project_id = projects.id
            JOIN users ON tasks.assigned_to = users.id
            WHERE assigned_to=?
        """, (session["user_id"],)).fetchall()

    users = conn.execute("SELECT * FROM users").fetchall()
    projects = conn.execute("SELECT * FROM projects").fetchall()

    conn.close()

    return render_template("dashboard.html", tasks=tasks, users=users, projects=projects, role=session["role"])

@app.route("/update_task/<int:id>")
def update_task(id):
    conn = sqlite3.connect("database.db")

    task = conn.execute(
        "SELECT * FROM tasks WHERE id=?",
        (id,)
    ).fetchone()

    new_status = "Completed" if task[4] == "Pending" else "Pending"

    conn.execute(
        "UPDATE tasks SET status=? WHERE id=?",
        (new_status, id)
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)