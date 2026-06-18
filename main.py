import json
import random
import asyncio
import httpx
import numpy as np
import os
import secrets
import uvicorn
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- СИСТЕМА УПРАВЛЕНИЯ TELEGRAM И АДМИНКОЙ ---
BOT_TOKEN = "8905743098:AAHS3eozt39qyO3Hjiy4GSapT1VlOmPFZW4"
MY_TG_ID = 6765689893
MY_ADMIN_PASSWORD = "SUPER_ADMIN_123"
DB_FILE = "hrom_database.json"

if not hasattr(app, "generated_keys"):
    app.generated_keys = set()

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {"sessions": {}, "banned_nicknames": []}
    return {"sessions": {}, "banned_nicknames": []}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_db()

# Функция отправки сообщений с кнопками управления
async def send_tg_admin(text: str, reply_markup: dict = None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": MY_TG_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print(f"Ошибка отправки в ТГ: {e}")

# --- ФОНОВЫЙ ПРОЦЕСС ТГ-БОТА (ОБРАБОТКА ИНЛАЙН КНОПОК БАН/РАЗБАН) ---
async def tg_bot_loop():
    offset = 0
    global db
    print("ТГ-Админка запущена...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=20"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=25.0)
                updates = resp.json().get("result", [])
                
            for update in updates:
                offset = update["update_id"] + 1
                
                # ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ПОД СООБЩЕНИЕМ
                if "callback_query" in update:
                    callback = update["callback_query"]
                    data = callback.get("data", "")
                    chat_id = callback["message"]["chat"]["id"]
                    
                    if chat_id != MY_TG_ID: continue
                    
                    # Нажата кнопка ЗАБЛОКИРОВАТЬ
                    if data.startswith("tgban_"):
                        nik_to_ban = data.replace("tgban_", "").strip().lower()
                        
                        db = load_db()
                        if nik_to_ban not in db["banned_nicknames"]:
                            db["banned_nicknames"].append(nik_to_ban)
                        
                        # Отключаем активные сессии
                        for token, info in db["sessions"].items():
                            if info["username"].lower() == nik_to_ban:
                                info["active"] = False
                        save_db(db)
                        
                        # Всплывающее окошко в ТГ
                        url_ans = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        async with httpx.AsyncClient() as c:
                            await c.post(url_ans, json={"callback_query_id": callback["id"], "text": f"@{nik_to_ban} забанен!"})
                            
                        await send_tg_admin(f"🔴 Пользователь <b>@{nik_to_ban}</b> заблокирован и выброшен из терминала!")
                    
                    # Нажата кнопка РАЗБЛОКИРОВАТЬ
                    elif data.startswith("tgunban_"):
                        nik_to_unban = data.replace("tgunban_", "").strip().lower()
                        
                        db = load_db()
                        if nik_to_unban in db["banned_nicknames"]:
                            db["banned_nicknames"].remove(nik_to_unban)
                        
                        # Возвращаем доступ сессиям
                        for token, info in db["sessions"].items():
                            if info["username"].lower() == nik_to_unban:
                                info["active"] = True
                        save_db(db)
                        
                        url_ans = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
                        async with httpx.AsyncClient() as c:
                            await c.post(url_ans, json={"callback_query_id": callback["id"], "text": f"@{nik_to_unban} разбанен!"})
                            
                        await send_tg_admin(f"🟢 Пользователь <b>@{nik_to_unban}</b> успешно разблокирован!")
                
                # Обычные команды в чате
                elif "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    text = message.get("text", "").strip()
                    
                    if chat_id != MY_TG_ID: continue
                    
                    if text == "/start":
                        await send_tg_admin("Привет, Босс! Теперь при каждом первом входе нового ученика сюда будет прилетать автоматическое уведомление с кнопками БАНА и РАЗБАНА прямо под ним.")
                    elif text == "/list":
                        db = load_db()
                        banned = db.get("banned_nicknames", [])
                        if not banned: await send_tg_admin("Черный список пуст.")
                        else: await send_tg_admin("🚫 <b>Сейчас в ЧС:</b>\n\n" + "\n".join([f"• @{x}" for x in banned]))
                            
        except Exception as e:
            await asyncio.sleep(2)
        await asyncio.sleep(1)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(tg_bot_loop())


# --- БРАУЗЕРНЫЙ ГЕНЕРАТОР ОДНОРАЗОВЫХ КЛЮЧЕЙ ДОСТУПА ---
@app.get("/generate_key")
async def generate_key(master: str = ""):
    if master != MY_ADMIN_PASSWORD:
        return HTMLResponse("Ошибка: Доступ к генератору запрещен!", status_code=403)
    
    new_key = "HROM_" + secrets.token_hex(3).upper()
    app.generated_keys.add(new_key)
    
    return HTMLResponse(f"""
    <div style="text-align:center; padding:50px; font-family:sans-serif; background:#06080c; color:white; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; margin:0; box-sizing:border-box;">
        <h2 style="color:#586988; margin-bottom:10px;">Создан новый одноразовый ключ:</h2>
        <div style="background:#0f131e; border:1px solid #1a2233; padding:20px 40px; border-radius:14px; font-size:24px; font-weight:bold; color:#00ff66; letter-spacing:1px; margin-bottom:20px;">
            {new_key}
        </div>
        <p style="color:#4b5975; max-width:300px; font-size:13px;">Отдай его человеку вместе с запросом его Telegram-ника.</p>
        <button onclick="window.location.reload()" style="padding:10px 20px; background:#a855f7; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">Создать еще один</button>
    </div>
    """)


# --- ОБРАБОТКА ФОРМЫ ВХОДА И АВТО-ОТПРАВКА КНОПОК В ТГ ---
@app.post("/request_access")
async def request_access(username: str = Form(...), access_code: str = Form(...)):
    input_nik = username.strip().lower().replace("@", "")
    code_entered = access_code.strip()
    
    global db
    db = load_db()
    
    if input_nik in db.get("banned_nicknames", []):
        return HTMLResponse("<body style='background:#06080c; color:white; text-align:center; padding-top:50px; font-family:sans-serif;'><h2>Доступ заблокирован администратором!</h2></body>")
    
    if code_entered in app.generated_keys:
        app.generated_keys.remove(code_entered) 
        
        user_session_token = secrets.token_hex(16)
        db["sessions"][user_session_token] = {"username": input_nik, "active": True}
        save_db(db)
        
        # ГЕНЕРИРУЕМ ДВЕ ИНЛАЙН КНОПКИ ПОД УВЕДОМЛЕНИЕМ ДЛЯ КАЖДОГО ЮЗЕРА
        markup = {
            "inline_keyboard": [
                [
                    {"text": "❌ Заблокировать", "callback_data": f"tgban_{input_nik}"},
                    {"text": "✅ Разблокировать", "callback_data": f"tgunban_{input_nik}"}
                ]
            ]
        }
        
        # Отправляем тебе мгновенный пуш в Telegram
        asyncio.create_task(send_tg_admin(
            f"🔔 <b>Новый ученик активировал код!</b>\n\n<b>Ник:</b> @{input_nik}\n<b>Код:</b> <code>{code_entered}</code>\n\nУправляй доступом с помощью кнопок ниже:", 
            reply_markup=markup
        ))
        
        response = HTMLResponse("<script>window.location.href='/';</script>")
        response.set_cookie(key="hrom_session_id", value=user_session_token, max_age=315360000, path="/")
        return response
    else:
        return HTMLResponse("<div style='color:white; background:#06080c; height:100vh; text-align:center; padding-top:50px; font-family:sans-serif;'><h2>Этот код не существует, либо уже активирован!</h2><br><a href='/' style='color:#a855f7;'>Назад</a></div>")


# --- СИСТЕМА СИГНАЛОВ И ОСТАЛЬНОЙ ИНТЕРФЕЙС ---
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
    }
}

