
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import yfinance as yf
import json

app = FastAPI()

# Список реальных тикеров (символов) для Yahoo Finance
# AAPL = Apple, TSLA = Tesla, AMD = AMD, MSFT = Microsoft
SYMBOLS = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "AMD": "Advanced Micro Devices",
    "MSFT": "Microsoft"
}

@app.get("/analyze/{symbol}")
async def analyze(symbol: str):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        last_price = data['Close'].iloc[-1]
        open_price = data['Open'].iloc[-1]
        
        # Логика: если цена выше открытия — сигнал ВВЕРХ, если ниже — ВНИЗ
        trend = "ВВЕРХ" if last_price >= open_price else "ВНИЗ"
        prob = round(85 + (abs(last_price - open_price) / open_price) * 1000, 1)
        
        return {"trend": trend, "prob": min(prob, 99.9)}
    except:
        return {"trend": "Ошибка", "prob": 0}

# ... (далее идет HTML-код интерфейса) ...
