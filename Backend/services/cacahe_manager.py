"""
Enhanced Cache Manager with Redis + Postgres persistence
Integrated with existing event discovery flow
"""
import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
import asyncio
from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)
Base = declarative_base()

class EventCacheWindow(Base):
    __tablename__ = 'event_cache_windows'
    
    id = Column(String, primary_key=True)
    city = Column(String, nullable=False)
    category = Column(String)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    providers_covered = Column(JSON, default=list)
    event_count = Column(Integer, default=0)
    hit_count = Column(Integer, default=0)
    last_refreshed = Column(DateTime, default=datetime.utcnow)
    next_refresh_recommended = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

@dataclass
class DateRange:
    start_date: datetime
    end_date: datetime
    
    def contains(self, other: 'DateRange') -> bool:
        return self.start_date <= other.start_date and self.end_date >= other.end_date
    
    def overlaps(self, other: 'DateRange') -> bool:
        return not (self.end_date < other.start_date or self.start_date > other.end_date)

class CacheManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 db_url: str = "postgresql://user:pass@localhost/events_db"):
        # Redis for hot cache
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        
        # Postgres for persistent cache windows
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
    @contextmanager
    def db_session(self):
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    
    def build_cache_key(self, city: str, category: Optional[str], 
                       start_date: str, end_date: str) -> str:
        """Build consistent cache key (matches your event discovery parameters)"""
        category_part = category or 'all'
        # Normalize dates to YYYY-MM-DD format
        start_norm = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
        end_norm = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
        
        key = f"events:{city}:{category_part}:{start_norm}:{end_norm}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    async def get_cached_events(self, cache_key: str) -> Optional[List[Dict]]:
        """Get events from Redis cache"""
        try:
            cached = self.redis_client.get(f"events:{cache_key}")
            if cached:
                logger.info(f"Redis cache hit for key: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis cache error: {e}")
        return None
    
    def set_cached_events(self, cache_key: str, events: List[Dict], ttl: int = 3600):
        """Set events in Redis cache with TTL"""
        try:
            self.redis_client.setex(
                f"events:{cache_key}",
                ttl,
                json.dumps(events, default=str)
            )
            logger.info(f"Cached {len(events)} events with key: {cache_key}")
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def find_cache_windows(self, city: str, category: Optional[str],
                          start_date: str, end_date: str) -> List[Dict]:
        """Find overlapping cache windows in database"""
        with self.db_session() as session:
            # Convert string dates to datetime for comparison
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Query for overlapping windows
            windows = session.query(EventCacheWindow).filter(
                EventCacheWindow.city == city,
                EventCacheWindow.category == (category or EventCacheWindow.category),
                EventCacheWindow.end_date >= start_dt.date(),
                EventCacheWindow.start_date <= end_dt.date()
            ).all()
            
            return [
                {
                    'start_date': w.start_date,
                    'end_date': w.end_date,
                    'providers_covered': w.providers_covered,
                    'event_count': w.event_count,
                    'hit_count': w.hit_count,
                    'last_refreshed': w.last_refreshed
                }
                for w in windows
            ]
    
    def update_cache_window(self, city: str, category: Optional[str],
                           start_date: str, end_date: str, providers: List[str]):
        """Create or update cache window entry"""
        with self.db_session() as session:
            # Generate window ID
            window_id = f"{city}:{category or 'all'}:{start_date}:{end_date}"
            window_id_hash = hashlib.md5(window_id.encode()).hexdigest()[:32]
            
            # Check if window exists
            window = session.query(EventCacheWindow).filter_by(id=window_id_hash).first()
            
            if window:
                # Update existing window
                window.last_refreshed = datetime.utcnow()
                window.hit_count += 1
                # Merge providers
                existing_providers = set(window.providers_covered or [])
                existing_providers.update(providers)
                window.providers_covered = list(existing_providers)
            else:
                # Create new window
                window = EventCacheWindow(
                    id=window_id_hash,
                    city=city,
                    category=category,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
                    end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
                    providers_covered=providers,
                    last_refreshed=datetime.utcnow(),
                    next_refresh_recommended=datetime.utcnow() + timedelta(days=1)
                )
                session.add(window)