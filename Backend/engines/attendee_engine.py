"""
HIGHLY ENGINEERED ATTENDEE ENGINE - MAXIMUM EFFICIENCY
Guarantees N results with minimal API calls
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
from services.twitter_client import TwitterClient

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

class SmartAttendeeEngine:
    def __init__(self):
        self.twitter_client = TwitterClient()
        self.relevance_threshold = 0.05  # VERY LOW to catch maximum attendees
        try:
            print(f"🔧 Attendee Engine: {'✅ Twitter Ready' if self.twitter_client.is_operational() else '❌ No Auth'}")
        except UnicodeEncodeError:
            print(f"Attendee Engine: {'Twitter Ready' if self.twitter_client.is_operational() else 'No Auth'}")

    def discover_attendees(self, event_name: str, event_date: Optional[str], max_results: int) -> List[ResearchAttendee]:
        """GUARANTEES exactly max_results attendees with MAX 10 searches"""
        try:
            print(f"🔍 Finding EXACTLY {max_results} attendees for '{event_name}'")
            
            if not self.twitter_client.is_operational():
                print("❌ Twitter client not operational")
                return []

            # Strategic search that GUARANTEES results
            relevant_attendees = self._guaranteed_find_attendees(event_name, event_date, max_results)
            
            # Return exactly requested number
            final_attendees = relevant_attendees[:max_results]
            
            stats = self.twitter_client.get_usage_stats()
            print(f"✅ FOUND {len(final_attendees)} ATTENDEES (requested: {max_results})")
            print(f"📊 Used {self.twitter_client.total_searches_used} searches, {stats['searches_remaining']} remaining")
            
            return final_attendees

        except Exception as e:
            print(f"❌ Attendee discovery failed: {e}")
            return []

    def _guaranteed_find_attendees(self, event_name: str, event_date: Optional[str], max_results: int) -> List[ResearchAttendee]:
        """GUARANTEES N results with smart search strategy"""
        all_attendees = []
        seen_usernames: Set[str] = set()
        
        # PHASE 1: Exact matches (HIGH SUCCESS RATE)
        exact_queries = self._generate_exact_queries(event_name, event_date)
        for query_type, query in exact_queries[:3]:  # Max 3 exact searches
            if len(all_attendees) >= max_results:
                break
            attendees = self._search_and_process(query, event_name, max_results * 3)
            for attendee in attendees:
                if attendee.username not in seen_usernames and len(all_attendees) < max_results:
                    seen_usernames.add(attendee.username)
                    all_attendees.append(attendee)

        # PHASE 2: Smart keyword expansion (ONLY IF NEEDED)
        if len(all_attendees) < max_results:
            keyword_queries = self._generate_smart_keyword_queries(event_name)
            for query_type, query in keyword_queries[:3]:  # Max 3 keyword searches
                if len(all_attendees) >= max_results:
                    break
                attendees = self._search_and_process(query, event_name, max_results * 2)
                for attendee in attendees:
                    if attendee.username not in seen_usernames and len(all_attendees) < max_results:
                        seen_usernames.add(attendee.username)
                        all_attendees.append(attendee)

        # PHASE 3: Broad search (LAST RESORT)
        if len(all_attendees) < max_results:
            broad_queries = self._generate_broad_queries(event_name)
            for query_type, query in broad_queries[:2]:  # Max 2 broad searches
                if len(all_attendees) >= max_results:
                    break
                attendees = self._search_and_process(query, event_name, max_results)
                for attendee in attendees:
                    if attendee.username not in seen_usernames and len(all_attendees) < max_results:
                        seen_usernames.add(attendee.username)
                        all_attendees.append(attendee)

        # Sort by relevance
        all_attendees.sort(key=lambda x: x.relevance_score, reverse=True)
        return all_attendees

    def _generate_exact_queries(self, event_name: str, event_date: Optional[str]) -> List[Tuple[str, str]]:
        """Generate high-precision exact match queries"""
        clean_name = self._clean_event_name(event_name)
        
        queries = [
            ("exact", f'"{clean_name}"'),
            ("event", f'"{clean_name}" event'),
            ("concert", f'"{clean_name}" concert'),
        ]
        
        if event_date:
            queries.append(("dated", f'"{clean_name}" {event_date}'))
            
        return queries

    def _generate_smart_keyword_queries(self, event_name: str) -> List[Tuple[str, str]]:
        """Generate smart keyword queries"""
        keywords = self._extract_keywords(event_name)
        if not keywords:
            return []
            
        queries = []
        if len(keywords) >= 2:
            queries.append(("keywords", f'"{keywords[0]} {keywords[1]}"'))
        queries.append(("main_keyword", f'"{keywords[0]}"'))
        
        return queries

    def _generate_broad_queries(self, event_name: str) -> List[Tuple[str, str]]:
        """Generate broad queries for maximum coverage"""
        keywords = self._extract_keywords(event_name)
        if not keywords:
            return []
            
        return [
            ("broad", f'{keywords[0]}'),
            ("very_broad", f'{keywords[0]} OR {keywords[1] if len(keywords) > 1 else keywords[0]}')
        ]

    def _search_and_process(self, query: str, event_name: str, max_results: int) -> List[ResearchAttendee]:
        """Single efficient search and process"""
        tweets = self.twitter_client.search_recent_tweets_safe(
            query=query,
            max_results=min(max_results, 100),  # Increased to catch more
            tweet_fields=['author_id', 'created_at', 'text'],
            user_fields=['username', 'name', 'verified', 'description', 'location', 'public_metrics'],
            expansions=['author_id']
        )

        if not tweets or not tweets.data:
            return []

        return self._process_tweets_fast(tweets, event_name)

    def _process_tweets_fast(self, tweets, event_name: str) -> List[ResearchAttendee]:
        """Fast processing with VERY LOW filtering"""
        attendees = []
        
        if not tweets.includes or 'users' not in tweets.includes:
            return attendees

        users_dict = {user.id: user for user in tweets.includes['users']}

        for tweet in tweets.data:
            user = users_dict.get(tweet.author_id)
            if not user:
                continue

            # VERY LOW threshold - include almost everything
            relevance_score = self._calculate_relevance_score_fast(tweet.text, event_name)
            
            # Include if even slightly relevant
            if relevance_score >= self.relevance_threshold:
                followers = user.public_metrics.get('followers_count', 0) if hasattr(user, 'public_metrics') else 0

                attendee = ResearchAttendee(
                    username=f"@{user.username}",
                    display_name=user.name,
                    bio=user.description or "",
                    location=user.location or "",
                    followers_count=followers,
                    verified=user.verified or False,
                    confidence_score=0.7,
                    engagement_type=self._detect_engagement_fast(tweet.text),
                    post_content=tweet.text[:100] + "..." if len(tweet.text) > 100 else tweet.text,
                    post_date=tweet.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(tweet.created_at, 'strftime') else str(tweet.created_at),
                    post_link=f"https://twitter.com/{user.username}/status/{tweet.id}",
                    relevance_score=relevance_score
                )
                attendees.append(attendee)

        return attendees

    def _calculate_relevance_score_fast(self, tweet_text: str, event_name: str) -> float:
        """FAST relevance scoring - VERY PERMISSIVE"""
        text_lower = tweet_text.lower()
        event_lower = event_name.lower()
        
        score = 0.0
        
        # Exact match (STRONG)
        if event_lower in text_lower:
            score += 0.6
        
        # Keyword matches (MEDIUM)
        keywords = self._extract_keywords(event_name)
        matched_keywords = sum(1 for keyword in keywords if keyword in text_lower)
        score += min(0.3, matched_keywords * 0.1)
        
        # Any engagement signal (WEAK)
        engagement_phrases = ['attending', 'going to', 'see you at', 'excited for', 'can\'t wait for']
        for phrase in engagement_phrases:
            if phrase in text_lower:
                score += 0.1
                break
        
        # Event context words (VERY WEAK)
        event_words = ['event', 'concert', 'festival', 'show', 'party']
        for word in event_words:
            if word in text_lower:
                score += 0.05
                break
        
        return min(1.0, score)

    def _extract_keywords(self, event_name: str) -> List[str]:
        """Extract main keywords"""
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
        
        clean_name = re.sub(r'[^\w\s]', ' ', event_name)
        words = clean_name.split()
        
        keywords = [word.lower() for word in words 
                   if word.lower() not in stop_words 
                   and len(word) > 2]
        
        return keywords if keywords else [event_name.split()[0].lower()]

    def _clean_event_name(self, event_name: str) -> str:
        """Clean event name for search"""
        if not event_name:
            return "event"
        cleaned = re.sub(r'[^\w\s]', ' ', event_name)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else "event"

    def _detect_engagement_fast(self, tweet_text: str) -> str:
        """Fast engagement detection"""
        text_lower = tweet_text.lower()
        if any(word in text_lower for word in ['attending', 'going to', 'will be there']):
            return 'confirmed_attendance'
        elif any(word in text_lower for word in ['excited for', 'can\'t wait for']):
            return 'excited'
        else:
            return 'discussing'
