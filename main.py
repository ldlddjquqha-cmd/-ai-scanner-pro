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

DB_FILE = "requests.json"
BOT_TOKEN = "8905743098:AAFCqIHqY1PzaVM4hqISpvuBV4s2ka30bfs"
ADMIN_CHAT_ID = "6765689893" 

# --- ИНИЦИАЛИЗАЦИЯ И РАБОТА С БАЗОЙ КЛЮЧЕЙ И ЮЗЕРОВ ---
def get_db():
    if not os.path.exists(DB_FILE): 
        return {"keys": ["HROM_7777", "HROM_8888", "HROM_9999"], "users": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: 
            data = json.load(f)
            if "keys" not in data or "users" not in data:
                return {"keys": ["HROM_7777", "HROM_8888", "HROM_9999"], "users": {}}
            return data
        except: 
            return {"keys": ["HROM_7777", "HROM_8888", "HROM_9999"], "users": {}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- УВЕДОМЛЕНИЕ В ТГ С КНОПКАМИ БАНА ---
async def send_tg_notification(username, code):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": f"🔔 **Новый ученик успешно вошел!**\n\n**Ник:** @{username}\n**Использованный код:** `{code}`\n**Текущий статус:** ✅ Доступ разрешен",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "❌ Забанить", "callback_data": f"block_{username}"},
                    {"text": "✅ Разблокировать", "callback_data": f"approve_{username}"}
                ]
            ]
        }
    }
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            print(f"Ошибка ТГ: {e}")

# --- ТЕЛЕГРАМ ВЕБХУК ДЛЯ УПРАВЛЕНИЯ ДОСТУПОМ ---
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
            if len(parts) < 2: return {"status": "error"}
            
            action = parts[0]
            username = parts[1]
            
            db = get_db()
            new_status_text = ""
            
            if username in db["users"]:
                if action == "block":
                    db["users"][username]["status"] = "blocked"
                    new_status_text = "❌ ЗАБЛОКИРОВАН"
                elif action == "approve":
                    db["users"][username]["status"] = "approved"
                    new_status_text = "✅ ДОСТУП РАЗРЕШЕН"
                save_db(db)
            
            new_text = f"🔔 **Обновление статуса ученика!**\n\n**Ник:** @{username}\n**Текущий статус:** {new_status_text}"
            
            edit_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
            edit_payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "❌ Забанить", "callback_data": f"block_{username}"},
                            {"text": "✅ Разблокировать", "callback_data": f"approve_{username}"}
                        ]
                    ]
                }
            }
            
            answer_url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
            answer_payload = {"callback_query_id": callback_query["id"], "text": f"Статус: {new_status_text}"}
            
            async with httpx.AsyncClient() as client:
                await client.post(edit_url, json=edit_payload, timeout=5.0)
                await client.post(answer_url, json=answer_payload, timeout=5.0)
    except Exception as e:
        print(f"Ошибка в вебхуке: {e}")
    return {"status": "ok"}

# --- ПРОВЕРКА СТАТУСА ДЛЯ СТРАНИЦЫ ---
@app.get("/check_user_status")
async def check_user_status(username: str = ""):
    username = username.strip().replace("@", "").replace(" ", "")
    db = get_db()
    status = db["users"].get(username, {}).get("status") if username else None
    return JSONResponse({"status": status})

# --- АКТИВАЦИЯ ОДНОРАЗОВОГО КОДА ---
@app.post("/request_access")
async def request_access(username: str = Form(...), code: str = Form(...)):
    username = username.strip().replace("@", "").replace(" ", "")
    code = code.strip().replace(" ", "")
    db = get_db()
    
    if username in db["users"]:
        if db["users"][username]["status"] == "approved":
            return JSONResponse({"success": True, "message": "Доступ активен! Входим..."})
        if db["users"][username]["status"] == "blocked":
            return JSONResponse({"success": False, "message": "Ваш доступ заблокирован!"})
            
    if code in db["keys"]:
        db["keys"].remove(code)
        db["users"][username] = {"status": "approved", "code": code}
        save_db(db)
        asyncio.create_task(send_tg_notification(username, code))
        return JSONResponse({"success": True, "message": "Код успешно активирован!"})
        
    return JSONResponse({"success": False, "message": "Неверный код доступа!"})

