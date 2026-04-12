#!/usr/bin/env python3
"""
Тестирование ScamGuard AI на разных типах мошенничества
"""
import asyncio
import httpx
import json
from pathlib import Path


async def test_scam_detection():
    """Test ScamGuard AI on different scam types"""
    
    print("🧪 Тестирование ScamGuard AI - Универсальный детектор мошенничества")
    print("=" * 80)
    
    # Load test dataset
    dataset_path = Path("data/test_dataset_universal.json")
    
    if not dataset_path.exists():
        print("❌ Test dataset not found!")
        return
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Test examples from different categories
    test_cases = [
        {"id": 1, "type": "rental", "name": "Поддельная аренда"},
        {"id": 2, "type": "investment", "name": "Финансовая пирамида"},
        {"id": 3, "type": "romance", "name": "Романтический мошенник"},
        {"id": 4, "type": "phishing", "name": "Фишинг банка"},
        {"id": 5, "type": "job", "name": "Поддельная работа"},
        {"id": 24, "type": "safe", "name": "Легальная аренда"},
    ]
    
    print(f"\n📊 Найдено примеров в датасете: {len(data['listings'])}")
    print(f"   Категории: {data['metadata']['scam_types']}")
    print(f"\n⏳ Начинаю тестирование...\n")
    
    results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test_case in test_cases:
            # Find example in dataset
            example = next((l for l in data['listings'] if l['id'] == test_case['id']), None)
            
            if not example:
                print(f"❌ Пример {test_case['id']} не найден")
                continue
            
            print(f"\n{'='*80}")
            print(f"🧪 Тест #{test_case['id']}: {test_case['name']} ({test_case['type']})")
            print(f"{'='*80}")
            print(f"📝 Текст: {example['text'][:150]}...")
            print(f"🎯 Expected: {example['ground_truth_score']} (scam={example['is_scam']})")
            
            # Create test URL (mock)
            test_url = f"https://t.me/test/{test_case['id']}"
            
            # Call API (using mock parser will extract text from listing)
            # For real test, we'd need actual URLs or update parser
            print(f"\n⏳ Анализ через API...")
            
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/analyze",
                    json={
                        "url": test_url,
                        "user_id": 999,
                        "text_override": example['text']  # For testing
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"\n✅ Результат:")
                    print(f"   Risk Score: {result['risk_score']}/100")
                    print(f"   Risk Level: {result['risk_level']}")
                    print(f"   Красных флагов: {len(result['red_flags'])}")
                    
                    if result['red_flags']:
                        print(f"\n   🚩 Топ-3 флага:")
                        for flag in result['red_flags'][:3]:
                            print(f"      • {flag['category']}: {flag['description']}")
                    
                    # Check accuracy
                    score_diff = abs(result['risk_score'] - example['ground_truth_score'])
                    if score_diff <= 15:
                        print(f"\n   ✅ Точность: ОТЛИЧНО (ошибка {score_diff} баллов)")
                    elif score_diff <= 25:
                        print(f"\n   ⚠️ Точность: НОРМА (ошибка {score_diff} баллов)")
                    else:
                        print(f"\n   ❌ Точность: ПЛОХО (ошибка {score_diff} баллов)")
                    
                    results.append({
                        "test": test_case['name'],
                        "expected": example['ground_truth_score'],
                        "actual": result['risk_score'],
                        "error": score_diff,
                        "correct": score_diff <= 15
                    })
                else:
                    print(f"❌ API error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Ошибка: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    
    if results:
        correct = sum(1 for r in results if r['correct'])
        avg_error = sum(r['error'] for r in results) / len(results)
        
        print(f"\n✅ Протестировано: {len(results)} примеров")
        print(f"✅ Точных: {correct}/{len(results)} ({correct/len(results)*100:.1f}%)")
        print(f"✅ Средняя ошибка: {avg_error:.1f} баллов")
        
        print(f"\n📋 Детали:")
        for r in results:
            status = "✅" if r['correct'] else "❌"
            print(f"   {status} {r['test']}: {r['expected']} → {r['actual']} (ошибка: {r['error']})")
    
    print(f"\n{'='*80}")
    print(f"✅ Тестирование завершено!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    print("\n🛡️ ScamGuard AI - Тестирование универсального детектора\n")
    asyncio.run(test_scam_detection())
