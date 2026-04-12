"""
Utility functions for ScamGuard AI
"""
import re
from typing import Optional


def validate_url(url: str) -> bool:
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def format_risk_score(score: int) -> str:
    """Format risk score for display"""
    if score < 30:
        return f"🟢 {score}/100 (Низкий риск)"
    elif score < 60:
        return f"🟡 {score}/100 (Средний риск)"
    else:
        return f"🔴 {score}/100 (Высокий риск)"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL"""
    pattern = r'https?://([^/]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None