# --- ГЕНЕРАЦИЯ ОДНОРАЗОВЫХ КЛЮЧЕЙ ---
@app.get("/generate_key")
async def generate_key(master: str = None):
    if master != "SUPER_ADMIN_123": 
        return HTMLResponse("<h1 style='color:red;'>Отказ в доступе</h1>")
    chars = "0123456789ABCDEF"
    new_key = "HROM_" + "".join(random.choice(chars) for _ in range(6))
    db = get_db()
    db["keys"].append(new_key)
    save_db(db)
    return HTMLResponse(f"<h2>Создан одноразовый ключ: <span style='color:green;'>{new_key}</span></h2>")

# --- ДВИЖОК ИНДИКАТОРОВ И СИГНАЛОВ ---
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
    }
}

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50.0
    deltas = np.diff(prices)
    up = np.where(deltas > 0, deltas, 0).mean()
    down = np.where(deltas < 0, -deltas, 0).mean()
    if down == 0: return 100.0
    return 100.0 - (100.0 / (1.0 + (up / down)))

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
        return {"signal": "UP" if random.random() > 0.5 else "DOWN", "payout": 92, "accuracy": round(random.uniform(67.2, 72.5), 1)}
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1m&limit=30"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=3.0)
            prices = [float(c[4]) for c in response.json()]
    except: prices = [100.0] * 30
    rsi = calculate_rsi(prices)
    ema = calculate_ema(prices)
    curr = prices[-1]
    signal = "UP" if (curr > ema and rsi < 35) or (curr > ema) else "DOWN"
    accuracy = round(70.0 + random.uniform(0, 5), 1) if (rsi < 35 or rsi > 65) else round(60.0 + random.uniform(0, 3), 1)
    return {"signal": signal, "payout": 82, "accuracy": accuracy}

