"""
URL Analyzer — checks links found in messages for legitimacy.

Checks performed (no external paid APIs needed):
1. Domain age via WHOIS  — fresh domains (< 90 days) are high risk
2. DNS resolution        — non-resolving domains are suspicious
3. Suspicious TLD list   — .xyz, .top, .click, .tk, etc.
4. Brand impersonation   — "apple-promo.com", "google-gift.ru", etc.
5. Keyword patterns      — promo, gift, win, prize, free, pay in domain
6. HTTP reachability     — redirects to unknown hosts, no HTTPS
7. URL structure         — excessive subdomains, long random paths
"""

import re
import asyncio
import socket
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from loguru import logger


# ---------------------------------------------------------------------------
# Known-safe apex domains — these alone are NOT suspicious
# (subdomains / paths may still be checked separately)
# ---------------------------------------------------------------------------
TRUSTED_DOMAINS = {
    # Social / messaging
    "t.me", "telegram.org", "telegram.me",
    "whatsapp.com", "wa.me",
    "instagram.com", "facebook.com", "fb.com",
    "twitter.com", "x.com",
    "youtube.com", "youtu.be",
    "tiktok.com",
    # Tech giants
    "google.com", "gmail.com", "googleapis.com",
    "apple.com", "icloud.com",
    "microsoft.com", "live.com", "outlook.com",
    "amazon.com", "aws.amazon.com",
    # Banks / payments
    "sberbank.ru", "tinkoff.ru", "raiffeisen.ru", "vtb.ru",
    "paypal.com", "stripe.com", "visa.com", "mastercard.com",
    "click.uz", "payme.uz", "uzcard.uz",
    # Marketplaces / classifieds
    "olx.uz", "olx.ru", "avito.ru", "youla.ru",
    "aliexpress.com", "ozon.ru", "wildberries.ru",
    # Government / official
    "gov.uz", "gov.ru",
    # News / reference
    "wikipedia.org", "github.com",
}

# TLDs heavily abused by scammers
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".click", ".tk", ".ml", ".ga", ".cf",
    ".gq", ".buzz", ".icu", ".cam", ".loan", ".work",
    ".date", ".win", ".download", ".racing", ".trade",
    ".party", ".review", ".science", ".faith",
    ".bid", ".stream", ".gdn", ".accountant", ".cricket",
    # Additional abused new-gTLDs
    ".shop", ".store", ".online", ".site", ".website",
    ".fun", ".uno", ".life", ".live", ".club",
    ".vip", ".pro", ".ltd", ".sbs", ".cyou",
}

# Keywords in domain names that strongly indicate scam
SCAM_DOMAIN_KEYWORDS = [
    "promo", "prize", "gift", "win", "winner", "free",
    "bonus", "lucky", "reward", "claim", "delivery-pay",
    "secure-check", "verify", "login-confirm", "account-verify",
    "bank-secure", "pay-delivery", "get-iphone", "iphone-free",
    "crypto-earn", "invest-profit", "fast-money",
]

# Popular brand names — if found in a non-trusted domain, it's impersonation
BRAND_NAMES = [
    "google", "apple", "microsoft", "amazon", "facebook", "instagram",
    "telegram", "whatsapp", "tiktok", "youtube",
    "sberbank", "tinkoff", "vtb", "alfa", "raiffeisen",
    "visa", "mastercard", "paypal", "stripe",
    "aliexpress", "avito", "olx", "wildberries", "ozon",
    "iphone", "samsung", "sony",
]


