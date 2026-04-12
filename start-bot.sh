#!/bin/bash

cd /home/exfiltrix/Projects/ScamGuard-AI

echo "🤖 Starting Telegram Bot..."

# Set PYTHONPATH
export PYTHONPATH=$(pwd)

# Start bot
nohup ./venv/bin/python backend/bot/telegram_bot.py > logs/bot.log 2>&1 &
BOT_PID=$!
echo $BOT_PID > .bot.pid

sleep 4

if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "✅ Telegram bot started (PID: $BOT_PID)"
    echo "📱 Найдите вашего бота в Telegram: @your_bot_name"
    echo "📋 Логи: tail -f logs/bot.log"
    echo ""
    echo "Команды бота:"
    echo "  /start - Начать"
    echo "  /analyze - Проверить объявление"
    echo "  /help - Справка"
else
    echo "❌ Bot failed to start"
    echo "Логи:"
    tail -20 logs/bot.log
    exit 1
fi
