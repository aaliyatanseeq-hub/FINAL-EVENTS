"""
FIXED DATE RANGE Event Discovery Engine
PROPER date filtering for ANY date range
"""

import requests
import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

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
    start_datetime: Optional[datetime] = None

class SmartEventEngine:
    def __init__(self):
        self.serp_api_key = os.getenv('SERP_API_KEY')
        try:
            print(f"🔧 Event Engine: {'✅ SerpAPI Ready' if self.serp_api_key else '❌ No Key'}")
        except UnicodeEncodeError:
            print(f"Event Engine: {'SerpAPI Ready' if self.serp_api_key else 'No Key'}")

    def discover_events(self, location: str, start_date: str, end_date: str, categories: List[str], max_results: int) -> List[ResearchEvent]:
        """PROPER DATE RANGE FILTERING: Return events within exact date range"""
        try:
            print(f"🎯 Finding events in {location} from {start_date} to {end_date}")
            
            if not self.serp_api_key:
                print("❌ SerpAPI key missing")
                return []

            # Parse user's date range
            start_dt = self._parse_user_date(start_date)
            end_dt = self._parse_user_date(end_date)
            
            if not start_dt or not end_dt:
                print("❌ Invalid date range")
                return []

            print(f"📅 ACTIVE DATE FILTER: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")

            # Build date-specific queries
            date_queries = self._build_date_specific_queries(location, categories, start_dt, end_dt)
            
            # Fetch events with date filtering
            filtered_events = self._fetch_events_with_date_filter(date_queries, start_dt, end_dt, max_results)
            
            # Score by hype
            scored_events = self._score_events_by_hype(filtered_events)
            top_events = scored_events[:max_results]
            
            print(f"✅ FOUND {len(top_events)} events in date range {start_date} to {end_date}")
            for i, event in enumerate(top_events[:3], 1):
                print(f"   {i}. {event.event_name} | {event.exact_date}")
            
            return top_events

        except Exception as e:
            print(f"❌ Event discovery failed: {e}")
            return []

    def _build_date_specific_queries(self, location: str, categories: List[str], start_dt: datetime, end_dt: datetime) -> List[str]:
        """Build queries that specifically target the date range"""
        queries = []
        
        # Generate queries for each month in range
        current = start_dt
        while current <= end_dt:
            month_year = current.strftime("%B %Y")
            month_name = current.strftime("%B")
            
            queries.extend([
                f"events {location} {month_year}",
                f"{month_name} events {location} {current.year}",
                f"upcoming events {location} {month_year}",
                f"things to do {location} {month_name} {current.year}",
            ])
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Add specific date range queries
        queries.extend([
            f"events {location} {start_dt.strftime('%B %d')} to {end_dt.strftime('%B %d %Y')}",
            f"{location} events {start_dt.year}",
            f"upcoming events {location} {start_dt.year}",
        ])
        
        # Add category-specific queries
        for category in categories:
            queries.extend([
                f"{category} events {location} {start_dt.year}",
                f"{category} {location} {start_dt.strftime('%B %Y')}",
            ])
        
        # Remove duplicates
        return list(dict.fromkeys(queries))

    def _fetch_events_with_date_filter(self, queries: List[str], start_dt: datetime, end_dt: datetime, max_results: int) -> List[ResearchEvent]:
        """Fetch events and strictly filter by date range"""
        all_events = []
        seen_events: Set[str] = set()
        
        for query in queries:
            if len(all_events) >= max_results * 2:
                break
                
            print(f"🔍 Searching: '{query}'")
            events = self._fetch_serpapi_events(query, 10)
            
            for event in events:
                # Parse event date properly
                event_start_dt = self._parse_serpapi_date(event.exact_date)
                
                # STRICT DATE FILTERING
                if event_start_dt and start_dt <= event_start_dt <= end_dt:
                    event_key = self._create_event_key(event)
                    if event_key not in seen_events:
                        seen_events.add(event_key)
                        all_events.append(event)
                        print(f"   ✅ INCLUDED: {event.event_name} - {event_start_dt.strftime('%Y-%m-%d')}")
                elif event_start_dt:
                    print(f"   ❌ EXCLUDED (date): {event.event_name} - {event_start_dt.strftime('%Y-%m-%d')}")
                else:
                    print(f"   ❌ EXCLUDED (no date): {event.event_name}")
        
        print(f"📊 After strict date filtering: {len(all_events)} events")
        return all_events

    def _parse_serpapi_date(self, date_info: Any) -> Optional[datetime]:
        """Parse SerpAPI date format and return clean datetime"""
        try:
            if not date_info:
                return None
            
            # If it's a dictionary-like string, parse it
            if isinstance(date_info, str) and date_info.startswith('{'):
                try:
                    # Clean the string and parse as JSON
                    clean_str = date_info.replace("'", '"')
                    date_dict = json.loads(clean_str)
                    
                    # Try start_date first, then when
                    date_str = date_dict.get('start_date') or date_dict.get('when')
                    if date_str:
                        return self._parse_date_string(date_str)
                except:
                    pass
            
            # If it's a simple string
            if isinstance(date_info, str):
                return self._parse_date_string(date_info)
            
            return None
            
        except Exception as e:
            print(f"⚠️ Date parsing error: {e}")
            return None

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date string formats"""
        try:
            if not date_str:
                return None
            
            # Clean the string
            clean_str = date_str.strip()
            
            # Handle "Sat, Nov 22, 8 – 11 PM" format - extract date part
            if ',' in clean_str and any(month in clean_str.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
                # Extract the date portion (before the first time indicator)
                date_part = clean_str.split(',')[1].split('–')[0].split('PM')[0].split('AM')[0].strip()
                clean_str = date_part
            
            # Month mapping
            months = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
                'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
                'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
                'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
                'dec': 12, 'december': 12
            }
            
            # Try to find month and day
            for month_name, month_num in months.items():
                if month_name in clean_str.lower():
                    # Extract day number
                    day_match = re.search(r'(\d{1,2})', clean_str)
                    if day_match:
                        day = int(day_match.group(1))
                        # Use current year or next year if month has passed
                        current_year = datetime.now().year
                        proposed_date = datetime(current_year, month_num, day)
                        
                        # If the date is in the past, assume next year
                        if proposed_date < datetime.now():
                            proposed_date = proposed_date.replace(year=current_year + 1)
                        
                        return proposed_date
            
            return None
            
        except Exception as e:
            print(f"⚠️ Date string parsing error: {e}")
            return None

    def _parse_user_date(self, date_str: str) -> Optional[datetime]:
        """Parse user input date"""
        try:
            # Handle various formats
            formats = [
                "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", 
                "%B %d, %Y", "%b %d, %Y", "%m-%d-%Y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            # If no format matches, try to interpret
            clean_date = date_str.lower().strip()
            current_year = datetime.now().year
            
            # Month mapping
            months = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
                'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
                'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
                'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
                'dec': 12, 'december': 12
            }
            
            for month_name, month_num in months.items():
                if month_name in clean_date:
                    # Extract day and year
                    day_match = re.search(r'(\d{1,2})', clean_date)
                    year_match = re.search(r'20(\d{2})', clean_date)
                    
                    day = int(day_match.group(1)) if day_match else 1
                    year = int(year_match.group()) if year_match else current_year
                    
                    return datetime(year, month_num, day)
            
            print(f"❌ Cannot parse user date: {date_str}")
            return None
            
        except Exception as e:
            print(f"❌ User date parsing error: {e}")
            return None

    def _fetch_serpapi_events(self, query: str, limit: int) -> List[ResearchEvent]:
        """Fetch events from SerpAPI with CLEAN date display"""
        try:
            params = {
                "q": query,
                "engine": "google_events",
                "api_key": self.serp_api_key,
                "hl": "en",
                "gl": "us"
            }
            
            response = requests.get("https://serpapi.com/search", params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                events = []
                
                if 'events_results' in data and data['events_results']:
                    for event_data in data['events_results'][:limit]:
                        event = self._parse_event_data_clean(event_data)
                        if event and self._is_valid_event(event):
                            events.append(event)
                    
                    print(f"   📅 Found {len(events)} events for '{query}'")
                
                return events
            else:
                print(f"   ❌ SerpAPI HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ SerpAPI fetch failed: {e}")
            return []

    def _parse_event_data_clean(self, event_data: Dict) -> ResearchEvent:
        """Parse event data with CLEAN date display"""
        try:
            title = self._safe_extract(event_data.get('title'))
            raw_date = self._safe_extract(event_data.get('date', 'Date not specified'))
            address = self._safe_extract(event_data.get('address', ''))
            link = self._safe_extract(event_data.get('link', ''))
            
            if not title or title == 'Unknown Event':
                return None
            
            # CLEAN DATE DISPLAY - Convert dictionary to readable string
            clean_date_display = self._clean_date_display(raw_date)
            clean_name = self._clean_event_name(title)
            
            event = ResearchEvent(
                event_name=clean_name,
                exact_date=clean_date_display,  # Now shows clean readable date
                exact_venue=self._extract_venue(address),
                location=self._extract_location(address),
                category=self._classify_event_type(clean_name),
                confidence_score=0.8,
                source_url=link,
                posted_by="Event Search",
                hype_score=0.5
            )
            
            return event
            
        except Exception as e:
            print(f"⚠️ Event parse error: {e}")
            return None

    def _clean_date_display(self, raw_date: Any) -> str:
        """Convert raw date to clean readable format"""
        try:
            if not raw_date:
                return "Date not specified"
            
            # If it's a dictionary-like string, extract readable date
            if isinstance(raw_date, str) and raw_date.startswith('{'):
                try:
                    clean_str = raw_date.replace("'", '"')
                    date_dict = json.loads(clean_str)
                    
                    # Prefer 'when' field as it's more descriptive
                    if date_dict.get('when'):
                        return date_dict['when']
                    elif date_dict.get('start_date'):
                        return f"Starts: {date_dict['start_date']}"
                    
                except:
                    pass
            
            # If it's already a clean string, return as is
            return str(raw_date)
            
        except Exception as e:
            print(f"⚠️ Date display cleaning error: {e}")
            return "Date information available"

    def _create_event_key(self, event: ResearchEvent) -> str:
        """Create unique key for event deduplication"""
        normalized_name = re.sub(r'[^\w\s]', '', event.event_name.lower())
        normalized_name = re.sub(r'\s+', ' ', normalized_name).strip()
        date_part = event.exact_date.split()[0] if event.exact_date else "nodate"
        return f"{normalized_name}_{date_part}"

    def _is_valid_event(self, event: ResearchEvent) -> bool:
        """Validate event before including"""
        if not event.event_name or len(event.event_name.strip()) < 3:
            return False
        generic_names = ['event', 'events', 'unknown', 'unknown event']
        if event.event_name.lower() in generic_names:
            return False
        return True

    def _score_events_by_hype(self, events: List[ResearchEvent]) -> List[ResearchEvent]:
        """Score events based on hype"""
        scored_events = []
        for event in events:
            hype_score = self._calculate_hype_score(event)
            event.hype_score = hype_score
            scored_events.append(event)
        scored_events.sort(key=lambda x: x.hype_score, reverse=True)
        return scored_events

    def _calculate_hype_score(self, event: ResearchEvent) -> float:
        """Calculate hype score"""
        score = 0.0
        name_lower = event.event_name.lower()
        hype_keywords = [
            'festival', 'concert', 'championship', 'tournament', 'expo',
            'summit', 'conference', 'awards', 'gala', 'premiere'
        ]
        for keyword in hype_keywords:
            if keyword in name_lower:
                score += 0.1
        venue_lower = event.exact_venue.lower()
        prestigious_venues = ['stadium', 'arena', 'center', 'garden', 'hall']
        for venue in prestigious_venues:
            if venue in venue_lower:
                score += 0.15
        category_weights = {
            'music': 0.3, 'festival': 0.4, 'sports': 0.35,
            'conference': 0.2, 'arts': 0.25, 'food': 0.15
        }
        score += category_weights.get(event.category, 0.1)
        return min(1.0, score)

    def _clean_event_name(self, title: str) -> str:
        """Clean event name"""
        if not title:
            return "Event"
        patterns_to_remove = [
            r'\s+at\s+.+$', r'\s+in\s+.+$', r'\s*-\s*.+$',
            r'\s*\|.*$', r'\s*@\s*.+$'
        ]
        clean_name = title
        for pattern in patterns_to_remove:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        return clean_name if clean_name else title

    def _safe_extract(self, field):
        if isinstance(field, list):
            return field[0] if field else ""
        return str(field) if field else ""

    def _extract_venue(self, address: str) -> str:
        if not address:
            return "Various Venues"
        venue = address.split(',')[0].strip()
        return venue if len(venue) > 3 else "Various Venues"

    def _extract_location(self, address: str) -> str:
        if not address:
            return "Location not specified"
        parts = address.split(',')
        return parts[-1].strip() if len(parts) > 1 else address

    def _classify_event_type(self, text: str) -> str:
        if not text:
            return 'other'
        text_lower = text.lower()
        categories = {
            'music': ['concert', 'music', 'dj', 'band', 'live music'],
            'sports': ['sports', 'game', 'match', 'tournament'],
            'arts': ['art', 'theater', 'exhibition', 'gallery'],
            'food': ['food', 'drink', 'culinary', 'wine'],
            'festival': ['festival', 'cultural'],
            'conference': ['conference', 'summit', 'workshop'],
        }
        for category, keywords in categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        return 'other'