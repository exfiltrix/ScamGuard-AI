"""
Тест улучшенного NLP промпта для Gemini Analysis v2.0
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.services.gemini_analyzer import GeminiAnalyzer
from backend.models.schemas import ListingData
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


async def test_prompt_improvements():
    """Test the improved prompt with various scenarios"""
    
    # Initialize analyzer
    analyzer = GeminiAnalyzer()
    
    # Test cases
    test_cases = [
        {
            "name": "🔴 ВЫСОКИЙ РИСК - Классическая схема аренды",
            "text": """
СРОЧНО! 2-комнатная квартира в центре Ташкента по супер цене!
Всего 800,000 сум/месяц (рынок 2,500,000)
Евроремонт, мебель, центр города!

Для бронирования нужна 100% предоплата на карту Uzum Bank.
Договор не нужен - мы же честные люди!
Просмотр невозможен - я сейчас в командировке в Москве.

Пишите ТОЛЬКО в WhatsApp: +998901234567
Звонить НЕ БЕСПОКОИТЬ!

Предложение действует только СЕГОДНЯ! 
Уже 5 человек хотят, кто первый оплатит, тому и квартира!
            """,
            "expected_risk": "80-95",
            "expected_flags": ["предоплата", "нет договора", "нет просмотра", "срочность", "только мессенджер", "низкая цена"]
        },
        {
            "name": "🟢 НИЗКИЙ РИСК - Нормальное объявление",
            "text": """
Сдается 2-комнатная квартира в Мирзо-Улугбекском районе Ташкента.
Площадь: 65 кв.м, 3 этаж из 9, евроремонт 2022 года.
Мебель: диван, кровать, шкаф, кухонный гарнитур.
Техника: холодильник, стиральная машина, кондиционер.

Цена: 3,500,000 сум/месяц
Депозит: 3,500,000 сум (возвращается при выезде)
Коммунальные платежи оплачиваются отдельно.

Документы в порядке, заключаем официальный договор аренды.
Рядом метро, магазины, парк.

Контакты:
Телефон: +998 90 123-45-67 (можно звонить с 9:00 до 21:00)
Email: landlord@example.com
Telegram: @landlord_tashkent

Показ квартиры в любое удобное время по договоренности.
            """,
            "expected_risk": "10-30",
            "expected_flags": []
        },
        {
            "name": "🟡 СРЕДНИЙ РИСК - Подозрительное предложение заработка",
            "text": """
Привет! Есть отличный способ заработка 💰

Нужно просто принимать деньги на свою карту и переводить дальше.
30% от суммы - твой доход!

Никаких вложений не нужно.
Работа 2-3 часа в день.
Доход от 5,000,000 сум в месяц гарантирован!

Уже 50 человек работают с нами.
Все довольны!

Пиши в Telegram @money_maker_uz для подробностей.
            """,
            "expected_risk": "65-85",
            "expected_flags": ["пересланное", "только мессенджер", "перевод денег", "гарантии заработка", "подозрительная схема"]
        },
        {
            "name": "🟠 ВЫШЕ СРЕДНЕГО - Давление на эмоции",
            "text": """
Мама в больнице, срочно нужны деньги на операцию!
Сумма: 15,000,000 сум

Взамен продаю iPhone 15 Pro Max всего за 3,000,000 сум
(рыночная цена 12,000,000)

Телефон новый, в идеальном состоянии.
Все документы и чеки есть.

Но деньги нужны СРОЧНО - до завтрашнего вечера!
Кто первый переведет предоплату 1,000,000 сум на карту, 
тому и телефон!

Пожалуйста, помогите! 
Карта: 9860 **** **** 1234 (Uzum Bank)
            """,
            "expected_risk": "75-90",
            "expected_flags": ["эмоциональное давление", "низкая цена", "срочность", "предоплата"]
        }
    ]
    
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ УЛУЧШЕННОГО NLP ПРОМПТА v2.0")
    print("="*80)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"ТЕСТ {i}/4: {test_case['name']}")
        print(f"Ожидаемый риск: {test_case['expected_risk']}")
        print(f"Ожидаемые флаги: {', '.join(test_case['expected_flags']) if test_case['expected_flags'] else 'Нет'}")
        print(f"{'='*80}")
        
        # Create listing data
        listing = ListingData(
            url=f"test_case_{i}",
            title=f"Test Case {i}",
            description=test_case["text"],
            price=None,
            location="",
            contact_info={},
            images=[],
            metadata={"test": True}
        )
        
        print("\n⏳ Анализирую...")
        try:
            result = await analyzer.analyze(listing)
            
            print(f"\n✅ РЕЗУЛЬТАТ:")
            print(f"   Риск: {result.risk_score}/100 ({result.risk_level.value})")
            print(f"   Уверенность: {result.details.get('confidence', 0):.2f}")
            print(f"   Тип мошенничества: {result.details.get('scam_type', 'N/A')}")
            
            print(f"\n🚩 КРАСНЫЕ ФЛАГИ ({len(result.red_flags)}):")
            for flag in result.red_flags:
                severity_emoji = "🔴" if flag.severity >= 8 else "🟠" if flag.severity >= 6 else "🟡"
                print(f"   {severity_emoji} [{flag.severity}/10] {flag.category}: {flag.description}")
            
            print(f"\n🎯 МАНИПУЛЯТИВНЫЕ ТАКТИКИ:")
            tactics = result.details.get('manipulation_tactics', [])
            if tactics and tactics != ['none']:
                for tactic in tactics:
                    print(f"   ⚠️  {tactic}")
            else:
                print(f"   ✅ Не обнаружено")
            
            print(f"\n💡 РЕКОМЕНДАЦИИ ({len(result.recommendations)}):")
            for idx, rec in enumerate(result.recommendations, 1):
                print(f"   {idx}. {rec}")
            
            if result.details.get('explanation'):
                print(f"\n📝 ОБЪЯСНЕНИЕ:")
                print(f"   {result.details['explanation']}")
            
            if result.details.get('detailed_analysis'):
                detailed = result.details['detailed_analysis']
                print(f"\n🔬 ДЕТАЛЬНЫЙ АНАЛИЗ:")
                if detailed.get('price_analysis'):
                    print(f"   💵 Цена: {detailed['price_analysis']}")
                if detailed.get('text_quality'):
                    print(f"   📝 Текст: {detailed['text_quality']}")
                if detailed.get('contact_analysis'):
                    print(f"   📞 Контакты: {detailed['contact_analysis']}")
                if detailed.get('psychological_pressure'):
                    print(f"   🧠 Давление: {detailed['psychological_pressure']}")
            
            print(f"\n{'='*80}")
            
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            print(f"{'='*80}")
    
    print("\n" + "="*80)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_prompt_improvements())
