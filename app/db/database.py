import sqlite3
import os
from typing import Annotated
import datetime
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Data", "prototype.db")

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        if not os.path.isfile(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        print(f"Database: {os.path.abspath(self.db_path)}") # For debugging

    def get_connection(self):
        # Increase timeout to 30 seconds to reduce 'database is locked' errors
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.isolation_level = "DEFERRED"  # Autocommit mode = None
        return conn

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                is_verified INTEGER,
                verificayion_token TEXT,
                token_expires_at TEXT    
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                full_name TEXT,
                age INTEGER,
                school TEXT,
                grade TEXT,
                stream TEXT,
                contact_info TEXT,
                address TEXT,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                subject TEXT NOT NULL,
                UNIQUE(username, subject),
                FOREIGN KEY(username) REFERENCES users(username)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                due_date TEXT,
                FOREIGN KEY(username) REFERENCES users(username)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                lesson TEXT NOT NULL,
                creation_date TEXT DEFAULT (datetime('now')),
                last_studied_at TEXT,
                UNIQUE(username, lesson),
                FOREIGN KEY(username) REFERENCES users(username)
            )
        """)

        conn.commit()
        conn.close()
    
    def add_email_verification_columns(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        def column_exists(column_name):
            cursor.execute("PRAGMA table_info(users)")
            return any(col[1] == column_name for col in cursor.fetchall())
        
        if not column_exists("is_verified"):
            cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")

        if not column_exists("verification_token"):
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
        
        if not column_exists("token_expires_at"):
            cursor.execute("ALTER TABLE users ADD COLUMN token_expires_at TEXT")

        conn.commit()
        conn.close()
    
    def verify_email(self, token: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT username, token_expires_at
            FROM users
            WHERE verification_token = ?
        """, (token,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid verification link")
        
        username, expires_at = row

        if datetime.datetime.now() > datetime.datetime.fromisoformat(expires_at):
            conn.close()
            raise HTTPException(status_code=400, detail="Verification link expired")
        
        cursor.execute("""
            UPDATE users
            SET is_verified = 1,
                verification_token = NULL,
                token_expires_at = NULL
            WHERE username = ?
        """, (username,))

        conn.commit()
        conn.close()
    
    def get_current_user(self, request: Request):
        username = request.cookies.get("username")
        if not username:
            return None
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, created_at FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        return user
    
    def get_user_email(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT email
            FROM users
            WHERE username = ?
        """, (username,))

        result = cursor.fetchone()
        conn.close()
        return result
    
    def update_user(self, username, full_name, age, school, grade, stream, contact_info, address):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO user_profile (username, full_name, age, school, grade, stream, contact_info, address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            full_name = excluded.full_name,
            age = excluded.age,
            school = excluded.school,
            grade = excluded.grade,
            stream = excluded.stream,
            contact_info = excluded.contact_info,
            address = excluded.address
        """, (username, full_name, age, school, grade, stream, contact_info, address))

        conn.commit()
        conn.close()

    def get_subjects_count(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT count(subject)
            FROM user_subjects
            WHERE username = ?
        """, (username,))

        count = cursor.fetchone()[0]
        print(count)
        return count