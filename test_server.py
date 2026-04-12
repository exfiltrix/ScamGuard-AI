#!/usr/bin/env python3
import sys
import os

# Add project root to path
sys.path.insert(0, '/home/exfiltrix/Projects/ScamGuard-AI')

print("🔍 Проверка импортов...")

try:
    print("1. Импорт pydantic_settings...")
    from pydantic_settings import BaseSettings
    print("   ✅ OK")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    sys.exit(1)

try:
    print("2. Импорт backend.config...")
    from backend.config import get_settings
    print("   ✅ OK")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    sys.exit(1)

try:
    print("3. Импорт backend.api.main...")
    from backend.api.main import app
    print("   ✅ OK")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Все импорты успешны! Запускаю сервер...")

import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
