import fastapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated, Optional
from fastapi import HTTPException
from fastapi import Depends, Request
import sqlite3
import os

from .authenticate import register_user, login_user 
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

app = fastapi.FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

DB_PATH = os.path.join(os.path.dirname(__file__), "../Data/prototype.db")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

print("USING DATABASE:", os.path.abspath(DB_PATH))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password TEXT,
            created_at TEXT DEFAULT (datetime('now'))
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
            FOREIGN KEY(username) REFERENCES users(username));
    """)

    conn.commit()
    conn.close()

init_db()


@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: fastapi.Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: fastapi.Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

# @app.get("/home", name="dashboard", response_class=HTMLResponse)
# async def dashboard(request: fastapi.Request):
#     return templates.TemplateResponse(
#         "dashboard/dashboard.html",
#         {"request": request}
#     )

@app.post("/register")
async def register(
    username: Annotated[str, fastapi.Form()],
    email: Annotated[str, fastapi.Form()],
    password: Annotated[str, fastapi.Form()],
):
    if register_user(username, email, password):
        response = JSONResponse({"success": True})
        return response
    raise HTTPException(status_code=400, detail="User already exists")

@app.post("/login")
async def login(
    username: Annotated[str, fastapi.Form()],
    password: Annotated[str, fastapi.Form()]
):
    user = login_user(username, password)
    if user:
        response = JSONResponse({"success": True})
        response.set_cookie("username", username, httponly=True)
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")
# Get the current user cookie
def get_current_user(request: Request):
    username = request.cookies.get("username")
    if not username:
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT username, email, created_at
        FROM users
        WHERE username = ?
        """,
        (username,)
    )
    user = cursor.fetchone()
    conn.close()

    return user

@app.post("/profile")
async def update_profile(
    request: Request,
    full_name: str = fastapi.Form(...),
    age: int = fastapi.Form(...),
    school: str = fastapi.Form(None),
    grade: str = fastapi.Form(None),
    stream: str = fastapi.Form(None),
    contact_info: str = fastapi.Form(None),
    address: str = fastapi.Form(None),
    subjects: list[str] = fastapi.Form([])  # multiple subjects
):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse("/login", status_code=303)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Update user profile
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

    # Update subjects: remove old ones, insert new ones
    # ---------------- SUBJECT HANDLING ----------------

    # Remove empty values + duplicates
    clean_subjects = list(set(
        sub.strip() for sub in subjects if sub and sub.strip()
    ))

    # Delete old subjects
    cursor.execute(
        "DELETE FROM user_subjects WHERE username = ?",
        (username,)
    )

    # Insert new subjects
    cursor.executemany(
        "INSERT INTO user_subjects (username, subject) VALUES (?, ?)",
        [(username, sub) for sub in clean_subjects]
    )


    conn.commit()
    conn.close()

    return JSONResponse({"status": "ok"})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user = Depends(get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=303)

    username, _, _ = user

    return templates.TemplateResponse(
        "dashboard/dashboard.html",
        {"request": request, "username": username}
    )

@app.get("/logout")
async def logout(response: fastapi.Response):
    response = RedirectResponse("/login")
    response.delete_cookie("username")
    return response

@app.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    user = Depends(get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=303)

    username, email, created_at = user
    created_date = created_at.split(" ")[0]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT full_name, age, school, grade, stream, contact_info, address
        FROM user_profile
        WHERE username = ?
    """, (username,))
    profile_data = cursor.fetchone()

    cursor.execute("""
        SELECT subject
        FROM user_subjects
        WHERE username = ?
    """, (username,))
    subjects = [row[0] for row in cursor.fetchall()]

    conn.close()

    return templates.TemplateResponse(
        "sections/profile.html",
        {
            "request": request,
            "username": username,
            "email": email,
            "created_at": created_date,
            "profile": profile_data,
            "subjects": subjects
        }
    )