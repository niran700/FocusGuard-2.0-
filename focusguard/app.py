import json
import os
import webbrowser
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import psutil
import threading
import time
from datetime import datetime

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "focusguard-demo-key-2026"

USERS_FILE = "users.json"
BLOCKED_FILE = "blocked.json"
GOALS_FILE = "goals.json"
STATS_FILE = "user_stats.json"
SESSION_HISTORY_FILE = "session_history.json"

blocking_active = False
blocking_thread = None


def load_users():
    """Load users from JSON file."""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_users(users):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def load_blocked():
    """Load blocked apps from JSON file."""
    if os.path.exists(BLOCKED_FILE):
        with open(BLOCKED_FILE, "r") as f:
            return json.load(f)
    return []


def save_blocked(blocked):
    """Save blocked apps to JSON file."""
    with open(BLOCKED_FILE, "w") as f:
        json.dump(blocked, f, indent=2)


def load_goals():
    """Load goals from JSON file."""
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE, "r") as f:
            return json.load(f)
    return []


def save_goals(goals):
    """Save goals to JSON file."""
    with open(GOALS_FILE, "w") as f:
        json.dump(goals, f, indent=2)


def load_user_stats(user_email):
    """Load stats for a specific user."""
    all_stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            all_stats = json.load(f)
    
    if user_email not in all_stats:
        all_stats[user_email] = {
            "focus_time": 0,
            "distraction_time": 0,
            "completed_sessions": 0,
            "incomplete_sessions": 0,
            "exit_attempts": 0
        }
    
    # Ensure exit_attempts field exists for legacy data
    if "exit_attempts" not in all_stats[user_email]:
        all_stats[user_email]["exit_attempts"] = 0
    
    return all_stats[user_email]


def save_user_stats(user_email, stats):
    """Save stats for a specific user."""
    all_stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            all_stats = json.load(f)
    
    all_stats[user_email] = stats
    
    with open(STATS_FILE, "w") as f:
        json.dump(all_stats, f, indent=2)


