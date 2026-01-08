"""
ENHANCED Event Discovery Engine with Multi-Source Support
Sources: SerpAPI (Primary) → PredictHQ → Ticketmaster
Priority-based with caching and deduplication
"""
import requests
import os
import re
import json
import hashlib
from typing import List, Dict, Set, Optional, Any, Tuple
from difflib import SequenceMatcher

# Optional Redis import - gracefully handles missing dependency
# Redis is optional for caching; code works without it
try:
    import redis  # pyright: ignore[reportMissingImports]
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore[assignment]

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from dotenv import load_dotenv
import time
from functools import lru_cache
from urllib.parse import urlparse, urlunparse, quote

# Optional geocoding - gracefully handles missing dependency
try:
    from geopy.geocoders import Nominatim  # pyright: ignore[reportMissingImports]
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError  # pyright: ignore[reportMissingImports]
    GEOCODING_AVAILABLE = True
except ImportError:
    GEOCODING_AVAILABLE = False
    Nominatim = None  # type: ignore[assignment]

load_dotenv()

def validate_and_sanitize_url(url: Optional[str]) -> str:
    """
    Validate and sanitize URL to ensure it's properly formatted and safe.
    Returns empty string if URL is invalid.
    """
    if not url or not isinstance(url, str):
        return ''
    
    # Strip whitespace
    url = url.strip()
    
    # Remove any control characters or invalid characters
    url = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
    
    # If empty after cleaning, return empty
    if not url:
        return ''
    
    # If URL doesn't start with http:// or https://, try to add it
    if not url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if '.' in url and not url.startswith('//'):
            url = 'https://' + url
        else:
            return ''
    
    # Validate URL structure using urlparse
    try:
        parsed = urlparse(url)
        
        # Must have scheme and netloc (domain)
        if not parsed.scheme or not parsed.netloc:
            return ''
        
        # Reconstruct URL with proper encoding
        # Encode path, query, and fragment properly
        safe_path = quote(parsed.path, safe='/')
        safe_query = quote(parsed.query, safe='=&')
        safe_fragment = quote(parsed.fragment, safe='')
        
        # Reconstruct URL
        sanitized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            safe_path,
            parsed.params,
            safe_query if parsed.query else '',
            safe_fragment if parsed.fragment else ''
        ))
        
        # Final validation: URL should be reasonable length and contain valid characters
        if len(sanitized) > 2048:  # Max URL length
            return ''
        
        # Check for obviously malformed URLs
        if ' ' in sanitized or '\n' in sanitized or '\r' in sanitized:
            return ''
        
        return sanitized
        
    except Exception:
        # If parsing fails, return empty
        return ''

@dataclass
class ResearchEvent:
    event_name: str
    exact_date: str
    exact_venue: str
    location: str
    category: str
    confidence_score: float
    source_url: str
    posted_by: str
    hype_score: float
    source: str = "serpapi"  # serpapi, ticketmaster, predicthq
    start_datetime: Optional[datetime] = None
    ticket_url: Optional[str] = None
    price_range: Optional[str] = None
    event_hash: str = field(init=False)
    
    def __post_init__(self):
        """Generate unique hash for deduplication"""
        normalized = f"{self.event_name.lower()}_{self.exact_venue.lower()}_{self.exact_date[:10]}"
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', '_', normalized)
        self.event_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]

