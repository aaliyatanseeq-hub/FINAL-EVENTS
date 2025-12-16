"""
CRUD operations - COMPLETE VERSION
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import hashlib
from . import models, schemas

# Event CRUD operations
def create_event(db: Session, event_data: Dict[str, Any]):
    """Create event in database with proper error handling"""
    try:
        # Filter out fields that don't exist in Event model
        valid_fields = {col.name for col in models.Event.__table__.columns}
        filtered_data = {k: v for k, v in event_data.items() if k in valid_fields}
        
        # Check if event already exists
        existing = db.query(models.Event).filter(
            models.Event.event_name == filtered_data.get('event_name'),
            models.Event.exact_date == filtered_data.get('exact_date'),
            models.Event.location == filtered_data.get('location')
        ).first()
        
        if existing:
            # Update existing event
            for key, value in filtered_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new event
            db_event = models.Event(**filtered_data)
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            return db_event
    except Exception as e:
        db.rollback()
        raise

def get_events_by_location(db: Session, location: str, limit: int = 100):
    """Get events by location"""
    return db.query(models.Event).filter(
        models.Event.location.ilike(f"%{location}%")
    ).limit(limit).all()

def get_events_by_location_date(
    db: Session, 
    location: str, 
    start_date: str, 
    end_date: str,
    categories: List[str] = None,
    limit: int = 100
):
    """Get events from database by location and date range"""
    query = db.query(models.Event).filter(
        models.Event.location.ilike(f"%{location}%")
    )
    
    # Filter by date range if possible (simplified - actual date parsing would be more complex)
    if start_date and end_date:
        # Try to filter by exact_date containing the date
        query = query.filter(
            models.Event.exact_date.between(start_date, end_date)
        )
    
    if categories:
        query = query.filter(models.Event.category.in_(categories))
    
    return query.order_by(desc(models.Event.hype_score)).limit(limit).all()

# Attendee CRUD operations
def create_attendee(db: Session, attendee_data: Dict[str, Any]):
    """Create attendee in database with proper error handling"""
    try:
        # Filter out fields that don't exist in Attendee model
        valid_fields = {col.name for col in models.Attendee.__table__.columns}
        filtered_data = {k: v for k, v in attendee_data.items() if k in valid_fields}
        
        # Check if attendee already exists for this event
        existing = db.query(models.Attendee).filter(
            models.Attendee.username == filtered_data.get('username'),
            models.Attendee.event_name == filtered_data.get('event_name')
        ).first()
        
        if existing:
            # Update existing attendee
            for key, value in filtered_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new attendee
            db_attendee = models.Attendee(**filtered_data)
            db.add(db_attendee)
            db.commit()
            db.refresh(db_attendee)
            return db_attendee
    except Exception as e:
        db.rollback()
        raise

def get_attendees_by_event(db: Session, event_name: str, limit: int = 100):
    """Get attendees by event name"""
    return db.query(models.Attendee).filter(
        models.Attendee.event_name.ilike(f"%{event_name}%")
    ).order_by(
        desc(models.Attendee.relevance_score),
        desc(models.Attendee.followers_count)
    ).limit(limit).all()

# User Action CRUD operations
def create_user_action(db: Session, action_data: schemas.UserActionCreate):
    """Create user action in database"""
    # Convert Pydantic model to dict
    action_dict = action_data.model_dump()  # Pydantic v2 uses model_dump() instead of dict()
    
    db_action = models.UserAction(**action_dict)
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action

# Analytics CRUD operations
def update_analytics(db: Session, analytics_type: str):
    """Update analytics for today"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    analytics = db.query(models.Analytics).filter(
        func.date(models.Analytics.date) == today
    ).first()
    
    if not analytics:
        analytics = models.Analytics(
            date=today_start,
            event_searches=0,
            attendee_searches=0,
            twitter_actions=0,
            api_calls_saved=0,
            active_users=0
        )
        db.add(analytics)
        db.flush()  # Flush to get the ID
    
    # Initialize fields if None (safety check)
    if analytics.event_searches is None:
        analytics.event_searches = 0
    if analytics.attendee_searches is None:
        analytics.attendee_searches = 0
    if analytics.twitter_actions is None:
        analytics.twitter_actions = 0
    if analytics.api_calls_saved is None:
        analytics.api_calls_saved = 0
    if analytics.active_users is None:
        analytics.active_users = 0
    
    if analytics_type == 'event_search':
        analytics.event_searches += 1
    elif analytics_type == 'attendee_search':
        analytics.attendee_searches += 1
    elif analytics_type == 'twitter_action':
        analytics.twitter_actions += 1
    elif analytics_type == 'api_saved':
        analytics.api_calls_saved += 1
    
    db.commit()
    return analytics

# Cache functions
def get_cache(db: Session, cache_key: str):
    """Get cached data if not expired"""
    cache_entry = db.query(models.Cache).filter(
        models.Cache.cache_key == cache_key,
        models.Cache.expires_at > datetime.utcnow()
    ).first()
    
    if cache_entry:
        return cache_entry.cache_data
    return None

def set_cache(db: Session, cache_key: str, data: Dict[str, Any], ttl_minutes: int = 60):
    """Set cache with time-to-live"""
    expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    
    # Check if key exists
    existing = db.query(models.Cache).filter(
        models.Cache.cache_key == cache_key
    ).first()
    
    if existing:
        existing.cache_data = data
        existing.expires_at = expires_at
    else:
        cache_entry = models.Cache(
            cache_key=cache_key,
            cache_data=data,
            expires_at=expires_at
        )
        db.add(cache_entry)
    
    db.commit()
    return True

def generate_cache_key(search_type: str, params: Dict[str, Any]) -> str:
    """Generate a unique cache key from search parameters"""
    params_str = json.dumps(params, sort_keys=True)
    key_string = f"{search_type}:{params_str}"
    return hashlib.md5(key_string.encode()).hexdigest()
