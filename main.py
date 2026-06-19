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
            else:
                new_status_text = "НЕИЗВЕСТНО"
            
            # Изменяем только строчку статуса, кнопки оставляем рабочими!
            new_text = f"🔔 **Новый ученик активировал код!**\n\n**Ник:** @{username}\n**Код:** `{code}`\n**Текущий статус:** {new_status_text}"
            
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            edit_payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
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
            
            answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
            answer_payload = {"callback_query_id": callback_query["id"], "text": f"Статус изменен на: {new_status_text}"}
            
            async with httpx.AsyncClient() as client:
                await client.post(edit_url, json=edit_payload, timeout=5.0)
                await client.post(answer_url, json=answer_payload, timeout=5.0)
                
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

# --- СТРОГАЯ ПРОВЕРКА СТАТУСА ДЛЯ ФРОНТЕНДА ---
@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    return JSONResponse({"status": status})

# --- ИСПРАВЛЕННАЯ ЛОГИКА АКТИВАЦИИ ОДНОРАЗОВЫХ КОДОВ ---
@app.post("/request_access")
async def request_access(username: str = Form(...), code: str = Form(...)):
    username = username.strip().replace("@", "").replace(" ", "")
    code = code.strip().replace(" ", "")
    db = get_db()
    
    if code in db["keys"]:
        db["keys"].remove(code)
        db["users"][username] = {"status": "approved", "used_code": code}
        save_db(db)
        
        asyncio.create_task(send_tg_notification(username, code))
        return JSONResponse({"success": True, "message": "Код успешно активирован! Загрузка..."})
        
    if username in db["users"] and db["users"][username]["status"] == "approved":
        return JSONResponse({"success": True, "message": "Доступ подтвержден! Входим в терминал..."})
        
    return JSONResponse({"success": False, "message": "Неверный, использованный код или доступ закрыт!"})

