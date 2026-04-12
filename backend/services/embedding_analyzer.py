"""
Embedding-based analysis for fraud detection
Uses semantic similarity to compare messages with known scam patterns
Works without OpenAI - uses keyword-based semantic matching as fallback
"""
from typing import List, Tuple, Dict, Optional
from backend.models.schemas import RedFlag
from loguru import logger
import re


# Minimal scam pattern database (15 patterns)
SCAM_PATTERNS = [
    {
        'text': 'Срочно! Только сегодня! 100% предоплата без просмотра!',
        'type': 'urgency_prepayment',
        'severity': 9,
        'keywords': ['срочно', 'только сегодня', 'предоплата', 'без просмотра']
    },
    {
        'text': 'Очень дешево, паспорт не нужен, документы не требуются',
        'type': 'no_documents',
        'severity': 10,
        'keywords': ['дешево', 'паспорт не нужен', 'документы не требуются']
    },
    {
        'text': 'Оплатите сразу на карту, встречаться не будем',
        'type': 'card_payment_no_meet',
        'severity': 10,
        'keywords': ['оплатите', 'на карту', 'встречаться не']
    },
    {
        'text': 'Супер предложение только для вас, успейте купить',
        'type': 'fake_exclusive',
        'severity': 7,
        'keywords': ['супер предложение', 'только для вас', 'успейте']
    },
    {
        'text': 'Цена договорная, торг уместен, можно без договора',
        'type': 'no_contract',
        'severity': 8,
        'keywords': ['без договора', 'торг', 'цена договорная']
    },
    {
        'text': 'Гарантированный доход 100000 в месяц без вложений',
        'type': 'investment_scam',
        'severity': 9,
        'keywords': ['гарантирован', 'доход', 'без вложений']
    },
    {
        'text': 'Вы выиграли iPhone! Оплатите только доставку',
        'type': 'fake_prize',
        'severity': 8,
        'keywords': ['выиграли', 'оплатите', 'доставку']
    },
    {
        'text': 'Работа на дому, высокая зарплата, без опыта',
        'type': 'job_scam',
        'severity': 6,
        'keywords': ['работа на дому', 'высокая зарплата', 'без опыта']
    },
    {
        'text': 'Я тебя люблю, но мне нужны деньги на билет',
        'type': 'romance_scam',
        'severity': 9,
        'keywords': ['люблю', 'нужны деньги', 'билет']
    },
    {
        'text': 'Введите код из SMS для подтверждения аккаунта',
        'type': 'phishing',
        'severity': 10,
        'keywords': ['введите код', 'sms', 'подтверждения']
    },
    {
        'text': 'Хозяин за границей, адрес сообщу после оплаты',
        'type': 'absentee_landlord',
        'severity': 9,
        'keywords': ['хозяин за границей', 'после оплаты']
    },
    {
        'text': 'Вложи 1000 получи 10000 за неделю, проверенная схема',
        'type': 'pyramid',
        'severity': 10,
        'keywords': ['вложи', 'получишь', 'проверенная схема']
    },
    {
        'text': 'Скиньте предоплату на карту, иначе отдадим другому',
        'type': 'pressure_payment',
        'severity': 10,
        'keywords': ['скиньте', 'предоплату', 'иначе']
    },
    {
        'text': 'Перейдите по ссылке для верификации аккаунта',
        'type': 'phishing_link',
        'severity': 9,
        'keywords': ['перейдите', 'ссылке', 'верификации']
    },
    {
        'text': 'Секретная методика заработка, не упустите шанс',
        'type': 'secret_method',
        'severity': 7,
        'keywords': ['секретн', 'методик', 'не упустите']
    }
]


