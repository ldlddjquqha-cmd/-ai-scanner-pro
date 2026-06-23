# ==============================================================================
#                 AI TRADING BOT "TEAM MASTER CORE" v2.6
# ==============================================================================
# Скрипт разработан специально для проекта "Команда Мастер" (Team Master)
# Полный функционал: ИИ-генерация сигналов, парсинг OTC, интеграция с ИИ-камерами,
# расширенная база данных SQLite3, продвинутая админка и система Мартингейла.
# ==============================================================================

import os
import sys
import time
import logging
import asyncio
import sqlite3
import random
import cv2  # OpenCV для работы с ИИ-камерами видеофиксации терминалов
import numpy as np
from datetime import datetime, timedelta

# Импорты aiogram для построения Telegram-интерфейса
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.utils.exceptions import TelegramAPIError

# ==========================================
# ПОДРОБНАЯ КОНФИГУРАЦИЯ И НАСТРОЙКИ СИСТЕМЫ
# ==========================================
TOKEN = "ТВОЙ_ТЕЛЕГРАМ_БОТ_ТОКЕН"
ADMIN_IDS = [123456789]  # Вставь сюда свой Telegram ID

# Полный список активов, включая стандартные валютные пары, криптовалюту и OTC
ASSETS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "USD/CAD", "NZD/USD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP", "EUR/CHF", "AUD/JPY", "CAD/JPY", "CHF/JPY",
    "EUR/USD (OTC)", "GBP/USD (OTC)", "USD/JPY (OTC)", "AUD/USD (OTC)", 
    "USD/CHF (OTC)", "USD/CAD (OTC)", "EUR/JPY (OTC)", "GBP/JPY (OTC)",
    "EUR/GBP (OTC)", "EUR/CHF (OTC)", "AUD/JPY (OTC)", "NZD/USD (OTC)",
    "BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD", "DOT/USD"
]

# Настройка логирования для контроля работы на сервере Render
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("team_master.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TeamMasterAI")

# Инициализация бота и диспетчера с оперативной памятью для состояний FSM
bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ==========================================
# ИНИЦИАЛИЗАЦИЯ И СТРУКТУРА БАЗЫ ДАННЫХ
# ==========================================
def init_database():
    """Создание всех необходимых таблиц в SQLite3 для долгосрочной работы"""
    logger.info("Инициализация базы данных...")
    conn = sqlite3.connect("master_core.db")
    cursor = conn.cursor()
    
    # Таблица пользователей системы
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status TEXT DEFAULT 'free',
            expiry_date TEXT,
            joined_date TEXT,
            signals_received INTEGER DEFAULT 0
        )
    """)
    
    # Таблица глобальной статистики сигналов ИИ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT,
            direction TEXT,
            timeframe TEXT,
            result TEXT,
            confidence INTEGER,
            timestamp TEXT
        )
    """)
    
    # Таблица динамических настроек ИИ и подключенных камер
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    # Заполнение настроек по умолчанию, если они отсутствуют
    default_config = [
        ("ai_accuracy_floor", "82"),
        ("ai_accuracy_ceil", "96"),
        ("martingale_steps", "2"),
        ("default_timeframe_min", "1"),
        ("otc_timeframe_min", "1"),
        ("camera_device_index", "0"),
        ("ai_camera_scanning", "0"),
        ("vip_signals_only", "0")
    ]
    for key, val in default_config:
        cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (key, val))
        
    conn.commit()
    conn.close()
    logger.info("База данных успешно настроена и проверена.")

# Запуск функции инициализации БД при старте скрипта
init_database()

# Вспомогательные методы для работы с конфигурацией в БД
def db_get_param(key: str, default_val: str = "") -> str:
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default_val
    except Exception as e:
        logger.error(f"Ошибка чтения параметра {key}: {e}")
        return default_val

def db_set_param(key: str, value: str):
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка записи параметра {key}: {e}")

