from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import random

app = FastAPI()

PAIRS = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "GBP/JPY": "GBPJPY=X",
    "EUR/JPY": "EURJPY=X", "AUD/JPY": "AUDJPY=X", "CHF/JPY": "CHFJPY=X",
    "NZD/USD": "NZDUSD=X"
}

@app.get("/analyze/{pair}")
async def analyze(pair: str):
    # Генерируем сигнал (ВВЕРХ/ВНИЗ) и вероятность для демонстрации
    is_up = random.choice([True, False])
    trend = "📈 ВВЕРХ" if is_up else "📉 ВНИЗ"
    prob = round(random.uniform(85.0, 99.0), 1)
    return {"trend": trend, "prob": prob}

@app.get("/", response_class=HTMLResponse)
async def index():
    options_pairs = "".join([f"<option value='{sym}'>{name}</option>" for name, sym in PAIRS.items()])
    times = ["5 сек", "15 сек", "30 сек", "1 мин", "2 мин", "3 мин", "4 мин", "5 мин", "6 мин", "7 мин", "8 мин", "9 мин", "10 мин"]
    options_times = "".join([f"<option value='{t}'>{t}</option>" for t in times])
    
    return f"""
    <html style="font-size:20px;"><body style="background:#0a0a0c; color:#fff; font-family:'Segoe UI', sans-serif; margin:0; padding:10px;">
        <div style="max-width:500px; margin:auto; background:#16161a; padding:25px; border-radius:20px; border:1px solid #333;">
            <h1 style="text-align:center; color:#00ffcc; font-size: 1.5rem;">QUANTUM CORE v4.2</h1>
            
            <label style="color:#888; font-size:0.7rem;">ВАЛЮТНАЯ ПАРА:</label>
            <select id="asset" style="width:100%; padding:12px; margin-bottom:15px; background:#1f1f24; color:#fff; border:1px solid #333; border-radius:10px;">{options_pairs}</select>
            
            <div style="display:flex; gap:10px; margin-bottom:15px;">
                <div style="flex:1;">
                    <label style="color:#888; font-size:0.7rem;">ТАЙМФРЕЙМ:</label>
                    <select id="candle" style="width:100%; padding:10px; background:#1f1f24; color:#fff; border:1px solid #333; border-radius:10px;">{options_times}</select>
                </div>
                <div style="flex:1;">
                    <label style="color:#888; font-size:0.7rem;">ЭКСПИРАЦИЯ:</label>
                    <select id="duration" style="width:100%; padding:10px; background:#1f1f24; color:#fff; border:1px solid #333; border-radius:10px;">{options_times}</select>
                </div>
            </div>
            
            <button id="btn" style="width:100%; padding:18px; background:linear-gradient(90deg, #00ffcc, #0088ff); border:none; border-radius:10px; font-weight:bold; cursor:pointer;" onclick="runAI()">ЗАПУСК АНАЛИЗА</button>
            
            <div id="res" style="display:none; margin-top:20px; padding:20px; text-align:center; border-radius:15px; background:#1f1f24; border:1px solid #444;">
                <div id="sig" style="font-size: 28px; font-weight: bold;"></div>
                <div style="color: #aaa; margin-top:5px;">Вероятность: <span id="prob"></span>%</div>
                <div id="timer-box" style="margin-top:10px; font-size: 1rem; color: #ffcc00;"></div>
                <button id="martingaleBtn" style="width:100%; padding:12px; margin-top:20px; background:transparent; border:1px solid #ffcc00; color:#ffcc00; border-radius:10px; cursor:pointer;" onclick="sendMartingale()">ПЕРЕКРЫТИЕ СДЕЛКИ</button>
            </div>
            
            <script>
            async function runAI() {{
                const asset = document.getElementById('asset').value;
                const btn = document.getElementById('btn');
                const mBtn = document.getElementById('martingaleBtn');
                
                btn.disabled = true; btn.innerHTML = "АНАЛИЗ...";
                
                mBtn.innerHTML = "ПЕРЕКРЫТИЕ СДЕЛКИ";
                mBtn.style.backgroundColor = "transparent";
                mBtn.style.borderColor = "#ffcc00"; 
                mBtn.style.color = "#ffcc00";
                mBtn.disabled = false;
                
                const res = await fetch('/analyze/' + asset);
                const data = await res.json();
                
                document.getElementById('res').style.display = 'block';
                document.getElementById('sig').innerHTML = data.trend;
                document.getElementById('sig').style.color = data.trend.includes('ВВЕРХ') ? '#00ff00' : '#ff4444';
                document.getElementById('prob').innerHTML = data.prob;
                
                let s = 9;
                const timer = setInterval(() => {{
                    s--;
                    document.getElementById('timer-box').innerHTML = "ВХОД ЧЕРЕЗ: " + s + " СЕК.";
                    if(s <= 0) {{
                        clearInterval(timer);
                        document.getElementById('timer-box').innerHTML = "ВХОДИТЕ В СДЕЛКУ СЕЙЧАС!";
                        btn.disabled = false;
                        btn.innerHTML = "ЗАПУСК АНАЛИЗА";
                    }}
                }}, 1000);
            }}

            function sendMartingale() {{
                const mBtn = document.getElementById('martingaleBtn');
                mBtn.innerHTML = "ПЕРЕКРЫТИЕ ОТПРАВЛЕНО";
                mBtn.style.backgroundColor = "#004400";
                mBtn.style.borderColor = "#00ff00";
                mBtn.style.color = "#00ff00";
                mBtn.disabled = true;
            }}
            </script>
        </div>
    </body></html>
    """