class EmbeddingAnalyzer:
    """
    Analyze text similarity with known scam patterns
    
    This module compares input text against a database of known scam patterns
    using semantic similarity (keyword overlap + pattern matching).
    
    In production, this would use real embeddings (OpenAI, sentence-transformers),
    but for MVP we use keyword-based matching which is surprisingly effective.
    """

    def __init__(self):
        self.scam_database = SCAM_PATTERNS
        logger.info(f"EmbeddingAnalyzer initialized with {len(self.scam_database)} patterns")

    async def analyze(self, text: str) -> Tuple[int, List[RedFlag], Dict]:
        """
        Analyze text for similarity with known scam patterns
        
        Returns: (risk_score, red_flags, details)
        """
        if not text or len(text) < 20:
            return 0, [], {'error': 'Text too short for embedding analysis'}

        risk_score = 0
        red_flags = []
        details = {
            'embedding_analysis': True,
            'scam_similarity': 0.0,
            'matched_patterns': [],
            'matches_count': 0
        }

        try:
            # Compare with each scam pattern
            matches = []
            for scam_pattern in self.scam_database:
                similarity = self._calculate_similarity(text, scam_pattern)
                
                if similarity > 0.3:  # Threshold for meaningful match
                    matches.append({
                        'pattern': scam_pattern,
                        'similarity': similarity
                    })
            
            # Sort by similarity
            matches.sort(key=lambda m: m['similarity'], reverse=True)
            
            # Process matches
            max_similarity = 0.0
            for match in matches[:5]:  # Top 5 matches
                pattern = match['pattern']
                similarity = match['similarity']
                
                if similarity > max_similarity:
                    max_similarity = similarity
                
                # High similarity = high risk
                if similarity > 0.6:
                    risk_score += pattern['severity'] * 2
                    red_flags.append(RedFlag(
                        category='pattern',
                        description=f'Совпадение с паттерном мошенничества: {pattern["type"]} ({similarity:.0%})',
                        severity=pattern['severity']
                    ))
                elif similarity > 0.4:
                    risk_score += pattern['severity']
                    red_flags.append(RedFlag(
                        category='pattern',
                        description=f'Частичное совпадение с паттерном: {pattern["type"]}',
                        severity=max(pattern['severity'] - 2, 5)
                    ))
            
            details['scam_similarity'] = max_similarity
            details['matched_patterns'] = [m['pattern']['type'] for m in matches[:3]]
            details['matches_count'] = len(matches)
            
            return min(risk_score, 40), red_flags, details

        except Exception as e:
            logger.error(f"Error in embedding analysis: {e}")
            return 0, [], {'error': str(e)}

    def _calculate_similarity(self, text: str, scam_pattern: Dict) -> float:
        """
        Calculate semantic similarity between text and scam pattern
        
        Uses keyword overlap + text similarity scoring
        Returns: 0.0 (no match) to 1.0 (exact match)
        """
        text_lower = text.lower()
        pattern_keywords = scam_pattern.get('keywords', [])
        pattern_text = scam_pattern.get('text', '').lower()
        
        # Method 1: Keyword overlap score
        keyword_matches = sum(1 for kw in pattern_keywords if kw in text_lower)
        keyword_score = keyword_matches / len(pattern_keywords) if pattern_keywords else 0
        
        # Method 2: Pattern text similarity (word overlap)
        text_words = set(re.findall(r'\w+', text_lower))
        pattern_words = set(re.findall(r'\w+', pattern_text))
        
        if text_words and pattern_words:
            overlap = len(text_words & pattern_words)
            union = len(text_words | pattern_words)
            word_similarity = overlap / union if union > 0 else 0
        else:
            word_similarity = 0
        
        # Method 3: Phrase matching (check if significant chunks match)
        text_chunks = [text_lower[i:i+30] for i in range(0, len(text_lower), 10)]
        pattern_chunks = [pattern_text[i:i+30] for i in range(0, len(pattern_text), 10)]
        
        chunk_matches = sum(
            1 for tc in text_chunks 
            for pc in pattern_chunks 
            if len(set(tc.split()) & set(pc.split())) >= 2
        )
        chunk_score = chunk_matches / max(len(pattern_chunks), 1)
        
        # Weighted combination
        similarity = (
            keyword_score * 0.5 +      # Keywords are most important
            word_similarity * 0.3 +    # Word overlap
            chunk_score * 0.2          # Phrase matching
        )
        
        return min(similarity, 1.0)


# Export for compatibility
__all__ = ['EmbeddingAnalyzer', 'SCAM_PATTERNS']
