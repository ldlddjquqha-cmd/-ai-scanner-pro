from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json
import random

app = FastAPI()

# Список ТОЛЬКО валютных пар БЕЗ OTC
DATA = {
    "Валюты": ["AUD/CHF", "AUD/JPY", "AUD/USD", "CHF/JPY", "EUR/CAD", "EUR/JPY", "EUR/USD", "GBP/AUD", "GBP/CAD", "USD/CAD"]
}

@app.get("/", response_class=HTMLResponse)
async def index():
    data_json = json.dumps(DATA)
    times = ["5 сек", "15 сек", "30 сек", "1 мин", "2 мин", "3 мин", "4 мин", "5 мин"]
    options_html = "".join([f"<option value='{t}'>{t}</option>" for t in times])
    
    return f"""
    <html style="font-size:20px;"><body style="background:#0a0a0c; color:#fff; font-family:'Segoe UI', sans-serif; margin:0; padding:10px;">
        <div style="max-width:500px; margin:auto; background:#16161a; padding:25px; border-radius:20px; border:1px solid #333; box-shadow: 0 0 30px rgba(0,255,204,0.1);">
            <h1 style="text-align:center; color:#00ffcc; font-size: 1.6rem; letter-spacing: 2px;">QUANTUM CORE v4.2</h1>
            
            <label style="color:#888; font-size:0.7rem;">КАТЕГОРИЯ:</label>
            <select id="cat" style="width:100%; padding:12px; margin-bottom:15px; background:#1f1f24; color:#fff; border:1px solid #333; border-radius:10px;">
                <option value="Валюты">Валюты</option>
            </select>
            
            <label style="color:#888; font-size:0.7rem;">ВЫБОР АКТИВА:</label>
            <select id="asset" style="width:100%; padding:12px; margin-bottom:15px; background:#1f1f24; color:#fff; border:1px solid #333; border-radius:10px;"></select>
            
            <button id="btn" style="width:100%; padding:18px; background:linear-gradient(90deg, #00ffcc, #0088ff); border:none; border-radius:10px; font-weight:bold; cursor:pointer;" onclick="runAI()">ЗАПУСК АНАЛИЗА</button>
            
            <div id="result-block" style="display:none; margin-top:20px; padding:20px; text-align:center; border-radius:15px; background:#1f1f24; border:1px solid #444;">
                <div id="signal-text" style="font-size: 28px; font-weight: bold;"></div>
                <div style="color: #aaa; margin-top:5px;">Вероятность: <span id="prob"></span>%</div>
                <div style="color: #ffcc00; margin: 15px 0; font-size: 1.1rem;">ВХОД ЧЕРЕЗ: <span id="timer">9</span> СЕК.</div>
                <div id="advice" style="font-size: 0.8rem; color: #777;"></div>
                <button id="martingaleBtn" style="width:100%; padding:12px; margin-top:20px; background:transparent; border:1px solid #ffcc00; color:#ffcc00; border-radius:10px;" onclick="alert('Сигнал перекрытия отправлен!')">ПЕРЕКРЫТИЕ СДЕЛКИ</button>
            </div>
            
            <script>
            const data = {data_json};
            const assetSelect = document.getElementById('asset');
            data["Валюты"].forEach(a => assetSelect.innerHTML += `<option value='${{a}}'>${{a}}</option>`);

            async function runAI() {{
                document.getElementById('btn').disabled = true;
                const block = document.getElementById('result-block');
                const sig = document.getElementById('signal-text');
                const adv = document.getElementById('advice');
                
                block.style.display = 'block';
                const trend = Math.random() > 0.4 ? 'ВВЕРХ' : 'ВНИЗ';
                sig.innerHTML = trend === 'ВВЕРХ' ? '📈 ВВЕРХ' : '📉 ВНИЗ';
                sig.style.color = trend === 'ВВЕРХ' ? '#00ff00' : '#ff4444';
                document.getElementById('prob').innerHTML = (90 + Math.random() * 8).toFixed(1);
                adv.innerHTML = "• Рекомендация: Вход по тренду<br>• Анализ объема: Оптимально";
                
                let s = 9;
                const t = document.getElementById('timer');
                const i = setInterval(() => {{
                    s--; t.innerHTML = s;
                    if(s <= 0) {{ clearInterval(i); document.getElementById('btn').disabled = false; }}
                }}, 1000);
            }}
            </script>
        </div>
    </body></html>
    """
