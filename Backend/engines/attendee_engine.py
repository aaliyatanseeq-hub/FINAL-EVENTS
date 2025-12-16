"""
PRIORITY-BASED ATTENDEE DISCOVERY ENGINE
Twitter as primary, Reddit as secondary with improved queries
"""

import re
import os
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

from services.twitter_client import TwitterClient
from services.reddit_client import RedditClient

load_dotenv()

@dataclass
class ResearchAttendee:
    username: str
    display_name: str
    bio: str
    location: str
    followers_count: int
    verified: bool
    confidence_score: float
    engagement_type: str
    post_content: str
    post_date: str
    post_link: str
    relevance_score: float
    source: str
    user_id: Optional[str] = None  # Twitter user ID for DMs
    karma: Optional[int] = None
    upvotes: Optional[int] = None

class SmartAttendeeEngine:
    def __init__(self):
        self.twitter_client = TwitterClient()
        self.reddit_client = RedditClient()
        
        # Priority configuration
        self.source_priority = [
            ('twitter', 1.2, "PRIMARY - Real-time discussions"),
            ('reddit', 1.0, "SECONDARY - Forum discussions")
        ]
        
        print("=" * 70)
        print("🚀 PRIORITY-BASED ATTENDEE DISCOVERY ENGINE")
        print("=" * 70)
        print(f"📊 SOURCE PRIORITY:")
        for source, weight, desc in self.source_priority:
            status = "✅ ACTIVE" if self._is_source_enabled(source) else "❌ INACTIVE"
            print(f"   {source.upper():10} [{weight:.1f}x] - {desc} - {status}")
        print("=" * 70)

    def discover_attendees(self, event_name: str, event_date: Optional[str], max_results: int) -> List[ResearchAttendee]:
        """Priority-based attendee discovery"""
        try:
            print(f"\n🎯 ATTENDEE DISCOVERY: '{event_name[:50]}...'")
            
            if not event_name or len(event_name.strip()) < 3:
                print("❌ ERROR: Event name too short")
                return []
            
            # Clean and optimize event name
            clean_name = self._optimize_event_name(event_name)
            print(f"   🔧 Optimized query: '{clean_name}'")
            
            all_attendees = []
            seen_users = set()
            source_stats = {}
            
            # Execute sources in priority order
            # NOTE: Reddit is on hold - only using Twitter for now
            for source_name, priority_weight, description in self.source_priority:
                # Skip Reddit as requested (on hold until authentication is fixed)
                if source_name == 'reddit':
                    print(f"   ⚠️ {source_name.upper()}: Skipped (on hold)")
                    source_stats[source_name] = {'total': 0, 'unique': 0}
                    continue
                
                if not self._is_source_enabled(source_name):
                    print(f"   ⚠️ {source_name.upper()}: Skipped")
                    source_stats[source_name] = {'total': 0, 'unique': 0}
                    continue
                
                print(f"\n   🔍 {source_name.upper()}: {description}")
                
                try:
                    if source_name == 'twitter':
                        attendees = self._fetch_twitter_attendees_priority(clean_name, event_date, max_results)
                    elif source_name == 'reddit':
                        # Reddit skipped - on hold
                        attendees = []
                    else:
                        attendees = []
                    
                    # Add with priority weighting
                    added = 0
                    for attendee in attendees:
                        user_key = f"{source_name}:{attendee.username.lower()}"
                        if user_key not in seen_users:
                            seen_users.add(user_key)
                            # Apply priority weight
                            attendee.relevance_score = min(1.0, attendee.relevance_score * priority_weight)
                            all_attendees.append(attendee)
                            added += 1
                    
                    source_stats[source_name] = {
                        'total': len(attendees),
                        'unique': added
                    }
                    
                    print(f"      ✅ Found: {len(attendees)} | Unique: {added}")
                    
                    # Don't skip Reddit - always try both sources for better coverage
                    # Only skip if we have way more than needed
                    if len(all_attendees) >= max_results * 2:
                        print(f"      ⚡ Sufficient attendees collected, continuing to secondary source for diversity")
                        # Continue to Reddit for more diverse results
                        
                except Exception as e:
                    print(f"      ❌ {source_name.upper()} failed: {str(e)[:80]}")
                    source_stats[source_name] = {'total': 0, 'unique': 0}
                    continue
            
            # Since Reddit is on hold, use only Twitter results
            # Sort by relevance score
            all_attendees.sort(key=lambda x: x.relevance_score, reverse=True)
            final_attendees = all_attendees[:max_results]
            
            # Print summary
            self._print_attendee_summary(final_attendees, source_stats)
            
            # Log usage
            if self.twitter_client.is_operational():
                stats = self.twitter_client.get_usage_stats()
                print(f"   📊 Twitter API Usage: {self.twitter_client.total_searches_used} searches")
                print(f"   📊 Remaining: {stats['searches_remaining']} searches")
            
            return final_attendees
            
        except Exception as e:
            print(f"\n❌ ATTENDEE DISCOVERY ERROR: {str(e)}")
            return []

    def _fetch_twitter_attendees_priority(self, event_name: str, event_date: Optional[str], max_results: int) -> List[ResearchAttendee]:
        """Primary source: Twitter with expanded queries to find up to 100 attendees"""
        if not self.twitter_client.is_operational():
            return []
        
        try:
            # Generate expanded priority queries (up to 15 variations)
            queries = self._generate_twitter_priority_queries(event_name, event_date)
            
            all_attendees = []
            seen_twitter_users = set()
            
            print(f"      🎯 Executing {len(queries)} priority queries (target: {max_results} attendees)...")
            
            # Use higher max_results per query to get more tweets
            # Twitter API v2 allows up to 100 tweets per request
            tweets_per_query = min(100, max_results)
            
            for i, (query_type, query) in enumerate(queries):
                # Stop if we've reached our target
                if len(all_attendees) >= max_results:
                    print(f"      ✅ Target reached: {len(all_attendees)}/{max_results} attendees found")
                    break
                
                print(f"      🔍 Query {i+1}/{len(queries)} [{query_type}]: '{query}'")
                print(f"         📊 Current: {len(all_attendees)}/{max_results} attendees")
                
                tweets = self.twitter_client.search_recent_tweets_safe(
                    query=query,
                    max_results=tweets_per_query,  # Request up to 100 tweets per query
                    tweet_fields=['author_id', 'created_at', 'text', 'public_metrics'],
                    user_fields=['username', 'name', 'verified', 'description', 'location', 'public_metrics'],
                    expansions=['author_id']
                )
                
                if not tweets or not tweets.data:
                    print(f"         ℹ️  No tweets found")
                    continue
                
                # Process tweets
                batch_attendees = self._process_twitter_response_priority(tweets, event_name)
                
                new_count = 0
                for attendee in batch_attendees:
                    if attendee.username not in seen_twitter_users:
                        seen_twitter_users.add(attendee.username)
                        all_attendees.append(attendee)
                        new_count += 1
                
                print(f"         ✅ Found {len(batch_attendees)} attendees ({new_count} new, {len(all_attendees)} total)")
            
            print(f"      📊 Twitter Total: {len(all_attendees)} unique attendees")
            return all_attendees[:max_results]
            
        except Exception as e:
            print(f"      ❌ Twitter failed: {str(e)[:80]}")
            return []

    def _generate_twitter_priority_queries(self, event_name: str, event_date: Optional[str]) -> List[Tuple[str, str]]:
        """Generate expanded Twitter queries to find up to 100 attendees"""
        queries = []
        
        # Extract keywords
        keywords = self._extract_keywords(event_name)
        
        # Priority 1: Exact matches (most relevant)
        if len(event_name) < 50:
            queries.append(('exact', f'"{event_name}"'))
            # Also try without quotes
            queries.append(('exact_no_quotes', event_name))
        
        # Priority 2: Main keywords (multiple variations)
        if len(keywords) >= 2:
            queries.append(('keywords', f'"{keywords[0]} {keywords[1]}"'))
            queries.append(('keywords_alt', f'{keywords[0]} {keywords[1]}'))
        if len(keywords) >= 1:
            queries.append(('single_keyword', keywords[0]))
        
        # Priority 3: Engagement phrases (expanded list)
        engagement_phrases = [
            'attending', 'going to', 'see you at', 'got tickets', 
            'can\'t wait', 'excited for', 'will be there', 'see you there',
            'tickets for', 'buying tickets', 'going', 'attending'
        ]
        for phrase in engagement_phrases:
            if keywords:
                queries.append(('engagement', f'{keywords[0]} {phrase}'))
                if len(keywords) >= 2:
                    queries.append(('engagement_2word', f'{keywords[0]} {keywords[1]} {phrase}'))
        
        # Priority 4: Date-specific variations
        if event_date:
            queries.append(('dated', f'{keywords[0]} {event_date}'))
            if len(keywords) >= 2:
                queries.append(('dated_2word', f'{keywords[0]} {keywords[1]} {event_date}'))
        
        # Priority 5: Generic and hashtag variations
        if keywords:
            queries.append(('generic', f'{keywords[0]} event'))
            queries.append(('hashtag', f'#{keywords[0].replace(" ", "")}'))
            if len(keywords) >= 2:
                combined = keywords[0] + keywords[1]
                queries.append(('hashtag_combined', f'#{combined.replace(" ", "")}'))
        
        # Priority 6: Location-based (if event has location context)
        # Add more variations for better coverage
        
        # Return up to 15 queries to maximize results
        return queries[:15]

    def _extract_location_from_user(self, user) -> str:
        """
        Extract location from Twitter user object - COMPLETE VERSION
        Handles all possible Twitter API response formats to get the 'Account based in' location
        """
        user_location = ""
        
        # Method 1: Direct attribute access (Twitter API v2 standard)
        try:
            if hasattr(user, 'location'):
                loc_value = getattr(user, 'location', None)
                if loc_value is not None:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in ['none', 'null', '']:
                        user_location = loc_str
                        return user_location
        except Exception as e:
            pass
        
        # Method 2: Check if user has data dict (nested structure)
        try:
            if not user_location and hasattr(user, 'data') and isinstance(user.data, dict):
                loc_value = user.data.get('location', '')
                if loc_value:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in ['none', 'null', '']:
                        user_location = loc_str
                        return user_location
        except Exception as e:
            pass
        
        # Method 3: Check if user is a dict directly
        try:
            if not user_location and isinstance(user, dict):
                loc_value = user.get('location', '')
                if loc_value:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in ['none', 'null', '']:
                        user_location = loc_str
                        return user_location
        except Exception as e:
            pass
        
        # Method 4: Try accessing via __dict__ (for object attributes)
        try:
            if not user_location and hasattr(user, '__dict__'):
                user_dict = user.__dict__
                if 'location' in user_dict:
                    loc_value = user_dict.get('location')
                    if loc_value:
                        loc_str = str(loc_value).strip()
                        if loc_str and loc_str.lower() not in ['none', 'null', '']:
                            user_location = loc_str
                            return user_location
        except Exception as e:
            pass
        
        # Method 5: Try getattr with different possible attribute names
        try:
            if not user_location:
                possible_attrs = ['location', 'user_location', 'geo_location', 'place', 'geo', 'country']
                for attr_name in possible_attrs:
                    if hasattr(user, attr_name):
                        loc_value = getattr(user, attr_name, None)
                        if loc_value:
                            loc_str = str(loc_value).strip()
                            if loc_str and loc_str.lower() not in ['none', 'null', '']:
                                user_location = loc_str
                                return user_location
        except Exception as e:
            pass
        
        # Method 6: Try to extract from bio/description if location field is empty
        try:
            if not user_location and hasattr(user, 'description'):
                description = getattr(user, 'description', None)
                if description:
                    bio = str(description)
                    user_location = self._extract_location_from_bio(bio)
                    if user_location:
                        return user_location
        except Exception as e:
            pass
        
        # Return empty string if no location found
        return ""

    def _extract_location_from_bio(self, bio_text: str) -> str:
        """Extract location information from user bio using pattern matching"""
        if not bio_text:
            return ""
        
        # Location patterns to match in bio
        location_patterns = [
            r'📍\s*([^\n📍]+)',                    # Pin emoji followed by location
            r'🗺️\s*([^\n🗺️]+)',                   # Map emoji followed by location
            r'From\s+([A-Z][a-zA-Z\s,]+)',         # "From [Location]"
            r'Location:\s*([^\n]+)',               # "Location: [Location]"
            r'Based in\s+([A-Z][a-zA-Z\s,]+)',     # "Based in [Location]"
            r'Lives in\s+([A-Z][a-zA-Z\s,]+)',     # "Lives in [Location]"
            r'Located in\s+([A-Z][a-zA-Z\s,]+)',   # "Located in [Location]"
            r'City:\s*([^\n]+)',                   # "City: [Location]"
            r'🇺🇸|🇬🇧|🇯🇵|🇮🇳|🇨🇦|🇦🇺|🇩🇪|🇫🇷|🇧🇷|🇲🇽',  # Country flags
            r'[A-Z][a-zA-Z\s]+,\s*[A-Z]{2}',       # "New York, NY" format
            r'[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s*(?:City|Town)',  # "New York City"
        ]
        
        for pattern in location_patterns:
            try:
                match = re.search(pattern, bio_text, re.IGNORECASE)
                if match:
                    if match.groups():
                        extracted = match.group(1).strip()
                    else:
                        # For flag patterns without groups
                        extracted = match.group(0).strip()
                    
                    # Clean up extracted location
                    extracted = re.sub(r'\s+', ' ', extracted)
                    extracted = extracted.rstrip(',')
                    if extracted and len(extracted) > 1:
                        return extracted
            except Exception:
                continue
        
        return ""

    def _process_twitter_response_priority(self, tweets, event_name: str) -> List[ResearchAttendee]:
        """Process Twitter response with quality filtering"""
        attendees = []
        
        if not tweets.includes or 'users' not in tweets.includes:
            return attendees
        
        users_dict = {user.id: user for user in tweets.includes['users']}
        
        for tweet in tweets.data:
            user = users_dict.get(tweet.author_id)
            if not user:
                continue
            
            # Calculate relevance with enhanced scoring
            relevance_score = self._calculate_tweet_relevance_priority(tweet.text, event_name)
            
            if relevance_score < 0.3:  # Higher threshold for primary source
                continue
            
            # Get engagement type
            engagement_type = self._detect_engagement_priority(tweet.text)
            
            # Get metrics
            followers_count = user.public_metrics.get('followers_count', 0) if hasattr(user, 'public_metrics') else 0
            
            # Skip low-engagement users for primary source
            if followers_count < 10 and engagement_type == 'mention':
                continue
            
            # EXTRACT LOCATION FROM "ABOUT THIS ACCOUNT" SECTION
            # Extract the exact "Account based in" value from Twitter API response
            location = ""
            
            # Try multiple ways to access location from API response
            # Method 1: Direct attribute access
            try:
                if hasattr(user, 'location'):
                    loc_value = getattr(user, 'location', None)
                    if loc_value is not None:
                        loc_str = str(loc_value).strip()
                        if loc_str and loc_str.lower() not in ['none', 'null', '']:
                            location = loc_str
            except Exception:
                pass
            
            # Method 2: Check if user has __dict__ with location
            if not location:
                try:
                    if hasattr(user, '__dict__'):
                        user_dict = user.__dict__
                        if 'location' in user_dict:
                            loc_value = user_dict.get('location')
                            if loc_value:
                                loc_str = str(loc_value).strip()
                                if loc_str and loc_str.lower() not in ['none', 'null', '']:
                                    location = loc_str
                except Exception:
                    pass
            
            # Method 3: Check if user is dict-like
            if not location:
                try:
                    if isinstance(user, dict):
                        loc_value = user.get('location')
                        if loc_value:
                            loc_str = str(loc_value).strip()
                            if loc_str and loc_str.lower() not in ['none', 'null', '']:
                                location = loc_str
                except Exception:
                    pass
            
            # Ensure location is never None, always string
            if location is None:
                location = ""
            
            # Add detailed debug logging for first 3 users to see what's being extracted
            if len(attendees) < 3:
                # Debug: Show all available attributes
                user_attrs = []
                try:
                    if hasattr(user, '__dict__'):
                        user_attrs = list(user.__dict__.keys())
                    elif not isinstance(user, dict):
                        user_attrs = [attr for attr in dir(user) if not attr.startswith('_')]
                except Exception:
                    pass
                
                username = getattr(user, 'username', 'unknown') if not isinstance(user, dict) else user.get('username', 'unknown')
                print(f"         📍 Location for @{username}: '{location}' (from 'About this account' section)")
                if user_attrs:
                    print(f"            Available user attributes: {user_attrs[:10]}...")  # Show first 10
                if hasattr(user, 'location'):
                    print(f"            user.location value: {repr(getattr(user, 'location', None))}")
            
            # Create attendee with extracted location
            # Safe attribute access for user object (handles both object and dict)
            if isinstance(user, dict):
                username = user.get('username', 'unknown')
                display_name = user.get('name', '')
                bio = user.get('description', '')
                verified = user.get('verified', False)
                user_id = user.get('id', None)
            else:
                username = getattr(user, 'username', 'unknown')
                display_name = getattr(user, 'name', '')
                bio = getattr(user, 'description', '')
                verified = getattr(user, 'verified', False)
                user_id = getattr(user, 'id', None)
            
            # Convert user_id to string if it exists
            user_id_str = str(user_id) if user_id is not None else None
            
            attendee = ResearchAttendee(
                username=f"@{username}",
                display_name=display_name or "",
                bio=bio or "",
                location=location,  # Extracted location
                followers_count=int(followers_count),
                verified=bool(verified),
                confidence_score=0.8,
                engagement_type=engagement_type,
                post_content=tweet.text[:120] + ("..." if len(tweet.text) > 120 else ""),
                post_date=tweet.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(tweet.created_at, 'strftime') else str(tweet.created_at),
                post_link=f"https://twitter.com/{username}/status/{tweet.id}",
                relevance_score=relevance_score,
                source='twitter',
                user_id=user_id_str  # Store user_id for DMs
            )
            
            attendees.append(attendee)
        
        return attendees

    def _calculate_tweet_relevance_priority(self, tweet_text: str, event_name: str) -> float:
        """Enhanced relevance scoring for primary source"""
        text_lower = tweet_text.lower()
        event_lower = event_name.lower()
        
        score = 0.0
        
        # 1. Exact match (highest weight)
        if event_lower in text_lower:
            score += 0.6
        
        # 2. Keyword matches with partial matching
        keywords = self._extract_keywords(event_name)
        for keyword in keywords:
            if keyword in text_lower:
                score += 0.15  # Higher per-keyword score
        
        # 3. Strong engagement signals
        strong_engagement = ['attending', 'going to', 'see you at', 'got tickets', 'bought tickets']
        for phrase in strong_engagement:
            if phrase in text_lower:
                score += 0.2
                break
        
        # 4. Medium engagement signals
        medium_engagement = ['excited for', 'can\'t wait', 'looking forward', 'hyped for']
        for phrase in medium_engagement:
            if phrase in text_lower:
                score += 0.1
                break
        
        # 5. Event context
        event_words = ['concert', 'festival', 'show', 'game', 'match', 'event']
        for word in event_words:
            if word in text_lower:
                score += 0.05
                break
        
        return min(1.0, score)

    def _detect_engagement_priority(self, tweet_text: str) -> str:
        """Enhanced engagement detection"""
        text_lower = tweet_text.lower()
        
        engagement_levels = {
            'confirmed_attendance': ['attending', 'going to', 'will be there', 'see you', 'got tickets'],
            'interested': ['interested', 'thinking about', 'considering', 'might go'],
            'excited': ['excited', 'can\'t wait', 'looking forward', 'hyped'],
            'reviewing': ['went to', 'attended', 'was amazing', 'great show'],
            'planning': ['where to', 'best seats', 'parking', 'transportation']
        }
        
        for level, phrases in engagement_levels.items():
            if any(phrase in text_lower for phrase in phrases):
                return level
        
        return 'discussing'

    def _fetch_reddit_attendees_priority(self, event_name: str, max_results: int) -> List[ResearchAttendee]:
        """Secondary source: Reddit with improved search"""
        if not self.reddit_client.is_operational():
            print(f"      ⚠️ Reddit client not operational - check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
            return []
        
        try:
            print(f"      🎯 Searching Reddit for '{event_name}'...")
            
            # Optimize search query (for logging)
            search_query = self._optimize_reddit_query(event_name)
            print(f"      🔍 Reddit query: '{search_query}'")
            
            # Request more results from Reddit to ensure we get a good mix
            # Request 1.5x max_results to account for filtering
            reddit_max = int(max_results * 1.5)
            
            # Get Reddit data - pass event_name (Reddit client handles query optimization internally)
            reddit_data = self.reddit_client.discover_event_attendees(event_name, reddit_max)
            
            if not reddit_data:
                print(f"      ℹ️  Reddit returned no results for '{event_name}'")
                print(f"      💡 Tip: Reddit search may need different keywords or the event may not be discussed on Reddit")
                return []
            
            print(f"      ✅ Reddit found {len(reddit_data)} raw results, processing...")
            
            # Convert to ResearchAttendee
            attendees = []
            for rd in reddit_data:
                try:
                    # Extract location from Reddit data (if available in API response)
                    reddit_location = ""
                    if rd.get('location'):
                        reddit_location = str(rd.get('location', '')).strip()
                    
                    # Ensure location is always a string (never None)
                    if reddit_location is None:
                        reddit_location = ""
                    
                    # Use ISO date format if available, fallback to display format
                    post_date = rd.get('post_date') or rd.get('post_date_display', 'Unknown date')
                    
                    attendee = ResearchAttendee(
                        username=rd.get('username', 'unknown'),
                        display_name=rd.get('display_name', 'Unknown'),
                        bio=rd.get('bio', ''),
                        location=reddit_location or "",  # Add location here
                        followers_count=int(rd.get('followers_count', 0)) if rd.get('followers_count') else 0,
                        verified=bool(rd.get('verified', False)),
                        confidence_score=0.7,
                        engagement_type=rd.get('engagement_type', 'mention'),
                        post_content=rd.get('post_content', ''),  # Full content (already formatted in reddit_client)
                        post_date=post_date,  # ISO format or display format
                        post_link=rd.get('post_link', ''),
                        relevance_score=float(rd.get('relevance_score', 0.5)) if rd.get('relevance_score') else 0.5,
                        source='reddit',
                        karma=rd.get('karma', 0),
                        upvotes=rd.get('upvotes', 0)
                    )
                    attendees.append(attendee)
                except Exception as e:
                    print(f"      ⚠️ Failed to convert Reddit result: {str(e)[:50]}")
                    continue
            
            print(f"      📊 Reddit Total: {len(attendees)} processed attendees")
            return attendees[:max_results]
            
        except Exception as e:
            print(f"      ❌ Reddit failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _optimize_reddit_query(self, event_name: str) -> str:
        """Optimize query for Reddit search"""
        # Extract main keywords
        keywords = self._extract_keywords(event_name)
        
        if len(keywords) >= 2:
            return f"{keywords[0]} {keywords[1]}"
        elif keywords:
            return keywords[0]
        else:
            return event_name.split()[0] if event_name.split() else event_name

    def _optimize_event_name(self, event_name: str) -> str:
        """Optimize event name for search"""
        # Remove common prefixes/suffixes
        prefixes = ['buy', 'tickets', 'for', 'the', 'event', 'dates', 'schedule']
        
        words = event_name.split()
        filtered_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in prefixes and len(word) > 2:
                filtered_words.append(word)
        
        optimized = ' '.join(filtered_words)
        
        # If too long, truncate
        if len(optimized) > 60:
            words = optimized.split()
            if len(words) > 5:
                optimized = ' '.join(words[:5])
        
        return optimized.strip()

    def _extract_keywords(self, event_name: str) -> List[str]:
        """Extract main keywords from event name"""
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were',
            'tickets', 'ticket', 'buy', 'event', 'events', 'dates', 'schedule'
        }
        
        clean_name = re.sub(r'[^\w\s]', ' ', event_name)
        words = clean_name.split()
        
        keywords = [
            word.lower() for word in words
            if word.lower() not in stop_words and len(word) > 2
        ]
        
        return keywords if keywords else [event_name.split()[0].lower()]

    def _is_source_enabled(self, source_name: str) -> bool:
        """Check if source is enabled"""
        if source_name == 'twitter':
            return self.twitter_client.is_operational()
        elif source_name == 'reddit':
            return self.reddit_client.is_operational()
        return False

    def _print_attendee_summary(self, attendees: List[ResearchAttendee], source_stats: Dict):
        """Print attendee discovery summary"""
        if not attendees:
            print(f"\n   📊 No attendees found")
            return
        
        print(f"\n{'='*60}")
        print(f"📈 ATTENDEE DISCOVERY SUMMARY")
        print(f"{'='*60}")
        
        # Source contribution - show actual mix in final results
        twitter_count = sum(1 for a in attendees if a.source == 'twitter')
        reddit_count = sum(1 for a in attendees if a.source == 'reddit')
        
        print(f"📊 SOURCE CONTRIBUTION (Final Mix):")
        if twitter_count > 0:
            percentage = (twitter_count / len(attendees) * 100)
            print(f"   🐦 TWITTER    → {twitter_count:3} ({percentage:.1f}%)")
        if reddit_count > 0:
            percentage = (reddit_count / len(attendees) * 100)
            print(f"   📱 REDDIT     → {reddit_count:3} ({percentage:.1f}%)")
        
        # Also show raw discovery stats
        print(f"\n📊 RAW DISCOVERY STATS:")
        for source, stats in source_stats.items():
            if stats['total'] > 0:
                print(f"   {source.upper():10} → {stats['total']:3} found, {stats['unique']:3} unique")
        
        # Engagement breakdown
        engagement_counts = {}
        for attendee in attendees:
            engagement_counts[attendee.engagement_type] = engagement_counts.get(attendee.engagement_type, 0) + 1
        
        print(f"\n🎯 ENGAGEMENT TYPES:")
        for eng_type, count in sorted(engagement_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(attendees) * 100)
            print(f"   {eng_type:20} → {count:3} ({percentage:.1f}%)")
        
        # Quality metrics
        avg_relevance = sum(a.relevance_score for a in attendees) / len(attendees)
        twitter_verified = sum(1 for a in attendees if a.source == 'twitter' and a.verified)
        
        print(f"\n⭐ QUALITY METRICS:")
        print(f"   Avg Relevance: {avg_relevance:.2f}/1.0")
        print(f"   Total Unique: {len(attendees)}")
        if twitter_verified > 0:
            print(f"   Verified Users: {twitter_verified}")
        
        print(f"\n🏆 TOP ATTENDEES:")
        for i, attendee in enumerate(attendees[:3], 1):
            source_icon = '🐦' if attendee.source == 'twitter' else '📱'
            print(f"   {i}. {source_icon} {attendee.username}")
            print(f"      Score: {attendee.relevance_score:.2f} | {attendee.engagement_type}")
        
        print(f"{'='*60}\n")