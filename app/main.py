import fastapi
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated, Optional
from fastapi import HTTPException
from fastapi import Depends, Request
import sqlite3
import os
import secrets
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from fastapi import BackgroundTasks
import asyncio

from app.db.database import Database
from app.routes.auth import register_user, login_user 
from pathlib import Path
from app.core.mail_sender import send_verification_email

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.path.join(BASE_DIR, "Data", "prototype.db")

app = fastapi.FastAPI()
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

templates = Jinja2Templates(directory="/app/templates")
# Initialize the DB
db = Database()
db.init_db()
db.add_email_verification_columns()



# default_k = 0.3

# @app.get("/api/forgetting-curves/{username}")
# def get_forgetting_curves(username: str):
#     conn = db.get_connection()
#     conn.row_factory = sqlite3.Row
#     cursor = conn.cursor()

#     cursor.execute("""
#         SELECT lesson, creation_date, last_studied_at
#         FROM user_lessons
#         WHERE username = ?
#     """, (username,))

#     lesson_db = cursor.fetchall()
#     conn.close()
#     today = datetime.now().date()
#     result = []

#     for lesson in lesson_db:
#         reference_date_str = lesson["last_studied_at"] or lesson["creation_date"]

#         reference_date = datetime.strptime(reference_date_str, "%Y-%m-%d %H:%M:%S")
#         days_passed = (today - reference_date.date()).days
#         curve = []

#         for day in range(days_passed + 1):
#             retention = 100 * (1 - default_k*day)
#             curve.append({
#                 "x": day,
#                 "y": round(retention, 2)
#             })
#         result.append({
#             "name": lesson["lesson"],
#             "curve": curve
#         })
#     return result

@app.get("/api/current-user")
async def get_current_user(request: Request):
    username = request.cookies.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": username}

@app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse("/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: fastapi.Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: fastapi.Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

# To verify the user
@app.get("/verify_email")
async def verify(token: str):
    db.verify_email(token)
    return RedirectResponse("/login?verified=true", status_code=303)

@app.post("/register")
async def register(
    username: Annotated[str, fastapi.Form()],
    email: Annotated[str, fastapi.Form()],
    password: Annotated[str, fastapi.Form()],
    background_tasks: BackgroundTasks
):
    
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

    success = register_user(
        username = username,
        email = email,
        password = password,
        verification_token = token,
        token_expires_at = expires_at
    )

    if success:
        verification_link = f"http://localhost:8000/verify_email?token={token}"
        background_tasks.add_task(send_verification_email, email, verification_link)
        return JSONResponse({"success": True, "message": "Account created. Please verify your email."})
    
    return JSONResponse({"success": False, "detail": "User already exists"}, status_code=400)

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
    raise HTTPException(status_code=401, detail="Invalid credentials or email not verified")

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
    subjects: list[str] = fastapi.Form([])
):
    username = request.cookies.get("username")
    if not username:
        return RedirectResponse("/login", status_code=303)

    conn = db.get_connection()
    cursor = conn.cursor()

    db.update_user(username, full_name, age, school, grade, stream, contact_info, address)
    
    # Update subjects
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
async def dashboard(request: Request, user = Depends(db.get_current_user)):
    if not user:
        return RedirectResponse("/login", status_code=303)

    username, _, _ = user

    conn = db.get_connection()
    cursor = conn.cursor()

    # Fetch subjects
    # cursor.execute("SELECT COUNT(*) FROM user_subjects WHERE username = ?", (username,))
    subjects = db.get_subjects_count(username)

    # Fetch completed assignment count 
    cursor.execute("SELECT COUNT(*) FROM assignments WHERE username = ? AND status='completed'", (username,))
    row = cursor.fetchone()
    completed_assignments = row[0] if row else 0

    # Calculate progress
    cursor.execute("SELECT COUNT(*) FROM assignments WHERE username = ?", (username,))
    row = cursor.fetchone()
    total_assignments = row[0] if row else 0
    progress = int((completed_assignments/total_assignments)*100) if total_assignments > 0 else 0

    # Recent activity
    cursor.execute("""
        SELECT title, status, due_date
        FROM assignments
        WHERE username = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (username,))
    recent_activity = cursor.fetchall()

    conn.close()

    return templates.TemplateResponse(
        "dashboard/dashboard.html",
        {
            "request": request, 
            "username": username,
            "subjects": subjects,
            "completed_assignments": completed_assignments,
            "progress": progress,
            "recent_activity": recent_activity
        }
    )

class LessonPayload(BaseModel):
    lesson: str

@app.post("/dashboard/add-lesson")
async def add_lesson(
    request: Request,
    payload: LessonPayload
):
    username = request.cookies.get("username")
    
    if not username:
        raise HTTPException(status_code=401, detail="Not Authenticated")

    lesson = payload.lesson.strip()
    if not lesson:
        return JSONResponse({"status": "nothing to add"})

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.executemany(
        "INSERT OR IGNORE INTO user_lessons (username, lesson) VALUES (?, ?)",
        [(username, lesson)]
    )

    conn.commit()
    conn.close()

    return JSONResponse({
        "Status": "Ok",
        "added": 1
    })


@app.get("/logout")
async def logout(response: fastapi.Response):
    response = RedirectResponse("/login")
    response.delete_cookie("username")
    return response

@app.get("/analysis", response_class=HTMLResponse, name="analysis")
async def analysis_page(
    request: Request
):
    return templates.TemplateResponse("sections/analysis.html", {"request": request})


@app.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    user = Depends(db.get_current_user)
):
    if not user:
        return RedirectResponse("/login", status_code=303)

    username, email, created_at = user
    created_date = created_at.split(" ")[0]
    conn = db.get_connection()
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