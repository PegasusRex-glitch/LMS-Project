import sqlite3
from app.core.security import Hasher
from app.db.database import Database

db = Database()

conn = db.get_connection()

def register_user(username, email, password, verification_token, token_expires_at):
    hashed_password = Hasher.get_password_hash(password)
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, is_verified, verification_token, token_expires_at) VALUES (?, ?, ?, 0, ?, ?)",
            (username, email, hashed_password, verification_token, token_expires_at)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password, is_verified FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and Hasher.verify_password(password, row[0]) and row[1] == 1:
        return username
    return None