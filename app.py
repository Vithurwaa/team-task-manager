import sqlite3
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect("database.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT,
    password TEXT,
    role TEXT
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    project_id INTEGER,
    assigned_to INTEGER,
    status TEXT,
    issue_date TEXT,
    due_date TEXT
)
""")

conn.commit()
conn.close()

print("Tables created")

# ---------------- APP ----------------
app = Flask(__name__)
app.secret_key = "secret123"

@app.route("/")
def home():
    return render_template("home.html")

# ---------------- AUTH ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

        conn = sqlite3.connect("database.db")
        conn.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, password, role)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row

        user = conn.execute(
            "SELECT * FROM users WHERE username=? OR email=?",
            (identifier, identifier)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- PROJECT ----------------
@app.route("/create_project", methods=["POST"])
def create_project():
    if session.get("role") != "Admin":
        return "Unauthorized"

    name = request.form["name"]

    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- TASK ----------------
@app.route("/create_task", methods=["POST"])
def create_task():
    if session.get("role") != "Admin":
        return "Unauthorized"

    title = request.form.get("title")
    project_id = request.form.get("project_id")
    assigned_to = request.form.get("assigned_to")
    issue_date = request.form.get("issue_date")
    due_date = request.form.get("due_date")

    conn = sqlite3.connect("database.db")
    conn.execute("""
        INSERT INTO tasks (title, project_id, assigned_to, status, issue_date, due_date)
        VALUES (?, ?, ?, 'Pending', ?, ?)
    """, (title, project_id, assigned_to, issue_date, due_date))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    projects = conn.execute("SELECT * FROM projects").fetchall()
    users = conn.execute("SELECT * FROM users").fetchall()

    if session.get("role") == "Admin":
        tasks = conn.execute("""
            SELECT tasks.id, tasks.title, tasks.status, tasks.due_date,
                   tasks.project_id, tasks.assigned_to as user_id,
                   projects.name as project_name,
                   users.username
            FROM tasks
            JOIN projects ON tasks.project_id = projects.id
            JOIN users ON tasks.assigned_to = users.id
        """).fetchall()
    else:
        tasks = conn.execute("""
            SELECT tasks.id, tasks.title, tasks.status, tasks.due_date,
                   tasks.project_id, tasks.assigned_to as user_id,
                   projects.name as project_name,
                   users.username
            FROM tasks
            JOIN projects ON tasks.project_id = projects.id
            JOIN users ON tasks.assigned_to = users.id
            WHERE tasks.assigned_to = ?
        """, (session["user_id"],)).fetchall()

    total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0]

    overdue = conn.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE due_date < date('now') AND status != 'Completed'
    """).fetchone()[0]

    tasks_per_user = conn.execute("""
        SELECT users.username, COUNT(tasks.id)
        FROM tasks
        JOIN users ON tasks.assigned_to = users.id
        GROUP BY users.username
    """).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        projects=projects,
        users=users,
        tasks=tasks,
        role=session.get("role"),
        total_tasks=total_tasks,
        pending=pending,
        completed=completed,
        overdue=overdue,
        tasks_per_user=tasks_per_user
    )

# ---------------- UPDATE ----------------
@app.route("/update_task/<int:id>")
def update_task(id):
    conn = sqlite3.connect("database.db")

    task = conn.execute("SELECT * FROM tasks WHERE id=?", (id,)).fetchone()
    new_status = "Completed" if task[4] == "Pending" else "Pending"

    conn.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, id))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- REMOVE ----------------
@app.route("/remove_user/<int:user_id>/<int:project_id>")
def remove_user(user_id, project_id):
    if session.get("role") != "Admin":
        return "Unauthorized"

    conn = sqlite3.connect("database.db")
    conn.execute(
        "DELETE FROM tasks WHERE assigned_to=? AND project_id=?",
        (user_id, project_id)
    )
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)