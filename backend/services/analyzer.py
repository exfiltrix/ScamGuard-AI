from typing import List, Dict
from openai import AsyncOpenAI
from backend.models.schemas import ListingData, AnalysisResult, RedFlag, RiskLevel
from backend.config import get_settings
from loguru import logger
import json

settings = get_settings()


class AIAnalyzer:
    """AI-powered listing analyzer"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.ai_model
    
    async def analyze(self, listing: ListingData) -> AnalysisResult:
        """Analyze listing for scam indicators"""
        
        # Build analysis prompt
        prompt = self._build_prompt(listing)
        
        try:
            # Call OpenAI API
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Add images if available
            if listing.images and 'vision' in self.model:
                messages = self._add_images_to_prompt(messages, listing.images[:3])
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            content = response.choices[0].message.content
            result_data = json.loads(content)
            
            # Build result
            red_flags = [
                RedFlag(
                    category=flag.get('category', 'unknown'),
                    description=flag.get('description', ''),
                    severity=flag.get('severity', 5)
                )
                for flag in result_data.get('red_flags', [])
            ]
            
            risk_score = result_data.get('risk_score', 50)
            
            return AnalysisResult(
                risk_score=risk_score,
                risk_level=self._calculate_risk_level(risk_score),
                red_flags=red_flags,
                recommendations=result_data.get('recommendations', []),
                details=result_data.get('details', {})
            )
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            # Fallback to rule-based analysis
            return await self._fallback_analysis(listing)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for AI"""
        return """Ты эксперт по выявлению мошенничества в объявлениях аренды жилья.

Твоя задача - проанализировать объявление и оценить риск мошенничества.

Обрати внимание на:
1. Подозрительно низкая цена (намного ниже рынка)
2. Срочность и давление ("только сегодня", "последний шанс")
3. Требование 100% предоплаты без просмотра
4. Отсутствие контактной информации или документов
5. Плохое качество фотографий или фото из интернета
6. Грамматические ошибки и странный текст
7. Отсутствие деталей о жилье
8. Подозрительные контакты (только мессенджеры, нет телефона)

Верни результат строго в JSON формате:
{
  "risk_score": 0-100,
  "red_flags": [
    {
      "category": "price|urgency|prepayment|contact|quality|text|other",
      "description": "описание проблемы",
      "severity": 1-10
    }
  ],
  "recommendations": ["рекомендация 1", "рекомендация 2"],
  "details": {
    "price_analysis": "анализ цены",
    "text_quality": "качество текста",
    "contact_verification": "проверка контактов"
  }
}"""
    
    def _build_prompt(self, listing: ListingData) -> str:
        """Build analysis prompt"""
        prompt_parts = [
            "Проанализируй следующее объявление об аренде жилья:\n"
        ]
        
        if listing.title:
            prompt_parts.append(f"Заголовок: {listing.title}\n")
        
        if listing.description:
            prompt_parts.append(f"Описание:\n{listing.description[:1000]}\n")
        
        if listing.price and listing.currency:
            prompt_parts.append(f"Цена: {listing.price} {listing.currency}\n")
        
        if listing.location:
            prompt_parts.append(f"Локация: {listing.location}\n")
        
        if listing.contact_info:
            prompt_parts.append(f"Контакты: {listing.contact_info}\n")
        
        if listing.images:
            prompt_parts.append(f"Количество фотографий: {len(listing.images)}\n")
        
        prompt_parts.append("\nОцени риск мошенничества и дай рекомендации.")
        
        return "".join(prompt_parts)
    
    def _add_images_to_prompt(self, messages: List[Dict], image_urls: List[str]) -> List[Dict]:
        """Add images to prompt for vision models"""
        if not image_urls:
            return messages
        
        # Modify user message to include images
        content = [
            {"type": "text", "text": messages[-1]["content"]}
        ]
        
        for url in image_urls[:3]:  # Max 3 images
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })
        
        messages[-1]["content"] = content
        return messages
    
    def _calculate_risk_level(self, risk_score: int) -> RiskLevel:
        """Calculate risk level from score"""
        if risk_score < 30:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH
    
    async def _fallback_analysis(self, listing: ListingData) -> AnalysisResult:
        """Fallback rule-based analysis if AI fails"""
        red_flags = []
        risk_score = 0
        
        # Check for missing description
        if not listing.description or len(listing.description) < 50:
            red_flags.append(RedFlag(
                category="text",
                description="Слишком короткое или отсутствующее описание",
                severity=7
            ))
            risk_score += 20
        
        # Check for missing images
        if not listing.images:
            red_flags.append(RedFlag(
                category="quality",
                description="Отсутствуют фотографии",
                severity=8
            ))
            risk_score += 25
        
        # Check for missing contact info
        if not listing.contact_info:
            red_flags.append(RedFlag(
                category="contact",
                description="Отсутствует контактная информация",
                severity=9
            ))
            risk_score += 30
        
        # Check for suspicious keywords
        if listing.description:
            suspicious_keywords = ['срочно', 'только сегодня', '100% предоплата', 'без просмотра']
            for keyword in suspicious_keywords:
                if keyword.lower() in listing.description.lower():
                    red_flags.append(RedFlag(
                        category="urgency",
                        description=f"Подозрительное слово: '{keyword}'",
                        severity=6
                    ))
                    risk_score += 15
        
        risk_score = min(risk_score, 100)
        
        recommendations = [
            "⚠️ Не переводите деньги без личного просмотра жилья",
            "⚠️ Проверьте документы владельца",
            "⚠️ Встретьтесь лично перед заключением договора",
        ]
        
        if risk_score > 60:
            recommendations.insert(0, "🚨 ВЫСОКИЙ РИСК! Будьте крайне осторожны")
        
        return AnalysisResult(
            risk_score=risk_score,
            risk_level=self._calculate_risk_level(risk_score),
            red_flags=red_flags,
            recommendations=recommendations,
            details={
                "analysis_type": "fallback",
                "note": "Использован базовый анализ"
            }
        )
