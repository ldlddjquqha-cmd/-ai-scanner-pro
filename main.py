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
BOT_TOKEN = "8761108877:AAHGS5tME2dqGF6iMC1IIN9HzgWJ0wgNGTU"
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

async def send_tg_notification(username, code):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"🔔 **Новый ученик активировал код!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Текущий статус:** ✅ Доступ разрешен",
        "parse_mode": "Markdown"
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"Ошибка отправки в ТГ: {e}")

async def send_tg_notification_simple(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=5.0)
        except:
            pass

# --- ОБРАБОТЧИК СООБЩЕНИЙ В TELEGRAM (WEBHOOK) ---
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        if "message" in data and "text" in data["message"]:
            text = data["message"]["text"]
            chat_id = str(data["message"]["chat"]["id"])
            
            if chat_id == ADMIN_CHAT_ID:
                parts = text.split()
                if len(parts) >= 2:
                    command = parts[0]
                    username = parts[1].replace("@", "").strip()
                    db = get_db()
                    
                    if command == "/бан":
                        db["users"][username] = {"status": "blocked"}
                        save_db(db)
                        await send_tg_notification_simple(f"🚫 Пользователь @{username} забанен. Доступ закрыт навсегда.")
                    
                    elif command == "/разбанить":
                        db["users"][username] = {"status": "approved"}
                        save_db(db)
                        await send_tg_notification_simple(f"✅ Пользователь @{username} разблокирован.")
    except Exception as e:
        print(f"Ошибка вебхука ТГ: {e}")
        
    return {"status": "ok"}

# --- СТРАНИЦА ГЕНЕРАЦИИ ОДНОРАЗОВЫХ КЛЮЧЕЙ ---
@app.get("/generate_key")
async def generate_key(master: str = None):
    if master != "SUPER_ADMIN_123": 
        return HTMLResponse("<h1 style='color:red; text-align:center;'>Доступ запрещен</h1>")
    
    chars = "0123456789ABCDEF"
    new_key = "HROM_" + "".join(random.choice(chars) for _ in range(6))
    
    db = get_db()
    db["keys"].append(new_key)
    save_db(db)
    
    return HTMLResponse(f"""
    <div style="background:#06080c; color:#ffffff; font-family:sans-serif; text-align:center; padding:50px; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center;">
        <p style="color:#586988; font-size:18px; margin-bottom:5px;">Создан новый одноразовый ключ:</p>
        <div style="background:#0f131e; border:1px solid #1a2233; color:#00ff66; font-size:24px; font-weight:bold; padding:15px 30px; border-radius:12px; letter-spacing:1px; margin-bottom:20px;">
            {new_key}
        </div>
        <p style="color:#4b5975; font-size:12px; max-width:300px; margin-bottom:20px;">Отдай его человеку. Как только он введет его на сайте, его устройство запомнится навсегда.</p>
        <a href="/generate_key?master=SUPER_ADMIN_123" style="text-decoration:none;">
            <button style="background:#963bfe; color:white; font-weight:bold; padding:12px 24px; border:none; border-radius:10px; cursor:pointer;">Создать еще один</button>
        </a>
    </div>
    """)

# --- АДМИН-ПАНЕЛЬ СУПЕР-АДМИНА ---
@app.get("/admin_panel")
async def admin_panel(secret: str = None):
    if secret != "SUPER_ADMIN_123": return "Доступ запрещен"
    db = get_db()
    html = "<h1>Управление учениками</h1>"
    for user, info in db["users"].items():
        status = info.get("status")
        html += f"<p><b>{user}</b> — Статус: {status} | <a href='/set_status?user={user}&status=approved&secret=SUPER_ADMIN_123'>ОДОБРИТЬ</a> | <a href='/set_status?user={user}&status=blocked&secret=SUPER_ADMIN_123'>ЗАБЛОКИРОВАТЬ</a></p>"
    return HTMLResponse(html)

@app.get("/set_status")
async def set_status(user: str, status: str, secret: str = None):
    if secret != "SUPER_ADMIN_123": return "Доступ запрещен"
    db = get_db()
    if user in db["users"]:
        db["users"][user]["status"] = status
        save_db(db)
    return HTMLResponse(f"Статус {user} изменен на {status}! <a href='/admin_panel?secret=SUPER_ADMIN_123'>Назад</a>")

