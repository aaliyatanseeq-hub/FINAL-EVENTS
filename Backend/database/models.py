"""
SQLAlchemy Models for PostgreSQL - CLEAN VERSION
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    searches = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    actions = relationship("UserAction", back_populates="user", cascade="all, delete-orphan")

class SearchHistory(Base):
    """Track search queries"""
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    search_type = Column(String(50), nullable=False)
    query = Column(JSON, nullable=False)
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="searches")

class Event(Base):
    """Store discovered events"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(500), nullable=False, index=True)
    exact_date = Column(String(200))
    exact_venue = Column(String(500))
    location = Column(String(200))
    category = Column(String(100))
    confidence_score = Column(Float, default=0.0)
    source_url = Column(String(1000))
    posted_by = Column(String(200))
    hype_score = Column(Float, default=0.0)
    source = Column(String(50), default='unknown', index=True)
    source_data = Column(JSON)
    # Quality filtering fields
    is_real_event = Column(Boolean, default=True, index=True)  # False = noise/utility
    quality_score = Column(Float, default=1.0, index=True)  # 0.0 to 1.0
    clean_category = Column(String(100))  # Cleaned/inferred category
    rejection_reasons = Column(JSON)  # List of rejection reasons if filtered
    quality_confidence = Column(Float, default=1.0)  # Confidence in quality assessment
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Attendee(Base):
    """Store discovered attendees"""
    __tablename__ = "attendees"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    display_name = Column(String(200))
    bio = Column(Text)
    location = Column(String(200))
    followers_count = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    engagement_type = Column(String(50))
    post_content = Column(Text)
    post_date = Column(String(100))
    post_link = Column(String(500))
    relevance_score = Column(Float, default=0.0)
    event_name = Column(String(500), index=True)
    source = Column(String(50), default='unknown', index=True)
    source_data = Column(JSON)
    user_id = Column(String(100), nullable=True, index=True)  # Twitter user ID for DMs
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserAction(Base):
    """Track user actions"""
    __tablename__ = "user_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50), nullable=False)  # retweet, like, comment, quote
    target_username = Column(String(100))
    target_tweet_id = Column(String(100))
    status = Column(String(50))  # success, failed
    message = Column(Text)
    additional_data = Column(JSON)  # Changed from 'metadata' to 'additional_data'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="actions")

class Cache(Base):
    """Cache API responses"""
    __tablename__ = "cache"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, index=True, nullable=False)
    cache_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

class Analytics(Base):
    """Platform analytics"""
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    event_searches = Column(Integer, default=0)
    attendee_searches = Column(Integer, default=0)
    twitter_actions = Column(Integer, default=0)
    api_calls_saved = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
