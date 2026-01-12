import sqlite3
import os
from .password_hashing import Hasher

DB_PATH = os.path.join(os.path.dirname(__file__), "../Data/prototype.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn

def register_user(username, email, password):
    hashed_password = Hasher.get_password_hash(password)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and Hasher.verify_password(password, row[0]):
        return username
    return None
