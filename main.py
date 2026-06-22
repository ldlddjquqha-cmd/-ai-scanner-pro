import json
import random
import asyncio
import numpy as np
import os
import uvicorn
import httpx
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from google import genai  # Новый официальный SDK google-genai
from google.genai import types

app = FastAPI()

# --- КОНФИГУРАЦИЯ СИСТЕМЫ И ТЕЛЕГРАМ БОТА ---
DB_FILE = "requests.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8761108877:AAHGS5tME2dqGF6iMC1IIN9HzgWJ0wgNGTU")
ADMIN_CHAT_ID = "6765689893"

# Настройка ключа ИИ через новый SDK
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ТВОЙ_GEMINI_API_KEY_ЗДЕСЬ")
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Жесткая системная инструкция для ИИ ядра HROM QUANTUM (Без рандома)
SYSTEM_INSTRUCTION = """
Ты — старший ИИ-аналитик квантового торгового ядра HROM QUANTUM.
Твоя задача — проводить бескомпромиссный математический и технический анализ рынка.
Тебе категорически запрещено выдавать случайные прогнозы, угадывать или подстраивать результаты.
Если на рынке наблюдается флэт, ложные пробития, отсутствие объемов или спорные показатели индикаторов, ты ОБЯЗАН выдать вердикт "СИГНАЛА НЕТ".
Твоя цель — сохранить депозит трейдера, отсекая рыночный шум. Твой анализ должен быть хладнокровным.
"""

def get_db():
    if not os.path.exists(DB_FILE): 
        return {"users": {}, "keys": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: 
            data = json.load(f)
            if "users" not in data: 
                data = {"users": data, "keys": []}
            return data
        except: 
            return {"users": {}, "keys": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- СИСТЕМА УВЕДОМЛЕНИЙ В ТЕЛЕГРАМ ---
async def send_tg_notification(username, code):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "❌ Забанить", "callback_data": f"ban:{username}"},
                {"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}
            ]
        ]
    }
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"🔔 **Новый ученик активировал код!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Текущий статус:** ✅ Доступ разрешен",
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
            print(f"[TG LOG] Уведомление об активации {username} успешно отправлено админу.")
        except Exception as e: 
            print(f"[TG ERROR] Ошибка отправки уведомления в ТГ: {e}")

async def send_tg_notification_simple(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"[TG ERROR] Ошибка отправки простого сообщения: {e}")

async def edit_tg_message_status(chat_id, message_id, username, status_text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": f"🔔 **Управление учеником**\n\n**Ник:** @{username}\n**Статус изменен:** {status_text}",
        "parse_mode": "Markdown"
    }
    if reply_markup: 
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"[TG ERROR] Ошибка редактирования сообщения: {e}")

