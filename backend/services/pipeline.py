"""
Unified fraud detection pipeline v2.0
4 specialized AI modules: NLP/LLM, Rule Engine, Embedding, Image Analysis
"""
from typing import Dict, List, Optional
from backend.models.schemas import ListingData, AnalysisResult, RedFlag, RiskLevel
from backend.services.rule_engine import RuleEngine
from backend.services.gemini_analyzer import GeminiAnalyzer
from backend.services.image_analyzer import ImageAnalyzer
from backend.services.embedding_analyzer import EmbeddingAnalyzer
from loguru import logger
from collections import defaultdict


class FraudDetectionPipeline:
    """
    Unified pipeline for fraud detection with 4 specialized modules
    
    Architecture:
    1. NLP/LLM Analysis (Gemini) - Context understanding, manipulation detection
    2. Rule Engine - Deterministic checks (price, prepayment, urgency)
    3. Embedding Analysis - Similarity with known scam patterns
    4. Image Analysis (Gemini Vision) - Stock photos, duplicates, quality
    """

    def __init__(self):
        from backend.config import get_settings
        settings = get_settings()

        # Module 1: NLP/LLM Analysis (Gemini)
        self.nlp_analyzer = GeminiAnalyzer()
        logger.info("✅ NLP/LLM Module: Gemini initialized")

        # Module 2: Rule Engine
        self.rule_engine = RuleEngine()
        logger.info("✅ Rule Engine: initialized")

        # Module 3: Embedding Analysis
        self.embedding_analyzer = EmbeddingAnalyzer()
        logger.info("✅ Embedding Module: initialized with scam database")

        # Module 4: Image Analysis
        self.image_analyzer = ImageAnalyzer()
        logger.info("✅ Image Module: initialized")

        # Weights for scoring (sum = 1.0)
        self.weights = {
            'nlp_llm': 0.35,        # AI understands context & manipulation
            'rule_engine': 0.25,    # Deterministic checks
            'embedding': 0.20,      # Known scam similarity
            'image_analysis': 0.20  # Photo authenticity
        }

    async def analyze_listing(self, listing: ListingData) -> AnalysisResult:
        """
        Legacy method - analyze from parsed URL/listing
        """
        logger.info(f"Starting fraud detection pipeline for {listing.url}")
        
        all_red_flags = []
        component_scores = {}
        analysis_details = {}

        try:
            # Module 1: NLP/LLM Analysis
            logger.debug("🧠 Module 1: NLP/LLM Analysis...")
            nlp_result = await self.nlp_analyzer.analyze(listing)
            component_scores['nlp_llm'] = nlp_result.risk_score
            all_red_flags.extend(nlp_result.red_flags)
            analysis_details['nlp_llm'] = nlp_result.details

            # Module 2: Rule Engine
            logger.debug("📐 Module 2: Rule Engine...")
            rule_score, rule_flags = self.rule_engine.analyze(listing)
            component_scores['rule_engine'] = rule_score
            all_red_flags.extend(rule_flags)
            analysis_details['rule_engine'] = {
                'score': rule_score,
                'flags_count': len(rule_flags)
            }

            # Module 3: Embedding Analysis
            logger.debug("🔗 Module 3: Embedding Analysis...")
            if listing.description:
                try:
                    emb_score, emb_flags, emb_details = await self.embedding_analyzer.analyze(
                        listing.description
                    )
                    component_scores['embedding'] = emb_score
                    all_red_flags.extend(emb_flags)
                    analysis_details['embedding'] = emb_details
                except Exception as e:
                    logger.error(f"Embedding analysis failed: {e}")
                    component_scores['embedding'] = 0
            else:
                component_scores['embedding'] = 0

            # Module 4: Image Analysis
            logger.debug("🖼 Module 4: Image Analysis...")
            if listing.images:
                try:
                    image_score, image_flags, image_details = await self.image_analyzer.analyze(
                        listing.images
                    )
                    component_scores['image_analysis'] = image_score
                    all_red_flags.extend(image_flags)
                    analysis_details['image_analysis'] = image_details
                except Exception as e:
                    logger.error(f"Image analysis failed: {e}")
                    component_scores['image_analysis'] = 20
            else:
                component_scores['image_analysis'] = 20  # Penalty for no images

            # Calculate final score
            final_score = self._calculate_weighted_score(component_scores)

            # Deduplicate and sort flags
            unique_flags = self._deduplicate_flags(all_red_flags)
            unique_flags.sort(key=lambda x: x.severity, reverse=True)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                final_score,
                unique_flags,
                analysis_details
            )

            # Add metadata
            analysis_details['component_scores'] = component_scores
            analysis_details['weights'] = self.weights
            analysis_details['final_score'] = final_score

            logger.info(f"✅ Pipeline completed. Final score: {final_score}")

            return AnalysisResult(
                risk_score=final_score,
                risk_level=self._calculate_risk_level(final_score),
                red_flags=unique_flags[:10],
                recommendations=recommendations,
                details=analysis_details
            )

        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}")
            # Fallback to NLP analysis
            try:
                return await self.nlp_analyzer._fallback_analysis(listing)
            except:
                return self._emergency_fallback()

    async def quick_check(
        self,
        text: str,
        has_photos: bool = False,
        metadata: Optional[Dict] = None,
    ) -> AnalysisResult:
        """
        QUICK CHECK: Rule Engine only (instant, no AI)

        This is the FIRST check when user sends a message.
        Returns immediate results with red flags and button for deep analysis.

        Args:
            text: Message text
            has_photos: Whether message has photos
            metadata: Additional metadata (has_file, file_count, etc.)

        Returns:
            AnalysisResult with rule-based analysis
        """
        logger.info(f"⚡ Quick check (rules only) for text length={len(text)}")

        # Merge provided metadata with defaults
        merged_metadata = {"quick_check": True, "has_photos": has_photos}
        if metadata:
            merged_metadata.update(metadata)

        # Create pseudo-listing for compatibility
        pseudo_listing = ListingData(
            url="telegram_message_quick",
            title="Telegram Message",
            description=text,
            price=None,
            location="",
            contact_info={},
            images=[],
            metadata=merged_metadata,
        )

        all_red_flags = []
        component_scores = {}
        analysis_details = {}

        try:
            # Module 1: Rule Engine (PRIMARY for quick check)
            logger.debug("📐 Quick Check: Rule Engine...")
            rule_score, rule_flags = self.rule_engine.analyze(pseudo_listing)
            component_scores['rule_engine'] = rule_score
            all_red_flags.extend(rule_flags)
            analysis_details['rule_engine'] = {
                'score': rule_score,
                'flags_count': len(rule_flags)
            }

            # Module 2: Embedding Analysis (fast, no API call)
            if text and len(text) > 20:
                try:
                    emb_score, emb_flags, emb_details = await self.embedding_analyzer.analyze(text)
                    component_scores['embedding'] = emb_score
                    all_red_flags.extend(emb_flags)
                    analysis_details['embedding'] = emb_details
                except Exception as e:
                    logger.error(f"Embedding analysis failed: {e}")
                    component_scores['embedding'] = 0
            else:
                component_scores['embedding'] = 0

            # Calculate final score (only rules + embeddings, no AI)
            # Adjust weights for quick check
            final_score = self._calculate_weighted_score_quick(component_scores)

            # Deduplicate and sort flags
            unique_flags = self._deduplicate_flags(all_red_flags)
            unique_flags.sort(key=lambda x: x.severity, reverse=True)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                final_score,
                unique_flags,
                analysis_details
            )

            # Add metadata
            analysis_details['component_scores'] = component_scores
            analysis_details['is_quick_check'] = True
            analysis_details['needs_deep_analysis'] = True

            logger.info(f"✅ Quick check completed. Score: {final_score}")

            return AnalysisResult(
                risk_score=final_score,
                risk_level=self._calculate_risk_level(final_score),
                red_flags=unique_flags[:10],
                recommendations=recommendations,
                details=analysis_details
            )

        except Exception as e:
            logger.error(f"❌ Quick check error: {e}")
            return self._emergency_fallback()

    async def deep_analyze(
        self,
        text: str,
        photos: Optional[List[bytes]] = None,
        is_forwarded: bool = False,
        forward_info: Optional[Dict] = None,
        quick_result: Optional[AnalysisResult] = None
    ) -> AnalysisResult:
        """
        DEEP ANALYSIS: Full pipeline with AI (Gemini NLP + Vision)

        This runs when user clicks "Deep AI Analysis" button.
        Can reuse quick_result to avoid duplicate rule checks.

        Args:
            text: Message text
            photos: List of photo bytes (up to 3)
            is_forwarded: Whether message was forwarded
            forward_info: Info about forwarded message sender
            quick_result: Optional quick check result to reuse

        Returns:
            AnalysisResult with full AI analysis
        """
        logger.info(f"🔍 Deep analysis (full AI pipeline) (forwarded={is_forwarded}, photos={len(photos) if photos else 0})")

        all_red_flags = []
        component_scores = {}
        analysis_details = {}

        # Create pseudo-listing for compatibility
        pseudo_listing = ListingData(
            url="telegram_message_deep",
            title="Telegram Message",
            description=text,
            price=None,
            location="",
            contact_info={},
            images=photos or [],
            metadata={
                "is_forwarded": is_forwarded,
                "forward_info": forward_info,
                "deep_analysis": True
            }
        )

        try:
            # If we have quick_result, reuse rule/embedding scores
            if quick_result and quick_result.details:
                logger.debug("♻️ Reusing quick check results")
                qc_scores = quick_result.details.get('component_scores', {})
                component_scores['rule_engine'] = qc_scores.get('rule_engine', 0)
                component_scores['embedding'] = qc_scores.get('embedding', 0)
                all_red_flags.extend(quick_result.red_flags)
                analysis_details['reused_from_quick'] = True
            else:
                # Run Rule Engine
                logger.debug("📐 Module 2: Rule Engine...")
                rule_score, rule_flags = self.rule_engine.analyze(pseudo_listing)
                component_scores['rule_engine'] = rule_score
                all_red_flags.extend(rule_flags)
                analysis_details['rule_engine'] = {
                    'score': rule_score,
                    'flags_count': len(rule_flags)
                }

                # Run Embedding Analysis
                if text and len(text) > 20:
                    try:
                        emb_score, emb_flags, emb_details = await self.embedding_analyzer.analyze(text)
                        component_scores['embedding'] = emb_score
                        all_red_flags.extend(emb_flags)
                        analysis_details['embedding'] = emb_details
                    except Exception as e:
                        logger.error(f"Embedding analysis failed: {e}")
                        component_scores['embedding'] = 0
                else:
                    component_scores['embedding'] = 0

            # Module 1: NLP/LLM Analysis (Gemini) - PRIMARY
            logger.debug("🧠 Module 1: Gemini NLP Analysis...")
            nlp_result = await self.nlp_analyzer.analyze(pseudo_listing)
            component_scores['nlp_llm'] = nlp_result.risk_score
            all_red_flags.extend(nlp_result.red_flags)
            analysis_details['nlp_llm'] = nlp_result.details

            # Module 4: Image Analysis (if photos exist, max 3)
            if photos and len(photos) > 0:
                logger.debug(f"🖼 Module 4: Image Analysis ({len(photos)} photos)...")
                try:
                    # Limit to 3 photos for speed
                    photos_limited = photos[:3]
                    image_score, image_flags, image_details = await self.image_analyzer.analyze_photos(
                        photos_limited
                    )
                    component_scores['image_analysis'] = image_score
                    all_red_flags.extend(image_flags)
                    analysis_details['image_analysis'] = image_details
                except Exception as e:
                    logger.error(f"Image analysis failed: {e}")
                    component_scores['image_analysis'] = 0
            else:
                component_scores['image_analysis'] = 0

            # Calculate final score
            final_score = self._calculate_weighted_score(component_scores)

            # Deduplicate and sort flags
            unique_flags = self._deduplicate_flags(all_red_flags)
            unique_flags.sort(key=lambda x: x.severity, reverse=True)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                final_score,
                unique_flags,
                analysis_details
            )

            # Add metadata
            analysis_details['component_scores'] = component_scores
            analysis_details['weights'] = self.weights
            analysis_details['final_score'] = final_score
            analysis_details['message_type'] = "forwarded" if is_forwarded else "direct"
            analysis_details['is_deep_analysis'] = True

            logger.info(f"✅ Deep analysis completed. Final score: {final_score}")

            return AnalysisResult(
                risk_score=final_score,
                risk_level=self._calculate_risk_level(final_score),
                red_flags=unique_flags[:10],
                recommendations=recommendations,
                details=analysis_details
            )

        except Exception as e:
            logger.error(f"❌ Deep analysis error: {e}")
            # Fallback to NLP analysis
            try:
                return await self.nlp_analyzer.analyze(pseudo_listing)
            except:
                return self._emergency_fallback()

    def _calculate_weighted_score_quick(self, component_scores: Dict[str, int]) -> int:
        """Calculate weighted score for quick check (rules + embeddings only)"""
        # Adjusted weights for quick check (no AI)
        quick_weights = {
            'rule_engine': 0.60,
            'embedding': 0.40,
        }

        total_score = 0
        total_weight = 0

        for component, score in component_scores.items():
            if component in quick_weights and score > 0:
                weight = quick_weights[component]
                total_score += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50  # Default medium risk

        final_score = int(total_score / total_weight)
        return min(max(final_score, 0), 100)

    async def analyze_message(
        self,
        text: str,
        photos: Optional[List[bytes]] = None,
        is_forwarded: bool = False,
        forward_info: Optional[Dict] = None
    ) -> AnalysisResult:
        """
        NEW: Analyze a forwarded message or direct text
        
        This is the primary method for the new bot workflow.
        User forwards a suspicious message, and we run it through all 4 modules.
        
        Args:
            text: Message text from user/scammer
            photos: List of photo bytes (up to 5)
            is_forwarded: Whether message was forwarded
            forward_info: Info about forwarded message sender
            
        Returns:
            AnalysisResult with risk score, flags, and recommendations
        """
        logger.info(f"📨 Starting message analysis pipeline (forwarded={is_forwarded})")
        
        all_red_flags = []
        component_scores = {}
        analysis_details = {}

        # Create pseudo-listing for compatibility
        pseudo_listing = ListingData(
            url="telegram_message",
            title="Telegram Message",
            description=text,
            price=None,
            location="",
            contact_info={},
            images=photos or [],
            metadata={
                "is_forwarded": is_forwarded,
                "forward_info": forward_info
            }
        )

        try:
            # Module 1: NLP/LLM Analysis (PRIMARY)
            logger.debug("🧠 Module 1: NLP/LLM Analysis (Gemini)...")
            nlp_result = await self.nlp_analyzer.analyze(pseudo_listing)
            component_scores['nlp_llm'] = nlp_result.risk_score
            all_red_flags.extend(nlp_result.red_flags)
            analysis_details['nlp_llm'] = nlp_result.details

            # Module 2: Rule Engine
            logger.debug("📐 Module 2: Rule Engine...")
            rule_score, rule_flags = self.rule_engine.analyze(pseudo_listing)
            component_scores['rule_engine'] = rule_score
            all_red_flags.extend(rule_flags)
            analysis_details['rule_engine'] = {
                'score': rule_score,
                'flags_count': len(rule_flags)
            }

            # Module 3: Embedding Analysis (if text exists)
            logger.debug("🔗 Module 3: Embedding Analysis...")
            if text and len(text) > 20:  # Need minimum text for embeddings
                try:
                    emb_score, emb_flags, emb_details = await self.embedding_analyzer.analyze(text)
                    component_scores['embedding'] = emb_score
                    all_red_flags.extend(emb_flags)
                    analysis_details['embedding'] = emb_details
                except Exception as e:
                    logger.error(f"Embedding analysis failed: {e}")
                    component_scores['embedding'] = 0
            else:
                component_scores['embedding'] = 0
                logger.debug("Embedding skipped (text too short)")

            # Module 4: Image Analysis (if photos exist)
            logger.debug("🖼 Module 4: Image Analysis (Gemini Vision)...")
            if photos:
                try:
                    image_score, image_flags, image_details = await self.image_analyzer.analyze_photos(
                        photos
                    )
                    component_scores['image_analysis'] = image_score
                    all_red_flags.extend(image_flags)
                    analysis_details['image_analysis'] = image_details
                except Exception as e:
                    logger.error(f"Image analysis failed: {e}")
                    component_scores['image_analysis'] = 20
            else:
                component_scores['image_analysis'] = 0  # No penalty for text-only messages

            # Calculate final score
            final_score = self._calculate_weighted_score(component_scores)

            # Deduplicate and sort flags
            unique_flags = self._deduplicate_flags(all_red_flags)
            unique_flags.sort(key=lambda x: x.severity, reverse=True)

            # Generate personalized recommendations
            recommendations = self._generate_recommendations(
                final_score,
                unique_flags,
                analysis_details
            )

            # Add metadata
            analysis_details['component_scores'] = component_scores
            analysis_details['weights'] = self.weights
            analysis_details['final_score'] = final_score
            analysis_details['message_type'] = "forwarded" if is_forwarded else "direct"

            logger.info(f"✅ Message analysis completed. Final score: {final_score}")

            return AnalysisResult(
                risk_score=final_score,
                risk_level=self._calculate_risk_level(final_score),
                red_flags=unique_flags[:10],
                recommendations=recommendations,
                details=analysis_details
            )

        except Exception as e:
            logger.error(f"❌ Message pipeline error: {e}")
            # Fallback to simple NLP analysis
            try:
                return await self.nlp_analyzer.analyze(pseudo_listing)
            except:
                return self._emergency_fallback()

    def _calculate_weighted_score(self, component_scores: Dict[str, int]) -> int:
        """Calculate weighted average score from components"""
        total_score = 0
        total_weight = 0

        for component, score in component_scores.items():
            if component in self.weights and score > 0:
                weight = self.weights[component]
                total_score += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50  # Default medium risk

        final_score = int(total_score / total_weight)
        return min(max(final_score, 0), 100)

    def _deduplicate_flags(self, flags: List[RedFlag]) -> List[RedFlag]:
        """Remove duplicate red flags"""
        seen = set()
        unique_flags = []

        for flag in flags:
            key = f"{flag.category}:{flag.description[:50]}"
            if key not in seen:
                seen.add(key)
                unique_flags.append(flag)

        return unique_flags

    def _calculate_risk_level(self, risk_score: int) -> RiskLevel:
        """Calculate risk level from score"""
        if risk_score < 30:
            return RiskLevel.LOW
        elif risk_score < 60:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _generate_recommendations(
        self,
        risk_score: int,
        red_flags: List[RedFlag],
        details: Dict
    ) -> List[str]:
        """Generate personalized recommendations based on analysis"""
        recommendations = []

        # Group flags by category
        flag_categories = defaultdict(list)
        for flag in red_flags:
            flag_categories[flag.category].append(flag)

        # Risk level based recommendations
        if risk_score >= 70:
            recommendations.append("🚨 ВЫСОКИЙ РИСК! Не продолжайте общение с этим человеком")
            recommendations.append("🚨 Ни в коем случае не переводите деньги")
        elif risk_score >= 50:
            recommendations.append("⚠️ СРЕДНИЙ РИСК! Будьте крайне осторожны")
            recommendations.append("⚠️ Не принимайте поспешных решений под давлением")
        else:
            recommendations.append("✅ Риск относительно низкий, но оставайтесь бдительны")

        # Category-specific recommendations
        if 'price' in flag_categories:
            recommendations.append("💰 Проверьте рыночные цены — слишком низкая цена подозрительна")

        if 'prepayment' in flag_categories or 'payment' in flag_categories:
            recommendations.append("💳 Не переводите предоплату без личной встречи и проверки")

        if 'urgency' in flag_categories or 'pressure' in flag_categories:
            recommendations.append("⏰ Не поддавайтесь на срочность — мошенники торопят жертв")

        if 'contact' in flag_categories:
            recommendations.append("📞 Требуйте полные контактные данные и проверяйте их")

        if 'image' in flag_categories or 'quality' in flag_categories:
            recommendations.append("📸 Попросите дополнительные фото или устройте видеозвонок")

        if 'pattern' in flag_categories or 'embedding' in flag_categories:
            recommendations.append("🔍 Сообщение похоже на известные схемы мошенничества")

        if 'manipulation' in flag_categories:
            recommendations.append("🧠 Обнаружены психологические манипуляции — будьте начеку")

        # General safety recommendations
        recommendations.append("🤝 Встречайтесь лично перед любыми финансовыми операциями")
        recommendations.append("📝 Проверяйте документы и удостоверяйте личность")

        # Limit to top recommendations
        return recommendations[:8]

    def _emergency_fallback(self) -> AnalysisResult:
        """Emergency fallback when everything fails"""
        logger.warning("🆘 Using emergency fallback - all modules failed")
        return AnalysisResult(
            risk_score=50,
            risk_level=RiskLevel.MEDIUM,
            red_flags=[
                RedFlag(
                    severity=5,
                    category="system",
                    description="Не удалось провести полный анализ. Будьте осторожны!"
                )
            ],
            recommendations=[
                "⚠️ Произошла ошибка при анализе",
                "🤝 Встречайтесь лично перед любыми финансовыми операциями",
                "📞 Проверяйте личность собеседника"
            ],
            details={"error": "Pipeline failure, using fallback"}
        )
