import re
from typing import Optional, List, Dict
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from backend.models.schemas import ListingData
from loguru import logger


class ListingParser:
    """Parser for rental listing URLs"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def parse(self, url: str) -> ListingData:
        """Parse listing from URL"""
        parsed_url = urlparse(url)
        
        # Determine source and use appropriate parser
        if 't.me' in parsed_url.netloc:
            return await self._parse_telegram(url)
        else:
            return await self._parse_generic(url)
    
    async def _parse_telegram(self, url: str) -> ListingData:
        """Parse Telegram channel post"""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract text content
            text_element = soup.find('div', class_='tgme_widget_message_text')
            description = text_element.get_text(strip=True) if text_element else ""
            
            # Extract images
            images = []
            for img in soup.find_all('a', class_='tgme_widget_message_photo_wrap'):
                style = img.get('style', '')
                match = re.search(r"url\('([^']+)'\)", style)
                if match:
                    images.append(match.group(1))
            
            # Extract price (basic pattern matching)
            price, currency = self._extract_price(description)
            
            # Extract location
            location = self._extract_location(description)
            
            # Extract contact info
            contact_info = self._extract_contacts(description)
            
            return ListingData(
                url=url,
                title=self._extract_title(description),
                description=description,
                price=price,
                currency=currency,
                location=location,
                images=images,
                contact_info=contact_info,
                metadata={'source': 'telegram'},
                raw_html=response.text[:5000]  # Limit size
            )
            
        except Exception as e:
            logger.error(f"Error parsing Telegram URL {url}: {e}")
            return ListingData(
                url=url,
                description="",
                metadata={'error': str(e), 'source': 'telegram'}
            )
    
    async def _parse_generic(self, url: str) -> ListingData:
        """Parse generic website listing"""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Generic extraction
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ""
            
            # Try to find main content
            description = ""
            for tag in soup.find_all(['p', 'div'], limit=20):
                text = tag.get_text(strip=True)
                if len(text) > 50:
                    description += text + " "
            
            # Extract images
            images = []
            for img in soup.find_all('img', limit=10):
                src = img.get('src')
                if src and src.startswith('http'):
                    images.append(src)
            
            price, currency = self._extract_price(description)
            location = self._extract_location(description)
            contact_info = self._extract_contacts(description)
            
            return ListingData(
                url=url,
                title=title_text[:500],
                description=description[:2000],
                price=price,
                currency=currency,
                location=location,
                images=images,
                contact_info=contact_info,
                metadata={'source': 'generic'},
                raw_html=response.text[:5000]
            )
            
        except Exception as e:
            logger.error(f"Error parsing generic URL {url}: {e}")
            return ListingData(
                url=url,
                description="",
                metadata={'error': str(e), 'source': 'generic'}
            )
    
    def _extract_price(self, text: str) -> tuple[Optional[float], Optional[str]]:
        """Extract price from text"""
        patterns = [
            r'(\d+(?:[\s,]\d{3})*(?:\.\d{2})?)\s*(сум|sum|usd|USD|\$|€)',
            r'([\$€])\s*(\d+(?:[\s,]\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 2:
                        if match.group(1).replace(',', '').replace(' ', '').isdigit():
                            price = float(match.group(1).replace(',', '').replace(' ', ''))
                            currency = match.group(2).upper()
                        else:
                            price = float(match.group(2).replace(',', '').replace(' ', ''))
                            currency = match.group(1).upper()
                        return price, currency
                except ValueError:
                    continue
        
        return None, None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        patterns = [
            r'(?:г\.|город|city)[\s:]*([А-Яа-яA-Za-z\s-]+)',
            r'(?:район|district)[\s:]*([А-Яа-яA-Za-z\s-]+)',
            r'(Ташкент|Самарканд|Бухара|Андижан|Наманган|Фергана)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_contacts(self, text: str) -> Dict[str, str]:
        """Extract contact information"""
        contacts = {}
        
        # Phone numbers
        phone_pattern = r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contacts['phones'] = ', '.join(phones[:3])
        
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contacts['email'] = emails[0]
        
        # Telegram username
        telegram_pattern = r'@([A-Za-z0-9_]{5,32})'
        telegram_users = re.findall(telegram_pattern, text)
        if telegram_users:
            contacts['telegram'] = ', '.join(telegram_users[:3])
        
        return contacts
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract title from description"""
        lines = text.split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 10 and len(first_line) < 200:
                return first_line
        
        return text[:100] if text else None
