import json
import random
import asyncio
import httpx
import numpy as np
import os
import uvicorn
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- СИСТЕМА ДОСТУПА ---
DB_FILE = "requests.json"
# Список одноразовых кодов (можешь добавить свои)
VALID_CODES = ["HROM2026", "QUANTUM1", "ACCESS777", "SECRET99"]

def get_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- АДМИН-ПАНЕЛЬ ---
@app.get("/admin_panel")
async def admin_panel(secret: str = None):
    if secret != "SUPER_ADMIN_123": return "Доступ запрещен"
    db = get_db()
    html = "<h1>Управление учениками</h1>"
    for user, info in db.items():
        status = info.get("status")
        html += f"<p><b>{user}</b> — Статус: {status} | <a href='/set_status?user={user}&status=approved&secret=SUPER_ADMIN_123'>ОДОБРИТЬ</a> | <a href='/set_status?user={user}&status=blocked&secret=SUPER_ADMIN_123'>ЗАБЛОКИРОВАТЬ</a></p>"
    return HTMLResponse(html)

@app.get("/set_status")
async def set_status(user: str, status: str, secret: str = None):
    if secret != "SUPER_ADMIN_123": return "Доступ запрещен"
    db = get_db()
    if user in db:
        db[user]["status"] = status
        save_db(db)
    return HTMLResponse(f"Статус {user} изменен на {status}! <a href='/admin_panel?secret=SUPER_ADMIN_123'>Назад</a>")

# --- ЛОГИКА ВХОДА ---
@app.post("/request_access")
async def request_access(response: Response, username: str = Form(...), code: str = Form(...)):
    db = get_db()
    # Проверка кода: если код в списке, одобряем навсегда
    if code in VALID_CODES:
        db[username] = {"status": "approved"}
        save_db(db)
        response.set_cookie(key="tg_username", value=username, max_age=315360000)
        return HTMLResponse("Доступ активирован! <br><a href='/'>Перейти в панель</a>")
    else:
        return HTMLResponse("Неверный код. <br><a href='/'>Назад</a>")
