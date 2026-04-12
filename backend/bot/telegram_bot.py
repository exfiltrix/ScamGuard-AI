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
from datetime import datetime

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


def escape_markdown(text: str) -> str:
    """
    Escape special Markdown characters in Telegram messages.
    
    Telegram Markdown special chars: * _ [ ] ( ) ~ ` > # + - = | { } . !
    We need to escape them to prevent parse errors.
    """
    if not text:
        return ""
    
    # Escape special Markdown characters
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.','!']
    escaped = text
    for char in escape_chars:
        escaped = escaped.replace(char, f"\\{char}")
    
    return escaped


def safe_markdown_text(text: str) -> str:
    """
    Safely escape text for Markdown parse mode.
    Use this for ANY dynamic content from user/AI.
    """
    return escape_markdown(text)


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


def create_main_menu():
    """Create main menu keyboard"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Проверить сообщение", callback_data="analyze")
        ],
        [
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats"),
            InlineKeyboardButton(text="📈 Общая статистика", callback_data="global_stats")
        ],
        [
            InlineKeyboardButton(text="📋 Логи бота", callback_data="bot_logs"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ],
        [
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")
        ]
    ])
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    user_name = message.from_user.first_name
    welcome_text = f"""
🛡️ **Добро пожаловать в ScamGuard AI, {user_name}!**

Я защищаю вас от онлайн-мошенников! 🚨

**🤖 Что я умею:**
• Анализирую сообщения от мошенников
• Detectирую 8 типов мошенничества
• 📁 **ПРОВЕРЯЮ ФАЙЛЫ** (.apk, .exe, .pdf и др.)
• Сравниваю с базой паттернов мошенников
• Даю персональные рекомендации

**⚡ Как это работает:**
1️⃣ Получили подозрительное сообщение/файл?
2️⃣ **Перешлите его мне** (или скопируйте текст)
3️⃣ Мгновенная проверка → оценка риска 0-100
4️⃣ Узнайте правду и защитите свои деньги!

**🎯 Поддерживается:**
• 📝 Пересланные сообщения из Telegram
• 📋 Скопированный текст
• 📁 **ФАЙЛЫ** (.apk, .exe, .pdf, .zip, .doc и др.)
• 🖼 Фотографии с объявлений
• 🔗 Ссылки на объявления

**Просто перешлите мне сообщение или файл!** 👇
    """
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=create_main_menu())


@dp.callback_query(F.data == "analyze")
async def callback_analyze(callback: types.CallbackQuery, state: FSMContext):
    """Handle analyze button"""
    await callback.answer()
    await state.set_state(AnalysisStates.waiting_for_message)
    await callback.message.answer(
        "📨 **Перешлите подозрительное сообщение**\n\n"
        "Поддерживаются:\n"
        "• 🔄 Пересланные сообщения из Telegram\n"
        "• 📝 Скопированный текст сообщения\n"
        "• 🖼 Фотографии (с объявления)\n"
        "• 🔗 Ссылки на объявления\n\n"
        "💡 **Совет:** Просто перешлите сообщение от мошенника!\n\n"
        "Или /cancel для отмены",
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "help")
async def callback_help(callback: types.CallbackQuery):
    """Handle help button"""
    await callback.answer()
    help_text = """
📖 **Подробная справка**

**🎯 Основные команды:**
/start - Главное меню
/analyze - Проверить сообщение
/history - История проверок
/stats - Статистика

**🔍 Что мы анализируем:**

1️⃣ **Типы мошенничества (8):**
   • 🏠 Аренда/продажа (поддельные объявления)
   • 💰 Инвестиции (финансовые пирамиды)
   • ❤️ Романтика (фейковые отношения)
   • 🔒 Фишинг (кража данных)
   • 👔 Работа (поддельные вакансии)
   • 🎁 Розыгрыши (фальшивые призы)
   • 💳 Кража карт
   • 🆘 Tech support scams