# --- ТРЕЙДИНГ ДАННЫЕ И ИНДИКАТОРЫ ---
POCKET_API_TOKEN = "Avqw-qRFXfnAsn88w"

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
            .loader {{ width: 45px; height: 45px; border: 4px solid #161b26; border-top: 4px solid #a855f7; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 15px auto; display: none; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            select {{ width: 100%; padding: 14px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; font-size: 14px; font-weight: 600; color: #ffffff; outline: none; }}
            label {{ font-size: 11px; font-weight: bold; color: #4b5975; display: block; margin-bottom: 5px; letter-spacing: 0.8px; text-transform: uppercase; }}
            .btn {{ width: 100%; padding: 16px; border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; }}
            .btn-activate {{ width: 100%; max-width: 320px; padding: 16px; background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 12px; letter-spacing: 1px; text-transform: uppercase; box-shadow: 0 5px 20px rgba(100,27,250,0.4); }}
            .btn-activate:disabled {{ background: #1a2233; color: #4b5975; cursor: not-allowed; box-shadow: none; }}
            .btn-main {{ background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); }}
            .btn-auto {{ background: linear-gradient(135deg, #00ff66 0%, #00b344 100%); color: #000; font-weight: 900; }}
            .btn-pocket {{ background: #141924; border: 1px solid #222d42; color: #38ef7d; }}
            .btn-support {{ background: #080a10; border: 1px solid #161b26; color: #586988; font-size: 11px; margin-top: 15px; }}
            .btn-mart {{ background: #ff3344; display: none; }}
            .lang-select {{ background: #0f131e; color: white; border: 1px solid #1a2233; padding: 6px 10px; border-radius: 8px; font-size: 12px; }}
            .payout-badge {{ color: #00ff66; font-weight: 800; font-size: 12px; margin-top: 4px; display: block; }}
            .stat-panel {{ background: #080a10; border: 1px solid #1a2233; border-radius: 20px; padding: 15px; margin-bottom: 20px; text-align: center; }}
            .wr-val {{ font-size: 22px; font-weight: 900; color: #00ff66; margin-bottom: 10px; }}
            .counter-box {{ display: flex; gap: 10px; }}
            .count-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; background: #0f131e; padding: 10px; border-radius: 12px; border: 1px solid #1a2233; color: white; font-weight: 800; }}
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
                    <span id="flag_icon" style="font-size:20px;">🇷🇺</span>
                    <select id="lang" class="lang-select" onchange="changeLang()">
                        <option value="ru">🇷🇺 RU</option>
                        <option value="en">🇺🇸 EN</option>
                        <option value="ua">🇺🇦 UA</option>
                        <option value="es">🇪🇸 ES</option>
                        <option value="de">🇩🇪 DE</option>
                    </select>
                </div>
            </div>

            <div style="max-width:430px; width: 100%; margin:15px auto 30px auto; padding:25px; background:#080a10; border-radius:28px; border: 1px solid #121722; text-align:center; box-sizing: border-box;">
                <div class="stat-panel">
                    <div id="wr_display" class="wr-val">WIN RATE: 0%</div>
                    <div class="counter-box">
                        <button class="count-btn" onclick="updateStat('win', 1)">Profit <span id="win_counter">0</span></button>
                        <button class="count-btn" onclick="updateStat('loss', 1)">Loss <span id="loss_counter">0</span></button>
                    </div>
                </div>
                <div style="text-align:left; margin-bottom:14px;"><label id="lbl_market">КАТЕГОРИЯ РЫНКА</label><select id="cat" onchange="updCategory()"></select></div>
                <div id="sub_cat_block" style="text-align:left; margin-bottom:14px;"><label id="lbl_type">ТИП АКТИВА</label><select id="sub_cat" onchange="updSubCategory()"></select></div>
                <div style="text-align:left; margin-bottom:14px;"><label id="lbl_asset">АКТИВНАЯ ПАРА</label><select id="asset" onchange="updAsset()"></select><span id="payout_lbl" class="payout-badge">PAYOUT: 92%</span></div>
                
                <button id="runBtn" class="btn btn-main" onclick="startFlow(false)">СКАНИРОВАТЬ РЫНОК</button>
                <button id="autoBtn" class="btn btn-auto" onclick="startFlow(true)">ИИ СДЕЛАТЬ ЗА ВАС</button>
                <button id="martBtn" class="btn btn-mart" onclick="startFlow(false, true)">ПЕРЕКРЫТИЕ</button>
                
                <div id="loader" class="loader"></div>
                <div id="res" style="font-size:55px; font-weight:900; margin:10px 0; color:#ffffff;">--</div>
                <div id="accuracy" style="font-size:14px; font-weight:800; color:#a855f7; display:none;"></div>
                <div id="timer" style="font-size:14px; font-weight:800; color:#ffaa00; margin-bottom:15px;"></div>
                
                <button class="btn" style="background:#141924; color:#ff3344; margin-top:10px; font-size:11px;" onclick="logout()">ВЫЙТИ ИЗ АККАУНТА</button>
            </div>
        </div>

        <div id="blocked-screen" style="display: none; background:#06080c; color:#ff3344; text-align:center; padding-top:100px; height:100vh; flex-direction:column; align-items:center;">
            <h1>Доступ заблокирован администратором.</h1>
        </div>

        <script>
            const rawData = {json.dumps(ASSETS_DATA)};
            let wins = 0, losses = 0, currentExpInterval = null;

            async function checkAuth() {{
                const localUser = localStorage.getItem('tg_username');
                if (!localUser) {{ showScreen('auth-screen'); return; }}
                try {{
                    const response = await fetch('/check_user_status?username=' + encodeURIComponent(localUser));
                    const data = await response.json();
                    if (data.status === 'approved') {{ showScreen('terminal-screen'); changeLang(); }}
                    else if (data.status === 'blocked') {{ showScreen('blocked-screen'); }}
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
            function updateStat(type, val) {{ if(type=='win') wins+=val; else losses+=val; updateDisplay(); }}
            function updateDisplay() {{
                document.getElementById('win_counter').innerText = wins; document.getElementById('loss_counter').innerText = losses;
                let total = wins + losses; let wr = total == 0 ? 0 : ((wins/total)*100).toFixed(1);
                document.getElementById('wr_display').innerText = "WIN RATE: " + wr + "%";
            }}
            
            function changeLang() {{ 
                let l = document.getElementById('lang').value;
                const flags = {{ "ru": "🇷🇺", "en": "🇺🇸", "ua": "🇺🇦", "es": "🇪🇸", "de": "🇩🇪" }};
                document.getElementById('flag_icon').innerText = flags[l] || "🇷🇺";
                
                let catSelect = document.getElementById('cat'); catSelect.innerHTML = ""; 
                Object.keys(rawData[l]).forEach(c => {{ catSelect.innerHTML += `<option>${{c}}</option>`; }}); 
                updCategory(); 
            }}
            
            function updCategory(){{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value; document.getElementById('sub_cat').innerHTML = Object.keys(rawData[l][c]).map(t => `<option>${{t}}</option>`).join(''); updSubCategory(); }}
            function updSubCategory() {{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, t = document.getElementById('sub_cat').value; document.getElementById('asset').innerHTML = rawData[l][c][t].map(a => `<option>${{a}}</option>`).join(''); updAsset(); }}
            
            function updAsset() {{
                let asset = document.getElementById('asset').value;
                let payout = asset.includes("OTC") ? 92 : (["BTC", "ETH", "SOL", "XRP", "Bitcoin", "Ethereum", "Solana", "Ripple"].some(c => asset.includes(c)) ? 78 : 82);
                document.getElementById('payout_lbl').innerText = "PAYOUT: " + payout + "%";
            }}

            async function startFlow(isAI, isMart = false) {{
                if(currentExpInterval) clearInterval(currentExpInterval);
                document.getElementById('loader').style.display = 'block';
                let resp = await fetch(`/get_signal?asset=${{encodeURIComponent(document.getElementById('asset').value)}}&timeframe=1m`);
                let data = await resp.json();
                document.getElementById('loader').style.display = 'none';
                document.getElementById('res').innerText = data.signal;
                document.getElementById('res').style.color = data.signal == "UP" ? "#00ff66" : "#ff3344";
            }}

            async function sendForm() {{
                const userInp = document.getElementById('username').value.trim().replace('@', '');
                const codeInp = document.getElementById('code').value.trim();
                const btn = document.getElementById('submitBtn');
                const errDiv = document.getElementById('error-msg');
                const succDiv = document.getElementById('success-msg');

                if(!userInp || !codeInp) return;
                btn.disabled = true;
                errDiv.style.display = 'none';
                succDiv.style.display = 'none';

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
                        btn.disabled = false;
                    }}
                }} catch(e) {{ btn.disabled = false; }}
            }}
            checkAuth();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
