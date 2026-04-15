import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import httpx
from backend.config import get_settings
from loguru import logger
import sys
import io
import re
import base64
from datetime import datetime
from pathlib import Path

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
logger.add("logs/bot.log", rotation="500 MB", level="DEBUG")

settings = get_settings()

# Initialize bot and dispatcher
bot = Bot(token=settings.telegram_bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# API endpoint
API_URL = f"http://localhost:{settings.api_port}/api/v1"

SUPPORTED_LANGUAGES = {"ru", "en"}


TRANSLATIONS = {
    "ru": {
        "menu_analyze": "🔍 Проверить сообщение",
        "menu_my_stats": "📊 Моя статистика",
        "menu_global_stats": "📈 Общая статистика",
        "menu_logs": "📋 Логи бота",
        "menu_help": "❓ Помощь",
        "menu_about": "ℹ️ О проекте",
        "main_menu_title": "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        "start_welcome": """🛡️ <b>Добро пожаловать в ScamGuard AI, {user_name}!</b>

Я защищаю вас от онлайн-мошенников! 🚨

<b>🤖 Что я умею:</b>
• Анализирую подозрительные сообщения
• Проверяю вложения и файлы
• Даю оценку риска 0-100
• Объясняю, почему сообщение выглядит опасным

<b>⚡ Как это работает:</b>
1️⃣ Получили подозрительное сообщение или файл?
2️⃣ Перешлите его мне
3️⃣ Я сделаю быструю проверку
4️⃣ При необходимости запущу глубокий AI анализ

<b>Поддерживается:</b>
• Пересланные сообщения
• Обычный текст
• Фотографии
• Файлы
• Ссылки на объявления

Просто отправьте сообщение или нажмите кнопку ниже.""",
        "analyze_prompt": """📨 <b>Перешлите подозрительное сообщение</b>

Поддерживаются:
• Пересланные сообщения
• Текст
• Фотографии
• Файлы
• Ссылки

Или <code>/cancel</code> для отмены.""",
        "help_text": """📖 <b>Справка</b>

<b>Команды:</b>
/start - Главное меню
/analyze - Проверить сообщение
/history - История проверок
/stats - Статистика
/logs - Логи бота
/cancel - Отмена

<b>Режимы анализа:</b>
⚡ Быстрая проверка - мгновенно по правилам
🧠 Глубокий AI анализ - детальная проверка текста и контекста

<b>Что мы ищем:</b>
• Предоплату и давление
• Подозрительные ссылки и файлы
• Манипуляции и срочность
• Типичные паттерны мошенников

Это инструмент помощи, окончательное решение остаётся за вами.""",
        "about_text": """🛡️ <b>О проекте ScamGuard AI</b>

ScamGuard AI помогает выявлять онлайн-мошенничество в сообщениях и объявлениях.

<b>Что внутри:</b>
• Rule Engine
• AI анализ через Gemini
• Анализ вложений и фото
• История проверок и статистика

<b>Цель:</b>
Остановить мошенничество до того, как пользователь потеряет деньги или данные.""",
        "loading_my_stats": "Загружаю вашу статистику...",
        "loading_stats": "Загружаю статистику...",
        "loading_logs": "Загружаю логи...",
        "stats_empty": "📊 <b>Ваша статистика</b>\n\nУ вас пока нет проверок.\nНачните с кнопки проверки сообщения.",
        "stats_error": "❌ Ошибка при получении статистики",
        "generic_error": "❌ Произошла ошибка",
        "cancelled": "❌ Операция отменена",
        "history_empty": "📋 У вас пока нет истории проверок\n\nНачните с команды /analyze",
        "history_title": "📋 <b>Ваша история проверок</b> (последние {count}):\n\n",
        "history_error": "❌ Ошибка при получении истории",
        "history_unknown": "неизвестный источник",
        "my_stats_title": "📊 <b>Ваша статистика</b>",
        "my_stats_total": "<b>Всего проверок:</b> {total}",
        "my_stats_distribution": "<b>Распределение рисков:</b>",
        "my_stats_high": "🔴 Высокий: {count} ({percent}%)",
        "my_stats_medium": "🟡 Средний: {count} ({percent}%)",
        "my_stats_low": "🟢 Низкий: {count} ({percent}%)",
        "my_stats_avg": "<b>Средний риск:</b> {avg:.1f}/100",
        "my_stats_recent": "<b>Последние проверки:</b>",
        "my_stats_recent_item": "{idx}. {emoji} Риск {score}/100 ({date})",
        "my_stats_saved": "✅ <b>Вы избежали {count} мошенничеств!</b>",
        "global_stats_title": "📈 <b>Общая статистика ScamGuard AI</b>",
        "global_stats_total": "<b>Всего проверок:</b> {total}",
        "global_stats_avg": "<b>Средний риск:</b> {avg:.1f}/100",
        "global_stats_distribution": "<b>Распределение:</b>",
        "global_stats_low": "🟢 Низкий риск: {count}",
        "global_stats_medium": "🟡 Средний риск: {count}",
        "global_stats_high": "🔴 Высокий риск: {count}",
        "global_stats_savings": "💰 <b>Предотвращено потерь:</b> ~${amount}",
        "global_stats_flags": "<b>Топ красные флаги:</b>\n• Подозрительная цена\n• Требование предоплаты\n• Срочность и давление\n• Отсутствие контактов",
        "global_stats_mission": "🎯 <b>Миссия:</b> Защитить людей от мошенников!",
        "quick_status": "⚡ <b>Быстрая проверка...</b>\n▰▰▰▱▱▱▱▱▱▱ 30%\n⏳ Проверяю по 80+ правилам",
        "quick_error": "❌ <b>Ошибка быстрой проверки:</b>\n{detail}",
        "quick_timeout": "❌ <b>Быстрая проверка не удалась</b>\n\nПревышено время ожидания.\nПопробуйте позже.",
        "analysis_error": "❌ <b>Произошла ошибка</b>\n\nДетали: <code>{detail}</code>",
        "quick_result_header": "БЫСТРАЯ ПРОВЕРКА",
        "risk_low": "НИЗКИЙ РИСК",
        "risk_medium": "СРЕДНИЙ РИСК",
        "risk_high": "ВЫСОКИЙ РИСК",
        "status_label": "Статус: {level}",
        "risk_score_label": "Оценка риска: {score}/100",
        "problems_found": "Найдено проблем: {count}",
        "detected_items": "Обнаружено:",
        "recommendation_label": "Рекомендация:",
        "quick_advice_high": "Подозрительное сообщение. Рекомендую провести глубокий AI анализ для точного вердикта.",
        "quick_advice_medium": "Есть подозрительные признаки. Хотите глубокий анализ?",
        "quick_advice_low": "Явных признаков мошенничества нет, но будьте бдительны.",
        "deep_button": "Глубокий AI анализ",
        "check_more_button": "Проверить ещё",
        "home_button": "Главная",
        "deep_offer": "Хотите узнать больше?\n\nЗапустите полный AI анализ с Gemini:\n- Глубокое понимание контекста\n- Определение тактик манипуляции\n- Анализ фото (если есть)\n- Точный вердикт за 10-15 секунд",
    },
    "en": {
        "menu_analyze": "🔍 Check message",
        "menu_my_stats": "📊 My stats",
        "menu_global_stats": "📈 Global stats",
        "menu_logs": "📋 Bot logs",
        "menu_help": "❓ Help",
        "menu_about": "ℹ️ About",
        "main_menu_title": "🏠 <b>Main menu</b>\n\nChoose an action:",
        "start_welcome": """🛡️ <b>Welcome to ScamGuard AI, {user_name}!</b>

I help protect you from online scams. 🚨

<b>🤖 What I can do:</b>
• Analyze suspicious messages
• Check attachments and files
• Return a 0-100 risk score
• Explain why a message looks dangerous

<b>⚡ How it works:</b>
1️⃣ You get a suspicious message or file
2️⃣ Forward it to me
3️⃣ I run a quick check
4️⃣ If needed, I run a deeper AI analysis

<b>Supported inputs:</b>
• Forwarded messages
• Plain text
• Photos
• Files
• Listing URLs

Just send a message or use the button below.""",
        "analyze_prompt": """📨 <b>Forward a suspicious message</b>

Supported:
• Forwarded messages
• Text
• Photos
• Files
• Links

Or use <code>/cancel</code> to stop.""",
        "help_text": """📖 <b>Help</b>

<b>Commands:</b>
/start - Main menu
/analyze - Check a message
/history - Analysis history
/stats - Statistics
/logs - Bot logs
/cancel - Cancel

<b>Analysis modes:</b>
⚡ Quick check - instant rule-based scan
🧠 Deep AI analysis - more detailed text and context review

<b>What we look for:</b>
• Prepayment and pressure
• Suspicious links and files
• Manipulation and urgency
• Common scam patterns

This is an assistant tool. Final judgment is still yours.""",
        "about_text": """🛡️ <b>About ScamGuard AI</b>

ScamGuard AI helps detect online fraud in messages and listings.

<b>What it uses:</b>
• Rule Engine
• Gemini AI analysis
• Attachment and photo checks
• Analysis history and statistics

<b>Goal:</b>
Stop scams before the user loses money or personal data.""",
        "loading_my_stats": "Loading your stats...",
        "loading_stats": "Loading statistics...",
        "loading_logs": "Loading logs...",
        "stats_empty": "📊 <b>Your stats</b>\n\nYou have no checks yet.\nStart with the message analysis button.",
        "stats_error": "❌ Failed to load statistics",
        "generic_error": "❌ An error occurred",
        "cancelled": "❌ Operation cancelled",
        "history_empty": "📋 You have no analysis history yet\n\nStart with /analyze",
        "history_title": "📋 <b>Your analysis history</b> (latest {count}):\n\n",
        "history_error": "❌ Failed to load history",
        "history_unknown": "unknown source",
        "my_stats_title": "📊 <b>Your stats</b>",
        "my_stats_total": "<b>Total checks:</b> {total}",
        "my_stats_distribution": "<b>Risk distribution:</b>",
        "my_stats_high": "🔴 High: {count} ({percent}%)",
        "my_stats_medium": "🟡 Medium: {count} ({percent}%)",
        "my_stats_low": "🟢 Low: {count} ({percent}%)",
        "my_stats_avg": "<b>Average risk:</b> {avg:.1f}/100",
        "my_stats_recent": "<b>Recent checks:</b>",
        "my_stats_recent_item": "{idx}. {emoji} Risk {score}/100 ({date})",
        "my_stats_saved": "✅ <b>You may have avoided {count} scams!</b>",
        "global_stats_title": "📈 <b>ScamGuard AI global stats</b>",
        "global_stats_total": "<b>Total checks:</b> {total}",
        "global_stats_avg": "<b>Average risk:</b> {avg:.1f}/100",
        "global_stats_distribution": "<b>Distribution:</b>",
        "global_stats_low": "🟢 Low risk: {count}",
        "global_stats_medium": "🟡 Medium risk: {count}",
        "global_stats_high": "🔴 High risk: {count}",
        "global_stats_savings": "💰 <b>Estimated losses prevented:</b> ~${amount}",
        "global_stats_flags": "<b>Top red flags:</b>\n• Suspicious price\n• Prepayment request\n• Urgency and pressure\n• Missing contact details",
        "global_stats_mission": "🎯 <b>Mission:</b> Protect people from scammers!",
        "quick_status": "⚡ <b>Quick check...</b>\n▰▰▰▱▱▱▱▱▱▱ 30%\n⏳ Checking against 80+ rules",
        "quick_error": "❌ <b>Quick check failed:</b>\n{detail}",
        "quick_timeout": "❌ <b>Quick check failed</b>\n\nThe request timed out.\nPlease try again later.",
        "analysis_error": "❌ <b>An error occurred</b>\n\nDetails: <code>{detail}</code>",
        "quick_result_header": "QUICK CHECK",
        "risk_low": "LOW RISK",
        "risk_medium": "MEDIUM RISK",
        "risk_high": "HIGH RISK",
        "status_label": "Status: {level}",
        "risk_score_label": "Risk score: {score}/100",
        "problems_found": "Problems found: {count}",
        "detected_items": "Detected:",
        "recommendation_label": "Recommendation:",
        "quick_advice_high": "This looks suspicious. I recommend a deep AI analysis for a stronger verdict.",
        "quick_advice_medium": "There are suspicious signs. Do you want a deeper analysis?",
        "quick_advice_low": "No obvious scam indicators found, but stay careful.",
        "deep_button": "Deep AI analysis",
        "check_more_button": "Check another",
        "home_button": "Home",
        "deep_offer": "Want more detail?\n\nRun the full Gemini-powered AI analysis:\n- Better context understanding\n- Manipulation tactic detection\n- Photo analysis (if available)\n- More precise verdict in 10-15 seconds",
    },
}


def get_user_language(obj) -> str:
    """Bot replies in Russian for all users."""
    return "ru"


def t(lang: str, key: str, **kwargs) -> str:
    """Translate a UI message with fallback to Russian."""
    bucket = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])
    template = bucket.get(key) or TRANSLATIONS["ru"].get(key, key)
    return template.format(**kwargs) if kwargs else template


def compact_risk_bar(score: int) -> str:
    """Return a short visual risk bar."""
    filled = max(0, min(10, score // 10))
    return "▰" * filled + "▱" * (10 - filled)


def risk_badge(score: int, lang: str) -> str:
    """Return localized risk badge."""
    if score >= 60:
        return f"🔴 {t(lang, 'risk_high')}"
    if score >= 30:
        return f"🟡 {t(lang, 'risk_medium')}"
    return f"🟢 {t(lang, 'risk_low')}"


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for Telegram HTML parse mode.

    Telegram HTML mode only needs escaping for: < > &
    This keeps parentheses, dashes, underscores, etc. intact — much more readable.
    """
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def safe_markdown_text(text: str) -> str:
    """
    Safely escape text for Telegram HTML parse mode.
    Use this for ANY dynamic content from user/AI.
    """
    return escape_html(text)


class AnalysisStates(StatesGroup):
    """States for analysis flow"""
    waiting_for_message = State()
    waiting_deep_confirmation = State()  # Waiting for user to confirm deep analysis


# Опасные расширения файлов
DANGEROUS_FILE_EXTENSIONS = {
    # Исполняемые файлы (ВЫСОКИЙ РИСК)
    '.exe': 'executable_windows',
    '.msi': 'installer_windows',
    '.bat': 'batch_script',
    '.cmd': 'command_script',
    '.ps1': 'powershell_script',
    '.vbs': 'vbscript',
    '.js': 'javascript',
    '.scr': 'screensaver_executable',

    # Мобильные приложения
    '.apk': 'android_app',
    '.aab': 'android_app_bundle',

    # Документы с макросами
    '.docm': 'word_with_macros',
    '.xlsm': 'excel_with_macros',
    '.pptm': 'powerpoint_with_macros',

    # Архивы
    '.zip': 'archive',
    '.rar': 'archive',
    '.7z': 'archive',

    # Другие
    '.pdf': 'document',
    '.iso': 'disk_image',
    '.dmg': 'macos_installer',
}

# Критически опасные файлы (мгновенный high risk)
CRITICAL_FILE_TYPES = {
    'executable_windows', 'batch_script', 'command_script',
    'powershell_script', 'vbscript', 'screensaver_executable',
    'android_app', 'android_app_bundle',
}

# Подозрительные файлы (medium risk)
SUSPICIOUS_FILE_TYPES = {
    'word_with_macros', 'excel_with_macros', 'powerpoint_with_macros',
    'javascript', 'archive', 'disk_image', 'macos_installer',
}


def create_main_menu(lang: str = "ru"):
    """Create main menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, "menu_analyze"), callback_data="analyze")
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_my_stats"), callback_data="my_stats"),
            InlineKeyboardButton(text=t(lang, "menu_global_stats"), callback_data="global_stats")
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_logs"), callback_data="bot_logs"),
            InlineKeyboardButton(text=t(lang, "menu_help"), callback_data="help")
        ],
        [
            InlineKeyboardButton(text=t(lang, "menu_about"), callback_data="about")
        ]
    ])
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    user_name = message.from_user.first_name
    welcome_text = f"""
🛡️ <b>Добро пожаловать в ScamGuard AI, {user_name}!</b>

Я защищаю вас от онлайн-мошенников! 🚨

<b>🤖 Что я умею:</b>
• Анализирую сообщения от мошенников
• Detectирую 8 типов мошенничества
• 📁 <b>ПРОВЕРЯЮ ФАЙЛЫ</b> (.apk, .exe, .pdf и др.)
• Сравниваю с базой паттернов мошенников
• Даю персональные рекомендации

<b>⚡ Как это работает:</b>
1️⃣ Получили подозрительное сообщение/файл?
2️⃣ <b>Перешлите его мне</b> (или скопируйте текст)
3️⃣ Мгновенная проверка → оценка риска 0-100
4️⃣ Узнайте правду и защитите свои деньги!

<b>🎯 Поддерживается:</b>
• 📝 Пересланные сообщения из Telegram
• 📋 Скопированный текст
• 📁 <b>ФАЙЛЫ</b> (.apk, .exe, .pdf, .zip, .doc и др.)
• 🖼 Фотографии с объявлений
• 🔗 Ссылки на объявления

<b>Просто перешлите мне сообщение или файл!</b> 👇
    """
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=create_main_menu())


@dp.callback_query(F.data == "analyze")
async def callback_analyze(callback: types.CallbackQuery, state: FSMContext):
    """Handle analyze button"""
    await callback.answer()
    await state.set_state(AnalysisStates.waiting_for_message)
    await callback.message.answer(
        "📨 <b>Перешлите подозрительное сообщение</b>\n\n"
        "Поддерживаются:\n"
        "• 🔄 Пересланные сообщения из Telegram\n"
        "• 📝 Скопированный текст сообщения\n"
        "• 🖼 Фотографии (с объявления)\n"
        "• 🔗 Ссылки на объявления\n\n"
        "💡 <b>Совет:</b> Просто перешлите сообщение от мошенника!\n\n"
        "Или /cancel для отмены",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "help")
async def callback_help(callback: types.CallbackQuery):
    """Handle help button"""
    await callback.answer()
    help_text = """
📖 <b>Подробная справка</b>

<b>🎯 Основные команды:</b>
/start - Главное меню
/analyze - Проверить сообщение
/history - История проверок
/stats - Статистика

<b>🔍 Что мы анализируем:</b>

1️⃣ <b>Типы мошенничества (8):</b>
   • 🏠 Аренда/продажа (поддельные объявления)
   • 💰 Инвестиции (финансовые пирамиды)
   • ❤️ Романтика (фейковые отношения)
   • 🔒 Фишинг (кража данных)
   • 👔 Работа (поддельные вакансии)
   • 🎁 Розыгрыши (фальшивые призы)
   • 💳 Кража карт
   • 🆘 Tech support scams

2️⃣ <b>📁 ПРОВЕРКА ФАЙЛОВ:</b>
   • 🔴 .exe, .msi, .bat, .cmd — ИСПОЛНЯЕМЫЕ (ВИРУСЫ!)
   • 🔴 .apk, .aab — Android приложения
   • 🟡 .docm, .xlsm — Документы с макросами
   • 🟡 .zip, .rar, .7z — Архивы
   • 🟢 .pdf — Документы (обычно безопасно)

3️⃣ <b>Психологические манипуляции:</b>
   • Срочность и давление
   • Обещания лёгких денег
   • Эмоциональный шантаж
   • Фейковый авторитет
   • Секретность

4️⃣ <b>Технический анализ:</b>
   • Проверка фото (дубликаты, качество)
   • Сравнение с 25 паттернами
   • 80+ правил детектирования
   • AI анализ (87% точность)

<b>⚡ Два режима проверки:</b>
⚡ <b>Быстрая</b> — мгновенно, 80+ правил
🧠 <b>Глубокая AI</b> — по кнопке, 10-15 сек

<b>⚠️ Уровни риска:</b>
🟢 0-29: Низкий риск
🟡 30-59: Средний риск
🔴 60-100: Высокий риск (мошенник!)

<b>💡 Помните:</b>
Это инструмент помощи, окончательное решение за вами!
    """
    await callback.message.answer(help_text, parse_mode="HTML", reply_markup=create_main_menu())


@dp.callback_query(F.data == "about")
async def callback_about(callback: types.CallbackQuery):
    """Handle about button"""
    await callback.answer()
    about_text = """
🛡️ <b>О проекте ScamGuard AI</b>

<b>Миссия:</b>
Универсальная защита от ЛЮБЫХ онлайн-мошенников!

<b>Возможности:</b>
🎯 8 типов мошенничества (аренда, инвестиции, романтика, фишинг, работа...)
🧠 80+ правил детектирования
📊 25 паттернов в базе мошенников
🤖 AI анализ (Google Gemini 1.5 Flash)
🔍 Проверка фото на дубликаты
💡 Анализ психологических манипуляций

<b>Pipeline анализа (4 модуля):</b>
• Rule Engine (80+ правил, instant)
• Image Analysis (проверка фото)
• Embedding Analysis (сравнение с базой)
• AI Analysis (глубокий контекст)

<b>Доказанная эффективность:</b>
✅ 87% Precision (точность)
✅ 93% Recall (полнота)
✅ 30 тестовых примеров
✅ $0 стоимость (бесплатный AI!)

<b>Рынок:</b>
🌍 30M+ потенциальных пользователей
💰 $500M ущерба ежегодно от мошенников

<b>Команда:</b>
Создано с ❤️ для защиты людей

<b>Версия:</b> 0.4.0 (Universal Scam Detector)
    """
    await callback.message.answer(about_text, parse_mode="HTML", reply_markup=create_main_menu())


@dp.callback_query(F.data == "my_stats")
async def callback_my_stats(callback: types.CallbackQuery):
    """Handle my stats button"""
    await callback.answer("Загружаю вашу статистику...")
    user_id = callback.from_user.id
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/history/{user_id}", timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                
                if not history:
                    await callback.message.answer(
                        "📊 <b>Ваша статистика</b>\n\n"
                        "У вас пока нет проверок.\n"
                        "Начните с кнопки '🔍 Проверить сообщение'!",
                        parse_mode="HTML",
                        reply_markup=create_main_menu()
                    )
                    return
                
                # Calculate stats
                total = len(history)
                high_risk = sum(1 for h in history if h['risk_level'] == 'high')
                medium_risk = sum(1 for h in history if h['risk_level'] == 'medium')
                low_risk = sum(1 for h in history if h['risk_level'] == 'low')
                avg_risk = sum(h['risk_score'] for h in history) / total
                
                stats_text = f"""
📊 <b>Ваша статистика</b>

<b>Всего проверок:</b> {total}

<b>Распределение рисков:</b>
🔴 Высокий: {high_risk} ({high_risk*100//total}%)
🟡 Средний: {medium_risk} ({medium_risk*100//total}%)
🟢 Низкий: {low_risk} ({low_risk*100//total}%)

<b>Средний риск:</b> {avg_risk:.1f}/100

<b>Последние проверки:</b>
"""
                
                for i, item in enumerate(history[:3], 1):
                    risk_emoji = "🟢" if item['risk_level'] == 'low' else "🟡" if item['risk_level'] == 'medium' else "🔴"
                    date = item['created_at'][:10]
                    stats_text += f"\n{i}. {risk_emoji} Риск {item['risk_score']}/100 ({date})"
                
                if high_risk > 0:
                    stats_text += f"\n\n✅ <b>Вы избежали {high_risk} мошенничеств!</b>"
                
                await callback.message.answer(stats_text, parse_mode="HTML", reply_markup=create_main_menu())
            else:
                await callback.message.answer("❌ Ошибка при получении статистики", reply_markup=create_main_menu())
                
    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        await callback.message.answer("❌ Произошла ошибка", reply_markup=create_main_menu())


@dp.callback_query(F.data == "global_stats")
async def callback_global_stats(callback: types.CallbackQuery):
    """Handle global stats button"""
    await callback.answer("Загружаю статистику...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/stats", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                total = data['total_analyses']
                avg_risk = data['average_risk_score']
                dist = data.get('risk_distribution', {})

                # Calculate savings (assuming average loss is $300)
                high_risk = dist.get('high', 0)
                estimated_savings = high_risk * 300

                stats_text = f"""
📈 <b>Общая статистика ScamGuard AI</b>

<b>Всего проверок:</b> {total:,}
<b>Средний риск:</b> {avg_risk:.1f}/100

<b>Распределение:</b>
🟢 Низкий риск: {dist.get('low', 0)}
🟡 Средний риск: {dist.get('medium', 0)}
🔴 Высокий риск: {dist.get('high', 0)}

💰 <b>Предотвращено потерь:</b> ~${estimated_savings:,}

<b>Топ красные флаги:</b>
• Подозрительная цена
• Требование предоплаты
• Срочность и давление
• Отсутствие контактов

🎯 <b>Миссия:</b> Защитить людей от мошенников!
                """

                await callback.message.answer(stats_text, parse_mode="HTML", reply_markup=create_main_menu())
            else:
                await callback.message.answer("❌ Ошибка при получении статистики", reply_markup=create_main_menu())

    except Exception as e:
        logger.error(f"Error in global_stats: {e}")
        await callback.message.answer("❌ Произошла ошибка", reply_markup=create_main_menu())


@dp.callback_query(F.data == "bot_logs")
async def callback_bot_logs(callback: types.CallbackQuery):
    """Handle bot logs button"""
    await callback.answer("Загружаю логи...")
    
    try:
        log_file = Path("logs/bot.log")
        
        if not log_file.exists():
            await callback.message.answer(
                "❌ Файл логов не найден",
                reply_markup=create_main_menu()
            )
            return
        
        # Read last 25 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-25:]
        
        # Parse
        errors = 0
        warnings = 0
        info = 0
        
        formatted_logs = []
        
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            if '| ERROR |' in line:
                errors += 1
                emoji = '❌'
            elif '| WARNING |' in line:
                warnings += 1
                emoji = '⚠️'
            elif '| INFO |' in line:
                info += 1
                emoji = 'ℹ️'
            else:
                emoji = '📝'
            
            parts = line.split('|')
            if len(parts) >= 3:
                time_part = parts[0].strip()
                msg_part = parts[-1].strip()[:70]
                formatted_logs.append(f"{emoji} <code>{time_part}</code> {msg_part}")
        
        # Build report
        report = f"""
📋 <b>ЛОГИ БОТА</b>

📊 <b>Сводка:</b>
ℹ️ Информации: {info}
⚠️ Предупреждений: {warnings}
❌ Ошибок: {errors}

<b>Последние события:</b>
{'─' * 32}
"""
        
        for log_entry in formatted_logs[-12:]:
            report += f"{log_entry}\n"
        
        # Health
        health = 100 - (errors * 10) - (warnings * 5)
        health = max(0, min(100, health))
        
        if health >= 80:
            health_emoji = '✅'
            health_text = 'ОТЛИЧНО'
        elif health >= 60:
            health_emoji = '⚠️'
            health_text = 'НОРМАЛЬНО'
        else:
            health_emoji = '❌'
            health_text = 'ПЛОХО'
        
        report += f"""
{'─' * 32}
{health_emoji} <b>Здоровье: {health_text} ({health}/100)</b>

💡 <b>Команды:</b>
• <code>/logs</code> — показать логи в боте
• <code>/stats</code> — общая статистика
"""
        
        if len(report) > 4000:
            report = report[:3900] + "\n..."
        
        await callback.message.answer(report, parse_mode="HTML", reply_markup=create_main_menu())
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        await callback.message.answer(
            "❌ Ошибка при чтении логов",
            reply_markup=create_main_menu()
        )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Handle /cancel command"""
    await state.clear()
    await message.answer("❌ Операция отменена", reply_markup=create_main_menu())


@dp.message(Command("history"))
async def cmd_history(message: Message):
    """Handle /history command"""
    user_id = message.from_user.id
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/history/{user_id}", timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                
                if not history:
                    await message.answer(
                        "📋 У вас пока нет истории проверок\n\n"
                        "Начните с команды /analyze",
                        reply_markup=create_main_menu()
                    )
                    return
                
                text = f"📋 <b>Ваша история проверок</b> (последние {len(history)}):\n\n"
                
                for i, item in enumerate(history, 1):
                    risk_emoji = "🟢" if item['risk_level'] == 'low' else "🟡" if item['risk_level'] == 'medium' else "🔴"
                    source_text = item.get('summary') or item.get('url') or "unknown"
                    url_short = source_text[:40] + "..." if len(source_text) > 40 else source_text
                    date = item['created_at'][:16].replace('T', ' ')
                    
                    text += f"{i}. {risk_emoji} <b>{item['risk_score']}/100</b>\n"
                    text += f"   <code>{url_short}</code>\n"
                    text += f"   📅 {date}\n\n"
                
                await message.answer(text, parse_mode="HTML", reply_markup=create_main_menu())
            else:
                await message.answer("❌ Ошибка при получении истории", reply_markup=create_main_menu())
                
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        await message.answer("❌ Ошибка при получении истории", reply_markup=create_main_menu())


@dp.message(AnalysisStates.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    """Process message with immediate deep AI analysis."""
    await state.clear()

    # Extract text and photos from the message
    message_text = message.text or message.caption or ""
    photos = message.photo if message.photo else []

    # Check if it's a forwarded message
    is_forwarded = message.forward_from is not None or message.forward_sender_name is not None

    # Check if text is a URL
    if message_text.startswith(('http://', 'https://')):
        await analyze_url(message, message_text.strip())
        return

    # If no text and no photos, reject
    if not message_text.strip() and not photos:
        await message.answer(
            "❌ Не удалось извлечь данные из сообщения\n\n"
            "Попробуйте:\n"
            "• Переслать текстовое сообщение\n"
            "• Отправить фото с объявления\n"
            "• Скопировать текст сообщения",
            parse_mode="HTML",
            reply_markup=create_main_menu()
        )
        return

    await process_message_deep_analysis(
        message, message_text, photos, is_forwarded
    )


@dp.message(F.forward_from)
async def handle_forwarded_message(message: Message, state: FSMContext):
    """Handle direct forwarded messages (even outside FSM state)"""
    await state.set_state(AnalysisStates.waiting_for_message)

    message_text = message.text or message.caption or ""
    photos = message.photo if message.photo else []

    # If it's just a URL, analyze as URL
    if message_text.strip().startswith(('http://', 'https://')):
        await state.clear()
        await analyze_url(message, message_text.strip())
        return

    await state.clear()
    await process_message_deep_analysis(
        message, message_text, photos, is_forwarded=True
    )


@dp.message(F.photo)
async def handle_photo_message(message: Message, state: FSMContext):
    """Handle photo messages with optional caption"""
    await state.clear()

    caption = message.caption or ""
    photos = message.photo

    # If caption has a URL, analyze as URL
    if 'http://' in caption or 'https://' in caption:
        import re
        url_match = re.search(r'https?://\S+', caption)
        if url_match:
            await analyze_url(message, url_match.group())
            return

    await process_message_deep_analysis(
        message, caption, photos, is_forwarded=False
    )


@dp.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    """Handle direct text messages"""
    await state.clear()

    text = message.text.strip()

    # If it's a URL, analyze as URL
    if text.startswith(('http://', 'https://')):
        await analyze_url(message, text)
        return

    await process_message_deep_analysis(
        message, text, [], is_forwarded=False
    )


@dp.message(F.document)
async def handle_document_message(message: Message, state: FSMContext):
    """Handle document/file messages"""
    await state.clear()

    document = message.document
    caption = message.caption or ""

    # Get file info
    file_name = document.file_name or "unknown_file"
    file_size = document.file_size or 0
    mime_type = document.mime_type or ""

    # Extract file extension
    file_ext = '.' + file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''

    # Check if it's a known file type
    file_type = DANGEROUS_FILE_EXTENSIONS.get(file_ext, 'unknown')

    # Analyze the file
    await analyze_file_with_warning(
        message, file_name, file_ext, file_type, file_size, mime_type, caption
    )


async def analyze_file_with_warning(
    message: Message,
    file_name: str,
    file_ext: str,
    file_type: str,
    file_size: int,
    mime_type: str,
    caption: str
):
    """
    Analyze a file and show warning if dangerous

    Checks:
    - File extension (exe, apk, etc.)
    - File size
    - Context (caption text)
    """
    risk_score = 0
    red_flags = []
    recommendations = []
    lang = get_user_language(message)

    # Check 1: File type risk
    if file_type in CRITICAL_FILE_TYPES:
        risk_score += 70
        red_flags.append({
            'severity': 10,
            'category': 'file',
            'description': f'⚠️ ИСПОЛНЯЕМЫЙ ФАЙЛ: {file_ext.upper()} может содержать вирус/троян'
        })

        if file_type in ['android_app', 'android_app_bundle']:
            red_flags.append({
                'severity': 9,
                'category': 'file',
                'description': f'📱 APK файл — может украсть данные с телефона'
            })
            recommendations.append('🚨 НЕ УСТАНАВЛИВАЙТЕ этот файл!')
            recommendations.append('📱 APK файлы от неизвестных источников = вирус')
        elif file_type in ['executable_windows', 'installer_windows', 'screensaver_executable']:
            red_flags.append({
                'severity': 9,
                'category': 'file',
                'description': f'💻 {file_ext.upper()} файл — может заразить компьютер'
            })
            recommendations.append('🚨 НЕ ЗАПУСКАЙТЕ этот файл!')
            recommendations.append('💻 Исполняемые файлы = возможные вирусы')
        elif file_type in ['batch_script', 'command_script', 'powershell_script', 'vbscript']:
            red_flags.append({
                'severity': 9,
                'category': 'file',
                'description': f'📜 Скрипт ({file_ext}) — может выполнить команды'
            })
            recommendations.append('🚨 НЕ ОТКРЫВАЙТЕ этот файл!')
            recommendations.append('📜 Скрипты могут украсть пароли и данные')

    elif file_type in SUSPICIOUS_FILE_TYPES:
        risk_score += 40
        red_flags.append({
            'severity': 7,
            'category': 'file',
            'description': f'⚠️ Подозрительный файл: {file_ext.upper()}'
        })

        if 'macros' in file_type:
            red_flags.append({
                'severity': 8,
                'category': 'file',
                'description': '📄 Документ с МАКРОСАМИ — может выполнить код'
            })
            recommendations.append('⚠️ Не включайте макросы в документе!')
        elif file_type == 'archive':
            red_flags.append({
                'severity': 6,
                'category': 'file',
                'description': '📦 Архив — внутри может быть вирус'
            })
            recommendations.append('⚠️ Распакуйте и проверьте содержимое')
            recommendations.append('🔍 Проверьте антивирусом перед открытием')

    elif file_type == 'document':
        risk_score += 10
        red_flags.append({
            'severity': 3,
            'category': 'file',
            'description': f'📄 PDF документ — обычно безопасно, но проверьте контекст'
        })
        recommendations.append('✅ PDF обычно безопасен, но не переходите по ссылкам внутри')

    # Check 2: File size
    if file_size > 50 * 1024 * 1024:  # > 50MB
        risk_score += 10
        red_flags.append({
            'severity': 5,
            'category': 'file',
            'description': f'📏 Большой файл ({file_size // 1024 // 1024} MB)'
        })
    elif file_size < 1024:  # < 1KB
        risk_score += 15
        red_flags.append({
            'severity': 7,
            'category': 'file',
            'description': f'📏 Очень маленький файл ({file_size} bytes) — подозрительно'
        })

    # Check 3: Caption text analysis
    if caption:
        # Check if caption has scam keywords
        caption_lower = caption.lower()
        scam_file_words = [
            'скачай', 'установи', 'открой файл', 'это приложение',
            'тут всё есть', 'перейди по ссылке', 'получи доступ',
            'войди в аккаунт', 'подтверди данные', 'верификация',
        ]

        for word in scam_file_words:
            if word in caption_lower:
                risk_score += 20
                red_flags.append({
                    'severity': 9,
                    'category': 'file',
                    'description': f'⚠️ В тексте просят: "{word}"'
                })
                recommendations.append('🚨 Мошенники часто просят скачать файл!')
                break

    # Check 4: Unknown file type
    if file_type == 'unknown' and file_ext:
        risk_score += 25
        red_flags.append({
            'severity': 6,
            'category': 'file',
            'description': f'❓ Неизвестный формат файла: {file_ext}'
        })
        recommendations.append('⚠️ Не открывайте файлы неизвестных форматов')

    # Cap risk score
    risk_score = min(risk_score, 100)

    # Determine risk level
    if risk_score >= 70:
        risk_level = 'high'
        emoji = '🔴'
        level_text = 'КРИТИЧЕСКИЙ РИСК'
    elif risk_score >= 40:
        risk_level = 'medium'
        emoji = '🟡'
        level_text = 'СРЕДНИЙ РИСК'
    else:
        risk_level = 'low'
        emoji = '🟢'
        level_text = 'НИЗКИЙ РИСК'

    size_label = f"{file_size // 1024 if file_size > 1024 else file_size} {'MB' if file_size > 1024*1024 else 'KB' if file_size > 1024 else 'B'}"
    file_type_label = file_ext.upper() if file_ext else ("Unknown" if lang == "en" else "Неизвестно")
    result_text = (
        f"📁 <b>{'File check' if lang == 'en' else 'Проверка файла'}</b>\n\n"
        f"{emoji} <b>{level_text}</b>\n"
        f"<code>{compact_risk_bar(risk_score)}</code> {risk_score}/100\n\n"
        f"<b>{'File' if lang == 'en' else 'Файл'}:</b> <code>{file_name}</code>\n"
        f"<b>{'Type' if lang == 'en' else 'Тип'}:</b> {file_type_label}\n"
        f"<b>{'Size' if lang == 'en' else 'Размер'}:</b> {size_label}\n"
        f"<b>{'Findings' if lang == 'en' else 'Найдено'}:</b> {len(red_flags)}"
    )

    if red_flags:
        title = "⚠️ <b>Top risks:</b>" if lang == "en" else "⚠️ <b>Главные риски:</b>"
        result_text += f"\n\n{title}\n"
        for flag in red_flags[:4]:
            result_text += f"• {flag['description']}\n"

    if recommendations:
        title = "💡 <b>What to do:</b>" if lang == "en" else "💡 <b>Что делать:</b>"
        result_text += f"\n{title}\n"
        for rec in recommendations[:3]:
            result_text += f"• {rec}\n"

    safety_title = "🔒 <b>Basic safety:</b>" if lang == "en" else "🔒 <b>Базовая безопасность:</b>"
    safety_lines = (
        [
            "Do not install files from unknown senders",
            "Scan files before opening them",
            "Do not enable macros in documents",
        ]
        if lang == "en"
        else [
            "Не устанавливайте файлы от неизвестных отправителей",
            "Проверяйте файлы перед открытием",
            "Не включайте макросы в документах",
        ]
    )
    result_text += f"\n{safety_title}\n"
    for line in safety_lines:
        result_text += f"• {line}\n"

    await message.answer(result_text, parse_mode="HTML")

    # Offer deep analysis for context
    if caption and risk_score < 70:
        # If there's caption text, offer deep text analysis
        deep_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Text analysis" if lang == "en" else "🧠 Анализ текста сообщения",
                    callback_data="analyze"
                )
            ],
            [
                InlineKeyboardButton(text="🏠 Home" if lang == "en" else "🏠 Главная", callback_data="main_menu")
            ]
        ])

        await message.answer(
            "📝 Want me to analyze the <b>message text</b> too?\n\nI can scan the text for scam signals."
            if lang == "en" else
            "📝 Хотите проанализировать <b>текст сообщения</b>?\n\nБот проверит текст на признаки мошенничества.",
            parse_mode="HTML",
            reply_markup=deep_keyboard
        )


async def analyze_url(message: Message, url: str):
    """Analyze URL and send results with beautiful formatting"""
    user_id = message.from_user.id

    # Send animated "analyzing" messages
    status_msg = await message.answer("🔍 <b>Начинаю анализ...</b>", parse_mode="HTML")

    await asyncio.sleep(1)
    await status_msg.edit_text("🔍 <b>Парсинг данных...</b>\n⏳ Загружаю информацию", parse_mode="HTML")

    try:
        async with httpx.AsyncClient() as client:
            # Show progress
            await asyncio.sleep(1.5)
            await status_msg.edit_text(
                "🔍 <b>Анализирую данные...</b>\n"
                "▰▰▰▱▱▱▱▱▱▱ 30%\n"
                "⏳ Проверяю текст и фото",
                parse_mode="HTML"
            )

            response = await client.post(
                f"{API_URL}/analyze",
                json={"url": url, "user_id": user_id},
                timeout=60.0
            )

            await status_msg.edit_text(
                "🔍 <b>Финализирую результаты...</b>\n"
                "▰▰▰▰▰▰▰▰▰▱ 90%\n"
                "⏳ Генерирую рекомендации",
                parse_mode="HTML"
            )

            if response.status_code == 200:
                result = response.json()
                await send_detailed_result(message, result, url, status_msg)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                await status_msg.edit_text(f"❌ <b>Ошибка анализа:</b>\n{error_detail}", parse_mode="HTML")

    except httpx.TimeoutException:
        await status_msg.edit_text(
            "❌ <b>Превышено время ожидания</b>\n\n"
            "Возможные причины:\n"
            "• Сообщение слишком большое\n"
            "• Проблемы с сетью\n\n"
            "Попробуйте позже или другую ссылку",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error analyzing URL: {e}")
        await status_msg.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            f"Детали: <code>{str(e)[:100]}</code>\n\n"
            "Попробуйте другую ссылку или обратитесь в поддержку",
            parse_mode="HTML"
        )


async def prepare_photo_payload(photos: list) -> list[dict]:
    """Download up to 3 Telegram photos and encode them for deep analysis."""
    if not photos:
        return []

    encoded_photos = []
    for index, photo in enumerate(photos[-3:]):
        try:
            telegram_file = await bot.get_file(photo.file_id)
            buffer = io.BytesIO()
            await bot.download_file(telegram_file.file_path, destination=buffer)
            encoded_photos.append(
                {
                    "index": index,
                    "data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to download photo {index} for deep analysis: {e}")

    return encoded_photos


async def process_message_deep_analysis(
    message: Message,
    text: str,
    photos: list,
    is_forwarded: bool = False
):
    """Primary bot flow: run the full deep AI analysis immediately."""
    user_id = message.from_user.id
    message_text = (text or "").strip()

    status_msg = await message.answer(
        "🧠 <b>Запускаю глубокий AI анализ...</b>\n"
        "<code>▰▰▰▱▱▱▱▱▱▱</code>\n"
        "Готовлю текст и вложения",
        parse_mode="HTML"
    )

    try:
        encoded_photos = await prepare_photo_payload(photos)

        await status_msg.edit_text(
            "🧠 <b>Глубокий AI анализ...</b>\n"
            "<code>▰▰▰▰▰▰▱▱▱▱</code>\n"
            "Анализирую контекст, манипуляции и риск-сигналы",
            parse_mode="HTML"
        )

        payload = {
            "text": message_text,
            "user_id": user_id,
            "is_forwarded": is_forwarded,
            "photos": encoded_photos,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/analyze-message-deep",
                json=payload,
                timeout=150.0
            )

        if response.status_code == 200:
            result = response.json()
            message_id = result.get("details", {}).get("message_id")
            await send_summary_result(message, result, status_msg, message_id)
            return

        error_detail = response.json().get("detail", "Unknown error")
        await status_msg.edit_text(
            f"❌ <b>Ошибка AI анализа:</b>\n{safe_markdown_text(str(error_detail)[:300])}",
            parse_mode="HTML"
        )
    except httpx.TimeoutException:
        await status_msg.edit_text(
            "❌ <b>AI анализ занял слишком много времени</b>\n\n"
            "Попробуйте ещё раз через минуту.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in deep analysis: {e}")
        await status_msg.edit_text(
            "❌ <b>Произошла ошибка при AI анализе</b>\n\n"
            f"Детали: <code>{str(e)[:120]}</code>",
            parse_mode="HTML"
        )


def get_risk_verdict_text(risk_level: str) -> str:
    """Return a short Russian verdict for the current risk level."""
    if risk_level == "low":
        return "Похоже относительно безопасно"
    if risk_level == "medium":
        return "Нужна осторожность"
    return "Высокая вероятность мошенничества"


async def send_summary_result(
    message: Message,
    result: dict,
    status_msg: Message,
    message_id: int | None
):
    """Send a simple, user-friendly summary — no technical jargon."""
    risk_score = result["risk_score"]
    risk_level = result["risk_level"]
    red_flags = result.get("red_flags", [])
    recommendations = result.get("recommendations", [])
    details = result.get("details", {})

    try:
        await status_msg.delete()
    except Exception as e:
        logger.debug(f"Could not delete status message (already deleted?): {e}")

    # Simple verdict based on risk level
    if risk_level == "high":
        verdict_emoji = "🔴"
        verdict_title = "⚠️ ВЫСОКИЙ РИСК"
        verdict_text = "Это похоже на мошенничество. Будьте очень осторожны!"
    elif risk_level == "medium":
        verdict_emoji = "🟡"
        verdict_title = "СРЕДНИЙ РИСК"
        verdict_text = "Есть подозрительные моменты. Проявите осторожность."
    else:
        verdict_emoji = "🟢"
        verdict_title = "НИЗКИЙ РИСК"
        verdict_text = "Явных признаков обмана нет, но будьте внимательны."

    # Build simple summary
    summary_text = f"{verdict_emoji} <b>{verdict_title}</b>\n\n"
    summary_text += f"<b>Оценка:</b> {risk_score}/100\n"
    summary_text += f"<b>Вывод:</b> {verdict_text}"

    # Top 2 red flags (translated to simple language)
    if red_flags:
        summary_text += "\n\n<b>Что насторожило:</b>\n"
        for flag in red_flags[:2]:
            desc = flag['description']
            # Remove technical prefixes like "🚨", "⚠️", etc.
            desc = desc.lstrip('🚨⚠️❌🔴🟡⚪ ').strip()
            summary_text += f"• {safe_markdown_text(desc)}\n"

    # Top 1-2 recommendations
    if recommendations:
        summary_text += "\n<b>Совет:</b>\n"
        for rec in recommendations[:2]:
            summary_text += f"• {safe_markdown_text(rec)}\n"

    # Action buttons
    keyboard_rows = []
    if message_id:
        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    text="📋 Полный отчёт",
                    callback_data=f"details_message:{message_id}"
                )
            ]
        )
    keyboard_rows.append(
        [
            InlineKeyboardButton(text="🔍 Проверить ещё", callback_data="analyze"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    )

    await message.answer(
        summary_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    )


async def send_message_detailed_report(message: Message, report: dict):
    """Send the full saved report — simplified for regular users."""
    risk_score = report["risk_score"]
    risk_level = report["risk_level"]
    red_flags = report.get("red_flags", [])
    recommendations = report.get("recommendations", [])
    details = report.get("details", {}) or {}

    nlp_details = details.get("nlp_llm", {})
    explanation = nlp_details.get("explanation") or details.get("explanation") or "Подробное объяснение не сохранено."
    scam_type = nlp_details.get("scam_type") or details.get("scam_type") or "не определён"
    manipulation_tactics = nlp_details.get("manipulation_tactics") or details.get("manipulation_tactics") or []
    message_text = (report.get("message_text") or "").strip()

    # Simple verdict
    if risk_level == "high":
        verdict_emoji = "🔴"
        verdict_title = "ВЫСОКИЙ РИСК МОШЕННИЧЕСТВА"
    elif risk_level == "medium":
        verdict_emoji = "🟡"
        verdict_title = "СРЕДНИЙ РИСК"
    else:
        verdict_emoji = "🟢"
        verdict_title = "НИЗКИЙ РИСК"

    detail_text = f"{verdict_emoji} <b>{verdict_title}</b>\n\n"
    detail_text += f"<b>Оценка риска:</b> {risk_score}/100\n\n"

    # Full explanation from AI
    detail_text += f"<b>📝 Объяснение:</b>\n{safe_markdown_text(explanation[:500])}\n\n"

    # Scam type
    detail_text += f"<b>Тип схемы:</b> {safe_markdown_text(str(scam_type))}\n"

    # Manipulation tactics (simplified)
    if manipulation_tactics and manipulation_tactics != "не определён":
        detail_text += "\n<b>Методы давления:</b>\n"
        if isinstance(manipulation_tactics, list):
            for tactic in manipulation_tactics[:3]:
                detail_text += f"• {safe_markdown_text(str(tactic))}\n"
        else:
            detail_text += f"• {safe_markdown_text(str(manipulation_tactics))}\n"

    # All red flags
    if red_flags:
        detail_text += f"\n<b>Найдено подозрительного: {len(red_flags)}</b>\n\n"
        for index, flag in enumerate(red_flags[:8], 1):
            desc = flag['description'].lstrip('🚨⚠️❌🔴🟡⚪ ').strip()
            severity_icon = "🔴" if flag['severity'] >= 7 else "🟡" if flag['severity'] >= 5 else "⚪"
            detail_text += f"{index}. {severity_icon} {safe_markdown_text(desc)}\n"

    # Recommendations
    if recommendations:
        detail_text += f"\n<b>Что делать:</b>\n"
        for index, rec in enumerate(recommendations[:5], 1):
            detail_text += f"{index}. {safe_markdown_text(rec)}\n"

    # Message snippet (only if not too long)
    if message_text and len(message_text) > 50:
        snippet = message_text[:400]
        detail_text += f"\n<b>Проверенное сообщение:</b>\n_{safe_markdown_text(snippet)}_"

    # Limit message length
    if len(detail_text) > 4000:
        detail_text = detail_text[:3900] + "\n\n_... отчёт сокращён ..._"

    await message.answer(
        detail_text,
        parse_mode="HTML",
        reply_markup=create_main_menu()
    )


async def process_message_quick_then_offer_deep(
    message: Message,
    text: str,
    photos: list,
    is_forwarded: bool = False
):
    """
    NEW FLOW: Quick check first (instant), then offer deep AI analysis

    This is the new workflow:
    1. User sends message
    2. Instant quick check (rules only, 1-2 sec)
    3. Show results + button "🔍 Глубокий AI анализ"
    4. User clicks → deep analysis with Gemini (5-15 sec)
    """
    user_id = message.from_user.id
    has_photos = len(photos) > 0
    lang = get_user_language(message)

    # Check for file attachments (from message.document)
    has_file = False
    file_count = 0
    # Note: document is handled separately in handle_document_message
    # For text/photo messages, has_file stays False

    # Step 1: Quick check (instant)
    status_msg = await message.answer(
        "⚡ <b>Quick check...</b>\n<code>▰▰▰▱▱▱▱▱▱▱</code>\nChecking 80+ rules"
        if lang == "en" else
        "⚡ <b>Быстрая проверка...</b>\n<code>▰▰▰▱▱▱▱▱▱▱</code>\nПроверяю по 80+ правилам",
        parse_mode="HTML"
    )

    try:
        async with httpx.AsyncClient() as client:
            # Prepare payload for quick check
            payload = {
                "text": text,
                "user_id": user_id,
                "is_forwarded": is_forwarded,
                "has_photos": has_photos,
                "has_file": has_file,
                "file_count": file_count,
            }

            response = await client.post(
                f"{API_URL}/analyze-message-quick",
                json=payload,
                timeout=10.0  # Quick check should be fast
            )

            if response.status_code == 200:
                quick_result = response.json()
                message_id = quick_result.get('details', {}).get('message_id')

                # Show quick results with button for deep analysis
                await send_quick_result(
                    message, quick_result, text, status_msg, message_id
                )
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                await status_msg.edit_text(
                    f"❌ <b>Quick check failed:</b>\n{error_detail}"
                    if lang == "en" else
                    f"❌ <b>Ошибка быстрой проверки:</b>\n{error_detail}",
                    parse_mode="HTML"
                )

    except httpx.TimeoutException:
        await status_msg.edit_text(
            "❌ <b>Quick check timed out</b>\n\nPlease try again later."
            if lang == "en" else
            "❌ <b>Быстрая проверка не удалась</b>\n\nПревышено время ожидания.\nПопробуйте позже.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in quick check: {e}")
        await status_msg.edit_text(
            f"❌ <b>An error occurred</b>\n\nDetails: <code>{str(e)[:100]}</code>"
            if lang == "en" else
            "❌ <b>Произошла ошибка</b>\n\n"
            f"Детали: <code>{str(e)[:100]}</code>",
            parse_mode="HTML"
        )


async def send_quick_result(
    message: Message,
    result: dict,
    text: str,
    status_msg: Message,
    message_id: int
):
    """Show quick check results — simplified for regular users."""
    risk_score = result['risk_score']
    risk_level = result['risk_level']
    red_flags = result.get('red_flags', [])
    lang = get_user_language(message)

    # Delete status message
    await status_msg.delete()

    # Simple verdict
    if risk_level == "high":
        verdict_emoji = "🔴"
        verdict_title = "ВЫСОКИЙ РИСК"
        verdict_text = "Это выглядит подозрительно. Рекомендую глубокий анализ."
    elif risk_level == "medium":
        verdict_emoji = "🟡"
        verdict_title = "СРЕДНИЙ РИСК"
        verdict_text = "Есть подозрительные моменты. Хотите глубокий анализ?"
    else:
        verdict_emoji = "🟢"
        verdict_title = "НИЗКИЙ РИСК"
        verdict_text = "Явных признаков обмана нет, но будьте внимательны."

    result_text = f"{verdict_emoji} <b>{verdict_title}</b>\n\n"
    result_text += f"<b>Оценка:</b> {risk_score}/100\n"
    result_text += f"<b>Вывод:</b> {verdict_text}"

    if red_flags:
        result_text += f"\n\n<b>Нашлось подозрительного: {len(red_flags)}</b>\n"
        for i, flag in enumerate(red_flags[:3], 1):
            safe_desc = safe_markdown_text(flag['description'].lstrip('🚨⚠️❌🔴🟡⚪ ').strip())
            result_text += f"{i}. {safe_desc}\n"

    await message.answer(result_text, parse_mode="HTML")

    # Button for deep analysis
    deep_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🧠 Глубокий AI анализ",
                callback_data=f"deep_analysis:{message_id}"
            )
        ],
        [
            InlineKeyboardButton(text="🔍 Проверить ещё", callback_data="analyze"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

    await message.answer(
        "💡 Хотите узнать больше?\n\n"
        "Запустите полный AI анализ — он проверит текст, контекст и фото (если есть).",
        reply_markup=deep_keyboard
    )


async def process_deep_analysis(
    message: Message,
    callback: types.CallbackQuery,
    message_id: int
):
    """Run deep AI analysis when user clicks the button"""
    user_id = callback.from_user.id

    # Get message text from database
    try:
        async with httpx.AsyncClient() as client:
            # First, get the message from history
            response = await client.get(f"{API_URL}/history/{user_id}", timeout=10.0)

            if response.status_code != 200:
                await callback.answer("Не удалось найти сообщение", show_alert=True)
                return

            history_data = response.json()
            history = history_data.get('history', [])

            # Find the message by ID
            target_message = None
            for item in history:
                if item.get('id') == message_id:
                    target_message = item
                    break

            if not target_message:
                await callback.answer("Сообщение не найдено", show_alert=True)
                return

            # Get the message text
            # Note: We need to store message_text in history response
            # For now, we'll ask user to resend or we fetch from DB
            # Better approach: add endpoint to get message by ID

            await callback.answer("Запускаю AI анализ...", show_alert=False)

            # For now, we need to get the original text
            # This is a limitation - we need to improve this
            # Temporary solution: fetch from message_analyses table via new endpoint

            await run_deep_analysis_for_message(callback, user_id, message_id)

    except Exception as e:
        logger.error(f"Error preparing deep analysis: {e}")
        await callback.answer("❌ Ошибка при подготовке анализа", show_alert=True)


async def run_deep_analysis_for_message(
    callback: types.CallbackQuery,
    user_id: int,
    message_id: int
):
    """Run deep analysis for a specific message ID"""
    try:
        # Send progress messages
        progress_msg = await callback.message.answer(
            "<b>Запускаю глубокий AI анализ...</b>\n"
            "XXX....... 30%\n"
            "Анализирую контекст сообщения",
            parse_mode="HTML"
        )

        async with httpx.AsyncClient() as client:
            # Get full message details (including text and photos)
            # We need a new endpoint for this, but for now we'll use a workaround
            # Fetch from history and reconstruct

            # For MVP, let's assume we can get the message
            # In production, add: GET /api/v1/message/{message_id}

            # Temporary: fetch history and find message
            response = await client.get(f"{API_URL}/history/{user_id}", timeout=10.0)

            if response.status_code != 200:
                await progress_msg.edit_text("Ошибка получения данных")
                return

            history_data = response.json()
            history = history_data.get('history', [])

            # This is a limitation - history doesn't include full text
            # We need to add a proper endpoint

            # For now, show a message that we need the text again
            await progress_msg.edit_text(
                "<b>Требуется сообщение</b>\n\n"
                "Пожалуйста, перешлите сообщение ещё раз,\n"
                "и сразу запустится полный AI анализ.\n\n"
                "Или используйте команду /analyze",
                parse_mode="HTML",
                reply_markup=create_main_menu()
            )

    except Exception as e:
        logger.error(f"Error in deep analysis: {e}")
        await callback.message.answer(
            "<b>Ошибка глубокого анализа</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку",
            parse_mode="HTML"
        )


async def analyze_message(message: Message, text: str, photos: list, is_forwarded: bool = False):
    """
    LEGACY FUNCTION - kept for compatibility
    Use process_message_deep_analysis instead
    """
    logger.warning("Using legacy analyze_message function")
    await process_message_deep_analysis(message, text, photos, is_forwarded)


async def send_detailed_result(message: Message, result: dict, url: str, status_msg: Message):
    """Format and send detailed analysis result — simplified for regular users."""
    risk_score = result['risk_score']
    risk_level = result['risk_level']
    red_flags = result.get('red_flags', [])
    recommendations = result.get('recommendations', [])
    details = result.get('details', {})
    lang = get_user_language(message)

    # Delete status message (safely - ignore if already deleted)
    try:
        await status_msg.delete()
    except Exception as e:
        logger.debug(f"Could not delete status message (already deleted?): {e}")

    # Simple verdict
    if risk_level == 'high':
        verdict_emoji = "🔴"
        verdict_title = "ВЫСОКИЙ РИСК"
        verdict_text = "Это похоже на мошенничество!"
    elif risk_level == 'medium':
        verdict_emoji = "🟡"
        verdict_title = "СРЕДНИЙ РИСК"
        verdict_text = "Есть подозрительные моменты."
    else:
        verdict_emoji = "🟢"
        verdict_title = "НИЗКИЙ РИСК"
        verdict_text = "Явных признаков обмана нет."

    result_text = (
        f"{verdict_emoji} <b>{verdict_title}</b>\n\n"
        f"<b>Оценка:</b> {risk_score}/100\n"
        f"<b>Вывод:</b> {verdict_text}"
    )

    # Skip component scores — regular users don't need them

    await message.answer(result_text, parse_mode="HTML")

    if red_flags:
        flags_text = "⚠️ <b>Что насторожило:</b>\n\n"
        # Group by severity but show simply
        critical = [f for f in red_flags if f['severity'] >= 8]
        high = [f for f in red_flags if 5 <= f['severity'] < 8]
        medium = [f for f in red_flags if f['severity'] < 5]

        if critical:
            flags_text += "<b>Критично:</b>\n"
            for i, flag in enumerate(critical[:3], 1):
                safe_desc = safe_markdown_text(flag['description'].lstrip('🚨⚠️❌🔴🟡⚪ ').strip())
                flags_text += f"{i}. 🔴 {safe_desc}\n"
            flags_text += "\n"

        if high:
            flags_text += "<b>Серьёзно:</b>\n"
            for i, flag in enumerate(high[:3], 1):
                safe_desc = safe_markdown_text(flag['description'].lstrip('🚨⚠️❌🔴🟡⚪ ').strip())
                flags_text += f"{i}. 🟡 {safe_desc}\n"
            flags_text += "\n"

        if medium and not critical and not high:
            flags_text += "<b>Другое:</b>\n"
            for i, flag in enumerate(medium[:2], 1):
                safe_desc = safe_markdown_text(flag['description'].lstrip('🚨⚠️❌🔴🟡⚪ ').strip())
                flags_text += f"{i}. ⚪ {safe_desc}\n"

        await message.answer(flags_text, parse_mode="HTML")

    if recommendations:
        rec_text = "💡 <b>Что делать:</b>\n\n"
        for i, rec in enumerate(recommendations[:3], 1):
            safe_rec = safe_markdown_text(rec)
            rec_text += f"{i}. {safe_rec}\n"

        await message.answer(rec_text, parse_mode="HTML")

    # Add action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Проверить ещё", callback_data="analyze"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
        ]
    ])

    final_text = f"🔗 <a href='{url}'>Открыть источник</a>\n\n"

    if risk_score >= 70:
        final_text += "🔴 Не связывайтесь с этим источником!"
    elif risk_score >= 50:
        final_text += "🟡 Проявите особую осторожность."
    else:
        final_text += "🟢 Явных сигналов нет, но будьте внимательны."

    await message.answer(final_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=keyboard)

    # Ask for feedback if high risk
    if risk_score > 40:
        feedback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Точно", callback_data=f"feedback_good"),
                InlineKeyboardButton(text="❌ Неточно", callback_data=f"feedback_bad")
            ]
        ])
        await message.answer(
            "📊 <b>Помогите стать лучше</b>\nНаш анализ был точным?",
            parse_mode="HTML",
            reply_markup=feedback_keyboard
        )