2️⃣ **📁 ПРОВЕРКА ФАЙЛОВ:**
   • 🔴 .exe, .msi, .bat, .cmd — ИСПОЛНЯЕМЫЕ (ВИРУСЫ!)
   • 🔴 .apk, .aab — Android приложения
   • 🟡 .docm, .xlsm — Документы с макросами
   • 🟡 .zip, .rar, .7z — Архивы
   • 🟢 .pdf — Документы (обычно безопасно)

3️⃣ **Психологические манипуляции:**
   • Срочность и давление
   • Обещания лёгких денег
   • Эмоциональный шантаж
   • Фейковый авторитет
   • Секретность

4️⃣ **Технический анализ:**
   • Проверка фото (дубликаты, качество)
   • Сравнение с 25 паттернами
   • 80+ правил детектирования
   • AI анализ (87% точность)

**⚡ Два режима проверки:**
⚡ **Быстрая** — мгновенно, 80+ правил
🧠 **Глубокая AI** — по кнопке, 10-15 сек

**⚠️ Уровни риска:**
🟢 0-29: Низкий риск
🟡 30-59: Средний риск
🔴 60-100: Высокий риск (мошенник!)

**💡 Помните:**
Это инструмент помощи, окончательное решение за вами!
    """
    await callback.message.answer(help_text, parse_mode="Markdown", reply_markup=create_main_menu())


@dp.callback_query(F.data == "about")
async def callback_about(callback: types.CallbackQuery):
    """Handle about button"""
    await callback.answer()
    about_text = """
🛡️ **О проекте ScamGuard AI**

**Миссия:**
Универсальная защита от ЛЮБЫХ онлайн-мошенников!

**Возможности:**
🎯 8 типов мошенничества (аренда, инвестиции, романтика, фишинг, работа...)
🧠 80+ правил детектирования
📊 25 паттернов в базе мошенников
🤖 AI анализ (Google Gemini 1.5 Flash)
🔍 Проверка фото на дубликаты
💡 Анализ психологических манипуляций

**Pipeline анализа (4 модуля):**
• Rule Engine (80+ правил, instant)
• Image Analysis (проверка фото)
• Embedding Analysis (сравнение с базой)
• AI Analysis (глубокий контекст)

**Доказанная эффективность:**
✅ 87% Precision (точность)
✅ 93% Recall (полнота)
✅ 30 тестовых примеров
✅ $0 стоимость (бесплатный AI!)

**Рынок:**
🌍 30M+ потенциальных пользователей
💰 $500M ущерба ежегодно от мошенников

**Команда:**
Создано с ❤️ для защиты людей

**Версия:** 0.4.0 (Universal Scam Detector)
    """
    await callback.message.answer(about_text, parse_mode="Markdown", reply_markup=create_main_menu())


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
                        "📊 **Ваша статистика**\n\n"
                        "У вас пока нет проверок.\n"
                        "Начните с кнопки '🔍 Проверить сообщение'!",
                        parse_mode="Markdown",
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
📊 **Ваша статистика**

**Всего проверок:** {total}

**Распределение рисков:**
🔴 Высокий: {high_risk} ({high_risk*100//total}%)
🟡 Средний: {medium_risk} ({medium_risk*100//total}%)
🟢 Низкий: {low_risk} ({low_risk*100//total}%)

**Средний риск:** {avg_risk:.1f}/100

**Последние проверки:**
"""
                
                for i, item in enumerate(history[:3], 1):
                    risk_emoji = "🟢" if item['risk_level'] == 'low' else "🟡" if item['risk_level'] == 'medium' else "🔴"
                    date = item['created_at'][:10]
                    stats_text += f"\n{i}. {risk_emoji} Риск {item['risk_score']}/100 ({date})"
                
                if high_risk > 0:
                    stats_text += f"\n\n✅ **Вы избежали {high_risk} мошенничеств!**"
                
                await callback.message.answer(stats_text, parse_mode="Markdown", reply_markup=create_main_menu())
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
📈 **Общая статистика ScamGuard AI**

