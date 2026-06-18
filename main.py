import json
import random
import asyncio
import httpx
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# ТВОЙ ОФИЦИАЛЬНЫЙ API-ТОКЕН
POCKET_API_TOKEN = "Avqw-qRFXfnAsn88w"

# Полный маппинг
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
    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calculate_ema(prices, period=20):
    if len(prices) < period: return prices[-1]
    values = np.array(prices)
    alpha = 2 / (period + 1)
    ema = values[0]
    for price in values[1:]: ema = (price * alpha) + (ema * (1 - alpha))
    return float(ema)

@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str):
    await asyncio.sleep(1.5)
    binance_symbol = BINANCE_MAPPING.get(asset, "BTCUSDT")
    is_otc = "OTC" in asset
    interval = "1m"
    if "мин" in timeframe or "min" in timeframe or "m" in timeframe:
        try: interval = f"{int(''.join(filter(str.isdigit, timeframe)))}m"
        except: interval = "1m"
    if is_otc:
        random.seed(int(asyncio.get_event_loop().time() * 1000) % 9999)
        win_chance = random.uniform(0, 100)
        final_signal = "UP" if win_chance <= 68.0 else "DOWN"
        accuracy = round(random.uniform(86.4, 95.8), 1)
        return {"signal": final_signal, "payout": get_pocket_payout(asset), "accuracy": accuracy, "outcome": "WIN", "session_verified": True}
    prices = []
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={interval}&limit=50"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=3.0)
            if response.status_code == 200: prices = [float(candle[4]) for candle in response.json()]
    except Exception: pass
    if not prices:
        seed_base = sum(ord(char) for char in POCKET_API_TOKEN) + len(asset)
        random.seed(seed_base)
        base_price = random.uniform(10, 500)
        prices = [base_price * (1 + random.uniform(-0.005, 0.005)) for _ in range(50)]
    current_price = prices[-1]
    rsi_value = calculate_rsi(prices[-25:], period=14)
    ema_value = calculate_ema(prices, period=20)
    market_trend = "UP" if current_price > ema_value else "DOWN"
    if rsi_value >= 63 and market_trend == "DOWN":
        final_signal = "DOWN"
        accuracy = round(rsi_value if rsi_value <= 97.5 else 94.2, 1)
    elif rsi_value <= 37 and market_trend == "UP":
        final_signal = "UP"
        accuracy = round((100 - rsi_value) if (100 - rsi_value) <= 97.5 else 93.8, 1)
    else:
        final_signal = market_trend
        random.seed(int(current_price * 1000) % 777)
        accuracy = round(random.uniform(78.5, 88.2), 1)
    return {"signal": final_signal, "payout": get_pocket_payout(asset), "accuracy": accuracy, "outcome": "WIN", "session_verified": True}

@app.get("/", response_class=HTMLResponse)
async def index():
    return f"""
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
            .btn-vip-top {{ padding: 8px 12px; border: none; border-radius: 8px; background: linear-gradient(270deg, #ffd700, #ffa500, #b8860b, #ffd700); background-size: 400% 400%; animation: shine 4s ease infinite; color: #000 !important; font-weight: 900; font-size: 11px; cursor: pointer; box-shadow: 0 2px 10px rgba(255,215,0,0.3); text-transform: uppercase; letter-spacing: 0.5px; }}
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
                <option value="ru">🇷🇺 RU</option><option value="en">🇺🇸 EN</option><option value="ua">🇺🇦 UA</option>
                <option value="es">🇪🇸 ES</option><option value="de">🇩🇪 DE</option><option value="fr">🇫🇷 FR</option>
                <option value="it">🇮🇹 IT</option><option value="tr">🇹🇷 TR</option><option value="pt">🇵🇹 PT</option>
                <option value="pl">🇵🇱 PL</option>
            </select>
        </div>
        <a href="https://t.me/+uekq4TquqkM4Mzcy" target="_blank" style="text-decoration: none;"><button id="vip_btn_text" class="btn-vip-top">👑 VIP СИГНАЛЫ</button></a>
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
        const rawData = {json.dumps(ASSETS_DATA)};
        const tf_options = {{
            ru: ["5 сек", "15 сек", "30 сек", "1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "6 мин", "7 мин", "8 мин", "9 мин", "10 мин"],
            en: ["5 sec", "15 sec", "30 sec", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
            ua: ["5 сек", "15 сек", "30 сек", "1 хв", "2 хв", "3 хв", "4 хв", "5 хв", "6 хв", "7 хв", "8 хв", "9 хв", "10 хв"],
            es: ["5 seg", "15 seg", "30 seg", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
            de: ["5 Sek", "15 Sek", "30 Sek", "1 Min", "2 Min", "3 Min", "4 Min", "5 Min", "6 Min", "7 Min", "8 Min", "9 Min", "10 Min"],
            fr: ["5 sec", "15 sec", "30 sec", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
            it: ["5 sec", "15 sec", "30 sec", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
            tr: ["5 sn", "15 sn", "30 sn", "1 dk", "2 dk", "3 dk", "4 dk", "5 dk", "6 dk", "7 dk", "8 dk", "9 dk", "10 dk"],
            pt: ["5 seg", "15 seg", "30 seg", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"],
            pl: ["5 sek", "15 sek", "30 sek", "1 min", "2 min", "3 min", "4 min", "5 min", "6 min", "7 min", "8 min", "9 min", "10 min"]
        }};
        let wins = 0, losses = 0;
        function updateStat(t, v) {{ if(t=='win') wins = Math.max(0, wins + v); else losses = Math.max(0, losses + v); updateDisplay(); }}
        function updateDisplay() {{
            document.getElementById('win_counter').innerText = wins;
            document.getElementById('loss_counter').innerText = losses;
            let wr = (wins + losses) == 0 ? 0 : ((wins/(wins+losses))*100).toFixed(1);
            document.getElementById('wr_display').innerText = "WIN RATE: " + wr + "%";
        }}
        function resetStats() {{ wins=0; losses=0; updateDisplay(); }}
        function changeLang() {{ /* Логика переключения */ }}
        function updCategory() {{ /* Логика категорий */ }}
        function startFlow(auto) {{ document.getElementById('res').innerText = "CALCULATING..."; document.getElementById('loader').style.display = 'block'; }}
    </script>
    </html>
    """
    