@dp.callback_query(F.data.startswith("details_message:"))
async def callback_details_message(callback: types.CallbackQuery):
    """Show the saved detailed report for a message analysis."""
    await callback.answer()

    try:
        message_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Неверный идентификатор отчёта", show_alert=True)
        return

    loading_msg = await callback.message.answer(
        "📄 <b>Открываю детальный отчёт...</b>",
        parse_mode="HTML"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/message/{message_id}", timeout=15.0)

        if response.status_code != 200:
            await loading_msg.edit_text(
                "❌ <b>Не удалось получить детальный отчёт</b>",
                parse_mode="HTML"
            )
            return

        await loading_msg.delete()
        await send_message_detailed_report(callback.message, response.json())
    except Exception as e:
        logger.error(f"Error loading detailed report: {e}")
        await loading_msg.edit_text(
            "❌ <b>Ошибка при загрузке детального отчёта</b>",
            parse_mode="HTML"
        )


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    """Return to main menu"""
    await callback.answer()
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode="HTML",
        reply_markup=create_main_menu()
    )


@dp.callback_query(F.data.startswith('feedback_'))
async def process_feedback(callback: types.CallbackQuery):
    """Process feedback callback"""
    feedback = callback.data.replace('feedback_', '')
    
    if feedback == 'good':
        await callback.answer("Спасибо за отзыв! 🙏", show_alert=True)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Спасибо за отзыв!</b> Вы помогаете нам стать лучше 💙",
            parse_mode="HTML"
        )
    else:
        await callback.answer("Мы учтем ваш отзыв для улучшения!", show_alert=True)
        await callback.message.edit_text(
            callback.message.text + "\n\n📝 <b>Отзыв принят!</b> Мы постоянно улучшаем алгоритм",
            parse_mode="HTML"
        )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command - show global stats"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/stats", timeout=10.0)

            if response.status_code == 200:
                data = response.json()
                total = data['total_analyses']
                avg_risk = data['average_risk_score']
                dist = data.get('risk_distribution', {})

                high_risk = dist.get('high', 0)
                estimated_savings = high_risk * 300

                stats_text = f"""
📈 <b>Статистика ScamGuard AI</b>

<b>Всего проверок:</b> {total:,}
<b>Средний риск:</b> {avg_risk:.1f}/100

<b>Распределение рисков:</b>
🔴 Высокий: {dist.get('high', 0)}
🟡 Средний: {dist.get('medium', 0)}
🟢 Низкий: {dist.get('low', 0)}

💰 <b>Предотвращено потерь:</b> ~${estimated_savings:,}

Вместе мы боремся с мошенниками! 💪
                """

                await message.answer(stats_text, parse_mode="HTML", reply_markup=create_main_menu())
            else:
                await message.answer("❌ Ошибка при получении статистики", reply_markup=create_main_menu())

    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await message.answer("❌ Произошла ошибка", reply_markup=create_main_menu())