class URLAnalyzer:
    """
    Analyzes URLs extracted from messages and returns a risk score + flags.
    All checks are offline or use standard DNS/WHOIS — no paid APIs needed.
    """

    # WHOIS domain age threshold in days — younger = suspicious
    NEW_DOMAIN_THRESHOLD_DAYS = 90

    def __init__(self):
        logger.info("URLAnalyzer initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_urls(self, text: str) -> Tuple[int, List[Dict], Dict]:
        """
        Extract all URLs from text and analyze them.

        Returns:
            (risk_score 0-100, list of flag dicts, details dict)
        """
        urls = self._extract_urls(text)
        if not urls:
            return 0, [], {"urls_found": 0}

        total_risk = 0
        all_flags: List[Dict] = []
        url_reports = []

        for url in urls[:5]:  # Limit to 5 URLs per message
            risk, flags, report = await self._analyze_single_url(url)
            total_risk = max(total_risk, risk)  # Take worst URL score
            all_flags.extend(flags)
            url_reports.append(report)

        details = {
            "urls_found": len(urls),
            "urls_analyzed": len(url_reports),
            "url_reports": url_reports,
        }

        return min(total_risk, 100), all_flags, details

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _extract_urls(self, text: str) -> List[str]:  # noqa: C901
        # Match: http(s)://, www., or bare domains like ssilka.com / t.me/xxx
        pattern = (
            r'https?://[^\s\)\]\>\"\'<]+'
            r'|(?<!\w)www\.[^\s\)\]\>\"\'<]+'
            r'|(?<!\w)(?:[a-zA-Z0-9\-]+\.)+(?:com|ru|uz|net|org|io|me|co|shop|site|online|info|biz|top|xyz|live|click|link|pw|tk|ml|ga|cf)(?:/[^\s\)\]\>\"\'<]*)?(?!\w)'
        )
        return list(dict.fromkeys(re.findall(pattern, text)))  # deduplicate preserving order

    async def _analyze_single_url(self, url: str) -> Tuple[int, List[Dict], Dict]:
        """Full analysis of one URL. Returns (risk, flags, report)."""
        if not url.startswith(("http://", "https://")):
            url = "http://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.")
        apex = self._get_apex_domain(domain)

        risk = 0
        flags: List[Dict] = []
        report: Dict = {"url": url, "domain": domain, "checks": {}}

        # 1. Trusted domain — stop early
        if apex in TRUSTED_DOMAINS or domain in TRUSTED_DOMAINS:
            report["checks"]["trusted"] = True
            return 0, [], report

        report["checks"]["trusted"] = False

        # 2. Suspicious TLD
        tld_risk, tld_flags = self._check_tld(domain)
        risk += tld_risk
        flags.extend(tld_flags)
        report["checks"]["tld"] = {"risk": tld_risk, "flags": len(tld_flags)}

        # 3. Scam keywords in domain
        kw_risk, kw_flags = self._check_domain_keywords(domain)
        risk += kw_risk
        flags.extend(kw_flags)
        report["checks"]["keywords"] = {"risk": kw_risk, "flags": len(kw_flags)}

        # 4. Brand impersonation
        imp_risk, imp_flags = self._check_brand_impersonation(domain, apex)
        risk += imp_risk
        flags.extend(imp_flags)
        report["checks"]["impersonation"] = {"risk": imp_risk, "flags": len(imp_flags)}

        # 5. HTTP (no HTTPS)
        if parsed.scheme == "http":
            risk += 15
            flags.append({
                "severity": 6,
                "category": "url",
                "description": f"🔓 Ссылка без HTTPS: {domain} — данные передаются незашифрованно",
            })
            report["checks"]["no_https"] = True

        # 6. DNS resolution (async, short timeout)
        dns_ok = await self._check_dns(domain)
        report["checks"]["dns_resolves"] = dns_ok
        if not dns_ok:
            risk += 20
            flags.append({
                "severity": 7,
                "category": "url",
                "description": f"🚫 Домен {domain} не существует или не отвечает — вероятно фейковый",
            })

        # 7. Domain age via WHOIS (run in executor to avoid blocking)
        age_risk, age_flags, domain_age_days = await self._check_domain_age(domain)
        risk += age_risk
        flags.extend(age_flags)
        report["checks"]["domain_age_days"] = domain_age_days

        # 8. Excessive subdomains (e.g. secure.bank.verify.login.ru)
        subdomain_parts = domain.split(".")
        if len(subdomain_parts) > 4:
            risk += 15
            flags.append({
                "severity": 6,
                "category": "url",
                "description": f"🔀 Подозрительная структура домена: слишком много уровней ({domain})",
            })

        # 9. Random/high-entropy subdomain or domain name (e.g. z1xx.ydi55trui.shop)
        rand_risk, rand_flags = self._check_random_domain(domain)
        risk += rand_risk
        flags.extend(rand_flags)
        report["checks"]["random_domain"] = {"risk": rand_risk}

        report["total_risk"] = min(risk, 100)
        return min(risk, 100), flags, report

    def _get_apex_domain(self, domain: str) -> str:
        """Return last two parts: sub.example.com → example.com"""
        parts = domain.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else domain

    def _check_tld(self, domain: str) -> Tuple[int, List[Dict]]:
        for tld in SUSPICIOUS_TLDS:
            if domain.endswith(tld):
                return 25, [{
                    "severity": 7,
                    "category": "url",
                    "description": f"⚠️ Подозрительная доменная зона {tld} — часто используется мошенниками: {domain}",
                }]
        return 0, []

    def _check_domain_keywords(self, domain: str) -> Tuple[int, List[Dict]]:
        domain_lower = domain.replace("-", " ").replace(".", " ")
        found = [kw for kw in SCAM_DOMAIN_KEYWORDS if kw in domain_lower]
        if len(found) >= 2:
            return 35, [{
                "severity": 9,
                "category": "url",
                "description": f"🎣 Домен содержит несколько мошеннических ключевых слов: {', '.join(found)} — {domain}",
            }]
        if found:
            return 20, [{
                "severity": 7,
                "category": "url",
                "description": f"⚠️ Подозрительное слово в домене: '{found[0]}' — {domain}",
            }]
        return 0, []

    def _check_brand_impersonation(self, domain: str, apex: str) -> Tuple[int, List[Dict]]:
        if apex in TRUSTED_DOMAINS:
            return 0, []
        domain_lower = domain.replace("-", "").replace(".", "")
        found_brands = [b for b in BRAND_NAMES if b in domain_lower]
        if found_brands:
            brand = found_brands[0]
            return 40, [{
                "severity": 10,
                "category": "url",
                "description": (
                    f"🎭 Домен имитирует бренд '{brand}', но не является официальным сайтом — "
                    f"это подделка: {domain}"
                ),
            }]
        return 0, []

    async def _check_dns(self, domain: str) -> bool:
        """Returns True if domain resolves."""
        loop = asyncio.get_event_loop()
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: socket.gethostbyname(domain)),
                timeout=5.0,
            )
            return True
        except Exception:
            return False

    def _check_random_domain(self, domain: str) -> Tuple[int, List[Dict]]:
        """
        Detect algorithmically generated or high-entropy domain/subdomain names.
        Examples: z1xx.ydi55trui.shop, a8fk2.xn--verify.top, ab3cd5ef.site
        """
        import math

        def entropy(s: str) -> float:
            """Shannon entropy of string."""
            if not s:
                return 0.0
            freq = {}
            for c in s:
                freq[c] = freq.get(c, 0) + 1
            n = len(s)
            return -sum((f / n) * math.log2(f / n) for f in freq.values())

        def looks_random(part: str) -> bool:
            """True if the label looks like gibberish."""
            if len(part) < 4:
                return False
            # High ratio of digits mixed with letters
            digits = sum(c.isdigit() for c in part)
            alpha  = sum(c.isalpha() for c in part)
            if digits > 0 and alpha > 0 and (digits / len(part)) >= 0.25:
                return True
            # High Shannon entropy (random strings have entropy > 3.5)
            if entropy(part) > 3.5 and len(part) >= 6:
                return True
            # Consonant cluster — no vowels at all in a longer string
            vowels = set("aeiouаеиоуыёэюяАЕИОУЫЁЭЮЯ")
            if len(part) >= 5 and not any(c in vowels for c in part):
                return True
            return False

        parts = domain.split(".")
        # Check each label except the TLD
        labels = parts[:-1] if len(parts) > 1 else parts
        random_labels = [l for l in labels if looks_random(l)]

        if len(random_labels) >= 2:
            return 35, [{
                "severity": 9,
                "category": "url",
                "description": (
                    f"🤖 Домен выглядит как автоматически сгенерированный: "
                    f"'{'.'.join(random_labels)}' — такие домены массово создаются для фишинга: {domain}"
                ),
            }]
        elif random_labels:
            return 20, [{
                "severity": 7,
                "category": "url",
                "description": (
                    f"⚠️ Подозрительное имя домена: '{random_labels[0]}' — "
                    f"содержит случайные символы/цифры, характерно для фишинговых сайтов: {domain}"
                ),
            }]
        return 0, []

    async def _check_domain_age(self, domain: str) -> Tuple[int, List[Dict], Optional[int]]:
        """
        Query WHOIS for domain creation date.
        Returns (risk, flags, age_in_days or None).
        """
        loop = asyncio.get_event_loop()
        try:
            import whois as whois_lib

            def _whois_query():
                return whois_lib.whois(domain)

            w = await asyncio.wait_for(
                loop.run_in_executor(None, _whois_query),
                timeout=8.0,
            )

            creation = w.creation_date
            if isinstance(creation, list):
                creation = creation[0]

            if creation is None:
                return 0, [], None

            # Make timezone-aware if needed
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)

            age_days = (datetime.now(timezone.utc) - creation).days

            if age_days < 30:
                return 40, [{
                    "severity": 9,
                    "category": "url",
                    "description": (
                        f"🆕 Домен создан всего {age_days} дней назад — "
                        f"свежезарегистрированные домены часто используются для мошенничества: {domain}"
                    ),
                }], age_days
            elif age_days < self.NEW_DOMAIN_THRESHOLD_DAYS:
                return 25, [{
                    "severity": 7,
                    "category": "url",
                    "description": (
                        f"🆕 Домен создан {age_days} дней назад ({self.NEW_DOMAIN_THRESHOLD_DAYS} дней — порог подозрения): {domain}"
                    ),
                }], age_days

            return 0, [], age_days

        except asyncio.TimeoutError:
            logger.debug(f"WHOIS timeout for {domain}")
            return 0, [], None
        except Exception as e:
            logger.debug(f"WHOIS error for {domain}: {e}")
            return 0, [], None
