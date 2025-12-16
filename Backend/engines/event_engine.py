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

load_dotenv()

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
                'daily_limit': 500,
                'cache_ttl': 1800  # 30 minutes
            }
        }
        
        print("=" * 80)
        print("🚀 ENHANCED EVENT DISCOVERY ENGINE")
        print("=" * 80)
        print("📊 CONFIGURED SOURCES:")
        for source, config in self.source_config.items():
            status = "✅ ENABLED" if config['enabled'] else "❌ DISABLED"
            print(f"   {source.upper():12} [Priority: {config['priority']}] {status}")
        print("=" * 80)
    
    def _init_redis(self):
        """Initialize Redis connection for caching"""
        if not REDIS_AVAILABLE:
            print("⚠️ Redis not available (module not installed). Caching disabled.")
            self.redis_client = None
            return
            
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            print("✅ Redis cache initialized")
        except Exception as e:
            print(f"⚠️ Redis initialization failed: {e}. Caching disabled.")
            self.redis_client = None
    
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
            
            # Parse dates
            start_dt = self._parse_user_date(start_date)
            end_dt = self._parse_user_date(end_date)
            
            if not start_dt or not end_dt:
                print("❌ Invalid date format")
                return []
            
            all_events = []
            seen_hashes = set()
            source_counts = {}
            
            # Execute sources in priority order
            enabled_sources = sorted(
                [s for s in self.source_config.items() if s[1]['enabled']],
                key=lambda x: x[1]['priority']
            )
            
            for source_name, config in enabled_sources:
                print(f"\n🔍 Querying {source_name.upper()}...")
                
                try:
                    source_start = time.time()
                    
                    if source_name == 'serpapi':
                        events = self._fetch_serpapi_events(
                            location, categories, start_dt, end_dt, max_results
                        )
                    elif source_name == 'predicthq':
                        events = self._fetch_predicthq_events(
                            location, categories, start_dt, end_dt, max_results
                        )
                    elif source_name == 'ticketmaster':
                        events = self._fetch_ticketmaster_events(
                            location, start_dt, end_dt, max_results
                        )
                    else:
                        events = []
                    
                    source_time = time.time() - source_start
                    
                    # Add unique events
                    added = 0
                    for event in events:
                        if event.event_hash not in seen_hashes:
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
            
            # Score and sort events
            scored_events = self._score_events(all_events)
            final_events = scored_events[:max_results]
            
            # Cache results
            if final_events:
                self._cache_events(cache_key, final_events)
            
            # Print summary
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
            
            for i, query in enumerate(queries[:5]):  # Limit to 5 queries
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
            
            # Smart date filtering - include events even without parsed datetime if date string matches
            filtered_events = []
            filtered_out_strict = 0
            filtered_out_loose = 0
            
            for event in events:
                included = False
                # If we have parsed datetime, use strict filtering
                if event.start_datetime:
                    if start_dt <= event.start_datetime <= end_dt:
                        filtered_events.append(event)
                        included = True
                    else:
                        filtered_out_strict += 1
                # Otherwise, include if date string contains relevant month/year
                elif event.exact_date and event.exact_date != 'Date not specified':
                    # Try to extract year/month from date string for loose matching
                    date_lower = event.exact_date.lower()
                    
                    # Check for both full and abbreviated month names
                    target_months_full = [start_dt.strftime('%B').lower(), end_dt.strftime('%B').lower()]
                    target_months_abbrev = [start_dt.strftime('%b').lower(), end_dt.strftime('%b').lower()]
                    target_year = str(start_dt.year)
                    
                    # Month matching: check for full names (december, january) or abbreviations (dec, jan)
                    month_match = (any(month in date_lower for month in target_months_full) or
                                 any(month in date_lower for month in target_months_abbrev))
                    
                    # Year matching: check if year is in date string
                    year_match = target_year in date_lower
                    
                    # Also check if date is within range by extracting month number
                    # This handles cases like "Dec 7" where we can infer it's December
                    month_num_match = False
                    month_abbrev_map = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    for abbrev, month_num in month_abbrev_map.items():
                        if abbrev in date_lower:
                            # Check if this month is in our target range
                            if start_dt.month <= month_num <= end_dt.month or \
                               (start_dt.month > end_dt.month and (month_num >= start_dt.month or month_num <= end_dt.month)):
                                month_num_match = True
                                break
                    
                    # Include if month matches OR year matches OR month number is in range
                    if month_match or year_match or month_num_match:
                        filtered_events.append(event)
                        included = True
                    else:
                        filtered_out_loose += 1
                else:
                    # Include events without dates (better than nothing)
                    filtered_events.append(event)
                    included = True
                
                # Debug first few filtered events
                if not included and len(filtered_events) < 3:
                    print(f"      🔍 Filtered out: {event.event_name[:50]} | Date: {event.exact_date} | Has datetime: {event.start_datetime is not None}")
            
            if filtered_out_strict > 0 or filtered_out_loose > 0:
                print(f"      📊 Date filtering: {len(filtered_events)} included, {filtered_out_strict} filtered (strict), {filtered_out_loose} filtered (loose)")
            
            return filtered_events[:max_results]
            
        except Exception as e:
            print(f"   ❌ SerpAPI fetch failed: {str(e)[:80]}")
            return []
    
    def _generate_serpapi_queries(self, location: str, categories: List[str],
                                 start_dt: datetime, end_dt: datetime) -> List[str]:
        """Generate optimized queries for SerpAPI"""
        queries = []
        city = location.split(',')[0].strip()
        
        # Time phrases
        days_diff = (end_dt - start_dt).days
        if days_diff <= 7:
            time_phrases = ['this week', 'next 7 days']
        elif days_diff <= 30:
            time_phrases = [start_dt.strftime('%B'), 'this month']
        else:
            time_phrases = [start_dt.strftime('%B %Y')]
        
        # Base queries
        for time_phrase in time_phrases:
            queries.append(f"events in {city} {time_phrase}")
            queries.append(f"upcoming events {city} {time_phrase}")
            queries.append(f"{city} events {time_phrase}")
        
        # Category queries
        category_map = {
            'music': ['concert', 'live music', 'music festival'],
            'sports': ['sports game', 'football', 'basketball'],
            'tech': ['tech conference', 'workshop'],
            'business': ['business conference', 'networking'],
            'arts': ['art exhibition', 'theater show'],
            'food': ['food festival', 'wine tasting']
        }
        
        for cat in categories:
            if cat in category_map:
                for keyword in category_map[cat][:2]:
                    queries.append(f"{keyword} {city}")
        
        return list(dict.fromkeys(queries))[:10]
    
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
            
            # Extract date - handle multiple SerpAPI response formats
            start_dt = None
            date_display = 'Date not specified'
            
            # Try multiple date extraction methods
            date_info = event_data.get('date', {})
            start_date = None
            
            if isinstance(date_info, dict):
                # Try different date keys in order of preference
                start_date = (date_info.get('start_date') or 
                             date_info.get('when') or 
                             date_info.get('date') or
                             date_info.get('timestamp'))
            elif date_info:
                start_date = str(date_info)
            
            # Also check for direct date fields
            if not start_date:
                start_date = event_data.get('start_date') or event_data.get('when') or event_data.get('date')
            
            # Parse date with comprehensive format handling
            if start_date:
                try:
                    # ISO format with timezone
                    if isinstance(start_date, str) and 'T' in start_date:
                        try:
                            # Handle ISO format: 2025-12-15T19:00:00Z or 2025-12-15T19:00:00+00:00
                            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            date_display = start_dt.strftime('%B %d, %Y')
                        except:
                            # Try parsing just the date part
                            date_part = start_date.split('T')[0]
                            start_dt = datetime.strptime(date_part, '%Y-%m-%d')
                            date_display = start_dt.strftime('%B %d, %Y')
                    # Unix timestamp
                    elif isinstance(start_date, (int, float)):
                        start_dt = datetime.fromtimestamp(start_date)
                        date_display = start_dt.strftime('%B %d, %Y')
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
                                date_display = start_dt.strftime('%B %d, %Y')
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
                                        month = month_abbrev[month_str]
                                        day = int(day_str)
                                        # If month has passed, use next year
                                        if month < datetime.now().month or \
                                           (month == datetime.now().month and day < datetime.now().day):
                                            year = current_year + 1
                                        else:
                                            year = current_year
                                        start_dt = datetime(year, month, day)
                                        date_display = start_dt.strftime('%B %d, %Y')
                                    except:
                                        date_display = start_date
                                else:
                                    date_display = start_date
                            else:
                                date_display = start_date
                except Exception as e:
                    # Use date string as fallback
                    date_display = str(start_date) if start_date else 'Date not specified'
            
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
            
            # Extract location - get address from event_data if not already extracted
            address = event_data.get('address', '')
            if not address:
                # Try to get from venue
                venue_obj = event_data.get('venue', {})
                if isinstance(venue_obj, dict):
                    address = venue_obj.get('address', '')
            
            event_location = location  # Default to search location
            if address:
                if ',' in address:
                    event_location = address.split(',')[-1].strip()
                else:
                    event_location = address
            
            # Calculate hype score
            hype_score = self._calculate_hype_score(title, venue)
            
            event = ResearchEvent(
                event_name=title[:100],
                exact_date=date_display,
                exact_venue=venue[:80],
                location=event_location[:60],
                category=self._classify_event_type(title),
                confidence_score=0.85,
                source_url=event_data.get('link', ''),
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
        """Fetch events from PredictHQ API"""
        if not self.predicthq_api_key:
            return []
        
        events = []
        
        try:
            # Category mapping
            phq_categories = {
                'music': 'concerts',
                'sports': 'sports',
                'tech': 'conferences',
                'business': 'conferences',
                'arts': 'performing-arts',
                'festival': 'festivals'
            }
            
            # Get PredictHQ categories
            phq_cats = []
            for cat in categories:
                if cat in phq_categories:
                    phq_cats.append(phq_categories[cat])
            
            params = {
                'q': location,
                'active.gte': start_dt.strftime('%Y-%m-%d'),
                'active.lte': end_dt.strftime('%Y-%m-%d'),
                'limit': min(max_results * 2, 50),
                'sort': 'rank'
            }
            
            if phq_cats:
                params['category'] = ','.join(phq_cats[:3])
            
            headers = {
                'Authorization': f'Bearer {self.predicthq_api_key}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                'https://api.predicthq.com/v1/events/',
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                events = self._parse_predicthq_response(data, location)
                return events[:max_results]
            else:
                print(f"   ❌ PredictHQ HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ PredictHQ fetch failed: {str(e)[:80]}")
            return []
    
    def _parse_predicthq_response(self, data: Dict, location: str) -> List[ResearchEvent]:
        """Parse PredictHQ response"""
        events = []
        
        if 'results' not in data or not data['results']:
            return events
        
        for event_data in data['results']:
            try:
                event = self._parse_predicthq_event(event_data, location)
                if event:
                    events.append(event)
            except Exception:
                continue
        
        return events
    
    def _parse_predicthq_event(self, event_data: Dict, location: str) -> Optional[ResearchEvent]:
        """Parse individual PredictHQ event"""
        try:
            title = event_data.get('title', '').strip()
            if not title:
                return None
            
            # Date
            start_str = event_data.get('start', '')
            start_dt = None
            date_display = 'Date not specified'
            
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    date_display = start_dt.strftime('%B %d, %Y')
                except:
                    pass
            
            # Venue - Comprehensive extraction from PredictHQ API structure
            venue_name = 'Various Venues'
            venue_info = event_data.get('venue', {})
            
            # PredictHQ venue structure: venue.name, venue.address, venue.city, venue.state, venue.country
            if isinstance(venue_info, dict):
                # Primary: venue name
                if venue_info.get('name'):
                    venue_name = venue_info.get('name', '')
                
                # Build complete venue string with location details
                venue_parts = [venue_name] if venue_name and venue_name != 'Various Venues' else []
                
                # Add address if available
                address = venue_info.get('address') or venue_info.get('street')
                if address and address not in venue_parts:
                    venue_parts.append(address)
                
                # Add city
                city = venue_info.get('city')
                if city and city not in venue_parts:
                    venue_parts.append(city)
                
                # Add state/region
                state = venue_info.get('state') or venue_info.get('region')
                if state and state not in venue_parts:
                    venue_parts.append(state)
                
                # Combine if we have multiple parts
                if len(venue_parts) > 1:
                    venue_name = ', '.join([str(p) for p in venue_parts if p])
                elif len(venue_parts) == 1:
                    venue_name = venue_parts[0]
            
            # Fallback: Check for location fields at event level
            if venue_name == 'Various Venues' or not venue_name:
                location_info = event_data.get('location', {})
                if isinstance(location_info, dict):
                    venue_name = (location_info.get('name') or 
                                 location_info.get('venue') or 
                                 location_info.get('address') or 
                                 'Various Venues')
            
            # Final fallback
            if not venue_name or venue_name == 'Various Venues':
                # Try to extract from event title or description
                title = event_data.get('title', '')
                if ' at ' in title:
                    venue_name = title.split(' at ')[-1].split(',')[0].strip()
                elif ' @ ' in title:
                    venue_name = title.split(' @ ')[-1].split(',')[0].strip()
            
            # URL
            phq_id = event_data.get('id', '')
            url = f"https://predicthq.com/events/{phq_id}" if phq_id else ''
            
            # Calculate hype based on rank
            rank = event_data.get('rank', 100)
            hype_score = max(0.6, 1.0 - (rank / 150))
            
            event = ResearchEvent(
                event_name=title[:100],
                exact_date=date_display,
                exact_venue=venue_name[:80],
                location=location,
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
    
    def _fetch_ticketmaster_events(self, location: str, start_dt: datetime,
                                  end_dt: datetime, max_results: int) -> List[ResearchEvent]:
        """Fetch events from Ticketmaster API with comprehensive error handling"""
        if not self.ticketmaster_api_key:
            print(f"   ⚠️ Ticketmaster: No API key configured")
            return []
        
        events = []
        
        try:
            # Extract city from location
            city = location.split(',')[0].strip()
            
            # Format dates for Ticketmaster API
            start_str = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            print(f"      🎯 Querying Ticketmaster API for {city}...")
            
            # Try multiple search strategies
            search_strategies = [
                # Strategy 1: City-based search
                {
                    'apikey': self.ticketmaster_api_key,
                    'city': city,
                    'startDateTime': start_str,
                    'endDateTime': end_str,
                    'size': min(max_results, 50),
                    'sort': 'date,asc'
                },
                # Strategy 2: Country/region search if city fails
                {
                    'apikey': self.ticketmaster_api_key,
                    'countryCode': 'US',  # Default, could be made dynamic
                    'startDateTime': start_str,
                    'endDateTime': end_str,
                    'size': min(max_results, 50),
                    'sort': 'date,asc'
                }
            ]
            
            for strategy_idx, params in enumerate(search_strategies):
                try:
                    response = requests.get(
                        "https://app.ticketmaster.com/discovery/v2/events.json",
                        params=params,
                        timeout=20
                    )
                    
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
                            print(f"      ✅ Ticketmaster returned {len(event_list)} events")
                            
                            for event_data in event_list[:max_results]:
                                try:
                                    event = self._parse_ticketmaster_event(event_data, location)
                                    if event:
                                        events.append(event)
                                except Exception as e:
                                    print(f"      ⚠️ Failed to parse Ticketmaster event: {str(e)[:50]}")
                                    continue
                            
                            # If we got results, stop trying other strategies
                            if events:
                                break
                        else:
                            print(f"      ℹ️  Ticketmaster: No events in response")
                    
                    elif response.status_code == 401:
                        print(f"      ❌ Ticketmaster: Invalid API key (401 Unauthorized)")
                        break
                    elif response.status_code == 403:
                        print(f"      ❌ Ticketmaster: API key lacks permissions (403 Forbidden)")
                        break
                    else:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get('fault', {}).get('faultstring', f"HTTP {response.status_code}")
                            print(f"      ❌ Ticketmaster HTTP {response.status_code}: {error_msg}")
                        except:
                            print(f"      ❌ Ticketmaster HTTP {response.status_code}: {response.text[:100]}")
                    
                    # Only try first strategy if it works
                    if strategy_idx == 0 and events:
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
            
            # Format date
            date_str = dates.get('localDate', 'Date not specified')
            if dates.get('localTime'):
                date_str += f" {dates['localTime']}"
            
            # Get venue with comprehensive extraction
            venue_name = 'Various Venues'
            city = location.split(',')[0].strip() if location else 'Unknown City'
            
            if venues and len(venues) > 0:
                venue = venues[0]
                venue_name = venue.get('name', 'Various Venues')
                
                # Build complete venue string
                venue_parts = [venue_name] if venue_name != 'Various Venues' else []
                
                # Add address
                address = venue.get('address', {}).get('line1') or venue.get('address')
                if address:
                    venue_parts.append(address)
                
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
            
            # Get ticket URL
            ticket_url = None
            if 'url' in event_data:
                ticket_url = event_data['url']
            
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
                location=city,
                category=self._classify_event_type(name),
                confidence_score=0.75,
                source_url=ticket_url or f"https://www.ticketmaster.com/event/{event_data.get('id', '')}",
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
        """Classify event type"""
        if not text:
            return 'other'
        
        text_lower = text.lower()
        
        categories = {
            'music': ['concert', 'music', 'dj', 'band', 'live music', 'festival'],
            'sports': ['sports', 'game', 'match', 'tournament', 'championship', 'cup'],
            'tech': ['tech', 'technology', 'conference', 'summit', 'workshop'],
            'business': ['business', 'conference', 'networking', 'expo'],
            'arts': ['art', 'theater', 'exhibition', 'gallery', 'performance'],
            'food': ['food', 'culinary', 'wine', 'tasting', 'festival']
        }
        
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
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
            if stats['unique'] > 0:
                print(f"   {source.upper():12} → {stats['unique']:3} events | {stats['time']}")
        
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