class SmartEventEngine:
    def __init__(self):
        # API Keys
        self.serp_api_key = os.getenv('SERP_API_KEY')
        # Support both TICKETMASTER_API_KEY and TICKETMASTER_KEY for compatibility
        self.ticketmaster_api_key = os.getenv('TICKETMASTER_API_KEY') or os.getenv('TICKETMASTER_KEY')
        # Support both PREDICTHQ_API_KEY and PREDICTHQ_TOKEN for compatibility
        self.predicthq_api_key = os.getenv('PREDICTHQ_API_KEY') or os.getenv('PREDICTHQ_TOKEN')
        
        # Redis for caching
        self.redis_client = None
        self._init_redis()
        
        # Source priorities and weights
        self.source_config = {
            'serpapi': {
                'priority': 1,
                'weight': 1.2,
                'enabled': bool(self.serp_api_key),
                'daily_limit': 100,
                'cache_ttl': 3600  # 1 hour
            },
            'predicthq': {
                'priority': 2,
                'weight': 1.1,
                'enabled': bool(self.predicthq_api_key),
                'daily_limit': 1000,
                'cache_ttl': 7200  # 2 hours
            },
            'ticketmaster': {
                'priority': 3,
                'weight': 1.0,
                'enabled': bool(self.ticketmaster_api_key),
                'daily_limit': 5000,  # Ticketmaster default quota (per API docs)
                'rate_limit_per_second': 5,  # Ticketmaster default rate limit (per API docs)
                'cache_ttl': 1800  # 30 minutes
            }
        }
        
        print("=" * 80)
        print("🚀 ENHANCED EVENT DISCOVERY ENGINE")
        print("=" * 80)
        print("📊 CONFIGURED SOURCES:")
        for source, config in self.source_config.items():
            status = "✅ ENABLED" if config['enabled'] else "❌ DISABLED"
            key_status = ""
            if source == 'serpapi':
                key_status = f" (Key: {'✅' if self.serp_api_key else '❌ Missing'})"
            elif source == 'predicthq':
                key_status = f" (Key: {'✅' if self.predicthq_api_key else '❌ Missing'})"
            elif source == 'ticketmaster':
                key_status = f" (Key: {'✅' if self.ticketmaster_api_key else '❌ Missing'})"
            print(f"   {source.upper():12} [Priority: {config['priority']}] {status}{key_status}")
        print("=" * 80)
    
    def _init_redis(self):
        """Initialize Redis connection for caching"""
        if not REDIS_AVAILABLE or redis is None:
            print("⚠️ Redis not available (module not installed). Caching disabled.")
            self.redis_client = None
            return
            
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            print("✅ Redis cache initialized")
            self.redis_client = client
        except Exception as e:
            print(f"⚠️ Redis initialization failed: {e}. Caching disabled.")
            self.redis_client = None
    
    @lru_cache(maxsize=1000)
    def _get_country_code_from_city(self, location_name: str) -> Optional[str]:
        """
        Production-grade geocoding: Get country code from ANY city or country name
        Uses multiple strategies and variations to ensure success for ANY location worldwide
        """
        if not GEOCODING_AVAILABLE or not location_name or Nominatim is None:
            return None
        
        location_name = location_name.strip()
        if not location_name:
            return None
        
        try:
            # Use Nominatim geocoder (OpenStreetMap - free, no API key)
            geolocator = Nominatim(user_agent="event_discovery_engine/1.0", timeout=15)
            
            # Strategy 1: Direct geocoding (works for both cities and countries)
            try:
                location = geolocator.geocode(location_name, exactly_one=True, timeout=15, language='en')
                if location:
                    address = location.raw.get('address', {})
                    country_code = address.get('country_code', '').upper()
                    if country_code and len(country_code) == 2:
                        return country_code
            except Exception:
                pass
            
            # Strategy 2: Try with "country" suffix (helps for country names)
            try:
                enhanced_query = f"{location_name}, country"
                location = geolocator.geocode(enhanced_query, exactly_one=True, timeout=15, language='en')
                if location:
                    address = location.raw.get('address', {})
                    country_code = address.get('country_code', '').upper()
                    if country_code and len(country_code) == 2:
                        return country_code
            except Exception:
                pass
            
            # Strategy 3: Try with country context (dynamic - works for ANY location)
            # Try common country patterns dynamically - no hardcoding
            # This helps when direct geocoding fails
            country_contexts = [
                f"{location_name}, India",
                f"{location_name}, USA",
                f"{location_name}, United States",
                f"{location_name}, UK",
                f"{location_name}, United Kingdom",
                f"{location_name}, Canada",
                f"{location_name}, Australia"
            ]
            
            # Try a few country contexts dynamically (limit to avoid too many API calls)
            for query in country_contexts[:3]:
                try:
                    location = geolocator.geocode(query, exactly_one=True, timeout=15, language='en')
                    if location:
                        address = location.raw.get('address', {})
                        country_code = address.get('country_code', '').upper()
                        if country_code and len(country_code) == 2:
                            return country_code
                except Exception:
                    continue
            
            return None
            
        except (GeocoderTimedOut, GeocoderServiceError):
            # Geocoding is optional - failures are expected and handled gracefully
            return None
        except Exception:
            # Silently fail - geocoding is optional
            return None
    
    def _parse_time_from_string(self, time_str: str) -> Optional[Tuple[int, int]]:
        """
        Parse time from various formats: "3 PM", "15:00", "evening", "morning", etc.
        Returns (hour, minute) tuple or None if parsing fails.
        """
        if not time_str or not isinstance(time_str, str):
            return None
        
        time_str = time_str.strip().lower()
        
        # Handle textual time descriptions
        textual_times = {
            'morning': (9, 0),
            'early morning': (7, 0),
            'late morning': (11, 0),
            'afternoon': (14, 0),
            'early afternoon': (13, 0),
            'late afternoon': (16, 0),
            'evening': (19, 0),
            'early evening': (17, 0),
            'late evening': (21, 0),
            'night': (20, 0),
            'late night': (22, 0),
            'midnight': (0, 0),
            'noon': (12, 0),
            'midday': (12, 0)
        }
        
        # Check for textual time first
        for key, (hour, minute) in textual_times.items():
            if key in time_str:
                return (hour, minute)
        
        # Handle time ranges (e.g., "8 – 11 PM" → use start time)
        if '–' in time_str or '-' in time_str or '—' in time_str:
            # Extract first time from range
            parts = re.split(r'[–—\-]', time_str, 1)
            if parts:
                time_str = parts[0].strip()
        
        # Remove common prefixes/suffixes
        time_str = re.sub(r'^(at|@|starts?|begins?|from)\s+', '', time_str, flags=re.IGNORECASE)
        time_str = time_str.strip()
        
        # Try 12-hour format with AM/PM (e.g., "3 PM", "8:30 PM", "11:45 AM")
        am_pm_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str, re.IGNORECASE)
        if am_pm_match:
            hour = int(am_pm_match.group(1))
            minute = int(am_pm_match.group(2)) if am_pm_match.group(2) else 0
            period = am_pm_match.group(3).lower()
            
            # Convert to 24-hour format
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            return (hour, minute)
        
        # Try 24-hour format (e.g., "15:00", "19:30", "20")
        hour_minute_match = re.search(r'(\d{1,2})(?::(\d{2}))?', time_str)
        if hour_minute_match:
            hour = int(hour_minute_match.group(1))
            minute = int(hour_minute_match.group(2)) if hour_minute_match.group(2) else 0
            
            # Validate hour range
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)
        
        return None
    
    def _format_date_time_display(self, date_obj: Optional[datetime], time_only: Optional[Tuple[int, int]] = None) -> str:
        """
        Format date/time display according to user requirements:
        - If date is there, show date
        - If time is there, show time
        - If both are there, show both
        - If neither is there, show "NA"
        """
        has_date = date_obj is not None
        has_time = False
        time_tuple = None
        
        # Check if date_obj has time component (but NOT default midnight)
        # Only consider it has time if it's not 00:00 (which might be a false fallback)
        if date_obj:
            # Check if time is explicitly set (not default midnight)
            # If hour is 0 and minute is 0, it might be a false fallback, so check time_only
            if (date_obj.hour != 0 or date_obj.minute != 0):
                has_time = True
                time_tuple = (date_obj.hour, date_obj.minute)
            elif time_only:
                # If datetime has midnight but we have separate time, use that
                has_time = True
                time_tuple = time_only
        elif time_only:
            has_time = True
            time_tuple = time_only
        
        # Format according to what we have
        if has_date and has_time:
            # Both date and time
            return date_obj.strftime('%m-%d-%y %I:%M %p')
        elif has_date:
            # Date only
            return date_obj.strftime('%m-%d-%y')
        elif has_time and time_tuple:
            # Time only
            hour, minute = time_tuple
            time_obj = datetime(2000, 1, 1, hour, minute).time()
            return time_obj.strftime('%I:%M %p')
        else:
            # Neither
            return "NA"
    
    def discover_events(self, location: str, start_date: str, end_date: str, 
                       categories: List[str], max_results: int) -> List[ResearchEvent]:
        """
        Discover events from multiple sources with caching and deduplication
        """
        try:
            print(f"\n🎯 EVENT DISCOVERY REQUEST")
            print(f"{'='*50}")
            print(f"📍 Location: {location}")
            print(f"📅 Date Range: {start_date} to {end_date}")
            print(f"🏷️  Categories: {categories}")
            print(f"🎯 Target: {max_results} events")
            print(f"{'='*50}")
            
            # Check cache first
            cache_key = self._build_cache_key(location, categories, start_date, end_date)
            cached_events = self._get_cached_events(cache_key)
            
            if cached_events and len(cached_events) >= max_results:
                print(f"✅ Cache hit! Returning {len(cached_events)} cached events")
                return cached_events[:max_results]
            
            # Parse dates - with enhanced validation
            start_dt = self._parse_user_date(start_date)
            end_dt = self._parse_user_date(end_date)
            
            if not start_dt or not end_dt:
                error_msg = f"Invalid date format. Start: '{start_date}', End: '{end_date}'. Please use YYYY-MM-DD format."
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # Validate date range is within 3 months (90 days)
            days_diff = (end_dt.date() - start_dt.date()).days
            if days_diff > 90:
                error_msg = f"Date range exceeds 3 months (90 days). Range: {days_diff} days. Maximum allowed: 90 days."
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            if days_diff < 0:
                error_msg = f"End date must be after start date. Start: {start_date}, End: {end_date}"
                print(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            print(f"✅ Date range validated: {days_diff} days (within 3-month limit)")
            
            all_events = []
            seen_hashes = set()
            source_counts = {}
            
            # DISTRIBUTED SOURCE STRATEGY: 50% SerpAPI, 25% PredictHQ, 25% Ticketmaster
            # This prevents exhausting any single API quota
            serpapi_target = int(max_results * 0.5)  # 50%
            predicthq_target = int(max_results * 0.25)  # 25%
            ticketmaster_target = int(max_results * 0.25)  # 25%
            
            # Adjust if rounding causes total to be less than max_results
            total_target = serpapi_target + predicthq_target + ticketmaster_target
            if total_target < max_results:
                serpapi_target += (max_results - total_target)  # Add remainder to SerpAPI
            
            print(f"\n📊 SOURCE DISTRIBUTION TARGETS:")
            print(f"   SerpAPI: {serpapi_target} events (50%)")
            print(f"   PredictHQ: {predicthq_target} events (25%)")
            print(f"   Ticketmaster: {ticketmaster_target} events (25%)")
            
            # Step 1: Fetch from SerpAPI (50% target)
            if self.serp_api_key:
                print(f"\n🔍 Querying SERPAPI (50% target: {serpapi_target} events)...")
                try:
                    source_start = time.time()
                    serpapi_events = self._fetch_serpapi_events(
                        location, categories, start_dt, end_dt, serpapi_target
                    )
                    source_time = time.time() - source_start
                    
                    # Add SerpAPI events - STRICT LIMIT to 50%
                    added = 0
                    for event in serpapi_events:
                        if added >= serpapi_target:  # Stop at target, don't exceed
                            break
                        if event.event_hash not in seen_hashes:
                            all_events.append(event)
                            seen_hashes.add(event.event_hash)
                            added += 1
                    
                    source_counts['serpapi'] = {'count': added, 'time': source_time}
                    print(f"   ✅ Found: {added} events | Unique: {added} | Time: {source_time:.2f}s")
                except Exception as e:
                    print(f"   ❌ SerpAPI Error: {str(e)[:100]}")
                    source_counts['serpapi'] = {'count': 0, 'time': 0}
            
            # Step 2: Fetch from PredictHQ (25% target)
            if self.predicthq_api_key:
                print(f"\n🔍 Querying PREDICTHQ (25% target: {predicthq_target} events)...")
                try:
                    source_start = time.time()
                    predicthq_events = self._fetch_predicthq_events(
                        location, categories, start_dt, end_dt, predicthq_target
                    )
                    source_time = time.time() - source_start
                    
                    added = 0
                    for event in predicthq_events:
                        if event.event_hash not in seen_hashes:
                            all_events.append(event)
                            seen_hashes.add(event.event_hash)
                            added += 1
                            if added >= predicthq_target:
                                break
                    
                    source_counts['predicthq'] = {'count': added, 'time': source_time}
                    print(f"   ✅ Found: {added} events | Unique: {added} | Time: {source_time:.2f}s")
                except Exception as e:
                    print(f"   ❌ PredictHQ Error: {str(e)[:100]}")
                    source_counts['predicthq'] = {'count': 0, 'time': 0}
            
            # Step 3: Fetch from Ticketmaster (25% target)
            if self.ticketmaster_api_key:
                print(f"\n🔍 Querying TICKETMASTER (25% target: {ticketmaster_target} events)...")
                try:
                    source_start = time.time()
                    ticketmaster_events = self._fetch_ticketmaster_events(
                        location, categories, start_dt, end_dt, ticketmaster_target
                    )
                    source_time = time.time() - source_start
                    
                    added = 0
                    for event in ticketmaster_events:
                        # Don't limit here - add all unique events to meet ratio requirements
                        if event.event_hash not in seen_hashes:
                            all_events.append(event)
                            seen_hashes.add(event.event_hash)
                            added += 1
                            # Only stop if we've exceeded target significantly (allow some buffer)
                            if added >= ticketmaster_target * 2:
                                break
                    
                    source_counts['ticketmaster'] = {'count': added, 'time': source_time}
                    print(f"   ✅ Found: {added} events | Unique: {added} | Time: {source_time:.2f}s")
                except Exception as e:
                    print(f"   ❌ Ticketmaster Error: {str(e)[:100]}")
                    source_counts['ticketmaster'] = {'count': 0, 'time': 0}
            
            # Legacy code path for other sources (if any)
            enabled_sources = sorted(
                [s for s in self.source_config.items() if s[1]['enabled'] and s[0] not in ['serpapi', 'predicthq', 'ticketmaster']],
                key=lambda x: x[1]['priority']
            )
            
            for source_name, config in enabled_sources:
                if len(all_events) >= max_results:
                    break
                print(f"\n🔍 Querying {source_name.upper()}...")
                
                try:
                    source_start = time.time()
                    events = []
                    
                    source_time = time.time() - source_start
                    
                    # Enhanced deduplication - check both hash and similarity
                    added = 0
                    for event in events:
                        is_duplicate = False
                        
                        # Fast check: exact hash match
                        if event.event_hash in seen_hashes:
                            is_duplicate = True
                        else:
                            # Check for semantic duplicates (similar names + same venue + same date)
                            for existing_event in all_events:
                                # Name similarity
                                name_sim = SequenceMatcher(None, 
                                    event.event_name.lower(), 
                                    existing_event.event_name.lower()).ratio()
                                
                                if name_sim > 0.85:  # 85% similar names
                                    # Check venue similarity
                                    venue_sim = SequenceMatcher(None,
                                        event.exact_venue.lower(),
                                        existing_event.exact_venue.lower()).ratio()
                                    
                                    if venue_sim > 0.8:  # 80% similar venues
                                        # Check date proximity (within 1 day)
                                        if event.start_datetime and existing_event.start_datetime:
                                            date_diff = abs((event.start_datetime - existing_event.start_datetime).days)
                                            if date_diff <= 1:
                                                is_duplicate = True
                                                break
                        
                        if not is_duplicate:
                            seen_hashes.add(event.event_hash)
                            all_events.append(event)
                            added += 1
                    
                    source_counts[source_name] = {
                        'total': len(events),
                        'unique': added,
                        'time': f"{source_time:.2f}s"
                    }
                    
                    print(f"   ✅ Found: {len(events)} events | Unique: {added} | Time: {source_time:.2f}s")
                    
                    # Early exit if we have enough events
                    if len(all_events) >= max_results * 2:
                        print("   ⚡ Early exit: Sufficient events collected")
                        break
                        
                except Exception as e:
                    print(f"   ❌ {source_name.upper()} failed: {str(e)[:80]}")
                    source_counts[source_name] = {'total': 0, 'unique': 0, 'time': 'error'}
                    continue
            
            # ENSURE EXACTLY N EVENTS: If we don't have enough, fetch more from available sources
            # Continue fetching until we have max_results or all sources are exhausted
            if len(all_events) < max_results:
                print(f"\n⚠️ Only found {len(all_events)} events, need {max_results}. Fetching more...")
                
                # Calculate how many more we need
                needed = max_results - len(all_events)
                
                # Try to get more from SerpAPI if available
                if self.serp_api_key and len(all_events) < max_results:
                    try:
                        additional_needed = max_results - len(all_events)
                        print(f"   🔍 Fetching {additional_needed} more from SerpAPI...")
                        additional_events = self._fetch_serpapi_events(
                            location, categories, start_dt, end_dt, additional_needed * 2  # Fetch extra to account for duplicates
                        )
                        for event in additional_events:
                            if len(all_events) >= max_results:
                                break
                            if event.event_hash not in seen_hashes:
                                all_events.append(event)
                                seen_hashes.add(event.event_hash)
                    except Exception as e:
                        print(f"   ⚠️ Additional SerpAPI fetch failed: {str(e)[:50]}")
                
                # Try to get more from PredictHQ if available
                if self.predicthq_api_key and len(all_events) < max_results:
                    try:
                        additional_needed = max_results - len(all_events)
                        print(f"   🔍 Fetching {additional_needed} more from PredictHQ...")
                        additional_events = self._fetch_predicthq_events(
                            location, categories, start_dt, end_dt, additional_needed * 2
                        )
                        for event in additional_events:
                            if len(all_events) >= max_results:
                                break
                            if event.event_hash not in seen_hashes:
                                all_events.append(event)
                                seen_hashes.add(event.event_hash)
                    except Exception as e:
                        print(f"   ⚠️ Additional PredictHQ fetch failed: {str(e)[:50]}")
                
                # Try to get more from Ticketmaster if available
                if self.ticketmaster_api_key and len(all_events) < max_results:
                    try:
                        additional_needed = max_results - len(all_events)
                        print(f"   🔍 Fetching {additional_needed} more from Ticketmaster...")
                        additional_events = self._fetch_ticketmaster_events(
                            location, categories, start_dt, end_dt, additional_needed * 2
                        )
                        for event in additional_events:
                            if len(all_events) >= max_results:
                                break
                            if event.event_hash not in seen_hashes:
                                all_events.append(event)
                                seen_hashes.add(event.event_hash)
                    except Exception as e:
                        print(f"   ⚠️ Additional Ticketmaster fetch failed: {str(e)[:50]}")
            
            # Score and sort events
            scored_events = self._score_events(all_events)
            
            # ============================================
            # CRITICAL: FILTER TO MATCH RATIO (50/25/25)
            # ============================================
            # Group events by source
            events_by_source = {'serpapi': [], 'predicthq': [], 'ticketmaster': []}
            other_events = []
            
            for event in scored_events:
                source = getattr(event, 'source', '').lower()
                if source in events_by_source:
                    events_by_source[source].append(event)
                else:
                    other_events.append(event)
            
            # Calculate target counts for ratio
            serpapi_target = int(max_results * 0.5)  # 50%
            predicthq_target = int(max_results * 0.25)  # 25%
            ticketmaster_target = int(max_results * 0.25)  # 25%
            
            # If one source failed, redistribute proportionally
            total_available = len(events_by_source['serpapi']) + len(events_by_source['predicthq']) + len(events_by_source['ticketmaster'])
            
            if total_available < max_results:
                # Redistribute targets based on what's actually available
                if len(events_by_source['ticketmaster']) == 0:
                    # Ticketmaster failed - redistribute to SerpAPI and PredictHQ
                    remaining = max_results - len(events_by_source['predicthq'])
                    serpapi_target = min(remaining, len(events_by_source['serpapi']))
                    predicthq_target = min(max_results - serpapi_target, len(events_by_source['predicthq']))
                    ticketmaster_target = 0
                elif len(events_by_source['predicthq']) == 0:
                    # PredictHQ failed - redistribute to SerpAPI and Ticketmaster
                    remaining = max_results - len(events_by_source['ticketmaster'])
                    serpapi_target = min(remaining, len(events_by_source['serpapi']))
                    ticketmaster_target = min(max_results - serpapi_target, len(events_by_source['ticketmaster']))
                    predicthq_target = 0
                else:
                    # All sources have events, use ratio
                    serpapi_target = min(serpapi_target, len(events_by_source['serpapi']))
                    predicthq_target = min(predicthq_target, len(events_by_source['predicthq']))
                    ticketmaster_target = min(ticketmaster_target, len(events_by_source['ticketmaster']))
            
            # Build final list respecting ratio
            final_events = []
            final_events.extend(events_by_source['serpapi'][:serpapi_target])
            final_events.extend(events_by_source['predicthq'][:predicthq_target])
            final_events.extend(events_by_source['ticketmaster'][:ticketmaster_target])
            
            # Fill remaining slots with other sources if needed
            remaining_slots = max_results - len(final_events)
            if remaining_slots > 0:
                # Fill from other events first
                final_events.extend(other_events[:remaining_slots])
                remaining_slots = max_results - len(final_events)
                
                # Then fill from sources that have more events available
                if remaining_slots > 0:
                    # Prioritize sources that haven't met their target
                    if len(final_events) < max_results and len(events_by_source['serpapi']) > serpapi_target:
                        final_events.extend(events_by_source['serpapi'][serpapi_target:serpapi_target + remaining_slots])
                    remaining_slots = max_results - len(final_events)
                    
                    if remaining_slots > 0 and len(events_by_source['predicthq']) > predicthq_target:
                        final_events.extend(events_by_source['predicthq'][predicthq_target:predicthq_target + remaining_slots])
                    remaining_slots = max_results - len(final_events)
                    
                    if remaining_slots > 0 and len(events_by_source['ticketmaster']) > ticketmaster_target:
                        final_events.extend(events_by_source['ticketmaster'][ticketmaster_target:ticketmaster_target + remaining_slots])
            
            # Limit to max_results
            final_events = final_events[:max_results]
            
            # Re-sort by hype score after ratio filtering
            final_events.sort(key=lambda x: getattr(x, 'hype_score', 0.0), reverse=True)
            
            # Cache results
            if final_events:
                self._cache_events(cache_key, final_events)
            
            # Print summary with ratio info
            self._print_discovery_summary(final_events, source_counts)
            
            return final_events
            
        except Exception as e:
            print(f"\n❌ Event discovery failed: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _fetch_serpapi_events(self, location: str, categories: List[str],
                             start_dt: datetime, end_dt: datetime, max_results: int) -> List[ResearchEvent]:
        """Fetch events from SerpAPI (Google Events)"""
        if not self.serp_api_key:
            return []
        
        events = []
        
        try:
            # Generate queries for SerpAPI
            queries = self._generate_serpapi_queries(location, categories, start_dt, end_dt)
            
            # Use all queries (up to 10 per category, max 50 total)
            for i, query in enumerate(queries):
                try:
                    print(f"   Query {i+1}: '{query}'")
                    
                    params = {
                        'q': query,
                        'engine': 'google_events',
                        'api_key': self.serp_api_key,
                        'hl': 'en',
                        'gl': 'us',
                        'num': 20
                    }
                    
                    response = requests.get(
                        'https://serpapi.com/search',
                        params=params,
                        timeout=25
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Check for API errors in response
                        if 'error' in data:
                            print(f"      ❌ SerpAPI Error: {data.get('error', 'Unknown error')}")
                            continue
                        # Debug: Log response structure for troubleshooting
                        if 'events_results' not in data:
                            print(f"      ⚠️  SerpAPI response missing 'events_results'. Keys: {list(data.keys())[:10]}")
                            # Check for alternative response formats
                            if 'events' in data:
                                print(f"      ℹ️  Found 'events' key instead, attempting to parse...")
                                data['events_results'] = data.get('events', [])
                        
                        parsed_events = self._parse_serpapi_response(data, location)
                        events.extend(parsed_events)
                        raw_count = len(data.get('events_results', []))
                        print(f"      ✅ Parsed {len(parsed_events)} events from {raw_count} raw SerpAPI results")
                        if raw_count > 0 and len(parsed_events) == 0:
                            print(f"      ⚠️  WARNING: {raw_count} raw events but 0 parsed! Check date/venue parsing.")
                    else:
                        error_msg = "Unknown error"
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('error', f"HTTP {response.status_code}")
                        except:
                            error_msg = response.text[:100] if response.text else f"HTTP {response.status_code}"
                        print(f"      ❌ SerpAPI HTTP {response.status_code}: {error_msg}")
                    
                    # Rate limiting
                    time.sleep(0.3)
                    
                    if len(events) >= max_results * 2:
                        break
                        
                except requests.Timeout:
                    print(f"      ⏱️ Timeout")
                    continue
                except Exception as e:
                    print(f"      ⚠️ Error: {str(e)[:50]}")
                    continue
            
            # 100% ACCURATE date filtering - STRICT validation
            filtered_events = []
            filtered_out = 0
            
            for event in events:
                # Only include events with valid datetime within range
                if event.start_datetime:
                    # Normalize to date (ignore time for range comparison)
                    event_date = event.start_datetime.date()
                    start_date = start_dt.date()
                    end_date = end_dt.date()
                    
                    # STRICT range check: start <= event <= end (inclusive boundaries)
                    # This ensures 100% accuracy - events outside range are excluded
                    if start_date <= event_date <= end_date:
                        filtered_events.append(event)
                    else:
                        filtered_out += 1
                        # Debug: Log events filtered out for verification
                        if filtered_out <= 3:  # Log first 3 for debugging
                            print(f"         ⚠️ Filtered out: {event.event_name[:40]} - Date: {event_date} (outside range {start_date} to {end_date})")
                else:
                    # Events without datetime are excluded for 100% accuracy
                    filtered_out += 1
            
            if filtered_out > 0:
                print(f"      📊 Date filtering: {len(filtered_events)} included, {filtered_out} filtered out (strict validation)")
            
            return filtered_events[:max_results]
            
        except Exception as e:
            print(f"   ❌ SerpAPI fetch failed: {str(e)[:80]}")
            return []
    
    def _generate_serpapi_queries(self, location: str, categories: List[str],
                                 start_dt: datetime, end_dt: datetime) -> List[str]:
        """
        Generate 10 category-specific sub-queries per selected category
        Each query includes location and category-specific terms
        """
        queries = []
        city = location.split(',')[0].strip()
        
        # Time phrases based on date range
        days_diff = (end_dt - start_dt).days
        if days_diff <= 7:
            time_phrases = ['this week', 'next 7 days', 'upcoming']
        elif days_diff <= 30:
            time_phrases = [start_dt.strftime('%B'), 'this month', 'upcoming']
        else:
            time_phrases = [f"{start_dt.strftime('%B')} to {end_dt.strftime('%B %Y')}", 'upcoming']
        
        # Query templates - 10 variations per category
        # Format: (template, category_keyword)
        category_query_templates = {
            'music': [
                ('{category} events in {location}', 'music'),
                ('top {category} events {location}', 'music'),
                ('upcoming {category} events {location}', 'music'),
                ('{category} concerts {location}', 'concerts'),
                ('live {category} {location}', 'live music'),
                ('{category} festival {location}', 'music festival'),
                ('{category} shows {location}', 'music shows'),
                ('best {category} events {location}', 'music'),
                ('{category} performances {location}', 'music performances'),
                ('{category} gigs {location}', 'music gigs')
            ],
            'sports': [
                ('{category} events in {location}', 'sports'),
                ('top {category} events {location}', 'sports'),
                ('upcoming {category} events {location}', 'sports'),
                ('{category} games {location}', 'sports games'),
                ('{category} matches {location}', 'sports matches'),
                ('{category} championship {location}', 'championship'),
                ('{category} tournament {location}', 'tournament'),
                ('best {category} events {location}', 'sports'),
                ('{category} competition {location}', 'sports competition'),
                ('live {category} {location}', 'live sports')
            ],
            'tech': [
                ('{category} events in {location}', 'tech'),
                ('top {category} events {location}', 'tech'),
                ('upcoming {category} events {location}', 'tech'),
                ('{category} conference {location}', 'tech conference'),
                ('{category} summit {location}', 'technology summit'),
                ('{category} workshop {location}', 'tech workshop'),
                ('{category} meetup {location}', 'tech meetup'),
                ('best {category} events {location}', 'tech'),
                ('{category} expo {location}', 'tech expo'),
                ('{category} innovation {location}', 'tech innovation')
            ],
            'arts': [
                ('{category} events in {location}', 'arts'),
                ('top {category} events {location}', 'arts'),
                ('upcoming {category} events {location}', 'arts'),
                ('{category} exhibition {location}', 'art exhibition'),
                ('{category} gallery {location}', 'art gallery'),
                ('{category} show {location}', 'art show'),
                ('{category} museum {location}', 'art museum'),
                ('best {category} events {location}', 'arts'),
                ('{category} fair {location}', 'art fair'),
                ('{category} festival {location}', 'art festival')
            ],
            'theater': [
                ('{category} events in {location}', 'theater'),
                ('top {category} events {location}', 'theater'),
                ('upcoming {category} events {location}', 'theater'),
                ('{category} shows {location}', 'theater shows'),
                ('{category} plays {location}', 'plays'),
                ('{category} musicals {location}', 'musicals'),
                ('broadway {location}', 'broadway'),
                ('best {category} events {location}', 'theater'),
                ('{category} performances {location}', 'theater performances'),
                ('{category} drama {location}', 'drama')
            ],
            'food': [
                ('{category} events in {location}', 'food'),
                ('top {category} events {location}', 'food'),
                ('upcoming {category} events {location}', 'food'),
                ('{category} festival {location}', 'food festival'),
                ('culinary {location}', 'culinary events'),
                ('{category} tasting {location}', 'food tasting'),
                ('wine tasting {location}', 'wine tasting'),
                ('best {category} events {location}', 'food'),
                ('{category} and wine {location}', 'food and wine'),
                ('{category} market {location}', 'food market')
            ],
            'conference': [
                ('{category} events in {location}', 'conference'),
                ('top {category} events {location}', 'conference'),
                ('upcoming {category} events {location}', 'conference'),
                ('{category} summit {location}', 'summit'),
                ('{category} convention {location}', 'convention'),
                ('{category} workshop {location}', 'workshop'),
                ('{category} seminar {location}', 'seminar'),
                ('best {category} events {location}', 'conference'),
                ('{category} expo {location}', 'expo'),
                ('{category} forum {location}', 'forum')
            ],
            'comedy': [
                ('{category} events in {location}', 'comedy'),
                ('top {category} events {location}', 'comedy'),
                ('upcoming {category} events {location}', 'comedy'),
                ('{category} shows {location}', 'comedy shows'),
                ('stand-up {category} {location}', 'stand-up comedy'),
                ('{category} club {location}', 'comedy club'),
                ('{category} night {location}', 'comedy night'),
                ('best {category} events {location}', 'comedy'),
                ('{category} performances {location}', 'comedy performances'),
                ('{category} festival {location}', 'comedy festival')
            ],
            'family': [
                ('{category} events in {location}', 'family'),
                ('top {category} events {location}', 'family'),
                ('upcoming {category} events {location}', 'family'),
                ('{category} activities {location}', 'family activities'),
                ('kids events {location}', 'kids events'),
                ('{category} fun {location}', 'family fun'),
                ('{category} entertainment {location}', 'family entertainment'),
                ('best {category} events {location}', 'family'),
                ('{category} festival {location}', 'family festival'),
                ('children events {location}', 'children events')
            ],
            'networking': [
                ('{category} events in {location}', 'networking'),
                ('top {category} events {location}', 'networking'),
                ('upcoming {category} events {location}', 'networking'),
                ('business {category} {location}', 'business networking'),
                ('professional {category} {location}', 'professional networking'),
                ('{category} meetup {location}', 'networking meetup'),
                ('{category} mixer {location}', 'networking mixer'),
                ('best {category} events {location}', 'networking'),
                ('{category} social {location}', 'networking social'),
                ('{category} gathering {location}', 'networking gathering')
            ],
            'dance': [
                ('{category} events in {location}', 'dance'),
                ('top {category} events {location}', 'dance'),
                ('upcoming {category} events {location}', 'dance'),
                ('{category} performances {location}', 'dance performances'),
                ('{category} shows {location}', 'dance shows'),
                ('ballet {location}', 'ballet'),
                ('{category} festival {location}', 'dance festival'),
                ('best {category} events {location}', 'dance'),
                ('{category} concert {location}', 'dance concert'),
                ('{category} recital {location}', 'dance recital')
            ]
        }
        
        # If "all" categories or empty, use general queries
        if not categories or 'all' in [c.lower() for c in categories]:
            for time_phrase in time_phrases:
                queries.append(f"events in {city} {time_phrase}")
                queries.append(f"top events {city} {time_phrase}")
                queries.append(f"upcoming events {city} {time_phrase}")
                queries.append(f"{city} events {time_phrase}")
                queries.append(f"best events {city} {time_phrase}")
                queries.append(f"events {city} {time_phrase}")
                queries.append(f"{city} upcoming events {time_phrase}")
                queries.append(f"{city} top events {time_phrase}")
                queries.append(f"popular events {city} {time_phrase}")
                queries.append(f"{city} events calendar {time_phrase}")
        else:
            # Category-specific queries - 10 sub-queries per category
            for category in categories:
                category_lower = category.lower()
                if category_lower in category_query_templates:
                    templates = category_query_templates[category_lower]
                    # Generate 10 queries per category
                    for template, keyword in templates:
                        # Format template: use keyword directly, not as {category} placeholder
                        # This prevents duplication (e.g., "sports games games")
                        query = template.replace('{category}', keyword).replace('{location}', city)
                        queries.append(query)
                        
                        # Add time phrase variations for first 3 queries
                        query_count = len([q for q in queries if keyword.lower() in q.lower()])
                        if query_count <= 3:
                            for time_phrase in time_phrases[:1]:  # Use first time phrase
                                query_with_time = f"{query} {time_phrase}"
                                queries.append(query_with_time)
        
        # Remove duplicates while preserving order
        unique_queries = list(dict.fromkeys(queries))
        
        # Limit: 10 queries per category, max 50 total
        max_queries = min(len(categories) * 10, 50) if categories and 'all' not in [c.lower() for c in categories] else 20
        return unique_queries[:max_queries]
    
    def _parse_serpapi_response(self, data: Dict, location: str) -> List[ResearchEvent]:
        """Parse SerpAPI response with comprehensive error handling"""
        events = []
        
        # Check for events_results
        if 'events_results' not in data:
            print(f"      ⚠️ No 'events_results' in SerpAPI response. Keys: {list(data.keys())[:10]}")
            # Try alternative keys
            if 'events' in data:
                print(f"      ℹ️  Found 'events' key, using that instead...")
                data['events_results'] = data.get('events', [])
            else:
                return events
        
        events_data = data.get('events_results', [])
        if not events_data:
            print(f"      ⚠️ SerpAPI returned empty events_results")
            return events
        
        print(f"      📊 Parsing {len(events_data)} events from SerpAPI...")
        
        parse_errors = 0
        skipped_no_title = 0
        skipped_no_venue = 0
        skipped_date_issue = 0
        
        for idx, event_data in enumerate(events_data):
            try:
                # Debug first 3 events structure
                if idx < 3:
                    print(f"      🔍 Event {idx+1} keys: {list(event_data.keys())[:10]}")
                    if 'date' in event_data:
                        date_val = event_data['date']
                        print(f"         Date: {type(date_val).__name__} = {str(date_val)[:100]}")
                    if 'venue' in event_data:
                        venue_val = event_data['venue']
                        print(f"         Venue: {type(venue_val).__name__} = {str(venue_val)[:100]}")
                    if 'title' in event_data:
                        print(f"         Title: {event_data.get('title', 'N/A')[:60]}")
                
                event = self._parse_serpapi_event(event_data, location)
                if event:
                    events.append(event)
                    if idx < 3:
                        print(f"      ✅ Event {idx+1} parsed: {event.event_name[:50]} | Date: {event.exact_date}")
                else:
                    parse_errors += 1
                    # Check why it failed
                    title = event_data.get('title', '')
                    if not title or len(title.strip()) < 3:
                        skipped_no_title += 1
                    else:
                        # Check venue
                        venue_obj = event_data.get('venue', {})
                        venue_name = venue_obj.get('name', '') if isinstance(venue_obj, dict) else str(venue_obj)
                        if not venue_name or len(venue_name.strip()) < 3:
                            skipped_no_venue += 1
                        else:
                            skipped_date_issue += 1
            except Exception as e:
                parse_errors += 1
                if idx < 5:  # Log first 5 errors for debugging
                    import traceback
                    print(f"      ❌ Failed to parse event {idx+1}: {str(e)[:100]}")
                    if idx < 2:
                        print(f"         Traceback: {traceback.format_exc()[:200]}")
                continue
        
        if parse_errors > 0:
            print(f"      ⚠️ {parse_errors} events failed to parse:")
            if skipped_no_title > 0:
                print(f"         - {skipped_no_title} skipped (no title)")
            if skipped_no_venue > 0:
                print(f"         - {skipped_no_venue} skipped (no venue)")
            if skipped_date_issue > 0:
                print(f"         - {skipped_date_issue} skipped (date parsing issue)")
        
        return events
    
    def _parse_serpapi_event(self, event_data: Dict, location: str) -> Optional[ResearchEvent]:
        """Parse individual SerpAPI event with comprehensive error handling"""
        try:
            # Extract title
            title = event_data.get('title', '')
            if not title or len(title.strip()) < 3:
                return None
            
            # Extract date and time - handle multiple SerpAPI response formats
            # IMPORTANT: Preserve COMPLETE time range (e.g., "9:00 AM - 6:00 PM Asia/Tokyo")
            start_dt = None
            time_tuple = None
            complete_time_str = None  # Store complete time range string
            timezone_str = None  # Store timezone if available
            
            # Try multiple date extraction methods
            date_info = event_data.get('date', {})
            start_date = None
            time_str = None
            
            if isinstance(date_info, dict):
                # Try different date keys in order of preference
                start_date = (date_info.get('start_date') or 
                             date_info.get('date') or
                             date_info.get('timestamp'))
                # Check for time in date dict
                time_str = date_info.get('time') or date_info.get('start_time')
                
                # Extract "when" field which contains date + time (e.g., "Sun, Dec 28, 3 PM" or "Wed, Dec 17, 7:30 – 9:00 PM")
                when_str = date_info.get('when', '')
                if when_str:
                    # Extract COMPLETE time range from "when" string (preserve full range like "7:30 – 9:00 PM" or "9:00 AM - 6:00 PM")
                    # Match full time range patterns: "7:30 – 9:00 PM", "9:00 AM - 6:00 PM", "3 PM - 5 PM", etc.
                    time_range_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*(?:–|-|—|to)\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))|(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
                    time_match = re.search(time_range_pattern, when_str, re.IGNORECASE)
                    if time_match:
                        # Get the full match (either range or single time)
                        complete_time_str = time_match.group(0).strip() if time_match.group(0) else (time_match.group(1) or time_match.group(2))
                        time_str = complete_time_str
                    
                    # Extract timezone if present (e.g., "Asia/Tokyo", "EST", "PST", "UTC", etc.)
                    timezone_match = re.search(r'\b(Asia/[A-Za-z]+|America/[A-Za-z]+|Europe/[A-Za-z]+|Africa/[A-Za-z]+|Australia/[A-Za-z]+|Pacific/[A-Za-z]+|EST|PST|CST|MST|EDT|PDT|CDT|MDT|UTC|GMT|JST|KST|CET|CEST)\b', when_str, re.IGNORECASE)
                    if timezone_match:
                        timezone_str = timezone_match.group(1)
                    
                    # Extract date part: "Dec 28" from "Sun, Dec 28, 3 PM"
                    date_only_match = re.search(r'([A-Za-z]+\s+\d{1,2})', when_str)
                    if date_only_match:
                        start_date = date_only_match.group(1)
                    elif not start_date:
                        start_date = when_str
            elif date_info:
                start_date = str(date_info)
            
            # Also check for direct date fields
            if not start_date:
                when_str = event_data.get('when', '')
                if when_str:
                    # Extract COMPLETE time range from "when" string
                    time_range_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*(?:–|-|—|to)\s*\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))|(\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm))'
                    time_match = re.search(time_range_pattern, when_str, re.IGNORECASE)
                    if time_match:
                        complete_time_str = time_match.group(0).strip() if time_match.group(0) else (time_match.group(1) or time_match.group(2))
                        time_str = complete_time_str
                    
                    # Extract timezone if present
                    timezone_match = re.search(r'\b(Asia/[A-Za-z]+|America/[A-Za-z]+|Europe/[A-Za-z]+|Africa/[A-Za-z]+|Australia/[A-Za-z]+|Pacific/[A-Za-z]+|EST|PST|CST|MST|EDT|PDT|CDT|MDT|UTC|GMT|JST|KST|CET|CEST)\b', when_str, re.IGNORECASE)
                    if timezone_match:
                        timezone_str = timezone_match.group(1)
                    
                    # Extract date part
                    date_only_match = re.search(r'([A-Za-z]+\s+\d{1,2})', when_str)
                    if date_only_match:
                        start_date = date_only_match.group(1)
                    else:
                        start_date = when_str
                else:
                    start_date = event_data.get('start_date') or event_data.get('date')
            
            # Check for separate time field at event level
            # Also check in scraping data fields (SerpAPI often puts time in various places)
            if not time_str:
                time_str = (event_data.get('time') or 
                           event_data.get('start_time') or 
                           event_data.get('event_time') or
                           event_data.get('eventTime') or
                           event_data.get('when_time') or
                           event_data.get('date', {}).get('time') if isinstance(event_data.get('date'), dict) else None)
                if time_str:
                    complete_time_str = time_str
            
            # Check for time range fields (e.g., "start_time" and "end_time")
            if not complete_time_str:
                start_time = event_data.get('start_time') or (event_data.get('date', {}).get('start_time') if isinstance(event_data.get('date'), dict) else None)
                end_time = event_data.get('end_time') or (event_data.get('date', {}).get('end_time') if isinstance(event_data.get('date'), dict) else None)
                if start_time and end_time:
                    complete_time_str = f"{start_time} - {end_time}"
                elif start_time:
                    complete_time_str = start_time
            
            # Check for timezone in separate fields
            if not timezone_str:
                timezone_str = (event_data.get('timezone') or 
                               event_data.get('tz') or
                               event_data.get('date', {}).get('timezone') if isinstance(event_data.get('date'), dict) else None)
            
            # Parse time using helper function
            if time_str:
                time_tuple = self._parse_time_from_string(time_str)
            
            # Also try to extract time from "when" field if we haven't found it yet
            # This is common in SerpAPI scraping data
            if not time_tuple:
                when_str = event_data.get('when', '') or (event_data.get('date', {}).get('when', '') if isinstance(event_data.get('date'), dict) else '')
                if when_str:
                    time_tuple = self._parse_time_from_string(when_str)
            
            # Parse date with comprehensive format handling
            if start_date:
                try:
                    # ISO format with timezone
                    if isinstance(start_date, str) and 'T' in start_date:
                        try:
                            # Handle ISO format: 2025-12-15T19:00:00Z or 2025-12-15T19:00:00+00:00
                            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        except:
                            # Try parsing just the date part
                            date_part = start_date.split('T')[0]
                            start_dt = datetime.strptime(date_part, '%Y-%m-%d')
                            # If we have time tuple from parsing, combine it
                            if time_tuple:
                                start_dt = start_dt.replace(hour=time_tuple[0], minute=time_tuple[1])
                    # Unix timestamp
                    elif isinstance(start_date, (int, float)):
                        start_dt = datetime.fromtimestamp(start_date)
                        # Only use time_tuple if timestamp doesn't have meaningful time (is midnight)
                        # This prevents false fallback times
                        if time_tuple and (start_dt.hour == 0 and start_dt.minute == 0):
                            start_dt = start_dt.replace(hour=time_tuple[0], minute=time_tuple[1])
                        elif not time_tuple and (start_dt.hour == 0 and start_dt.minute == 0):
                            # If timestamp is midnight and no separate time, don't treat it as having time
                            pass
                    # String date formats - handle abbreviated months like "Dec 7", "Dec 6"
                    elif isinstance(start_date, str):
                        date_formats = [
                            '%Y-%m-%d',
                            '%B %d, %Y',      # December 7, 2025
                            '%b %d, %Y',      # Dec 7, 2025
                            '%b %d',          # Dec 7 (current year assumed)
                            '%B %d',          # December 7 (current year assumed)
                            '%m/%d/%Y',
                            '%d/%m/%Y',
                            '%Y-%m-%d %H:%M:%S',
                            '%B %d, %Y %I:%M %p',
                            '%b %d, %Y %I:%M %p',
                            '%d %B %Y',
                            '%d %b %Y',
                            '%b %d %Y',       # Dec 7 2025 (no comma)
                            '%B %d %Y'        # December 7 2025 (no comma)
                        ]
                        for fmt in date_formats:
                            try:
                                parsed_dt = datetime.strptime(start_date.strip(), fmt)
                                # If year not in format, assume current year or next year if month has passed
                                if '%Y' not in fmt:
                                    current_year = datetime.now().year
                                    # If the month has already passed this year, use next year
                                    if parsed_dt.month < datetime.now().month or \
                                       (parsed_dt.month == datetime.now().month and parsed_dt.day < datetime.now().day):
                                        parsed_dt = parsed_dt.replace(year=current_year + 1)
                                    else:
                                        parsed_dt = parsed_dt.replace(year=current_year)
                                start_dt = parsed_dt
                                # If format had time, it's already in start_dt
                                # Otherwise, use time_tuple if available
                                if time_tuple and ('%I:%M %p' not in fmt and '%H:%M' not in fmt and '%H:%M:%S' not in fmt):
                                    start_dt = start_dt.replace(hour=time_tuple[0], minute=time_tuple[1])
                                break
                            except:
                                continue
                        # If no format matched, try to extract month/day from "Dec 7" format manually
                        if not start_dt:
                            # Try to parse abbreviated month formats like "Dec 7", "Jan 3"
                            month_abbrev = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                            }
                            parts = start_date.strip().lower().split()
                            if len(parts) >= 2:
                                month_str = parts[0]
                                day_str = parts[1].rstrip(',')
                                if month_str in month_abbrev and day_str.isdigit():
                                    try:
                                        current_year = datetime.now().year
                                        current_month = datetime.now().month
                                        current_day = datetime.now().day
                                        month = month_abbrev[month_str]
                                        day = int(day_str)
                                        
                                        # Determine year: if month/day has passed, use next year
                                        if month < current_month or \
                                           (month == current_month and day < current_day):
                                            year = current_year + 1
                                        else:
                                            year = current_year
                                        
                                        # Additional check: if we're in December and date is in early months,
                                        # it's likely next year
                                        if current_month == 12 and month <= 3:
                                            year = current_year + 1
                                        
                                        start_dt = datetime(year, month, day)
                                        
                                        # Add time if we have it (but only if it's real, not false fallback)
                                        if time_tuple:
                                            start_dt = start_dt.replace(hour=time_tuple[0], minute=time_tuple[1])
                                    except:
                                        pass
                except Exception:
                    pass
            
            # Format date/time display - PRESERVE COMPLETE TIME RANGE from API response
            # Priority: Use complete_time_str if available (preserves full range like "9:00 AM - 6:00 PM")
            if complete_time_str:
                # We have a complete time string from the API - use it!
                if start_date:
                    # Parse date part to format it consistently
                    date_part = None
                    try:
                        # Try to extract just the date part (e.g., "Dec 17" from "Wed, Dec 17, 7:30 – 9:00 PM")
                        if isinstance(start_date, str):
                            date_only_match = re.search(r'([A-Za-z]+\s+\d{1,2})', start_date)
                            if date_only_match:
                                date_part = date_only_match.group(1)
                            else:
                                date_part = start_date
                        else:
                            date_part = str(start_date)
                    except:
                        date_part = str(start_date) if start_date else None
                    
                    if date_part:
                        # Format: "MM-DD-YY complete_time_str timezone"
                        # First, try to format the date part properly
                        try:
                            # Try to parse and reformat date
                            month_abbrev = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                            }
                            parts = date_part.strip().lower().split()
                            if len(parts) >= 2:
                                month_str = parts[0]
                                day_str = parts[1].rstrip(',')
                                if month_str in month_abbrev and day_str.isdigit():
                                    current_year = datetime.now().year
                                    current_month = datetime.now().month
                                    current_day = datetime.now().day
                                    month = month_abbrev[month_str]
                                    day = int(day_str)
                                    
                                    # Determine year
                                    if month < current_month or (month == current_month and day < current_day):
                                        year = current_year + 1
                                    else:
                                        year = current_year
                                    
                                    if current_month == 12 and month <= 3:
                                        year = current_year + 1
                                    
                                    formatted_date = datetime(year, month, day).strftime('%m-%d-%y')
                                    date_display = f"{formatted_date} {complete_time_str}"
                                    if timezone_str:
                                        date_display += f" {timezone_str}"
                                else:
                                    date_display = f"{date_part} {complete_time_str}"
                                    if timezone_str:
                                        date_display += f" {timezone_str}"
                            else:
                                date_display = f"{date_part} {complete_time_str}"
                                if timezone_str:
                                    date_display += f" {timezone_str}"
                        except:
                            date_display = f"{date_part} {complete_time_str}"
                            if timezone_str:
                                date_display += f" {timezone_str}"
                    else:
                        date_display = complete_time_str
                        if timezone_str:
                            date_display += f" {timezone_str}"
                else:
                    # No date, just time
                    date_display = complete_time_str
                    if timezone_str:
                        date_display += f" {timezone_str}"
            else:
                # Fallback to original formatting if no complete time string
                date_display = self._format_date_time_display(start_dt, time_tuple)
            
            # Final validation: if we couldn't parse anything meaningful, return "NA"
            if not date_display or date_display == "NA":
                date_display = "NA"
            
            # Extract venue - try multiple sources
            venue = 'Venue not specified'
            
            # Try venue.name first (most reliable)
            venue_obj = event_data.get('venue', {})
            if isinstance(venue_obj, dict) and venue_obj.get('name'):
                venue = venue_obj.get('name', '')
            
            # Fallback to address if venue name not available
            if not venue or len(venue.strip()) < 3:
                address = event_data.get('address', '')
                if address:
                    # Get first part of address as venue name
                    venue = address.split(',')[0].strip()
            
            # Final fallback
            if not venue or len(venue.strip()) < 3:
                venue = event_data.get('venue', 'Venue not specified')
                if isinstance(venue, dict):
                    venue = venue.get('name', 'Venue not specified')
                venue = str(venue) if venue else 'Venue not specified'
            
            # Extract location - SerpAPI address can be a LIST or string
            # Based on web search: address field from SerpAPI is often a list
            address = event_data.get('address', '')
            
            # Handle address as list (common in SerpAPI)
            if isinstance(address, list):
                address = ', '.join(str(a) for a in address if a) if address else ''
            elif not isinstance(address, str):
                address = str(address) if address else ''
            
            # If no address, try to get from venue
            if not address:
                venue_obj = event_data.get('venue', {})
                if isinstance(venue_obj, dict):
                    venue_address = venue_obj.get('address', '')
                    if isinstance(venue_address, list):
                        venue_address = ', '.join(str(a) for a in venue_address if a) if venue_address else ''
                    address = str(venue_address) if venue_address else ''
            
            # Extract city/region from address (last part after comma)
            event_location = location  # Default to search location (city name)
            if address:
                address_parts = [p.strip() for p in address.split(',') if p.strip()]
                if address_parts:
                    # Use last part (usually city, state) or second-to-last if last is just state abbreviation
                    if len(address_parts) >= 2:
                        # Last part is usually city, state or just state
                        event_location = address_parts[-1]  # e.g., "East Rutherford, NJ" -> "NJ" or "New York, NY" -> "NY"
                        # If it's just a state abbreviation, use the city part
                        if len(event_location) <= 3 and len(address_parts) >= 2:
                            event_location = address_parts[-2]  # Use city instead
                    else:
                        event_location = address_parts[0]
            
            # CRITICAL: Ensure location is always a string, never a list
            if isinstance(event_location, list):
                event_location = ', '.join(str(l) for l in event_location if l) if event_location else location
            event_location = str(event_location).strip() if event_location else location
            
            # Final safety: if location is still problematic, use search location
            if not event_location or len(event_location) > 200:
                event_location = location
            
            # Calculate hype score
            hype_score = self._calculate_hype_score(title, venue)
            
            event = ResearchEvent(
                event_name=title[:100],
                exact_date=date_display,
                exact_venue=venue[:80],
                location=event_location[:60],
                category=self._classify_event_type(title),
                confidence_score=0.85,
                source_url=validate_and_sanitize_url(
                    event_data.get('link', '') or event_data.get('url', '') or ''
                ),
                posted_by='Google Events',
                hype_score=hype_score,
                source='serpapi',
                start_datetime=start_dt
            )
            
            return event
            
        except Exception as e:
            # Log detailed error for debugging
            import traceback
            if not hasattr(self, '_parse_error_count'):
                self._parse_error_count = 0
            
            self._parse_error_count += 1
            
            if self._parse_error_count <= 5:
                print(f"      ❌ Parse error #{self._parse_error_count}: {str(e)[:150]}")
                if self._parse_error_count <= 2:
                    # Show full traceback for first 2 errors
                    print(f"         Full error: {traceback.format_exc()[:300]}")
            return None
    
    def _fetch_predicthq_events(self, location: str, categories: List[str],
                               start_dt: datetime, end_dt: datetime, max_results: int) -> List[ResearchEvent]:
        """Fetch events from PredictHQ API with comprehensive error handling"""
        if not self.predicthq_api_key:
            print(f"   ⚠️ PredictHQ: No API key configured")
            return []
        
        events = []
        
        try:
            # Category mapping for PredictHQ API
            phq_categories = {
                'music': 'concerts',
                'sports': 'sports',
                'tech': 'conferences',
                'business': 'conferences',
                'arts': 'performing-arts',
                'festival': 'festivals',
                'conference': 'conferences',
                'theater': 'performing-arts',
                'comedy': 'performing-arts',
                'family': 'community',
                'networking': 'conferences',
                'workshop': 'conferences',
                'dance': 'performing-arts'
            }
            
            # Get PredictHQ categories
            phq_cats = []
            for cat in categories:
                cat_lower = cat.lower()
                if cat_lower in phq_categories:
                    mapped = phq_categories[cat_lower]
                    if mapped not in phq_cats:
                        phq_cats.append(mapped)
            
            # Extract city from location for better search
            city = location.split(',')[0].strip() if location else ''
            
            # Build API parameters - use start.gte/start.lte for better results (per PredictHQ docs)
            # Try multiple search strategies for better coverage
            search_queries = []
            if city and city.lower() != location.lower():
                search_queries.append(city)  # Try city first
            search_queries.append(location)  # Then full location
            
            events = []
            for search_query in search_queries[:2]:  # Try up to 2 queries
                params = {
                    'q': search_query,
                    'start.gte': start_dt.strftime('%Y-%m-%d'),
                    'start.lte': end_dt.strftime('%Y-%m-%d'),
                    'limit': min(max_results * 3, 50),  # Get more to ensure we meet ratio
                    'sort': 'rank'
                }
                
                # Add category filter if available
                if phq_cats:
                    params['category'] = ','.join(phq_cats[:3])  # PredictHQ allows up to 3 categories
                    print(f"      🎯 PredictHQ categories: {params['category']}")
                else:
                    # If no category filter, try without it for broader results
                    print(f"      🎯 PredictHQ: No category filter, searching all categories")
                
                headers = {
                    'Authorization': f'Bearer {self.predicthq_api_key}',
                    'Accept': 'application/json'
                }
                
                print(f"      🔍 Querying PredictHQ API for '{search_query}'...")
                
                response = requests.get(
                    'https://api.predicthq.com/v1/events/',
                    params=params,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Log response structure for debugging
                    if 'results' not in data:
                        print(f"      ⚠️ PredictHQ: Unexpected response structure")
                        print(f"      📋 Response keys: {list(data.keys())}")
                        if 'count' in data:
                            print(f"      📊 API reported {data.get('count', 0)} events")
                        continue  # Try next query
                    
                    query_events = self._parse_predicthq_response(data, location)
                    events.extend(query_events)
                    print(f"      ✅ Found {len(query_events)} events for '{search_query}'")
                    
                    # If we have enough events, stop trying more queries
                    if len(events) >= max_results:
                        break
                elif response.status_code == 401:
                    print(f"      ❌ PredictHQ: Authentication failed (401) - Check API token")
                    break
                elif response.status_code == 403:
                    print(f"      ❌ PredictHQ: Forbidden (403) - Check API permissions")
                    break
                else:
                    print(f"      ⚠️ PredictHQ HTTP {response.status_code} for '{search_query}'")
                    # Continue to next query
            
            # Remove duplicates and limit
            seen_hashes = set()
            unique_events = []
            for event in events:
                if event.event_hash not in seen_hashes:
                    seen_hashes.add(event.event_hash)
                    unique_events.append(event)
            
            print(f"   ✅ PredictHQ: Found {len(unique_events)} unique events")
            return unique_events[:max_results]
                
        except requests.Timeout:
            print(f"   ⏱️ PredictHQ: Request timeout (30s)")
            return []
        except requests.RequestException as e:
            print(f"   ❌ PredictHQ: Network error - {str(e)[:100]}")
            return []
        except Exception as e:
            print(f"   ❌ PredictHQ fetch failed: {str(e)[:100]}")
            import traceback
            if hasattr(self, '_predicthq_error_count'):
                self._predicthq_error_count += 1
            else:
                self._predicthq_error_count = 1
            
            if self._predicthq_error_count <= 2:
                print(f"      Full error: {traceback.format_exc()[:300]}")
            return []
    
    def _parse_predicthq_response(self, data: Dict, location: str) -> List[ResearchEvent]:
        """
        Parse PredictHQ response - STRICT venue filtering
        Filters out ALL generic/invalid venues
        """
        events = []
        skipped_no_venue = 0
        
        if 'results' not in data:
            print(f"      ⚠️ PredictHQ: No 'results' key in response")
            print(f"      📋 Response keys: {list(data.keys())}")
            if 'count' in data:
                print(f"      📊 Total events in response: {data.get('count', 0)}")
            return events
        
        results = data.get('results', [])
        if not results:
            print(f"      ℹ️ PredictHQ: Response has 'results' key but it's empty")
            if 'count' in data:
                print(f"      📊 API reported {data.get('count', 0)} events, but results array is empty")
            return events
        
        print(f"      📊 PredictHQ returned {len(results)} events in response")
        
        # Comprehensive list of invalid/generic venues
        invalid_venues = {
            'various venues', 'various', 'multiple venues', 'tbd', 'tba', 'tbc',
            'to be determined', 'to be announced', 'to be confirmed',
            'location tbd', 'venue tbd', 'see website', 'check website',
            'various locations', 'multiple locations', 'online', 'virtual',
            'streaming', 'livestream', 'live stream', 'tba venue'
        }
        
        for event_data in data['results']:
            try:
                event = self._parse_predicthq_event(event_data, location)
                if event:
                    # Check event category - sports events may not have specific venues
                    event_category = event.category.lower() if event.category else ''
                    is_sports_event = 'sports' in event_category or any(
                        keyword in event.event_name.lower() 
                        for keyword in ['vs', 'match', 'championship', 'tournament', 'cup', 'league']
                    )
                    
                    # STRICT venue validation (relaxed for sports events)
                    venue_lower = event.exact_venue.lower().strip()
                    
                    # For sports events, allow location-based venues (e.g., "South Korea" for international matches)
                    if is_sports_event:
                        # Sports events can use location if no specific venue
                        if (venue_lower in invalid_venues or len(event.exact_venue.strip()) < 3):
                            # Use location as venue fallback for sports events
                            if location and location.lower() not in ['various', 'tbd', 'tba']:
                                event.exact_venue = location
                                print(f"      ℹ️ PredictHQ event '{event.event_name[:50]}' - using location as venue fallback")
                            else:
                                skipped_no_venue += 1
                                continue
                    else:
                        # Non-sports events: strict venue validation
                        if (venue_lower in invalid_venues or 
                            len(event.exact_venue.strip()) < 3 or
                            any(invalid in venue_lower for invalid in ['various', 'tbd', 'tba', 'tbc', 'to be'])):
                            skipped_no_venue += 1
                            continue
                    
                    events.append(event)
            except Exception:
                continue
        
        if skipped_no_venue > 0:
            print(f"      ⚠️ Skipped {skipped_no_venue} PredictHQ events (invalid/generic venue)")
        
        return events
    
    def _parse_predicthq_event(self, event_data: Dict, location: str) -> Optional[ResearchEvent]:
        """Parse individual PredictHQ event"""
        try:
            title = event_data.get('title', '').strip()
            if not title:
                return None
            
            # Date and time - PRESERVE COMPLETE TIME RANGE from PredictHQ API
            start_str = event_data.get('start', '')
            end_str = event_data.get('end', '')
            start_dt = None
            end_dt = None
            time_tuple = None
            complete_time_str = None
            timezone_str = None
            
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    # Extract timezone if present in ISO string
                    if '+' in start_str or start_str.endswith('Z'):
                        # Try to extract timezone
                        tz_match = re.search(r'([+-]\d{2}:\d{2}|Z|UTC|GMT|EST|PST|CST|MST|EDT|PDT|CDT|MDT|JST|KST|CET|CEST|Asia/[A-Za-z]+|America/[A-Za-z]+|Europe/[A-Za-z]+)', start_str, re.IGNORECASE)
                        if tz_match:
                            timezone_str = tz_match.group(1)
                    
                    # Only extract time if it's not midnight (which might be a false fallback)
                    if start_dt.hour != 0 or start_dt.minute != 0:
                        time_tuple = (start_dt.hour, start_dt.minute)
                except:
                    pass
            
            # Check for end time to create time range
            if end_str:
                try:
                    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    # If we have both start and end times, create complete time range
                    if start_dt and end_dt:
                        start_time_str = start_dt.strftime('%I:%M %p').lstrip('0')
                        end_time_str = end_dt.strftime('%I:%M %p').lstrip('0')
                        complete_time_str = f"{start_time_str} - {end_time_str}"
                    elif end_dt:
                        end_time_str = end_dt.strftime('%I:%M %p').lstrip('0')
                        if start_dt:
                            start_time_str = start_dt.strftime('%I:%M %p').lstrip('0')
                            complete_time_str = f"{start_time_str} - {end_time_str}"
                        else:
                            complete_time_str = end_time_str
                except:
                    pass
            
            # Also check for separate time fields (start_time, end_time)
            if not complete_time_str:
                start_time_field = event_data.get('start_time') or event_data.get('time')
                end_time_field = event_data.get('end_time')
                if start_time_field and end_time_field:
                    complete_time_str = f"{start_time_field} - {end_time_field}"
                elif start_time_field:
                    complete_time_str = start_time_field
            
            # If we still don't have complete time, check for time tuple
            if not complete_time_str and time_tuple:
                time_str = start_dt.strftime('%I:%M %p').lstrip('0') if start_dt else None
                if time_str:
                    complete_time_str = time_str
            
            # Format date/time display - PRESERVE COMPLETE TIME RANGE
            if complete_time_str and start_dt:
                # Format date part
                date_part = start_dt.strftime('%m-%d-%y')
                date_display = f"{date_part} {complete_time_str}"
                if timezone_str:
                    date_display += f" {timezone_str}"
            else:
                # Fallback to original formatting
                date_display = self._format_date_time_display(start_dt, time_tuple)
            
            # Venue - Enhanced extraction from PredictHQ API structure
            # Check ALL possible fields: venue, place, location, entities
            venue_name = None
            venue_info = event_data.get('venue', {})
            
            # Method 1: Extract from venue.name (primary source)
            if isinstance(venue_info, dict):
                venue_name = venue_info.get('name') or venue_info.get('title')
                
                # If venue name exists, build complete venue string
                if venue_name and str(venue_name).strip() and str(venue_name).lower() != 'various venues':
                    venue_parts = [str(venue_name).strip()]
                    
                    # Add address if available
                    address = venue_info.get('address') or venue_info.get('street')
                    if address and str(address).strip() and str(address).lower() not in ['various', 'tbd', 'tba']:
                        venue_parts.append(str(address).strip())
                    
                    # Add city
                    city = venue_info.get('city')
                    if city and str(city).strip() and city not in venue_parts:
                        venue_parts.append(str(city).strip())
                    
                    # Combine if we have multiple parts
                    if len(venue_parts) > 1:
                        venue_name = ', '.join([p for p in venue_parts if p and str(p).strip()])
                    else:
                        venue_name = str(venue_parts[0]).strip() if venue_parts else None
            
            # Method 2: Check place field (PredictHQ often uses 'place' for venue)
            if not venue_name or str(venue_name).lower() in ['various venues', 'various', 'tbd', 'tba']:
                place_info = event_data.get('place', {})
                if isinstance(place_info, dict):
                    # Check place.name first (most common)
                    venue_name = place_info.get('name') or place_info.get('venue') or place_info.get('title')
                    if venue_name:
                        venue_name = str(venue_name).strip()
                        # Build complete venue string if we have address
                        if venue_name:
                            venue_parts = [venue_name]
                            address = place_info.get('address') or place_info.get('street')
                            if address and str(address).strip():
                                venue_parts.append(str(address).strip())
                            city = place_info.get('city')
                            if city and str(city).strip() and city not in venue_parts:
                                venue_parts.append(str(city).strip())
                            if len(venue_parts) > 1:
                                venue_name = ', '.join([p for p in venue_parts if p and str(p).strip()])
            
            # Method 3: Check location fields at event level
            if not venue_name or str(venue_name).lower() in ['various venues', 'various', 'tbd', 'tba']:
                location_info = event_data.get('location', {})
                if isinstance(location_info, dict):
                    venue_name = (location_info.get('name') or 
                                 location_info.get('venue') or 
                                 location_info.get('title') or
                                 location_info.get('address'))
                    if venue_name:
                        venue_name = str(venue_name).strip()
            
            # Method 4: Check entities array (PredictHQ sometimes stores venue in entities)
            if not venue_name or str(venue_name).lower() in ['various venues', 'various', 'tbd', 'tba']:
                entities = event_data.get('entities', [])
                if entities and isinstance(entities, list):
                    for entity in entities:
                        if isinstance(entity, dict):
                            # Check if entity is a venue/place
                            entity_type = entity.get('type', '').lower()
                            if 'venue' in entity_type or 'place' in entity_type or 'location' in entity_type:
                                venue_name = entity.get('name') or entity.get('title')
                                if venue_name:
                                    venue_name = str(venue_name).strip()
                                    break
            
            # Method 5: Extract from event title (for sports events like "Team A vs Team B at Venue")
            if not venue_name or str(venue_name).lower() in ['various venues', 'various', 'tbd', 'tba']:
                title_lower = title.lower()
                # Check for patterns: "at Venue", "@ Venue", "vs Team at Venue"
                if ' at ' in title:
                    # Extract venue from "Team A at Venue" or "Team A vs Team B at Venue"
                    parts = title.split(' at ')
                    if len(parts) > 1:
                        potential_venue = parts[-1].split(',')[0].strip()
                        # Validate it's not just a team name (should be longer than 3 chars and not common team words)
                        if len(potential_venue) > 3 and potential_venue.lower() not in ['stadium', 'arena', 'center', 'field', 'park']:
                            venue_name = potential_venue
                elif ' @ ' in title:
                    parts = title.split(' @ ')
                    if len(parts) > 1:
                        potential_venue = parts[-1].split(',')[0].strip()
                        if len(potential_venue) > 3:
                            venue_name = potential_venue
            
            # Final validation: Handle None venue case
            if not venue_name:
                # Check if this is a sports event - if so, use location as venue
                if 'vs' in title.lower() or 'at' in title.lower() or any(sport in title.lower() for sport in ['game', 'match', 'championship', 'tournament', 'cup', 'league']):
                    if location and location.lower() not in ['various venues', 'various', 'tbd', 'tba']:
                        venue_name = location
                    else:
                        return None
                else:
                    return None
            
            venue_lower = str(venue_name).lower().strip()
            invalid_venues = {
                'various venues', 'various', 'multiple venues', 'tbd', 'tba', 'tbc',
                'to be determined', 'to be announced', 'to be confirmed',
                'location tbd', 'venue tbd', 'see website', 'check website',
                'various locations', 'multiple locations', 'online', 'virtual',
                'streaming', 'livestream', 'live stream', 'tba venue', 'venue tba'
            }
            
            # Check if venue is invalid
            if (venue_lower in invalid_venues or 
                len(str(venue_name).strip()) < 3 or
                any(invalid in venue_lower for invalid in ['various', 'tbd', 'tba', 'tbc', 'to be', 'online', 'virtual'])):
                # For sports events, if we have location, use location as venue fallback
                # Don't add "(Venue TBD)" suffix - just use location directly to avoid noise filter
                if 'vs' in title.lower() or 'at' in title.lower() or any(sport in title.lower() for sport in ['game', 'match', 'championship', 'tournament', 'cup', 'league']):
                    # Sports events - use location as venue if no specific venue
                    if location and location.lower() not in ['various venues', 'various', 'tbd', 'tba']:
                        venue_name = location  # Use location directly, no "(Venue TBD)" suffix
                        print(f"      ℹ️ PredictHQ event '{title[:50]}' - using location as venue fallback")
                    else:
                        print(f"      ⚠️ Skipping PredictHQ event '{title[:50]}' - no specific venue found")
                        return None
                else:
                    print(f"      ⚠️ Skipping PredictHQ event '{title[:50]}' - no specific venue found")
                    return None
            
            # URL - Extract real event URLs from PredictHQ API response
            # Priority: 1) Real URLs from API, 2) PredictHQ control panel URL (valid PredictHQ link)
            url = ''
            event_id = event_data.get('id', '')
            
            # Method 1: Check entities array for actual event URLs (PredictHQ API structure)
            # These are the REAL event URLs from the API response
            entities = event_data.get('entities', [])
            if entities and isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, dict):
                        # Check for actual event URLs in entities
                        url_raw = (entity.get('url') or 
                                  entity.get('entity_url') or 
                                  entity.get('website') or
                                  entity.get('homepage'))
                        if url_raw and isinstance(url_raw, str) and url_raw.strip():
                            url = validate_and_sanitize_url(url_raw)
                            if url:
                                break
            
            # Method 2: Check root-level URL fields
            if not url:
                url_raw = (event_data.get('url') or 
                          event_data.get('entity_url') or 
                          event_data.get('website') or
                          event_data.get('homepage'))
                if url_raw and isinstance(url_raw, str) and url_raw.strip():
                    url = validate_and_sanitize_url(url_raw)
            
            # Method 3: Use PredictHQ control panel URL (valid PredictHQ link format)
            # Format: https://control.predicthq.com/search/events/{event_id}
            if not url and event_id:
                url = f"https://control.predicthq.com/search/events/{event_id}"
                # Validate the constructed URL
                url = validate_and_sanitize_url(url)
            
            # Calculate hype based on rank
            rank = event_data.get('rank', 100)
            hype_score = max(0.6, 1.0 - (rank / 150))
            
            event = ResearchEvent(
                event_name=title[:100],
                exact_date=date_display,
                exact_venue=venue_name[:80],
                location=str(location).strip() if location else 'Unknown',  # Ensure location is string
                category=self._classify_event_type(title),
                confidence_score=0.8,
                source_url=url,
                posted_by='PredictHQ',
                hype_score=hype_score,
                source='predicthq',
                start_datetime=start_dt
            )
            
            return event
            
        except Exception:
            return None
    
    def _fetch_ticketmaster_events(self, location: str, categories: List[str],
                                  start_dt: datetime, end_dt: datetime, max_results: int) -> List[ResearchEvent]:
        """Fetch events from Ticketmaster API with category filtering and comprehensive error handling"""
        if not self.ticketmaster_api_key:
            print(f"   ⚠️ Ticketmaster: No API key configured")
            return []
        
        events = []
        
        try:
            # Extract and normalize location for Ticketmaster
            # Use geocoding to handle ANY location in the world (no hardcoding needed)
            location_parts = [p.strip() for p in location.split(',')]
            city = location_parts[0] if location_parts else location
            
            # Try to extract country code from location string first (e.g., "New York, NY, US")
            country_code = None
            if len(location_parts) >= 2:
                # Check if last part looks like a country code (2 letters)
                last_part = location_parts[-1].strip().upper()
                if len(last_part) == 2 and last_part.isalpha():
                    country_code = last_part
                    # If we have 3 parts, middle might be state, city is first
                    if len(location_parts) >= 3:
                        city = location_parts[0]
                elif len(location_parts) == 2:
                    # Two parts: could be "City, State" or "City, Country"
                    city = location_parts[0]
            
            # PRIMARY METHOD: Production-grade geocoding (works for ANY country/city in the world)
            # Multiple strategies to ensure success for ANY location
            if not country_code and GEOCODING_AVAILABLE and Nominatim is not None:
                geocode_result = None
                
                # Strategy 1: Try city name first (most specific)
                if city and city.lower() != location.lower():
                    geocode_result = self._get_country_code_from_city(city)
                    if geocode_result:
                        print(f"      ✅ Found country code '{geocode_result}' for city '{city}' via geocoding")
                
                # Strategy 2: If city geocoding failed, try full location
                if not geocode_result:
                    geocode_result = self._get_country_code_from_city(location)
                    if geocode_result:
                        print(f"      ✅ Found country code '{geocode_result}' for location '{location}' via geocoding")
                
                # Strategy 3: Try with country context (dynamic - works for ANY location)
                # No hardcoding - try common country patterns dynamically
                if not geocode_result and city:
                    country_contexts = ['India', 'USA', 'United States', 'UK', 'United Kingdom', 'Canada', 'Australia']
                    for country_context in country_contexts[:4]:  # Try first 4 to avoid too many requests
                        enhanced_location = f"{city}, {country_context}"
                        geocode_result = self._get_country_code_from_city(enhanced_location)
                        if geocode_result:
                            print(f"      ✅ Found country code '{geocode_result}' for '{enhanced_location}'")
                            break
                
                if geocode_result:
                    country_code = geocode_result
                    # If location is just a country name, set city to None for country-only searches
                    if not city or city.lower() == location.lower():
                        city = None
                else:
                    print(f"      ⚠️ Geocoding failed for '{city or location}' - will try keyword search (this is OK)")
            
            if not country_code:
                print(f"      ⚠️ Could not determine country code for '{city or location}' - will use keyword search as fallback")
            
            print(f"      🔍 Ticketmaster location parsing: city='{city}', country_code='{country_code}', location='{location}'")
            
            # Format dates for Ticketmaster API
            start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Ticketmaster Segment IDs for category filtering (more effective than classificationId)
            # These filter out noise like season passes, vouchers, etc.
            category_to_segment = {
                'sports': 'KZFzniwnSyZfZ7v7nJ',  # Sports
                'music': 'KZFzniwnSyZfZ7v7nE',   # Music
                'arts': 'KZFzniwnSyZfZ7v7na',    # Arts & Theatre
                'theater': 'KZFzniwnSyZfZ7v7na', # Arts & Theatre
                'comedy': 'KZFzniwnSyZfZ7v7na',  # Arts & Theatre
                'family': 'KZFzniwnSyZfZ7v7n1',  # Family
                'conference': 'KZFzniwnSyZfZ7v7nn', # Miscellaneous
                'tech': 'KZFzniwnSyZfZ7v7nn',    # Miscellaneous
                'networking': 'KZFzniwnSyZfZ7v7nn', # Miscellaneous
                'food': 'KZFzniwnSyZfZ7v7nn',    # Miscellaneous
                'dance': 'KZFzniwnSyZfZ7v7na'     # Arts & Theatre
            }
            
            # Build search strategies with category filtering
            search_strategies = []
            
            # If specific categories selected, filter by segment to reduce noise
            if categories and 'all' not in [c.lower() for c in categories]:
                for category in categories:
                    category_lower = category.lower()
                    if category_lower in category_to_segment:
                        segment_id = category_to_segment[category_lower]
                        # Build params with country code if available, otherwise use city
                        params = {
                            'apikey': self.ticketmaster_api_key,
                            'segmentId': segment_id,  # Category filter - reduces noise significantly
                            'startDateTime': start_str,
                            'endDateTime': end_str,
                            'size': min(max_results, 50),
                            'sort': 'date,asc'
                        }
                        # Add location filter: prefer city+country, then country, then city, then keyword
                        # This ensures we get results
                        if city and country_code:
                            # Best: city + country code
                            params['city'] = city
                            params['countryCode'] = country_code
                        elif country_code:
                            # Good: country code only
                            params['countryCode'] = country_code
                        elif city:
                            # Fallback: city only
                            params['city'] = city
                        else:
                            # Last resort: keyword
                            params['keyword'] = location
                        
                        # Increase size to ensure we get enough events for the ratio
                        params['size'] = min(max_results * 3, 50)
                        
                        search_strategies.append(params)
                        
                        # ALSO try WITHOUT city filter (just country code + segment) - sometimes city filter is too restrictive
                        if city and country_code:
                            params_no_city = params.copy()
                            del params_no_city['city']  # Remove city filter
                            params_no_city['countryCode'] = country_code
                            params_no_city['size'] = min(max_results * 3, 50)
                            search_strategies.append(params_no_city)
            
            # If no category filters or "all", use general search
            if not search_strategies:
                search_strategies = []
                
                # Strategy 1: City + country code (most specific and reliable)
                if city and len(city) > 2:
                    if country_code:
                        # City + country code is most specific
                        search_strategies.append({
                            'apikey': self.ticketmaster_api_key,
                            'city': city,
                            'countryCode': country_code,
                            'startDateTime': start_str,
                            'endDateTime': end_str,
                            'size': min(max_results * 3, 50),  # Get more to ensure we meet ratio
                            'sort': 'date,asc'
                        })
                    else:
                        # City without country code (still works for major cities)
                        search_strategies.append({
                            'apikey': self.ticketmaster_api_key,
                            'city': city,
                            'startDateTime': start_str,
                            'endDateTime': end_str,
                            'size': min(max_results * 3, 50),
                            'sort': 'date,asc'
                        })
                
                # Strategy 2: Country code search (works for country names like "Philippines", "Switzerland", "Thailand")
                if country_code and len(country_code) == 2:
                    # Try without category filter first (broader search)
                    search_strategies.append({
                        'apikey': self.ticketmaster_api_key,
                        'countryCode': country_code,
                        'startDateTime': start_str,
                        'endDateTime': end_str,
                        'size': min(max_results * 3, 50),  # Get more to ensure we meet ratio
                        'sort': 'date,asc'
                    })
                
                # Strategy 3: Keyword search as fallback (works when city/country don't work)
                # ALWAYS try keyword search - it works even when geocoding fails
                search_keyword = city if city and len(city) > 2 else location
                if search_keyword and len(search_keyword) > 2:
                    # Try keyword search with date filters
                    search_strategies.append({
                        'apikey': self.ticketmaster_api_key,
                        'keyword': search_keyword,
                        'startDateTime': start_str,
                        'endDateTime': end_str,
                        'size': min(max_results * 3, 50),
                        'sort': 'date,asc'
                    })
                    # Also try keyword search WITHOUT date filters (broader search)
                    search_strategies.append({
                        'apikey': self.ticketmaster_api_key,
                        'keyword': search_keyword,
                        'size': min(max_results * 3, 50),
                        'sort': 'date,asc'
                    })
                
                # Strategy 4: Try without date filters (if date range is too restrictive)
                # This helps when Ticketmaster has events but not in the exact date range
                if country_code and len(country_code) == 2:
                    search_strategies.append({
                        'apikey': self.ticketmaster_api_key,
                        'countryCode': country_code,
                        'size': min(max_results * 3, 50),
                        'sort': 'date,asc'
                        # No date filters - get all upcoming events
                    })
            
            # ALWAYS add keyword search as final fallback (even for category searches)
            # This ensures we get results even when geocoding fails
            search_keyword = city if city and len(city) > 2 else location
            if search_keyword and len(search_keyword) > 2:
                # Check if keyword search already exists in strategies
                has_keyword = any('keyword' in s for s in search_strategies)
                if not has_keyword:
                    # Add keyword search with category if categories are specified
                    keyword_params = {
                        'apikey': self.ticketmaster_api_key,
                        'keyword': search_keyword,
                        'startDateTime': start_str,
                        'endDateTime': end_str,
                        'size': min(max_results * 3, 50),
                        'sort': 'date,asc'
                    }
                    # Add category filter if available
                    if categories and 'all' not in [c.lower() for c in categories]:
                        for category in categories:
                            category_lower = category.lower()
                            if category_lower in category_to_segment:
                                keyword_params['segmentId'] = category_to_segment[category_lower]
                                break  # Use first matching category
                    search_strategies.append(keyword_params)
            
            location_display = city if city else (country_code if country_code else location)
            print(f"      🎯 Querying Ticketmaster API for {location_display} (categories: {categories or ['all']}, strategies: {len(search_strategies)})...")
            
            for strategy_idx, params in enumerate(search_strategies):
                try:
                    # Rate limiting: Ticketmaster allows 5 requests per second
                    # Add small delay between requests to respect rate limit
                    if strategy_idx > 0:
                        time.sleep(0.25)  # 250ms delay = 4 requests/second (safe margin)
                    
                    response = requests.get(
                        "https://app.ticketmaster.com/discovery/v2/events.json",
                        params=params,
                        timeout=20
                    )
                    
                    # Check rate limit headers (per Ticketmaster API docs)
                    rate_limit = response.headers.get('Rate-Limit', 'N/A')
                    rate_limit_available = response.headers.get('Rate-Limit-Available', 'N/A')
                    rate_limit_reset = response.headers.get('Rate-Limit-Reset', 'N/A')
                    
                    if rate_limit_available != 'N/A' and int(rate_limit_available) < 100:
                        print(f"      ⚠️ Ticketmaster: Low rate limit remaining ({rate_limit_available}/{rate_limit})")
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for errors in response
                        if 'errors' in data:
                            error_msg = data['errors'].get('message', 'Unknown error')
                            print(f"      ❌ Ticketmaster API error: {error_msg}")
                            continue
                        
                        # Parse events
                        if '_embedded' in data and 'events' in data['_embedded']:
                            event_list = data['_embedded']['events']
                            print(f"      ✅ Ticketmaster returned {len(event_list)} events (Rate limit: {rate_limit_available}/{rate_limit})")
                            
                            # Parse ALL events from response (don't limit here - we'll limit later)
                            # If this strategy doesn't have date filters, we need to filter by date after parsing
                            strategy_has_date_filter = 'startDateTime' in params and 'endDateTime' in params
                            
                            for event_data in event_list:
                                try:
                                    event = self._parse_ticketmaster_event(event_data, location)
                                    if event:
                                        # If strategy doesn't have date filters, filter by date here
                                        if not strategy_has_date_filter and event.start_datetime:
                                            # Check if event falls within requested date range
                                            if start_dt <= event.start_datetime <= end_dt:
                                                events.append(event)
                                            # else: skip this event (outside date range)
                                        else:
                                            # Strategy has date filters, so Ticketmaster already filtered
                                            events.append(event)
                                except Exception as e:
                                    print(f"      ⚠️ Failed to parse Ticketmaster event: {str(e)[:50]}")
                                    continue
                            
                            # Continue trying other strategies to get more events (don't break early)
                            # This ensures we meet the ratio requirements
                            if events:
                                print(f"      ✅ Successfully parsed {len(events)} Ticketmaster events from {len(event_list)} raw events")
                                # Continue to get more events from other strategies
                                # Only break if we have plenty of events (3x target to ensure ratio)
                                if len(events) >= max_results * 3:
                                    print(f"      ✅ Got enough events ({len(events)}), stopping search")
                                    break
                            else:
                                # If no events from this strategy, continue to next
                                print(f"      ℹ️  Strategy {strategy_idx + 1} returned {len(event_list)} events but none were valid")
                                continue
                        else:
                            # Log why no events found - but continue to next strategy
                            if 'page' in data:
                                total_pages = data.get('page', {}).get('totalPages', 0)
                                total_elements = data.get('page', {}).get('totalElements', 0)
                                print(f"      ℹ️  Ticketmaster Strategy {strategy_idx + 1}: No events (totalElements: {total_elements}, pages: {total_pages})")
                                if total_elements == 0:
                                    print(f"      💡 Search params: {dict((k, v) for k, v in params.items() if k != 'apikey')}")
                                    print(f"      💡 Trying next strategy...")
                            elif '_embedded' in data:
                                print(f"      📋 Ticketmaster Strategy {strategy_idx + 1}: Response has '_embedded' but no 'events' key")
                                print(f"      💡 Trying next strategy...")
                            else:
                                print(f"      ℹ️  Ticketmaster Strategy {strategy_idx + 1}: Unexpected response structure. Keys: {list(data.keys())[:10]}")
                                print(f"      💡 Trying next strategy...")
                            # Continue to next strategy instead of breaking
                            continue
                    
                    elif response.status_code == 401:
                        print(f"      ❌ Ticketmaster: Invalid API key (401 Unauthorized)")
                        break
                    elif response.status_code == 403:
                        print(f"      ❌ Ticketmaster: API key lacks permissions (403 Forbidden)")
                        break
                    elif response.status_code == 429:
                        # Rate limit quota violation (per Ticketmaster API docs)
                        try:
                            error_data = response.json()
                            fault = error_data.get('fault', {})
                            error_msg = fault.get('faultstring', 'Rate limit quota violation')
                            error_code = fault.get('detail', {}).get('errorcode', 'policies.ratelimit.QuotaViolation')
                            print(f"      ⚠️ Ticketmaster: Rate limit exceeded (429)")
                            print(f"         Error: {error_msg}")
                            print(f"         Code: {error_code}")
                            print(f"         Reset: {rate_limit_reset}")
                        except:
                            print(f"      ⚠️ Ticketmaster: Rate limit exceeded (429) - Quota violation")
                        # Don't break, continue to next strategy but with longer delay
                        time.sleep(1)  # Wait 1 second before next request
                        continue
                    else:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('fault', {}).get('faultstring', f"HTTP {response.status_code}")
                            print(f"      ❌ Ticketmaster HTTP {response.status_code}: {error_msg}")
                        except:
                            print(f"      ❌ Ticketmaster HTTP {response.status_code}: {response.text[:100]}")
                    
                    # Continue trying all strategies to maximize event count
                    # Only skip remaining strategies if we have plenty of events
                    if len(events) >= max_results * 2:
                        print(f"      ✅ Got enough events ({len(events)}), skipping remaining strategies")
                        break
                        
                except requests.Timeout:
                    print(f"      ⏱️ Ticketmaster request timeout")
                    continue
                except requests.RequestException as e:
                    print(f"      ❌ Ticketmaster request error: {str(e)[:80]}")
                    continue
                except Exception as e:
                    print(f"      ❌ Ticketmaster error: {str(e)[:80]}")
                    continue
        
        except Exception as e:
            print(f"   ❌ Ticketmaster fetch failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return events
    
    def _parse_ticketmaster_event(self, event_data: Dict, location: str) -> Optional[ResearchEvent]:
        """Parse Ticketmaster event"""
        try:
            name = event_data.get('name', 'Unknown Event')
            dates = event_data.get('dates', {}).get('start', {})
            venues = event_data.get('_embedded', {}).get('venues', [{}])
            
            # Extract date and time - PRESERVE COMPLETE TIME RANGE from Ticketmaster API
            start_dt = None
            end_dt = None
            time_tuple = None
            complete_time_str = None
            timezone_str = None
            local_date = dates.get('localDate', '')
            local_time = dates.get('localTime', '')
            local_end_time = dates.get('localEndTime', '') or dates.get('endTime', '')
            timezone = dates.get('timezone', '') or dates.get('tz', '')
            
            if local_date:
                try:
                    # Parse Ticketmaster date format (YYYY-MM-DD)
                    start_dt = datetime.strptime(local_date, '%Y-%m-%d')
                    
                    # Parse start time if available
                    if local_time:
                        # Try parsing time using helper function first
                        time_tuple = self._parse_time_from_string(local_time)
                        
                        # If helper didn't work, try direct parsing
                        if not time_tuple:
                            try:
                                # Parse time format (HH:MM:SS or HH:MM)
                                if len(local_time) >= 5:
                                    time_parts = local_time.split(':')
                                    hour = int(time_parts[0])
                                    minute = int(time_parts[1])
                                    time_tuple = (hour, minute)
                            except:
                                pass
                        
                        # Apply time to datetime if we have it
                        if time_tuple:
                            start_dt = start_dt.replace(hour=time_tuple[0], minute=time_tuple[1])
                            # Format time as 12-hour format
                            complete_time_str = start_dt.strftime('%I:%M %p').lstrip('0')
                    
                    # Check for end time to create time range
                    if local_end_time:
                        try:
                            # Parse end time
                            if len(local_end_time) >= 5:
                                time_parts = local_end_time.split(':')
                                hour = int(time_parts[0])
                                minute = int(time_parts[1])
                                end_dt = start_dt.replace(hour=hour, minute=minute)
                                end_time_str = end_dt.strftime('%I:%M %p').lstrip('0')
                                
                                # Create complete time range
                                if complete_time_str:
                                    complete_time_str = f"{complete_time_str} - {end_time_str}"
                                else:
                                    complete_time_str = end_time_str
                        except:
                            pass
                except:
                    pass
            
            # Extract timezone if available
            if timezone:
                timezone_str = timezone
            elif dates.get('timezone'):
                timezone_str = dates.get('timezone')
            
            # Format date/time display - PRESERVE COMPLETE TIME RANGE
            if complete_time_str and start_dt:
                # Format date part
                date_part = start_dt.strftime('%m-%d-%y')
                date_str = f"{date_part} {complete_time_str}"
                if timezone_str:
                    date_str += f" {timezone_str}"
            else:
                # Fallback to original formatting
                date_str = self._format_date_time_display(start_dt, time_tuple)
            
            # Get venue with comprehensive extraction
            venue_name = 'Various Venues'
            city = location.split(',')[0].strip() if location else 'Unknown City'
            
            if venues and len(venues) > 0:
                venue = venues[0]
                venue_name = venue.get('name', 'Various Venues')
                
                # Ensure venue_name is a string (not a list)
                if isinstance(venue_name, list):
                    venue_name = ', '.join(str(v) for v in venue_name if v) if venue_name else 'Various Venues'
                venue_name = str(venue_name).strip() if venue_name else 'Various Venues'
                
                # Build complete venue string
                venue_parts = [venue_name] if venue_name != 'Various Venues' else []
                
                # Add address (handle both dict and string formats)
                address = venue.get('address', {})
                if isinstance(address, dict):
                    address = address.get('line1') or address.get('address', '')
                if address:
                    if isinstance(address, list):
                        address = ', '.join(str(a) for a in address if a)
                    venue_parts.append(str(address).strip())
                
                # Get city from venue
                venue_city = venue.get('city', {})
                if isinstance(venue_city, dict):
                    city = venue_city.get('name', city)
                elif venue_city:
                    city = str(venue_city)
                
                # Add city to venue string
                if city and city not in venue_parts:
                    venue_parts.append(city)
                
                # Combine venue parts
                if len(venue_parts) > 1:
                    venue_name = ', '.join([str(p) for p in venue_parts if p])
                elif len(venue_parts) == 1:
                    venue_name = venue_parts[0]
            
            # Get URL - ONLY use exact URLs from Ticketmaster API response
            # NO fake/constructed URLs - only use what API provides
            # Ticketmaster API provides 'url' field at root level with the actual event page URL
            source_url = ''
            
            # Method 1: Check root-level 'url' field (primary source - actual event URL from API)
            url_raw = event_data.get('url')
            if url_raw and isinstance(url_raw, str) and url_raw.strip():
                source_url = validate_and_sanitize_url(url_raw)
                if source_url:
                    print(f"         ✅ Ticketmaster URL from 'url' field: {source_url[:80]}")
            
            # Method 2: Check _links.self.href (Ticketmaster API structure - self link)
            if not source_url:
                links = event_data.get('_links', {})
                if isinstance(links, dict):
                    # Check self link
                    self_link = links.get('self', {})
                    if isinstance(self_link, dict):
                        href = self_link.get('href')
                        if href and isinstance(href, str) and href.strip():
                            source_url = validate_and_sanitize_url(href)
                            if source_url:
                                print(f"         ✅ Ticketmaster URL from '_links.self.href': {source_url[:80]}")
                    
                    # Also check attractions link (sometimes has event URL)
                    if not source_url:
                        attractions_link = links.get('attractions', [])
                        if isinstance(attractions_link, list) and attractions_link:
                            for attr in attractions_link[:1]:  # Check first attraction
                                if isinstance(attr, dict):
                                    attr_href = attr.get('href')
                                    if attr_href and isinstance(attr_href, str) and attr_href.strip():
                                        # Attraction links are usually not event pages, but check anyway
                                        if 'ticketmaster.com' in attr_href.lower():
                                            source_url = validate_and_sanitize_url(attr_href)
                                            if source_url:
                                                print(f"         ✅ Ticketmaster URL from '_links.attractions': {source_url[:80]}")
                                                break
            
            # Method 3: Check ticket URL fields (if they exist and are different from main URL)
            ticket_url_raw = (
                event_data.get('ticket_url') or
                event_data.get('ticketUrl') or
                event_data.get('ticketInfo', {}).get('url') if isinstance(event_data.get('ticketInfo'), dict) else None
            )
            ticket_url = validate_and_sanitize_url(ticket_url_raw) if ticket_url_raw else ''
            
            # Use ticket_url as source_url if we don't have a main URL
            # But only if it's a real URL from API, not constructed
            if not source_url and ticket_url:
                source_url = ticket_url
                if source_url:
                    print(f"         ✅ Ticketmaster URL from 'ticket_url' field: {source_url[:80]}")
            
            # NO Method 4 - We don't construct fake URLs like https://www.ticketmaster.com/event/{id}
            # If no real URL from API, leave it empty (will show as "NA" in frontend)
            if not source_url:
                print(f"         ⚠️ No valid URL found in Ticketmaster response for event: {name[:50]}")
                print(f"         📋 Available URL fields: url={bool(event_data.get('url'))}, _links={bool(event_data.get('_links'))}, ticket_url={bool(ticket_url_raw)}")
            
            # Get price range
            price_range = None
            if 'priceRanges' in event_data:
                price_ranges = event_data['priceRanges']
                if price_ranges:
                    min_price = price_ranges[0].get('min')
                    max_price = price_ranges[0].get('max')
                    if min_price and max_price:
                        price_range = f"${min_price:.2f} - ${max_price:.2f}"
            
            event = ResearchEvent(
                event_name=name[:100],
                exact_date=date_str,
                exact_venue=venue_name[:80],
                location=str(city).strip() if city else location,  # Ensure location is string
                category=self._classify_event_type(name),
                confidence_score=0.75,
                source_url=source_url,
                posted_by='Ticketmaster',
                hype_score=0.7,
                source='ticketmaster',
                ticket_url=ticket_url,
                price_range=price_range
            )
            
            return event
            
        except Exception as e:
            return None
    
    def _calculate_hype_score(self, title: str, venue: str) -> float:
        """Calculate hype score for event"""
        score = 0.5
        
        # Title keywords
        title_lower = title.lower()
        hype_keywords = {
            'festival': 0.2,
            'concert': 0.15,
            'championship': 0.15,
            'tournament': 0.1,
            'expo': 0.1,
            'summit': 0.1,
            'premiere': 0.1,
            'gala': 0.1
        }
        
        for keyword, bonus in hype_keywords.items():
            if keyword in title_lower:
                score += bonus
        
        # Venue quality
        venue_lower = venue.lower()
        premium_venues = ['stadium', 'arena', 'center', 'garden', 'hall']
        for v in premium_venues:
            if v in venue_lower:
                score += 0.15
                break
        
        return min(1.0, score)
    
    def _classify_event_type(self, text: str) -> str:
        """Classify event type with improved accuracy"""
        if not text:
            return 'other'
        
        text_lower = text.lower()
        
        # Priority-based classification (more specific first)
        # Music - check first to avoid false positives
        music_keywords = [
            'concert', 'music', 'dj', 'band', 'live music', 'musician', 'singer', 'song',
            'album', 'tour', 'gig', 'performance', 'symphony', 'orchestra', 'jazz', 'rock',
            'pop', 'hip hop', 'rap', 'country', 'folk', 'blues', 'reggae', 'electronic',
            'edm', 'festival', 'music festival', 'live show', 'acoustic', 'karaoke'
        ]
        if any(keyword in text_lower for keyword in music_keywords):
            return 'music'
        
        # Sports - check before other categories
        sports_keywords = [
            'sports', 'game', 'match', 'tournament', 'championship', 'cup', 'league',
            'vs ', 'versus', 'football', 'soccer', 'basketball', 'baseball', 'hockey',
            'tennis', 'golf', 'cricket', 'rugby', 'boxing', 'mma', 'ufc', 'wrestling',
            'racing', 'nascar', 'f1', 'olympics', 'stadium', 'arena', 'field', 'court'
        ]
        if any(keyword in text_lower for keyword in sports_keywords):
            return 'sports'
        
        # Theater/Arts
        theater_keywords = [
            'theater', 'theatre', 'play', 'musical', 'broadway', 'drama', 'comedy show',
            'stand-up', 'standup', 'improv', 'sketch', 'show', 'performance', 'dance',
            'ballet', 'opera', 'exhibition', 'gallery', 'art', 'museum', 'sculpture'
        ]
        if any(keyword in text_lower for keyword in theater_keywords):
            if 'comedy' in text_lower or 'stand' in text_lower:
                return 'comedy'
            return 'theater' if 'theater' in text_lower or 'theatre' in text_lower else 'arts'
        
        # Food
        food_keywords = [
            'food', 'culinary', 'wine', 'tasting', 'food festival', 'restaurant',
            'chef', 'cooking', 'cuisine', 'dining', 'beverage', 'beer', 'cocktail',
            'farmers market', 'food truck', 'brunch', 'dinner', 'lunch event'
        ]
        if any(keyword in text_lower for keyword in food_keywords):
            return 'food'
        
        # Tech/Conference
        tech_keywords = [
            'tech', 'technology', 'conference', 'summit', 'workshop', 'seminar',
            'expo', 'convention', 'forum', 'meetup', 'hackathon', 'startup',
            'innovation', 'ai', 'artificial intelligence', 'software', 'coding'
        ]
        if any(keyword in text_lower for keyword in tech_keywords):
            return 'tech'
        
        # Comedy (separate check)
        if 'comedy' in text_lower or 'stand-up' in text_lower or 'standup' in text_lower:
            return 'comedy'
        
        return 'other'
    
    def _parse_user_date(self, date_str: str) -> Optional[datetime]:
        """Parse user date string"""
        try:
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except:
                    continue
            return None
        except:
            return None
    
    def _score_events(self, events: List[ResearchEvent]) -> List[ResearchEvent]:
        """Score events based on source priority and other factors"""
        for event in events:
            base_score = event.hype_score
            
            # Source priority bonus
            source_bonus = {
                'serpapi': 0.2,
                'predicthq': 0.15,
                'ticketmaster': 0.1
            }
            
            base_score += source_bonus.get(event.source, 0)
            
            # Quality bonuses
            if event.start_datetime:
                base_score += 0.1
            
            if len(event.event_name) > 20:
                base_score += 0.05
            
            event.hype_score = min(1.0, base_score)
        
        # Sort by score
        events.sort(key=lambda x: x.hype_score, reverse=True)
        return events
    
    def _build_cache_key(self, location: str, categories: List[str], 
                        start_date: str, end_date: str) -> str:
        """Build cache key for event query"""
        categories_str = '_'.join(sorted(categories)) if categories else 'all'
        key_parts = [
            location.lower().replace(' ', '_'),
            categories_str,
            start_date,
            end_date
        ]
        key = 'events:' + ':'.join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _get_cached_events(self, cache_key: str) -> Optional[List[ResearchEvent]]:
        """Get events from Redis cache"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(f"events:v2:{cache_key}")
            if cached:
                data = json.loads(cached)
                # Convert dicts back to ResearchEvent objects
                events = []
                for item in data:
                    try:
                        # Handle datetime conversion
                        if item.get('start_datetime'):
                            item['start_datetime'] = datetime.fromisoformat(item['start_datetime'])
                        events.append(ResearchEvent(**item))
                    except:
                        continue
                return events
        except Exception as e:
            print(f"   ⚠️ Cache error: {e}")
        
        return None
    
    def _cache_events(self, cache_key: str, events: List[ResearchEvent]):
        """Cache events in Redis"""
        if not self.redis_client or not events:
            return
        
        try:
            # Convert to dict for serialization
            events_dict = []
            for event in events:
                event_dict = {
                    'event_name': event.event_name,
                    'exact_date': event.exact_date,
                    'exact_venue': event.exact_venue,
                    'location': event.location,
                    'category': event.category,
                    'confidence_score': event.confidence_score,
                    'source_url': event.source_url,
                    'posted_by': event.posted_by,
                    'hype_score': event.hype_score,
                    'source': event.source,
                    'start_datetime': event.start_datetime.isoformat() if event.start_datetime else None,
                    'ticket_url': event.ticket_url,
                    'price_range': event.price_range,
                    'event_hash': event.event_hash
                }
                events_dict.append(event_dict)
            
            # Determine TTL based on source
            source_ttl = 3600  # Default 1 hour
            if events:
                primary_source = events[0].source
                if primary_source in self.source_config:
                    source_ttl = self.source_config[primary_source]['cache_ttl']
            
            self.redis_client.setex(
                f"events:v2:{cache_key}",
                source_ttl,
                json.dumps(events_dict, default=str)
            )
            print(f"   ✅ Cached {len(events)} events (TTL: {source_ttl}s)")
            
        except Exception as e:
            print(f"   ⚠️ Cache error: {e}")
    
    def _print_discovery_summary(self, events: List[ResearchEvent], source_counts: Dict):
        """Print discovery summary"""
        print(f"\n{'='*80}")
        print(f"📈 DISCOVERY SUMMARY")
        print(f"{'='*80}")
        
        # Source performance
        print(f"📊 SOURCE PERFORMANCE:")
        for source, stats in source_counts.items():
            # Handle both 'count' and 'unique' keys for compatibility
            count = stats.get('unique', stats.get('count', 0))
            time_val = stats.get('time', 0)
            if count > 0:
                if isinstance(time_val, (int, float)):
                    print(f"   {source.upper():12} → {count:3} events | {time_val:.2f}s")
                else:
                    print(f"   {source.upper():12} → {count:3} events | {time_val}")
        
        # Event quality
        if events:
            source_dist = {}
            for event in events:
                source_dist[event.source] = source_dist.get(event.source, 0) + 1
            
            print(f"\n⭐ EVENT DISTRIBUTION:")
            for source, count in source_dist.items():
                percentage = (count / len(events)) * 100
                print(f"   {source.upper():12} → {count:3} events ({percentage:.1f}%)")
            
            avg_hype = sum(e.hype_score for e in events) / len(events)
            print(f"\n📈 QUALITY METRICS:")
            print(f"   Total Events: {len(events)}")
            print(f"   Avg Hype Score: {avg_hype:.2f}/1.0")
        
        # Top events
        if events:
            print(f"\n🏆 TOP 5 EVENTS:")
            for i, event in enumerate(events[:5], 1):
                source_icon = {
                    'serpapi': '🔍',
                    'predicthq': '📈',
                    'ticketmaster': '🎟️'
                }.get(event.source, '❓')
                
                print(f"   {i}. {source_icon} {event.event_name[:60]}...")
                print(f"      📍 {event.exact_venue[:40]} | 📅 {event.exact_date}")
                print(f"      ⭐ Score: {event.hype_score:.2f} | Source: {event.source}")
        
        print(f"{'='*80}\n")