@dp.message(Command("logs"))
async def cmd_logs(message: Message):
    """Handle /logs command - show recent bot logs"""
    try:
        log_file = Path("logs/bot.log")
        
        if not log_file.exists():
            await message.answer(
                "❌ Файл логов не найден",
                reply_markup=create_main_menu()
            )
            return
        
        # Read last 30 lines
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-30:]
        
        # Parse and format
        errors = 0
        warnings = 0
        info = 0
        
        formatted_logs = []
        
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # Simple parsing
            if '| ERROR |' in line:
                errors += 1
                emoji = '❌'
            elif '| WARNING |' in line:
                warnings += 1
                emoji = '⚠️'
            elif '| INFO |' in line:
                info += 1
                emoji = 'ℹ️'
            else:
                emoji = '📝'
            
            # Extract time and message
            parts = line.split('|')
            if len(parts) >= 3:
                time_part = parts[0].strip()
                msg_part = parts[-1].strip()[:80]
                formatted_logs.append(f"{emoji} <code>{time_part}</code> {msg_part}")
        
        # Build report
        report = f"""
📋 <b>ПОСЛЕДНИЕ СОБЫТИЯ БОТА</b>

📊 <b>Сводка:</b>
ℹ️ Информации: {info}
⚠️ Предупреждений: {warnings}
❌ Ошибок: {errors}

<b>Последние 15 событий:</b>
{'─' * 35}
"""
        
        for log_entry in formatted_logs[-15:]:
            report += f"{log_entry}\n"
        
        # Health status
        health = 100 - (errors * 10) - (warnings * 5)
        health = max(0, min(100, health))
        
        if health >= 80:
            health_emoji = '✅'
            health_text = 'ОТЛИЧНО'
        elif health >= 60:
            health_emoji = '⚠️'
            health_text = 'НОРМАЛЬНО'
        else:
            health_emoji = '❌'
            health_text = 'ПЛОХО'
        
        report += f"""
{'─' * 35}
{health_emoji} <b>Здоровье: {health_text} ({health}/100)</b>
"""
        
        # Split message if too long (Telegram limit ~4096 chars)
        if len(report) > 4000:
            report = report[:3900] + "\n\n... (продолжение в файле)"
        
        await message.answer(report, parse_mode="HTML", reply_markup=create_main_menu())
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        await message.answer(
            "❌ Ошибка при чтении логов",
            reply_markup=create_main_menu()
        )


