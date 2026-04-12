#!/bin/bash

echo "🛡️  ScamGuard AI - Quick Start"
echo "================================"

cd /home/exfiltrix/Projects/ScamGuard-AI

# Check .env
if [ ! -f .env ]; then
    echo "❌ .env not found"
    exit 1
fi

# Create dirs
mkdir -p logs data

# Start API
echo "🚀 Starting API server..."
nohup ./venv/bin/python test_server.py > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > .api.pid

sleep 5

# Check health
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ API server running (PID: $API_PID)"
    echo "   URL: http://localhost:8000"
    echo "   Docs: http://localhost:8000/docs"
    echo "   Logs: tail -f logs/api.log"
else
    echo "❌ API server failed to start"
    cat logs/api.log | tail -20
    exit 1
fi

echo ""
echo "🎉 ScamGuard AI is running!"
