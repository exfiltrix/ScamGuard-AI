from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Analysis(Base):
    """Database model for analysis records"""
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    url = Column(String(500), nullable=False)

    # Listing data
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(10), nullable=True)
    location = Column(String(200), nullable=True)

    # Analysis results
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    red_flags = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    details = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    feedback = Column(String(500), nullable=True)
    is_scam = Column(Integer, nullable=True)  # 1=scam, 0=legitimate, null=unknown


class MessageAnalysis(Base):
    """Database model for message analysis records"""
    __tablename__ = "message_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    
    # Message data
    message_text = Column(Text, nullable=False)
    is_forwarded = Column(Boolean, default=False)
    forward_from = Column(String(200), nullable=True)
    photo_count = Column(Integer, default=0)
    
    # Analysis results
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    red_flags = Column(JSON, nullable=False)
    recommendations = Column(JSON, nullable=False)
    details = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    feedback = Column(String(500), nullable=True)
    is_scam = Column(Integer, nullable=True)


class User(Base):
    """Database model for users"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=True)
    username = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), onupdate=func.now())
    analysis_count = Column(Integer, default=0)