@dp.message()
async def handle_any_message(message: Message):
    """Handle any other message (fallback)"""
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❓ Неизвестная команда\n\n"
            "Используйте /start для списка команд",
            reply_markup=create_main_menu()
        )
    elif message.text:
        await process_message_deep_analysis(
            message, message.text.strip(), [], is_forwarded=False
        )
    elif message.photo:
        caption = message.caption or ""
        await process_message_deep_analysis(
            message, caption, message.photo, is_forwarded=False
        )
    elif message.document:
        # If it's a file/document, analyze it
        document = message.document
        caption = message.caption or ""
        file_name = document.file_name or "unknown_file"
        file_size = document.file_size or 0
        file_ext = '.' + file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''
        file_type = DANGEROUS_FILE_EXTENSIONS.get(file_ext, 'unknown')

        await analyze_file_with_warning(
            message, file_name, file_ext, file_type, file_size,
            document.mime_type or "", caption
        )
    else:
        await message.answer(
            "🤔 Перешлите мне подозрительное сообщение или файл\n\n"
            "Используйте /start для помощи",
            reply_markup=create_main_menu()
        )


@dp.callback_query(F.data.startswith("deep_analysis:"))
async def callback_deep_analysis(callback: types.CallbackQuery):
    """Handle deep analysis button"""
    await callback.answer()
    
    message_id_str = callback.data.split(":")[1]
    try:
        message_id = int(message_id_str)
    except ValueError:
        await callback.answer("❌ Ошибка: неверный ID сообщения", show_alert=True)
        return

    user_id = callback.from_user.id
    
    # Send progress message
    progress_msg = await callback.message.answer(
        "🧠 <b>Запускаю глубокий AI анализ...</b>\n"
        "▰▰▰▱▱▱▱▱▱▱ 30%\n"
        "⏳ Загружаю сообщение",
        parse_mode="HTML"
    )
    
    try:
        async with httpx.AsyncClient() as client:
            # Get the full message data
            response = await client.get(
                f"{API_URL}/message/{message_id}",
                timeout=10.0
            )
            
            if response.status_code != 200:
                await progress_msg.edit_text(
                    "❌ <b>Сообщение не найдено</b>\n\n"
                    "Перешлите сообщение ещё раз для анализа.",
                    parse_mode="HTML",
                    reply_markup=create_main_menu()
                )
                return
            
            message_data = response.json()
            message_text = message_data.get('message_text', '')
            photo_count = message_data.get('photo_count', 0)
            is_forwarded = message_data.get('is_forwarded', False)
            forward_from = message_data.get('forward_from')
            
            if not message_text:
                await progress_msg.edit_text(
                    "<b>Текст сообщения пустой</b>\n\n"
                    "Перешлите сообщение ещё раз.",
                    parse_mode="HTML",
                    reply_markup=create_main_menu()
                )
                return

            # Update progress
            await progress_msg.edit_text(
                "<b>Глубокий AI анализ...</b>\n"
                "XXXXXX.... 60%\n"
                "Запускаю Gemini NLP",
                parse_mode="HTML"
            )
            
            # Prepare deep analysis request
            forward_info = {"from_user": forward_from} if forward_from else None
            
            payload = {
                "text": message_text,
                "user_id": user_id,
                "is_forwarded": is_forwarded,
                "forward_info": forward_info,
                "message_id": message_id,  # Link to quick check
                "photos": []  # Photos not stored in DB for deep analysis
            }
            
            # Run deep analysis (this will take 10-30 seconds)
            response = await client.post(
                f"{API_URL}/analyze-message-deep",
                json=payload,
                timeout=150.0  # Extended timeout for AI analysis with retries
            )
            
            if response.status_code == 200:
                deep_result = response.json()
                # Don't delete progress_msg - let send_detailed_result handle it
                await send_detailed_result(callback.message, deep_result, "Сообщение", progress_msg)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                try:
                    await progress_msg.edit_text(
                        f"Ошибка глубокого анализа: {error_detail}"
                    )
                except Exception:
                    await callback.message.answer(
                        f"Ошибка глубокого анализа: {error_detail}"
                    )

    except httpx.TimeoutException:
        try:
            await progress_msg.edit_text(
                "Превышено время ожидания\n\n"
                "AI анализ занимает 10-15 секунд.\n"
                "Попробуйте ещё раз или позже."
            )
        except Exception:
            await callback.message.answer(
                "Превышено время ожидания\n\n"
                "AI анализ занимает 10-15 секунд.\n"
                "Попробуйте ещё раз или позже."
            )
    except Exception as e:
        logger.error(f"Error in deep analysis callback: {e}")
        try:
            await progress_msg.edit_text(
                f"Произошла ошибка\n\n"
                f"Детали: {str(e)[:200]}\n\n"
                "Попробуйте позже или перешлите сообщение заново.",
                reply_markup=create_main_menu()
            )
        except Exception:
            await callback.message.answer(
                f"Произошла ошибка\n\n"
                f"Детали: {str(e)[:200]}\n\n"
                "Попробуйте позже или перешлите сообщение заново.",
                reply_markup=create_main_menu()
            )