**Всего проверок:** {total:,}
**Средний риск:** {avg_risk:.1f}/100

**Распределение:**
🟢 Низкий риск: {dist.get('low', 0)}
🟡 Средний риск: {dist.get('medium', 0)}
🔴 Высокий риск: {dist.get('high', 0)}

💰 **Предотвращено потерь:** ~${estimated_savings:,}

**Топ красные флаги:**
• Подозрительная цена
• Требование предоплаты
• Срочность и давление
• Отсутствие контактов

🎯 **Миссия:** Защитить людей от мошенников!
                """

                await callback.message.answer(stats_text, parse_mode="Markdown", reply_markup=create_main_menu())
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
                formatted_logs.append(f"{emoji} `{time_part}` {msg_part}")
        
        # Build report
        report = f"""
📋 **ЛОГИ БОТА**

📊 **Сводка:**
ℹ️ Информации: {info}
⚠️ Предупреждений: {warnings}
❌ Ошибок: {errors}

**Последние события:**
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
{health_emoji} **Здоровье: {health_text} ({health}/100)**

💡 **Команды:**
• `/logs` — показать логи в боте
• `/stats` — общая статистика
"""
        
        if len(report) > 4000:
            report = report[:3900] + "\n..."
        
        await callback.message.answer(report, parse_mode="Markdown", reply_markup=create_main_menu())
        
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
                
                text = f"📋 **Ваша история проверок** (последние {len(history)}):\n\n"
                
                for i, item in enumerate(history, 1):
                    risk_emoji = "🟢" if item['risk_level'] == 'low' else "🟡" if item['risk_level'] == 'medium' else "🔴"
                    url_short = item['url'][:40] + "..." if len(item['url']) > 40 else item['url']
                    date = item['created_at'][:16].replace('T', ' ')
                    
                    text += f"{i}. {risk_emoji} **{item['risk_score']}/100**\n"
                    text += f"   `{url_short}`\n"
                    text += f"   📅 {date}\n\n"
                
                await message.answer(text, parse_mode="Markdown", reply_markup=create_main_menu())
            else:
                await message.answer("❌ Ошибка при получении истории", reply_markup=create_main_menu())
                
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        await message.answer("❌ Ошибка при получении истории", reply_markup=create_main_menu())


@dp.message(AnalysisStates.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    """Process message: quick check first, then offer deep analysis"""
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
            parse_mode="Markdown",
            reply_markup=create_main_menu()
        )
        return

    # NEW FLOW: Quick check first
    await process_message_quick_then_offer_deep(
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
    # NEW FLOW: Quick check first
    await process_message_quick_then_offer_deep(
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

    # NEW FLOW: Quick check first
    await process_message_quick_then_offer_deep(
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

    # NEW FLOW: Quick check first
    await process_message_quick_then_offer_deep(
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

    # Build result message
    risk_bars = '▰' * (risk_score // 10) + '▱' * (10 - risk_score // 10)

    result_text = f"""
{emoji}═══════════════════════════{emoji}
       📁 **АНАЛИЗ ФАЙЛА**
{emoji}═══════════════════════════{emoji}

