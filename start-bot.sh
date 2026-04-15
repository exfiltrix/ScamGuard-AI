#!/bin/bash

cd /home/exfiltrix/Projects/ScamGuard-AI

echo "🤖 Starting Telegram Bot..."

PID_FILE="$(pwd)/.bot.pid"
LOG_FILE="$(pwd)/logs/bot.log"

# Ensure runtime directories exist
mkdir -p logs

# Set PYTHONPATH
export PYTHONPATH=$(pwd)
export SCAMGUARD_BOT_PID_FILE="$PID_FILE"

# Refuse duplicate start, but clean stale PID state
if [ -f "$PID_FILE" ]; then
    EXISTING_PID=$(cat "$PID_FILE")
    if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "⚠️ Telegram bot is already running (PID: $EXISTING_PID)"
        echo "📋 Logs: tail -f $LOG_FILE"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Start bot
nohup ./venv/bin/python backend/bot/telegram_bot.py > "$LOG_FILE" 2>&1 &
BOT_PID=$!

for _ in 1 2 3 4 5 6 7 8; do
    if ! kill -0 "$BOT_PID" 2>/dev/null; then
        break
    fi

    if [ -f "$PID_FILE" ]; then
        break
    fi

    sleep 1
done

if kill -0 "$BOT_PID" 2>/dev/null && [ -f "$PID_FILE" ]; then
    echo "✅ Telegram bot started (PID: $BOT_PID)"
    echo "📱 Bot username: @ScamGuardAI_bot"
    echo "📋 Logs: tail -f $LOG_FILE"
    echo ""
    echo "Bot commands:"
    echo "  /start - Начать"
    echo "  /analyze - Проверить объявление"
    echo "  /help - Справка"
else
    echo "❌ Bot failed to start"
    rm -f "$PID_FILE"
    echo "Logs:"
    tail -20 "$LOG_FILE"
    exit 1
fi
