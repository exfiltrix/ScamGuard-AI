#!/bin/bash

# ScamGuard AI - Stop Script

echo "🛑 Stopping ScamGuard AI..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Stop API
if [ -f .api.pid ]; then
    API_PID=$(cat .api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo "Stopping API server (PID: $API_PID)..."
        kill $API_PID
        echo -e "${GREEN}✓${NC} API server stopped"
    fi
    rm .api.pid
fi

# Stop Bot
if [ -f .bot.pid ]; then
    BOT_PID=$(cat .bot.pid)
    if kill -0 $BOT_PID 2>/dev/null; then
        echo "Stopping Telegram bot (PID: $BOT_PID)..."
        kill $BOT_PID
        echo -e "${GREEN}✓${NC} Telegram bot stopped"
    fi
    rm .bot.pid
fi

# Kill any remaining processes on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Killing remaining processes on port 8000..."
    kill $(lsof -t -i:8000) 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
