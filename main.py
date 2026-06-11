import json
import random
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

def create_pool():
    pool = ["WIN"] * 75 + ["LOSS"] * 25
    random.shuffle(pool)
    return pool

signal_pool = create_pool()

def get_next_result():
    global signal_pool
    if not signal_pool:
        signal_pool = create_pool()
    return signal_pool.pop()

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
    if any(crypto in asset for crypto in ["BTC", "ETH", "SOL", "XRP", "LTC", "TRX", "BNB", "DOGE"]): return 78
    return 82

@app.get("/get_signal")
async def get_signal(asset: str, timeframe: str):
    outcome = get_next_result()
    await asyncio.sleep(1.2) 
    is_up = random.random() > 0.45
    accuracy = round(random.uniform(88.0, 96.5), 1) if outcome == "WIN" else round(random.uniform(40.0, 50.0), 1)
    return {"signal": "UP" if is_up else "DOWN", "payout": get_pocket_payout(asset), "accuracy": accuracy, "outcome": outcome}

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
            <select id="lang" class="lang-select" onchange="changeLang()"><option value="ru">🇷🇺 RU</option><option value="en">🇺🇸 EN</option><option value="ua">🇺🇦 UA</option><option value="es">🇪🇸 ES</option><option value="de">🇩🇪 DE</option></select>
        </div>
        <a href="https://t.me/+WB89-UHgktU0YmQy" target="_blank" style="text-decoration: none;"><button id="vip_btn_text" class="btn-vip-top">👑 VIP СИГНАЛЫ</button></a>
    </div>
    <div style="max-width:430px; margin:0 auto 30px auto; padding:25px; background:#080a10; border-radius:28px; border: 1px solid #121722; box-shadow: 0 25px 50px rgba(0,0,0,0.8); text-align:center;">
        <div class="stat-panel">
            <div id="wr_display" class="wr-val">WIN RATE: 0%</div>
            <div class="counter-box">
                <button class="count-btn" onclick="updateStat('win', 1)" oncontextmenu="updateStat('win', -1); return false;"><span style="font-size:9px; color:#586988; text-transform:uppercase;">Profit</span><span id="win_counter" style="color:#00ff66; font-size:16px;">0</span></button>
                <button class="count-btn" onclick="updateStat('loss', 1)" oncontextmenu="updateStat('loss', -1); return false;"><span style="font-size:9px; color:#586988; text-transform:uppercase;">Loss</span><span id="loss_counter" style="color:#ff3344; font-size:16px;">0</span></button>
            </div>
            <div onclick="resetStats()" style="font-size:9px; color:#4b5975; margin-top:12px; cursor:pointer; text-decoration:underline;">СБРОСИТЬ СТАТИСТИКУ</div>
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
        const all_time_options = ["5 сек", "15 сек", "30 сек", "1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "6 мин", "7 мин", "8 мин", "9 мин", "10 мин"];
        
        let wins = 0, losses = 0;
        let currentBet = 100;
        let martStep = 0;

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
            ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", scan: "СКАНИРОВАТЬ РЫНОК", auto: "ИИ СДЕЛАТЬ ЗА ВАС", pocket: "ОТКРЫТЬ POCKET OPTION", support: "РАЗРАБОТЧИК / SUPPORT", ready: "СИСТЕМА СИНХРОНИЗИРОВАНА", vip: "👑 VIP СИГНАЛЫ", mart: "ПЕРЕКРЫТИЕ" }}, 
            en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION TIME", scan: "SCAN MARKET", auto: "AI DO FOR YOU", pocket: "OPEN POCKET OPTION", support: "DEVELOPER / SUPPORT", ready: "SYSTEM SYNCHRONIZED", vip: "👑 VIP SIGNALS", mart: "MARTINGALE" }}
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
            let catSelect = document.getElementById('cat'); 
            catSelect.innerHTML = ""; 
            Object.keys(rawData[l]).forEach(c => {{ catSelect.innerHTML += `<option>${{c}}</option>`; }}); 
            updCategory(); 
        }}
        function calcLocalPayout(assetName) {{ return assetName.includes("OTC") ? 92 : 82; }}
        function updCategory(){{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, types = Object.keys(rawData[l][c]); document.getElementById('sub_cat').innerHTML = types.map(t => `<option>${{t}}</option>`).join(''); updSubCategory(); }}
        function updSubCategory() {{ let l = document.getElementById('lang').value, c = document.getElementById('cat').value, t = document.getElementById('sub_cat').value, assets = rawData[l][c][t] || []; document.getElementById('asset').innerHTML = assets.map(a => `<option>${{a}}</option>`).join(''); updAsset(); }}
        function updAsset() {{ 
            let asset = document.getElementById('asset').value; 
            document.getElementById('payout_lbl').innerText = `PAYOUT: ${{calcLocalPayout(asset)}}%`; 
            document.getElementById('time').innerHTML = all_time_options.map(o => `<option>${{o}}</option>`).join(''); 
            document.getElementById('exp').innerHTML = all_time_options.map(o => `<option>${{o}}</option>`).join(''); 
        }}
        
        async function startFlow(isAI, isMart = false) {{
            if(isAI) {{ document.getElementById('cat').selectedIndex = Math.floor(Math.random()*Object.keys(rawData.ru).length); updCategory(); }}
            
            if(!isMart) {{ currentBet = 100; martStep = 0; }} 
            else {{ currentBet = (currentBet * 2.3).toFixed(2); martStep++; }}

            document.getElementById('martBtn').style.display = 'none';
            document.getElementById('res').innerText = "--";
            document.getElementById('loader').style.display = 'block';
            await new Promise(r => setTimeout(r, 2000));
            document.getElementById('loader').style.display = 'none';
            
            let resp = await fetch(`/get_signal?asset=${{encodeURIComponent(document.getElementById('asset').value)}}&timeframe=${{encodeURIComponent(document.getElementById('time').value)}}`);
            let d = await resp.json();
            
            document.getElementById('res').innerText = (d.signal == "UP" ? "ВВЕРХ" : "ВНИЗ");
            document.getElementById('res').style.color = d.signal == "UP" ? "#00ff66" : "#ff3344";
            document.getElementById('accuracy').style.display = 'block';
            document.getElementById('accuracy').innerText = "ACCURACY: " + d.accuracy + "%";
            
            let expVal = document.getElementById('exp').value;
            let expSeconds = expVal.includes("сек") ? parseInt(expVal) : parseInt(expVal) * 60;
            
            let wait = 10;
            let timerEl = document.getElementById('timer');
            let int = setInterval(() => {{
                timerEl.innerText = "ВХОД ЧЕРЕЗ: " + wait;
                if(wait-- <= 0) {{
                    clearInterval(int);
                    timerEl.innerText = "СДЕЛКА ОТКРЫТА!";
                    let expInt = setInterval(() => {{
                        timerEl.innerText = "ДО ЗАКРЫТИЯ: " + expSeconds;
                        if(expSeconds-- <= 0) {{ 
                            clearInterval(expInt); 
                            timerEl.innerText = "ЦИКЛ ЗАВЕРШЕН"; 
                            document.getElementById('martBtn').style.display = 'block';
                        }}
                    }}, 1000);
                }}
            }}, 1000);
        }}

        changeLang();
    </script>
    </html>
    """
