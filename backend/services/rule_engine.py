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
            'гарантированный доход': {'severity': 9, 'category': 'promises', 'type': 'investment'},
            'гарантия прибыли': {'severity': 9, 'category': 'promises', 'type': 'investment'},
            '100% гарантия': {'severity': 8, 'category': 'promises', 'type': 'universal'},
            'пассивный доход': {'severity': 7, 'category': 'promises', 'type': 'investment'},
            'заработок без вложений': {'severity': 8, 'category': 'promises', 'type': 'job'},
            'легкие деньги': {'severity': 8, 'category': 'promises', 'type': 'universal'},
            'быстрый заработок': {'severity': 7, 'category': 'promises', 'type': 'job'},
            'финансовая свобода': {'severity': 6, 'category': 'promises', 'type': 'investment'},
            'удвоим ваши деньги': {'severity': 10, 'category': 'promises', 'type': 'investment'},
            'вложи 1000 получи 10000': {'severity': 10, 'category': 'promises', 'type': 'investment'},
            
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
            
            # 🔒 PHISHING & DATA THEFT
            'введите код из sms': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'отправьте пароль': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'данные карты': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'cvv код': {'severity': 10, 'category': 'phishing', 'type': 'phishing'},
            'ваш аккаунт заблокирован': {'severity': 8, 'category': 'phishing', 'type': 'phishing'},
            'подтвердите личность': {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            'восстановите доступ': {'severity': 7, 'category': 'phishing', 'type': 'phishing'},
            'перейдите по ссылке': {'severity': 6, 'category': 'phishing', 'type': 'phishing'},
            
            # 🎁 FAKE PRIZES & GIVEAWAYS
            'вы выиграли': {'severity': 8, 'category': 'manipulation', 'type': 'fake_prize'},
            'поздравляем': {'severity': 5, 'category': 'manipulation', 'type': 'fake_prize'},
            'бесплатный iphone': {'severity': 9, 'category': 'manipulation', 'type': 'fake_prize'},
            'получите приз': {'severity': 7, 'category': 'manipulation', 'type': 'fake_prize'},
            
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
        has_url = bool(re.search(r'https?://[^\s]+', text))

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

