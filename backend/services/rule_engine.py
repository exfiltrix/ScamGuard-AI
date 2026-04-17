"""
Rule-based fraud detection engine
"""
from typing import List, Dict, Tuple
from backend.models.schemas import ListingData, RedFlag
from loguru import logger
import re


class RuleEngine:
    """Rule-based fraud detection"""
    
    def __init__(self):
        # Market average prices by city (UZS per month) - for rental scams
        self.market_prices = {
            'ташкент': 3_000_000,
            'самарканд': 1_500_000,
            'бухара': 1_200_000,
            'андижан': 1_000_000,
            'наманган': 1_000_000,
            'фергана': 1_100_000,
        }
        
        # Universal scam keywords with weights (ALL TYPES)
        self.red_flag_keywords = {
            # ⏰ URGENCY & PRESSURE
            'срочно': {'severity': 7, 'category': 'urgency', 'type': 'universal'},
            'только сегодня': {'severity': 8, 'category': 'urgency', 'type': 'universal'},
            'последний шанс': {'severity': 8, 'category': 'urgency', 'type': 'universal'},
            'успейте': {'severity': 6, 'category': 'urgency', 'type': 'universal'},
            'ограниченное предложение': {'severity': 7, 'category': 'urgency', 'type': 'universal'},
            'осталось мест': {'severity': 7, 'category': 'urgency', 'type': 'universal'},
            'много желающих': {'severity': 6, 'category': 'urgency', 'type': 'universal'},
            'быстрее': {'severity': 5, 'category': 'urgency', 'type': 'universal'},
            
            # 📝 DOCUMENTS & VERIFICATION
            'без документов': {'severity': 9, 'category': 'contact', 'type': 'universal'},
            'паспорт не нужен': {'severity': 9, 'category': 'contact', 'type': 'universal'},
            'договор не нужен': {'severity': 9, 'category': 'contact', 'type': 'universal'},
            'документы потом': {'severity': 8, 'category': 'contact', 'type': 'universal'},
            'документы позже': {'severity': 8, 'category': 'contact', 'type': 'universal'},
            
            # 💸 INVESTMENT & MONEY-MAKING SCAMS
            'гарантированный доход': {'severity': 9, 'category': 'investment_scam', 'type': 'investment'},
            'гарантия прибыли': {'severity': 9, 'category': 'investment_scam', 'type': 'investment'},
            '100% гарантия': {'severity': 8, 'category': 'investment_scam', 'type': 'universal'},
            'пассивный доход': {'severity': 7, 'category': 'investment_scam', 'type': 'investment'},
            'заработок без вложений': {'severity': 8, 'category': 'investment_scam', 'type': 'job'},
            'легкие деньги': {'severity': 8, 'category': 'investment_scam', 'type': 'universal'},
            'быстрый заработок': {'severity': 7, 'category': 'investment_scam', 'type': 'job'},
            'финансовая свобода': {'severity': 6, 'category': 'investment_scam', 'type': 'investment'},
            'удвоим ваши деньги': {'severity': 10, 'category': 'investment_scam', 'type': 'investment'},
            'вложи 1000 получи 10000': {'severity': 10, 'category': 'investment_scam', 'type': 'investment'},

            # 🤖 BOT / CRYPTO / PYRAMID SCAM ("заработай через мой бот")
            'есть бот': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'у меня есть бот': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'мой бот': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},
            'торговый бот': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'бот зарабатывает': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'бот приносит': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заработал миллион': {'severity': 10, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заработал 1000000': {'severity': 10, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заработал 100000': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заработал на боте': {'severity': 10, 'category': 'investment_scam', 'type': 'bot_scam'},
            'зарабатываю на боте': {'severity': 10, 'category': 'investment_scam', 'type': 'bot_scam'},
            'хочешь заработать': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'хочешь зарабатывать': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'могу поделиться ботом': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заходи по моей ссылке': {'severity': 10, 'category': 'investment_scam', 'type': 'bot_scam'},
            'заходи по ссылке': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'регистрируйся по ссылке': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'зарегистрируйся по моей': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'моя реферальная': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'реферальная ссылка': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},
            'пассивный заработок': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'автоматический заработок': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'крипто бот': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'криптобот': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'crypto bot': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'форекс бот': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'forex bot': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'трейдинг бот': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'сам зарабатываю': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},
            'я сам зарабатываю': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'я уже заработал': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'вывел деньги': {'severity': 6, 'category': 'investment_scam', 'type': 'bot_scam'},
            'уже вывел': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},

            # 🇺🇿 BOT/INVESTMENT SCAM (Uzbek)
            'bot bor': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'menda bot bor': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'pul ishlash': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},
            'pul ishladim': {'severity': 9, 'category': 'investment_scam', 'type': 'bot_scam'},
            'daromad olish': {'severity': 7, 'category': 'investment_scam', 'type': 'bot_scam'},
            'havolam orqali': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'mening havolam': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},
            'referal havola': {'severity': 8, 'category': 'investment_scam', 'type': 'bot_scam'},

            # 👔 JOB SCAMS
            'работа на дому': {'severity': 5, 'category': 'job', 'type': 'job'},
            'без опыта': {'severity': 4, 'category': 'job', 'type': 'job'},
            'высокая зарплата': {'severity': 5, 'category': 'job', 'type': 'job'},
            
            # ❤️ ROMANCE SCAMS & FAMILY IMPERSONATION
            'я тебя люблю': {'severity': 5, 'category': 'manipulation', 'type': 'romance'},
            'ты особенный': {'severity': 4, 'category': 'manipulation', 'type': 'romance'},
            'нужны деньги на лечение': {'severity': 8, 'category': 'manipulation', 'type': 'romance'},
            'встретимся скоро': {'severity': 4, 'category': 'promises', 'type': 'romance'},
            'экстренная ситуация': {'severity': 7, 'category': 'urgency', 'type': 'universal'},

            # 👨‍👩‍👧 FAMILY/FRIEND IMPERSONATION (срочные просьбы от "близких")
            'срочно нужны деньги': {'severity': 9, 'category': 'urgency', 'type': 'family_scam'},
            'мама попала в беду': {'severity': 9, 'category': 'manipulation', 'type': 'family_scam'},
            'папа в больнице': {'severity': 8, 'category': 'manipulation', 'type': 'family_scam'},
            'брат в trouble': {'severity': 8, 'category': 'urgency', 'type': 'family_scam'},
            'сестре нужна помощь': {'severity': 8, 'category': 'manipulation', 'type': 'family_scam'},
            'ребёнок заболел': {'severity': 9, 'category': 'manipulation', 'type': 'family_scam'},
            'муж/жена в беде': {'severity': 9, 'category': 'manipulation', 'type': 'family_scam'},
            'друг попал в неприятности': {'severity': 7, 'category': 'urgency', 'type': 'family_scam'},
            'пожалуйста помоги': {'severity': 5, 'category': 'manipulation', 'type': 'family_scam'},
            'ты мне доверяешь': {'severity': 7, 'category': 'manipulation', 'type': 'family_scam'},
            'это между нами': {'severity': 6, 'category': 'manipulation', 'type': 'family_scam'},
            'не говори никому': {'severity': 7, 'category': 'manipulation', 'type': 'family_scam'},
            'никто не должен знать': {'severity': 8, 'category': 'manipulation', 'type': 'family_scam'},

            # 🏦 BANK EMPLOYEE IMPERSONATION
            'я менеджер банка': {'severity': 10, 'category': 'phishing', 'type': 'bank_phishing'},
            'менеджер банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'сотрудник банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'специалист банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'работник банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'оператор банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'техподдержка банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'представитель банка': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'банковский сотрудник': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'служба поддержки': {'severity': 7, 'category': 'phishing', 'type': 'bank_phishing'},
            'служба безопасности': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердить платёж': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердить платеж': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердите платёж': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердите платеж': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердить перевод': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'подтвердите перевод': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'верифицировать платёж': {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            'перейдите по ссылке': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'зайдите по ссылке': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'перейти по ссылке': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'нажмите на ссылку': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'кликните по ссылке': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            'пройдите по ссылке': {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},

            # 🇺🇿 BANK IMPERSONATION (Uzbek)
            "bank xodimi": {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            "bank menejeri": {'severity': 10, 'category': 'phishing', 'type': 'bank_phishing'},
            "bank operatori": {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            "to'lovni tasdiqlang": {'severity': 9, 'category': 'phishing', 'type': 'bank_phishing'},
            "havolaga o'ting": {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},
            "havola orqali kiring": {'severity': 8, 'category': 'phishing', 'type': 'bank_phishing'},

            # 💰 LOAN/BORROW SCAM ("займи денег" / "одолжи")
            'одолжи': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'одолжить': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'займи': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'займите': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'дай в долг': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'дайте в долг': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'дай взаймы': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'позаимствуй': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'верну скоро': {'severity': 7, 'category': 'loan_scam', 'type': 'loan_scam'},
            'верну завтра': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'верну через': {'severity': 7, 'category': 'loan_scam', 'type': 'loan_scam'},
            'отдам потом': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'отдам завтра': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'отдам как только': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'верну как только': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'позже верну': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'отдам позже': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'нужна помощь': {'severity': 5, 'category': 'loan_scam', 'type': 'loan_scam'},
            'помоги с деньгами': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'переведи на карту': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'скинь на карту': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'переведи деньги': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'переведи средства': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'кинь на карту': {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            'на эту карту': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            'на мою карту': {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},

            # 🇺🇿 LOAN SCAM (Uzbek)
            "qarz ber": {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            "qarz bering": {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            "pul bor": {'severity': 5, 'category': 'loan_scam', 'type': 'loan_scam'},
            "pul kerak": {'severity': 7, 'category': 'loan_scam', 'type': 'loan_scam'},
            "kartaga o'tkaz": {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            "kartaga yubor": {'severity': 9, 'category': 'loan_scam', 'type': 'loan_scam'},
            "qaytaraman": {'severity': 7, 'category': 'loan_scam', 'type': 'loan_scam'},
            "qaytarib beraman": {'severity': 8, 'category': 'loan_scam', 'type': 'loan_scam'},
            "yordam ber": {'severity': 5, 'category': 'loan_scam', 'type': 'loan_scam'},
            
            # 🔒 PHISHING & DATA THEFT
            'введите код из sms': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'код из sms': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'код из смс': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'введите логин': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'введите пароль': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'логин, пароль': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'логин и пароль': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'отправьте пароль': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'данные карты': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'данные вашей карты': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'cvv код': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'ваш аккаунт заблокирован': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'счёт будет заблокирован': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'счет будет заблокирован': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'аккаунт будет заблокирован': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'средства будут заморожены': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'деньги будут заморожены': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'счёт заморожен': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'подтвердите личность': {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            'подтвердите свои данные': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'подтвердите данные': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'восстановите доступ': {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            'перейдите по ссылке': {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            'подозрительная операция': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'подозрительная транзакция': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'служба безопасности банка': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'служба безопасности': {'severity': 8, 'category': 'phishing', 'type': 'phishing'},
            'безопасность банка': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            'банк заблокировал': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'служба поддержки банка': {'severity': 8, 'category': 'phishing', 'type': 'phishing'},
            'верификация аккаунта': {'severity': 8, 'category': 'phishing', 'type': 'phishing'},
            'верифицируйте аккаунт': {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            
            # 🎁 FAKE PRIZES & GIVEAWAYS
            'вы выиграли': {'severity': 9, 'category': 'fake_prize', 'type': 'fake_prize'},
            'вы стали победителем': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'стали победителем': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'вы победитель': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'поздравляем вас': {'severity': 7, 'category': 'fake_prize', 'type': 'fake_prize'},
            'поздравляем!': {'severity': 6, 'category': 'fake_prize', 'type': 'fake_prize'},
            'бесплатный iphone': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'получите приз': {'severity': 8, 'category': 'fake_prize', 'type': 'fake_prize'},
            'получить приз': {'severity': 8, 'category': 'fake_prize', 'type': 'fake_prize'},
            'оплатите доставку': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'оплатить доставку': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'оплата доставки': {'severity': 9, 'category': 'fake_prize', 'type': 'fake_prize'},
            'акция от': {'severity': 7, 'category': 'fake_prize', 'type': 'fake_prize'},
            'известного бренда': {'severity': 8, 'category': 'fake_prize', 'type': 'fake_prize'},
            'победитель акции': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'выиграли iphone': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'выиграли деньги': {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            'забрать приз': {'severity': 9, 'category': 'fake_prize', 'type': 'fake_prize'},
            'осталось 3 часа': {'severity': 9, 'category': 'urgency', 'type': 'fake_prize'},
            'осталось 2 часа': {'severity': 9, 'category': 'urgency', 'type': 'fake_prize'},
            'осталось 1 час': {'severity': 9, 'category': 'urgency', 'type': 'fake_prize'},
            'осталось несколько часов': {'severity': 8, 'category': 'urgency', 'type': 'fake_prize'},
            'ограниченное время': {'severity': 8, 'category': 'urgency', 'type': 'fake_prize'},
            
            # ⏱️ TIMER / DEADLINE PRESSURE
            'в течение 10 минут': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'в течение 15 минут': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'в течение 30 минут': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'в течение часа': {'severity': 8, 'category': 'urgency', 'type': 'phishing'},
            'через 10 минут': {'severity': 8, 'category': 'urgency', 'type': 'phishing'},
            'через 15 минут': {'severity': 8, 'category': 'urgency', 'type': 'phishing'},
            'иначе счёт': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'иначе аккаунт': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'если не подтвердите': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'если не ответите': {'severity': 8, 'category': 'urgency', 'type': 'phishing'},

            # 🇺🇿 UZBEK LANGUAGE PATTERNS
            # Urgency / threats
            'shoshilinch': {'severity': 7, 'category': 'urgency', 'type': 'universal'},
            'tezda': {'severity': 6, 'category': 'urgency', 'type': 'universal'},
            'darhol': {'severity': 7, 'category': 'urgency', 'type': 'universal'},
            'zudlik bilan': {'severity': 8, 'category': 'urgency', 'type': 'universal'},
            'soat ichida': {'severity': 8, 'category': 'urgency', 'type': 'universal'},
            '13 soat': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            '24 soat': {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            'aks holda': {'severity': 8, 'category': 'urgency', 'type': 'universal'},
            "agar buni qilmasangiz": {'severity': 9, 'category': 'urgency', 'type': 'phishing'},
            "to'xtatib qo'yiladi": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "blokirovka qilinadi": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "hisobingiz cheklandi": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "hisobingiz bloklandi": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "hisobingiz to'xtatildi": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "shubhali qoidabuzarlik": {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            "shubhali faoliyat": {'severity': 9, 'category': 'phishing', 'type': 'phishing'},
            # Identity verification requests
            "shaxsni tasdiqlang": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "shaxsingizni tasdiqlang": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "tasdiqlashni yakunlang": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "ma'lumotlaringizni kiriting": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "login va parolingizni": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "sms kodni kiriting": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            # Fake prize / job
            "g'olib bo'ldingiz": {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            "sovg'a olish uchun": {'severity': 9, 'category': 'fake_prize', 'type': 'fake_prize'},
            "yetkazib berishni to'lang": {'severity': 10, 'category': 'fake_prize', 'type': 'fake_prize'},
            "ishga taklif": {'severity': 6, 'category': 'job', 'type': 'job'},
            "kafolatlangan daromad": {'severity': 9, 'category': 'promises', 'type': 'investment'},
            # Authority impersonation
            "bank xavfsizlik xizmati": {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            "xavfsizlik xizmati": {'severity': 8, 'category': 'phishing', 'type': 'phishing'},
            "quyidagi havola orqali": {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            "havola orqali o'ting": {'severity': 8, 'category': 'phishing', 'type': 'phishing'},

            # 🚨 GENERAL MANIPULATION
            'секрет': {'severity': 5, 'category': 'manipulation', 'type': 'universal'},
            'эксклюзив': {'severity': 5, 'category': 'manipulation', 'type': 'universal'},
            'только для вас': {'severity': 5, 'category': 'manipulation', 'type': 'universal'},
            'не упустите': {'severity': 6, 'category': 'urgency', 'type': 'universal'},
            'уникальная возможность': {'severity': 6, 'category': 'manipulation', 'type': 'universal'},
            'проверенная схема': {'severity': 7, 'category': 'manipulation', 'type': 'investment'},
        }
    
    def analyze(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """
        Run rule-based analysis
        Returns: (risk_score, red_flags)
        
        Enhanced to work with both listings and direct messages
        """
        risk_score = 0
        red_flags = []

        # Rule 1: Check price (if applicable)
        price_risk, price_flags = self._check_price(listing)
        risk_score += price_risk
        red_flags.extend(price_flags)

        # Rule 2: Check keywords (PRIMARY for messages)
        keyword_risk, keyword_flags = self._check_keywords(listing)
        risk_score += keyword_risk
        red_flags.extend(keyword_flags)

        # Rule 3: Check links & attachments (URL in text or files present)
        link_risk, link_flags = self._check_links_and_attachments(listing)
        risk_score += link_risk
        red_flags.extend(link_flags)

        # Rule 4: Check contact information
        contact_risk, contact_flags = self._check_contacts(listing)
        risk_score += contact_risk
        red_flags.extend(contact_flags)

        # Rule 5: Check description/message quality
        desc_risk, desc_flags = self._check_description(listing)
        risk_score += desc_risk
        red_flags.extend(desc_flags)

        # Rule 6: Check for new account indicators (if forwarded message)
        if listing.metadata and listing.metadata.get("is_forwarded"):
            account_risk, account_flags = self._check_account_indicators(listing)
            risk_score += account_risk
            red_flags.extend(account_flags)

        # Rule 7: Check payment request patterns
        payment_risk, payment_flags = self._check_payment_patterns(listing)
        risk_score += payment_risk
        red_flags.extend(payment_flags)

        # Rule 8: Combo — bank phishing signature
        combo_risk, combo_flags = self._check_phishing_combos(listing)
        risk_score += combo_risk
        red_flags.extend(combo_flags)

        return min(risk_score, 100), red_flags
    
    def _check_price(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """Check if price is suspiciously low"""
        risk = 0
        flags = []
        
        if not listing.price or not listing.location:
            return risk, flags
        
        # Get market price for location
        location_lower = listing.location.lower()
        market_price = None
        
        for city, price in self.market_prices.items():
            if city in location_lower:
                market_price = price
                break
        
        if not market_price:
            market_price = 2_000_000  # Default
        
        # Convert to same currency if needed (assume UZS)
        listing_price = listing.price
        if listing.currency and listing.currency.upper() in ['USD', '$']:
            listing_price = listing.price * 12_500  # Approximate rate
        
        # Check if price is too low
        price_ratio = listing_price / market_price
        
        if price_ratio < 0.5:  # More than 50% below market
            risk = 30
            flags.append(RedFlag(
                category='price',
                description=f'Цена на {int((1 - price_ratio) * 100)}% ниже рыночной',
                severity=9
            ))
        elif price_ratio < 0.7:  # 30-50% below market
            risk = 20
            flags.append(RedFlag(
                category='price',
                description=f'Цена на {int((1 - price_ratio) * 100)}% ниже рыночной',
                severity=7
            ))
        elif price_ratio < 0.8:  # 20-30% below market
            risk = 10
            flags.append(RedFlag(
                category='price',
                description='Цена немного ниже рыночной',
                severity=5
            ))
        
        return risk, flags
    
    def _check_keywords(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """Check for suspicious keywords"""
        risk = 0
        flags = []

        if not listing.description:
            return risk, flags

        text_lower = listing.description.lower()

        # Track critical keywords for combo bonuses
        critical_found = []

        for keyword, props in self.red_flag_keywords.items():
            if keyword in text_lower:
                # Increased risk for critical keywords
                base_risk = props['severity'] + 8  # Was +5, now +8
                
                # Critical keywords get extra risk
                if props['severity'] >= 9:
                    base_risk += 5
                    critical_found.append(keyword)

                risk += base_risk
                flags.append(RedFlag(
                    category=props['category'],
                    description=f'Обнаружено: "{keyword}"',
                    severity=props['severity']
                ))

        # Bonus risk for multiple critical keywords
        if len(critical_found) >= 3:
            risk += 15
            flags.append(RedFlag(
                category='pattern',
                description=f'Множество критических признаков ({len(critical_found)}): классическая схема мошенников',
                severity=10
            ))
        elif len(critical_found) >= 2:
            risk += 10
            flags.append(RedFlag(
                category='pattern',
                description='Несколько критических признаков мошенничества',
                severity=9
            ))

        return min(risk, 60), flags  # Cap keyword risk at 60 (was 50)
    
    def _check_contacts(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """Check contact information completeness"""
        risk = 0
        flags = []

        # Also look for phone/email patterns in description text
        text = listing.description or ""
        phone_in_text = bool(re.search(r'\+?[\d\s\-\(\)]{7,}', text))
        email_in_text = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
        has_contact_in_text = phone_in_text or email_in_text

        if not listing.contact_info and not has_contact_in_text:
            risk = 25
            flags.append(RedFlag(
                category='contact',
                description='Отсутствует контактная информация',
                severity=8
            ))
            return risk, flags

        if listing.contact_info:
            # Check for phone number
            if 'phones' not in listing.contact_info:
                risk += 15
                flags.append(RedFlag(
                    category='contact',
                    description='Нет номера телефона',
                    severity=7
                ))

            # Only messenger contacts is suspicious
            if 'telegram' in listing.contact_info and 'phones' not in listing.contact_info:
                risk += 10
                flags.append(RedFlag(
                    category='contact',
                    description='Только Telegram, нет телефона',
                    severity=6
                ))

        return risk, flags

    def _check_links_and_attachments(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """
        Check for links and file attachments in the message

        Risk logic:
        - URL found in text → +15 risk (phishing / external redirect)
        - File attached → +20 risk (malware / trojan)
        - Both URL + file → +30 risk (combined threat)
        - Nothing found → skip (0 risk, move to next stage)
        """
        risk = 0
        flags = []

        text = listing.description or listing.title or ""
        # Match both http(s):// URLs and bare domains like "ssilka.com", "t.me/xxx"
        has_url = bool(re.search(r'https?://[^\s]+', text)) or bool(
            re.search(r'\b(?:[a-zA-Z0-9\-]+\.)+(?:com|ru|uz|net|org|io|me|co|shop|site|online|info|biz|top|xyz|live|click|link|pw|tk|ml|ga|cf)\b', text)
        )

        # Check if files are attached (from metadata)
        metadata = listing.metadata or {}
        has_file = metadata.get("has_file", False)
        file_count = metadata.get("file_count", 0)

        if has_url and has_file:
            # Both link and file — highest risk
            risk = 30
            flags.append(RedFlag(
                category='attachment',
                description='Обнаружена ссылка И файл в сообщении (высокий риск)',
                severity=9
            ))
        elif has_url:
            # URL found
            risk = 15
            flags.append(RedFlag(
                category='attachment',
                description='Обнаружена внешняя ссылка (возможен фишинг)',
                severity=7
            ))
        elif has_file:
            # File attached
            file_desc = f'Прикреплен файл ({file_count} шт.)' if file_count > 1 else 'Прикреплен файл'
            risk = 20
            flags.append(RedFlag(
                category='attachment',
                description=file_desc,
                severity=8
            ))
        # else: nothing found → 0 risk, skip to next stage

        return risk, flags

    def _check_description(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """Check description quality"""
        risk = 0
        flags = []

        if not listing.description:
            risk = 20
            flags.append(RedFlag(
                category='text',
                description='Отсутствует описание',
                severity=8
            ))
            return risk, flags

        desc_len = len(listing.description)

        if desc_len < 50:
            risk = 15
            flags.append(RedFlag(
                category='text',
                description='Слишком короткое описание',
                severity=7
            ))
        elif desc_len < 100:
            risk = 8
            flags.append(RedFlag(
                category='text',
                description='Краткое описание',
                severity=5
            ))

        # Check for minimal information — ONLY if this is a housing listing
        # Detect housing context by looking for rental-specific terms
        text_lower = listing.description.lower()
        housing_keywords = ['комнат', 'метр', 'этаж', 'квартир', 'аренд', 'снимать', 'сдач', 'дом', 'район']
        is_housing = any(kw in text_lower for kw in housing_keywords)

        if is_housing:
            detail_keywords = ['ремонт', 'мебель', 'кондиционер', 'парковка', 'балкон', 'интернет', 'оплата', 'залог', 'договор']
            found_details = sum(1 for kw in detail_keywords if kw in text_lower)

            if found_details < 2:
                risk += 10
                flags.append(RedFlag(
                    category='text',
                    description='Мало деталей об объекте (нет описания условий)',
                    severity=6
                ))
        # If not housing — skip this check (laptop, phone, etc. don't need "этаж")
        
        return risk, flags
    
    def _check_account_indicators(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """
        Check for indicators that suggest a new/suspicious account
        
        This rule applies primarily to forwarded messages where we can
        analyze the sender's account characteristics
        """
        risk = 0
        flags = []
        
        metadata = listing.metadata or {}
        forward_info = metadata.get("forward_info", {})
        
        # Check if sender has no username (common with new/scam accounts)
        if forward_info and not forward_info.get("from_user"):
            # No visible username - could be deleted or new account
            risk += 10
            flags.append(RedFlag(
                category='account',
                description='Отправитель без видимого username (подозрительно)',
                severity=6
            ))
        
        # Check for generic sender indicators
        if forward_info and forward_info.get("sender_name"):
            # Message was forwarded from a person (not a channel)
            # This is normal, but worth noting
            pass
        
        # Check message patterns that suggest automated/scam accounts
        text = (listing.description or "").lower()
        
        # Very formal/templated language
        formal_patterns = [
            "уважаемый клиент", "уважаемый пользователь", "ваш аккаунт",
            "служба поддержки", "администрация", "официальное сообщение"
        ]
        formal_count = sum(1 for pattern in formal_patterns if pattern in text)
        if formal_count >= 2:
            risk += 15
            flags.append(RedFlag(
                category='account',
                description='Формальный/шаблонный язык (возможен бот или массовая рассылка)',
                severity=7
            ))
        
        return risk, flags

    def _check_payment_patterns(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """
        Check for payment request patterns - CRITICAL for fraud detection
        
        This specifically looks for:
        - Requests for prepayment/advance payment
        - Card-to-card transfers
        - Payment without meeting/viewing
        - Unusual payment methods
        """
        risk = 0
        flags = []
        
        text = (listing.description or listing.title or "").lower()
        
        # Prepayment requests
        prepayment_keywords = [
            "предоплата", "предварительная оплата", "аванс",
            "оплатите заранее", "оплатить до", "переведите заранее",
            "скиньте на карту", "перевод на карту", "карта для перевода"
        ]
        
        for keyword in prepayment_keywords:
            if keyword in text:
                risk += 25
                flags.append(RedFlag(
                    category='payment',
                    description=f'Запрос предоплаты: "{keyword}"',
                    severity=9
                ))
                break  # Only flag once
        
        # Payment without meeting/viewing
        no_meet_keywords = [
            "без просмотра", "без встречи", "дистанционно",
            "не нужно встречаться", "адрес после оплаты", "хозяин за границей"
        ]
        
        no_meet_count = sum(1 for kw in no_meet_keywords if kw in text)
        if no_meet_count >= 2:
            risk += 20
            flags.append(RedFlag(
                category='payment',
                description='Оплата без личной встречи/просмотра',
                severity=9
            ))
        elif no_meet_count == 1:
            risk += 10
            flags.append(RedFlag(
                category='payment',
                description='Упоминание оплаты без встречи',
                severity=7
            ))
        
        # Urgency + payment combination
        urgency_keywords = ["срочно", "быстро", "немедленно", "прямо сейчас", "только сегодня"]
        has_urgency = any(kw in text for kw in urgency_keywords)
        has_payment = any(kw in text for kw in prepayment_keywords)
        
        if has_urgency and has_payment:
            risk += 15
            flags.append(RedFlag(
                category='payment',
                description='Сочетание срочности и запроса оплаты (классическая схема)',
                severity=10
            ))
        
        # Specific payment method red flags
        payment_methods = {
            "только наличные": "Оплата только наличными (подозрительно)",
            "криптовалюта": "Запрос оплаты криптовалютой (невозможно откатить)",
            "usdt": "Запрос USDT/крипты (высокий риск)",
            "bitcoin": "Запрос Bitcoin (высокий риск)"
        }
        
        for method, description in payment_methods.items():
            if method in text:
                risk += 15
                flags.append(RedFlag(
                    category='payment',
                    description=description,
                    severity=8
                ))

        return min(risk, 50), flags  # Cap at 50

    def _check_phishing_combos(self, listing: ListingData) -> Tuple[int, List[RedFlag]]:
        """
        Detect high-confidence phishing by checking dangerous keyword combinations.

        Single keywords may have low signal — but their combination is a near-certain
        indicator of a specific scam type.
        """
        risk = 0
        flags = []
        text = (listing.description or listing.title or "").lower()

        # Detect any URL — with or without scheme
        has_url = bool(re.search(r'https?://[^\s]+', text)) or bool(
            re.search(r'\b(?:[a-zA-Z0-9\-]+\.)+(?:com|ru|uz|net|org|io|me|co|shop|site|online|info|biz|top|xyz|live|click|link|pw|tk|ml|ga|cf)\b', text)
        )

        # Bank phishing: authority claim + threat + action
        bank_authority = any(kw in text for kw in [
            'служба безопасности', 'безопасности банка', 'служба поддержки банка',
            'банк', 'финансовая организация',
        ])
        account_threat = any(kw in text for kw in [
            'заблокирован', 'заморожен', 'приостановлен', 'подозрительная операция',
            'подозрительная транзакция', 'несанкционированный',
        ])
        data_request = any(kw in text for kw in [
            'подтвердите', 'введите', 'логин', 'пароль', 'код из sms', 'код из смс',
            'верификация', 'верифицируйте',
        ])

        if bank_authority and account_threat and data_request:
            risk += 40
            flags.append(RedFlag(
                category='phishing',
                description='🏦 Классический банковский фишинг: "служба безопасности" + угроза блокировки + запрос данных',
                severity=10,
            ))

        # Phishing link combo: threat/urgency + URL + data request
        if has_url and account_threat and data_request:
            risk += 30
            flags.append(RedFlag(
                category='phishing',
                description='🔗 Фишинговая ссылка: угроза + ссылка + запрос учётных данных',
                severity=10,
            ))

        # Credentials harvest: asking for login + password + SMS code together
        wants_login = any(kw in text for kw in ['логин', 'введите логин', 'login'])
        wants_password = any(kw in text for kw in ['пароль', 'введите пароль', 'password'])
        wants_sms = any(kw in text for kw in ['код из sms', 'код из смс', 'sms код', 'смс код'])

        credential_count = sum([wants_login, wants_password, wants_sms])
        if credential_count >= 2:
            risk += 35
            flags.append(RedFlag(
                category='phishing',
                description='🔑 Запрос сразу нескольких учётных данных (логин/пароль/SMS) — кража аккаунта',
                severity=10,
            ))

        # Fake prize combo: "победитель/выиграли" + "ссылка" + "оплата доставки"
        is_prize = any(kw in text for kw in [
            'победитель', 'выиграли', 'вы выиграли', 'получите приз', 'вы стали победителем',
        ])
        wants_delivery_pay = any(kw in text for kw in [
            'оплатите доставку', 'оплатить доставку', 'оплата доставки',
        ])

        if is_prize and has_url:
            risk += 35
            flags.append(RedFlag(
                category='fake_prize',
                description='🎁 Классический фейковый конкурс: "вы победитель" + ссылка — никакого приза нет, цель — ваши деньги или данные',
                severity=10,
            ))

        if is_prize and wants_delivery_pay:
            risk += 40
            flags.append(RedFlag(
                category='fake_prize',
                description='💸 Фейковый приз с оплатой доставки — классическая схема: приз не существует, деньги за доставку заберут и исчезнут',
                severity=10,
            ))

        # Uzbek phishing combo: account threat + link + verification request
        uz_account_threat = any(kw in text for kw in [
            "to'xtatib qo'yiladi", "blokirovka qilinadi", "hisobingiz cheklandi",
            "hisobingiz bloklandi", "hisobingiz to'xtatildi", "shubhali qoidabuzarlik",
        ])
        uz_verify_request = any(kw in text for kw in [
            "shaxsni tasdiqlang", "shaxsingizni tasdiqlang", "tasdiqlashni yakunlang",
            "ma'lumotlaringizni kiriting", "quyidagi havola orqali",
        ])

        if uz_account_threat and has_url:
            risk += 35
            flags.append(RedFlag(
                category='phishing',
                description='🇺🇿 Узбекский фишинг: угроза блокировки аккаунта + ссылка — классическая схема кражи данных',
                severity=10,
            ))

        if uz_account_threat and uz_verify_request:
            risk += 40
            flags.append(RedFlag(
                category='phishing',
                description='🇺🇿 Банковский фишинг на узбекском: угроза блокировки + запрос подтверждения личности',
                severity=10,
            ))

        # ── BANK EMPLOYEE IMPERSONATION + LINK ──────────────────────────────
        bank_employee = any(kw in text for kw in [
            'менеджер банка', 'сотрудник банка', 'специалист банка', 'работник банка',
            'оператор банка', 'техподдержка банка', 'представитель банка',
            'банковский сотрудник', 'служба поддержки', 'служба безопасности',
            'bank xodimi', 'bank menejeri', 'bank operatori',
        ])
        payment_confirm = any(kw in text for kw in [
            'подтвердить платёж', 'подтвердить платеж', 'подтвердите платёж', 'подтвердите платеж',
            'подтвердить перевод', 'подтвердите перевод', 'верифицировать',
            "to'lovni tasdiqlang",
        ])
        link_action = any(kw in text for kw in [
            'перейдите по ссылке', 'зайдите по ссылке', 'перейти по ссылке',
            'нажмите на ссылку', 'кликните', 'пройдите по ссылке', 'зайти по ссылке',
            'зайдите', 'зайти', 'перейдите', 'перейти',
            "havolaga o'ting", "havola orqali",
        ])

        if bank_employee and has_url:
            risk += 45
            flags.append(RedFlag(
                category='phishing',
                description='🏦 Самозванец: "менеджер/сотрудник банка" + ссылка — банки никогда не пишут в мессенджерах с такими просьбами',
                severity=10,
            ))

        if bank_employee and payment_confirm:
            risk += 45
            flags.append(RedFlag(
                category='phishing',
                description='🏦 Классический банковский фишинг: представляется сотрудником банка и просит "подтвердить платёж"',
                severity=10,
            ))

        if bank_employee and (has_url or payment_confirm or link_action):
            risk += 20  # Extra push if any combination
            flags.append(RedFlag(
                category='phishing',
                description='⚠️ Комбинация: сотрудник банка + действие по ссылке — 100% мошенничество',
                severity=10,
            ))

        if link_action and has_url and not bank_employee:
            # Generic "click this link" phishing without bank claim
            risk += 25
            flags.append(RedFlag(
                category='phishing',
                description='🔗 Призыв перейти по ссылке — типичный приём фишинга',
                severity=8,
            ))

        # ── BOT / INVESTMENT / PYRAMID SCAM ──────────────────────────────────
        has_bot_claim = any(kw in text for kw in [
            'есть бот', 'у меня есть бот', 'мой бот', 'торговый бот',
            'бот зарабатывает', 'бот приносит', 'заработал на боте',
            'crypto bot', 'криптобот', 'крипто бот', 'форекс бот', 'forex bot',
            'bot bor', 'menda bot bor',
        ])
        has_earnings_claim = any(kw in text for kw in [
            'заработал', 'зарабатываю', 'я уже заработал', 'уже вывел',
            'вывел деньги', 'пассивный доход', 'автоматический заработок',
            'pul ishladim', 'pul ishlash',
        ])
        # Large sum of money claimed (1 million, 100k, $, etc.)
        has_big_money = bool(re.search(
            r'(?:[\$\€\£]|долларов|баксов|сум|рублей)?\s*\d[\d\s]*(?:000\s*000|\s*млн|million|миллион)',
            text
        )) or bool(re.search(r'[\$\€\£]\s*\d{5,}|\d{6,}\s*(?:сум|руб|долларов|баксов)', text))

        has_referral_invite = any(kw in text for kw in [
            'заходи по моей ссылке', 'заходи по ссылке', 'регистрируйся по ссылке',
            'зарегистрируйся по моей', 'моя реферальная', 'реферальная ссылка',
            'хочешь заработать', 'хочешь зарабатывать',
            'havolam orqali', 'mening havolam', 'referal havola',
        ])

        if has_bot_claim and has_referral_invite:
            risk += 50
            flags.append(RedFlag(
                category='investment_scam',
                description='🤖 Схема "зарабатывай через мой бот": реферальная ссылка + утверждение о боте — классическая пирамида',
                severity=10,
            ))
        elif has_bot_claim and (has_earnings_claim or has_big_money):
            risk += 45
            flags.append(RedFlag(
                category='investment_scam',
                description='🤖 Бот + заявление о большом заработке — инвестиционная афера',
                severity=10,
            ))
        elif has_earnings_claim and has_referral_invite and has_url:
            risk += 45
            flags.append(RedFlag(
                category='investment_scam',
                description='💰 "Я заработал" + реферальная ссылка — классическая пирамидальная схема',
                severity=10,
            ))

        if has_big_money and has_url:
            risk += 25
            flags.append(RedFlag(
                category='investment_scam',
                description='💸 Упоминание огромных сумм заработка + ссылка — признак финансовой пирамиды',
                severity=9,
            ))

        if has_referral_invite and has_url:
            risk += 20
            flags.append(RedFlag(
                category='investment_scam',
                description='🔗 Приглашение по реферальной ссылке — заработок организатора идёт за счёт новых участников',
                severity=8,
            ))

        # ── LOAN / BORROW SCAM ("займи денег") ──────────────────────────────
        borrow_request = any(kw in text for kw in [
            'одолжи', 'одолжить', 'займи', 'займите', 'дай в долг', 'дайте в долг',
            'дай взаймы', 'позаимствуй', 'помоги с деньгами',
            'qarz ber', 'qarz bering',
        ])
        repay_promise = any(kw in text for kw in [
            'верну', 'отдам', 'верну скоро', 'верну завтра', 'позже верну',
            'отдам потом', 'отдам завтра', 'верну как только', 'отдам как только',
            'qaytaraman', 'qaytarib beraman',
        ])
        transfer_request = any(kw in text for kw in [
            'переведи на карту', 'скинь на карту', 'кинь на карту', 'на эту карту',
            'на мою карту', 'переведи деньги', 'переведи средства',
            'kartaga', 'перевод',
        ])
        # Card number in text (e.g. "8600 **** **** 1234" or "8600123412341234")
        has_card_number = bool(re.search(
            r'\b(?:\d[ -]?){13,19}\b|\b\d{4}[\s\-\*]+\d{2,4}[\s\-\*]+\d{2,4}[\s\-\*]+\d{2,4}\b',
            text
        ))

        if borrow_request and (repay_promise or transfer_request or has_card_number):
            risk += 45
            flags.append(RedFlag(
                category='loan_scam',
                description='💸 Классическая схема "займи денег": просьба одолжить + обещание вернуть + реквизиты карты',
                severity=10,
            ))
        elif borrow_request and transfer_request:
            risk += 40
            flags.append(RedFlag(
                category='loan_scam',
                description='💸 Просьба занять деньги с переводом на карту — типичный social engineering',
                severity=10,
            ))
        elif borrow_request:
            risk += 25
            flags.append(RedFlag(
                category='loan_scam',
                description='💸 Обнаружена просьба одолжить/занять деньги — будьте осторожны',
                severity=8,
            ))

        if has_card_number and transfer_request:
            risk += 30
            flags.append(RedFlag(
                category='loan_scam',
                description='💳 Запрос перевода с указанием номера карты — проверьте личность отправителя',
                severity=9,
            ))
        elif has_card_number:
            risk += 15
            flags.append(RedFlag(
                category='payment',
                description='💳 В сообщении содержится номер карты — убедитесь, что это легитимный получатель',
                severity=7,
            ))

        # Urgency + borrow = high pressure manipulation
        has_urgency = any(kw in text for kw in [
            'срочно', 'быстро', 'немедленно', 'прямо сейчас', 'очень нужно',
            'жду', 'не могу ждать', 'помоги срочно',
        ])
        if has_urgency and borrow_request:
            risk += 20
            flags.append(RedFlag(
                category='loan_scam',
                description='⏰ Срочность + просьба занять деньги — давление для отключения критического мышления',
                severity=9,
            ))

        return min(risk, 100), flags

