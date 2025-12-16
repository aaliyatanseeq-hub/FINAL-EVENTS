"""
Pydantic schemas for data validation - SIMPLIFIED VERSION
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas - using str instead of EmailStr
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# Search History schemas
class SearchHistoryBase(BaseModel):
    search_type: str
    query: Dict[str, Any]
    results_count: int = 0

class SearchHistoryCreate(SearchHistoryBase):
    user_id: Optional[int] = None

class SearchHistory(SearchHistoryBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# Event schemas
class EventBase(BaseModel):
    event_name: str
    exact_date: Optional[str]
    exact_venue: Optional[str]
    location: str
    category: str
    confidence_score: float = 0.0
    source_url: Optional[str]
    posted_by: Optional[str]
    hype_score: float = 0.0
    source: str = 'unknown'

class EventCreate(EventBase):
    source_data: Optional[Dict[str, Any]] = None

class Event(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# Attendee schemas
class AttendeeBase(BaseModel):
    username: str
    display_name: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    followers_count: int = 0
    verified: bool = False
    confidence_score: float = 0.0
    engagement_type: str
    post_content: str
    post_date: str
    post_link: str
    relevance_score: float = 0.0
    event_name: str
    source: str = 'unknown'
    user_id: Optional[str] = None  # Twitter user ID for DMs

class AttendeeCreate(AttendeeBase):
    source_data: Optional[Dict[str, Any]] = None

class Attendee(AttendeeBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# User Action schemas
class UserActionBase(BaseModel):
    action_type: str
    target_username: str
    target_tweet_id: str
    status: str
    message: Optional[str]
    additional_data: Optional[Dict[str, Any]] = None  # Changed from metadata

class UserActionCreate(UserActionBase):
    user_id: Optional[int] = None

class UserAction(UserActionBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# Analytics schemas
class AnalyticsBase(BaseModel):
    event_searches: int = 0
    attendee_searches: int = 0
    twitter_actions: int = 0
    api_calls_saved: int = 0
    active_users: int = 0

class Analytics(AnalyticsBase):
    id: int
    date: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)

# Cache schemas
class CacheBase(BaseModel):
    cache_key: str
    cache_data: Dict[str, Any]
    expires_at: datetime

class Cache(CacheBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