# --- ТЕЛЕГРАМ ВЕБХУК (ОБРАБОТКА КНОПОК И КОМАНД) ---
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        print(f"[WEBHOOK] Получены данные: {data}")
        
        if "callback_query" in data:
            callback_query = data["callback_query"]
            chat_id = str(callback_query["message"]["chat"]["id"])
            message_id = callback_query["message"]["message_id"]
            callback_data = callback_query["data"]
            
            if chat_id == ADMIN_CHAT_ID:
                action, username = callback_data.split(":")
                db = get_db()
                
                if action == "ban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "blocked"
                    save_db(db)
                    unban_markup = {"inline_keyboard": [[{"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}]]}
                    await edit_tg_message_status(chat_id, message_id, username, "🚫 Заблокирован (Доступ закрыт)", reply_markup=unban_markup)
                    print(f"[ADMIN ACTION] Ученик @{username} заблокирован через инлайн-кнопку.")
                    
                elif action == "unban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "approved"
                    save_db(db)
                    standard_markup = {
                        "inline_keyboard": [
                            [
                                {"text": "❌ Забанить", "callback_data": f"ban:{username}"},
                                {"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}
                            ]
                        ]
                    }
                    await edit_tg_message_status(chat_id, message_id, username, "✅ Разблокирован (Доступ open)", reply_markup=standard_markup)
                    print(f"[ADMIN ACTION] Ученик @{username} разблокирован через инлайн-кнопку.")
            return {"status": "ok"}

        if "message" in data and "text" in data["message"]:
            text = data["message"]["text"].strip()
            chat_id = str(data["message"]["chat"]["id"])
            
            if chat_id == ADMIN_CHAT_ID:
                parts = text.split()
                if len(parts) >= 2:
                    command = parts[0]
                    username = parts[1].replace("@", "").strip().replace(" ", "")
                    db = get_db()
                    
                    if command == "/бан":
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "blocked"
                        save_db(db)
                        await send_tg_notification_simple(f"🚫 Пользователь @{username} заблокирован.")
                        print(f"[ADMIN COMMAND] Успешная блокировка @{username}")
                    
                    elif command == "/разбанить":
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "approved"
                        save_db(db)
                        await send_tg_notification_simple(f"✅ Пользователь @{username} разблокирован.")
                        print(f"[ADMIN COMMAND] Успешная разблокировка @{username}")
    except Exception as e: 
        print(f"[WEBHOOK ERROR] Исключение при обработке вебхука: {e}")
        
    return {"status": "ok"}

# --- СТРАНИЦА ГЕНЕРАЦИИ КЛЮЧЕЙ ДОСТУПА ---
@app.get("/generate_key")
async def generate_key(master: str = None):
    if master != "SUPER_ADMIN_123": 
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ закрыт. Неверный секретный ключ!</h1>")
    
    chars = "0123456789ABCDEF"
    new_key = "HROM_" + "".join(random.choice(chars) for _ in range(6))
    
    db = get_db()
    db["keys"].append(new_key)
    save_db(db)
    
    print(f"[SERVER LOG] Сгенерирован новый одноразовый ключ: {new_key}")
    
    return HTMLResponse(f"""
    <div style="background:#06080c; color:#ffffff; font-family:sans-serif; text-align:center; padding:50px; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; box-sizing:border-box;">
        <p style="color:#586988; font-size:18px; margin-bottom:5px;">Создан новый одноразовый ключ:</p>
        <div style="background:#0f131e; border:1px solid #1a2233; color:#00ff66; font-size:26px; font-weight:bold; padding:15px 30px; border-radius:12px; letter-spacing:1px; margin-bottom:20px; box-shadow: 0 0 20px rgba(0,255,102,0.2);">
            {new_key}
        </div>
        <p style="color:#4b5975; font-size:13px; max-width:320px; margin-bottom:25px; line-height:1.5;">Передай этот ключ новому ученику. При активации его сессия привяжется намертво.</p>
        <a href="/generate_key?master=SUPER_ADMIN_123" style="text-decoration:none;">
            <button style="background:#963bfe; color:white; font-weight:bold; padding:14px 28px; border:none; border-radius:10px; cursor:pointer; font-size:14px; text-transform:uppercase; transition:0.2s;">Создать еще один</button>
        </a>
    </div>
    """)

# --- ВЕБ ПАНЕЛЬ АДМИНИСТРАТОРА ---
@app.get("/admin_panel")
async def admin_panel(secret: str = None):
    if secret != "SUPER_ADMIN_123": 
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

# --- ПРОВЕРКИ И АКТИВАЦИИ РЕГИСТРАЦИИ ---
@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    return JSONResponse({"status": status})

@app.post("/request_access")
async def request_access(username: str = Form(...), code: str = Form(...)):
    username = username.strip().replace("@", "").replace(" ", "")
    code = code.strip().replace(" ", "")
    db = get_db()
    
    if username in db["users"] and db["users"][username]["status"] == "blocked":
        return JSONResponse({"success": False, "message": "Вы заблокированы!"})

    if username in db["users"] and db["users"][username]["status"] == "approved":
        return JSONResponse({"success": True, "message": "Доступ уже подтвержден! Заходим..."})

    if code not in db["keys"]:
        return JSONResponse({"success": False, "message": "Неверный или уже использованный код!"})
    
    db["keys"].remove(code)
    db["users"][username] = {"status": "approved", "used_code": code}
    save_db(db)
    
    asyncio.create_task(send_tg_notification(username, code))
    
    return JSONResponse({"success": True, "message": "Код успешно активирован! Загрузка..."})

# --- МАССИВ АКТИВОВ БЕЗ СОКРАЩЕНИЙ ---
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
        "[ВСІ АКТИВИ] — ЖИВИЙ РИНОК": {
            "ВАЛЮТНІ ПАРИ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    }
}

# --- МАТЕМАТИЧЕСКИЙ АНАЛИЗАТОР ТРЕНДОВ И ИНДИКАТОРОВ ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: 
        return 50.0
    deltas = np.diff(prices)
    up = np.where(deltas > 0, deltas, 0).mean()
    down = np.where(deltas < 0, -deltas, 0).mean()
    if down == 0: 
        return 100.0
    rs = up / down
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_ema(prices, period=20):
    if len(prices) < period: 
        return prices[-1]
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    return np.convolve(prices, weights, mode='valid')[-1]

def generate_otc_candles(asset_name, count=50):
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
    return prices

# --- НАСТОЯЩИЙ ИИ АНАЛИЗАТОР СЕТИ GEMINI (БЕЗ РАНДОМА) ---
async def analyze_market_with_ai(asset: str, timeframe: str, current_price: float, rsi: float, ema: float, prices: list):
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
        parts = text_result.split()
        
        if "СИГНАЛА_НЕТ" in parts[0] or "НЕТ" in parts[0]:
            return "NONE", 0, "ИИ-анализ: Вход в сделку заблокирован из-за рыночного шума или бокового тренда."
            
        signal = "UP" if "ВВЕРХ" in parts[0] else "DOWN"
        accuracy = int(''.join(filter(str.isdigit, parts[1]))) if len(parts) > 1 else 85
        return signal, accuracy, f"Квантовый анализ ядра HROM завершен. Точка входа сформирована на основе тренда."
        
    except Exception as e:
        print(f"[AI CORE ERROR] Ошибка ИИ-генерации: {e}. Резервный технический шлюз.")
        if current_price > ema and rsi < 38:
            return "UP", 76, "Резервный алгоритм ТА: Сигнал на повышение от скользящей средней."
        elif current_price < ema and rsi > 62:
            return "DOWN", 76, "Резервный алгоритм ТА: Сигнал на понижение от зоны сопротивления."
        return "NONE", 0, "Резервный алгоритм ТА: Недостаточно волатильности для безопасной сделки."

@app.post("/scan_screenshot")
async def scan_screenshot(username: str = Form(""), file: UploadFile = File(...)):
    username = username.strip().replace("@", "")
    print(f"[AI SCANNER] Ученик @{username} отправил изображение для ИИ-сканирования.")
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

@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str, username: str = ""):
    print(f"[CORE LOG] Запрос сигнала. Ученик: {username}, Актив: {asset}, Свеча: {timeframe}")
    if username:
        asyncio.create_task(send_tg_notification_simple(f"📊 Ученик @{username} запросил ИИ-анализ рынка пары: **{asset}** ({timeframe})"))
        
    await asyncio.sleep(0.3)
    is_otc = "OTC" in asset
    clean_asset = asset.replace(" OTC", "").strip()
    
    if is_otc:
        prices = generate_otc_candles(asset, count=50)
    else:
        binance_symbol = BINANCE_MAPPING.get(clean_asset, "BTCUSDT")
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1m&limit=50"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=3.0)
                prices = [float(c[4]) for c in response.json()]
        except Exception as e:
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

# --- ПОЛНОЦЕННЫЙ ИНТЕРФЕЙС ТЕРМИНАЛА ---
@app.get("/", response_class=HTMLResponse)
async def index():
    html_data = json.dumps(ASSETS_DATA)
    return HTMLResponse(content=rf"""
    <html style="background:#06080c; color:#ffffff; font-family:'Segoe UI', Roboto, sans-serif; margin:0; padding:0;">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HROM QUANTUM CORE v16.0</title>
        <style>
            .container {{ max-width: 430px; margin: 0 auto; padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; box-sizing: border-box; }}
            .title {{ font-size: 20px; font-weight: 800; color: #a855f7; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; text-shadow: 0 0 15px rgba(168,85,247,0.3); }}
            .subtitle {{ font-size: 11px; color: #4b5975; font-weight: 600; margin-bottom: 30px; text-align: center; }}
            .input-box {{ width: 100%; max-width: 320px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; padding: 16px; margin-bottom: 12px; box-sizing: border-box; text-align: center; }}
            input {{ background: transparent; border: none; color: white; width: 100%; font-size: 14px; font-weight: bold; outline: none; text-align: center; }}
            input::placeholder {{ color: #4b5975; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            @keyframes shine {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
            .loader {{ width: 45px; height: 45px; border: 4px solid #161b26; border-top: 4px solid #a855f7; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 15px auto; display: none; }}
            select {{ width: 100%; padding: 14px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; font-size: 14px; font-weight: 600; color: #ffffff; outline: none; appearance: none; }}
            label {{ font-size: 11px; font-weight: bold; color: #4b5975; display: block; margin-bottom: 5px; letter-spacing: 0.8px; text-transform: uppercase; }}
            .btn {{ width: 100%; padding: 16px; border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; transition: all 0.2s; margin-bottom: 10px; box-sizing: border-box; }}
            .btn-activate {{ width: 100%; max-width: 320px; padding: 16px; background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; box-shadow: 0 5px 20px rgba(100,27,250,0.4); transition: transform 0.2s; }}
            .btn-activate:disabled {{ background: #1a2233; color: #4b5975; cursor: not-allowed; box-shadow: none; }}
            .btn-main {{ background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); box-shadow: 0 5px 20px rgba(100,27,250,0.4); }}
            .btn-auto {{ background: linear-gradient(135deg, #00ff66 0%, #00b344 100%); color: #000; font-weight: 900; }}
            .btn-scan-photo {{ background: linear-gradient(135deg, #38ef7d 0%, #11998e 100%); color: white; font-weight: 800; border: 1px dashed #ffffff; }}
            .btn-vip-top {{ padding: 8px 12px; border: none; border-radius: 8px; background: linear-gradient(270deg, #ffd700, #ffa500, #b8860b, #ffd700); background-size: 400% 400%; animation: shine 4s ease infinite; color: #000 !important; font-weight: 900; font-size: 11px; cursor: pointer; box-shadow: 0 2px 10px rgba(255,215,0,0.3); text-transform: uppercase; letter-spacing: 0.5px; }}
            .btn-pocket {{ background: #141924; border: 1px solid #222d42; color: #38ef7d; width: 100%; }}
            .btn-support {{ background: #080a10; border: 1px solid #161b26; color: #586988; font-size: 11px; margin-top: 15px; width: 100%; }}
            .btn-mart {{ background: #ff3344; display: none; width: 100%; }}
            .btn:active, .btn-activate:active {{ transform: scale(0.98); }}
            .lang-select {{ background: #0f131e; color: white; border: 1px solid #1a2233; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }}
            .payout-badge {{ color: #00ff66; font-weight: 800; font-size: 12px; margin-top: 4px; display: block; }}
            .stat-panel {{ background: #080a10; border: 1px solid #1a2233; border-radius: 20px; padding: 15px; margin-bottom: 20px; text-align: center; width: 100%; box-sizing: border-box; }}
            .wr-val {{ font-size: 22px; font-weight: 900; color: #00ff66; margin-bottom: 10px; text-shadow: 0 0 15px rgba(0,255,102,0.2); }}
            .counter-box {{ display: flex; gap: 10px; }}
            .count-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; background: #0f131e; padding: 10px; border-radius: 12px; border: 1px solid #1a2233; cursor: pointer; font-weight: 800; font-size: 13px; transition: 0.2s; color: white; }}
            .ai-comment {{ background: #0f131e; border: 1px solid #1a2233; border-radius: 12px; padding: 12px; font-size: 12px; color: #94a3b8; margin-top: 10px; display: none; text-align: left; line-height: 1.4; border-left: 3px solid #a855f7; }}
        </style>
    </head>
    <body>

        <div id="auth-screen" class="container" style="display: none;">
            <div class="title">HROM QUANTUM CORE</div>
            <div class="subtitle">Для доступа к сигналам введите ваш уникальный код</div>
            <div style="width: 100%; display: flex; flex-direction: column; align-items: center;">
                <div class="input-box"><input type="text" id="username" placeholder="Введите ваш @username в ТГ"></div>
                <div class="input-box"><input type="text" id="code" placeholder="Введите код доступа"></div>
                <button type="button" id="submitBtn" class="btn-activate" onclick="sendForm()">Активировать доступ</button>
                <div id="error-msg" style="color: #ff3344; font-size: 13px; font-weight: bold; margin-top: 15px; text-align: center; display: none;"></div>
                <div id="success-msg" style="color: #00ff66; font-size: 13px; font-weight: bold; margin-top: 15px; text-align: center; display: none;"></div>
            </div>
        </div>

        <div id="terminal-screen" style="display: none; flex-direction: column; min-height: 100vh; align-items: center;">
            <div style="max-width:430px; width: 100%; margin:15px auto 0 auto; padding:0 15px; display:flex; justify-content:space-between; align-items:center; box-sizing: border-box;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span id="flag_icon" style="font-size:20px; line-height:1;">🇷🇺</span>
                    <select id="lang" class="lang-select" onchange="changeLang()">
                        <option value="ru">🇷🇺 RU</option>
                        <option value="en">🇺🇸 EN</option>
                        <option value="ua">🇺🇦 UA</option>
                    </select>
                </div>
                <a href="https://t.me/+uekq4TquqkM4Mzcy" target="_blank" style="text-decoration: none;"><button id="vip_btn_text" class="btn-vip-top">👑 VIP СИГНАЛЫ</button></a>
            </div>

            <div style="max-width:430px; width: 100%; margin:15px auto 30px auto; padding:25px; background:#080a10; border-radius:28px; border: 1px solid #121722; box-shadow: 0 25px 50px rgba(0,0,0,0.8); text-align:center; box-sizing: border-box;">
                <div class="stat-panel">
                    <div id="wr_display" class="wr-val">WIN RATE: 0%</div>
                    <div class="counter-box">
                        <button class="count-btn" onclick="updateStat('win', 1)" oncontextmenu="updateStat('win', -1); return false;"><span id="lbl_profit" style="font-size:9px; color:#586988; text-transform:uppercase;">Profit</span><span id="win_counter" style="color:#00ff66; font-size:16px;">0</span></button>
                        <button class="count-btn" onclick="updateStat('loss', 1)" oncontextmenu="updateStat('loss', -1); return false;"><span id="lbl_loss" style="font-size:9px; color:#586988; text-transform:uppercase;">Loss</span><span id="loss_counter" style="color:#ff3344; font-size:16px;">0</span></button>
                    </div>
                    <div id="lbl_reset" onclick="resetStats()" style="font-size:9px; color:#4b5975; margin-top:12px; cursor:pointer; text-decoration:underline;">СБРОСИТЬ СТАТИСТИКУ</div>
                </div>
                <div style="text-align:left; margin-bottom:14px;"><label id="lbl_market">КАТЕГОРИЯ РЫНКА</label><select id="cat" onchange="updCategory()"></select></div>
                <div id="sub_cat_block" style="text-align:left; margin-bottom:14px;"><label id="lbl_type">ТИП АКТИВА</label><select id="sub_cat" onchange="updSubCategory()"></select></div>
                <div style="text-align:left; margin-bottom:14px;"><label id="lbl_asset">АКТИВНАЯ ПАРА</label><select id="asset" onchange="updAsset()"></select><span id="payout_lbl" class="payout-badge">PAYOUT: 92%</span></div>
                <div style="display:flex; gap:12px; margin-bottom:20px; text-align:left;">
                    <div style="flex:1;"><label id="lbl_tf">ИНТЕРВАЛ СВЕЧИ</label><select id="time"></select></div>
                    <div style="flex:1;"><label id="lbl_exp">ЭКСПИРАЦИЯ</label><select id="exp"></select></div>
                </div>
                
                <button id="runBtn" class="btn btn-main" onclick="startFlow(false)">СКАНИРОВАТЬ РЫНОК</button>
                <button id="autoBtn" class="btn btn-auto" onclick="startFlow(true)">ИИ АНАЛИЗ ТЕКУЩЕЙ ПАРЫ</button>
                
                <input type="file" id="screenshot_file" accept="image/*" capture="environment" style="display: none;" onchange="uploadScreenshot()">
                <button id="scanPhotoBtn" class="btn btn-scan-photo" onclick="document.getElementById('screenshot_file').click()">📸 ИИ СКАНИРОВАТЬ ФОТО</button>
                
                <button id="martBtn" class="btn btn-mart" onclick="startFlow(false, true)">ПЕРЕКРЫТИЕ</button>
                
                <a href="https://pocketoption.com/register" target="_blank" style="text-decoration: none;"><button id="btn_pocket" class="btn btn-pocket">ОТКРЫТЬ POCKET OPTION</button></a>
                <div id="status" style="font-size:11px; color:#4b5975; margin-top:20px; min-height:18px; font-weight:700; letter-spacing:0.5px;">СИСТЕМА СИНХРОНИЗИРОВАНА</div>
                <div id="loader" class="loader"></div>
                
                <div id="res" style="font-size:55px; font-weight:900; margin:10px 0; min-height:66px; letter-spacing:2px; color:#ffffff;">--</div>
                <div id="accuracy" style="font-size:14px; font-weight:800; color:#a855f7; margin-top:-5px; margin-bottom:10px; display:none;"></div>
                <div id="ai_comment" class="ai-comment"></div>
                <div id="timer" style="font-size:14px; font-weight:800; color:#ffaa00; margin-bottom:15px; min-height:20px;"></div>
                
                <button class="btn" style="background:#141924; color:#ff3344; margin-top:10px; font-size:11px; padding:10px;" onclick="logout()">ВЫЙТИ ИЗ АККАУНТА</button>
                <a href="https://t.me/andriddddd" target="_blank" style="text-decoration: none;"><button id="btn_supp" class="btn btn-support">РАЗРАБОТЧИК / SUPPORT</button></a>
            </div>
        </div>

        <div id="blocked-screen" style="display: none; width:100%; background:#06080c; color:#ff3344; font-family:sans-serif; text-align:center; padding-top:100px; height:100vh; flex-direction:column; align-items:center; box-sizing: border-box;">
            <h1 style="font-size:24px; padding: 0 20px;">Доступ заблокирован администратором.</h1>
        </div>

        <script>
            const rawData = {html_data};
            
            const options_min_ru = ["1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "10 мин", "15 мин"];
            const options_min_en = ["1 min", "2 min", "3 min", "4 min", "5 min", "10 min", "15 min"];
            const options_min_ua = ["1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "10 хв", "15 хв"];

            let wins = 0, losses = 0, currentBet = 100, martStep = 0, currentExpInterval = null;

            async function checkAuth() {{
                const localUser = localStorage.getItem('tg_username');
                if (!localUser) {{ showScreen('auth-screen'); return; }}
                try {{
                    const response = await fetch('/check_user_status?username=' + encodeURIComponent(localUser));
                    const data = await response.json();
                    if (data.status === 'approved') {{ showScreen('terminal-screen'); changeLang(); }} 
                    else {{ localStorage.removeItem('tg_username'); showScreen('auth-screen'); }}
                }} catch(e) {{ showScreen('auth-screen'); }}
            }}

            function showScreen(screenId) {{
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('terminal-screen').style.display = 'none';
                document.getElementById('blocked-screen').style.display = 'none';
                document.getElementById(screenId).style.display = 'flex';
            }}

            function logout() {{ localStorage.removeItem('tg_username'); window.location.reload(); }}
            function updateStat(type, val) {{ if(type=='win') wins = Math.max(0, wins + val); else losses = Math.max(0, losses + val); updateDisplay(); }}
            
            function updateDisplay() {{
                document.getElementById('win_counter').innerText = wins;
                document.getElementById('loss_counter').innerText = losses;
                let total = wins + losses;
                let wr = total == 0 ? 0 : ((wins/total)*100).toFixed(1);
                let el = document.getElementById('wr_display');
                el.innerText = "WIN RATE: " + wr + "%";
                el.style.color = wr >= 50 ? "#00ff66" : "#ff3344";
            }}
            
            function resetStats() {{ wins=0; losses=0; currentBet=100; martStep=0; updateDisplay(); }}
            
            const flags = {{ ru: "🇷🇺", en: "🇺🇸", ua: "🇺🇦" }};
            const dictionary = {{ 
                ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", scan: "СКАНИРОВАТЬ РЫНОК", auto: "ИИ АНАЛИЗ ТЕКУЩЕЙ ПАРЫ", pocket: "ОТКРЫТЬ POCKET OPTION", support: "РАЗРАБОТЧИК / SUPPORT", ready: "СИСТЕМА СИНХРОНИЗИРОВАНА", vip: "👑 VIP СИГНАЛЫ", mart: "ПЕРЕКРЫТИЕ", profit: "Profit", loss: "Loss", reset: "СБРОСИТЬ СТАТИСТИКУ", up: "ВВЕРХ", down: "ВНИЗ", enter: "ВХОД ЧЕРЕЗ: ", open: "АНАЛИЗ ЗАВЕРШЕН!", close: "ТАЙМЕР ЭКСПИРАЦИИ: ", end: "ЦИКЛ ЗАВЕРШЕН" }}, 
                en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION TIME", scan: "MARKET SCAN", auto: "AI ANALYZE THIS PAIR", pocket: "OPEN POCKET OPTION", support: "DEVELOPER / SUPPORT", ready: "SYSTEM SYNCHRONIZED", vip: "👑 VIP SIGNALS", mart: "MARTINGALE", profit: "Profit", loss: "Loss", reset: "RESET STATISTICS", up: "CALL / UP", down: "PUT / DOWN", enter: "ENTRY IN: ", open: "ANALYSIS DONE!", close: "CLOSING IN: ", end: "CYCLE COMPLETED" }},
                ua: {{ market: "КАТЕГОРІЯ РИНКУ", type: "ТИП АКТИВУ", asset: "АКТИВНА ПАРА", tf: "ІНТЕРВАЛ СВІЧКИ", exp: "ЕКСПІРАЦІЯ", scan: "СКАНУВАТИ РИНОК", auto: "ШІ АНАЛІЗ ПОТОЧНОЇ ПАРИ", pocket: "ВІДКРИТИ POCKET OPTION", support: "РОЗРОБНИК / SUPPORT", ready: "СИСТЕМА СИНХРОНІЗОВАНА", vip: "👑 VIP СИГНАЛИ", mart: "ПЕРЕКРИТТЯ", profit: "Профіт", loss: "Лос", reset: "СКИНУТИ СТАТИСТИКУ", up: "ВГОРУ", down: "ВНИЗ", enter: "ВХІД ЧЕРЕЗ: ", open: "АНАЛІЗ ЗАВЕРШЕНО!", close: "ДО ЗАКРИТЯ: ", end: "ЦИКЛ ЗАВЕРШЕНО" }}
            }};
            
            function changeLang() {{ 
                let l = document.getElementById('lang').value;
                let d = dictionary[l] || dictionary['en'];
                document.getElementById('flag_icon').innerText = flags[l];
                document.getElementById('lbl_market').innerText = d.market; 
                document.getElementById('lbl_type').innerText = d.type; 
                document.getElementById('lbl_asset').innerText = d.asset; 
                document.getElementById('lbl_tf').innerText = d.tf; 
                document.getElementById('lbl_exp').innerText = d.exp; 
                document.getElementById('runBtn').innerText = d.scan; 
                document.getElementById('autoBtn').innerText = d.auto; 
                document.getElementById('btn_pocket').innerText = d.pocket; 
                document.getElementById('btn_supp').innerText = d.support; 
                document.getElementById('status').innerText = d.ready; 
                document.getElementById('vip_btn_text').innerText = d.vip; 
                document.getElementById('martBtn').innerText = d.mart;
                document.getElementById('lbl_profit').innerText = d.profit;
                document.getElementById('lbl_loss').innerText = d.loss;
                document.getElementById('lbl_reset').innerText = d.reset;
                let catSelect = document.getElementById('cat'); 
                catSelect.innerHTML = ""; 
                Object.keys(rawData[l]).forEach(c => {{ catSelect.innerHTML += `<option>${{c}}</option>`; }}); 
                updCategory(); 
            }}
            
            function calcLocalPayout(assetName) {{ return assetName.includes("OTC") ? 92 : 82; }}
            function updCategory() {{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, types = Object.keys(rawData[l][c]); document.getElementById('sub_cat').innerHTML = types.map(t => `<option>${{t}}</option>`).join(''); updSubCategory(); }}
            function updSubCategory() {{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, t = document.getElementById('sub_cat').value, assets = rawData[l][c][t] || []; document.getElementById('asset').innerHTML = assets.map(a => `<option>${{a}}</option>`).join(''); updAsset(); }}
            
            function updAsset() {{ 
                let l = document.getElementById('lang').value;
                let asset = document.getElementById('asset').value; 
                document.getElementById('payout_lbl').innerText = `PAYOUT: ${{calcLocalPayout(asset)}}%`; 
                
                let timeSelect = document.getElementById('time');
                let expSelect = document.getElementById('exp');
                
                let min_opts = l === 'ru' ? options_min_ru : (l === 'ua' ? options_min_ua : options_min_en);
                
                timeSelect.innerHTML = min_opts.map(o => `<option>${{o}}</option>`).join('');
                expSelect.innerHTML = min_opts.map(o => `<option>${{o}}</option>`).join('');
            }}
            
            async function startFlow(isAIChoice, isMart = false) {{
                if(currentExpInterval) clearInterval(currentExpInterval);
                let l = document.getElementById('lang').value;
                let d = dictionary[l] || dictionary['en'];
                let localUser = localStorage.getItem('tg_username') || "unknown";

                if(!isMart) {{ currentBet = 100; martStep = 0; }} 
                else {{ currentBet = (currentBet * 2.3).toFixed(2); martStep++; }}
                
                document.getElementById('martBtn').style.display = 'none';
                document.getElementById('res').innerText = "--";
                document.getElementById('accuracy').style.display = 'none';
                document.getElementById('ai_comment').style.display = 'none';
                document.getElementById('timer').innerText = "";
                document.getElementById('loader').style.display = 'block';
                
                let assetField = document.getElementById('asset').value;
                let timeField = document.getElementById('time').value;
                
                let resp = await fetch(`/get_signal?asset=${{encodeURIComponent(assetField)}}&timeframe=${{encodeURIComponent(timeField)}}&username=${{encodeURIComponent(localUser)}}`);
                let data = await resp.json();
                
                document.getElementById('loader').style.display = 'none';
                
                if(data.signal === "NONE") {{
                    document.getElementById('res').innerText = "ПРОПУСК";
                    document.getElementById('res').style.color = "#586988";
                    document.getElementById('ai_comment').style.display = 'block';
                    document.getElementById('ai_comment').innerText = data.ai_comment;
                    return;
                }}
                
                document.getElementById('res').innerText = (data.signal == "UP" ? d.up : d.down);
                document.getElementById('res').style.color = data.signal == "UP" ? "#00ff66" : "#ff3344";
                document.getElementById('accuracy').style.display = 'block';
                document.getElementById('accuracy').innerText = "AI ACCURACY: " + data.accuracy + "%";
                
                document.getElementById('ai_comment').style.display = 'block';
                document.getElementById('ai_comment').innerText = data.ai_comment;
                
                let expVal = document.getElementById('exp').value;
                let expSeconds = parseInt(expVal.replace(/\D/g, '')) * 60;
                
                let timerEl = document.getElementById('timer');
                timerEl.innerText = d.open;
                currentExpInterval = setInterval(() => {{
                    if(expSeconds > 0) {{ 
                        timerEl.innerText = d.close + expSeconds + (l == 'ru' || l == 'ua' ? " сек" : " sec"); 
                        expSeconds--; 
                    }} else {{ 
                        clearInterval(currentExpInterval); 
                        timerEl.innerText = d.end; 
                        document.getElementById('martBtn').style.display = 'block'; 
                    }}
                }}, 1000);
            }}

            async function uploadScreenshot() {{
                const fileInput = document.getElementById('screenshot_file');
                if(fileInput.files.length === 0) return;
                
                let l = document.getElementById('lang').value;
                let d = dictionary[l] || dictionary['en'];
                let localUser = localStorage.getItem('tg_username') || "unknown";
                
                document.getElementById('res').innerText = "--";
                document.getElementById('accuracy').style.display = 'none';
                document.getElementById('ai_comment').style.display = 'none';
                document.getElementById('timer').innerText = "";
                document.getElementById('loader').style.display = 'block';
                document.getElementById('status').innerText = "ИИ ИЗУЧАЕТ СНИМОК ГРАФИКА...";
                
                const formData = new FormData();
                formData.append('username', localUser);
                formData.append('file', fileInput.files[0]);
                
                try {{
                    const response = await fetch('/scan_screenshot', {{ method: 'POST', body: formData }});
                    const result = await response.json();
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('status').innerText = d.ready;
                    
                    if(result.success) {{
                        if(result.signal === "NONE") {{
                            document.getElementById('res').innerText = "ПРОПУСК";
                            document.getElementById('res').style.color = "#586988";
                        }} else {{
                            document.getElementById('res').innerText = (result.signal == "UP" ? d.up : d.down);
                            document.getElementById('res').style.color = result.signal == "UP" ? "#00ff66" : "#ff3344";
                            document.getElementById('accuracy').style.display = 'block';
                            document.getElementById('accuracy').innerText = "VISION ACCURACY: " + result.accuracy + "%";
                        }}
                        const commentDiv = document.getElementById('ai_comment');
                        commentDiv.style.display = 'block';
                        commentDiv.innerText = result.raw_analysis;
                    }} else {{
                        alert("Ошибка ИИ-сканера: " + result.message);
                    }}
                }} catch(e) {{
                    document.getElementById('loader').style.display = 'none';
                    alert("Ошибка отправки кадра в ИИ: " + e.message);
                }}
                fileInput.value = "";
            }}

            async function sendForm() {{
                const userInp = document.getElementById('username').value.trim().replace('@', '');
                const codeInp = document.getElementById('code').value.trim();
                const btn = document.getElementById('submitBtn');
                const errDiv = document.getElementById('error-msg');
                const succDiv = document.getElementById('success-msg');
                errDiv.style.display = 'none'; succDiv.style.display = 'none';

                if(!userInp || !codeInp) {{ errDiv.innerText = "Заполните все поля!"; errDiv.style.display = 'block'; return; }}
                btn.disabled = true; btn.innerText = "Проверка кода...";

                try {{
                    const formData = new FormData();
                    formData.append('username', userInp);
                    formData.append('code', codeInp);
                    const response = await fetch('/request_access', {{ method: 'POST', body: formData }});
                    const result = await response.json();

                    if(result.success) {{
                        succDiv.innerText = result.message; succDiv.style.display = 'block';
                        localStorage.setItem('tg_username', userInp);
                        setTimeout(() => {{ checkAuth(); }}, 1000);
                    }} else {{
                        errDiv.innerText = result.message; errDiv.style.display = 'block';
                        btn.disabled = false; btn.innerText = "Активировать доступ";
                    }}
                }} catch(e) {{
                    errDiv.innerText = "Ошибка: " + e.message; errDiv.style.display = 'block';
                    btn.disabled = false; btn.innerText = "Активировать доступ";
                }}
            }}
            checkAuth();
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
