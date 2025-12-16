"""
HIGHLY ENGINEERED TWITTER CLIENT - FINAL
Combines OAuth 1.1 (working) + v2 API + Rate Limiting + Basic Tier compatibility
"""

import os
import tweepy
import time
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class TwitterClient:
    def __init__(self):
        self.consumer_key = os.getenv('TWITTER_API_KEY')
        self.consumer_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # Dual clients for maximum compatibility
        self.client_v2 = None  # v2 API for posting (PROVEN WORKING)
        self.api_v1 = None     # v1.1 API for search
        self.rate_limit_remaining = 60
        self.last_reset_time = datetime.now()
        self.total_searches_used = 0
        self.setup_clients()

    def setup_clients(self):
        """Setup both v2 and v1.1 clients"""
        try:
            # v2 Client for posting (YOUR WORKING CODE)
            self.client_v2 = tweepy.Client(
                consumer_key=self.consumer_key,
                consumer_secret=self.consumer_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                bearer_token=self.bearer_token,
                wait_on_rate_limit=False
            )
            
            # v1.1 API for search (backup)
            if all([self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret]):
                auth = tweepy.OAuth1UserHandler(
                    self.consumer_key, self.consumer_secret,
                    self.access_token, self.access_token_secret
                )
                self.api_v1 = tweepy.API(auth)
            
            print("✅ Twitter clients: v2 (posting) + v1.1 (search)")
            
            # Test authentication
            user = self.client_v2.get_me()
            print(f"✅ Authenticated as: @{user.data.username}")
            
            return True
        except Exception as e:
            print(f"❌ Twitter setup failed: {e}")
            return False

    def _check_rate_limit(self):
        """Manual rate limit checking"""
        now = datetime.now()
        time_since_reset = (now - self.last_reset_time).total_seconds()
        
        # Reset every 15 minutes
        if time_since_reset >= 900:
            self.rate_limit_remaining = 60
            self.last_reset_time = now
            self.total_searches_used = 0
        
        if self.rate_limit_remaining <= 0:
            return False
        return True

    def search_recent_tweets_safe(self, query: str, max_results: int = 10, **kwargs):
        """Optimized search with manual rate limiting"""
        try:
            if not self._check_rate_limit():
                print("🚫 Search blocked: Rate limit reached")
                return None
            
            print(f"🔍 Searching: '{query}'")
            print(f"📊 Quota: {self.rate_limit_remaining}/60 searches left")
            
            # Twitter API v2 allows up to 100 tweets per request
            # Use higher limit to find more attendees
            response = self.client_v2.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                **kwargs
            )
            
            self.rate_limit_remaining -= 1
            self.total_searches_used += 1
            
            if response and response.data:
                print(f"✅ Found {len(response.data)} tweets")
            else:
                print("❌ No tweets found")
            
            return response
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return None

    def post_tweet(self, text: str, reply_to_tweet_id: str = None):
        """POSTING THAT WORKS - Using v2 API (YOUR WORKING CODE)"""
        try:
            print(f"🐦 Posting: {text[:50]}...")
            
            if reply_to_tweet_id:
                # First, try to get the tweet to check if we can access it and get author info
                author_id = None
                is_protected = False
                try:
                    tweet_info = self.client_v2.get_tweet(
                        id=reply_to_tweet_id,
                        tweet_fields=['author_id', 'conversation_id', 'public_metrics', 'reply_settings'],
                        user_fields=['protected', 'username'],
                        expansions=['author_id']
                    )
                    print(f"📋 Tweet accessible: {reply_to_tweet_id}")
                    
                    # Check if we got author info
                    if tweet_info.data:
                        author_id = tweet_info.data.get('author_id')
                        # Check if author is protected
                        if tweet_info.includes and 'users' in tweet_info.includes:
                            for user in tweet_info.includes['users']:
                                if user.id == author_id:
                                    is_protected = getattr(user, 'protected', False)
                                    if is_protected:
                                        print(f"⚠️ Author account is protected")
                                    break
                except Exception as check_error:
                    error_msg = str(check_error)
                    if '403' in error_msg or 'Forbidden' in error_msg:
                        return {
                            'success': False,
                            'error': '403 Forbidden - Cannot access tweet. It may be from a protected account or deleted.',
                            'error_code': 403,
                            'details': 'Tweet is not accessible for replies'
                        }
                    elif '404' in error_msg or 'Not Found' in error_msg:
                        return {
                            'success': False,
                            'error': '404 Not Found - Tweet does not exist or was deleted',
                            'error_code': 404
                        }
                    # If we can't check, continue anyway
                    print(f"⚠️ Could not verify tweet access: {check_error}")
                
                # Post as reply using v2 API
                try:
                    response = self.client_v2.create_tweet(
                        text=text,
                        in_reply_to_tweet_id=reply_to_tweet_id
                    )
                    print(f"✅ Reply posted to {reply_to_tweet_id}")
                    print(f"📝 Tweet ID: {response.data['id']}")
                    return {'success': True, 'tweet_id': response.data['id']}
                except tweepy.Forbidden as fb_error:
                    # More detailed 403 error with diagnostics
                    error_detail = str(fb_error)
                    error_response = fb_error.response
                    
                    # Try to extract more details from the error
                    additional_info = []
                    if is_protected:
                        additional_info.append("Author account is protected - you may need to follow them first")
                    if author_id:
                        additional_info.append(f"Author ID: {author_id}")
                    
                    # Check if it's a specific Twitter error code
                    if error_response and hasattr(error_response, 'json'):
                        try:
                            error_json = error_response.json()
                            if 'detail' in error_json:
                                error_detail = error_json['detail']
                            if 'title' in error_json:
                                additional_info.append(f"Error type: {error_json['title']}")
                        except:
                            pass
                    
                    error_msg = f'403 Forbidden - {error_detail}'
                    if additional_info:
                        error_msg += f'. Additional info: {"; ".join(additional_info)}'
                    error_msg += '. Common causes: Twitter blocking automated replies, account restrictions, or need to follow the user first.'
                    
                    print(f"❌ Reply blocked: {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_code': 403,
                        'details': error_detail,
                        'author_protected': is_protected,
                        'author_id': author_id
                    }
            else:
                # Post as new tweet
                response = self.client_v2.create_tweet(text=text)
                print(f"✅ Tweet posted")
                print(f"📝 Tweet ID: {response.data['id']}")
                return {'success': True, 'tweet_id': response.data['id']}
            
        except tweepy.Forbidden as e:
            error_str = str(e)
            print(f"❌ Post failed (403): {error_str}")
            return {
                'success': False, 
                'error': f'403 Forbidden - {error_str}. Account may not have permission to reply, or tweet may be from protected account.',
                'error_code': 403,
                'details': error_str
            }
        except tweepy.Unauthorized as e:
            error_str = str(e)
            print(f"❌ Post failed (401): {error_str}")
            return {
                'success': False,
                'error': f'401 Unauthorized - {error_str}. Check Twitter API credentials.',
                'error_code': 401,
                'details': error_str
            }
        except tweepy.TooManyRequests as e:
            error_str = str(e)
            print(f"❌ Post failed (429 Rate Limit): {error_str}")
            return {
                'success': False,
                'error': f'429 Rate Limit Exceeded - {error_str}. Please wait before trying again.',
                'error_code': 429,
                'details': error_str
            }
        except tweepy.BadRequest as e:
            error_str = str(e)
            print(f"❌ Post failed (400 Bad Request): {error_str}")
            return {
                'success': False,
                'error': f'400 Bad Request - {error_str}. Check tweet text length and format.',
                'error_code': 400,
                'details': error_str
            }
        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__
            print(f"❌ Post failed ({error_type}): {error_str}")
            return {
                'success': False,
                'error': f'{error_type}: {error_str}',
                'error_code': 500,
                'details': error_str
            }

    def retweet_tweet(self, tweet_id: str):
        """Retweet using v2 API"""
        try:
            user = self.client_v2.get_me()
            user_id = user.data.id
            
            print(f"🔄 Retweeting: {tweet_id}")
            response = self.client_v2.retweet(user_id, tweet_id)
            print(f"✅ Retweeted: {tweet_id}")
            return True
            
        except Exception as e:
            print(f"❌ Retweet failed: {e}")
            return False

    def like_tweet(self, tweet_id: str):
        """Like using v2 API"""
        try:
            user = self.client_v2.get_me()
            user_id = user.data.id
            
            print(f"❤️  Liking: {tweet_id}")
            response = self.client_v2.like(user_id, tweet_id)
            print(f"✅ Liked: {tweet_id}")
            return True
            
        except Exception as e:
            print(f"❌ Like failed: {e}")
            return False

    def send_direct_message(self, user_id: str, message: str) -> Dict:
        """
        Send a direct message to a Twitter user
        Note: Requires Twitter API v1.1 or special permissions for DMs
        """
        try:
            if not self.is_operational():
                return {'success': False, 'error': 'Twitter client not operational'}
            
            # Twitter DMs require v1.1 API
            if not self.api_v1:
                return {
                    'success': False,
                    'error': 'Twitter OAuth 1.1 required for direct messages. DMs are not available in v2 API without special access.'
                }
            
            print(f"💬 Sending DM to user_id: {user_id}")
            
            # Send DM using v1.1 API
            try:
                self.api_v1.send_direct_message(recipient_id=user_id, text=message)
                print(f"✅ Twitter DM sent to user_id: {user_id}")
                return {
                    'success': True,
                    'user_id': user_id,
                    'message': 'Direct message sent successfully'
                }
            except tweepy.Forbidden as e:
                return {
                    'success': False,
                    'error': '403 Forbidden - Cannot send DM. User may have DMs disabled or account restrictions.',
                    'error_code': 403
                }
            except tweepy.NotFound as e:
                return {
                    'success': False,
                    'error': '404 Not Found - User does not exist or account is suspended.',
                    'error_code': 404
                }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Twitter DM failed: {error_msg[:100]}")
            return {
                'success': False,
                'error': error_msg,
                'user_id': user_id
            }

    def is_operational(self):
        return self.client_v2 is not None

    def get_usage_stats(self):
        now = datetime.now()
        time_since_reset = (now - self.last_reset_time).total_seconds()
        reset_in = max(0, 900 - time_since_reset)
        
        return {
            "searches_remaining": self.rate_limit_remaining,
            "searches_used": self.total_searches_used,
            "searches_limit": 60,
            "reset_in_minutes": int(reset_in / 60),
            "posting_limit": "100 posts/24hr"
        }