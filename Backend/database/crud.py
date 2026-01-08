"""
CRUD operations - COMPLETE VERSION
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import hashlib
from . import models, schemas

# Event CRUD operations
def create_event(db: Session, event_data: Dict[str, Any]):
    """Create event in database with proper error handling"""
    try:
        # Get valid columns from database schema
        valid_fields = {col.name for col in models.Event.__table__.columns}
        
        # Filter out fields that don't exist in Event model
        # Also remove quality fields if columns don't exist
        quality_fields = {'is_real_event', 'quality_score', 'clean_category', 'rejection_reasons', 'quality_confidence'}
        filtered_data = {}
        
        # FIRST: Remove all quality fields that don't exist in database
        # THEN: Only include fields that exist in the database schema
        for key, value in event_data.items():
            # Skip quality fields if the column doesn't exist in database
            if key in quality_fields:
                if key not in valid_fields:
                    continue  # Skip quality fields if column doesn't exist
                # If quality field exists in DB, include it
                filtered_data[key] = value
            elif key in valid_fields:
                # Only include fields that exist in the database schema
                filtered_data[key] = value
            # If key is not in valid_fields and not a quality field, skip it
        
        # Check if event already exists
        existing = db.query(models.Event).filter(
            models.Event.event_name == filtered_data.get('event_name'),
            models.Event.exact_date == filtered_data.get('exact_date'),
            models.Event.location == filtered_data.get('location')
        ).first()
        
        if existing:
            # Update existing event
            for key, value in filtered_data.items():
                if hasattr(existing, key) and key in valid_fields:
                    try:
                        setattr(existing, key, value)
                    except Exception:
                        # Skip fields that can't be set
                        pass
            try:
                setattr(existing, 'updated_at', datetime.utcnow())
            except:
                pass
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new event - ensure we only use fields that exist
            # Double-check: remove any quality fields that might have slipped through
            final_data = {}
            for key, value in filtered_data.items():
                if key in valid_fields:
                    final_data[key] = value
            
            db_event = models.Event(**final_data)
            db.add(db_event)
            db.commit()
            db.refresh(db_event)
            return db_event
    except Exception as e:
        db.rollback()
        # If error is due to missing column, remove problematic fields and retry
        if 'does not exist' in str(e) or 'UndefinedColumn' in str(e):
            # Remove all quality fields and retry
            safe_fields = {col.name for col in models.Event.__table__.columns}
            filtered_data = {k: v for k, v in event_data.items() 
                           if k in safe_fields and k not in quality_fields}
            try:
                db_event = models.Event(**filtered_data)
                db.add(db_event)
                db.commit()
                db.refresh(db_event)
                return db_event
            except Exception as e2:
                db.rollback()
                # Last resort: only use core fields
                core_fields = {'event_name', 'exact_date', 'exact_venue', 'location', 'category', 
                              'confidence_score', 'source_url', 'posted_by', 'hype_score', 'source', 'source_data'}
                minimal_data = {k: v for k, v in event_data.items() if k in core_fields and k in safe_fields}
                try:
                    db_event = models.Event(**minimal_data)
                    db.add(db_event)
                    db.commit()
                    db.refresh(db_event)
                    return db_event
                except:
                    db.rollback()
                    raise
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
    categories: Optional[List[str]] = None,
    limit: int = 100
):
    """Get events from database by location and date range"""
    try:
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
            
            # Try to filter by is_real_event if column exists, otherwise skip
            try:
                query = query.filter(models.Event.is_real_event == True)
            except Exception:
                # Column doesn't exist, skip this filter
                pass
        
        return query.order_by(desc(models.Event.hype_score)).limit(limit).all()
    except Exception as e:
        # If query fails due to missing columns, return empty list
        print(f"⚠️ Database query error (may be missing columns): {e}")
        return []

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
            setattr(existing, 'updated_at', datetime.utcnow())
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
        setattr(analytics, 'event_searches', 0)
    if analytics.attendee_searches is None:
        setattr(analytics, 'attendee_searches', 0)
    if analytics.twitter_actions is None:
        setattr(analytics, 'twitter_actions', 0)
    if analytics.api_calls_saved is None:
        setattr(analytics, 'api_calls_saved', 0)
    if analytics.active_users is None:
        setattr(analytics, 'active_users', 0)
    
    if analytics_type == 'event_search':
        current_value = getattr(analytics, 'event_searches', 0) or 0
        setattr(analytics, 'event_searches', current_value + 1)
    elif analytics_type == 'attendee_search':
        current_value = getattr(analytics, 'attendee_searches', 0) or 0
        setattr(analytics, 'attendee_searches', current_value + 1)
    elif analytics_type == 'twitter_action':
        current_value = getattr(analytics, 'twitter_actions', 0) or 0
        setattr(analytics, 'twitter_actions', current_value + 1)
    elif analytics_type == 'api_saved':
        current_value = getattr(analytics, 'api_calls_saved', 0) or 0
        setattr(analytics, 'api_calls_saved', current_value + 1)
    
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

def set_cache(db: Session, cache_key: str, data: Dict[str, Any], ttl_minutes: int = 129600):
    """Set cache with time-to-live"""
    expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
    
    # Check if key exists
    existing = db.query(models.Cache).filter(
        models.Cache.cache_key == cache_key
    ).first()
    
    if existing:
        setattr(existing, 'cache_data', data)
        setattr(existing, 'expires_at', expires_at)
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

def get_cached_events_by_date_range(
    db: Session,
    location: str,
    start_date: str,
    end_date: str,
    categories: Optional[List[str]] = None
) -> List[models.Event]:
    """
    Get cached events from database that overlap with the requested date range.
    This helps avoid excessive API calls by reusing previously fetched events.
    """
    try:
        from datetime import datetime as dt
        
        # Parse dates
        start_dt = dt.strptime(start_date, '%Y-%m-%d')
        end_dt = dt.strptime(end_date, '%Y-%m-%d')
        
        # Query events in database for this location
        # Use flexible matching: case-insensitive, no hardcoding
        location_normalized = location.strip().lower()
        query = db.query(models.Event).filter(
            func.lower(models.Event.location).contains(location_normalized)
        )
        
        # Filter by categories if provided
        if categories and len(categories) > 0:
            query = query.filter(models.Event.category.in_(categories))
        
        # Try to filter by is_real_event if column exists (gracefully handle missing column)
        try:
            # Check if column exists before filtering
            if 'is_real_event' in {col.name for col in models.Event.__table__.columns}:
                query = query.filter(models.Event.is_real_event == True)
        except Exception:
            # Column doesn't exist, skip this filter
            pass
        
        # Get all events for this location (we'll filter by date in Python)
        # Increase limit to find more events (especially for larger requests)
        # Also order by created_at DESC to get most recently stored events first
        all_events = query.order_by(desc(models.Event.created_at), desc(models.Event.hype_score)).limit(2000).all()
        
        print(f"📊 Cache: Found {len(all_events)} total events in DB for location '{location}'")
        
        # Filter events that fall within or overlap the requested date range
        cached_events = []
        parse_errors = 0
        date_mismatches = 0
        no_date_events = 0
        
        for event in all_events:
            event_date_str = getattr(event, 'exact_date', None)
            if not event_date_str:
                # Include events without dates if they're recent (within last 7 days)
                # This helps catch events that might have been stored but have date parsing issues
                try:
                    created_at = getattr(event, 'created_at', None)
                    if created_at:
                        days_old = (dt.now() - created_at).days
                        if days_old <= 7:  # Include recent events even without dates
                            cached_events.append(event)
                            no_date_events += 1
                except:
                    pass
                continue
            
            try:
                # Parse event date (format: MM-DD-YY HH:MM AM/PM or similar)
                # Try multiple date formats
                event_date = None
                date_str = str(event_date_str).strip()
                
                # Try parsing common formats (order matters - most common first)
                date_formats = [
                    '%m-%d-%y %I:%M %p',  # 12-17-25 08:00 PM
                    '%m-%d-%y',           # 12-17-25
                    '%Y-%m-%d',           # 2025-12-17
                    '%m/%d/%y',           # 12/17/25
                    '%Y-%m-%d %H:%M:%S',  # 2025-12-17 20:00:00
                    '%Y-%m-%d %H:%M:%S.%f',  # 2025-12-17 20:00:00.000000
                    '%m-%d-%Y',           # 12-17-2025
                    '%d-%m-%y',           # 17-12-25 (alternative)
                    '%d/%m/%y',           # 17/12/25 (alternative)
                    '%Y-%m-%dT%H:%M:%S',  # ISO format
                    '%Y-%m-%dT%H:%M:%S.%f',  # ISO with microseconds
                    '%Y-%m-%dT%H:%M:%S%z',  # ISO with timezone
                ]
                
                for fmt in date_formats:
                    try:
                        # Extract just the date part (before any time)
                        date_part = date_str.split()[0] if ' ' in date_str else date_str
                        # Remove timezone info if present
                        if '+' in date_part or date_part.endswith('Z'):
                            date_part = date_part.split('+')[0].split('Z')[0]
                        event_date = dt.strptime(date_part, fmt)
                        break
                    except:
                        continue
                
                if event_date:
                    # Check if event date falls within requested range
                    event_date_only = event_date.date()
                    if start_dt.date() <= event_date_only <= end_dt.date():
                        cached_events.append(event)
                    else:
                        date_mismatches += 1
                else:
                    # If we can't parse the date, but the event was created recently (within 7 days),
                    # include it anyway (might be from the same search session)
                    try:
                        created_at = getattr(event, 'created_at', None)
                        if created_at:
                            days_old = (dt.now() - created_at).days
                            if days_old <= 7:
                                cached_events.append(event)
                                parse_errors += 1
                            else:
                                parse_errors += 1
                    except:
                        parse_errors += 1
            except Exception as e:
                # For events with unparseable dates, include if recent (within 7 days)
                try:
                    created_at = getattr(event, 'created_at', None)
                    if created_at:
                        days_old = (dt.now() - created_at).days
                        if days_old <= 7:
                            cached_events.append(event)
                            parse_errors += 1
                        else:
                            parse_errors += 1
                    else:
                        parse_errors += 1
                except:
                    parse_errors += 1
                continue
        
        if parse_errors > 0:
            print(f"⚠️ Cache: Could not parse dates for {parse_errors} events (included recent ones)")
        if no_date_events > 0:
            print(f"ℹ️ Cache: Included {no_date_events} recent events without dates")
        if date_mismatches > 0:
            print(f"ℹ️ Cache: {date_mismatches} events found but outside date range")
        
        print(f"✅ Cache: {len(cached_events)} events match date range {start_date} to {end_date}")
        return cached_events
    except Exception as e:
        print(f"⚠️ Error getting cached events: {e}")
        return []
