"""
Context Analyzer — deep context + URL legitimacy check using Gemini with Google Search Grounding.

Flow:
1. Extract all URLs from the message
2. For each URL: ask Gemini (with Google Search) whether the domain is official/legitimate
3. Analyze the full message context: what is the sender really asking for?
4. Return structured verdict: is this message consistent with real-world facts?

Fallback (when Gemini quota is exhausted):
- HTTP metadata check (title, redirects, SSL)
- Domain reputation heuristics (already in URLAnalyzer)
- Return partial context verdict
"""

import asyncio
import re
import json
import httpx
from typing import Dict, List, Optional, Tuple
from loguru import logger


class ContextAnalyzer:
    """
    Uses Gemini with Google Search grounding to verify:
    1. Whether URLs in the message lead to real official sites
    2. Whether the claimed context (bank, brand, giveaway) actually exists
    3. Full message intent analysis with real-world knowledge
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self, api_keys: List[str]) -> None:
        self._keys = api_keys
        self._key_index = 0
        self._grounding_available = True  # toggled off if all keys quota-exhausted
        logger.info(f"ContextAnalyzer initialized with {len(api_keys)} key(s)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(self, text: str) -> Tuple[int, List[Dict], Dict]:
        """
        Full context analysis of a message.

        Returns:
            (risk_score 0-100, list of flag dicts, details dict)
        """
        urls = self._extract_urls(text)
        loop = asyncio.get_event_loop()

        # Try Gemini Search Grounding first
        if self._grounding_available and self._keys:
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self._gemini_context_check(text, urls)),
                    timeout=12.0,
                )
                if result:
                    return result
            except asyncio.TimeoutError:
                logger.warning("ContextAnalyzer: Gemini grounding timed out, falling back")
            except Exception as e:
                if "quota" in str(e).lower() or "429" in str(e) or "exhausted" in str(e).lower():
                    logger.warning("ContextAnalyzer: all keys quota-exhausted, switching to HTTP fallback")
                    self._grounding_available = False
                else:
                    logger.warning(f"ContextAnalyzer: Gemini error ({e}), falling back")

        # Fallback: HTTP metadata check for each URL
        if urls:
            return await self._http_fallback(urls, text)

        return 0, [], {"context_analysis": "no_urls", "grounding_used": False}

    # ------------------------------------------------------------------
    # Gemini Search Grounding
    # ------------------------------------------------------------------

    def _gemini_context_check(self, text: str, urls: List[str]) -> Optional[Tuple[int, List[Dict], Dict]]:
        """Synchronous call — runs in executor."""
        from google import genai
        from google.genai import types

        last_exc = None
        for attempt in range(len(self._keys)):
            key = self._keys[self._key_index % len(self._keys)]
            self._key_index += 1

            try:
                client = genai.Client(api_key=key)

                url_list = "\n".join(f"- {u}" for u in urls) if urls else "Нет ссылок"
                prompt = f"""Ты — эксперт по кибербезопасности. Используй поиск Google чтобы проверить факты.

СООБЩЕНИЕ ДЛЯ АНАЛИЗА:
{text}

ССЫЛКИ В СООБЩЕНИИ:
{url_list}

Выполни следующие проверки с помощью поиска:
1. Для каждой ссылки: является ли этот домен официальным сайтом реально существующей организации? Или это фишинговый/мошеннический сайт?
2. Организация/бренд упомянутые в сообщении — они реально существуют? Проводят ли они такие акции/верификации?
3. Соответствует ли контекст сообщения реальной практике легитимных организаций?