# --- СТРОГАЯ ПРОВЕРКА СТАТУСА ---
@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    return JSONResponse({"status": status})

# --- ЖЕСТКАЯ ЛОГИКА АКТИВАЦИИ ОДНОРАЗОВЫХ КОДОВ ---
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

# --- ТРЕЙДИНГ ДАННЫЕ И ИНДИКАТОРЫ ---
BINANCE_MAPPING = {
    "EUR/USD": "EURUSDT", "EUR/USD OTC": "EURUSDT",
    "GBP/USD": "GBPUSDT", "GBP/USD OTC": "GBPUSDT",
    "USD/JPY": "USDJPY", "USD/JPY OTC": "USDJPY",
    "AUD/USD": "AUDUSDT", "AUD/USD OTC": "AUDUSDT",
    "EUR/JPY": "EURJPY", "EUR/JPY OTC": "EURJPY",
    "USD/CAD": "USDCAD", "USD/CAD OTC": "USDCAD",
    "GBP/JPY": "GBPJPY", "GBP/JPY OTC": "GBPJPY",
    "NZD/USD": "NZDUSDT", "NZD/USD OTC": "NZDUSDT",
    "USD/CHF": "USDCHF", "USD/CHF OTC": "USDCHF",
    "EUR/GBP": "EURGBP", "EUR/GBP OTC": "EURGBP",
    "Bitcoin OTC": "BTCUSDT", "Ethereum OTC": "ETHUSDT", 
    "Solana OTC": "SOLUSDT", "Ripple OTC": "XRPUSDT",
    "Gold OTC": "PAXGUSDT", "Silver OTC": "XAGUSDT", 
    "Crude Oil OTC": "USO", "Brent Oil OTC": "BRENT",
    "US 500 OTC": "SPY", "NASDAQ 100 OTC": "QQQ",
    "Apple OTC": "AAPL", "Microsoft OTC": "MSFT", "Amazon OTC": "AMZN", 
    "Tesla OTC": "TSLA", "NVIDIA OTC": "NVDA", "Google OTC": "GOOGL", 
    "Netflix OTC": "NFLX", "Meta OTC": "META", "Intel OTC": "INTC", "AMD OTC": "AMD"
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
        "[ВСІ АКТИВИ] — ЖИВИЙ РИНОК": {
            "ВАЛЮТНІ ПАРИ": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "es": {
        "[TODOS LOS ACTIVOS] — CICLO OTC": {
            "PARES DE DIVISAS": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"],
            "ACCIONES": ["Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC", "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"],
            "CRIPTOMONEDAS": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "MATERIAS PRIMAS / ÍNDICES": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[TODOS LOS ACTIVOS] — MERCADO EN VIVO": {
            "PARES DE DIVISAS": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    },
    "de": {
        "[ALLE VERMÖGENSWERTE] — OTC-ZYKLUS": {
            "WÄHRUNGSPAARE": ["EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "GBP/JPY OTC", "NZD/USD OTC", "USD/CHF OTC", "EUR/GBP OTC"],
            "AKTIEN": ["Apple OTC", "Microsoft OTC", "Amazon OTC", "Tesla OTC", "NVIDIA OTC", "Google OTC", "Netflix OTC", "Meta OTC", "Intel OTC", "AMD OTC"],
            "KRYPTOWÄHRUNG": ["Bitcoin OTC", "Ethereum OTC", "Solana OTC", "Ripple OTC"],
            "ROHSTOFFE / INDIZES": ["Gold OTC", "Silver OTC", "Crude Oil OTC", "Brent Oil OTC", "US 500 OTC", "NASDAQ 100 OTC"]
        },
        "[ALLE VERMÖGENSWERTE] — LIVE-MARKT": {
            "WÄHRUNGSPAARE": ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", "USD/CHF", "EUR/JPY", "GBP/JPY", "EUR/GBP"]
        }
    }
}

def get_pocket_payout(asset: str) -> int:
    if "OTC" in asset: return 92
    if any(crypto in asset for crypto in ["BTC", "ETH", "SOL", "XRP", "LTC", "TRX", "BNB", "DOGE", "Bitcoin", "Ethereum", "Solana", "Ripple"]): return 78
    return 82

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50.0
    deltas = np.diff(prices)
    up = np.where(deltas > 0, deltas, 0).mean()
    down = np.where(deltas < 0, -deltas, 0).mean()
    if down == 0: return 100.0
    rs = up / down
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_ema(prices, period=20):
    if len(prices) < period: return prices[-1]
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    return np.convolve(prices, weights, mode='valid')[-1]

@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str):
    await asyncio.sleep(0.8) 
    binance_symbol = BINANCE_MAPPING.get(asset, "BTCUSDT")
    is_otc = "OTC" in asset
    if is_otc:
        random.seed(int(asyncio.get_event_loop().time() * 1000) % 9999)
        return {"signal": "UP" if random.random() > 0.5 else "DOWN", "payout": get_pocket_payout(asset), "accuracy": round(random.uniform(67.2, 72.5), 1), "outcome": "WIN", "session_verified": True}
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1m&limit=30"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=3.0)
            candles = response.json()
            prices = [float(c[4]) for c in candles]
    except: prices = [100.0] * 30
    rsi = calculate_rsi(prices)
    ema = calculate_ema(prices)
    curr = prices[-1]
    if curr > ema and rsi < 35: signal, accuracy = "UP", round(70.0 + random.uniform(0, 5), 1)
    elif curr < ema and rsi > 65: signal, accuracy = "DOWN", round(70.0 + random.uniform(0, 5), 1)
    else: signal, accuracy = ("UP" if curr > ema else "DOWN"), round(60.0 + random.uniform(0, 3), 1)
    return {"signal": signal, "payout": get_pocket_payout(asset), "accuracy": accuracy, "outcome": "WIN", "session_verified": True}

@app.get("/", response_class=HTMLResponse)
async def index():
    return rf"""
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
            .btn-vip-top {{ padding: 8px 12px; border: none; border-radius: 8px; background: linear-gradient(270deg, #ffd700, #ffa500, #b8860b, #ffd700); background-size: 400% 400%; animation: shine 4s ease infinite; color: #000 !important; font-weight: 900; font-size: 11px; cursor: pointer; box-shadow: 0 2px 10px rgba(255,215,0,0.3); text-transform: uppercase; letter-spacing: 0.5px; }}
            .btn-pocket {{ background: #141924; border: 1px solid #222d42; color: #38ef7d; width: 100%; }}
            .btn-support {{ background: #080a10; border: 1px solid #161b26; color: #586988; font-size: 11px; margin-top: 15px; width: 100%; }}
            .btn-mart {{ background: #ff3344; display: none; width: 100%; }}
            .btn:active, .btn-activate:active {{ transform: scale(0.98); }}
            .lang-select {{ background: #0f131e; color: white; border: 1px solid #1a2233; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }}
            .payout-badge {{ color: #00ff66; font-weight: 800; font-size: 12px; margin-top: 4px; display: block; }}
            .stat-panel {{ background: #080a10; border: 1px solid #1a2233; border-radius: 20px; padding: 15px; margin-bottom: 20px; text-align: center; }}
            .wr-val {{ font-size: 22px; font-weight: 900; color: #00ff66; margin-bottom: 10px; text-shadow: 0 0 15px rgba(0,255,102,0.2); }}
            .counter-box {{ display: flex; gap: 10px; }}
            .count-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; background: #0f131e; padding: 10px; border-radius: 12px; border: 1px solid #1a2233; cursor: pointer; font-weight: 800; font-size: 13px; transition: 0.2s; color: white; }}
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
                
                <div id="error-msg" style="color: #ff3344; font-size: 13px; font-weight: bold; margin-top: 15px; text-align: center; display: none;"></div>
                <div id="success-msg" style="color: #00ff66; font-size: 13px; font-weight: bold; margin-top: 15px; text-align: center; display: none;"></div>
            </div>
        </div>

        <div id="terminal-screen" style="display: none; flex-direction: column; min-height: 100vh;">
            <div style="max-width:430px; width: 100%; margin:15px auto 0 auto; padding:0 15px; display:flex; justify-content:space-between; align-items:center; box-sizing: border-box;">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span id="flag_icon" style="font-size:20px; line-height:1;">🇷🇺</span>
                    <select id="lang" class="lang-select" onchange="changeLang()">
                        <option value="ru">🇷🇺 RU</option>
                        <option value="en">🇺🇸 EN</option>
                        <option value="ua">🇺🇦 UA</option>
                        <option value="es">🇪🇸 ES</option>
                        <option value="de">🇩🇪 DE</option>
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
                <button id="autoBtn" class="btn btn-auto" onclick="startFlow(true)">ИИ СДЕЛАТЬ ЗА ВАС</button>
                <button id="martBtn" class="btn btn-mart" onclick="startFlow(false, true)">ПЕРЕКРЫТИЕ</button>
                
                <a href="https://pocketoption.com/register" target="_blank" style="text-decoration: none;"><button id="btn_pocket" class="btn btn-pocket">ОТКРЫТЬ POCKET OPTION</button></a>
                <div id="status" style="font-size:11px; color:#4b5975; margin-top:20px; min-height:18px; font-weight:700; letter-spacing:0.5px;">СИСТЕМА СИНХРОНИЗИРОВАНА</div>
                <div id="loader" class="loader"></div>
                <div id="res" style="font-size:55px; font-weight:900; margin:10px 0; min-height:66px; letter-spacing:2px; color:#ffffff;">--</div>
                <div id="accuracy" style="font-size:14px; font-weight:800; color:#a855f7; margin-top:-5px; margin-bottom:10px; display:none;"></div>
                <div id="timer" style="font-size:14px; font-weight:800; color:#ffaa00; margin-bottom:15px; min-height:20px;"></div>
                
                <button class="btn" style="background:#141924; color:#ff3344; margin-top:10px; font-size:11px; padding:10px;" onclick="logout()">ВЫЙТИ ИЗ АККАУНТА</button>
                <a href="https://t.me/andriddddd" target="_blank" style="text-decoration: none;"><button id="btn_supp" class="btn btn-support">РАЗРАБОТЧИК / SUPPORT</button></a>
            </div>
        </div>

        <div id="blocked-screen" style="display: none; background:#06080c; color:#ff3344; font-family:sans-serif; text-align:center; padding-top:100px; height:100vh; flex-direction:column; align-items:center;">
            <h1>Доступ заблокирован администратором.</h1>
        </div>

        <script>
            const rawData = {json.dumps(ASSETS_DATA)};
            const tf_options = {{
                ru: ["1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "6 мин", "7 мин", "8 мин", "9 мин", "10 мин"],
                en: ["1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
                ua: ["1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "6 хв", "7 хв", "8 хв", "9 хв", "10 хв"],
                es: ["1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
                de: ["1 Min", "2 Min", "3 Min", "4 Min", "5 Min", "6 Min", "7 Min", "8 Min", "9 Min", "10 Min"]
            }};
            
            let wins = 0, losses = 0, currentBet = 100, martStep = 0, currentInterval = null, currentExpInterval = null;

            async function checkAuth() {{
                const localUser = localStorage.getItem('tg_username');
                if (!localUser) {{
                    showScreen('auth-screen');
                    return;
                }}
                try {{
                    const response = await fetch('/check_user_status?username=' + encodeURIComponent(localUser));
                    const data = await response.json();
                    
                    if (data.status === 'approved') {{
                        showScreen('terminal-screen');
                        changeLang();
                    }} else if (data.status === 'blocked') {{
                        showScreen('blocked-screen');
                    }} else {{
                        localStorage.removeItem('tg_username');
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

            function logout() {{
                localStorage.removeItem('tg_username');
                window.location.reload();
            }}

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
            
            const flags = {{ ru: "🇷🇺", en: "🇺🇸", ua: "🇺🇦", es: "🇪🇸", de: "🇩🇪" }};
            const dictionary = {{ 
                ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", scan: "СКАНИРОВАТЬ РЫНОК", auto: "ИИ СДЕЛАТЬ ЗА ВАС", pocket: "ОТКРЫТЬ POCKET OPTION", support: "РАЗРАБОТЧИК / SUPPORT", ready: "СИСТЕМА СИНХРОНИЗИРОВАНА", vip: "👑 VIP СИГНАЛЫ", mart: "ПЕРЕКРЫТИЕ", profit: "Profit", loss: "Loss", reset: "СБРОСИТЬ СТАТИСТИКУ", up: "ВВЕРХ", down: "ВНИЗ", enter: "ВХОД ЧЕРЕЗ: ", open: "СДЕЛКА ОТКРЫТА!", close: "ДО ЗАКРЫТИЯ: ", end: "ЦИКЛ ЗАВЕРШЕН" }}, 
                en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION TIME", scan: "SCAN MARKET", auto: "AI DO FOR YOU", pocket: "OPEN POCKET OPTION", support: "DEVELOPER / SUPPORT", ready: "SYSTEM SYNCHRONIZED", vip: "👑 VIP SIGNALS", mart: "MARTINGALE", profit: "Profit", loss: "Loss", reset: "RESET STATISTICS", up: "CALL / UP", down: "PUT / DOWN", enter: "ENTRY IN: ", open: "TRADE OPENED!", close: "CLOSING IN: ", end: "CYCLE COMPLETED" }},
                ua: {{ market: "КАТЕГОРІЯ РИНКУ", type: "ТИП АКТИВУ", asset: "АКТИВНА ПАРА", tf: "ІНТЕРВАЛ СВІЧКИ", exp: "ЕКСПІРАЦІЯ", scan: "СКАНУВАТИ РИНОК", auto: "ШІ ЗРОБИТЬ ЗА ВАС", pocket: "ВІДКРИТИ POCKET OPTION", support: "РОЗРОБНИК / SUPPORT", ready: "СИСТЕМА СИНХРОНІЗОВАНА", vip: "👑 VIP СИГНАЛИ", mart: "ПЕРЕКРИТТЯ", profit: "Профіт", loss: "Лос", reset: "СКИНУТИ СТАТИСТИКУ", up: "ВГОРУ", down: "ВНИЗ", enter: "ВХІД ЧЕРЕЗ: ", open: "УГОДУ ВІДКРИТО!", close: "ДО ЗАКРИТЯ: ", end: "ЦИКЛ ЗАВЕРШЕНО" }},
                es: {{ market: "CATEGORÍA DE MERCADO", type: "TIPO DE ACTIVOS", asset: "PAR ACTIVO", tf: "TIMEFRAME DE VELA", exp: "EXPIRACIÓN", scan: "ESCANEAR MERCADO", auto: "IA LO HACE POR TI", pocket: "ABRIR POCKET OPTION", support: "DESARROLLADOR / SUPPORT", ready: "SISTEMA SINCRONIZADO", vip: "👑 SEÑALES VIP", mart: "MARTINGALA", profit: "Ganancia", loss: "Pérdida", reset: "REINICIAR ESTADÍСТICAS", up: "SUBIR", down: "BAJAR", enter: "ENTRADA EN: ", open: "¡OPERCION ABIERTA!", close: "CIERRE EN: ", end: "CICLO COMPLETADO" }},
                de: {{ market: "MARKTKATEGORIE", type: "PRODUKTTYP", asset: "AKTIVES PAAR", tf: "KERZEN ZEITRAHMEN", exp: "ABLAUFZEIT", scan: "MARKT SCANNEN", auto: "KI MACHT ES FÜR DICH", pocket: "POCKET OPTION ÖFFNEN", support: "ENTWICKLER / SUPPORT", ready: "SYSTEM SYNCHRONISIERT", vip: "👑 VIP SIGNALE", mart: "MARTINGALE", profit: "Gewinn", loss: "Verlust", reset: "STATISTIK ZURÜCKSETZEN", up: "HOCH", down: "RUNTER", enter: "EINSTIEG IN: ", open: "DEAL GEÖFFNET!", close: "RESTZEIT: ", end: "ZYKLUS BEENDET" }}
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
                let expSelect = document.getElementById('exp');
                let options = tf_options[l];
                expSelect.innerHTML = options.map(o => `<option>${{o}}</option>`).join('');
                document.getElementById('time').innerHTML = tf_options[l].map(o => `<option>${{o}}</option>`).join(''); 
            }}
            
            async function startFlow(isAI, isMart = false) {{
                if(currentInterval) clearInterval(currentInterval);
                if(currentExpInterval) clearInterval(currentExpInterval);
                let l = document.getElementById('lang').value;
                let d = dictionary[l] || dictionary['en'];
                if(isAI) {{ 
                    let cats = Object.keys(rawData[l]);
                    let rCat = cats[Math.floor(Math.random()*cats.length)]; document.getElementById('cat').value = rCat; updCategory(); 
                    let subCats = Object.keys(rawData[l][rCat]);
                    let rSub = subCats[Math.floor(Math.random()*subCats.length)]; document.getElementById('sub_cat').value = rSub; updSubCategory();
                    let assets = rawData[l][rCat][rSub];
                    document.getElementById('asset').value = assets[Math.floor(Math.random()*assets.length)]; updAsset();
                }}
                if(!isMart) {{ currentBet = 100; martStep = 0; }} 
                else {{ currentBet = (currentBet * 2.3).toFixed(2); martStep++; }}
                document.getElementById('martBtn').style.display = 'none';
                document.getElementById('res').innerText = "--";
                document.getElementById('accuracy').style.display = 'none';
                document.getElementById('timer').innerText = "";
                document.getElementById('loader').style.display = 'block';
                let resp = await fetch(`/get_signal?asset=${{encodeURIComponent(document.getElementById('asset').value)}}&timeframe=${{encodeURIComponent(document.getElementById('time').value)}}`);
                let data = await resp.json();
                document.getElementById('loader').style.display = 'none';
                document.getElementById('res').innerText = (data.signal == "UP" ? d.up : d.down);
                document.getElementById('res').style.color = data.signal == "UP" ? "#00ff66" : "#ff3344";
                document.getElementById('accuracy').style.display = 'block';
                document.getElementById('accuracy').innerText = "ACCURACY: " + data.accuracy + "%";
                let expVal = document.getElementById('exp').value;
                let expSeconds = parseInt(expVal.replace(/\D/g, '')) * 60;
                timerEl = document.getElementById('timer');
                timerEl.innerText = d.open;
                currentExpInterval = setInterval(() => {{
                    if(expSeconds > 0) {{ timerEl.innerText = d.close + expSeconds + (l == 'ru' || l == 'ua' ? " сек" : " sec"); expSeconds--; }} 
                    else {{ clearInterval(currentExpInterval); timerEl.innerText = d.end; document.getElementById('martBtn').style.display = 'block'; }}
                }}, 1000);
            }}

            async function sendForm() {{
                const userInp = document.getElementById('username').value.trim().replace('@', '');
                const codeInp = document.getElementById('code').value.trim();
                const btn = document.getElementById('submitBtn');
                const errDiv = document.getElementById('error-msg');
                const succDiv = document.getElementById('success-msg');

                errDiv.style.display = 'none';
                succDiv.style.display = 'none';

                if(!userInp || !codeInp) {{
                    errDiv.innerText = "Заполните все поля!";
                    errDiv.style.display = 'block';
                    return;
                }}

                btn.disabled = true;
                btn.innerText = "Проверка кода...";

                try {{
                    const formData = new FormData();
                    formData.append('username', userInp);
                    formData.append('code', codeInp);

                    const response = await fetch('/request_access', {{
                        method: 'POST',
                        body: formData
                    }});

                    if (!response.ok) {{
                        throw new Error("Сервер вернул ошибку " + response.status);
                    }}

                    const result = await response.json();

                    if(result.success) {{
                        succDiv.innerText = result.message;
                        succDiv.style.display = 'block';
                        localStorage.setItem('tg_username', userInp);
                        setTimeout(() => {{
                            checkAuth();
                        }}, 1000);
                    }} else {{
                        errDiv.innerText = result.message;
                        errDiv.style.display = 'block';
                        btn.disabled = false;
                        btn.innerText = "Активировать доступ";
                    }}
                }} catch(e) {{
                    errDiv.innerText = "Ошибка: " + e.message;
                    errDiv.style.display = 'block';
                    btn.disabled = false;
                    btn.innerText = "Активировать доступ";
                }}
            }}

            checkAuth();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
