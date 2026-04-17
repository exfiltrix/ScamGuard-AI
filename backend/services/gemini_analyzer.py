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
from backend.services.api_key_manager import ApiKeyManager

# Suppress deprecation warning for old SDK
warnings.filterwarnings("ignore", category=FutureWarning)
from loguru import logger


class GeminiAnalyzer:
    """
    NLP/LLM Analyzer using Google Gemini (google-genai SDK).

    Uses the new google.genai SDK which is actively maintained.
    Supports multiple API keys with automatic round-robin rotation and
    per-key cooldown when a 429 / quota error is received.
    """

    MODEL_NAME = "gemini-2.0-flash"

    def __init__(self):
        settings = get_settings()
        keys = settings.get_google_api_keys()

        if not keys:
            raise ValueError("No Google API key(s) configured")

        self._key_manager = ApiKeyManager(keys)
        self._keys = keys

        logger.info(
            f"Gemini NLP Analyzer initialized with {self._key_manager.key_count()} key(s)"
        )

    def _get_client(self, key: str):
        from google import genai
        return genai.Client(api_key=key)

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
        
        prompt = self._build_nlp_prompt(text)
        loop = asyncio.get_event_loop()

        # Retry across all available keys on rate-limit or timeout errors
        last_exc: Optional[Exception] = None
        for attempt in range(self._key_manager.key_count()):
            key = self._key_manager.next_key()
            try:
                client = self._get_client(key)

                def _call():
                    from google.genai import types
                    return client.models.generate_content(
                        model=self.MODEL_NAME,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.1),
                    )

                response = await asyncio.wait_for(
                    loop.run_in_executor(None, _call),
                    timeout=15.0,
                )
                result_text = response.text or ""
                logger.debug(f"Gemini response (key ...{key[-6:]}): {result_text[:500]}")

                json_data = self._extract_json(result_text)
                if json_data:
                    return self._parse_gemini_response(json_data)

                logger.warning("Failed to parse Gemini JSON response")
                return await self._fallback_analysis(listing)

            except asyncio.TimeoutError:
                logger.warning(f"Gemini timeout on key ...{key[-6:]} (attempt {attempt + 1}). Rotating.")
                self._key_manager.mark_exhausted(key, cooldown=10.0)
                last_exc = asyncio.TimeoutError()
                continue
            except Exception as exc:
                if self._key_manager.is_rate_limit_error(exc):
                    err_str = str(exc).lower()
                    # Daily quota hit — no point trying other keys (same project)
                    if "per_day" in err_str or "perday" in err_str or "daily" in err_str or "per day" in err_str:
                        logger.warning(f"Daily quota exhausted on key ...{key[-6:]} — skipping to fallback")
                        return await self._fallback_analysis(listing)
                    logger.warning(f"Rate limit on key ...{key[-6:]} (attempt {attempt + 1}). Rotating.")
                    self._key_manager.mark_exhausted(key)
                    last_exc = exc
                    continue
                logger.error(f"Gemini NLP analysis error: {exc}")
                return await self._fallback_analysis(listing)

        logger.error(f"All API keys exhausted after {self._key_manager.key_count()} attempt(s): {last_exc}")
        return await self._fallback_analysis(listing)

    def _build_nlp_prompt(self, text: str) -> str:
        """
        Universal free-form scam detection prompt.

        No hardcoded categories or keyword lists — the model reads the message,
        reasons from first principles, and self-describes every finding.
        """
        return f"""Ты — система обнаружения мошенничества. Твоя задача: прочитать сообщение ниже и самостоятельно определить, является ли оно мошенническим, подозрительным или безопасным.

НЕ используй заранее заготовленные категории. Анализируй конкретное содержание: что именно написано, что от тебя хотят, какие эмоции и действия пытаются вызвать, какие несоответствия или аномалии ты замечаешь.

Проведи анализ в три шага (внутренне, не выводи их):

1. ЧТО ПРОИСХОДИТ — определи суть сообщения своими словами: кто пишет, что предлагает или требует, какова цель отправителя.

2. ЧТО НАСТОРАЖИВАЕТ — найди конкретные фразы, структуры, требования или несоответствия, которые указывают на обман. Каждый флаг должен быть привязан к реальному фрагменту текста.

3. ИТОГОВАЯ ОЦЕНКА — на основе найденного выставь риск-скор и сформулируй рекомендации для получателя сообщения.

Правила оценки риска:
- 0–20: сообщение выглядит нормально, явных признаков обмана нет
- 21–40: есть мелкие подозрительные моменты, но в целом безопасно
- 41–65: несколько тревожных сигналов, нужна осторожность
- 66–85: явные признаки мошенничества
- 86–100: практически наверняка мошенничество — опасно

Верни ТОЛЬКО валидный JSON без markdown-обёрток, без пояснений до и после. Все строки на русском языке.

Формат ответа:
{{
  "risk_score": <число 0-100>,
  "scam_type": "<краткое название типа угрозы своими словами, например: банковский фишинг, фейковый продавец, инвестиционная пирамида, романтическая ловушка, none>",
  "manipulation_tactics": ["<тактика 1>", "<тактика 2>"],
  "extracted_info": {{
    "prepayment_requested": <true/false>,
    "urgency_signals": <true/false>,
    "contact_complete": <true/false>,
    "suspicious_links": <true/false>,
    "meeting_available": <true/false>,
    "contract_offered": <true/false>,
    "impersonation_detected": <true/false>,
    "credentials_requested": <true/false>
  }},
  "red_flags": [
    {{
      "severity": <1-10>,
      "category": "<категория флага своими словами>",
      "description": "<конкретная фраза из текста + объяснение почему это опасно>"
    }}
  ],
  "confidence": <0.0-1.0>,
  "explanation": "<2-4 предложения: что именно обнаружено, почему опасно, на что обратить внимание>",
  "detailed_analysis": {{
    "sender_intent": "<цель отправителя, определённая самостоятельно>",
    "psychological_pressure": "<описание давления если есть, иначе none>",
    "anomalies": "<конкретные несоответствия или странности в тексте>",
    "verdict": "<итоговый вывод одним предложением>"
  }}
}}

СООБЩЕНИЕ ДЛЯ АНАЛИЗА:
{text}"""

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
        """Parse free-form Gemini response into AnalysisResult."""
        risk_score = min(max(int(data.get("risk_score", 50)), 0), 100)
        scam_type = data.get("scam_type", "unknown")
        manipulation_tactics = data.get("manipulation_tactics", [])
        extracted_info = data.get("extracted_info", {})
        confidence = data.get("confidence", 0.5)
        explanation = data.get("explanation", "")
        detailed_analysis = data.get("detailed_analysis", {})

        # Build red flags directly from AI output — no hardcoded mapping
        red_flags = []
        for flag_data in data.get("red_flags", []):
            desc = flag_data.get("description", "").strip()
            if not desc:
                continue
            red_flags.append(RedFlag(
                severity=min(max(int(flag_data.get("severity", 5)), 1), 10),
                category=flag_data.get("category", "ai_detected"),
                description=desc,
            ))

        # Add manipulation tactics as extra flags if AI named them
        if manipulation_tactics and "none" not in [t.lower() for t in manipulation_tactics]:
            for tactic in manipulation_tactics:
                if isinstance(tactic, str) and tactic.strip():
                    red_flags.append(RedFlag(
                        severity=7,
                        category="manipulation",
                        description=f"🧠 Тактика манипуляции: {tactic}",
                    ))

        details = {
            "scam_type": scam_type,
            "manipulation_tactics": manipulation_tactics,
            "extracted_info": extracted_info,
            "confidence": confidence,
            "explanation": explanation,
            "detailed_analysis": detailed_analysis,
            "module": "nlp_llm",
        }

        return AnalysisResult(
            risk_score=risk_score,
            risk_level=self._calculate_risk_level(risk_score),
            red_flags=red_flags,
            recommendations=self._generate_nlp_recommendations(
                risk_score, scam_type, manipulation_tactics, extracted_info, detailed_analysis
            ),
            details=details,
        )

    def _generate_nlp_recommendations(
        self,
        risk_score: int,
        scam_type: str,
        manipulation_tactics: List[str],
        extracted_info: Dict,
        detailed_analysis: Dict = None,
    ) -> List[str]:
        """Generate actionable recommendations from AI free-form analysis."""
        recommendations: List[str] = []
        detailed = detailed_analysis or {}

        # Base risk verdict
        if risk_score >= 86:
            recommendations.append("🚨 КРИТИЧЕСКИЙ РИСК — почти наверняка мошенничество. Прекратите общение немедленно.")
        elif risk_score >= 66:
            recommendations.append("🚨 ВЫСОКИЙ РИСК — явные признаки обмана. Не переводите деньги и не давайте данные.")
        elif risk_score >= 41:
            recommendations.append("⚠️ СРЕДНИЙ РИСК — есть подозрительные моменты. Проверьте перед любыми действиями.")
        else:
            recommendations.append("✅ Признаков мошенничества не обнаружено, но оставайтесь бдительны.")

        # Verdict from AI if available
        verdict = detailed.get("verdict", "")
        if verdict and verdict.lower() != "none":
            recommendations.append(f"🔎 {verdict}")

        # Sender intent from AI
        intent = detailed.get("sender_intent", "")
        if intent and intent.lower() != "none" and risk_score >= 40:
            recommendations.append(f"🎯 Цель отправителя: {intent}")

        # Specific dangers from extracted_info
        if extracted_info.get("credentials_requested"):
            recommendations.append("🔑 Не вводите логин, пароль или коды из SMS — это кража аккаунта.")
        if extracted_info.get("prepayment_requested") and not extracted_info.get("contract_offered"):
            recommendations.append("💳 Предоплата без договора — классическая схема. Откажитесь.")
        if extracted_info.get("suspicious_links"):
            recommendations.append("🔗 Не переходите по ссылкам из этого сообщения — возможен фишинг.")
        if extracted_info.get("impersonation_detected"):
            recommendations.append("🎭 Отправитель выдаёт себя за другое лицо или организацию. Проверьте через официальные каналы.")
        if not extracted_info.get("meeting_available", True) and risk_score >= 40:
            recommendations.append("👁️ Отказ от личной встречи — очень подозрительно.")

        # Psychological pressure note
        pressure = detailed.get("psychological_pressure", "")
        if pressure and pressure.lower() not in ("none", "нет", "отсутствует"):
            recommendations.append(f"😰 Психологическое давление: {pressure}")

        # Anomalies noted by AI
        anomalies = detailed.get("anomalies", "")
        if anomalies and anomalies.lower() not in ("none", "нет", "отсутствуют"):
            recommendations.append(f"⚠️ Аномалии в тексте: {anomalies}")

        return recommendations[:8]

    def _calculate_risk_level(self, risk_score: int) -> RiskLevel:
        """Calculate risk level from score"""
        if risk_score < 30:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    async def _fallback_analysis(self, listing: ListingData) -> AnalysisResult:
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
