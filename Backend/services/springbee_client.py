"""
SpringBee (Scraping Bee) Client for enhanced web scraping
"""

import requests
import os
import json
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

class SpringBeeClient:
    def __init__(self):
        self.api_key = os.getenv('SPRINGBEE_API_KEY')
        self.base_url = "https://app.scrapingbee.com/api/v1/"
        self.initialized = bool(self.api_key)
        
        if self.initialized:
            print(f"✅ SpringBee Client: Initialized")
        else:
            print(f"❌ SpringBee Client: No API key found")
    
    def is_operational(self) -> bool:
        return self.initialized
    
    def search_events(self, query: str, location: str = None) -> List[Dict]:
        """Search for events using SpringBee"""
        if not self.is_operational():
            return []
        
        try:
            # Construct Google search URL
            search_query = f"{query} events {location}" if location else f"{query} events"
            google_url = f"https://www.google.com/search?q={requests.utils.quote(search_query)}&tbm=evt"
            
            params = {
                'api_key': self.api_key,
                'url': google_url,
                'render_js': 'true',
                'wait': '1500',
                'country_code': 'us',
                'premium_proxy': 'true'
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            
            if response.status_code == 200:
                # Parse the HTML response (simplified - in production use BeautifulSoup)
                events = self._parse_google_events_html(response.text)
                return events
            else:
                print(f"❌ SpringBee request failed: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ SpringBee search error: {str(e)[:100]}")
            return []
    
    def _parse_google_events_html(self, html: str) -> List[Dict]:
        """Parse Google Events HTML (simplified)"""
        # This is a simplified parser. In production, you would use BeautifulSoup
        # with proper selectors for Google Events results
        
        events = []
        
        # Mock parsing - implement proper HTML parsing in production
        try:
            # Look for event patterns in HTML
            import re
            
            # Simple regex patterns (will need refinement)
            event_patterns = [
                r'<div[^>]*role="heading"[^>]*>([^<]+)</div>',
                r'data-event-name="([^"]+)"',
                r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
            ]
            
            all_matches = []
            for pattern in event_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                all_matches.extend(matches)
            
            # Create mock events from found names
            for i, event_name in enumerate(set(all_matches)[:10]):  # Limit to 10 unique
                if len(event_name) > 5:  # Filter out too short names
                    events.append({
                        'name': event_name[:100],
                        'source': 'springbee',
                        'url': f'https://example.com/event-{i}',
                        'confidence': 0.7
                    })
            
        except Exception as e:
            print(f"⚠️ HTML parsing error: {str(e)[:50]}")
        
        return events
    
    def test_connection(self) -> Dict:
        """Test SpringBee API connection"""
        try:
            if not self.is_operational():
                return {'success': False, 'error': 'API key not configured'}
            
            # Simple test request
            params = {
                'api_key': self.api_key,
                'url': 'https://httpbin.org/status/200'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'credits_used': response.headers.get('X-Credits-Used', 'Unknown')
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}