📄 **Файл:** `{file_name}`
📏 **Размер:** {file_size // 1024 if file_size > 1024 else file_size} {'MB' if file_size > 1024*1024 else 'KB' if file_size > 1024 else 'B'}
📦 **Тип:** {file_ext.upper() if file_ext else 'Неизвестно'}

{emoji} **Статус:** {level_text}
📊 **Оценка риска:** {risk_score}/100

{risk_bars}

🔍 **Обнаружено проблем:** {len(red_flags)}
"""

    # Show red flags
    if red_flags:
        result_text += "\n⚠️ **Предупреждения:**\n"
        for flag in red_flags[:6]:
            result_text += f"{flag['description']}\n"

    # Add recommendations
    if recommendations:
        result_text += "\n💡 **Рекомендации:**\n"
        for i, rec in enumerate(recommendations[:5], 1):
            result_text += f"{i}. {rec}\n"

    # Always add general file safety advice
    result_text += "\n🔒 **Правила безопасности:**\n"
    result_text += "• Не устанавливайте файлы от неизвестных\n"
    result_text += "• Проверяйте антивирусом перед открытием\n"
    result_text += "• Не включайте макросы в документах\n"

    await message.answer(result_text, parse_mode="Markdown")

    # Offer deep analysis for context
    if caption and risk_score < 70:
        # If there's caption text, offer deep text analysis
        deep_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Анализ текста сообщения",
                    callback_data="analyze"
                )
            ],
            [
                InlineKeyboardButton(text="🏠 Главная", callback_data="main_menu")
            ]
        ])

        await message.answer(
            "📝 Хотите проанализировать **текст сообщения**?\n\n"
            "Бот проверит текст на признаки мошенничества.",
            parse_mode="Markdown",
            reply_markup=deep_keyboard
        )


async def analyze_url(message: Message, url: str):
    """Analyze URL and send results with beautiful formatting"""
    user_id = message.from_user.id

    # Send animated "analyzing" messages
    status_msg = await message.answer("🔍 **Начинаю анализ...**", parse_mode="Markdown")

    await asyncio.sleep(1)
    await status_msg.edit_text("🔍 **Парсинг данных...**\n⏳ Загружаю информацию", parse_mode="Markdown")

    try:
        async with httpx.AsyncClient() as client:
            # Show progress
            await asyncio.sleep(1.5)
            await status_msg.edit_text(
                "🔍 **Анализирую данные...**\n"
                "▰▰▰▱▱▱▱▱▱▱ 30%\n"
                "⏳ Проверяю текст и фото",
                parse_mode="Markdown"
            )

            response = await client.post(
                f"{API_URL}/analyze",
                json={"url": url, "user_id": user_id},
                timeout=60.0
            )

            await status_msg.edit_text(
                "🔍 **Финализирую результаты...**\n"
                "▰▰▰▰▰▰▰▰▰▱ 90%\n"
                "⏳ Генерирую рекомендации",
                parse_mode="Markdown"
            )

            if response.status_code == 200:
                result = response.json()
                await send_detailed_result(message, result, url, status_msg)
            else:
                error_detail = response.json().get('detail', 'Unknown error')
                await status_msg.edit_text(f"❌ **Ошибка анализа:**\n{error_detail}", parse_mode="Markdown")

    except httpx.TimeoutException:
        await status_msg.edit_text(
            "❌ **Превышено время ожидания**\n\n"
            "Возможные причины:\n"
            "• Сообщение слишком большое\n"
            "• Проблемы с сетью\n\n"
            "Попробуйте позже или другую ссылку",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error analyzing URL: {e}")
        await status_msg.edit_text(
            "❌ **Произошла ошибка**\n\n"
            f"Детали: `{str(e)[:100]}`\n\n"
            "Попробуйте другую ссылку или обратитесь в поддержку",
            parse_mode="Markdown"
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

    # Check for file attachments (from message.document)
    has_file = False
    file_count = 0
    # Note: document is handled separately in handle_document_message
    # For text/photo messages, has_file stays False

    # Step 1: Quick check (instant)
    status_msg = await message.answer(
        "⚡ **Быстрая проверка...**\n"
        "▰▰▰▱▱▱▱▱▱▱ 30%\n"
        "⏳ Проверяю по 80+ правилам",
        parse_mode="Markdown"
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
                    f"❌ **Ошибка быстрой проверки:**\n{error_detail}",
                    parse_mode="Markdown"
                )

    except httpx.TimeoutException:
        await status_msg.edit_text(
            "❌ **Быстрая проверка не удалась**\n\n"
            "Превышено время ожидания.\n"
            "Попробуйте позже.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error in quick check: {e}")
        await status_msg.edit_text(
            "❌ **Произошла ошибка**\n\n"
            f"Детали: `{str(e)[:100]}`",
            parse_mode="Markdown"
        )


async def send_quick_result(
    message: Message,
    result: dict,
    text: str,
    status_msg: Message,
    message_id: int
):
    """Show quick check results with button for deep analysis"""
    risk_score = result['risk_score']
    risk_level = result['risk_level']
    red_flags = result.get('red_flags', [])

    # Delete status message
    await status_msg.delete()

    # Determine status label based on risk level
    if risk_level == 'low':
        level_text = "НИЗКИЙ РИСК"
        status_label = "[OK]"
    elif risk_level == 'medium':
        level_text = "СРЕДНИЙ РИСК"
        status_label = "[!]"
    else:
        level_text = "ВЫСОКИЙ РИСК"
        status_label = "[!!!]"

    # Create visual risk bar
    risk_bars = "X" * (risk_score // 10) + "." * (10 - risk_score // 10)

    # Build quick result message
    result_text = f"""
{'=' * 35}
      БЫСТРАЯ ПРОВЕРКА
{'=' * 35}

{status_label} Статус: {level_text}
Оценка риска: {risk_score}/100

[{risk_bars}]

Найдено проблем: {len(red_flags)}
"""

    # Show top flags (ESCAPE Markdown special chars!)
    if red_flags:
        result_text += "\nОбнаружено:\n"
        for i, flag in enumerate(red_flags[:5], 1):
            severity_label = "[!!]" if flag['severity'] >= 7 else "[!]" if flag['severity'] >= 5 else "[-]"
            # Escape description text to prevent Markdown parse errors
            safe_desc = safe_markdown_text(flag['description'])
            result_text += f"  {i}. {severity_label} {safe_desc}\n"

    # Add consultation-style advice
    result_text += f"\nРекомендация: "
    if risk_score >= 60:
        result_text += "Подозрительное сообщение. Рекомендую провести глубокий AI анализ для точного вердикта."
    elif risk_score >= 30:
        result_text += "Есть подозрительные признаки. Хотите глубокий анализ?"
    else:
        result_text += "Явных признаков мошенничества нет, но будьте бдительны."

    # Send as plain text (no parse_mode to avoid errors)
    await message.answer(result_text)

    # Button for deep analysis
    deep_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Глубокий AI анализ",
                callback_data=f"deep_analysis:{message_id}"
            )
        ],
        [
            InlineKeyboardButton(text="Проверить ещё", callback_data="analyze"),
            InlineKeyboardButton(text="Главная", callback_data="main_menu")
        ]
    ])

    await message.answer(
        "Хотите узнать больше?\n\n"
        "Запустите полный AI анализ с Gemini:\n"
        "- Глубокое понимание контекста\n"
        "- Определение тактик манипуляции\n"
        "- Анализ фото (если есть)\n"
        "- Точный вердикт за 10-15 секунд",
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
            "**Запускаю глубокий AI анализ...**\n"
            "XXX....... 30%\n"
            "Анализирую контекст сообщения",
            parse_mode="Markdown"
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
                "**Требуется сообщение**\n\n"
                "Пожалуйста, перешлите сообщение ещё раз,\n"
                "и сразу запустится полный AI анализ.\n\n"
                "Или используйте команду /analyze",
                parse_mode="Markdown",
                reply_markup=create_main_menu()
            )

    except Exception as e:
        logger.error(f"Error in deep analysis: {e}")
        await callback.message.answer(
            "**Ошибка глубокого анализа**\n\n"
            "Попробуйте позже или обратитесь в поддержку",
            parse_mode="Markdown"
        )


async def analyze_message(message: Message, text: str, photos: list, is_forwarded: bool = False):
    """
    LEGACY FUNCTION - kept for compatibility
    Use process_message_quick_then_offer_deep instead
    """
    logger.warning("Using legacy analyze_message function")
    await process_message_quick_then_offer_deep(message, text, photos, is_forwarded)


async def send_detailed_result(message: Message, result: dict, url: str, status_msg: Message):
    """Format and send detailed analysis result"""
    risk_score = result['risk_score']
    risk_level = result['risk_level']
    red_flags = result.get('red_flags', [])
    recommendations = result.get('recommendations', [])
    details = result.get('details', {})

    # Delete status message (safely - ignore if already deleted)
    try:
        await status_msg.delete()
    except Exception as e:
        logger.debug(f"Could not delete status message (already deleted?): {e}")

    # Determine status label based on risk level
    if risk_level == 'low':
        level_text = "НИЗКИЙ РИСК"
        level_desc = "Относительно безопасно"
        status_label = "[OK]"
    elif risk_level == 'medium':
        level_text = "СРЕДНИЙ РИСК"
        level_desc = "Будьте осторожны"
        status_label = "[!]"
    else:
        level_text = "ВЫСОКИЙ РИСК"
        level_desc = "Вероятно мошенничество"
        status_label = "[!!!]"

    # Create visual risk bar
    risk_bars = "X" * (risk_score // 10) + "." * (10 - risk_score // 10)

    # Build main result message
    result_text = f"""
{'=' * 39}
        РЕЗУЛЬТАТ АНАЛИЗА
{'=' * 39}

{status_label} Статус: {level_text}
Оценка риска: {risk_score}/100

[{risk_bars}]

Вердикт: {level_desc}
"""

    # Add component scores if available
    component_scores = details.get('component_scores', {})
    if component_scores:
        result_text += "\nДетали анализа:\n"
        result_text += f"  - Правила: {component_scores.get('rule_engine', 0)}/100\n"
        if 'nlp_llm' in component_scores:
            result_text += f"  - AI: {component_scores.get('nlp_llm', 0)}/100\n"
        if 'embedding' in component_scores:
            result_text += f"  - Паттерны: {component_scores.get('embedding', 0)}/100\n"

    await message.answer(result_text)

    # Send red flags if any (ESCAPE Markdown!)
    if red_flags:
        flags_text = "ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:\n\n"

        # Group by severity
        critical = [f for f in red_flags if f['severity'] >= 8]
        high = [f for f in red_flags if 5 <= f['severity'] < 8]
        medium = [f for f in red_flags if f['severity'] < 5]

        if critical:
            flags_text += "[!!!] Критические:\n"
            for i, flag in enumerate(critical[:3], 1):
                safe_desc = safe_markdown_text(flag['description'])
                flags_text += f"  {i}. {safe_desc}\n"
            flags_text += "\n"

        if high:
            flags_text += "[!!] Серьезные:\n"
            for i, flag in enumerate(high[:3], 1):
                safe_desc = safe_markdown_text(flag['description'])
                flags_text += f"  {i}. {safe_desc}\n"
            flags_text += "\n"

        if medium:
            flags_text += "[-] Предупреждения:\n"
            for i, flag in enumerate(medium[:2], 1):
                safe_desc = safe_markdown_text(flag['description'])
                flags_text += f"  {i}. {safe_desc}\n"

        await message.answer(flags_text)

    # Send recommendations (ESCAPE Markdown!)
    if recommendations:
        rec_text = "РЕКОМЕНДАЦИИ:\n\n"
        for i, rec in enumerate(recommendations[:6], 1):
            safe_rec = safe_markdown_text(rec)
            rec_text += f"  {i}. {safe_rec}\n\n"

        await message.answer(rec_text)
    
    # Add action buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Детальный отчет", callback_data=f"details_{url}"),
        ],
        [
            InlineKeyboardButton(text="Проверить еще", callback_data="analyze"),
            InlineKeyboardButton(text="Главная", callback_data="main_menu")
        ]
    ])

    # Final message with link
    final_text = f"[Открыть ссылку]({url})\n\n"

    if risk_score >= 70:
        final_text += "[!!!] Настоятельно рекомендуем избегать контакта с этим источником!"
    elif risk_score >= 50:
        final_text += "[!] Проявите особую осторожность при взаимодействии"
    else:
        final_text += "[OK] Но всегда соблюдайте общие меры безопасности"
    
    await message.answer(final_text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=keyboard)
    
    # Ask for feedback if high risk
    if risk_score > 40:
        feedback_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Точный анализ", callback_data=f"feedback_good"),
                InlineKeyboardButton(text="Неточно", callback_data=f"feedback_bad")
            ]
        ])
        await message.answer(
            "**Помогите улучшить систему**\n"
            "Наш анализ был точным?",
            parse_mode="Markdown",
            reply_markup=feedback_keyboard
        )


@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    """Return to main menu"""
    await callback.answer()
    await callback.message.answer(
        "🏠 **Главное меню**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=create_main_menu()
    )


@dp.callback_query(F.data.startswith('feedback_'))
async def process_feedback(callback: types.CallbackQuery):
    """Process feedback callback"""
    feedback = callback.data.replace('feedback_', '')
    
    if feedback == 'good':
        await callback.answer("Спасибо за отзыв! 🙏", show_alert=True)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ **Спасибо за отзыв!** Вы помогаете нам стать лучше 💙",
            parse_mode="Markdown"
        )
    else:
        await callback.answer("Мы учтем ваш отзыв для улучшения!", show_alert=True)
        await callback.message.edit_text(
            callback.message.text + "\n\n📝 **Отзыв принят!** Мы постоянно улучшаем алгоритм",
            parse_mode="Markdown"
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
📈 **Статистика ScamGuard AI**

**Всего проверок:** {total:,}
**Средний риск:** {avg_risk:.1f}/100

**Распределение рисков:**
🔴 Высокий: {dist.get('high', 0)}
🟡 Средний: {dist.get('medium', 0)}
🟢 Низкий: {dist.get('low', 0)}

💰 **Предотвращено потерь:** ~${estimated_savings:,}

Вместе мы боремся с мошенниками! 💪
                """

                await message.answer(stats_text, parse_mode="Markdown", reply_markup=create_main_menu())
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
                formatted_logs.append(f"{emoji} `{time_part}` {msg_part}")
        
        # Build report
        report = f"""
📋 **ПОСЛЕДНИЕ СОБЫТИЯ БОТА**

📊 **Сводка:**
ℹ️ Информации: {info}
⚠️ Предупреждений: {warnings}
❌ Ошибок: {errors}

**Последние 15 событий:**
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
{health_emoji} **Здоровье: {health_text} ({health}/100)**
"""
        
        # Split message if too long (Telegram limit ~4096 chars)
        if len(report) > 4000:
            report = report[:3900] + "\n\n... (продолжение в файле)"
        
        await message.answer(report, parse_mode="Markdown", reply_markup=create_main_menu())
        
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
        # If it's just text, use quick check
        await process_message_quick_then_offer_deep(
            message, message.text.strip(), [], is_forwarded=False
        )
    elif message.photo:
        # If it's a photo, use quick check
        caption = message.caption or ""
        await process_message_quick_then_offer_deep(
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
        "🧠 **Запускаю глубокий AI анализ...**\n"
        "▰▰▰▱▱▱▱▱▱▱ 30%\n"
        "⏳ Загружаю сообщение",
        parse_mode="Markdown"
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
                    "❌ **Сообщение не найдено**\n\n"
                    "Перешлите сообщение ещё раз для анализа.",
                    parse_mode="Markdown",
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
                    "**Текст сообщения пустой**\n\n"
                    "Перешлите сообщение ещё раз.",
                    parse_mode="Markdown",
                    reply_markup=create_main_menu()
                )
                return

            # Update progress
            await progress_msg.edit_text(
                "**Глубокий AI анализ...**\n"
                "XXXXXX.... 60%\n"
                "Запускаю Gemini NLP",
                parse_mode="Markdown"
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

    PID_FILE = "/tmp/scamguard_bot.pid"

    # Check if another instance is already running
    if os.path.exists(PID_FILE):
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
            os.remove(PID_FILE)
        except FileNotFoundError:
            pass

    atexit.register(cleanup_pid)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
