"""
HIGHLY ENGINEERED REDDIT CLIENT FOR ATTENDEE DISCOVERY
Advanced search with sentiment analysis and engagement detection
"""

import os
import praw
import re
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import concurrent.futures

load_dotenv()

class RedditClient:
    def __init__(self):
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        # Reddit requires format: 'app-name/version by u/username'
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'EventIntelPlatform/1.0 by u/Personal-Field1481')
        # Optional: username/password for authenticated read-only access
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        
        self.reddit = None
        self.initialized = False
        self.last_request_time = 0
        self.request_delay = 2  # Rate limiting delay
        
        # Event-related subreddits (prioritized)
        self.event_subreddits = [
            'concerts', 'festivals', 'sports', 'aves', 'EDM', 'indieheads',
            'travel', 'cityspecific', 'technology', 'conferences',
            'food', 'beer', 'wine', 'art', 'theater', 'movies'
        ]
        
        # Engagement keywords
        self.engagement_keywords = {
            'confirmed_attendance': [
                'going', 'attending', 'will be there', 'see you', 'got tickets',
                'booked', 'reserved', 'bought tickets', 'I\'ll be', 'count me in'
            ],
            'interested': [
                'interested', 'thinking about', 'considering', 'might go',
                'looks good', 'sounds fun', 'want to go', 'planning to'
            ],
            'reviewing': [
                'went to', 'attended', 'was there', 'review', 'experience',
                'recap', 'summary', 'thoughts on', 'after attending'
            ],
            'planning': [
                'where to stay', 'best seats', 'parking', 'transportation',
                'what to wear', 'food options', 'drinks', 'meetup'
            ]
        }
        
        self._initialize_client()
    
    def _initialize_client(self) -> bool:
        """Initialize Reddit client with error handling - matches working example"""
        try:
            if not self.client_id or not self.client_secret:
                print("❌ Reddit: Missing credentials (client_id or client_secret)")
                return False
            
            # Debug: Show what credentials we have (without exposing secrets)
            print(f"🔍 Reddit Auth Debug:")
            print(f"   Client ID: {self.client_id[:15]}..." if self.client_id else "   Client ID: ❌ MISSING")
            print(f"   Client Secret: {'✅ SET (' + str(len(self.client_secret)) + ' chars)' if self.client_secret and self.client_secret != 'PASTE_YOUR_SECRET_HERE' else '❌ MISSING/INVALID'}")
            print(f"   User Agent: {self.user_agent}")
            print(f"   Username: {'✅ SET (optional)' if self.username else '❌ NOT SET (not required)'}")
            
            # Initialize Reddit client - EXACTLY like the working example (3 parameters only)
            # Working example: reddit = praw.Reddit(client_id="...", client_secret="...", user_agent="...")
            print("📖 Reddit: Initializing with 3 parameters (client_id + secret + user_agent)")
            print(f"   Matching your working example exactly...")
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
                # No check_for_async, no username/password - matches working example exactly
            )
            print(f"   ✅ PRAW Reddit object created")
            
            # Test connection by trying a simple search (like the working example)
            try:
                print(f"   🧪 Testing Reddit search capability...")
                # Test search like the working example
                test_query = "test"
                test_results = list(self.reddit.subreddit("all").search(test_query, limit=1))
                print(f"✅ Reddit: Search test successful (found {len(test_results)} result)")
                print(f"✅ Reddit Client: Initialized successfully (read-only mode)")
                self.initialized = True
                return True
            except Exception as search_error:
                error_str = str(search_error)
                error_type = type(search_error).__name__
                if '401' in error_str or 'Unauthorized' in error_str or 'HTTP 401' in error_str:
                    print(f"❌ Reddit: Search test FAILED - 401 Unauthorized")
                    print(f"   Error Type: {error_type}")
                    print(f"   Full Error: {error_str}")
                    print(f"\n   🔧 TROUBLESHOOTING STEPS:")
                    print(f"   1. ✅ Check REDDIT_CLIENT_ID: {self.client_id[:15]}...")
                    print(f"   2. ✅ Check REDDIT_CLIENT_SECRET: {'SET' if self.client_secret else 'MISSING'}")
                    print(f"   3. ✅ Check REDDIT_USER_AGENT: {self.user_agent}")
                    print(f"\n   📝 COMMON FIXES:")
                    print(f"   • Go to https://www.reddit.com/prefs/apps")
                    print(f"   • Verify your app type is 'script' (not 'web app')")
                    print(f"   • Copy the CLIENT ID (string under app name)")
                    print(f"   • Copy the SECRET (the 'secret' field)")
                    print(f"   • User agent format: 'app-name by u/username'")
                    print(f"   • Make sure .env has NO quotes around values")
                    print(f"   • Make sure .env has NO spaces around = sign")
                    print(f"\n   💡 Your working example used:")
                    print(f"      client_id='AvYPAjpVd-tCwmrp138fPA'")
                    print(f"      user_agent='event-intel-test by u/Fuzzy-Whole-1648'")
                    print(f"   → Use the SAME credentials that worked in your test!")
                    self.initialized = False
                    return False
                else:
                    print(f"⚠️ Reddit: Search test failed but continuing: {error_str[:150]}")
                    print(f"   Error Type: {error_type}")
                    # Still initialize - might work for other operations
                    self.initialized = True
                    return True
            
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            print(f"❌ Reddit Client initialization failed: {error_str[:200]}")
            print(f"   Error Type: {error_type}")
            if '401' in error_str or 'Unauthorized' in error_str:
                print(f"   💡 Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
            return False
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
        self.last_request_time = time.time()
    
    def is_operational(self) -> bool:
        """Check if Reddit client is ready"""
        return self.initialized and self.reddit is not None
    
    def discover_event_attendees(self, event_name: str, max_results: int = 20) -> List[Dict]:
        """
        Discover Reddit users discussing an event
        Returns: List of attendee dictionaries
        """
        if not self.is_operational():
            print("❌ Reddit: Client not operational")
            return []
        
        try:
            print(f"🔍 Reddit: Searching for attendees of '{event_name}'")
            
            attendees = []
            seen_users = set()
            
            # Strategy 1: Search in event-specific subreddits
            subreddit_attendees = self._search_in_event_subreddits(event_name, max_results // 2)
            for attendee in subreddit_attendees:
                if attendee['username'] not in seen_users:
                    seen_users.add(attendee['username'])
                    attendees.append(attendee)
            
            # Strategy 2: Search across all of Reddit
            if len(attendees) < max_results:
                self._rate_limit()
                global_attendees = self._search_all_reddit(event_name, max_results - len(attendees))
                for attendee in global_attendees:
                    if attendee['username'] not in seen_users:
                        seen_users.add(attendee['username'])
                        attendees.append(attendee)
            
            # Strategy 3: Search for event hashtags/common names
            if len(attendees) < max_results // 2:
                self._rate_limit()
                hashtag_attendees = self._search_event_variations(event_name, max_results // 4)
                for attendee in hashtag_attendees:
                    if attendee['username'] not in seen_users:
                        seen_users.add(attendee['username'])
                        attendees.append(attendee)
            
            print(f"✅ Reddit: Found {len(attendees)} unique attendees")
            return attendees[:max_results]
            
        except Exception as e:
            print(f"❌ Reddit search failed: {str(e)[:100]}")
            return []
    
    def _search_in_event_subreddits(self, event_name: str, limit: int) -> List[Dict]:
        """Search for event discussions in relevant subreddits"""
        attendees = []
        
        # Prioritize subreddits based on event type
        prioritized_subs = self._prioritize_subreddits(event_name)
        
        for subreddit_name in prioritized_subs[:5]:  # Limit to top 5 subreddits
            try:
                self._rate_limit()
                
                print(f"   📍 Searching r/{subreddit_name}...")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search for posts
                search_query = self._build_reddit_search_query(event_name)
                
                # Search like the working example: subreddit.search(query, sort, limit)
                for submission in subreddit.search(
                    query=search_query,
                    sort='new',  # Changed to 'new' to match working example
                    limit=min(limit, 15)
                ):
                    # Process submission
                    submission_attendee = self._process_submission(submission, event_name)
                    if submission_attendee:
                        attendees.append(submission_attendee)
                    
                    # Process top comments
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:10]:  # Top 10 comments
                        comment_attendee = self._process_comment(comment, event_name, submission.title)
                        if comment_attendee:
                            attendees.append(comment_attendee)
                
                if len(attendees) >= limit:
                    break
                    
            except Exception as e:
                error_str = str(e)
                if '401' in error_str or 'Unauthorized' in error_str:
                    print(f"   ❌ Error in r/{subreddit_name}: 401 Unauthorized")
                    print(f"      💡 Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
                    print(f"      💡 Verify your Reddit app is set to 'script' type")
                    print(f"      💡 Username/password NOT required for search")
                else:
                    print(f"   ⚠️ Error in r/{subreddit_name}: {error_str[:50]}")
                continue
        
        return attendees[:limit]
    
    def _search_all_reddit(self, event_name: str, limit: int) -> List[Dict]:
        """Search across all of Reddit"""
        attendees = []
        
        try:
            search_query = self._build_reddit_search_query(event_name)
            
            print(f"   🌐 Searching all Reddit for '{search_query}'...")
            
            # Search all Reddit like the working example
            for submission in self.reddit.subreddit("all").search(
                query=search_query,
                sort='new',  # Changed to 'new' to match working example
                limit=min(limit * 2, 30)
            ):
                attendee = self._process_submission(submission, event_name)
                if attendee:
                    attendees.append(attendee)
                
                # Also get commenters
                submission.comments.replace_more(limit=0)
                for comment in submission.comments[:5]:
                    comment_attendee = self._process_comment(comment, event_name, submission.title)
                    if comment_attendee:
                        attendees.append(comment_attendee)
                
                if len(attendees) >= limit:
                    break
        
        except Exception as e:
            error_str = str(e)
            if '401' in error_str or 'Unauthorized' in error_str:
                print(f"   ❌ Global search error: 401 Unauthorized")
                print(f"      💡 Check REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
                print(f"      💡 Verify your Reddit app is set to 'script' type")
                print(f"      💡 Username/password NOT required for search")
            else:
                print(f"   ⚠️ Global search error: {error_str[:50]}")
        
        return attendees[:limit]
    
    def _search_event_variations(self, event_name: str, limit: int) -> List[Dict]:
        """Search for event name variations and hashtags"""
        attendees = []
        
        # Generate variations
        variations = self._generate_event_variations(event_name)
        
        for variation in variations[:3]:  # Limit variations
            try:
                self._rate_limit()
                
                # Search variations like the working example
                for submission in self.reddit.subreddit("all").search(
                    query=variation,
                    sort='new',  # Changed to 'new' to match working example
                    limit=10
                ):
                    attendee = self._process_submission(submission, event_name)
                    if attendee:
                        attendees.append(attendee)
                
                if len(attendees) >= limit:
                    break
                    
            except Exception as e:
                continue
        
        return attendees[:limit]
    
    def _build_reddit_search_query(self, event_name: str) -> str:
        """Build optimized Reddit search query"""
        # Clean event name
        clean_name = re.sub(r'[^\w\s]', ' ', event_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        
        # Use exact phrase for main search
        words = clean_name.split()
        if len(words) <= 4:
            return f'"{clean_name}"'
        else:
            # For longer names, use most important words
            important_words = [words[0]]
            if len(words) > 1:
                important_words.append(words[-1])
            return ' '.join(important_words)
    
    def _generate_event_variations(self, event_name: str) -> List[str]:
        """Generate search variations for the event"""
        variations = []
        clean_name = event_name.lower()
        
        # Common event suffixes/prefixes
        suffixes = ['2024', '2025', 'tour', 'festival', 'concert', 'expo', 'conference']
        
        # Add year variations
        for year in ['2024', '2025', '2023']:
            variations.append(f"{clean_name} {year}")
        
        # Add event type variations
        for suffix in suffixes:
            if suffix not in clean_name:
                variations.append(f"{clean_name} {suffix}")
        
        # Add location if present
        if 'in ' in clean_name:
            location_part = clean_name.split('in ')[-1]
            variations.append(location_part)
        
        # Add hashtag style
        hashtag_name = clean_name.replace(' ', '')
        variations.append(f"#{hashtag_name}")
        
        return variations
    
    def _prioritize_subreddits(self, event_name: str) -> List[str]:
        """Prioritize subreddits based on event type"""
        event_lower = event_name.lower()
        prioritized = []
        
        # Check event type
        if any(word in event_lower for word in ['concert', 'music', 'festival', 'band', 'dj']):
            prioritized.extend(['concerts', 'festivals', 'aves', 'EDM', 'indieheads', 'music'])
        elif any(word in event_lower for word in ['sports', 'game', 'match', 'tournament']):
            prioritized.extend(['sports', 'nba', 'nfl', 'soccer', 'baseball'])
        elif any(word in event_lower for word in ['conference', 'tech', 'startup', 'business']):
            prioritized.extend(['technology', 'startups', 'business', 'programming'])
        elif any(word in event_lower for word in ['food', 'wine', 'beer', 'culinary']):
            prioritized.extend(['food', 'cooking', 'wine', 'beer'])
        elif any(word in event_lower for word in ['art', 'theater', 'movie', 'gallery']):
            prioritized.extend(['art', 'movies', 'theater', 'entertainment'])
        
        # Add general event subreddits
        prioritized.extend(self.event_subreddits)
        
        # Remove duplicates and return
        return list(dict.fromkeys(prioritized))
    
    def _process_submission(self, submission, event_name: str) -> Optional[Dict]:
        """Process a Reddit submission into attendee data - matches unified schema"""
        try:
            if not submission.author:
                return None
            
            content = f"{submission.title} {submission.selftext}"
            relevance_score = self._calculate_relevance_score(content, event_name)
            
            if relevance_score < 0.2:  # Minimum relevance threshold
                return None
            
            engagement_type = self._detect_engagement_type(content)
            user = submission.author
            
            # Get subreddit subscribers as proxy for followers
            try:
                subreddit_subscribers = getattr(submission.subreddit, 'subscribers', 0) if hasattr(submission, 'subreddit') else 0
            except:
                subreddit_subscribers = 0
            
            # Full post content (title + body) for schema compliance
            post_content = f"{submission.title}\n\n{submission.selftext}".strip()
            
            # UTC ISO string format for post_date
            post_date_iso = datetime.utcfromtimestamp(submission.created_utc).isoformat() + "Z"
            
            return {
                'username': f"u/{user.name}",
                'display_name': user.name,
                'bio': '',  # Reddit doesn't provide bio in submissions
                'location': '',  # Can be set from query context if needed
                'followers_count': subreddit_subscribers,  # Use subreddit subscribers as proxy
                'karma': user.link_karma + user.comment_karma,
                'verified': False,  # Reddit doesn't have verification like Twitter
                'post_content': post_content,  # Full content (title + body)
                'post_date': post_date_iso,  # UTC ISO string format
                'post_date_display': datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M'),  # Keep for display
                'post_link': f"https://reddit.com{submission.permalink}",
                'relevance_score': relevance_score,
                'engagement_type': engagement_type,
                'source': 'reddit',
                'comment_count': submission.num_comments,
                'upvotes': submission.score,
                'actions': 'pending_outreach'  # Schema field for actions
            }
            
        except Exception as e:
            return None
    
    def _process_comment(self, comment, event_name: str, post_title: str) -> Optional[Dict]:
        """Process a Reddit comment into attendee data - matches unified schema"""
        try:
            if not comment.author:
                return None
            
            content = comment.body
            combined_content = f"{post_title} {content}"
            relevance_score = self._calculate_relevance_score(combined_content, event_name)
            
            if relevance_score < 0.2:
                return None
            
            engagement_type = self._detect_engagement_type(content)
            user = comment.author
            
            # Get subreddit subscribers as proxy for followers
            try:
                subreddit_subscribers = getattr(comment.subreddit, 'subscribers', 0) if hasattr(comment, 'subreddit') else 0
            except:
                subreddit_subscribers = 0
            
            # Full post content (title + comment body) for schema compliance
            post_content = f"{post_title}\n\n{content}".strip()
            
            # UTC ISO string format for post_date
            post_date_iso = datetime.utcfromtimestamp(comment.created_utc).isoformat() + "Z"
            
            return {
                'username': f"u/{user.name}",
                'display_name': user.name,
                'bio': '',
                'location': '',
                'followers_count': subreddit_subscribers,  # Use subreddit subscribers as proxy
                'karma': user.link_karma + user.comment_karma,
                'verified': False,
                'post_content': post_content,  # Full content (title + body)
                'post_date': post_date_iso,  # UTC ISO string format
                'post_date_display': datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M'),  # Keep for display
                'post_link': f"https://reddit.com{comment.permalink}",
                'relevance_score': relevance_score,
                'engagement_type': engagement_type,
                'source': 'reddit',
                'comment_depth': getattr(comment, 'depth', 0),
                'upvotes': comment.score,
                'actions': 'pending_outreach'  # Schema field for actions
            }
            
        except Exception as e:
            return None
    
    def _calculate_relevance_score(self, text: str, event_name: str) -> float:
        """Calculate how relevant text is to the event"""
        if not text or not event_name:
            return 0.0
        
        text_lower = text.lower()
        event_lower = event_name.lower()
        
        score = 0.0
        
        # 1. Exact match (highest weight)
        if event_lower in text_lower:
            score += 0.5
        
        # 2. Partial matches
        event_words = set(re.findall(r'\b\w+\b', event_lower))
        text_words = set(re.findall(r'\b\w+\b', text_lower))
        
        common_words = event_words.intersection(text_words)
        if len(event_words) > 0:
            word_match_ratio = len(common_words) / len(event_words)
            score += word_match_ratio * 0.3
        
        # 3. Event context words
        context_words = ['event', 'concert', 'festival', 'ticket', 'attend', 'going', 'show']
        for word in context_words:
            if word in text_lower:
                score += 0.05
                break
        
        # 4. Engagement keywords bonus
        for engagement_type, keywords in self.engagement_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                score += 0.1
                break
        
        return min(1.0, score)
    
    def _detect_engagement_type(self, text: str) -> str:
        """Detect engagement type from text"""
        if not text:
            return 'mention'
        
        text_lower = text.lower()
        
        for engagement_type, keywords in self.engagement_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return engagement_type
        
        return 'mention'
    
    def get_user_details(self, username: str) -> Optional[Dict]:
        """Get detailed user information"""
        if not self.is_operational():
            return None
        
        try:
            self._rate_limit()
            
            # Remove 'u/' prefix if present
            clean_username = username.replace('u/', '')
            redditor = self.reddit.redditor(clean_username)
            
            # Try to get user info
            user_info = {
                'username': f"u/{redditor.name}",
                'display_name': redditor.name,
                'created_utc': redditor.created_utc,
                'link_karma': redditor.link_karma,
                'comment_karma': redditor.comment_karma,
                'total_karma': redditor.link_karma + redditor.comment_karma,
                'has_verified_email': getattr(redditor, 'has_verified_email', False),
                'is_mod': getattr(redditor, 'is_mod', False),
                'is_gold': getattr(redditor, 'is_gold', False)
            }
            
            # Try to get about info
            try:
                about = redditor.subreddit
                if about:
                    user_info['bio'] = getattr(about, 'public_description', '')[:500]
            except:
                user_info['bio'] = ''
            
            return user_info
            
        except Exception as e:
            print(f"⚠️ Failed to get user details for {username}: {str(e)[:50]}")
            return None
    
    def send_private_message(self, username: str, subject: str, message: str) -> Dict:
        """
        Send a private message to a Reddit user
        Note: Requires authenticated Reddit account with proper permissions
        """
        try:
            if not self.is_operational():
                return {'success': False, 'error': 'Reddit client not operational'}
            
            # Check if we have authenticated user (required for PMs)
            try:
                current_user = self.reddit.user.me()
                if not current_user:
                    return {
                        'success': False,
                        'error': 'Reddit authentication required for sending messages. Please configure username/password or OAuth.'
                    }
            except Exception:
                return {
                    'success': False,
                    'error': 'Reddit authentication required. Read-only mode cannot send messages.'
                }
            
            # Clean username (remove u/ prefix if present)
            clean_username = username.replace('u/', '').replace('u/', '')
            
            self._rate_limit()
            
            # Send private message
            self.reddit.redditor(clean_username).message(subject, message)
            
            print(f"✅ Reddit PM sent to u/{clean_username}")
            return {
                'success': True,
                'username': clean_username,
                'message': 'Private message sent successfully'
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Reddit PM failed to {username}: {error_msg[:100]}")
            return {
                'success': False,
                'error': error_msg,
                'username': username
            }
    
    def test_connection(self) -> Dict:
        """Test Reddit API connection"""
        try:
            if not self.is_operational():
                return {'success': False, 'error': 'Client not initialized'}
            
            # Test by accessing a public subreddit (no user auth required)
            test_subreddit = self.reddit.subreddit("test")
            _ = test_subreddit.display_name
            
            return {
                'success': True,
                'message': 'Reddit API connected successfully (read-only mode)',
                'mode': 'read-only'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}