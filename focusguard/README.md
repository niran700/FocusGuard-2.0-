# FocusGuard — Merged Login App

A unified Flask app that serves a responsive login/signup UI on desktop and mobile.

**Files:**
- `app.py` — Flask server with login/signup routes and session management.
- `login.html`, `signup.html`, `styles.css` — responsive web UI.
- `users.json` — stores registered users (created on first signup).

**Setup:**

1. Install Flask:
```powershell
pip install -r requirements.txt
```

2. Run the app (opens browser automatically):
```powershell
python app.py
```

3. Visit http://127.0.0.1:5000 in any browser (desktop or mobile).

**Features:**
- Responsive design (works on phones and tablets).
- User registration with password hashing.
- Session-based login.
- Protected dashboard route.
- Password validation (min 6 chars, must match).

**Test credentials (after signup):**
- Email, password, and confirm password required.
- Existing accounts will reject duplicate emails.
- Logout clears the session.

**Alternative desktop app:**
- `loginpage.py` — standalone Tkinter window (run with `python loginpage.py`).