# --- ИНТЕРФЕЙС ТЕРМИНАЛА ---
@app.get("/", response_class=HTMLResponse)
async def index():
    return rf"""
    <html style="background:#06080c; color:#ffffff; font-family:sans-serif; margin:0; padding:0;">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HROM QUANTUM CORE</title>
        <style>
            .container {{ max-width: 430px; margin: 0 auto; padding: 20px; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; box-sizing: border-box; }}
            .title {{ font-size: 20px; font-weight: 800; color: #a855f7; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 5px; }}
            .subtitle {{ font-size: 11px; color: #4b5975; margin-bottom: 30px; text-align: center; }}
            .input-box {{ width: 100%; max-width: 320px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; padding: 16px; margin-bottom: 12px; box-sizing: border-box; }}
            input {{ background: transparent; border: none; color: white; width: 100%; font-size: 14px; font-weight: bold; outline: none; text-align: center; }}
            .btn-activate {{ width: 100%; max-width: 320px; padding: 16px; background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 12px; text-transform: uppercase; }}
            .btn-activate:disabled {{ background: #1a2233; color: #4b5975; cursor: not-allowed; }}
            .loader {{ width: 45px; height: 45px; border: 4px solid #161b26; border-top: 4px solid #a855f7; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 15px auto; display: none; }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            select {{ width: 100%; padding: 14px; background: #0f131e; border: 1px solid #1a2233; border-radius: 14px; font-size: 14px; color: #ffffff; outline: none; margin-bottom:14px; }}
            .btn {{ width: 100%; padding: 16px; border: none; color: white; font-weight: 800; border-radius: 14px; cursor: pointer; font-size: 13px; text-transform: uppercase; margin-bottom: 10px; }}
            .btn-main {{ background: linear-gradient(135deg, #963bfe 0%, #641bfa 100%); }}
        </style>
    </head>
    <body>

        <div id="auth-screen" class="container">
            <div class="title">HROM QUANTUM</div>
            <div class="subtitle">Введите ваш @username ТГ и секретный одноразовый код</div>
            <div class="input-box"><input type="text" id="username" placeholder="Ваш @username в ТГ"></div>
            <div class="input-box"><input type="text" id="code" placeholder="Код доступа"></div>
            <button id="submitBtn" class="btn-activate" onclick="sendForm()">Войти в терминал</button>
            <div id="error-msg" style="color:#ff3344; font-size:13px; font-weight:bold; margin-top:15px; display:none;"></div>
        </div>

        <div id="terminal-screen" class="container" style="display: none; height: auto; padding-top: 50px;">
            <div style="width:100%; background:#080a10; border-radius:28px; border: 1px solid #121722; padding:25px; box-sizing:border-box;">
                <label style="font-size:11px; color:#4b5975; font-weight:bold;">КАТЕГОРИЯ РЫНКА</label>
                <select id="cat" onchange="updCategory()"></select>
                
                <label style="font-size:11px; color:#4b5975; font-weight:bold;">ТИП АКТИВА</label>
                <select id="sub_cat" onchange="updSubCategory()"></select>
                
                <label style="font-size:11px; color:#4b5975; font-weight:bold;">АКТИВНАЯ ПАРА</label>
                <select id="asset"></select>
                
                <button class="btn btn-main" onclick="startFlow()">СКАНИРОВАТЬ РЫНОК</button>
                <div id="loader" class="loader"></div>
                <div id="res" style="font-size:55px; font-weight:900; text-align:center; margin:10px 0;">--</div>
            </div>
        </div>

        <div id="blocked-screen" class="container" style="display: none; color:#ff3344;">
            <h1>Доступ заблокирован администратором!</h1>
        </div>

        <script>
            const rawData = {json.dumps(ASSETS_DATA)};
            let checkInterval = null;

            async function checkAuth() {{
                const localUser = localStorage.getItem('tg_username');
                if (!localUser) return;
                try {{
                    const response = await fetch('/check_user_status?username=' + encodeURIComponent(localUser));
                    const data = await response.json();
                    if (data.status === 'approved') {{
                        document.getElementById('auth-screen').style.display = 'none';
                        document.getElementById('terminal-screen').style.display = 'flex';
                    }} else if (data.status === 'blocked') {{
                        document.getElementById('auth-screen').style.display = 'none';
                        document.getElementById('terminal-screen').style.display = 'none';
                        document.getElementById('blocked-screen').style.display = 'flex';
                    }}
                }} catch(e) {{ }}
            }}

            function changeLang() {{
                let catSelect = document.getElementById('cat'); catSelect.innerHTML = "";
                Object.keys(rawData['ru']).forEach(c => {{ catSelect.innerHTML += `<option>${{c}}</option>`; }});
                updCategory();
            }}

            function updCategory() {{
                let c = document.getElementById('cat').value;
                document.getElementById('sub_cat').innerHTML = Object.keys(rawData['ru'][c]).map(t => `<option>${{t}}</option>`).join('');
                updSubCategory();
            }}

            function updSubCategory() {{
                let c = document.getElementById('cat').value, t = document.getElementById('sub_cat').value;
                document.getElementById('asset').innerHTML = rawData['ru'][c][t].map(a => `<option>${{a}}</option>`).join('');
            }}

            async function startFlow() {{
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
                if(!userInp || !codeInp) return;

                const formData = new FormData();
                formData.append('username', userInp);
                formData.append('code', codeInp);

                const response = await fetch('/request_access', {{ method: 'POST', body: formData }});
                const result = await response.json();

                if(result.success) {{
                    localStorage.setItem('tg_username', userInp);
                    checkAuth();
                    setInterval(checkAuth, 3000);
                }} else {{
                    let err = document.getElementById('error-msg');
                    err.innerText = result.message; err.style.display = 'block';
                }}
            }}
            changeLang();
            const localUser = localStorage.getItem('tg_username');
            if (localUser) {{ checkAuth(); setInterval(checkAuth, 3000); }}
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
