"""
Unified fraud detection pipeline v2.1
5 specialized AI modules: NLP/LLM, Rule Engine, Embedding, Image Analysis, Context/Grounding
"""
import asyncio as _asyncio
from typing import Dict, List, Optional
from backend.models.schemas import ListingData, AnalysisResult, RedFlag, RiskLevel
from backend.services.rule_engine import RuleEngine
from backend.services.gemini_analyzer import GeminiAnalyzer
from backend.services.image_analyzer import ImageAnalyzer
from backend.services.embedding_analyzer import EmbeddingAnalyzer
from backend.services.url_analyzer import URLAnalyzer
from backend.services.context_analyzer import ContextAnalyzer
from loguru import logger
from collections import defaultdict


class FraudDetectionPipeline:
    """
    Unified pipeline for fraud detection with 5 specialized modules

    Architecture:
    1. NLP/LLM Analysis (Gemini) - Context understanding, manipulation detection
    2. Rule Engine - Deterministic checks (price, prepayment, urgency)
    3. Embedding Analysis - Similarity with known scam patterns
    4. Image Analysis (Gemini Vision) - Stock photos, duplicates, quality
    5. Context/Grounding (Gemini + Google Search) - URL legitimacy, real-world verification
    """

    def __init__(self):
        from backend.config import get_settings
        settings = get_settings()
        keys = settings.get_google_api_keys()

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

        # Module 5: URL Analysis (offline heuristics)
        self.url_analyzer = URLAnalyzer()
        logger.info("✅ URL Module: initialized")

        # Module 6: Context/Grounding (Gemini + Google Search)
        self.context_analyzer = ContextAnalyzer(keys)
        logger.info("✅ Context/Grounding Module: initialized")

        # Weights for scoring (sum = 1.0)
        self.weights = {
            'nlp_llm': 0.25,
            'rule_engine': 0.20,
            'embedding': 0.10,
            'image_analysis': 0.10,
            'url_analysis': 0.15,
            'context': 0.20,
        }

    async def analyze(self, listing: ListingData) -> AnalysisResult:
        """Compatibility wrapper for URL/listing analysis."""
        return await self.analyze_listing(listing)

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

            # Module 3: URL Analysis (fast, offline) + Context HTTP fallback (parallel)
            try:
                url_result, ctx_result = await _asyncio.gather(
                    self.url_analyzer.analyze_urls(text),
                    self.context_analyzer.analyze(text),
                    return_exceptions=True,
                )

                if not isinstance(url_result, Exception):
                    url_score, url_flags, url_details = url_result
                    if url_score > 0:
                        component_scores['url_analysis'] = url_score
                        all_red_flags.extend([
                            RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                            for f in url_flags
                        ])
                        analysis_details['url_analysis'] = url_details
                        logger.debug(f"🔗 URL analysis: score={url_score}, flags={len(url_flags)}")

                if not isinstance(ctx_result, Exception) and ctx_result:
                    ctx_score, ctx_flags, ctx_details = ctx_result
                    if ctx_score > 0:
                        component_scores['context'] = ctx_score
                    all_red_flags.extend([
                        RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                        for f in ctx_flags
                    ])
                    analysis_details['context'] = ctx_details

            except Exception as e:
                logger.error(f"URL/Context analysis failed: {e}")

            # Calculate final score (rules + embeddings + URL + context)
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

                # Run NLP, Image, URL in parallel (rules already done)
                async def run_image():
                    if photos:
                        return await self.image_analyzer.analyze_photos(photos[:3])
                    return 0, [], {}

                nlp_result, image_result, url_result, ctx_result = await _asyncio.gather(
                    self.nlp_analyzer.analyze(pseudo_listing),
                    run_image(),
                    self.url_analyzer.analyze_urls(text),
                    self.context_analyzer.analyze(text),
                    return_exceptions=True
                )

                if isinstance(nlp_result, Exception):
                    logger.error(f"NLP failed: {nlp_result}")
                    nlp_result = await self.nlp_analyzer._fallback_analysis(pseudo_listing)

                component_scores['nlp_llm'] = nlp_result.risk_score
                all_red_flags.extend(nlp_result.red_flags)
                analysis_details['nlp_llm'] = nlp_result.details

                if isinstance(image_result, Exception):
                    logger.error(f"Image analysis failed: {image_result}")
                    component_scores['image_analysis'] = 0
                else:
                    image_score, image_flags, image_details = image_result
                    component_scores['image_analysis'] = image_score
                    all_red_flags.extend(image_flags)
                    if image_details:
                        analysis_details['image_analysis'] = image_details

                if not isinstance(url_result, Exception):
                    url_score, url_flags, url_details = url_result
                    if url_score > 0:
                        component_scores['url_analysis'] = url_score
                        all_red_flags.extend([
                            RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                            for f in url_flags
                        ])
                        analysis_details['url_analysis'] = url_details

                if not isinstance(ctx_result, Exception) and ctx_result:
                    ctx_score, ctx_flags, ctx_details = ctx_result
                    if ctx_score > 0:
                        component_scores['context'] = ctx_score
                    all_red_flags.extend([
                        RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                        for f in ctx_flags
                    ])
                    analysis_details['context'] = ctx_details
                elif isinstance(ctx_result, Exception):
                    logger.warning(f"Context analysis failed: {ctx_result}")

            else:
                # Run all modules: Rule Engine is sync+fast, others run in parallel
                logger.debug("📐 Rule Engine (sync)...")
                rule_score, rule_flags = self.rule_engine.analyze(pseudo_listing)
                component_scores['rule_engine'] = rule_score
                all_red_flags.extend(rule_flags)
                analysis_details['rule_engine'] = {
                    'score': rule_score,
                    'flags_count': len(rule_flags)
                }

                # NLP, Embedding, Image, URL — run in parallel
                async def run_embedding():
                    if text and len(text) > 20:
                        return await self.embedding_analyzer.analyze(text)
                    return 0, [], {}

                async def run_image():
                    if photos:
                        return await self.image_analyzer.analyze_photos(photos[:3])
                    return 0, [], {}

                nlp_result, emb_result, image_result, url_result, ctx_result = await _asyncio.gather(
                    self.nlp_analyzer.analyze(pseudo_listing),
                    run_embedding(),
                    run_image(),
                    self.url_analyzer.analyze_urls(text),
                    self.context_analyzer.analyze(text),
                    return_exceptions=True
                )

                if isinstance(nlp_result, Exception):
                    logger.error(f"NLP failed: {nlp_result}")
                    nlp_result = await self.nlp_analyzer._fallback_analysis(pseudo_listing)
                component_scores['nlp_llm'] = nlp_result.risk_score
                all_red_flags.extend(nlp_result.red_flags)
                analysis_details['nlp_llm'] = nlp_result.details

                if isinstance(emb_result, Exception):
                    logger.error(f"Embedding failed: {emb_result}")
                    component_scores['embedding'] = 0
                else:
                    emb_score, emb_flags, emb_details = emb_result
                    component_scores['embedding'] = emb_score
                    all_red_flags.extend(emb_flags)
                    if emb_details:
                        analysis_details['embedding'] = emb_details

                if not isinstance(url_result, Exception):
                    url_score, url_flags, url_details = url_result
                    if url_score > 0:
                        component_scores['url_analysis'] = url_score
                        all_red_flags.extend([
                            RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                            for f in url_flags
                        ])
                        analysis_details['url_analysis'] = url_details

                if isinstance(image_result, Exception):
                    logger.error(f"Image analysis failed: {image_result}")
                    component_scores['image_analysis'] = 0
                else:
                    image_score, image_flags, image_details = image_result
                    component_scores['image_analysis'] = image_score
                    all_red_flags.extend(image_flags)
                    if image_details:
                        analysis_details['image_analysis'] = image_details

                if not isinstance(ctx_result, Exception) and ctx_result:
                    ctx_score, ctx_flags, ctx_details = ctx_result
                    if ctx_score > 0:
                        component_scores['context'] = ctx_score
                    all_red_flags.extend([
                        RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                        for f in ctx_flags
                    ])
                    analysis_details['context'] = ctx_details
                elif isinstance(ctx_result, Exception):
                    logger.warning(f"Context analysis failed: {ctx_result}")

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
        """Calculate weighted score for quick check (rules + embeddings + URL + context)."""
        quick_weights = {
            'rule_engine': 0.40,
            'embedding': 0.15,
            'url_analysis': 0.25,
            'context': 0.20,
        }

        total_score = 0
        total_weight = 0

        for component, score in component_scores.items():
            if component in quick_weights and score > 0:
                weight = quick_weights[component]
                total_score += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50

        final_score = int(total_score / total_weight)

        rule_score = component_scores.get('rule_engine', 0)
        url_score  = component_scores.get('url_analysis', 0)
        ctx_score  = component_scores.get('context', 0)
        max_any    = max(component_scores.values()) if component_scores else 0

        if rule_score == 100:
            final_score = max(final_score, 85)
        elif rule_score >= 80:
            final_score = max(final_score, 75)

        if url_score >= 60:
            final_score = max(final_score, 70)

        if ctx_score >= 70:
            final_score = max(final_score, 75)

        if max_any >= 90:
            final_score = max(final_score, 80)

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

            # Module 4: Image Analysis + Context/Grounding (parallel)
            logger.debug("🖼 Module 4: Image + Context analysis...")

            async def run_image_msg():
                if photos:
                    return await self.image_analyzer.analyze_photos(photos)
                return 0, [], {}

            async def run_url_msg():
                return await self.url_analyzer.analyze_urls(text)

            image_result, url_result, ctx_result = await _asyncio.gather(
                run_image_msg(),
                run_url_msg(),
                self.context_analyzer.analyze(text),
                return_exceptions=True,
            )

            if isinstance(image_result, Exception):
                logger.error(f"Image analysis failed: {image_result}")
                component_scores['image_analysis'] = 0
            else:
                image_score, image_flags, image_details = image_result
                component_scores['image_analysis'] = image_score
                all_red_flags.extend(image_flags)
                if image_details:
                    analysis_details['image_analysis'] = image_details

            if not isinstance(url_result, Exception):
                url_score, url_flags, url_details = url_result
                if url_score > 0:
                    component_scores['url_analysis'] = url_score
                    all_red_flags.extend([
                        RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                        for f in url_flags
                    ])
                    analysis_details['url_analysis'] = url_details

            if not isinstance(ctx_result, Exception) and ctx_result:
                ctx_score, ctx_flags, ctx_details = ctx_result
                if ctx_score > 0:
                    component_scores['context'] = ctx_score
                all_red_flags.extend([
                    RedFlag(severity=f['severity'], category=f['category'], description=f['description'])
                    for f in ctx_flags
                ])
                analysis_details['context'] = ctx_details
            elif isinstance(ctx_result, Exception):
                logger.warning(f"Context analysis failed: {ctx_result}")

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
            try:
                return await self.nlp_analyzer.analyze(pseudo_listing)
            except:
                return self._emergency_fallback()

    def _calculate_weighted_score(self, component_scores: Dict[str, int]) -> int:
        """
        Weighted average score with floor protection.

        If any single module already signals HIGH/CRITICAL risk, the weighted
        average cannot artificially drag the score into MEDIUM territory.

        Floor rules:
          - rule_engine >= 80  → floor = 75
          - rule_engine == 100 → floor = 85
          - url_analysis >= 60 → floor = max(current, 70)
          - any module >= 90   → floor = max(current, 80)
        """
        total_score = 0
        total_weight = 0

        for component, score in component_scores.items():
            if component in self.weights and score > 0:
                weight = self.weights[component]
                total_score += score * weight
                total_weight += weight

        if total_weight == 0:
            return 50

        final_score = int(total_score / total_weight)

        # Apply floor protection
        rule_score = component_scores.get('rule_engine', 0)
        url_score  = component_scores.get('url_analysis', 0)
        ctx_score  = component_scores.get('context', 0)
        max_any    = max(component_scores.values()) if component_scores else 0

        if rule_score == 100:
            final_score = max(final_score, 85)
        elif rule_score >= 80:
            final_score = max(final_score, 75)

        if url_score >= 60:
            final_score = max(final_score, 70)

        if ctx_score >= 70:
            final_score = max(final_score, 75)

        if max_any >= 90:
            final_score = max(final_score, 80)

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

        if 'url_context' in flag_categories or 'context' in flag_categories:
            recommendations.append("🔍 Ссылки в сообщении не прошли проверку — сайт не существует или является мошенническим")

        if 'loan_scam' in flag_categories:
            recommendations.append("💸 Схема 'займи денег': мошенники взламывают аккаунты друзей и рассылают такие просьбы")
            recommendations.append("📞 Позвоните другу напрямую и убедитесь, что именно он писал — не отвечайте в этом же чате")

        if 'investment_scam' in flag_categories:
            recommendations.append("🤖 'Зарабатывай через мой бот' — это пирамида: деньги первых участников платят последним, большинство теряет всё")
            recommendations.append("🚫 Никогда не переводите деньги незнакомцам для 'инвестиций', даже если они показывают скриншоты заработка")

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
