#!/bin/bash

# ScamGuard AI - Stop Script

echo "🛑 Stopping ScamGuard AI..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
BOT_PID_FILE=".bot.pid"
API_PID_FILE=".api.pid"

# Stop API
if [ -f "$API_PID_FILE" ]; then
    API_PID=$(cat "$API_PID_FILE")
    if [ -n "$API_PID" ] && kill -0 "$API_PID" 2>/dev/null; then
        echo "Stopping API server (PID: $API_PID)..."
        kill "$API_PID"
        echo -e "${GREEN}✓${NC} API server stopped"
    else
        echo "Removing stale API PID file ($API_PID_FILE)"
    fi
    rm -f "$API_PID_FILE"
fi

# Stop Bot
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE")
    if [ -n "$BOT_PID" ] && kill -0 "$BOT_PID" 2>/dev/null; then
        echo "Stopping Telegram bot (PID: $BOT_PID)..."
        kill "$BOT_PID"
        echo -e "${GREEN}✓${NC} Telegram bot stopped"
    else
        echo "Removing stale bot PID file ($BOT_PID_FILE)"
    fi
    rm -f "$BOT_PID_FILE"
fi

# Kill any remaining processes on port 8000
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Killing remaining processes on port 8000..."
    kill $(lsof -t -i:8000) 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
