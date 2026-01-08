"""
PRIORITY-BASED ATTENDEE DISCOVERY ENGINE
Twitter as primary, Reddit as secondary with improved queries
"""

import re
import os
import concurrent.futures
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
from collections import Counter

from services.twitter_client import TwitterClient
from services.reddit_client import RedditClient
from engines.semantic_matcher import get_semantic_matcher
from config.config_loader import (
    COUNTRY_KEYWORDS, SPORTS_VENUES, COUNTRY_NAMES,
    ENGAGEMENT_PHRASES, STRONG_ENGAGEMENT, MEDIUM_ENGAGEMENT,
    STOP_WORDS, PREFIXES, INVALID_VALUES, INVALID_PATTERNS,
    LOCATION_KEYWORDS, LOCATION_PATTERNS, BIO_NONSENSE_PATTERNS
)

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
        # Initialize semantic matcher for ML-based relevance
        self.semantic_matcher = get_semantic_matcher()
        
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
                
                # Check rate limit BEFORE making the search (prevent unnecessary API calls)
                if hasattr(self.twitter_client, 'rate_limit_remaining') and self.twitter_client.rate_limit_remaining <= 0:
                    print(f"      ⚠️ Rate limit exhausted before query {i+1}. Stopping to preserve quota.")
                    print(f"      📊 Found {len(all_attendees)} attendees before rate limit")
                    break
                
                print(f"      🔍 Query {i+1}/{len(queries)} [{query_type}]: '{query}'")
                print(f"         📊 Current: {len(all_attendees)}/{max_results} attendees")
                
                tweets = self.twitter_client.search_recent_tweets_safe(
                    query=query,
                    max_results=tweets_per_query,  # Request up to 100 tweets per query
                    # Request place/geo data for country-level location inference
                    tweet_fields=['author_id', 'created_at', 'text', 'public_metrics', 'geo'],
                    # Request all available user fields from Twitter API v2
                    # Note: "About this account" section data (like "Account based in", "Date joined", etc.)
                    # is NOT available via API - only user-defined location field is available
                    user_fields=['username', 'name', 'verified', 'description', 'location', 'public_metrics', 'created_at'],
                    expansions=['author_id', 'geo.place_id'],  # Include place data if available
                    place_fields=['country', 'country_code', 'name']  # Request place fields for country inference
                )
                
                # CRITICAL: Check for rate limit errors IMMEDIATELY after search
                # Method 1: Check if response is a rate limit error dict
                if isinstance(tweets, dict):
                    error_type = tweets.get('error')
                    if error_type in ['rate_limit', 'rate_limit_429']:
                        print(f"         ⚠️ Rate limit hit (detected via error dict). Stopping queries to preserve quota.")
                        print(f"         📊 Found {len(all_attendees)} attendees before rate limit")
                        break
                
                # Method 2: Check if client's quota is exhausted (direct check)
                # This catches cases where rate_limit_remaining was set to 0
                if hasattr(self.twitter_client, 'rate_limit_remaining') and self.twitter_client.rate_limit_remaining <= 0:
                    print(f"         ⚠️ Rate limit reached (quota exhausted: {self.twitter_client.rate_limit_remaining}). Stopping queries.")
                    print(f"         📊 Found {len(all_attendees)} attendees before rate limit")
                    break
                
                # Also check if tweets is None (which can happen on errors)
                if tweets is None:
                    # Double-check rate limit even if tweets is None
                    if hasattr(self.twitter_client, 'rate_limit_remaining') and self.twitter_client.rate_limit_remaining <= 0:
                        print(f"         ⚠️ Rate limit reached (quota exhausted). Stopping queries.")
                        print(f"         📊 Found {len(all_attendees)} attendees before rate limit")
                        break
                    print(f"         ℹ️  No tweets found")
                    continue
                
                # Check if tweets has data attribute (normal response)
                if not hasattr(tweets, 'data') or not tweets.data:
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
        
        # Priority 3: Engagement phrases (loaded from config)
        for phrase in ENGAGEMENT_PHRASES:
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
        
        # For basic tier (100-500 requests), limit to 5 queries to preserve quota
        # Only use more queries if we have plenty of quota remaining
        max_queries = 5  # Conservative limit for basic tier
        return queries[:max_queries]

    def _is_valid_location(self, location_str: str) -> bool:
        """
        STRICT validation: Only accept strings that clearly indicate a real geographic location.
        Rejects pronouns, personality types, random phrases, fictional places, social media handles, etc.
        """
        if not location_str or len(location_str.strip()) < 2:
            return False
        
        loc_lower = location_str.lower().strip()
        loc_original = location_str.strip()
        
        # ===== INVALID PATTERNS (reject immediately) =====
        invalid_patterns = [
            # Pronouns and identity markers
            r'\b(she|he|they|ze|xe)\s*[/|]\s*(her|him|them|zir|hir)\b',  # "she/her", "he/him"
            r'\b(any|all)\s+pronouns?\b',  # "any pronouns"
            r'\b(he|she|they|it)\s+(is|was|will|can|should)\b',  # "he is", "she was"
            r'\b\d+\s*(years?|yrs?|yo)\s*(old|of age)\b',  # Age: "17 years old", "22 yo"
            r'\b\d+\s*(losing|gaining|finding|searching|making)\b',  # "17 losing", "22 making"
            r'\b(mun|mun is|is mun)\s+\d+\b',  # "Mun is 17"
            
            # Personality types and MBTI
            r'\b(infj|intj|enfp|entp|isfj|istj|esfp|estp|infp|intp|enfj|entj|isfp|istp|esfj|estj)[-a]?\b',  # MBTI types
            r'\b[a-z]{4}[-a]\b',  # 4-letter codes like "INFJ-A"
            
            # Social media and handles
            r'@\w+',  # "@username"
            r'\b(ig|insta|tiktok|yt|youtube|snap|twitter|fb|facebook)\s*:?\s*@?\w+',  # Social media handles
            r'/\s*@\w+',  # "/ @username"
            r'@\w+\s*/\s*@\w+',  # "@user1 / @user2"
            
            # Random phrases and quotes (but allow if it's a valid location with quotes)
            r'^["\']\s*[^"\']*\s*["\']$',  # Entirely quoted text: '( ´ཀ` )', "text"
            r'\([^)]*[´ཀ˘³♥🧘🏼💗]\s*[^)]*\)',  # Parentheses with emoji/special chars: "( ´ཀ` )", "( ˘ ³˘)"
            r'\b(anywhere|everywhere|nowhere|somewhere)\s+(and|or)\s+\w+\b',  # "anywhere and everywhere"
            r'\b(kill|make|find|get|go|come|be|do)\s+\w+\s+\w+\b',  # Action phrases: "kill joys", "make noise"
            r'\b(future|past|present|now|then)\s+(is|was|will|gonna|going)\b',  # "Future's gonna be okay"
            r'\b(one|a|an|the)\s+(and|only|legend|way|thing)\s*[=:]\s*\w+\b',  # "The one and only = jm"
            r'^(my|your|his|her|their|our)\s+(father|mother|father\'s|mother\'s)\s+(house|home)\b',  # "My Father's House"
            
            # Fictional and non-geographic places
            r'\b(mars|jupiter|venus|saturn|neptune|pluto|asgard|purgatory|hell|heaven|galaxy|universe|earth|moon)\b',
            r'\b(hogwarts|narnia|middle earth|westeros|hogwarts|gotham|metropolis)\b',
            r'\b(terra australis|atlantis|el dorado|shangri-la)\b',
            r'\b(the moon|on mars|in space|outer space)\b',
            
            # Crypto/blockchain references
            r'\b(onchain|on chain|blockchain|crypto|nft|web3|defi)\b',
            r'⛓️',  # Chain emoji
            
            # Emoji-heavy or emoji-only (but allow single flag emoji with location text)
            r'^[🔬🦊✨🌟💫⭐💗💥🍰🐮🌳🪷🦋🦊🐣🦌🍎🧘🏼]+$',  # Just non-location emojis
            r'^[🔬🦊✨🌟💫⭐💗💥🍰🐮🌳🪷🦋🦊🐣🦌🍎🧘🏼]{2,}$',  # Multiple non-location emojis only
            r'[🔬🦊✨🌟💫⭐💗💥🍰🐮🌳🪷🦋🦊🐣🦌🍎🧘🏼]{3,}',  # 3+ non-location emojis (too many)
            
            # Numbers and codes
            r'^\d+$',  # Just numbers: "2708"
            r'^\d+\.\d+\s*[°]\s*[NS]\s*,\s*\d+\.\d+\s*[°]\s*[EW]\b',  # Coordinates: "38.83496° N, 77.01289° W"
            r'^ot\d+',  # "ot8", "ot4" (fandom terms)
            r'^\w{1,3}\s*$',  # Very short codes: "Pa", "PLG", "FUB"
            
            # Non-English phrases that aren't locations
            r'お誘いはDMまで、お願いします',  # Japanese: "Please DM for invitations"
            r'[お-ん]{5,}',  # Long Japanese text (likely not a location name)
            r'[ก-๙]{5,}',  # Long Thai text (likely not a location name)
            
            # Special characters and symbols
            r'^[★☆•→|]+$',  # Just symbols
            r'[★☆•→|]{2,}',  # Multiple symbols
            r'^\s*[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]+\s*$',  # Emoji-only
            
            # Generic phrases
            r'\b(wherever|where|when|what|who|how)\s+\w+\s+(are|is|was|will)\b',  # "wherever you are"
            r'\b(parts|unknown|moving|to\.\.\.)\b',  # "parts unknown", "Moving to...."
            r'\b(free|track|world|house|father|mother|making|okay)\b$',  # Standalone words that aren't locations
        ]
        
        # Check against invalid patterns
        for pattern in INVALID_PATTERNS:
            if re.search(pattern, loc_lower, re.IGNORECASE):
                return False
        
        # Must contain at least one letter (not just numbers/symbols/emojis)
        if not re.search(r'[a-zA-Z\u00C0-\u017F\u0400-\u04FF\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', location_str):
            return False
        
        # Too short or too long
        if len(location_str) < 3 or len(location_str) > 100:
            return False
        
        # ===== POSITIVE INDICATORS (must match at least one) =====
        
        # 1. Standard location format: "City, State" or "City, Country"
        if re.search(r'^[A-Z][a-zA-Z\s]+,\s*([A-Z]{2}|[A-Z][a-zA-Z\s]+)$', loc_original):
            return True
        
        # 2. Contains location keywords (loaded from config)
        for pattern in LOCATION_KEYWORDS:
            if re.search(pattern, loc_lower):
                return True
        
        # 3. Known countries and major cities (from COUNTRY_KEYWORDS)
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                # Match whole word or at start/end with comma
                if re.search(r'\b' + re.escape(keyword) + r'\b', loc_lower):
                    if len(keyword) >= 4:  # Only longer keywords to avoid false positives
                        return True
        
        # 4. Two-word capitalized pattern (likely city name): "New York", "Los Angeles"
        if re.search(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', loc_original):
            # But reject if it's a known phrase
            if not re.search(r'\b(father|mother|making|okay|track|world|house)\b', loc_lower):
                return True
        
        # 5. Single capitalized word that's a known country/city
        if re.search(r'^[A-Z][a-z]+$', loc_original):
            # Check if it's in our known locations
            for country_code, keywords in COUNTRY_KEYWORDS.items():
                for keyword in keywords:
                    if loc_lower == keyword.lower() and len(keyword) >= 4:
                        return True
        
        # 6. Contains comma (likely "City, State" or "City, Country")
        if ',' in location_str:
            # Remove emojis for validation but keep original
            location_clean = re.sub(r'[🔬🦊📍🗺️✨🌟💫⭐💗💥🍰🐮🌳🪷🦋🦊🐣🦌🍎🧘🏼🇺🇸🇬🇧🇯🇵🇮🇳🇨🇦🇦🇺🇩🇪🇫🇷🇧🇷🇲🇽]', '', location_str).strip()
            parts = [p.strip() for p in location_clean.split(',')]
            if len(parts) == 2:
                # Both parts should have letters and reasonable length
                if all(len(p) >= 2 and re.search(r'[a-zA-Z\u00C0-\u017F\u0400-\u04FF\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', p) for p in parts):
                    return True
        
        # 7. Non-English location names (Japanese, Chinese, Thai, etc.) - but must look like a location
        # Check for common location characters in other scripts
        if re.search(r'[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF]', location_str):  # Chinese/Japanese
            # Must be reasonable length and not contain invitation phrases
            if 2 <= len(location_str) <= 50 and not re.search(r'(誘|DM|お願い|まで)', location_str):
                # Should look like a location (not a sentence)
                if not re.search(r'[。、！？]', location_str):  # No sentence punctuation
                    return True
        
        if re.search(r'[\u0E00-\u0E7F]', location_str):  # Thai
            # Must be reasonable length and not contain invitation phrases
            if 2 <= len(location_str) <= 50:
                # Should look like a location (not a sentence)
                if not re.search(r'[。、！？]', location_str):  # No sentence punctuation
                    return True
        
        # 8. Single capitalized word that matches known location patterns
        # Check if it's a proper noun (starts with capital) and matches location-like patterns
        if re.search(r'^[A-Z][a-z]+$', loc_original):
            # Must be at least 4 characters and not match invalid patterns
            if len(loc_original) >= 4:
                # Check if it's in COUNTRY_KEYWORDS (dynamic, not hardcoded)
                for country_code, keywords in COUNTRY_KEYWORDS.items():
                    for keyword in keywords:
                        if loc_lower == keyword.lower() and len(keyword) >= 4:
                            return True
        
        # 9. Locations with apostrophes (like "St.John's", "O'Brien") - pattern-based
        if "'" in location_str or "'" in location_str:
            # Check if it looks like a location name with apostrophe
            # Pattern matches both straight and curly apostrophes
            apostrophe_pattern = r"^[A-Z][a-zA-Z\s]*[''][a-zA-Z\s]+$"
            if re.search(apostrophe_pattern, loc_original):
                # Should not be a phrase
                if not re.search(r'\b(is|was|will|gonna|making|okay|father|mother)\b', loc_lower):
                    # Should have location-like structure (capitalized words)
                    if re.search(r'^[A-Z][a-z]+', loc_original):
                        return True
        
        # ===== DEFAULT: REJECT (strict mode) =====
        # Only accept if we have positive indicators above
        return False
    
    def _extract_location_from_user(self, user) -> str:
        """
        Extract EXACT location string from Twitter user object - ONLY "Account based in" field
        Returns the exact location string ONLY if it's a valid location (filters out pronouns, random text, etc.)
        """
        # Invalid values to skip (loaded from config)
        invalid_values = INVALID_VALUES
        
        # Method 1: Direct attribute access (tweepy User object - most common)
        try:
            if hasattr(user, 'location'):
                loc_value = user.location
                if loc_value is not None:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in invalid_values:
                        # Validate it's actually a location
                        if self._is_valid_location(loc_str):
                            return loc_str
        except (AttributeError, TypeError, Exception) as e:
            pass
        
        # Method 2: Check if user is a dict directly (raw API response)
        try:
            if isinstance(user, dict):
                loc_value = user.get('location')
                if loc_value is not None:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in invalid_values:
                        if self._is_valid_location(loc_str):
                            return loc_str
        except Exception as e:
            pass
        
        # Method 3: Try getattr (alternative access method)
        try:
            loc_value = getattr(user, 'location', None)
            if loc_value is not None:
                loc_str = str(loc_value).strip()
                if loc_str and loc_str.lower() not in invalid_values:
                    if self._is_valid_location(loc_str):
                        return loc_str
        except Exception as e:
            pass
        
        # Method 4: Check if user has data dict (nested structure)
        try:
            # Only check for .data attribute if user is not a dict
            if not isinstance(user, dict) and hasattr(user, 'data'):
                user_data = getattr(user, 'data', None)
                if isinstance(user_data, dict):
                    loc_value = user_data.get('location')
                    if loc_value is not None:
                        loc_str = str(loc_value).strip()
                        if loc_str and loc_str.lower() not in invalid_values:
                            if self._is_valid_location(loc_str):
                                return loc_str
        except Exception as e:
            pass
        
        # Method 5: Try accessing via __dict__ (for object attributes)
        try:
            if hasattr(user, '__dict__'):
                user_dict = user.__dict__
                if 'location' in user_dict:
                    loc_value = user_dict.get('location')
                    if loc_value is not None:
                        loc_str = str(loc_value).strip()
                        if loc_str and loc_str.lower() not in invalid_values:
                            if self._is_valid_location(loc_str):
                                return loc_str
        except Exception as e:
            pass
        
        # Return empty string if location field is not available, empty, or invalid
        return ""

    def _extract_location_from_bio(self, bio_text: str) -> str:
        """Extract location information from user bio using pattern matching"""
        if not bio_text:
            return ""
        
        # Location patterns to match in bio (loaded from config)
        for pattern in LOCATION_PATTERNS:
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
    
    def _extract_clean_display_name(self, raw_display_name: str, username: str) -> str:
        """
        Extract clean display name from "About this account" section.
        Filters out bio-like nonsense (pronouns, random phrases) and uses username as fallback.
        
        The "About this account" section shows:
        - Username (most reliable)
        - Date joined
        - Account based in
        - Username changes
        - Last on
        - Connected via
        
        We prefer username over display name if display name contains bio-like patterns.
        """
        if not raw_display_name or not raw_display_name.strip():
            # If no display name, use username (from "About this account")
            return username
        
        display_name = raw_display_name.strip()
        
        # Patterns that indicate bio-like nonsense (not a real name) - loaded from config
        # Check if display name matches any bio-like nonsense patterns
        for pattern in BIO_NONSENSE_PATTERNS:
            if re.search(pattern, display_name, re.IGNORECASE):
                # Display name contains bio-like nonsense, use username instead
                # Username is from "About this account" section and is more reliable
                return username
        
        # Check if display name is too short or looks like a handle
        if len(display_name) < 2:
            return username
        
        # Check if display name is just numbers or special characters
        if re.match(r'^[\d\s\W]+$', display_name):
            return username
        
        # Display name looks clean, use it
        # But clean up any leading/trailing separators that might have been missed
        cleaned = re.sub(r'^\s*[|•→]\s*|\s*[|•→]\s*$', '', display_name)
        cleaned = cleaned.strip()
        
        # If cleaning removed everything, use username
        if not cleaned:
            return username
        
        return cleaned
    
    def _extract_safe_location(self, user, tweet, event_name: str, places_dict: Optional[Dict] = None) -> str:
        """
        Extract location using practical, safer approach:
        1. Use tweet place.country/country_code when available (coarse signal)
        2. Infer country from public signals (keywords, venues, timezone from posting times)
        3. Store only country-level data, not precise coordinates
        
        Privacy: Only uses public data and optional tweet geo.
        Purpose: Infer approximate country for personalization/analytics, not tracking individuals.
        """
        location_signals = []
        
        # Method 1: Extract country from tweet place data (if available)
        country_from_place = self._extract_country_from_tweet_place(tweet, places_dict)
        if country_from_place:
            location_signals.append(('place', country_from_place))
        
        # Method 2: Extract from user location field (user-defined, may not be accurate)
        user_location = self._extract_user_location_field(user)
        if user_location:
            country_from_user = self._infer_country_from_text(user_location)
            if country_from_user:
                location_signals.append(('user_field', country_from_user))
        
        # Method 3: Infer from tweet content (keywords, venues, teams)
        country_from_content = self._infer_country_from_tweet_content(tweet.text, event_name)
        if country_from_content:
            location_signals.append(('content', country_from_content))
        
        # Method 4: Infer from posting timezone (coarse signal)
        country_from_timezone = self._infer_country_from_posting_time(tweet.created_at)
        if country_from_timezone:
            location_signals.append(('timezone', country_from_timezone))
        
        # Combine signals: prioritize place > user_field > content > timezone
        if location_signals:
            # Get most reliable signal (place is most reliable)
            priority_order = ['place', 'user_field', 'content', 'timezone']
            for priority in priority_order:
                for signal_type, country in location_signals:
                    if signal_type == priority:
                        # Return country name, not code (more user-friendly)
                        return self._get_country_name(country)
            
            # If no priority match, use first signal
            _, country = location_signals[0]
            return self._get_country_name(country)
        
        return ""
    
    def _extract_country_from_tweet_place(self, tweet, places_dict: Optional[Dict] = None) -> Optional[str]:
        """Extract country from tweet place data (coarse signal for relevance)"""
        try:
            # Check if tweet has geo/place_id reference
            place_id = None
            if hasattr(tweet, 'geo') and tweet.geo:
                if isinstance(tweet.geo, dict):
                    place_id = tweet.geo.get('place_id')
                elif hasattr(tweet.geo, 'place_id'):
                    place_id = tweet.geo.place_id
            
            # If we have place_id and places_dict, look up the place
            if place_id and places_dict:
                place_obj = places_dict.get(place_id)
                if place_obj:
                    country_code = None
                    if hasattr(place_obj, 'country_code'):
                        country_code = place_obj.country_code
                    elif isinstance(place_obj, dict):
                        country_code = place_obj.get('country_code') or place_obj.get('country')
                    
                    if country_code:
                        return country_code.upper()
            
            # Check if place is directly on tweet
            if hasattr(tweet, 'place') and tweet.place:
                place_obj = tweet.place
                # Try to get country code
                country_code = None
                if hasattr(place_obj, 'country_code'):
                    country_code = place_obj.country_code
                elif isinstance(place_obj, dict):
                    country_code = place_obj.get('country_code') or place_obj.get('country')
                
                if country_code:
                    return country_code.upper()
        except Exception:
            pass
        
        return None
    
    def _extract_user_location_field(self, user) -> Optional[str]:
        """Extract user-defined location field (may not be accurate)"""
        try:
            if hasattr(user, 'location'):
                loc_value = getattr(user, 'location', None)
                if loc_value:
                    loc_str = str(loc_value).strip()
                    if loc_str and loc_str.lower() not in ['none', 'null', '']:
                        return loc_str
        except Exception:
            pass
        
        return None
    
    def _infer_country_from_text(self, text: str) -> Optional[str]:
        """Infer country from text using public keywords (low-risk signal)"""
        if not text:
            return None
        
        text_lower = text.lower()
        
        # Check against country keywords
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return country_code
        
        return None
    
    def _infer_country_from_tweet_content(self, tweet_text: str, event_name: str) -> Optional[str]:
        """Infer country from tweet content (venues, teams, keywords)"""
        if not tweet_text:
            return None
        
        combined_text = (tweet_text + " " + event_name).lower()
        country_scores = Counter()
        
        # Check country keywords
        for country_code, keywords in COUNTRY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined_text:
                    country_scores[country_code] += 1
        
        # Check sports venues
        for country_code, venues in SPORTS_VENUES.items():
            for venue in venues:
                if venue in combined_text:
                    country_scores[country_code] += 2  # Venues are stronger signal
        
        if country_scores:
            # Return most common country
            return country_scores.most_common(1)[0][0]
        
        return None
    
    def _infer_country_from_posting_time(self, created_at) -> Optional[str]:
        """Infer approximate country from posting time (coarse timezone signal)"""
        try:
            if not created_at:
                return None
            
            # Parse tweet creation time
            if isinstance(created_at, str):
                tweet_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif hasattr(created_at, 'replace'):
                tweet_time = created_at.replace(tzinfo=timezone.utc)
            else:
                return None
            
            # Get hour in UTC
            hour_utc = tweet_time.hour
            
            # Coarse timezone inference (very approximate)
            # This is a weak signal, only use if other signals fail
            # US: 0-8 UTC (evening/night in US)
            # EU: 6-14 UTC (morning/afternoon in EU)
            # Asia: 14-22 UTC (evening/night in Asia)
            
            if 0 <= hour_utc <= 8:
                return 'US'  # Likely US evening/night
            elif 6 <= hour_utc <= 14:
                return 'GB'  # Likely EU morning/afternoon (using GB as proxy)
            elif 14 <= hour_utc <= 22:
                return 'JP'  # Likely Asia evening/night (using JP as proxy)
            
        except Exception:
            pass
        
        return None
    
    def _get_country_name(self, country_code: str) -> str:
        """Convert country code to country name (more user-friendly) - loaded from config"""
        return COUNTRY_NAMES.get(country_code.upper(), country_code.upper())

    def _process_twitter_response_priority(self, tweets, event_name: str) -> List[ResearchAttendee]:
        """Process Twitter response with quality filtering"""
        attendees = []
        
        if not tweets.includes or 'users' not in tweets.includes:
            return attendees
        
        users_dict = {user.id: user for user in tweets.includes['users']}
        
        # Build places dict if available (for country extraction)
        places_dict = {}
        if tweets.includes and 'places' in tweets.includes:
            for place in tweets.includes['places']:
                if hasattr(place, 'id'):
                    places_dict[place.id] = place
                elif isinstance(place, dict):
                    places_dict[place.get('id')] = place
        
        for tweet in tweets.data:
            user = users_dict.get(tweet.author_id)
            if not user:
                continue
            
            # Calculate relevance using ML-based semantic matching
            # This understands event context, not just keywords
            relevance_score = self._calculate_semantic_relevance(tweet.text, event_name)
            
            # Lower threshold for ML-based semantic matching (understands context better)
            # ML can find relevant tweets even with lower similarity scores
            if relevance_score < 0.2:  # Lower threshold - ML understands context
                continue
            
            # Get engagement type
            engagement_type = self._detect_engagement_priority(tweet.text)
            
            # Get metrics
            followers_count = user.public_metrics.get('followers_count', 0) if hasattr(user, 'public_metrics') else 0
            
            # Skip low-engagement users for primary source
            if followers_count < 10 and engagement_type == 'mention':
                continue
            
            # LOCATION EXTRACTION: Get EXACT location from user's "Account based in" field
            # Only use the exact location string the user entered - no inference, no fallbacks
            location = self._extract_location_from_user(user)
            
            # Add detailed debug logging for ALL users to see what's being extracted
            username = getattr(user, 'username', 'unknown') if not isinstance(user, dict) else user.get('username', 'unknown')
            
            # Debug: Show what we're getting from the user object
            if not location or location.strip() == "":
                # Try to see what fields are available and what the location value actually is
                try:
                    # Try to access location directly for debugging
                    debug_location = None
                    if isinstance(user, dict):
                        debug_location = user.get('location')
                        available_fields = list(user.keys())
                    elif hasattr(user, 'location'):
                        debug_location = getattr(user, 'location', None)
                        if hasattr(user, '__dict__'):
                            available_fields = list(user.__dict__.keys())
                        else:
                            available_fields = [attr for attr in dir(user) if not attr.startswith('_')]
                    else:
                        if hasattr(user, '__dict__'):
                            available_fields = list(user.__dict__.keys())
                        else:
                            available_fields = [attr for attr in dir(user) if not attr.startswith('_')]
                    
                    debug_info = f"location field value: {repr(debug_location)}"
                    if len(available_fields) > 0:
                        debug_info += f" | available fields: {available_fields[:8]}"
                    print(f"         📍 @{username}: '{location}' (empty) | {debug_info}")
                except Exception as e:
                    print(f"         📍 @{username}: '{location}' (empty) | debug error: {str(e)[:50]}")
            else:
                print(f"         📍 @{username}: '{location}' ✓ (EXACT location extracted)")
            
            # Create attendee with extracted location
            # Safe attribute access for user object (handles both object and dict)
            if isinstance(user, dict):
                username = user.get('username', 'unknown')
                raw_display_name = user.get('name', '')
                bio = user.get('description', '')
                verified = user.get('verified', False)
                user_id = user.get('id', None)
            else:
                username = getattr(user, 'username', 'unknown')
                raw_display_name = getattr(user, 'name', '')
                bio = getattr(user, 'description', '')
                verified = getattr(user, 'verified', False)
                user_id = getattr(user, 'id', None)
            
            # EXTRACT CLEAN DISPLAY NAME FROM "ABOUT THIS ACCOUNT" SECTION
            # Filter out bio-like nonsense (pronouns, common bio patterns) from display name
            # Use username as fallback if display name looks like nonsense
            display_name = self._extract_clean_display_name(raw_display_name, username)
            
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

    def _calculate_semantic_relevance(self, tweet_text: str, event_name: str) -> float:
        """
        Calculate relevance using ML-based semantic matching
        Understands event context semantically - knows what the event is about
        Extracts teams, venues, dates, event types to understand context better
        """
        # Use semantic matcher for ML-based understanding
        # The matcher extracts teams, venues, dates, event types automatically
        relevance = self.semantic_matcher.calculate_relevance(tweet_text, event_name)
        
        # Boost score if there are strong engagement signals (combine ML + heuristics)
        text_lower = tweet_text.lower()
        engagement_boost = 0.0
        
        # Strong engagement signals (loaded from config)
        for phrase in STRONG_ENGAGEMENT:
            if phrase in text_lower:
                engagement_boost = 0.2  # Higher boost for engagement
                break
        
        # Medium engagement signals (loaded from config)
        if engagement_boost == 0:
            for phrase in MEDIUM_ENGAGEMENT:
                if phrase in text_lower:
                    engagement_boost = 0.15
                    break
        
        # Combine semantic relevance with engagement boost
        final_score = min(1.0, relevance + engagement_boost)
        
        return final_score
    
    def _calculate_tweet_relevance_priority(self, tweet_text: str, event_name: str) -> float:
        """
        Legacy keyword-based relevance (kept for fallback)
        Use _calculate_semantic_relevance instead
        """
        return self._calculate_semantic_relevance(tweet_text, event_name)

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
        # Remove common prefixes/suffixes (loaded from config)
        words = event_name.split()
        filtered_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in PREFIXES and len(word) > 2:
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
        # Stop words loaded from config
        clean_name = re.sub(r'[^\w\s]', ' ', event_name)
        words = clean_name.split()
        
        keywords = [
            word.lower() for word in words
            if word.lower() not in STOP_WORDS and len(word) > 2
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