Верни ТОЛЬКО JSON без markdown:
{{
  "risk_score": <0-100>,
  "urls_verdict": [
    {{
      "url": "<url>",
      "is_official": <true/false>,
      "real_org_found": <true/false>,
      "verdict": "<что найдено в интернете об этом домене>",
      "severity": <1-10>
    }}
  ],
  "context_verdict": "<соответствует ли содержание сообщения реальным практикам — 2-3 предложения>",
  "grounding_findings": "<что конкретно нашёл поиск — факты из интернета>",
  "is_scam": <true/false>,
  "confidence": <0.0-1.0>
}}"""

                response = client.models.generate_content(
                    model=self.MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.1,
                    ),
                )

                raw = response.text or ""
                data = self._extract_json(raw)
                if not data:
                    logger.warning(f"ContextAnalyzer: could not parse JSON from Gemini response")
                    return None

                return self._build_result(data, grounding_used=True)

            except Exception as e:
                msg = str(e).lower()
                if "quota" in msg or "429" in msg or "exhausted" in msg or "resource_exhausted" in msg:
                    # Daily quota — skip remaining keys immediately
                    if "per_day" in msg or "perday" in msg or "daily" in msg or "per day" in msg:
                        self._grounding_available = False
                        raise Exception(f"Daily quota exhausted: {e}")
                    last_exc = e
                    continue
                raise

        # All keys exhausted
        self._grounding_available = False
        raise Exception(f"All keys quota-exhausted: {last_exc}")

    def _build_result(self, data: Dict, grounding_used: bool) -> Tuple[int, List[Dict], Dict]:
        risk_score = min(max(int(data.get("risk_score", 0)), 0), 100)
        flags: List[Dict] = []

        for url_v in data.get("urls_verdict", []):
            if not url_v.get("is_official", True):
                verdict_text = url_v.get("verdict", "")
                url = url_v.get("url", "")
                sev = min(max(int(url_v.get("severity", 8)), 1), 10)
                flags.append({
                    "severity": sev,
                    "category": "url_context",
                    "description": f"🔍 Проверка по интернету: '{url}' — {verdict_text}",
                })

        findings = data.get("grounding_findings", "")
        context_verdict = data.get("context_verdict", "")
        is_scam = data.get("is_scam", False)

        if is_scam and findings:
            flags.append({
                "severity": 9,
                "category": "context",
                "description": f"🌐 Интернет-проверка: {findings[:200]}",
            })

        if context_verdict:
            flags.append({
                "severity": 7 if is_scam else 3,
                "category": "context",
                "description": f"📋 Контекст: {context_verdict[:200]}",
            })

        details = {
            "grounding_used": grounding_used,
            "urls_verdict": data.get("urls_verdict", []),
            "context_verdict": context_verdict,
            "grounding_findings": findings,
            "is_scam": is_scam,
            "confidence": data.get("confidence", 0.5),
        }

        return risk_score, flags, details

    # ------------------------------------------------------------------
    # HTTP Fallback
    # ------------------------------------------------------------------

    async def _http_fallback(self, urls: List[str], text: str) -> Tuple[int, List[Dict], Dict]:
        """
        When Gemini quota is exhausted: check URLs via HTTP.
        Looks at: SSL cert, redirect chain, page title, response code.
        """
        flags: List[Dict] = []
        max_risk = 0
        url_reports = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=8.0,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ScamGuard/1.0)"},
        ) as client:
            for url in urls[:3]:
                report = await self._check_url_http(client, url)
                url_reports.append(report)

                if report["risk"] > 0:
                    max_risk = max(max_risk, report["risk"])
                    flags.append({
                        "severity": report["severity"],
                        "category": "url_context",
                        "description": report["description"],
                    })

        details = {
            "grounding_used": False,
            "fallback_used": True,
            "url_reports": url_reports,
        }

        return min(max_risk, 100), flags, details

    async def _check_url_http(self, client: httpx.AsyncClient, url: str) -> Dict:
        """Check a single URL via HTTP and return a risk report."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            resp = await client.get(url)
            final_url = str(resp.url)
            status = resp.status_code
            content = resp.text[:3000]

            # Extract page title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip()[:100] if title_match else ""

            risk = 0
            severity = 5
            description = ""

            # Non-200 status
            if status >= 400:
                risk = 30
                severity = 7
                description = f"🚫 Сайт {url} вернул ошибку {status} — страница не существует"

            # Redirect to completely different domain
            elif final_url != url:
                from urllib.parse import urlparse
                orig_apex = ".".join(urlparse(url).netloc.split(".")[-2:])
                final_apex = ".".join(urlparse(final_url).netloc.split(".")[-2:])
                if orig_apex != final_apex:
                    risk = 40
                    severity = 8
                    description = (
                        f"🔀 Ссылка '{url}' перенаправляет на другой домен: '{final_apex}' — "
                        f"типичный приём фишинга"
                    )

            # Suspicious page title patterns
            if title and not description:
                suspicious_titles = [
                    "verify", "login", "confirm", "account", "secure",
                    "sign in", "bank", "payment", "prize", "winner",
                    "подтвердить", "войти", "банк", "победитель",
                ]
                if any(t in title.lower() for t in suspicious_titles):
                    risk = max(risk, 35)
                    severity = 8
                    description = (
                        f"⚠️ Заголовок страницы '{title}' содержит подозрительные слова "
                        f"при нестандартном домене"
                    )

            # No HTTPS
            if url.startswith("http://") and not description:
                risk = max(risk, 20)
                severity = 6
                description = f"🔓 Сайт {url} не использует HTTPS — данные не защищены"

            if not description and risk == 0:
                description = f"✅ Сайт {url} отвечает (HTTP {status})"
                if title:
                    description += f", заголовок: '{title}'"

            return {
                "url": url,
                "final_url": final_url,
                "status": status,
                "title": title,
                "risk": risk,
                "severity": severity,
                "description": description,
            }

        except httpx.ConnectError:
            return {
                "url": url, "risk": 40, "severity": 8,
                "description": f"🚫 Не удалось подключиться к {url} — сайт не существует или заблокирован",
            }
        except Exception as e:
            logger.debug(f"HTTP check failed for {url}: {e}")
            return {"url": url, "risk": 0, "severity": 0, "description": ""}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_urls(self, text: str) -> List[str]:
        pattern = (
            r'https?://[^\s\)\]\>\"\'<]+'
            r'|(?<!\w)www\.[^\s\)\]\>\"\'<]+'
            r'|(?<!\w)(?:[a-zA-Z0-9\-]+\.)+(?:com|ru|uz|net|org|io|me|co|shop|site|online|info|biz|top|xyz|live|click|link|pw|tk|ml|ga|cf)(?:/[^\s\)\]\>\"\'<]*)?(?!\w)'
        )
        return list(dict.fromkeys(re.findall(pattern, text)))

    def _extract_json(self, text: str) -> Optional[Dict]:
        try:
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```\s*$", "", text)
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            logger.debug(f"JSON parse error: {e}")
        return None
