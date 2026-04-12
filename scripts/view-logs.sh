#!/bin/bash
# ScamGuard AI - Анализ логов бота
# Автоматическая обработка с красивым оформлением

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/bot.log"

echo ""
echo "🛡️  ScamGuard AI - Анализатор логов"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "❌ Файл логов не найден: $LOG_FILE"
    exit 1
fi

# Check if log file is empty
if [ ! -s "$LOG_FILE" ]; then
    echo "⚠️  Файл логов пустой"
    exit 0
fi

echo "📁 Лог файл: $LOG_FILE"
echo "📏 Размер: $(du -h "$LOG_FILE" | cut -f1)"
echo "📝 Строк: $(wc -l < "$LOG_FILE")"
echo ""
echo "⏳ Анализирую..."
echo ""

# Run Python analyzer
cd "$PROJECT_DIR"
source venv/bin/activate 2>/dev/null
python scripts/analyze_logs.py "$LOG_FILE"

# Check if HTML was generated
HTML_REPORT="$PROJECT_DIR/logs/bot_report.html"
if [ -f "$HTML_REPORT" ]; then
    echo ""
    echo "🌐 Открыть HTML отчёт:"
    echo "   xdg-open $HTML_REPORT"
    echo ""
fi
