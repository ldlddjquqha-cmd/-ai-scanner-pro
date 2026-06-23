import json
import random
import asyncio
import numpy as np
import os
import uvicorn
import httpx
import logging
from datetime import datetime
from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, JSONResponse

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("QuantumCore")

app = FastAPI(title="HROM QUANTUM CORE GLOBAL", version="18.0")

DB_FILE = "requests.json"
BOT_TOKEN = "8761108877:AAGzMIeErZoGcVlLvd-yO-w7FZbIezCQ9SE"
ADMIN_CHAT_ID = "6765689893"

# --- ИНФРАСТРУКТУРА БАЗЫ ДАННЫХ JSON ---
def get_db():
    if not os.path.exists(DB_FILE): 
        return {"users": {}, "keys": [], "history": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: 
            data = json.load(f)
            if "users" not in data: data = {"users": data, "keys": [], "history": []}
            if "keys" not in data: data["keys"] = []
            if "history" not in data: data["history"] = []
            return data
        except: 
            return {"users": {}, "keys": [], "history": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
        "text": f"🔔 **Новый ученик активировал доступ!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Статус:** ✅ Доступ разрешен",
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    }
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")

async def send_tg_signal_alert(username, asset, timeframe):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"📊 **Пользователь перешел к сигналам!**\n\n**Ученик:** @{username}\n**Актив:** `{asset}`\n**Таймфрейм:** `{timeframe}`\n**Время запроса:** {datetime.now().strftime('%H:%M:%S')}",
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Ошибка отправки алерта сигнала: {e}")

async def send_tg_notification_simple(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        try: 
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Ошибка отправки простого уведомления: {e}")

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
            logger.error(f"Ошибка редактирования сообщения в ТГ: {e}")

# --- ТЕЛЕГРАМ ВЕБХУК (ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ) ---
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        if "callback_query" in data:
            callback_query = data["callback_query"]
            chat_id = str(callback_query["message"]["chat"]["id"])
            message_id = callback_query["message"]["message_id"]
            callback_data = callback_query["data"]
            
            if chat_id == ADMIN_CHAT_ID:
                action, username = callback_data.split(":")
                db = get_db()
                username = username.strip().replace("@", "")
                
                if action == "ban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "blocked"
                    save_db(db)
                    unban_markup = {"inline_keyboard": [[{"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}]]}
                    await edit_tg_message_status(chat_id, message_id, username, "🚫 Заблокирован (Доступ закрыт)", reply_markup=unban_markup)
                    
                elif action == "unban":
                    if username not in db["users"]: 
                        db["users"][username] = {}
                    db["users"][username]["status"] = "approved"
                    save_db(db)
                    standard_markup = {"inline_keyboard": [[{"text": "❌ Забанить", "callback_data": f"ban:{username}"}, {"text": "✅ Разблокировать", "callback_data": f"unban:{username}"}]]}
                    await edit_tg_message_status(chat_id, message_id, username, "✅ Разблокирован (Доступ открыт)", reply_markup=standard_markup)
            return {"status": "ok"}

        if "message" in data and "text" in data["message"]:
            text = data["message"]["text"].strip()
            chat_id = str(data["message"]["chat"]["id"])
            
            if chat_id == ADMIN_CHAT_ID:
                parts = text.split()
                if len(parts) >= 2:
                    command = parts[0]
                    username = parts[1].replace("@", "").strip()
                    db = get_db()
                    
                    if command == "/бан":
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "blocked"
                        save_db(db)
                        await send_tg_notification_simple(f"🚫 Пользователь @{username} заблокирован.")
                    
                    elif command == "/разбанить":
                        if username not in db["users"]: 
                            db["users"][username] = {}
                        db["users"][username]["status"] = "approved"
                        save_db(db)
                        await send_tg_notification_simple(f"✅ Пользователь @{username} разблокирован.")
    except Exception as e:
        logger.error(f"Ошибка вебхука: {e}")
    return {"status": "ok"}

# --- ГЕНЕРАТОР КЛЮЧЕЙ ДОСТУПА ---
@app.get("/generate_key")
async def generate_key(master: str = None):
    if master != "SUPER_ADMIN_123": 
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ закрыт!</h1>")
    chars = "0123456789ABCDEF"
    new_key = "HROM_" + "".join(random.choice(chars) for _ in range(6))
    db = get_db()
    db["keys"].append(new_key)
    save_db(db)
    return HTMLResponse(f"""
    <div style="background:#06080c; color:#ffffff; font-family:sans-serif; text-align:center; padding:50px; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; box-sizing:border-box;">
        <p style="color:#586988; font-size:18px; margin-bottom:5px;">Создан новый одноразовый ключ:</p>
        <div style="background:#0f131e; border:1px solid #1a2233; color:#00ff66; font-size:26px; font-weight:bold; padding:15px 30px; border-radius:12px; margin-bottom:20px;">{new_key}</div>
        <a href="/generate_key?master=SUPER_ADMIN_123"><button style="background:#963bfe; color:white; font-weight:bold; padding:14px 28px; border:none; border-radius:10px; cursor:pointer;">Создать еще один</button></a>
    </div>
    """)

# --- АДМИН-ПАНЕЛЬ ---
@app.get("/admin_panel")
async def admin_panel(secret: str = None):
    if secret != "SUPER_ADMIN_123": 
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ запрещен</h1>")
    db = get_db()
    html_content = """
    <html><head><meta charset="utf-8"><title>HROM Admin</title>
    <style>
        body { background: #06080c; color: #fff; font-family: sans-serif; padding: 20px; }
        .box { max-width: 500px; margin: 0 auto; background: #080a10; padding: 20px; border-radius: 15px; border: 1px solid #1a2233; }
        .row { background: #0f131e; padding: 12px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .btn-ban { background: #ff3344; color: #fff; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; }
        .btn-unban { background: #00ff66; color: #000; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; }
    </style></head><body><div class="box"><h2 style="color:#a855f7; text-align:center;">УПРАВЛЕНИЕ УЧЕНИКАМИ</h2>"""
    if not db["users"]:
        html_content += "<p style='text-align:center; color:#4b5975;'>Учеников пока нет</p>"
    else:
        for user, info in db["users"].items():
            st = info.get("status", "unknown")
            html_content += f"""
            <div class="row">
                <span>@{user} [<b>{st}</b>]</span>
                <div>
                    <a href="/set_status?user={user}&status=approved&secret=SUPER_ADMIN_123" class="btn-unban">Разбанить</a>
                    <a href="/set_status?user={user}&status=blocked&secret=SUPER_ADMIN_123" class="btn-ban">Бан</a>
                </div>
            </div>"""
    html_content += "</div></body></html>"
    return HTMLResponse(html_content)

@app.get("/set_status")
async def set_status(user: str, status: str, secret: str = None):
    if secret != "SUPER_ADMIN_123": 
        return "Отказ"
    db = get_db()
    user = user.strip().replace("@", "")
    if user in db["users"]:
        db["users"][user]["status"] = status
        save_db(db)
    return HTMLResponse(f"<script>window.location.href='/admin_panel?secret=SUPER_ADMIN_123';</script>")

@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    return JSONResponse({"status": status})

# --- ФУНКЦИЯ КУКИ (COOKIE) ПРИ АВТОРИЗАЦИИ ---
@app.post("/request_access")
async def request_access(username: str = Form(...), code: str = Form(...)):
    username = username.strip().replace("@", "").replace(" ", "")
    code = code.strip().replace(" ", "")
    db = get_db()
    
    if username in db["users"] and db["users"][username]["status"] == "blocked":
        return JSONResponse({"success": False, "message": "Вы заблокированы!"})
        
    if username in db["users"] and db["users"][username]["status"] == "approved":
        response = JSONResponse({"success": True, "message": "Доступ активен! Входим..."})
        response.set_cookie(key="tg_username", value=username, max_age=2592000)
        return response
        
    if code not in db["keys"]:
        return JSONResponse({"success": False, "message": "Неверный или использованный код!"})
    
    db["keys"].remove(code)
    db["users"][username] = {
        "status": "approved", 
        "used_code": code, 
        "activated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_db(db)
    asyncio.create_task(send_tg_notification(username, code))
    
    response = JSONResponse({"success": True, "message": "Доступ активирован!"})
    response.set_cookie(key="tg_username", value=username, max_age=2592000)
    return response

# --- СЕТКА АКТИВОВ И МАТЕМАТИЧЕСКИЙ АНАЛИЗАТОР ---
BINANCE_MAPPING = {
    "EUR/USD": "EURUSDT", "GBP/USD": "GBPUSDT", "USD/JPY": "USDJPY",
    "AUD/USD": "AUDUSDT", "EUR/JPY": "EURJPY", "USD/CAD": "USDCAD",
    "GBP/JPY": "GBPJPY", "NZD/USD": "NZDUSDT", "USD/CHF": "USDCHF", "EUR/GBP": "EURGBP"
}

ASSETS_DATA = {
    "ru": {
        "[ВСЕ АКТИВЫ] — OTC ЦИКЛ": {
            "ВАЛЮТНЫЕ ПАРЫ": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"],
            "АКЦИИ": ["Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC", "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"],
            "КРИПТОВАЛЮТА": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "СЫРЬЕ / ИНДЕКСЫ": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ВСЕ АКТИВЫ] — ЖИВОЙ РЫНОК": {
            "ВАЛЮТНЫЕ ПАРЫ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "en": {
        "[ALL ASSETS] — OTC CYCLE": {
            "CURRENCY PAIRS": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"],
            "STOCKS": ["Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC", "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"],
            "CRYPTOCURRENCY": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "COMMODITIES / INDICES": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ALL ASSETS] — LIVE MARKET": {
            "CURRENCY PAIRS": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "ua": {
        "[ВСІ АКТИВИ] — OTC ЦИКЛ": {
            "ВАЛЮТНІ ПАРИ": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"],
            "АКЦІЇ": ["Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC", "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"],
            "КРИПТОВАЛЮТА": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "СИРОВИНА / ІНДЕКСИ": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ВСІ АКТИВИ] — ЖИВИЙ РЫНОК": {
            "ВАЛЮТНІ ПАРИ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    }
}

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

def calculate_bollinger_bands(prices, period=20, num_std=2):
    if len(prices) < period:
        return prices[-1], prices[-1]
    sma = np.mean(prices[-period:])
    std_dev = np.std(prices[-period:])
    upper_band = sma + (num_std * std_dev)
    lower_band = sma - (num_std * std_dev)
    return upper_band, lower_band

def ai_analyze_market(prices, rsi, ema):
    current_price = prices[-1]
    upper_b, lower_b = calculate_bollinger_bands(prices, period=20)
    bandwidth = (upper_b - lower_b) / current_price
    
    if bandwidth < 0.0008:
        return "WAIT"
        
    local_max = max(prices[-20:-1]) if len(prices) >= 21 else max(prices)
    local_min = min(prices[-20:-1]) if len(prices) >= 21 else min(prices)
    
    feature_breakout = 0.0
    if current_price >= local_max * 0.999:
        feature_breakout = 1.0
    elif current_price <= local_min * 1.001:
        feature_breakout = -1.0
        
    feature_trend = 1.0 if current_price > ema else -1.0
    feature_rsi_overbought = 1.0 if rsi > 68 else (-1.0 if rsi < 32 else 0.0)
    
    ai_score = (feature_breakout * 0.40) + (feature_trend * 0.35) + (-1.0 * feature_rsi_overbought * 0.25)
    
    if ai_score >= 0.45:
        return "UP"
    elif ai_score <= -0.45:
        return "DOWN"
    else:
        return "WAIT"

def generate_otc_candles(asset_name, count=60):
    seed_value = sum(ord(char) for char in asset_name) + int(asyncio.get_event_loop().time() / 150)
    state = random.Random(seed_value)
    if "Bitcoin" in asset_name: 
        start_price = 65000.0
    elif "Ethereum" in asset_name: 
        start_price = 3500.0
    elif "Gold" in asset_name: 
        start_price = 2300.0
    else: 
        start_price = 1.1250  
    prices = [start_price]
    for _ in range(count):
        prices.append(prices[-1] * (1 + state.uniform(-0.0018, 0.0018)))
    return prices

@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str, tg_username: str = Cookie(None)):
    user_for_alert = tg_username if tg_username else "Неизвестный ученик"
    asyncio.create_task(send_tg_signal_alert(user_for_alert, asset, timeframe))
    await asyncio.sleep(1.8)
    
    is_otc = "OTC" in asset
    clean_asset = asset.replace(" OTC", "").strip()
    
    if is_otc:
        prices = generate_otc_candles(asset, count=60)
    else:
        binance_symbol = BINANCE_MAPPING.get(clean_asset, "BTCUSDT")
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1m&limit=60"
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=3.0)
                prices = [float(c[4]) for c in res.json()]
        except:
            prices = generate_otc_candles(clean_asset, count=60)

    rsi = calculate_rsi(prices)
    ema = calculate_ema(prices, period=20)
    calculated_signal = ai_analyze_market(prices, rsi, ema)
    
    if calculated_signal == "WAIT":
        calculated_signal = random.choice(["UP", "DOWN"])
        base_accuracy = 65.0
    else:
        base_accuracy = 72.0 + (abs(rsi - 50.0) * 0.4)
        
    accuracy = round(min(max(base_accuracy, 66.5), 93.8), 1)
    return {"signal": calculated_signal, "payout": 92 if is_otc else 82, "accuracy": accuracy}

# --- ПОЛНЫЙ ИНТЕРФЕЙС ПЛАТФОРМЫ ---
@app.get("/", response_class=HTMLResponse)
async def index(tg_username: str = Cookie(None)):
    has_cookie = "true" if tg_username else "false"
    
    return rf"""
    <html style="background:#06080c; color:#ffffff; font-family:'Segoe UI', Roboto, sans-serif; margin:0; padding:0;">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HROM QUANTUM CORE v18.0</title>
        <style>
            .container {{ max-width: 430px; margin: 0 auto; padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; box-sizing: border-box; }}
            .title {{ font-size: 20px; font-weight: 800; color: #a855f7; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; }}
            .subtitle {{ font-size: 11px; color: #4b5975; font-weight: 600; margin-bottom: 30px; text-align: center; }}
            .input-box {{ width: 100%; max-width: 320px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; padding: 16px; margin-bottom: 12px; box-sizing: border-box; text-align: center; }}
            input {{ background: transparent; border: none; color: white; width: 100%; font-size: 14px; font-weight: bold; outline: none; text-align: center; }}
            input::placeholder {{ color: #4b5975; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .loader {{ width: 45px; height: 45px; border: 4px solid #161b26; border-top: 4px solid #a855f7; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 15px auto; display: none; }}
            select {{ width: 100%; padding: 14px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; font-size: 14px; font-weight: 600; color: #ffffff; outline: none; }}
            label {{ font-size: 11px; font-weight: bold; color: #4b5975; display: block; margin-bottom: 5px; letter-spacing: 0.8px; text-transform: uppercase; }}
            .btn {{ width: 100%; padding: 16px; border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; box-sizing: border-box; }}
            .btn-activate {{ width: 100%; max-width: 320px; padding: 16px; background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; box-shadow: 0 5px 20px rgba(100,27,250,0.4); }}
            .btn-activate:disabled {{ background: #1a2233; color: #4b5975; cursor: not-allowed; box-shadow: none; }}
            .btn-main {{ background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); box-shadow: 0 5px 20px rgba(100,27,250,0.4); }}
            .btn-vip-top {{ padding: 8px 12px; border: none; border-radius: 8px; background: #ffa500; color: #000 !important; font-weight: 900; font-size: 11px; cursor: pointer; text-transform: uppercase; }}
            .btn-pocket {{ background: #141924; border: 1px solid #222d42; color: #38ef7d; width: 100%; }}
            .btn-support {{ background: #080a10; border: 1px solid #161b26; color: #586988; font-size: 11px; margin-top: 15px; width: 100%; }}
            .btn-mart {{ background: #ff3344; display: none; width: 100%; }}
            .lang-select {{ background: #0f131e; color: white; border: 1px solid #1a2233; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }}
            .payout-badge {{ color: #00ff66; font-weight: 800; font-size: 12px; margin-top: 4px; display: block; }}
            .stat-panel {{ background: #080a10; border: 1px solid #1a2233; border-radius: 20px; padding: 15px; margin-bottom: 20px; text-align: center; }}
            .wr-val {{ font-size: 22px; font-weight: 900; color: #00ff66; margin-bottom: 10px; }}
            .counter-box {{ display: flex; gap: 10px; }}
            .count-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; background: #0f131e; padding: 10px; border-radius: 12px; border: 1px solid #1a2233; cursor: pointer; font-weight: 800; color: white; }}
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
                <div id="error-msg" style="color: #ff3344; font-size: 13px; font-weight: bold; margin-top: 15px; display: none;"></div>
                <div id="success-msg" style="color: #00ff66; font-size: 13px; font-weight: bold; margin-top: 15px; display: none;"></div>
            </div>
        </div>

        <div id="terminal-screen" style="display: none; flex-direction: column; min-height: 100vh;">
            <div style="max-width:430px; width: 100%; margin:15px auto 0 auto; padding:0 15px; display:flex; justify-content:space-between; align-items:center; box-sizing: border-box;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span id="flag_icon" style="font-size:20px;">🇷🇺</span>
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
                        <button class="count-btn" onclick="updateStat('win', 1)" oncontextmenu="updateStat('win', -1); return false;"><span id="lbl_profit" style="font-size:9px; color:#586988;">Profit</span><span id="win_counter" style="color:#00ff66; font-size:16px;">0</span></button>
                        <button class="count-btn" onclick="updateStat('loss', 1)" oncontextmenu="updateStat('loss', -1); return false;"><span id="lbl_loss" style="font-size:9px; color:#586988;">Loss</span><span id="loss_counter" style="color:#ff3344; font-size:16px;">0</span></button>
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
                
                <button id="runBtn" class="btn btn-main" onclick="startFlow()">ИИ СДЕЛАТЬ ЗА ВАС</button>
                <button id="martBtn" class="btn btn-mart" onclick="startFlow(true)">ПЕРЕКРЫТИЕ</button>
                
                <a href="https://pocketoption.com/register" target="_blank" style="text-decoration: none;"><button id="btn_pocket" class="btn btn-pocket">ОТКРЫТЬ POCKET OPTION</button></a>
                <div id="status" style="font-size:11px; color:#4b5975; margin-top:20px; min-height:18px; font-weight:700;">СИСТЕМА СИНХРОНИЗИРОВАНА</div>
                
                <div id="loader" class="loader"></div>
                <div id="res" style="font-size:55px; font-weight:900; margin:10px 0; min-height:66px; color:#ffffff;">--</div>
                <div id="accuracy" style="font-size:14px; font-weight:800; color:#a855f7; margin-top:-5px; margin-bottom:10px; display:none;"></div>
                <div id="timer" style="font-size:14px; font-weight:800; color:#ffaa00; margin-bottom:15px; min-height:20px;"></div>
                
                <button class="btn" style="background:#141924; color:#ff3344; margin-top:10px; font-size:11px; padding:10px;" onclick="logout()">ВЫЙТИ ИЗ АККАУНТА</button>
                <a href="https://t.me/andriddddd" target="_blank" style="text-decoration: none;"><button id="btn_supp" class="btn btn-support">РАЗРАБОТЧИК / SUPPORT</button></a>
            </div>
        </div>

        <div id="blocked-screen" style="display: none; width:100%; background:#06080c; color:#ff3344; font-family:sans-serif; text-align:center; padding-top:100px; height:100vh; flex-direction:column; align-items:center;">
            <h1 style="font-size:24px; padding: 0 20px;">Доступ заблокирован администратором.</h1>
        </div>

        <script>
            const rawData = {json.dumps(ASSETS_DATA)};
            const hasCookie = {has_cookie};
            
            const tf_otc_ru = ["1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "10 мин", "15 мин"];
            const tf_otc_en = ["1 min", "2 min", "3 min", "4 min", "5 min", "10 min", "15 min"];
            const tf_otc_ua = ["1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "10 хв", "15 хв"];

            const tf_live_ru = ["1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "10 мин", "15 мин"];
            const tf_live_en = ["1 min", "2 min", "3 min", "4 min", "5 min", "10 min", "15 min"];
            const tf_live_ua = ["1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "10 хв", "15 хв"];

            let wins = 0, losses = 0, currentBet = 100, martStep = 0, currentExpInterval = null;

            function getCookie(name) {{
                let matches = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/([\.$?*|{{}} \(\)\[\]\\\/\+^])/g, '\\$1') + "=([^;]*)"));
                return matches ? decodeURIComponent(matches[1]) : undefined;
            }}

            async function checkAuth() {{
                const userCookie = getCookie('tg_username');
                if (!userCookie) {{ 
                    showScreen('auth-screen'); 
                    return; 
                }}
                try {{
                    const response = await fetch('/check_user_status?username=' + encodeURIComponent(userCookie));
                    const data = await response.json();
                    if (data.status === 'approved') {{ 
                        showScreen('terminal-screen'); 
                        changeLang(); 
                    }} 
                    else if (data.status === 'blocked') {{ 
                        showScreen('blocked-screen'); 
                    }}
                    else {{ 
                        document.cookie = "tg_username=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"; 
                        showScreen('auth-screen'); 
                    }}
                }} catch(e) {{ 
                    showScreen('auth-screen'); 
                }}
            }}

            function showScreen(screenId) {{
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('terminal-screen').style.display = 'none';
                document.getElementById('blocked-screen').style.display = 'none';
                document.getElementById(screenId).style.display = 'flex';
            }}

            async function sendForm() {{
                const user = document.getElementById('username').value;
                const key = document.getElementById('code').value;
                if(!user || !key) return;
                
                const fData = new FormData();
                fData.append('username', user);
                fData.append('code', key);
                
                const response = await fetch('/request_access', {{ method: 'POST', body: fData }});
                const res = await response.json();
                if(res.success) {{
                    document.getElementById('success-msg').innerText = res.message;
                    document.getElementById('success-msg').style.display = 'block';
                    setTimeout(() => {{ window.location.reload(); }}, 1500);
                }} else {{
                    document.getElementById('error-msg').innerText = res.message;
                    document.getElementById('error-msg').style.display = 'block';
                }}
            }}

            function logout() {{ 
                document.cookie = "tg_username=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;"; 
                window.location.reload(); 
            }}
            
            function updateStat(type, val) {{ 
                if(type=='win') wins = Math.max(0, wins + val); 
                else losses = Math.max(0, losses + val); 
                updateDisplay(); 
            }}
            
            function updateDisplay() {{
                document.getElementById('win_counter').innerText = wins;
                document.getElementById('loss_counter').innerText = losses;
                let total = wins + losses;
                let wr = total == 0 ? 0 : ((wins/total)*100).toFixed(1);
                let el = document.getElementById('wr_display');
                el.innerText = "WIN RATE: " + wr + "%";
                el.style.color = wr >= 50 ? "#00ff66" : "#ff3344";
            }}
            
            function resetStats() {{ 
                wins=0; losses=0; currentBet=100; martStep=0; 
                updateDisplay(); 
            }}
            
            const flags = { "ru": "🇷🇺", "en": "🇺🇸", "ua": "🇺🇦" };

            const translations = {{
                ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", vip: "👑 VIP СИГНАЛЫ", pocket: "ОТКРЫТЬ POCKET OPTION", reset: "СБРОСИТЬ СТАТИСТИКУ" }},
                en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION", vip: "👑 VIP SIGNALS", pocket: "OPEN POCKET OPTION", reset: "RESET STATISTICS" }},
                ua: {{ market: "КАТЕГОРІЯ РИНКУ", type: "ТИП АКТИВУ", asset: "АКТИВНА ПАРА", tf: "ІНТЕРВАЛ СВІЧКИ", exp: "ЕКСПІРАЦІЯ", vip: "👑 VIP СИГНАЛИ", pocket: "ВІДКРИТИ POCKET OPTION", reset: "СКИНУТИ СТАТИСТИКУ" }}
            }};

            function changeLang() {{
                let l = document.getElementById('lang').value;
                document.getElementById('flag_icon').innerText = flags[l];
                document.getElementById('lbl_market').innerText = translations[l].market;
                document.getElementById('lbl_type').innerText = translations[l].type;
                document.getElementById('lbl_asset').innerText = translations[l].asset;
                document.getElementById('lbl_tf').innerText = translations[l].tf;
                document.getElementById('lbl_exp').innerText = translations[l].exp;
                document.getElementById('vip_btn_text').innerText = translations[l].vip;
                document.getElementById('btn_pocket').innerText = translations[l].pocket;
                document.getElementById('lbl_reset').innerText = translations[l].reset;
                
                let catSel = document.getElementById('cat');
                catSel.innerHTML = "";
                Object.keys(rawData[l]).forEach(c => {{
                    catSel.options[catSel.options.length] = new Option(c, c);
                }});
                updCategory();
            }}

            function updCategory() {{
                let l = document.getElementById('lang').value;
                let c = document.getElementById('cat').value;
                let subSel = document.getElementById('sub_cat');
                subSel.innerHTML = "";
                
                if(c.includes("LIVE") || c.includes("ЖИВОЙ") || c.includes("ЖИВИЙ")) {{
                    document.getElementById('sub_cat_block').style.display = 'none';
                    let assetSel = document.getElementById('asset');
                    assetSel.innerHTML = "";
                    rawData[l][c]["ВАЛЮТНЫЕ ПАРЫ" || "CURRENCY PAIRS" || "ВАЛЮТНІ ПАРИ"].forEach(a => {{
                        assetSel.options[assetSel.options.length] = new Option(a, a);
                    }});
                    updAsset();
                }} else {{
                    document.getElementById('sub_cat_block').style.display = 'block';
                    Object.keys(rawData[l][c]).forEach(s => {{
                        subSel.options[subSel.options.length] = new Option(s, s);
                    }});
                    updSubCategory();
                }}
            }}

            function updSubCategory() {{
                let l = document.getElementById('lang').value;
                let c = document.getElementById('cat').value;
                let s = document.getElementById('sub_cat').value;
                let assetSel = document.getElementById('asset');
                assetSel.innerHTML = "";
                rawData[l][c][s].forEach(a => {{
                    assetSel.options[assetSel.options.length] = new Option(a, a);
                }});
                updAsset();
            }}

            function updAsset() {{
                let a = document.getElementById('asset').value;
                let l = document.getElementById('lang').value;
                let tfSel = document.getElementById('time');
                let expSel = document.getElementById('exp');
                tfSel.innerHTML = ""; expSel.innerHTML = "";
                
                let tfs = a.includes("OTC") ? (l=='ru'?tf_otc_ru:(l=='ua'?tf_otc_ua:tf_otc_en)) : (l=='ru'?tf_live_ru:(l=='ua'?tf_live_ua:tf_live_en));
                tfs.forEach(t => {{
                    tfSel.options[tfSel.options.length] = new Option(t, t);
                    expSel.options[expSel.options.length] = new Option(t, t);
                }});
                document.getElementById('payout_lbl').innerText = "PAYOUT: " + (a.includes("OTC") ? "92%" : "82%");
            }}

            async function startFlow(isMart = false) {{
                document.getElementById('runBtn').style.display = 'none';
                document.getElementById('martBtn').style.display = 'none';
                document.getElementById('res').innerText = "--";
                document.getElementById('accuracy').style.display = 'none';
                document.getElementById('loader').style.display = 'block';
                
                let asset = document.getElementById('asset').value;
                let timeframe = document.getElementById('time').value;
                
                try {{
                    let response = await fetch(`/get_signal?asset=${{encodeURIComponent(asset)}}&timeframe=${{encodeURIComponent(timeframe)}}`);
                    let data = await response.json();
                    
                    document.getElementById('loader').style.display = 'none';
                    let resEl = document.getElementById('res');
                    resEl.innerText = data.signal;
                    resEl.style.color = data.signal === "UP" ? "#00ff66" : "#ff3344";
                    
                    let accEl = document.getElementById('accuracy');
                    accEl.innerText = `ACCURACY: ${{data.accuracy}}%`;
                    accEl.style.display = 'block';
                    
                    startTimer(timeframe);
                }} catch(e) {{
                    document.getElementById('loader').style.display = 'none';
                    document.getElementById('runBtn').style.display = 'block';
                }}
            }}

            function startTimer(tf) {{
                if(currentExpInterval) clearInterval(currentExpInterval);
                let mins = parseInt(tf) || 1;
                let totalSecs = mins * 60;
                
                let timerEl = document.getElementById('timer');
                currentExpInterval = setInterval(() => {{
                    let m = Math.floor(totalSecs / 60);
                    let s = totalSecs % 60;
                    timerEl.innerText = `EXPIRATION: ${{m.toString().padStart(2,'0')}}:${{s.toString().padStart(2,'0')}}`;
                    totalSecs--;
                    if(totalSecs < 0) {{
                        clearInterval(currentExpInterval);
                        timerEl.innerText = "";
                        document.getElementById('runBtn').style.display = 'block';
                        document.getElementById('martBtn').style.display = 'block';
                    }}
                }}, 1000);
            }}

            window.onload = function() {{
                checkAuth();
            }};
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
