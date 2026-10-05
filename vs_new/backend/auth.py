"""
auth.py
-------
Lightweight username/password authentication with server-side session
tokens, built entirely on the standard library (hashlib + secrets).

Design:
  - Passwords are stored as "salt$sha256(salt+password)" — never plaintext.
  - Logging in issues a random 64-char token stored in the `sessions`
    table, valid for SESSION_LIFETIME_HOURS.
  - The frontend sends the token back as: Authorization: Bearer <token>
  - Protected API routes are wrapped with @require_login (see server.py).

NOTE: This is intentionally simple — appropriate for an internal shop
admin panel / academic project. A production deployment should add
HTTPS, rate limiting, password policies, and a vetted auth library.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

from database import get_connection
from utils import ValidationError

SESSION_LIFETIME_HOURS = 12


class AuthError(Exception):
    """Raised for authentication/authorization failures -> HTTP 401."""
    pass


def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password, stored_hash):
    try:
        salt, _ = stored_hash.split("$", 1)
    except (ValueError, AttributeError):
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored_hash)


def create_user(username, password, full_name="", role="admin"):
    username = (username or "").strip()
    if not username or not password:
        raise ValidationError("Username and password are required.")
    if len(password) < 4:
        raise ValidationError("Password must be at least 4 characters.")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, _hash_password(password), full_name.strip(), role),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValidationError(f"Username '{username}' already exists.")
    conn.close()


def ensure_default_admin():
    """Seed a default admin login the very first time the app is run."""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    conn.close()
    if row["c"] == 0:
        create_user("admin", "admin123", full_name="Shop Administrator", role="admin")
        print("-" * 60)
        print(" Default admin login created:")
        print("   username: admin")
        print("   password: admin123")
        print(" Please change this after first login (Admin Panel).")
        print("-" * 60)


def login(username, password):
    username = (username or "").strip()
    if not username or not password:
        raise ValidationError("Username and password are required.")

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    if not user or not _verify_password(password, user["password_hash"]):
        conn.close()
        raise AuthError("Invalid username or password.")

    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(hours=SESSION_LIFETIME_HOURS)).isoformat()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user["user_id"], expires_at),
    )
    conn.commit()
    conn.close()

    return {
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
        },
    }


def logout(token):
    if not token:
        return
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def get_user_for_token(token):
    if not token:
        raise AuthError("Not logged in.")

    conn = get_connection()
    row = conn.execute(
        """SELECT s.expires_at, u.user_id, u.username, u.full_name, u.role
           FROM sessions s JOIN users u ON u.user_id = s.user_id
           WHERE s.token = ?""",
        (token,),
    ).fetchone()

    if not row:
        conn.close()
        raise AuthError("Session expired or invalid. Please log in again.")

    if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        raise AuthError("Session expired. Please log in again.")

    conn.close()
    return dict(row)


def change_password(user_id, old_password, new_password):
    if not new_password or len(new_password) < 4:
        raise ValidationError("New password must be at least 4 characters.")

    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user or not _verify_password(old_password, user["password_hash"]):
        conn.close()
        raise AuthError("Current password is incorrect.")

    conn.execute(
        "UPDATE users SET password_hash = ? WHERE user_id = ?",
        (_hash_password(new_password), user_id),
    )
    # Invalidate all existing sessions for this user so old tokens can't
    # be reused after a password change.
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
