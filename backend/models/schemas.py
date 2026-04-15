from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class RiskLevel(str, Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisRequest(BaseModel):
    """Request model for listing analysis"""
    url: HttpUrl
    user_id: Optional[int] = None


class RedFlag(BaseModel):
    """Red flag detected in listing"""
    category: str
    description: str
    severity: int = Field(..., ge=0, le=10)


class AnalysisResult(BaseModel):
    """Result of listing analysis"""
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    red_flags: List[RedFlag]
    recommendations: List[str]
    details: Dict[str, Any]
    analyzed_at: Optional[datetime] = None
    
    def __init__(self, **data):
        if 'analyzed_at' not in data:
            data['analyzed_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class ListingData(BaseModel):
    """Parsed listing data"""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    location: Optional[str] = None
    images: List[Any] = []  # Can be URLs (str) or image bytes
    contact_info: Dict[str, str] = {}
    metadata: Dict[str, Any] = {}
    raw_html: Optional[str] = None


class AnalysisHistory(BaseModel):
    """Historical analysis record"""
    id: int
    user_id: Optional[int]
    url: str
    risk_score: int
    risk_level: RiskLevel
    created_at: datetime
    feedback: Optional[str] = None


class PhotoData(BaseModel):
    """Photo data for message analysis"""
    index: int
    data: str  # Base64 encoded image


class MessageAnalysisRequest(BaseModel):
    """Request model for message analysis"""
    text: str
    user_id: Optional[int] = None
    is_forwarded: bool = False
    forward_info: Optional[Dict[str, Any]] = None
    photos: Optional[List[PhotoData]] = None


class QuickCheckRequest(BaseModel):
    """Request model for quick check (rules only, no AI)"""
    text: str
    user_id: Optional[int] = None
    is_forwarded: bool = False
    has_photos: bool = False
    has_file: bool = False
    file_count: int = 0


class DeepAnalysisRequest(BaseModel):
    """Request model for deep analysis (full AI pipeline)"""
    text: str
    user_id: Optional[int] = None
    is_forwarded: bool = False
    forward_info: Optional[Dict[str, Any]] = None
    photos: Optional[List[PhotoData]] = None
    message_id: Optional[int] = None  # ID from quick check to link results
