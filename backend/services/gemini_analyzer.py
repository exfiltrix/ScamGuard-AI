"""
NLP/LLM Analysis Module using Google Gemini
Specialized for message context understanding, manipulation detection, and pattern extraction
"""
import json
import re
import asyncio
import warnings
from typing import Dict, List, Optional
from backend.models.schemas import ListingData, AnalysisResult, RedFlag, RiskLevel
from backend.config import get_settings

# Suppress deprecation warning
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from loguru import logger


class GeminiAnalyzer:
    """
    NLP/LLM Analyzer using Google Gemini
    
    This module is the PRIMARY AI component of the pipeline.
    It performs:
    - Context understanding of messages
    - Manipulation and pressure detection
    - Price/condition extraction
    - Scam pattern identification
    """

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.google_api_key
        
        if not self.api_key:
            raise ValueError("Google API key not configured")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-flash-lite-latest')
        logger.info("Gemini NLP Analyzer initialized")

    async def analyze(self, listing: ListingData) -> AnalysisResult:
        """
        Analyze listing/message using Gemini LLM
        
        Returns AnalysisResult with:
        - Risk score (0-100)
        - Red flags with categories and severity
        - Extracted information (price, conditions, pressure)
        - Recommendations
        """
        logger.debug("Starting Gemini NLP analysis")
        
        # Prepare text for analysis
        text = listing.description or listing.title or ""
        
        # Add metadata if available
        metadata_parts = []
        if listing.price and listing.price > 0:
            metadata_parts.append(f"Цена: {listing.price}")
        if listing.location:
            metadata_parts.append(f"Локация: {listing.location}")
        if listing.contact_info:
            contact_str = ", ".join(listing.contact_info.values())
            metadata_parts.append(f"Контакты: {contact_str}")
        
        if metadata_parts:
            text = f"Метаданные:\n" + "\n".join(metadata_parts) + f"\n\nСообщение:\n{text}"
        
        # Check if forwarded message
        is_forwarded = listing.metadata.get("is_forwarded", False) if listing.metadata else False
        if is_forwarded:
            text = f"[Пересланное сообщение]\n\n{text}"
        
        try:
            # Run Gemini analysis
            prompt = self._build_nlp_prompt(text)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
            
            # Parse response
            result_text = response.text
            logger.debug(f"Gemini response: {result_text[:500]}")
            
            # Extract JSON from response
            json_data = self._extract_json(result_text)
            
            if json_data:
                return self._parse_gemini_response(json_data)
            else:
                logger.warning("Failed to parse Gemini JSON response")
                return self._fallback_analysis(listing)
                
        except Exception as e:
            logger.error(f"Gemini NLP analysis error: {e}")
            return self._fallback_analysis(listing)

    def _build_nlp_prompt(self, text: str) -> str:
        """
        Build specialized NLP prompt for scam detection

        This prompt is designed using advanced prompt engineering techniques:
        - Role-playing with specific expertise context
        - Structured analytical framework (step-by-step reasoning)
        - Clear examples of scam patterns
        - Separation of extraction, analysis, and recommendation phases
        - Constrained output format for reliable parsing
        """
        return f"""
<role>
Ты — ведущий эксперт по борьбе с мошенничеством с 15-летним опытом в:
- Лингвистическом анализе мошеннических сообщений
- Выявлении психологических манипуляций и социальной инженерии
- Анализе поведенческих паттернов мошенников
- Криминалистике текста (стилометрия, маркеры обмана)

Твоя задача — провести ГЛУБОКИЙ АНАЛИЗ предоставленного текста и выявить ВСЕ признаки мошенничества, используя систематический подход.
</role>

<analytical_framework>
АНАЛИЗИРУЙ ТЕКСТ ПО СЛЕДУЮЩЕЙ СТРУКТУРЕ (шаг за шагом):

ШАГ 1: ИЗВЛЕЧЕНИЕ ФАКТОВ
Выяви и извлеки из текста:
- Финансовые условия (цена, предоплата, депозит, способ оплаты)
- Временные ограничения (дедлайны, срочность, "только сегодня")
- Контактная информация (полнота, тип контактов)
- Условия сделки (договор, документы, встреча)
- Информация о товаре/услуге (детали, фото, описание)
- Каналы коммуникации (только мессенджеры, блокировка звонков)

ШАГ 2: ВЫЯВЛЕНИЕ МАРКЕРОВ МОШЕННИЧЕСТВА
Проверь текст на наличие следующих паттернов:

🔴 КРИТИЧЕСКИЕ МАРКЕРЫ (вес 9-10):
- Требование предоплаты/аванса до оказания услуги
- Перевод денег "на карту" без договора
- Отсутствие возможности личной встречи/просмотра
- Блокировка обратной связи (только текст, нет звонков)
- Угрозы, шантаж, давление
- Фейковые документы/поддельные профили

🟠 СЕРЬЕЗНЫЕ МАРКЕРЫ (вес 6-8):
- Аномально низкая цена (ниже рынка на 30%+)
- Срочность и давление времени ("только сейчас", "через час уеду")
- Только мессенджеры для связи (нет телефона/email)
- Отсутствие конкретики в описании (размытые формулировки)
- Грамматические ошибки в официальном контексте
- Слишком короткие/поверхностные описания
- Пересланное сообщение из неизвестного источника

🟡 ПРЕДУПРЕЖДАЮЩИЕ МАРКЕРЫ (вес 3-5):
- Неполная контактная информация
- Общие фразы без деталей ("хорошее состояние", "все включено")
- Отсутствие документации (нет чеков, договора, акта)
- Подозрительные ссылки или сокращенные URL
- Неестественный стиль общения (слишком формальный/дружелюбный)

ШАГ 3: АНАЛИЗ МАНИПУЛЯТИВНЫХ ТЕХНИК
Определи, какие психологические тактики используются:
- СРОЧНОСТЬ: Давление временем, искусственные дедлайны
- ЖАДНОСТЬ: Слишком выгодные условия, "легкие деньги"
- СТРАХ: Угрозы потери, запугивание последствиями
- АВТОРИТЕТ: Ссылки на организации, статус, должности
- ЖАЛОСТЬ: Эмоциональные истории, просьбы о помощи
- ЭКСКЛЮЗИВНОСТЬ: "Только для вас", секретные предложения
- СОЦИАЛЬНОЕ ДОКАЗАТЕЛЬСТВО: Фейковые отзывы, рейтинги

ШАГ 4: ОПРЕДЕЛЕНИЕ ТИПА МОШЕННИЧЕСТВА
Классифицируй по одной из категорий:
- "rental_scam" — аренда/продажа недвижимости (фейковые объявления)
- "fake_seller" — поддельный продавец (товаров нет, требует предоплату)
- "investment_scam" — инвестиции, финансовые пирамиды
- "romance_scam" — романтическое мошенничество
- "phishing" — фишинг, кража персональных данных
- "job_scam" — фейковые вакансии, работа за предоплату
- "tech_support" — фейковая техподдержка
- "charity_scam" — фальшивая благотворительность
- "advanced_fee" — мошенничество с авансовым платежом
- "impersonation" — выдача себя за другое лицо
- "none" — нет признаков мошенничества

ШАГ 5: ОЦЕНКА РИСКА (0-100)
Используй следующую шкалу:
- 0-20: БЕЗОПАСНО — нет признаков мошенничества, все прозрачно
- 21-40: НИЗКИЙ РИСК — мелкие недочеты, но в целом безопасно
- 41-60: СРЕДНИЙ РИСК — несколько подозрительных признаков, нужна осторожность
- 61-80: ВЫСОКИЙ РИСК — явные признаки мошенничества, не рекомендуется продолжение
- 81-100: КРИТИЧЕСКИЙ РИСК — почти определенно мошенничество, опасно

При оценке учитывай:
- Количество выявленных маркеров
- Их серьезность (severity)
- Комбинацию нескольких тактик
- Контекст и правдоподобие ситуации
</analytical_framework>

<output_constraints>
ВАЖНО: Ты должен вернуть ответ СТРОГО в формате JSON.

ПРАВИЛА ФОРМАТИРОВАНИЯ:
1. НЕ добавляй markdown (```json или ```)
2. НЕ добавляй пояснений до или после JSON
3. ВСЕ поля должны присутствовать (обязательные ключи)
4. Числа должны быть валидными (не строки!)
5. Массивы не должны быть пустыми — минимум 1 элемент или "none"
6. Строки должны быть на РУССКОМ языке
7. Описание каждого red_flag должно быть КОНКРЕТНЫМ (не общие фразы!)

ПРИМЕР ХОРОШЕГО red_flag.description:
✅ "Требуется 100% предоплата на карту без договора — классическая схема мошенничества"
❌ "Есть проблемы с оплатой"

ПРИМЕР ХОРОШЕГО explanation:
✅ "Обнаружены 3 критических маркера: предоплата без договора, отсутствие возможности просмотра, только WhatsApp. Цена на 60% ниже рынка. Давление срочности."
❌ "Много подозрительных признаков"
</output_constraints>

<input_text>
{text}
</input_text>

<json_output_template>
Верни ответ в следующей структуре JSON (ЗАПОЛНИ ВСЕ ПОЛЯ):

{{
  "risk_score": 75,
  "scam_type": "rental_scam",
  "manipulation_tactics": ["urgency", "greed"],
  "extracted_info": {{
    "price_mentioned": true,
    "price_value": 500000,
    "prepayment_requested": true,
    "urgency_signals": true,
    "contact_complete": false,
    "suspicious_links": false,
    "meeting_available": false,
    "contract_offered": false,
    "photos_mentioned": false
  }},
  "red_flags": [
    {{
      "severity": 9,
      "category": "prepayment",
      "description": "Требуется полная предоплата на банковскую карту без заключения договора — это классическая схема мошенничества"
    }},
    {{
      "severity": 8,
      "category": "urgency",
      "description": "Используется давление срочности ('только сегодня', 'через час уезжаю') чтобы помешать вам проверить информацию"
    }}
  ],
  "confidence": 0.85,
  "explanation": "Обнаружены множественные критические маркеры мошенничества: предоплата без договора, невозможность личной встречи, аномально низкая цена. Комбинация тактик срочности и жадности.",
  "detailed_analysis": {{
    "text_quality": "Низкое качество текста — много общих фраз, нет конкретики",
    "price_analysis": "Цена на 60% ниже рыночной, что является серьезным предупреждающим сигналом",
    "contact_analysis": "Контактная информация неполная — только мессенджеры, нет телефона или email",
    "psychological_pressure": "Высокое давление — используются тактики срочности и исключения"
  }}
}}
</json_output_template>

Помни: от качества твоего анализа зависит финансовая безопасность человека. Будь максимально внимателен, объективен и конкретен.

СГЕНЕРИРУЙ JSON ОТВЕТ СЕЙЧАС:
"""

    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from Gemini response"""
        try:
            # Remove markdown code blocks if present
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*$', '', text)
            text = text.strip()
            
            # Find JSON object
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON extraction error: {e}")
        return None

    def _parse_gemini_response(self, data: Dict) -> AnalysisResult:
        """Parse structured Gemini response into AnalysisResult"""
        risk_score = min(max(data.get("risk_score", 50), 0), 100)
        scam_type = data.get("scam_type", "unknown")
        manipulation_tactics = data.get("manipulation_tactics", [])
        extracted_info = data.get("extracted_info", {})
        confidence = data.get("confidence", 0.5)
        explanation = data.get("explanation", "")
        detailed_analysis = data.get("detailed_analysis", {})

        # Build red flags
        red_flags = []
        for flag_data in data.get("red_flags", []):
            red_flags.append(RedFlag(
                severity=min(max(flag_data.get("severity", 5), 1), 10),
                category=flag_data.get("category", "unknown"),
                description=flag_data.get("description", "")
            ))

        # Add flags for manipulation tactics (with enhanced severity based on context)
        if manipulation_tactics and "none" not in manipulation_tactics:
            tactic_names = {
                "urgency": "Срочность и давление времени — вас торопят, чтобы вы не успели проверить информацию",
                "greed": "Манипуляция жадностью — предлагают слишком выгодные условия, чтобы затмить разум",
                "fear": "Запугивание и страх — используют ваши страхи для принятия необдуманных решений",
                "authority": "Поддельный авторитет — ссылаются на организации/статус для внушения доверия",
                "sympathy": "Манипуляция на жалость — давят на эмоции, чтобы получить деньги",
                "exclusivity": "Искусственная эксклюзивность — создают ощущение уникального предложения",
                "social_proof": "Поддельные отзывы — используют фейковые отзывы для доверия"
            }
            for tactic in manipulation_tactics:
                if tactic in tactic_names:
                    red_flags.append(RedFlag(
                        severity=7,
                        category="manipulation",
                        description=f"🧠 Обнаружена тактика манипуляции: {tactic_names[tactic]}"
                    ))

        # Build details with enhanced information
        details = {
            "scam_type": scam_type,
            "manipulation_tactics": manipulation_tactics,
            "extracted_info": extracted_info,
            "confidence": confidence,
            "explanation": explanation,
            "detailed_analysis": detailed_analysis,
            "module": "nlp_llm"
        }

        return AnalysisResult(
            risk_score=risk_score,
            risk_level=self._calculate_risk_level(risk_score),
            red_flags=red_flags,
            recommendations=self._generate_nlp_recommendations(
                risk_score, scam_type, manipulation_tactics, extracted_info, detailed_analysis
            ),
            details=details
        )

    def _generate_nlp_recommendations(
        self,
        risk_score: int,
        scam_type: str,
        manipulation_tactics: List[str],
        extracted_info: Dict,
        detailed_analysis: Dict = None
    ) -> List[str]:
        """
        Generate NLP-specific recommendations based on AI analysis

        Enhanced to use detailed_analysis from the new prompt structure
        """
        recommendations = []
        detailed = detailed_analysis or {}

        # Risk level based recommendations
        if risk_score >= 80:
            recommendations.append("🚨 КРИТИЧЕСКИЙ РИСК! Это почти определенно мошенничество")
            recommendations.append("🛑 НЕМЕДЛЕННО прекратите общение с этим человеком")
        elif risk_score >= 60:
            recommendations.append("🚨 ВЫСОКИЙ РИСК! Это сообщение с высокой вероятностью мошенническое")
            recommendations.append("⛔ Не переводите деньги и не предоставляйте личные данные")
        elif risk_score >= 40:
            recommendations.append("⚠️ СРЕДНИЙ РИСК! Подозрительное сообщение — будьте крайне осторожны")
            recommendations.append("🔍 Проведите дополнительную проверку перед любыми действиями")
        else:
            recommendations.append("✅ Нет явных признаков мошенничества, но оставайтесь бдительны")

        # Prepayment warnings (CRITICAL)
        if extracted_info.get("prepayment_requested"):
            if not extracted_info.get("contract_offered"):
                recommendations.append("💳 ТРЕБУЕТСЯ ПРЕДОПЛАТА БЕЗ ДОГОВОРА — это классическая схема мошенничества!")
            else:
                recommendations.append("💳 Запрошена предоплата — убедитесь, что есть официальный договор")

        # Meeting/Viewing availability
        if not extracted_info.get("meeting_available", True):
            recommendations.append("👁️ Невозможно посмотреть товар/жилье лично — это очень подозрительно")

        # Manipulation tactics warnings
        if "urgency" in manipulation_tactics:
            recommendations.append("⏰ Вас торопят! Мошенники используют срочность, чтобы вы не успели проверить информацию. Остановитесь и подумайте.")

        if "greed" in manipulation_tactics:
            recommendations.append("💰 Предложены слишком выгодные условия — это намеренная манипуляция. Проверьте рыночные цены.")

        if "fear" in manipulation_tactics:
            recommendations.append("😰 Вас пытаются запугать — это признак психологической манипуляции. Не принимайте решения под давлением.")

        if "sympathy" in manipulation_tactics:
            recommendations.append("💔 Давят на жалость — эмоциональная манипуляция. Отделите эмоции от фактов.")

        if "authority" in manipulation_tactics:
            recommendations.append("🎭 Ссылаются на авторитетные организации — проверьте эту информацию независимо.")

        # Contact information
        if not extracted_info.get("contact_complete"):
            recommendations.append("📞 Неполные контактные данные — запросите телефон или email для проверки")

        # Suspicious links
        if extracted_info.get("suspicious_links"):
            recommendations.append("🔗 Обнаружены подозрительные ссылки — НЕ переходите по ним, это может быть фишинг")

        # Price analysis
        if detailed.get("price_analysis"):
            recommendations.append(f"💵 {detailed['price_analysis']}")

        # Text quality
        if detailed.get("text_quality") and "низк" in detailed["text_quality"].lower():
            recommendations.append("📝 Качество текста низкий — мало конкретики, много общих фраз")

        # Psychological pressure
        if detailed.get("psychological_pressure") and "высок" in detailed["psychological_pressure"].lower():
            recommendations.append("🧠 Обнаружено высокое психологическое давление — это серьезный признак мошенничества")

        # Scam type specific recommendations
        scam_type_advice = {
            "rental_scam": "🏠 Фейковое объявление об аренде — проверьте объект лично перед оплатой",
            "fake_seller": "🛒 Поддельный продавец — товар может не существовать. Требуйте встречи.",
            "investment_scam": "📈 Финансовая пирамида — не инвестируйте без проверки лицензии ЦБ",
            "phishing": "🎣 Фишинг — не переходите по ссылкам и не вводите личные данные",
            "job_scam": "💼 Фейковая вакансия — не платите за трудоустройство",
            "romance_scam": "💔 Романтическое мошенничество — не переводите деньги людям из интернета",
            "advanced_fee": "💸 Мошенничество с авансом — не платите заранее без гарантий",
        }

        if scam_type in scam_type_advice and scam_type != "none":
            recommendations.append(scam_type_advice[scam_type])

        # Limit to most important recommendations (top 8)
        return recommendations[:8]

    def _calculate_risk_level(self, risk_score: int) -> RiskLevel:
        """Calculate risk level from score"""
        if risk_score < 30:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _fallback_analysis(self, listing: ListingData) -> AnalysisResult:
        """Fallback when Gemini is unavailable"""
        logger.warning("Using fallback NLP analysis")
        text = (listing.description or listing.title or "").lower()
        
        red_flags = []
        risk_score = 30  # Start with medium risk
        
        # Basic keyword checks
        scam_keywords = [
            "срочно", "предоплата", "без просмотра", "на карту",
            "только сегодня", "последний шанс", "гарантированно"
        ]
        
        for keyword in scam_keywords:
            if keyword in text:
                risk_score += 10
                red_flags.append(RedFlag(
                    severity=6,
                    category="pattern",
                    description=f"Обнаружен подозрительный ключ: '{keyword}'"
                ))
        
        risk_score = min(risk_score, 100)
        
        return AnalysisResult(
            risk_score=risk_score,
            risk_level=self._calculate_risk_level(risk_score),
            red_flags=red_flags,
            recommendations=["⚠️ Проведите дополнительную проверку"],
            details={"module": "nlp_fallback", "method": "keyword_matching"}
        )