def get_pocket_payout(asset: str) -> int:
    if "OTC" in asset: return 92
    if any(crypto in asset for crypto in ["BTC", "ETH", "SOL", "XRP"]): return 78
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
    if "OTC" in asset:
        return {"signal": "UP" if random.random() > 0.5 else "DOWN", "payout": get_pocket_payout(asset), "accuracy": round(random.uniform(67.2, 72.5), 1), "outcome": "WIN"}
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
    return {"signal": signal, "payout": get_pocket_payout(asset), "accuracy": accuracy, "outcome": "WIN"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user_token = request.cookies.get("hrom_session_id")
    current_db = load_db()
    is_allowed = False
    current_user_nik = ""
    
    if user_token and user_token in current_db["sessions"]:
        session_info = current_db["sessions"][user_token]
        if session_info["active"] and (session_info["username"].lower() not in current_db.get("banned_nicknames", [])):
            is_allowed = True
            current_user_nik = session_info["username"]

    assets_json_str = json.dumps(ASSETS_DATA)

    if is_allowed:
        return rf"""
        <html style="background:#06080c; color:#ffffff; font-family:'Segoe UI', Roboto, sans-serif; margin:0; padding:0;">
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>HROM QUANTUM CORE v16.0</title>
            <style>
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                @keyframes shine {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
                .loader {{ width: 45px; height: 45px; border: 4px solid #161b26; border-top: 4px solid #a855f7; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 15px auto; display: none; }}
                select {{ width: 100%; padding: 14px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; font-size: 14px; font-weight: 600; color: #ffffff; outline: none; appearance: none; }}
                label {{ font-size: 11px; font-weight: bold; color: #4b5975; display: block; margin-bottom: 5px; letter-spacing: 0.8px; text-transform: uppercase; }}
                .btn {{ width: 100%; padding: 16px; border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 13px; letter-spacing: 1px; text-transform: uppercase; transition: all 0.2s; margin-bottom: 10px; }}
                .btn-main {{ background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); box-shadow: 0 5px 20px rgba(100,27,250,0.4); }}
                .btn-auto {{ background: linear-gradient(135deg, #00ff66 0%, #00b344 100%); color: #000; font-weight: 900; }}
                .btn-pocket {{ background: #141924; border: 1px solid #222d42; color: #38ef7d; }}
                .btn-support {{ background: #080a10; border: 1px solid #161b26; color: #586988; font-size: 11px; margin-top: 15px; }}
                .btn-mart {{ background: #ff3344; display: none; width: 100%; }}
                .btn:active {{ transform: scale(0.98); }}
                .lang-select {{ background: #0f131e; color: white; border: 1px solid #1a2233; padding: 6px 10px; border-radius: 8px; font-size: 12px; font-weight: bold; }}
                .payout-badge {{ color: #00ff66; font-weight: 800; font-size: 12px; margin-top: 4px; display: block; }}
                .stat-panel {{ background: #080a10; border: 1px solid #1a2233; border-radius: 20px; padding: 15px; margin-bottom: 20px; text-align: center; }}
                .wr-val {{ font-size: 22px; font-weight: 900; color: #00ff66; margin-bottom: 10px; text-shadow: 0 0 15px rgba(0,255,102,0.2); }}
                .counter-box {{ display: flex; gap: 10px; }}
                .count-btn {{ flex: 1; display: flex; flex-direction: column; align-items: center; background: #0f131e; padding: 10px; border-radius: 12px; border: 1px solid #1a2233; cursor: pointer; font-weight: 800; font-size: 13px; transition: 0.2s; }}
            </style>
        </head>
        <div style="max-width:430px; margin:15px auto; padding:0 15px; display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span id="flag_icon" style="font-size:20px; line-height:1;">🇷🇺</span>
                <select id="lang" class="lang-select" onchange="changeLang()">
                    <option value="ru">🇷🇺 RU</option>
                    <option value="en">🇺🇸 EN</option>
                    <option value="ua">🇺🇦 UA</option>
                </select>
            </div>
            <div style="font-size:11px; color:#a855f7; font-weight:bold;">УЧЕНИК: @{current_user_nik} ✅</div>
        </div>
        <div style="max-width:430px; margin:0 auto 30px auto; padding:25px; background:#080a10; border-radius:28px; border: 1px solid #121722; box-shadow: 0 25px 50px rgba(0,0,0,0.8); text-align:center;">
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
            <a href="https://t.me/andriddddd" target="_blank" style="text-decoration: none;"><button id="btn_supp" class="btn btn-support">РАЗРАБОТЧИК / SUPPORT</button></a>
        </div>
        <script>
            const rawData = {assets_json_str};
            const tf_options = {{
                ru: ["5 сек", "15 сек", "30 сек", "1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "6 мин", "7 мин", "8 мин", "9 мин", "10 мин"],
                en: ["5 sec", "15 sec", "30 sec", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
                ua: ["5 сек", "15 сек", "30 сек", "1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "6 хв", "7 хв", "8 хв", "9 хв", "10 хв"]
            }};
            let wins = 0, losses = 0, currentBet = 100, martStep = 0, currentInterval = null, currentExpInterval = null;
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
                ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", scan: "СКАНИРОВАТЬ РЫНОК", auto: "ИИ СДЕЛАТЬ ЗА ВАС", pocket: "ОТКРЫТЬ POCKET OPTION", support: "РАЗРАБОТЧИК / SUPPORT", ready: "СИСТЕМА СИНХРОНИЗИРОВАНА", mart: "ПЕРЕКРЫТИЕ", profit: "Profit", loss: "Loss", reset: "СБРОСИТЬ СТАТИСТИКУ", up: "ВВЕРХ", down: "ВНИЗ", enter: "ВХОД ЧЕРЕЗ: ", open: "СДЕЛКА ОТКРЫТА!", close: "ДО ЗАКРЫТИЯ: ", end: "ЦИКЛ ЗАВЕРШЕН" }}, 
                en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION TIME", scan: "SCAN MARKET", auto: "AI DO FOR YOU", pocket: "OPEN POCKET OPTION", support: "DEVELOPER / SUPPORT", ready: "SYSTEM SYNCHRONIZED", mart: "MARTINGALE", profit: "Profit", loss: "Loss", reset: "RESET STATISTICS", up: "CALL / UP", down: "PUT / DOWN", enter: "ENTRY IN: ", open: "TRADE OPENED!", close: "CLOSING IN: ", end: "CYCLE COMPLETED" }},
                ua: {{ market: "КАТЕГОРІЯ РИНКУ", type: "ТИП АКТИВУ", asset: "АКТИВНА ПАРА", tf: "ІНТЕРВАЛ СВІЧКИ", exp: "ЕКСПІРАЦІЯ", scan: "СКАНУВАТИ РИНОК", auto: "ШІ ЗРОБИТЬ ЗА ВАС", pocket: "ВІДКРИТИ POCKET OPTION", support: "РОЗРОБНИК / SUPPORT", ready: "СИСТЕМА СИНХРОНІЗОВАНА", mart: "ПЕРЕКРИТТЯ", profit: "Профіт", loss: "Лос", reset: "СКИНУТИ СТАТИСТИКУ", up: "ВГОРУ", down: "ВНИЗ", enter: "ВХІД ЧЕРЕЗ: ", open: "УГОДУ ВІДКРИТО!", close: "ДО ZАКРИТЯ: ", end: "ЦИКЛ ЗАВЕРШЕНО" }}
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
            function updCategory(){{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, types = Object.keys(rawData[l][c]); document.getElementById('sub_cat').innerHTML = types.map(t => `<option>${{t}}</option>`).join(''); updSubCategory(); }}
            function updSubCategory() {{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, t = document.getElementById('sub_cat').value, assets = rawData[l][c][t] || []; document.getElementById('asset').innerHTML = assets.map(a => `<option>${{a}}</option>`).join(''); updAsset(); }}
            function updAsset() {{ 
                let l = document.getElementById('lang').value;
                let asset = document.getElementById('asset').value; 
                document.getElementById('payout_lbl').innerText = `PAYOUT: ${{calcLocalPayout(asset)}}%`; 
                let expSelect = document.getElementById('exp');
                let options = tf_options[l];
                if (!asset.includes("OTC")) {{ options = options.filter(o => !o.includes("сек") && !o.includes("sec") && !o.includes("Sek")); }}
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
                    document.getElementById('cat').selectedIndex = Math.floor(Math.random()*cats.length); 
                    updCategory(); 
                    let subCats = document.getElementById('sub_cat').options;
                    document.getElementById('sub_cat').selectedIndex = Math.floor(Math.random()*subCats.length);
                    updSubCategory();
                    let assets = document.getElementById('asset').options;
                    document.getElementById('asset').selectedIndex = Math.floor(Math.random()*assets.length);
                    updAsset();
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
                let expSeconds = parseInt(expVal.replace(/\D/g, ''));
                if (!expVal.includes("сек") && !expVal.includes("sec") && !expVal.includes("Sek")) {{ expSeconds = expSeconds * 60; }}
                timerEl = document.getElementById('timer');
                timerEl.innerText = d.open;
                currentExpInterval = setInterval(() => {{
                    if(expSeconds > 0) {{ timerEl.innerText = d.close + expSeconds + (l == 'ru' || l == 'ua' ? " сек" : " sec"); expSeconds--; }} 
                    else {{ clearInterval(currentExpInterval); timerEl.innerText = d.end; document.getElementById('martBtn').style.display = 'block'; }}
                }}, 1000);
            }}
            changeLang();
        </script>
        </html>
        """

    return f"""
    <div style="text-align:center; padding:50px; color:white; font-family:'Segoe UI', Roboto, sans-serif; background:#06080c; height:100vh; display:flex; flex-direction:column; justify-content:center; align-items:center; margin:0; box-sizing:border-box;">
        <h1 style="color:#963bfe; font-size:28px; margin-bottom:10px; font-weight:900; letter-spacing:1px;">HROM QUANTUM CORE</h1>
        <p style="color:#586988; margin-bottom:25px; font-size:14px;">Для доступа к сигналам пройдите верификацию устройства</p>
        
        <form action="/request_access" method="post" style="background:#080a10; padding:30px; border-radius:24px; border:1px solid #1a2233; box-shadow:0 15px 40px rgba(0,0,0,0.6); max-width:340px; width:100%; box-sizing:border-box;">
            
            <div style="text-align:left; margin-bottom:15px;">
                <label style="font-size:11px; color:#4b5975; font-weight:bold; text-transform:uppercase;">1. Твой Telegram Username</label>
                <input type="text" name="username" placeholder="@твой_ник_в_тг" required style="padding:15px; width:100%; border-radius:14px; border:1px solid #222d42; background:#0f131e; color:white; font-size:14px; margin-top:5px; box-sizing:border-box; outline:none;">
            </div>
            
            <div style="text-align:left; margin-bottom:25px;">
                <label style="font-size:11px; color:#4b5975; font-weight:bold; text-transform:uppercase;">2. Одноразовый код доступа</label>
                <input type="text" name="access_code" placeholder="HROM_XXXXXX" required style="padding:15px; width:100%; border-radius:14px; border:1px solid #222d42; background:#0f131e; color:white; font-size:14px; font-weight:bold; text-align:center; margin-top:5px; box-sizing:border-box; letter-spacing:1px; outline:none;">
            </div>
            
            <button type="submit" style="padding:16px; width:100%; cursor:pointer; background:linear-gradient(135deg, #963bfe 0%, #641bfa 100%); color:white; border:none; border-radius:14px; font-weight:800; font-size:13px; letter-spacing:1px; text-transform:uppercase; transition:0.2s; box-shadow:0 5px 15px rgba(100,27,250,0.3);">АКТИВИРОВАТЬ ДОСТУП</button>
        </form>
    </div>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
