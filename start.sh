#!/bin/bash

# ScamGuard AI - Startup Script
# Автоматический запуск всех сервисов

set -e

echo "🛡️  ScamGuard AI - Starting..."
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo "Создаю из .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Пожалуйста, заполните .env файл с вашими API ключами${NC}"
    echo "   - OPENAI_API_KEY"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo ""
    read -p "Нажмите Enter после заполнения .env..."
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 не установлен!${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1,2)
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} найден"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Виртуальное окружение создано"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓${NC} Виртуальное окружение активировано"

# Install/update dependencies
echo "📦 Проверяю зависимости..."
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt
echo -e "${GREEN}✓${NC} Зависимости установлены"

# Create necessary directories
mkdir -p logs data
echo -e "${GREEN}✓${NC} Директории созданы"

# Check if ports are available
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Порт 8000 уже занят${NC}"
    echo "Останавливаю существующий процесс..."
    kill $(lsof -t -i:8000) 2>/dev/null || true
    sleep 2
fi

echo ""
echo "================================"
echo "🚀 Запускаю сервисы..."
echo "================================"
echo ""

# Start API server in background
echo "1️⃣  Запускаю API сервер..."
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓${NC} API сервер запущен (PID: $API_PID)"
echo "   Логи: logs/api.log"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"

# Wait for API to start
echo ""
echo "⏳ Жду запуска API сервера..."
sleep 5

# Check if API is running
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓${NC} API сервер готов!"
else
    echo -e "${RED}❌ API сервер не отвечает${NC}"
    echo "Проверьте logs/api.log для деталей"
    exit 1
fi

echo ""
echo "2️⃣  Запускаю Telegram бота..."
python backend/bot/telegram_bot.py > logs/bot.log 2>&1 &
BOT_PID=$!
echo -e "${GREEN}✓${NC} Telegram бот запущен (PID: $BOT_PID)"
echo "   Логи: logs/bot.log"

# Save PIDs for stopping
echo $API_PID > .api.pid
echo $BOT_PID > .bot.pid

echo ""
echo "================================"
echo -e "${GREEN}✅ Все сервисы запущены!${NC}"
echo "================================"
echo ""
echo "📊 Мониторинг:"
echo "   API:  tail -f logs/api.log"
echo "   Bot:  tail -f logs/bot.log"
echo ""
echo "🛑 Для остановки:"
echo "   ./stop.sh"
echo ""
echo "🔗 Ссылки:"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Telegram: найдите вашего бота в Telegram"
echo ""
echo "🛡️  ScamGuard AI защищает пользователей!"
echo "================================"
