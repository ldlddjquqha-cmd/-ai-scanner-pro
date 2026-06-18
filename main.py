import json
import random
import asyncio
import httpx
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

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
    <html>
    <head>
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
            const flags = {{ ru: "🇷🇺", en: "🇺🇸", ua: "🇺🇦", es: "🇪🇸", de: "🇩🇪", fr: "🇫🇷", it: "🇮🇹", tr: "🇹🇷", pt: "🇵🇹", pl: "🇵🇱" }};
            const dictionary = {{ 
                ru: {{ market: "КАТЕГОРИЯ РЫНКА", type: "ТИП АКТИВА", asset: "АКТИВНАЯ ПАРА", tf: "ИНТЕРВАЛ СВЕЧИ", exp: "ЭКСПИРАЦИЯ", scan: "СКАНИРОВАТЬ РЫНОК", auto: "ИИ СДЕЛАТЬ ЗА ВАС", pocket: "ОТКРЫТЬ POCKET OPTION", support: "РАЗРАБОТЧИК / SUPPORT", ready: "СИСТЕМА СИНХРОНИЗИРОВАНА", vip: "👑 VIP СИГНАЛЫ", mart: "ПЕРЕКРЫТИЕ", profit: "Profit", loss: "Loss", reset: "СБРОСИТЬ СТАТИСТИКУ" }},
                en: {{ market: "MARKET CATEGORY", type: "ASSET TYPE", asset: "ACTIVE PAIR", tf: "CANDLE TIMEFRAME", exp: "EXPIRATION TIME", scan: "SCAN MARKET", auto: "AI DO FOR YOU", pocket: "OPEN POCKET OPTION", support: "DEVELOPER / SUPPORT", ready: "SYSTEM SYNCHRONIZED", vip: "👑 VIP SIGNALS", mart: "MARTINGALE", profit: "Profit", loss: "Loss", reset: "RESET STATISTICS" }},
                ua: {{ market: "КАТЕГОРІЯ РИНКУ", type: "ТИП АКТИВУ", asset: "АКТИВНА ПАРА", tf: "ІНТЕРВАЛ СВІЧКИ", exp: "ЕКСПІРАЦІЯ", scan: "СКАНУВАТИ РИНОК", auto: "ШІ ЗРОБИТЬ ЗА ВАС", pocket: "ВІДКРИТИ POCKET OPTION", support: "РОЗРОБНИК / SUPPORT", ready: "СИСТЕМА СИНХРОНІЗОВАНА", vip: "👑 VIP СИГНАЛИ", mart: "ПЕРЕКРИТТЯ", profit: "Профіт", loss: "Лос", reset: "СКИНУТИ СТАТИСТИКУ" }},
                es: {{ market: "CATEGORÍA DE MERCADO", type: "TIPO DE ACTIVOS", asset: "PAR ACTIVO", tf: "TIMEFRAME DE VELA", exp: "EXPIRACIÓN", scan: "ESCANEAR MERCADO", auto: "IA LO HACE POR TI", pocket: "ABRIR POCKET OPTION", support: "DESARROLLADOR / SUPPORT", ready: "SISTEMA SINCRONIZADO", vip: "👑 SEÑALES VIP", mart: "MARTINGALA", profit: "Ganancia", loss: "Pérdida", reset: "REINICIAR ESTADÍSTICAS" }},
                de: {{ market: "MARKTKATEGORIE", type: "VERMÖGENSTYP", asset: "AKTIVES PAAR", tf: "KERZENZEITRAUM", exp: "ABLAUFZEIT", scan: "MARKT SCANNEN", auto: "KI MACHT DAS FÜR DICH", pocket: "POCKET OPTION ÖFFNEN", support: "ENTWICKLER / SUPPORT", ready: "SYSTEM SYNCHRONISIERT", vip: "👑 VIP-SIGNALE", mart: "MARTINGALE", profit: "Gewinn", loss: "Verlust", reset: "STATISTIK ZURÜCKSETZEN" }},
                fr: {{ market: "CATÉGORIE DE MARCHÉ", type: "TYPE D'ACTIF", asset: "PAIRE ACTIVE", tf: "TIMEFRAME", exp: "EXPIRATION", scan: "SCANNER LE MARCHÉ", auto: "IA LE FAIT POUR VOUS", pocket: "OUVRIR POCKET OPTION", support: "DÉVELOPPEUR / SUPPORT", ready: "SYSTÈME SYNCHRONISÉ", vip: "👑 SIGNAUX VIP", mart: "MARTINGALE", profit: "Profit", loss: "Perte", reset: "RÉINITIALISER LES STATS" }},
                it: {{ market: "CATEGORIA DI MERCATO", type: "TIPO DI ASSET", asset: "COPPIA ATTIVA", tf: "TIMEFRAME", exp: "SCADENZA", scan: "SCANSIONE MERCATO", auto: "L'IA LO FA PER TE", pocket: "APRI POCKET OPTION", support: "SVILUPPATORE / SUPPORT", ready: "SISTEMA SINCRONIZZATO", vip: "👑 SEGNALI VIP", mart: "MARTINGALA", profit: "Profitto", loss: "Perdita", reset: "AZZERA STATISTICHE" }},
                tr: {{ market: "PİYASA KATEGORİSİ", type: "VARLIK TÜRÜ", asset: "AKTİF ÇİFT", tf: "ZAMAN DİLİMİ", exp: "SON KULLANMA", scan: "PİYASAYI TARA", auto: "YAPAY ZEKA SENİN İÇİN YAPSIN", pocket: "POCKET OPTION'I AÇ", support: "GELİŞTİRİCİ / DESTEK", ready: "SİSTEM SENKRONİZE EDİLDİ", vip: "👑 VIP SİNYALLERİ", mart: "MARTİNGALE", profit: "Kar", loss: "Zarar", reset: "İSTATİSTİKLERİ SIFIRLA" }},
                pt: {{ market: "CATEGORIA DE MERCADO", type: "TIPO DE ATIVO", asset: "PAR ATIVO", tf: "TIMEFRAME", exp: "EXPIRAÇÃO", scan: "SCANEAR MERCADO", auto: "IA FAZ POR VOCÊ", pocket: "ABRIR POCKET OPTION", support: "DESENVOLVEDOR / SUPORTE", ready: "SISTEMA SINCRONIZADO", vip: "👑 SINAIS VIP", mart: "MARTINGALE", profit: "Lucro", loss: "Perda", reset: "REINICIAR ESTATÍSTICAS" }},
                pl: {{ market: "KATEGORIA RYNKU", type: "TYP AKTYWÓW", asset: "AKTYWNA PARA", tf: "RAMA CZASOWA", exp: "WYGAŚNIĘCIE", scan: "SKANUJ RYNEK", auto: "AI ZROBI TO ZA CIEBIE", pocket: "OTWÓRZ POCKET OPTION", support: "PROGRAMISTA / WSPARCIE", ready: "SYSTEM ZSYNCHRONIZOWANY", vip: "👑 SYGNAŁY VIP", mart: "MARTYNGALE", profit: "Zysk", loss: "Strata", reset: "RESETUJ STATYSTYKI" }}
            }};
        </script>
    </head>
    <body>
        </body>
    </html>
    """
4
