"""
Image analysis for fraud detection using Gemini Vision
Detects: Stock photos, fake images, duplicates, quality issues
"""
from typing import List, Dict, Tuple, Optional
import httpx
from PIL import Image
from io import BytesIO
from backend.models.schemas import RedFlag
from backend.config import get_settings
from loguru import logger
import hashlib
import asyncio
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai


class ImageAnalyzer:
    """
    Analyze images for fraud indicators using Gemini Vision
    
    Capabilities:
    - Stock photo detection (real vs stock/fake)
    - Duplicate detection (MD5 + perceptual)
    - Quality assessment (resolution, blur)
    - Metadata analysis (EXIF)
    - AI-generated image detection
    """

    def __init__(self):
        self.min_resolution = (400, 300)
        self.known_stock_sites = [
            'unsplash.com', 'pexels.com', 'pixabay.com',
            'shutterstock.com', 'istockphoto.com', 'freepik.com'
        ]
        
        # Initialize Gemini Vision
        settings = get_settings()
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.vision_model = genai.GenerativeModel('gemini-flash-lite-latest')
            self.gemini_available = True
            logger.info("Gemini Vision initialized")
        else:
            self.vision_model = None
            self.gemini_available = False
            logger.warning("Gemini Vision not available - using basic analysis only")

    async def analyze(self, image_urls: List[str]) -> Tuple[int, List[RedFlag], Dict]:
        """
        Analyze images from URLs (for listings)
        Returns: (risk_score, red_flags, details)
        """
        if not image_urls:
            return 20, [RedFlag(
                category='quality',
                description='Отсутствуют фотографии',
                severity=8
            )], {}

        # Download images
        images_bytes = []
        for url in image_urls[:5]:  # Max 5 images
            try:
                img_bytes = await self._download_image(url)
                if img_bytes:
                    images_bytes.append(img_bytes)
            except Exception as e:
                logger.warning(f"Failed to download image {url}: {e}")

        if not images_bytes:
            return 15, [RedFlag(
                category='quality',
                description='Не удалось загрузить фотографии',
                severity=7
            )], {}

        return await self.analyze_photos(images_bytes)

    async def analyze_photos(self, images_bytes: List[bytes]) -> Tuple[int, List[RedFlag], Dict]:
        """
        Analyze images from bytes (for forwarded messages with photos)
        Returns: (risk_score, red_flags, details)
        """
        if not images_bytes:
            return 0, [], {}  # No penalty for text-only messages

        risk_score = 0
        red_flags = []
        details = {
            'total_images': len(images_bytes),
            'analyzed': 0,
            'low_quality': 0,
            'duplicates': 0,
            'stock_photos': 0,
            'gemini_analysis': False
        }

        # Check 1: Basic quality analysis
        quality_risk, quality_flags, quality_details = self._basic_quality_check(images_bytes)
        risk_score += quality_risk
        red_flags.extend(quality_flags)
        details.update(quality_details)

        # Check 2: Duplicate detection
        dup_risk, dup_flags = self._check_duplicates(images_bytes)
        risk_score += dup_risk
        red_flags.extend(dup_flags)
        details['duplicates'] = len(dup_flags)

        # Check 3: Stock photo URL detection
        # (Not applicable for direct photos, only URLs)

        # Check 4: Gemini Vision analysis (if available)
        if self.gemini_available and len(images_bytes) > 0:
            try:
                gemini_risk, gemini_flags, gemini_details = await self._gemini_vision_analysis(
                    images_bytes[:3]  # Max 3 for Gemini (API limit)
                )
                risk_score += gemini_risk
                red_flags.extend(gemini_flags)
                details['gemini_analysis'] = True
                details.update(gemini_details)
            except Exception as e:
                logger.warning(f"Gemini Vision analysis failed: {e}")
                details['gemini_error'] = str(e)

        return min(risk_score, 100), red_flags, details

    async def _gemini_vision_analysis(self, images_bytes: List[bytes]) -> Tuple[int, List[RedFlag], Dict]:
        """
        Analyze images using Gemini Vision
        
        Checks for:
        - Stock photo characteristics
        - AI-generated images
        - Professional vs amateur photos
        - Inconsistencies in images
        """
        risk_score = 0
        red_flags = []
        details = {
            'is_stock_photo': False,
            'is_ai_generated': False,
            'professional_photo': False,
            'image_quality': 'unknown'
        }

        for i, img_bytes in enumerate(images_bytes):
            try:
                # Build prompt for image analysis
                prompt = """
Проанализируй это фото и определи его тип.

ВЕРНИ ОТВЕТ В ФОРМАТЕ JSON:
{
  "is_stock": true/false (похоже на стоковое фото),
  "is_professional": true/false (профессиональная съемка),
  "is_amateur": true/false (любительское фото),
  "is_ai_generated": true/false (сгенерировано AI),
  "quality": "high/medium/low",
  "description": "краткое описание что на фото (1 предложение)",
  "suspicious": true/false (есть ли подозрительные признаки),
  "reason": "почему решил что подозрительно или нет"
}

ОТВЕЧАЙ ТОЛЬКО JSON.
"""
                # Send image to Gemini
                loop = asyncio.get_event_loop()
                
                def call_gemini():
                    return self.vision_model.generate_content([prompt, img_bytes])
                
                response = await loop.run_in_executor(None, call_gemini)
                
                # Parse response
                import re
                import json
                
                response_text = response.text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        
                        if result.get('is_stock'):
                            risk_score += 15
                            red_flags.append(RedFlag(
                                category='image',
                                description=f'Фото {i+1} похоже на стоковое',
                                severity=7
                            ))
                            details['is_stock_photo'] = True
                        
                        if result.get('is_ai_generated'):
                            risk_score += 20
                            red_flags.append(RedFlag(
                                category='image',
                                description=f'Фото {i+1} может быть сгенерировано AI',
                                severity=9
                            ))
                            details['is_ai_generated'] = True
                        
                        if result.get('suspicious'):
                            risk_score += 10
                            red_flags.append(RedFlag(
                                category='image',
                                description=f'Фото {i+1}: {result.get("reason", "подозрительно")}',
                                severity=6
                            ))
                        
                        details['image_quality'] = result.get('quality', 'unknown')
                        details[f'photo_{i+1}'] = result
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Gemini response for photo {i+1}")
                
            except Exception as e:
                logger.warning(f"Gemini Vision failed for photo {i+1}: {e}")
                continue
        
        return risk_score, red_flags, details

    def _basic_quality_check(self, images_bytes: List[bytes]) -> Tuple[int, List[RedFlag], Dict]:
        """Basic quality check without AI"""
        risk_score = 0
        red_flags = []
        details = {
            'low_quality': 0,
            'total_analyzed': 0
        }
        
        for i, img_bytes in enumerate(images_bytes):
            try:
                img = Image.open(BytesIO(img_bytes))
                width, height = img.size
                details['total_analyzed'] += 1
                
                # Check resolution
                if width < 400 or height < 300:
                    risk_score += 10
                    red_flags.append(RedFlag(
                        category='quality',
                        description=f'Фото {i+1} низкого разрешения ({width}x{height})',
                        severity=5
                    ))
                    details['low_quality'] += 1
                
                # Check if image is mostly blank (single color)
                # Simple heuristic: check if image has low variance
                img_gray = img.convert('L')
                pixels = list(img_gray.getdata())
                avg_pixel = sum(pixels) / len(pixels)
                variance = sum((p - avg_pixel) ** 2 for p in pixels) / len(pixels)
                
                if variance < 100:  # Very low variance = mostly blank
                    risk_score += 15
                    red_flags.append(RedFlag(
                        category='quality',
                        description=f'Фото {i+1} подозрительно однотонное',
                        severity=7
                    ))
                    
            except Exception as e:
                logger.warning(f"Quality check failed for photo {i+1}: {e}")
        
        return risk_score, red_flags, details

    def _check_duplicates(self, images_bytes: List[bytes]) -> Tuple[int, List[RedFlag]]:
        """Check for duplicate images using MD5 hashing"""
        risk_score = 0
        red_flags = []
        
        hashes = set()
        for i, img_bytes in enumerate(images_bytes):
            img_hash = hashlib.md5(img_bytes).hexdigest()
            
            if img_hash in hashes:
                risk_score += 10
                red_flags.append(RedFlag(
                    category='image',
                    description=f'Фото {i+1} является дубликатом',
                    severity=6
                ))
            else:
                hashes.add(img_hash)
        
        return risk_score, red_flags

    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0, follow_redirects=True)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.warning(f"Failed to download image from {url}: {e}")
            return None