async def on_startup():
    """Actions on bot startup"""
    logger.info("=" * 50)
    logger.info("ScamGuard AI Telegram Bot Starting...")
    logger.info("=" * 50)
    logger.info(f"Bot username: @{(await bot.get_me()).username}")
    logger.info(f"API URL: {API_URL}")
    logger.info("Bot is ready to protect users! 🛡️")
    logger.info("=" * 50)


async def on_shutdown():
    """Actions on bot shutdown"""
    logger.info("ScamGuard AI Bot shutting down...")
    await bot.session.close()


async def main():
    """Main function to run the bot"""
    # Startup actions
    await on_startup()
    
    # Delete webhook if exists
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    import os, atexit

    project_root = Path(__file__).resolve().parents[2]
    pid_file_env = os.environ.get("SCAMGUARD_BOT_PID_FILE")
    PID_FILE = Path(pid_file_env) if pid_file_env else project_root / ".bot.pid"

    # Check if another instance is already running
    if PID_FILE.exists():
        with open(PID_FILE) as f:
            existing_pid = f.read().strip()
        try:
            os.kill(int(existing_pid), 0)  # Check if process exists
            logger.error(f"Bot is already running (PID {existing_pid}). Exiting.")
            sys.exit(1)
        except (ProcessLookupError, ValueError):
            pass  # Stale PID file — process is dead, continue

    # Write current PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def cleanup_pid():
        try:
            if PID_FILE.exists():
                with open(PID_FILE) as f:
                    current_pid = f.read().strip()
                if current_pid == str(os.getpid()):
                    PID_FILE.unlink()
        except FileNotFoundError:
            pass

    atexit.register(cleanup_pid)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