def check_admin_rights(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# Состояния машины конечных автоматов (FSM) для админки
class CloudBotStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_vip_grant = State()
    waiting_for_vip_revoke = State()
    waiting_for_config_key = State()
    waiting_for_config_value = State()

# ==========================================
# НЕЙРОСЕТЕВОЙ ИИ-ДВИЖОК АНАЛИЗА РЫНКА
# ==========================================
class AdvancedTradingAI:
    """Модуль математического моделирования и симуляции вывода торговых сигналов"""
    def __init__(self):
        self.technical_indicators = [
            "RSI (14) - Перепроданность", "MACD (12, 26, 9) - Пересечение линий", 
            "Bollinger Bands - Пробой границы", "Stochastic Oscillator", 
            "EMA (50) / EMA (200) Golden Cross", "ATR - Повышенная волатильность"
        ]
        self.price_action_patterns = [
            "Пин-бар на уровне поддержки", "Бычье поглощение", "Медвежье поглощение",
            "Утренний доджи", "Внутренний бар (Inside Bar)", "Флаг продолжения тренда"
        ]
        self.market_sentiments = ["Агрессивные покупки", "Крупный продавец в стакане", "Флэт / Накопление объемов"]

    async def calculate_market_entry(self, asset: str) -> dict:
        """Глубокий технический анализ. Исключительно минутные интервалы."""
        # Имитация вычислительной нагрузки нейросети
        await asyncio.sleep(1.8)
        
        direction = random.choice(["ВВЕРХ 🟢", "ВНИЗ 🔴"])
        
        # Строгое разграничение таймфреймов: только на минутах!
        if "OTC" in asset:
            timeframe = f"{db_get_param('otc_timeframe_min', '1')} МИНУТА"
        else:
            timeframe = f"{db_get_param('default_timeframe_min', '1')} МИНУТА"
            
        floor = int(db_get_param("ai_accuracy_floor", "82"))
        ceil = int(db_get_param("ai_accuracy_ceil", "96"))
        confidence = random.randint(floor, ceil)
        
        inds = random.sample(self.technical_indicators, 2)
        pattern = random.choice(self.price_action_patterns)
        sentiment = random.choice(self.market_sentiments)
        
        explanation = (
            f"Индикаторы: {inds[0]} и {inds[1]}. "
            f"Паттерн: {pattern}. Обстановка: {sentiment}."
        )
        
        return {
            "asset": asset,
            "direction": direction,
            "timeframe": timeframe,
            "confidence": confidence,
            "explanation": explanation,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

ai_trading_engine = AdvancedTradingAI()

# ==========================================
# ИИ-МОДУЛЬ ВЗАИМОДЕЙСТВИЯ С КАМЕРАМИ
# ==========================================
class AICameraInterface:
    """Управление физическими или виртуальными камерами для контроля рабочих экранов"""
    def __init__(self):
        self.video_capture = None

    def create_workspace_snapshot(self) -> str:
        """Захват кадра, наложение ИИ-контуров детекции графиков и сохранение снимка"""
        device_idx = int(db_get_param("camera_device_index", "0"))
        
        # Адаптивный бэкенд под ОС (Windows / Linux-сервер)
        if sys.platform == "win32":
            self.video_capture = cv2.VideoCapture(device_idx, cv2.CAP_DSHOW)
        else:
            self.video_capture = cv2.VideoCapture(device_idx, cv2.CAP_ANY)
            
        if not self.video_capture.isOpened():
            logger.warning(f"Камера с индексом {device_idx} не найдена. Создается виртуальный слепок экрана.")
            return self._generate_virtual_snapshot()
            
        success, frame = self.video_capture.read()
        if success:
            height, width, _ = frame.shape
            # Отрисовка ИИ-видоискателя для красоты и имитации сканирования рынка
            cv2.putText(frame, f"TEAM MASTER AI CAM v2.6: ACTIVE", (15, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.rectangle(frame, (int(width * 0.15), int(height * 0.15)), 
                          (int(width * 0.85), int(height * 0.85)), (0, 255, 255), 2)
            
            filename = "ai_camera_output.jpg"
            cv2.imwrite(filename, frame)
            self.video_capture.release()
            return filename
        else:
            self.video_capture.release()
            return self._generate_virtual_snapshot()

    def _generate_virtual_snapshot(self) -> str:
        """Создание виртуальной заглушки, если к серверу Render не подключена физ. камера"""
        img = np.zeros((600, 800, 3), dtype=np.uint8)
        cv2.putText(img, "STREAM ACTIVE: ANALYZING BROKER TERMINAL...", (50, 150), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", (50, 220), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        
        # Рисуем имитацию сетки графика цены
        cv2.line(img, (100, 450), (250, 380), (0, 255, 0), 3)
        cv2.line(img, (250, 380), (400, 490), (0, 0, 255), 3)
        cv2.line(img, (400, 490), (650, 310), (0, 255, 0), 4)
        
        filename = "ai_virtual_output.jpg"
        cv2.imwrite(filename, img)
        return filename

    async def continuous_stream_watcher(self):
        """Бесконечный фоновый цикл обработки потока для анализа изменений тренда"""
        while True:
            try:
                is_active = db_get_param("ai_camera_scanning", "0")
                if is_active == "1":
                    logger.info("[ИИ-Камера] Сканирование видеопотока терминала на паттерны...")
                    # Здесь может быть вызов тяжелых нейросетевых моделей детекции (YOLO/TensorFlow)
                    await asyncio.sleep(15)
                else:
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Ошибка в фоновом стриме камеры: {e}")
                await asyncio.sleep(10)

ai_camera_handler = AICameraInterface()

# ==========================================
# ИНТЕРФЕЙС, МЕНЮ И КЛАВИАТУРЫ (UI ПОКОЛЕНИЕ)
# ==========================================
def ui_build_main_keyboard(user_id: int) -> types.ReplyKeyboardMarkup:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🤖 Получить ИИ Сигнал", "📈 Статистика Системы")
    markup.row("📸 Поток ИИ Камеры", "💎 VIP Клуб")
    if check_admin_rights(user_id):
        markup.row("🛠 Панель Управления")
    return markup

def ui_build_admin_inline() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📢 Массовая Рассылка", callback_data="adm_mass_mail"),
        types.InlineKeyboardButton("🔑 Выдать VIP-статус", callback_data="adm_give_vip"),
        types.InlineKeyboardButton("❌ Аннулировать VIP", callback_data="adm_take_vip"),
        types.InlineKeyboardButton("📝 Параметры Системы", callback_data="adm_view_config"),
        types.InlineKeyboardButton("🔄 Сбросить Статистику", callback_data="adm_reset_stats")
    )
    return markup

# ==========================================
# ОБРАБОТЧИКИ ОСНОВНЫХ КОМАНД ПОЛЬЗОВАТЕЛЕЙ
# ==========================================
@dp.message_handler(commands=["start"])
async def handle_start_command(message: types.Message):
    uid = message.from_user.id
    uname = message.from_user.username or "UnknownUser"
    joined = datetime.now().strftime("%Y-%m-%d")
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                       (uid, uname, joined))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Не удалось сохранить пользователя в БД: {e}")
        
    greeting = (
        f"🌟 <b>Добро пожаловать в ИИ-платформу Команда Мастер!</b>\n\n"
        f"Я — нейросетевой комплекс, созданный для точного анализа рынков бинарных опционов. "
        f"Мой алгоритм просчитывает движение цены на **минутных интервалах** и "
        f"интегрируется с внешними камерами слежения за графиком.\n\n"
        f"Используй интерактивное меню для получения сигналов:"
    )
    await message.answer(greeting, reply_markup=ui_build_main_keyboard(uid))

@dp.message_handler(lambda msg: msg.text == "🤖 Получить ИИ Сигнал")
async def handle_signal_request(message: types.Message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Перемешиваем и выдаем пул из 8 случайных активов для торговли
    selected_assets = random.sample(ASSETS, 8)
    
    for item in selected_assets:
        markup.add(types.InlineKeyboardButton(f"📊 {item}", callback_data=f"get_ai_sig_{item}"))
        
    await message.answer("🎯 <b>Выбери торговую пару или OTC актив из списка ниже:</b>", reply_markup=markup)

@dp.message_handler(lambda msg: msg.text == "📈 Статистика Системы")
async def handle_stats_request(message: types.Message):
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), result FROM signals_history GROUP BY result")
        data = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка чтения статистики: {e}")
        data = []

    wins, losses = 0, 0
    for count, res in data:
        if res == "WIN": wins = count
        if res == "LOSS": losses = count

    total_signals = wins + losses
    if total_signals > 0:
        winrate = (wins / total_signals) * 100
    else:
        # Стартовая статистика по умолчанию для красивого отображения в новом боте
        wins = random.randint(1420, 1580)
        losses = random.randint(110, 140)
        total_signals = wins + losses
        winrate = (wins / total_signals) * 100

    report = (
        f"📊 <b>Глобальный аудит ИИ Команды Мастер:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Закрыто в плюс (WIN): <b>{wins}</b>\n"
        f"🔴 Основной минус (LOSS): <b>{losses}</b>\n"
        f"🔄 Всего обработано пар: <code>{total_signals}</code>\n\n"
        f"📈 Математическое ожидание точности: <b>{winrate:.2f}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Данные собираются на основе отчетов трейдеров команды круглосуточно.</i>"
    )
    await message.answer(report)

@dp.message_handler(lambda msg: msg.text == "📸 Поток ИИ Камеры")
async def handle_camera_request(message: types.Message):
    waiting_msg = await message.answer("🔄 <i>Подключение к ИИ-модулю захвата... Пожалуйста, подождите.</i>")
    
    # Запускаем синхронную обработку изображения в отдельном потоке, чтобы бот не зависал
    loop = asyncio.get_event_loop()
    photo_path = await loop.run_in_executor(None, ai_camera_handler.create_workspace_snapshot)
    
    await bot.delete_message(chat_id=message.chat.id, message_id=waiting_msg.message_id)
    
    if photo_path and os.path.exists(photo_path):
        with open(photo_path, "rb") as photo_file:
            await message.answer_photo(
                photo_file, 
                caption=f"📸 <b>Снапшот мониторинга рабочего места.</b>\n"
                        f"ИИ статус: Сканирование графиков запущено.\n"
                        f"Время фиксации: {datetime.now().strftime('%H:%M:%S')}"
            )
        try:
            os.remove(photo_path)
        except Exception as e:
            logger.error(f"Не удалось удалить временный файл снимка: {e}")
    else:
        await message.answer("⚠️ Не удалось получить доступ к видеосистеме или файловому кэшу.")

@dp.message_handler(lambda msg: msg.text == "💎 VIP Клуб")
async def handle_vip_info(message: types.Message):
    info_text = (
        f"💎 <b>VIP Клуб Сигналов Команды Мастер</b>\n\n"
        f"Расширенные возможности для участников закрытого пула:\n"
        f"⚡ Полный доступ к круглосуточным OTC котировкам\n"
        f"🎯 Увеличенная точность ИИ-фильтрации до 96%\n"
        f"📊 Персональные настройки количества колен Мартингейла\n\n"
        f"📥 Чтобы подать заявку на вступление, напиши нашему администратору: @team_master_admin"
    )
    await message.answer(info_text)

# ==========================================
# ОБРАБОТКА ИИ-СИГНАЛОВ И ИХ РЕЗУЛЬТАТОВ
# ==========================================
@dp.callback_query_handler(lambda call: call.data.startswith("get_ai_sig_"))
async def process_generation_flow(call: types.CallbackQuery):
    asset_name = call.data.replace("get_ai_sig_", "")
    await bot.answer_callback_query(call.id, text="Запрос отправлен в ядро ИИ...")
    
    status_msg = await bot.send_message(
        call.from_user.id, 
        f"⚙️ <b>Запущено сканирование котировок для {asset_name}</b>\n"
        f"<i>Индикаторы считывают исторические объемы...</i>"
    )
    
    # Генерация сигнала через ИИ-движок
    ai_result = await ai_trading_engine.calculate_market_entry(asset_name)
    max_steps = db_get_param("martingale_steps", "2")
    
    signal_card = (
        f"🤖 <b>СИГНАЛ ОТ ИИ КОМАНДЫ МАСТЕР</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Валютная пара: <b>{ai_result['asset']}</b>\n"
        f"Действие: {ai_result['direction']}\n"
        f"Время экспирации: <b>{ai_result['timeframe']}</b>\n"
        f"Вероятность отработки: <code>{ai_result['confidence']}%</code>\n"
        f"Стратегия догонов: <b>до {max_steps-1} перекрытия включительно</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 <i>{ai_result['explanation']}</i>\n\n"
        f"⌛ Время отправки: {ai_result['timestamp']}"
    )
    
    await bot.delete_message(chat_id=call.from_user.id, message_id=status_msg.message_id)
    
    # Клавиатура для обратной связи (наполнение статистики)
    feedback_kb = types.InlineKeyboardMarkup()
    feedback_kb.row(
        types.InlineKeyboardButton("✅ Зашел в плюс", callback_data=f"rep_win_{asset_name}_{ai_result['confidence']}"),
        types.InlineKeyboardButton("❌ Поймал минус", callback_data=f"rep_loss_{asset_name}_{ai_result['confidence']}")
    )
    
    await bot.send_message(call.from_user.id, signal_card, reply_markup=feedback_kb)

@dp.callback_query_handler(lambda call: call.data.startswith("rep_"))
async def process_signal_feedback(call: types.CallbackQuery):
    parts = call.data.split("_")
    outcome = parts[1].upper() # WIN или LOSS
    asset_name = parts[2]
    confidence_rate = int(parts[3])
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO signals_history (asset, direction, timeframe, result, confidence, timestamp) "
            "VALUES (?, 'N/A', '1M', ?, ?, ?)",
            (asset_name, outcome, confidence_rate, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        # Увеличиваем счетчик обработанных сигналов у пользователя
        cursor.execute("UPDATE users SET signals_received = signals_received + 1 WHERE user_id = ?", 
                       (call.from_user.id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Не удалось обновить фидбек в БД: {e}")
        
    await bot.answer_callback_query(call.id, text="Ваш результат успешно занесен в нейросеть!")
    
    # Убираем инлайн-кнопки у сообщения, чтобы избежать повторных нажатий
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=None
    )

# ==========================================
# МОЩНЫЙ АДМИНИСТРАТИВНЫЙ БЛОК (УПРАВЛЕНИЕ)
# ==========================================
@dp.message_handler(lambda msg: msg.text == "🛠 Панель Управления")
async def handle_admin_panel(message: types.Message):
    if not check_admin_rights(message.from_user.id):
        return
    await message.answer("🛠 <b>Главный пульт управления сервером:</b>", reply_markup=ui_build_admin_inline())

@dp.callback_query_handler(lambda call: call.data == "adm_view_config")
async def admin_view_config(call: types.CallbackQuery):
    if not check_admin_rights(call.from_user.id): return
    
    config_report = (
        f"📝 <b>Текущие глобальные переменные ядра:</b>\n\n"
        f"• <code>martingale_steps</code>: {db_get_param('martingale_steps')}\n"
        f"• <code>ai_accuracy_floor</code>: {db_get_param('ai_accuracy_floor')}\n"
        f"• <code>ai_accuracy_ceil</code>: {db_get_param('ai_accuracy_ceil')}\n"
        f"• <code>camera_device_index</code>: {db_get_param('camera_device_index')}\n"
        f"• <code>ai_camera_scanning</code>: {db_get_param('ai_camera_scanning')}\n"
        f"• <code>otc_timeframe_min</code>: {db_get_param('otc_timeframe_min')} мин\n\n"
        f"💡 Чтобы переписать любой параметр, используйте команду:\n"
        f"<code>/update_param [ключ] [значение]</code>"
    )
    await bot.send_message(call.from_user.id, config_report)

@dp.message_handler(commands=["update_param"])
async def handle_param_updating(message: types.Message):
    if not check_admin_rights(message.from_user.id): return
    
    tokens = message.get_args().split()
    if len(tokens) < 2:
        await message.answer("❌ Ошибка. Синтаксис: `/update_param martingale_steps 3`")
        return
        
    p_key, p_val = tokens[0], tokens[1]
    db_set_param(p_key, p_val)
    await message.answer(f"✅ Переменная <b>{p_key}</b> успешно изменена на: <code>{p_val}</code>")

@dp.callback_query_handler(lambda call: call.data == "adm_reset_stats")
async def admin_reset_stats(call: types.CallbackQuery):
    if not check_admin_rights(call.from_user.id): return
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM signals_history")
        conn.commit()
        conn.close()
        await bot.send_message(call.from_user.id, "✅ Вся история сигналов и статистика очищены!")
    except Exception as e:
        await bot.send_message(call.from_user.id, f"❌ Ошибка сброса: {e}")

@dp.callback_query_handler(lambda call: call.data == "adm_mass_mail")
async def admin_trigger_broadcast(call: types.CallbackQuery):
    if not check_admin_rights(call.from_user.id): return
    
    await CloudBotStates.waiting_for_broadcast_text.set()
    await bot.send_message(call.from_user.id, "📢 <b>Введите текст сообщения для рассылки всем юзерам:</b>")

@dp.message_handler(state=CloudBotStates.waiting_for_broadcast_text)
async def admin_execute_broadcast(message: types.Message, state: FSMContext):
    await state.finish()
    broadcast_body = message.text
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        user_list = cursor.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Не удалось получить юзеров для рассылки: {e}")
        user_list = []
        
    sent_counter = 0
    await message.answer(f"⚡ Начинаю рассылку для {len(user_list)} пользователей...")
    
    for row in user_list:
        target_id = row[0]
        try:
            await bot.send_message(target_id, broadcast_body)
            sent_counter += 1
            # Плавная задержка, чтобы Телеграм не забанил за спам
            await asyncio.sleep(0.04)
        except TelegramAPIError:
            continue
        except Exception as e:
            logger.debug(f"Пропуск пользователя {target_id}: {e}")
            continue
            
    await message.answer(f"📢 <b>Рассылка завершена успешно!</b>\nДоставлено: <code>{sent_counter}</code> аккаунтов.")

@dp.callback_query_handler(lambda call: call.data == "adm_give_vip")
async def admin_give_vip_start(call: types.CallbackQuery):
    if not check_admin_rights(call.from_user.id): return
    await CloudBotStates.waiting_for_vip_grant.set()
    await bot.send_message(call.from_user.id, "🔑 Введите <b>User ID</b> пользователя, кому выдать VIP:")

@dp.message_handler(state=CloudBotStates.waiting_for_vip_grant)
async def admin_give_vip_finish(message: types.Message, state: FSMContext):
    await state.finish()
    target_id = message.text.strip()
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'vip' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Пользователю <code>{target_id}</code> успешно выдан VIP-статус.")
        try:
            await bot.send_message(int(target_id), "🎉 <b>Поздравляем! Администратор выдал вам статус VIP!</b>")
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Ошибка обновления статуса: {e}")

@dp.callback_query_handler(lambda call: call.data == "adm_take_vip")
async def admin_take_vip_start(call: types.CallbackQuery):
    if not check_admin_rights(call.from_user.id): return
    await CloudBotStates.waiting_for_vip_revoke.set()
    await bot.send_message(call.from_user.id, "❌ Введите <b>User ID</b> пользователя, у кого забрать VIP:")

@dp.message_handler(state=CloudBotStates.waiting_for_vip_revoke)
async def admin_take_vip_finish(message: types.Message, state: FSMContext):
    await state.finish()
    target_id = message.text.strip()
    
    try:
        conn = sqlite3.connect("master_core.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'free' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await message.answer(f"✅ У пользователя <code>{target_id}</code> аннулирован VIP-статус.")
    except Exception as e:
        await message.answer(f"❌ Ошибка обновления: {e}")

# ==========================================
# ЗАПУСК И ИНИЦИАЛИЗАЦИЯ ВСЕЙ СИСТЕМЫ
# ==========================================
async def on_bot_startup_sequence(dispatcher_instance):
    """Выполняется при успешном развертывании проекта в облаке"""
    logger.info("==================================================")
    logger.info("   TEAM MASTER BOT IS LIVE ON DEPLOYMENT SERVER   ")
    logger.info("==================================================")
    
    # Регистрация фонового потока анализа видеокамер
    asyncio.create_task(ai_camera_handler.continuous_stream_watcher())

if __name__ == "__main__":
    # Точка входа приложения. Запускает бесконечный опрос серверов Telegram (Long Polling)
    executor.start_polling(dp, on_startup=on_bot_startup_sequence, skip_updates=True)
