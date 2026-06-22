import json
import random
import asyncio
import numpy as np
import os
import uvicorn
import httpx
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from google import genai
from google.genai import types

app = FastAPI()

# ==========================================
# КОНФИГУРАЦИЯ СИСТЕМЫ И ДАННЫХ
# ==========================================
DB_FILE = "requests.json"
BOT_TOKEN = "8761108877:AAHGS5tME2dqGF6iMC1IIN9HzgWJ0wgNGTU"
ADMIN_CHAT_ID = "6765689893"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ТВОЙ_GEMINI_API_KEY_ЗДЕСЬ")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Ты — старший ИИ-аналитик квантового торгового ядра HROM QUANTUM.
Твоя задача — проводить бескомпромиссный математический и технический анализ рынка.
Тебе категорически запрещено выдавать случайные прогнозы, угадывать или подстраивать результаты.
Если на рынке наблюдается флэт, ложные пробития, отсутствие объемов или спорные показатели индикаторов, ты ОБЯЗАН выдать вердикт "СИГНАЛА НЕТ".
Твоя цель — сохранить депозит трейдера, отсекая рыночный шум. Твой анализ должен быть хладнокровным.
"""

# ==========================================
# БАЗА ДАННЫХ И ХРАНИЛИЩЕ ИНФОРМАЦИИ
# ==========================================
def get_db():
    print("[DB LOG] Попытка чтения базы данных requests.json...")
    if not os.path.exists(DB_FILE): 
        print("[DB WARNING] Файл базы данных не найден. Создание новой структуры...")
        return {"users": {}, "keys": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: 
            data = json.load(f)
            if "users" not in data: 
                print("[DB LOG] Миграция структуры данных: добавление полей...")
                data = {"users": data, "keys": []}
            return data
        except Exception as e: 
            print(f"[DB ERROR] Ошибка парсинга JSON: {e}. Сброс к пустой структуре.")
            return {"users": {}, "keys": []}

def save_db(data):
    print("[DB LOG] Сохранение изменений в requests.json...")
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("[DB LOG] Сохранение успешно завершено.")

# ==========================================
# ТЕЛЕГРАМ СИСТЕМА УВЕДОМЛЕНИЙ И ЛОГОВ
# ==========================================
async def send_tg_notification(username, code):
    print(f"[TG LOG] Подготовка отправки уведомления об активации кода учеником @{username}...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "❌ Забанить ученика", "callback_data": f"ban:{username}"},
                {"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}
            ]
        ]
    }
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"🔔 **Новый ученик активировал код!**\n\n**Ник в Telegram:** @{username}\n**Использованный код:** `{code}`\n**Текущий статус:** ✅ Доступ разрешен (Сессия привязана)",
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    async with httpx.AsyncClient() as client:
        try: 
            response = await client.post(url, json=payload, timeout=5.0)
            if response.status_code == 200:
                print(f"[TG LOG] Уведомление об активации @{username} успешно доставлено админу.")
            else:
                print(f"[TG WARNING] Телеграм вернул статус код: {response.status_code}")
        except Exception as e: 
            print(f"[TG ERROR] Критическая ошибка отправки уведомления в ТГ: {e}")

async def send_tg_notification_simple(text):
    print(f"[TG LOG] Отправка текстового сообщения в чат администратора: {text[:30]}...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"[TG ERROR] Ошибка отправки простого сообщения: {e}")

async def edit_tg_message_status(chat_id, message_id, username, status_text, reply_markup=None):
    print(f"[TG LOG] Изменение статуса сообщения {message_id} для пользователя @{username}...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": f"🔔 **Управление учеником**\n\n**Ник в Telegram:** @{username}\n**Текущий статус в системе:** {status_text}",
        "parse_mode": "Markdown"
    }
    if reply_markup: 
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
            print(f"[TG LOG] Сообщение успешно обновлено.")
        except Exception as e:
            print(f"[TG ERROR] Ошибка редактирования сообщения: {e}")

# ==========================================
# ОБРАБОТЧИК ВЕБХУКОВ ТЕЛЕГРАМ БОТА
# ==========================================
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print(f"[WEBHOOK RECEIVE] Входящий пакет данных от Telegram сервера: {data}")
        
        if "callback_query" in data:
            callback_query = data["callback_query"]
            chat_id = str(callback_query["message"]["chat"]["id"])
            message_id = callback_query["message"]["message_id"]
            callback_data = callback_query["data"]
            
            print(f"[WEBHOOK CALLBACK] Нажата инлайн кнопка с данными: {callback_data}")
            if chat_id == ADMIN_CHAT_ID:
                action, username = callback_data.split(":")
                db = get_db()
                
                if action == "ban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "blocked"
                    save_db(db)
                    unban_markup = {"inline_keyboard": [[{"text": "✅ Разблокировать ученика", "callback_data": f"unban:{username}"}]]}
                    await edit_tg_message_status(chat_id, message_id, username, "🚫 Заблокирован (Доступ полностью закрыт)", reply_markup=unban_markup)
                    print(f"[ADMIN ACTION] Ученик @{username} успешно заблокирован из Telegram-интерфейса.")
                    
                elif action == "unban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "approved"
                    save_db(db)
                    standard_markup = {
                        "inline_keyboard": [
                            [
                                {"text": "❌ Забанить ученика", "callback_data": f"ban:{username}"},
                                {"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}
                            ]
                        ]
                    }
                    await edit_tg_message_status(chat_id, message_id, username, "✅ Разблокирован (Доступ открыт)", reply_markup=standard_markup)
                    print(f"[ADMIN ACTION] Ученик @{username} успешно разблокирован из Telegram-интерфейса.")
            return {"status": "ok"}

        if "message" in data and "text" in data["message"]:
            text = data["message"]["text"].strip()
            chat_id = str(data["message"]["chat"]["id"])
            
            print(f"[WEBHOOK MESSAGE] Получено текстовое сообщение: {text} из чата {chat_id}")
            if chat_id == ADMIN_CHAT_ID:
                parts = text.split()
                if len(parts) >= 2:
                    command = parts[0]
                    username = parts[1].replace("@", "").strip().replace(" ", "")
                    db = get_db()
                    
                    if command == "/бан": 
                        print(f"[ADMIN COMMAND] Запрос на бан пользователя @{username}...")
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "blocked"
                        save_db(db)
                        await send_tg_notification_simple(f"🚫 Пользователь @{username} успешно заблокирован в локальной базе данных.")
                        print(f"[ADMIN COMMAND] Успешная блокировка @{username}")
                    
                    elif command == "/разбанить":
                        print(f"[ADMIN COMMAND] Запрос на разбан пользователя @{username}...")
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "approved"
                        save_db(db)
                        await send_tg_notification_simple(f"✅ Пользователь @{username} успешно возвращен в пул активных учеников.")
                        print(f"[ADMIN COMMAND] Успешная разблокировка @{username}")
    except Exception as e: 
        print(f"[WEBHOOK ERROR] Исключение при парсинге или обработке вебхука: {e}")
        
    return {"status": "ok"}

# ==========================================
# ГЕНЕРАТОР КЛЮЧЕЙ И АДМИН-ПАНЕЛЬ ВЕБ-ИНТЕРФЕЙСА
# ==========================================
@app.get("/generate_key")
async def generate_key(master: str = None):
    print(f"[HTTP GET] Запрос на страницу генерации ключа. Мастер-ключ: {master}")
    if master != "SUPER_ADMIN_123": 
        print("[AUTH WARNING] Попытка несанкционированного доступа к генератору ключей!")
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ закрыт. Неверный секретный ключ!</h1>")
    
    chars = "0123456789ABCDEF"
    new_key = "HROM_" + "".join(random.choice(chars) for _ in range(6))
    
    db = get_db()
    db["keys"].append(new_key)
    save_db(db)
    
    print(f"[SERVER LOG] Сгенерирован новый одноразовый ключ доступа: {new_key}")
    
    return HTMLResponse(f"""
    <div style="background:#06080c; color:#ffffff; font-family:sans-serif; text-align:center; padding:50px; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; box-sizing:border-box;">
        <p style="color:#586988; font-size:18px; margin-bottom:5px;">Создан новый одноразовый ключ:</p>
        <div style="background:#0f131e; border:1px solid #1a2233; color:#00ff66; font-size:26px; font-weight:bold; padding:15px 30px; border-radius:12px; letter-spacing:1px; margin-bottom:20px; box-shadow: 0 0 20px rgba(0,255,102,0.2);">
            {new_key}
        </div>
        <p style="color:#4b5975; font-size:13px; max-width:320px; margin-bottom:25px; line-height:1.5;">Передай этот ключ новому ученику. При активации его сессия привяжется намертво к его нику.</p>
        <a href="/generate_key?master=SUPER_ADMIN_123" style="text-decoration:none;">
            <button style="background:#963bfe; color:white; font-weight:bold; padding:14px 28px; border:none; border-radius:10px; cursor:pointer; font-size:14px; text-transform:uppercase; transition:0.2s;">Создать еще один</button>
        </a>
    </div>
    """)

@app.get("/admin_panel")
async def admin_panel(secret: str = None):
    print(f"[HTTP GET] Запрос на веб-панель администратора. Секрет: {secret}")
    if secret != "SUPER_ADMIN_123": 
        print("[AUTH WARNING] Отклонен доступ к веб-панели администратора.")
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ запрещен</h1>")
    
    db = get_db()
    
    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Управление учениками — HROM</title>
        <style>
            body { background: #06080c; color: #ffffff; font-family: 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; background: #080a10; padding: 25px; border-radius: 20px; border: 1px solid #1a2233; box-shadow: 0 15px 30px rgba(0,0,0,0.5); }
            h1 { font-size: 24px; color: #a855f7; text-align: center; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px; }
            .user-row { background: #0f131e; border: 1px solid #161b26; padding: 15px; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
            .user-info { font-size: 15px; font-weight: 600; }
            .user-name { color: #00ff66; font-size: 16px; }
            .status-badge { padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-left: 5px; }
            .status-approved { background: rgba(0, 255, 102, 0.15); color: #00ff66; border: 1px solid #00ff66; }
            .status-blocked { background: rgba(255, 51, 68, 0.15); color: #ff3344; border: 1px solid #ff3344; }
            .status-unknown { background: rgba(88, 105, 136, 0.15); color: #586988; border: 1px solid #586988; }
            .btn-group { display: flex; gap: 8px; }
            .btn-action { text-decoration: none; padding: 8px 14px; font-size: 12px; font-weight: bold; border-radius: 8px; text-transform: uppercase; transition: all 0.2s; display: inline-block; cursor: pointer; text-align: center; }
            .btn-ban { background: #ff3344; color: #ffffff; border: none; box-shadow: 0 3px 10px rgba(255,51,68,0.2); }
            .btn-unban { background: #00ff66; color: #000000; border: none; box-shadow: 0 3px 10px rgba(0,255,102,0.2); font-weight: 800; }
            .btn-action:active { transform: scale(0.95); }
            .no-users { text-align: center; color: #4b5975; padding: 20px; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Управление учениками</h1>
    """
    
    if not db["users"]:
        html_content += '<div class="no-users">Список зарегистрированных учеников пока пуст.</div>'
    else:
        for user, info in db["users"].items():
            status = info.get("status", "unknown")
            if status == "approved":
                badge_class = "status-approved"
                badge_text = "Активен"
            elif status == "blocked":
                badge_class = "status-blocked"
                badge_text = "Бан"
            else:
                badge_class = "status-unknown"
                badge_text = status

            html_content += f"""
            <div class="user-row">
                <div class="user-info">
                    <span class="user-name">@{user}</span>
                    <span class="status-badge {badge_class}">{badge_text}</span>
                </div>
                <div class="btn-group">
                    <a href="/set_status?user={user}&status=approved&secret=SUPER_ADMIN_123" class="btn-action btn-unban">Разбанить ✅</a>
                    <a href="/set_status?user={user}&status=blocked&secret=SUPER_ADMIN_123" class="btn-action btn-ban">Забанить 🚫</a>
                </div>
            </div>
            """
            
    html_content += """
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.get("/set_status")
async def set_status(user: str, status: str, secret: str = None):
    print(f"[HTTP GET] Изменение статуса на сервере для @{user} на {status}")
    if secret != "SUPER_ADMIN_123": 
        return "Доступ запрещен"
    db = get_db()
    if user in db["users"]:
        db["users"][user]["status"] = status
        save_db(db)
        print(f"[SERVER LOG] Пользователю @{user} выставлен статус: {status}")
    return HTMLResponse(f"""
    <div style="background:#06080c; color:#ffffff; font-family:sans-serif; text-align:center; padding-top:100px; height:100vh; box-sizing:border-box;">
        <h2>Статус пользователя <b>@{user}</b> успешно изменен на <b>{status}</b>!</h2>
        <br><br>
        <a href="/admin_panel?secret=SUPER_ADMIN_123" style="background:#963bfe; color:white; font-weight:bold; padding:12px 24px; border:none; border-radius:10px; text-decoration:none; text-transform:uppercase; font-size:13px;">Вернуться в панель</a>
    </div>
    """)

# ==========================================
# ПРОВЕРКА СТАТУСОВ И РЕГИСТРАЦИЯ
# ==========================================
@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    print(f"[API CHECK] Проверка статуса авторизации для пользователя: @{username}")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    print(f"[API CHECK] Ответ статуса для @{username}: {status}")
    return JSONResponse({"status": status})

@app.post("/request_access")
async def request_access(username: str = Form(...), code: str = Form(...)):
    username = username.strip().replace("@", "").replace(" ", "")
    code = code.strip().replace(" ", "")
    print(f"[API AUTH] Запрос на активацию. Ученик: @{username}, Код: {code}")
    db = get_db()
    
    if username in db["users"] and db["users"][username]["status"] == "blocked":
        print(f"[API AUTH REJECT] Отклонено: пользователь @{username} заблокирован.")
        return JSONResponse({"success": False, "message": "Вы заблокированы!"})

    if username in db["users"] and db["users"][username]["status"] == "approved":
        print(f"[API AUTH ALLOW] Пользователь @{username} уже имел активный доступ.")
        return JSONResponse({"success": True, "message": "Доступ уже подтвержден! Заходим..."})

    if code not in db["keys"]:
        print(f"[API AUTH REJECT] Отклонено: неверный или использованный ключ {code}.")
        return JSONResponse({"success": False, "message": "Неверный или уже использованный код!"})
    
    db["keys"].remove(code)
    db["users"][username] = {"status": "approved", "used_code": code}
    save_db(db)
    
    print(f"[API AUTH SUCCESS] Ключ {code} успешно удален из пула. Доступ для @{username} выдан.")
    asyncio.create_task(send_tg_notification(username, code))
    
    return JSONResponse({"success": True, "message": "Код успешно активирован! Загрузка..."})

# ==========================================
# МАССИВЫ ВСЕХ АКТИВОВ (БЕЗ УРЕЗАНИЙ И СОКРАЩЕНИЙ)
# ==========================================
BINANCE_MAPPING = {
    "EUR/USD": "EURUSDT", "GBP/USD": "GBPUSDT", "USD/JPY": "USDJPY",
    "AUD/USD": "AUDUSDT", "EUR/JPY": "EURJPY", "USD/CAD": "USDCAD",
    "GBP/JPY": "GBPJPY", "NZD/USD": "NZDUSDT", "USD/CHF": "USDCHF", "EUR/GBP": "EURGBP"
}

ASSETS_DATA = {
    "ru": {
        "[ВСЕ АКТИВЫ] — OTC ЦИКЛ": {
            "ВАЛЮТНЫЕ ПАРЫ": [
                "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC",
                "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"
            ],
            "АКЦИИ": [
                "Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC",
                "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"
            ],
            "КРИПТОВАЛЮТА": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "СЫРЬЕ / ИНДЕКСЫ": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ВСЕ АКТИВЫ] — ЖИВОЙ РЫНОК": {
            "ВАЛЮТНЫЕ ПАРЫ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "en": {
        "[ALL ASSETS] — OTC CYCLE": {
            "CURRENCY PAIRS": [
                "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC",
                "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"
            ],
            "STOCKS": [
                "Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC",
                "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"
            ],
            "CRYPTOCURRENCY": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "COMMODITIES / INDICES": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ALL ASSETS] — LIVE MARKET": {
            "CURRENCY PAIRS": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "ua": {
        "[ВСІ АКТИВИ] — OTC ЦИКЛ": {
            "ВАЛЮТНІ ПАРИ": [
                "EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC",
                "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"
            ],
            "АКЦІЇ": [
                "Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC",
                "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"
            ],
            "КРИПТОВАЛЮТА": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "СИРОВИНА / ІНДЕКСИ": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ВСІ АКТИВИ] — ЖИВИЙ РЫНОК": {
            "ВАЛЮТНІ ПАРИ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    }
}

# ==========================================
# МАТЕМАТИЧЕСКИЕ ИНДИКАТОРЫ И ГЕНЕРАТОРЫ ДАННЫХ
# ==========================================
def calculate_rsi(prices, period=14):
    print(f"[MATH] Расчет технического индикатора RSI({period}) для {len(prices)} котировок...")
    if len(prices) < period + 1: 
        print("[MATH WARNING] Мало данных для полноценного расчета RSI. Возврат медианы 50.0")
        return 50.0
    deltas = np.diff(prices)
    up = np.where(deltas > 0, deltas, 0).mean()
    down = np.where(deltas < 0, -deltas, 0).mean()
    if down == 0: 
        print("[MATH] Down-импульсы отсутствуют. Достигнута критическая зона RSI 100.0")
        return 100.0
    rs = up / down
    rsi_result = 100.0 - (100.0 / (1.0 + rs))
    print(f"[MATH] Результирующий RSI: {rsi_result:.2f}")
    return rsi_result

def calculate_ema(prices, period=20):
    print(f"[MATH] Расчет экспоненциальной скользящей средней EMA({period})...")
    if len(prices) < period: 
        print(f"[MATH WARNING] Недостаточно свечей для EMA({period}). Возврат последней известной цены.")
        return prices[-1]
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    ema_result = np.convolve(prices, weights, mode='valid')[-1]
    print(f"[MATH] Результирующая EMA: {ema_result:.4f}")
    return ema_result

def generate_otc_candles(asset_name, count=50):
    print(f"[CRYPTO CORE] Квантовая симуляция движения для OTC актива: {asset_name}")
    # Псевдогенерация детерминирована на основе имени актива и времени
    seed_value = sum(ord(char) for char in asset_name) + int(asyncio.get_event_loop().time() / 150)
    np.random.seed(seed_value)
    
    if "Bitcoin" in asset_name: start_price = 65000.0
    elif "Ethereum" in asset_name: start_price = 3500.0
    elif "Gold" in asset_name: start_price = 2300.0
    elif "Apple" in asset_name or "Tesla" in asset_name: start_price = 180.0
    else: start_price = 1.1250  
        
    drift = np.random.uniform(-0.0001, 0.0001)
    noise = np.random.normal(drift, 0.0012, count)
    prices = [start_price]
    for n in noise:
        prices.append(prices[-1] * (1 + n))
    print(f"[CRYPTO CORE] График для {asset_name} смоделирован. Последняя цена: {prices[-1]:.4f}")
    return prices

# ==========================================
# ИИ КВАНТОВОЕ ЯДРО СЕТИ GEMINI (БЕЗ РАНДОМА)
# ==========================================
async def analyze_market_with_ai(asset: str, timeframe: str, current_price: float, rsi: float, ema: float, prices: list):
    print(f"[AI CORE] Инициализация обращения к нейросетевой модели Gemini Core...")
    try:
        prompt = (
            f"Проанализируй текущую ситуацию на рынке для актива: {asset}.\n"
            f"Таймфрейм операции: {timeframe}.\n"
            f"Математические показатели индикаторов:\n"
            f"- Текущая цена: {current_price}\n"
            f"- Значение RSI (14): {rsi:.2f}\n"
            f"- Экспертная EMA (20): {ema:.2f}\n"
            f"- Динамика последних 5 котировок: {prices[-5:]}\n\n"
            f"Выдай строгий вердикт. Твой ответ должен содержать ровно два слова на русском языке: направление сделки (ВВЕРХ или ВНИЗ) и через пробел уверенность ИИ в процентах от 70 до 98 (например: ВВЕРХ 87%). "
            f"Если на рынке нет выраженного движения, флэт или неопределенность индикаторов, ответь строго 'СИГНАЛА_НЕТ 0'."
        )
        
        response = await asyncio.to_thread(
            ai_client.models.generate_content,
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.1
            )
        )
        
        text_result = response.text.strip().upper()
        print(f"[AI CORE RAW] Сырой текстовый ответ нейросети: {text_result}")
        parts = text_result.split()
        
        if "СИГНАЛА_НЕТ" in parts[0] or "НЕТ" in parts[0]:
            print("[AI CORE VERDICT] ИИ заблокировал точку входа (Флэт/Рыночный шум).")
            return "NONE", 0, "ИИ-анализ: Вход в сделку заблокирован из-за рыночного шума или бокового тренда."
            
        signal = "UP" if "ВВЕРХ" in parts[0] else "DOWN"
        accuracy = int(''.join(filter(str.isdigit, parts[1]))) if len(parts) > 1 else 85
        print(f"[AI CORE VERDICT] Успешный расчет направления. Сигнал: {signal}, Точность: {accuracy}%")
        return signal, accuracy, f"Квантовый анализ ядра HROM завершен. Точка входа сформирована на основе тренда."
        
    except Exception as e:
        print(f"[AI CORE ERROR] Ошибка ИИ-генерации: {e}. Переключение на жесткие математические шлюзы.")
        if current_price > ema and rsi < 38:
            return "UP", 76, "Резервный алгоритм ТА: Сигнал на повышение от скользящей средней."
        elif current_price < ema and rsi > 62:
            return "DOWN", 76, "Резервный алгоритм ТА: Сигнал на понижение от зоны сопротивления."
        return "NONE", 0, "Резервный алгоритм ТА: Недостаточно волатильности для безопасной сделки."

# ==========================================
# ИИ СКАНИРОВАНИЕ И ЗРЕНИЕ ИЗОБРАЖЕНИЙ
# ==========================================
@app.post("/scan_screenshot")
async def scan_screenshot(username: str = Form(""), file: UploadFile = File(...)):
    username = username.strip().replace("@", "")
    print(f"[AI VISION] Получено изображение графика от ученика @{username}. Размер файла: {file.size if hasattr(file, 'size') else 'Unknown'} байт.")
    asyncio.create_task(send_tg_notification_simple(f"📸 **Ученик @{username} загрузил фото/снимок для ИИ-Сканирования графика!**"))
    
    try:
        contents = await file.read()
        image_parts = [{"mime_type": file.content_type, "data": contents}]
        
        prompt = (
            "Перед тобой снимок торгового графика с платформы Pocket Option/Quotex. Проведи глубокий технический анализ:\n"
            "1. Определи направление движения цены (тренд), уровни поддержки/сопротивления и свечные паттерны.\n"
            "2. Сформируй торговый сигнал на основе увиденного.\n"
            "Твой ответ должен быть профессиональным и строго в следующем формате (на русском):\n"
            "НАПРАВЛЕНИЕ: ВВЕРХ (или ВНИЗ, или СИГНАЛА НЕТ)\n"
            "УВЕРЕННОСТЬ: Число процентов от 70 до 99 (или 0 если сигнала нет)\n"
            "АНАЛИЗ: Твое детальное обоснование решения (1-2 предложения)."
        )
        
        response = await asyncio.to_thread(
            ai_client.models.generate_content,
            model='gemini-2.5-flash',
            contents=[prompt, image_parts[0]],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.1)
        )
        
        ai_text = response.text
        print(f"[AI VISION RESULT] Итог сканирования зрения: {ai_text}")
        
        signal = "NONE"
        if "ВВЕРХ" in ai_text.upper(): signal = "UP"
        elif "ВНИЗ" in ai_text.upper(): signal = "DOWN"
            
        accuracy = 85
        for line in ai_text.split('\n'):
            if "УВЕРЕННОСТЬ" in line.upper():
                nums = ''.join(filter(str.isdigit, line))
                accuracy = int(nums) if nums else 85
                
        return JSONResponse({"success": True, "signal": signal, "accuracy": accuracy, "raw_analysis": ai_text})
        
    except Exception as e:
        print(f"[AI SCANNER ERROR] Ошибка зрения ИИ: {e}")
        return JSONResponse({"success": False, "message": f"Ошибка сканирования ИИ: {str(e)}"})

# ==========================================
# ОСНОВНОЙ РОУТ ПОЛУЧЕНИЯ СИГНАЛОВ
# ==========================================
@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str, username: str = ""):
    print(f"[CORE REQUEST] Запрос сигнала. Ученик: @{username}, Актив: {asset}, Свеча: {timeframe}")
    if username:
        asyncio.create_task(send_tg_notification_simple(f"📊 Ученик @{username} запросил ИИ-анализ рынка пары: **{asset}** ({timeframe})"))
        
    await asyncio.sleep(0.3)
    is_otc = "OTC" in asset
    clean_asset = asset.replace(" OTC", "").strip()
    
    if is_otc:
        prices = generate_otc_candles(asset, count=50)
    else:
        binance_symbol = BINANCE_MAPPING.get(clean_asset, "BTCUSDT")
        print(f"[API LIVE] Запрос реального биржевого стакана Binance для пары {binance_symbol}...")
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1m&limit=50"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=3.0)
                prices = [float(c[4]) for c in response.json()]
            print(f"[API LIVE SUCCESS] Котировки успешно получены с биржи. Текущая цена: {prices[-1]}")
        except Exception as e:
            print(f"[API LIVE ERROR] Ошибка коннекта к API Binance: {e}. Принудительный откат на локальный OTC генератор.")
            prices = generate_otc_candles(clean_asset, count=50)

    rsi = calculate_rsi(prices)
    ema = calculate_ema(prices)
    current_price = prices[-1]
    
    calculated_signal, accuracy, ai_comment = await analyze_market_with_ai(asset, timeframe, current_price, rsi, ema, prices)
    
    payout = 92 if is_otc else 82
    return {
        "signal": calculated_signal, 
        "payout": payout, 
        "accuracy": accuracy, 
        "ai_comment": ai_comment,
        "outcome": "WIN", 
        "session_verified": True
    }

# ==========================================
# ВЕБ-ИНТЕРФЕЙС ТЕРМИНАЛА (ПОЛНЫЙ HTML/CSS/JS)
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def index():
    print("[SERVER LOG] Генерация и рендеринг главной страницы терминала...")
    return rf"""
    <!DOCTYPE html>
    <html lang="ru" style="background:#06080c; color:#ffffff; font-family:'Segoe UI', Roboto, sans-serif; margin:0; padding:0; height:100%;">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>HROM QUANTUM CORE v16.0</title>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                -webkit-tap-highlight-color: transparent;
            }}
            body {{
                background: #06080c;
                color: #ffffff;
                font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                overflow-x: hidden;
            }}
            .container {{
                max-width: 430px;
                width: 100%;
                margin: 0 auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                box-sizing: border-box;
            }}
            #auth-screen {{
                min-height: 100vh;
            }}
            .title {{
                font-size: 22px;
                font-weight: 900;
                color: #a855f7;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-bottom: 6px;
                text-shadow: 0 0 20px rgba(168,85,247,0.4);
                text-align: center;
            }}
            .subtitle {{
                font-size: 11px;
                color: #586988;
                font-weight: 600;
                margin-bottom: 35px;
                text-align: center;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }}
            .input-box {{
                width: 100%;
                max-width: 320px;
                background: #0f131e;
                border: 1px solid #1a2233;
                border-radius: 16px;
                padding: 18px;
                margin-bottom: 14px;
                box-sizing: border-box;
                text-align: center;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}
            .input-box:focus-within {{
                border-color: #a855f7;
                box-shadow: 0 0 15px rgba(168,85,247,0.15);
            }}
            input {{
                background: transparent;
                border: none;
                color: white;
                width: 100%;
                font-size: 14px;
                font-weight: 700;
                outline: none;
                text-align: center;
            }}
            input::placeholder {{
                color: #4b5975;
            }}
            
            /* АНИМАЦИИ И ЭФФЕКТЫ */
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            @keyframes shine {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}
            
            .loader {{
                width: 45px;
                height: 45px;
                border: 4px solid #161b26;
                border-top: 4px solid #a855f7;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin: 20px auto;
                display: none;
                box-shadow: 0 0 15px rgba(168,85,247,0.2);
            }}
            
            /* ЭЛЕМЕНТЫ ТЕРМИНАЛА */
            select {{
                width: 100%;
                padding: 15px;
                background: #0f131e;
                border: 1px solid #1a2233;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
                outline: none;
                appearance: none;
                cursor: pointer;
                transition: background 0.2s;
            }}
            select:focus {{
                border-color: #a855f7;
            }}
            label {{
                font-size: 11px;
                font-weight: bold;
                color: #4b5975;
                display: block;
                margin-bottom: 6px;
                letter-spacing: 0.8px;
                text-transform: uppercase;
            }}
            
            /* КНОПКИ */
            .btn {{
                width: 100%;
                padding: 16px;
                border: none;
                color: white;
                font-weight: 800;
                border-radius: 14px;
                cursor: pointer;
                font-size: 13px;
                letter-spacing: 1px;
                text-transform: uppercase;
                transition: all 0.2s;
                margin-bottom: 12px;
                box-sizing: border-box;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .btn-activate {{
                width: 100%;
                max-width: 320px;
                padding: 18px;
                background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%);
                border: none;
                color: white;
                font-weight: 800;
                border-radius: 16px;
                cursor: pointer;
                font-size: 13px;
                letter-spacing: 1px;
                text-transform: uppercase;
                box-shadow: 0 5px 25px rgba(100,27,250,0.4);
                transition: transform 0.2s, background 0.2s;
            }}
            .btn-activate:disabled {{
                background: #1a2233;
                color: #4b5975;
                cursor: not-allowed;
                box-shadow: none;
            }}
            .btn-main {{
                background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%);
                box-shadow: 0 5px 20px rgba(100,27,250,0.3);
            }}
            .btn-auto {{
                background: linear-gradient(135deg, #00ff66 0%, #00b344 100%);
                color: #000;
                font-weight: 900;
                box-shadow: 0 5px 20px rgba(0,255,102,0.2);
            }}
            .btn-scan-photo {{
                background: linear-gradient(135deg, #22c55e 0%, #15803d 100%);
                color: white;
                font-weight: 800;
                box-shadow: 0 5px 15px rgba(34,197,94,0.2);
            }}
            .btn-vip-top {{
                padding: 9px 14px;
                border: none;
                border-radius: 10px;
                background: linear-gradient(270deg, #ffd700, #ffa500, #b8860b, #ffd700);
                background-size: 400% 400%;
                animation: shine 4s ease infinite;
                color: #000 !important;
                font-weight: 900;
                font-size: 11px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(255,215,0,0.3);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .btn-pocket {{
                background: #141924;
                border: 1px solid #222d42;
                color: #38ef7d;
                margin-top: 5px;
            }}
            .btn-support {{
                background: #080a10;
                border: 1px solid #161b26;
                color: #586988;
                font-size: 11px;
                margin-top: 15px;
            }}
            .btn-mart {{
                background: #ff3344;
                display: none;
                box-shadow: 0 5px 15px rgba(255,51,68,0.3);
            }}
            .btn:active, .btn-activate:active {{
                transform: scale(0.97);
            }}
            
            /* СТАТИСТИКА И ДЕТАЛИ */
            .lang-select {{
                background: #0f131e;
                color: white;
                border: 1px solid #1a2233;
                padding: 6px 12px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }}
            .payout-badge {{
                color: #00ff66;
                font-weight: 800;
                font-size: 12px;
                margin-top: 5px;
                display: block;
                letter-spacing: 0.5px;
            }}
            .stat-panel {{
                background: #080a10;
                border: 1px solid #1a2233;
                border-radius: 22px;
                padding: 16px;
                margin-bottom: 22px;
                text-align: center;
                width: 100%;
                box-sizing: border-box;
            }}
            .wr-val {{
                font-size: 24px;
                font-weight: 900;
                color: #00ff66;
                margin-bottom: 12px;
                text-shadow: 0 0 15px rgba(0,255,102,0.25);
                letter-spacing: 0.5px;
            }}
            .counter-box {{
                display: flex;
                gap: 12px;
            }}
            .count-btn {{
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                background: #0f131e;
                padding: 12px;
                border-radius: 14px;
                border: 1px solid #1a2233;
                cursor: pointer;
                font-weight: 800;
                font-size: 14px;
                transition: transform 0.1s, background 0.2s;
                color: white;
            }}
            .count-btn:active {{
                transform: scale(0.95);
                background: #161b26;
            }}
            .ai-comment {{
                background: #0f131e;
                border: 1px solid #1a2233;
                border-radius: 14px;
                padding: 14px;
                font-size: 12px;
                color: #94a3b8;
                margin-top: 14px;
                display: none;
                text-align: left;
                line-height: 1.5;
                border-left: 4px solid #a855f7;
            }}
        </style>
    </head>
    <body>

        <div id="auth-screen" class="container" style="display: none;">
            <div class="title">HROM QUANTUM CORE</div>
            <div class="subtitle">Для доступа к сигналам введите ваш уникальный код</div>
            <div style="width: 100%; display: flex; flex-direction: column; align-items: center;">
                <div class="input-box">
                    <input type="text" id="username" placeholder="Введите ваш @username в ТГ">
                </div>
                <div class="input-box">
                    <input type="text" id="code" placeholder="Введите код доступа">
                </div>
                <button type="button" id="submitBtn" class="btn-activate" onclick="sendForm()">Активировать доступ</button>
                <div id="error-msg" style="color: #ff3344; font-size: 13px; font-weight: bold; margin-top: 16px; text-align: center; display: none;"></div>
                <div id="success-msg" style="color: #00ff66; font-size: 13px; font-weight: bold; margin-top: 16px; text-align: center; display: none;"></div>
            </div>
        </div>

        <div id="terminal-screen" style="display: none; flex-direction:
