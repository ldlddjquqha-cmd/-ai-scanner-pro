import json
import random
import asyncio
import numpy as np
import os
import uvicorn
import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

# --- НАСТРОЙКИ СИСТЕМЫ ДОСТУПА И TELEGRAM ---
DB_FILE = "requests.json"
BOT_TOKEN = "8905743098:AAFCqIHqY1PzaVM4hqISpvuBV4s2ka30bfs"
ADMIN_CHAT_ID = "6765689893" 

def get_db():
    if not os.path.exists(DB_FILE): 
        return {"users": {}, "keys": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: 
            data = json.load(f)
            if "users" not in data: data = {"users": data, "keys": []}
            return data
        except: 
            return {"users": {}, "keys": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Фоновая отправка уведомления в Telegram при входе
async def send_tg_notification(username, code):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"🔔 **Новый ученик активировал код!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Текущий статус:** ✅ Доступ разрешен",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "❌ Забанить", "callback_data": f"block_{username}_{code}"},
                    {"text": "✅ Разблокировать", "callback_data": f"approve_{username}_{code}"}
                ]
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"Ошибка отправки в ТГ: {e}")

# --- ОБРАБОТЧИК НАЖАТИЙ НА КНОПКИ В TELEGRAM (WEBHOOK) ---
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        if "callback_query" in data:
            callback_query = data["callback_query"]
            callback_data = callback_query["data"]
            message = callback_query["message"]
            chat_id = message["chat"]["id"]
            message_id = message["message_id"]
            
            parts = callback_data.split("_")
            action = parts[0]
            username = parts[1]
            code = parts[2] if len(parts) > 2 else ""
            
            db = get_db()
            
            if action == "block":
                if username in db["users"]:
                    db["users"][username]["status"] = "blocked"
                    save_db(db)
                new_status_text = "❌ ЗАБЛОКИРОВАН"
                
            elif action == "approve":
                if username in db["users"]:
                    db["users"][username]["status"] = "approved"
                    save_db(db)
                new_status_text = "✅ ДОСТУП РАЗРЕШЕН"
            
            # Изменяем только строчку статуса, кнопки оставляем рабочими!
            new_text = f"🔔 **Новый ученик активировал код!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Текущий статус:** {new_status_text}"
            
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            edit_payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard":