def load_session_history_data():
    """Load all users session history from JSON file."""
    if os.path.exists(SESSION_HISTORY_FILE):
        with open(SESSION_HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_session_history_data(history_data):
    """Persist all users session history to JSON file."""
    with open(SESSION_HISTORY_FILE, "w") as f:
        json.dump(history_data, f, indent=2)


def add_session_history_entry(user_email, duration_minutes, exit_attempts):
    """Append one completed focus session with date/time for a user."""
    history_data = load_session_history_data()
    if user_email not in history_data:
        history_data[user_email] = []

    now = datetime.now()
    history_data[user_email].insert(0, {
        "duration_minutes": duration_minutes,
        "exit_attempts": exit_attempts,
        "completed_at": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%I:%M %p")
    })

    save_session_history_data(history_data)


def get_user_session_history(user_email):
    """Return one user's completed focus sessions (newest first)."""
    history_data = load_session_history_data()
    return history_data.get(user_email, [])


def update_session_stats(user_email, duration_minutes, completed, exit_attempts):
    """Update user stats after a session."""
    stats = load_user_stats(user_email)
    
    stats["focus_time"] += duration_minutes
    stats["distraction_time"] += exit_attempts * 2  # 2 minutes per exit attempt
    stats["exit_attempts"] += exit_attempts  # Track total exit attempts
    
    if completed:
        stats["completed_sessions"] += 1
    else:
        stats["incomplete_sessions"] += 1
    
    save_user_stats(user_email, stats)



@app.route("/")
def index():
    """Redirect to login or dashboard based on session."""
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Login page and form handler."""
    if request.method == "POST":
        user = request.form.get("user", "").strip()
        password = request.form.get("password", "").strip()

        if not user or not password:
            return render_template("login.html", error="Email/Username and password required")

        users = load_users()
        if user in users and check_password_hash(users[user], password):
            session["user"] = user
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    """Signup page and form handler."""
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not all([fullname, email, password, confirm]):
            return render_template("signup.html", error="All fields required")

        if password != confirm:
            return render_template("signup.html", error="Passwords do not match")

        if len(password) < 6:
            return render_template("signup.html", error="Password must be at least 6 characters")

        users = load_users()
        if email in users:
            return render_template("signup.html", error="Account already exists")

        users[email] = generate_password_hash(password)
        save_users(users)

        session["user"] = email
        return redirect(url_for("dashboard"))

    return render_template("signup.html")


@app.route("/dashboard")
def dashboard():
    """Protected dashboard with user buttons."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    # Extract username from email (part before @)
    email = session["user"]
    username = email.split("@")[0] if "@" in email else email
    return render_template("dashboard.html", username=username)


@app.route("/focus")
def focus_mode():
    """Focus mode page."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("focus.html")


@app.route("/stats")
def stats():
    """Statistics page."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("stats.html")


@app.route("/api/stats")
def api_stats():
    """API endpoint to return user statistics."""
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_email = session["user"]
    stats = load_user_stats(user_email)
    
    return jsonify(stats)


@app.route("/save_session_stats", methods=["POST"])
def save_session_stats():
    """Save session statistics after focus mode completes."""
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user_email = session["user"]
    data = request.get_json() or request.form
    
    try:
        duration_minutes = int(data.get("duration_minutes", 0))
        completed_raw = data.get("completed", False)
        if isinstance(completed_raw, bool):
            completed = completed_raw
        else:
            completed = str(completed_raw).strip().lower() in ("true", "1", "yes", "on")
        exit_attempts = int(data.get("exit_attempts", 0))
        
        update_session_stats(user_email, duration_minutes, completed, exit_attempts)

        if completed:
            add_session_history_entry(user_email, duration_minutes, exit_attempts)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400



@app.route("/settings")
def settings():
    """To‑do list page (replaces original settings)."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("settings.html")


@app.route("/blocked")
def blocked_apps():
    """Blocked apps and browsers page."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("blocked.html")


@app.route("/history")
def session_history():
    """Session history page."""
    if "user" not in session:
        return redirect(url_for("login_page"))
    user_email = session["user"]
    sessions = get_user_session_history(user_email)
    return render_template("history.html", sessions=sessions)


@app.route("/verify_password", methods=["POST"])
def verify_password():
    """Endpoint used by focus mode to verify a user's password when exiting a session."""
    if "user" not in session:
        return jsonify({"success": False, "error": "Not logged in"})
    password = request.form.get("password", "").strip()
    users = load_users()
    user = session.get("user")
    if user in users and check_password_hash(users[user], password):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid password"})

@app.route("/get_goals")
def get_goals():
    if "user" not in session:
        return jsonify([])
    return jsonify(load_goals())


@app.route("/add_goal", methods=["POST"])
def add_goal():
    if "user" not in session:
        return jsonify({"success": False})
    text = request.form.get("text", "").strip()
    desc = request.form.get("desc", "").strip()
    if not text:
        return jsonify({"success": False})
    goals = load_goals()
    goals.append({"text": text, "desc": desc, "done": False})
    save_goals(goals)
    return jsonify({"success": True, "goals": goals})


@app.route("/update_goal", methods=["POST"])
def update_goal():
    if "user" not in session:
        return jsonify({"success": False})
    idx = int(request.form.get("index", -1))
    done = request.form.get("done") == "true"
    goals = load_goals()
    if 0 <= idx < len(goals):
        goals[idx]["done"] = done
        save_goals(goals)
        # Check if all goals are completed
        all_done = len(goals) > 0 and all(g["done"] for g in goals)
        if all_done:
            save_goals([])  # Reset goals
            return jsonify({"success": True, "goals": [], "reset": True})
        return jsonify({"success": True, "goals": goals})
    return jsonify({"success": False})


@app.route("/reset_goals", methods=["POST"])
def reset_goals():
    if "user" not in session:
        return jsonify({"success": False})
    save_goals([])
    return jsonify({"success": True})


def monitor_processes(blocked_apps, duration):
    global blocking_active
    start_time = time.time()
    while blocking_active and (time.time() - start_time) < duration * 60:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if any(b.lower() in proc_name for b in blocked_apps):
                    proc.kill()
                    print(f"Killed blocked process: {proc.info['name']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(5)
    blocking_active = False


@app.route("/get_blocked")
def get_blocked():
    if "user" not in session:
        return jsonify([])
    return jsonify(load_blocked())


@app.route("/add_block", methods=["POST"])
def add_block():
    if "user" not in session:
        return jsonify({"success": False})
    item = request.form.get("item", "").strip()
    if not item:
        return jsonify({"success": False})
    blocked = load_blocked()
    if item not in blocked:
        blocked.append(item)
        save_blocked(blocked)
    return jsonify({"success": True, "blocked": blocked})


@app.route("/remove_block", methods=["POST"])
def remove_block():
    if "user" not in session:
        return jsonify({"success": False})
    item = request.form.get("item", "").strip()
    blocked = load_blocked()
    if item in blocked:
        blocked.remove(item)
        save_blocked(blocked)
    return jsonify({"success": True, "blocked": blocked})


@app.route("/start_blocking", methods=["POST"])
def start_blocking():
    global blocking_thread, blocking_active
    if "user" not in session:
        return jsonify({"success": False})
    duration = int(request.form.get("duration", 0))
    blocked = load_blocked()
    if not blocked or duration <= 0:
        return jsonify({"success": False})
    if blocking_thread and blocking_thread.is_alive():
        return jsonify({"success": False, "error": "Blocking already active"})
    blocking_active = True
    blocking_thread = threading.Thread(target=monitor_processes, args=(blocked, duration))
    blocking_thread.start()
    return jsonify({"success": True})


@app.route("/stop_blocking", methods=["POST"])
def stop_blocking():
    global blocking_active
    if "user" not in session:
        return jsonify({"success": False})
    blocking_active = False
    return jsonify({"success": True})


if __name__ == "__main__":
    # Open browser automatically
    import threading
    def open_browser():
        import time
        time.sleep(2)
        webbrowser.open("http://localhost:5000")
    
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=True, port=5000)
