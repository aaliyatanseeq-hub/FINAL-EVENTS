"""
UNIFIED MESSAGING SERVICE
Handles messaging across Twitter and Reddit platforms with rate limiting and retries
"""

import time
from typing import List, Dict, Optional
from datetime import datetime
from services.twitter_client import TwitterClient
from services.reddit_client import RedditClient


class UnifiedMessagingService:
    """
    Unified messaging service for Twitter and Reddit
    Handles rate limiting, retries, and platform-specific logic
    """
    
    def __init__(self):
        self.twitter_client = TwitterClient()
        self.reddit_client = RedditClient()
        
        # Rate limiting per platform
        self.twitter_delay = 1.0  # 1 second between Twitter messages
        self.reddit_delay = 2.0   # 2 seconds between Reddit messages
        self.last_twitter_message = 0
        self.last_reddit_message = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 5  # seconds
    
    def send_message(self, platform: str, target: Dict, message: str, subject: str = None) -> Dict:
        """
        Send a message to a user on the specified platform
        
        Args:
            platform: 'twitter' or 'reddit'
            target: Dict with user info (username, user_id, etc.)
            message: Message content
            subject: Subject line (for Reddit PMs, optional for Twitter)
        
        Returns:
            Dict with success status and details
        """
        if platform == "twitter":
            return self._send_twitter_message(target, message)
        elif platform == "reddit":
            return self._send_reddit_message(target, message, subject)
        else:
            return {
                'success': False,
                'error': f'Unknown platform: {platform}'
            }
    
    def _send_twitter_message(self, target: Dict, message: str) -> Dict:
        """Send Twitter DM"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_twitter_message
            if time_since_last < self.twitter_delay:
                time.sleep(self.twitter_delay - time_since_last)
            
            # Get user_id from target
            user_id = target.get('user_id') or target.get('id')
            username = target.get('username', 'unknown')
            
            if not user_id:
                # Try to get user_id from username (would need additional API call)
                return {
                    'success': False,
                    'error': 'user_id required for Twitter DMs. Username lookup not implemented.',
                    'username': username
                }
            
            # Send DM with retries
            for attempt in range(self.max_retries):
                try:
                    result = self.twitter_client.send_direct_message(user_id, message)
                    self.last_twitter_message = time.time()
                    return result
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        print(f"⚠️ Twitter DM attempt {attempt + 1} failed, retrying...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': str(e),
                            'username': username
                        }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'platform': 'twitter'
            }
    
    def _send_reddit_message(self, target: Dict, message: str, subject: str = None) -> Dict:
        """Send Reddit private message"""
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_reddit_message
            if time_since_last < self.reddit_delay:
                time.sleep(self.reddit_delay - time_since_last)
            
            # Get username from target
            username = target.get('username', '')
            if not username:
                return {
                    'success': False,
                    'error': 'username required for Reddit PMs'
                }
            
            # Clean username (remove u/ prefix if present)
            clean_username = username.replace('u/', '').strip()
            
            # Default subject if not provided
            if not subject:
                subject = "Message from Event Intelligence Platform"
            
            # Send PM with retries
            for attempt in range(self.max_retries):
                try:
                    result = self.reddit_client.send_private_message(clean_username, subject, message)
                    self.last_reddit_message = time.time()
                    return result
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        print(f"⚠️ Reddit PM attempt {attempt + 1} failed, retrying...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        return {
                            'success': False,
                            'error': str(e),
                            'username': clean_username
                        }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'platform': 'reddit'
            }
    
    def send_batch_messages(self, targets: List[Dict], message: str, subject: str = None) -> List[Dict]:
        """
        Send messages to multiple targets across platforms
        
        Args:
            targets: List of dicts with 'platform', 'username', 'user_id', etc.
            message: Message content
            subject: Subject line (for Reddit)
        
        Returns:
            List of results for each target
        """
        results = []
        
        for target in targets:
            platform = target.get('platform', target.get('source', 'unknown'))
            result = self.send_message(platform, target, message, subject)
            result['target'] = target.get('username', 'unknown')
            results.append(result)
        
        return results
    
    def is_platform_ready(self, platform: str) -> bool:
        """Check if a platform is ready for messaging"""
        if platform == "twitter":
            return self.twitter_client.is_operational()
        elif platform == "reddit":
            return self.reddit_client.is_operational()
        return False

