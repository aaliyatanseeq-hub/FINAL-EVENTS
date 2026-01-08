"""
Location Validation Service
Validates location input and normalizes it before event discovery
"""
import requests
import os
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class LocationValidator:
    """Validates and normalizes location input"""
    
    def __init__(self):
        self.serp_api_key = os.getenv('SERP_API_KEY')
        # Common valid location patterns
        self.valid_patterns = [
            r'^[A-Za-z\s]+,\s*[A-Z]{2}$',  # City, State (e.g., "New York, NY")
            r'^[A-Za-z\s]+,\s*[A-Za-z\s]+$',  # City, Country (e.g., "London, UK")
            r'^[A-Za-z\s]+$',  # City only (e.g., "New York")
        ]
    
    def validate_location(self, location: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate location input
        
        Returns:
            (is_valid, normalized_location, error_message)
        """
        if not location or len(location.strip()) < 2:
            return False, None, "Location must be at least 2 characters long"
        
        location = location.strip()
        
        # Basic validation: check if it looks like a location
        # Reject obvious non-locations (too short, all numbers, etc.)
        if len(location) < 3:
            return False, None, f"'{location}' is too short to be a valid location. Please enter a city name (e.g., 'New York', 'London', 'Los Angeles')"
        
        # Check if it's all numbers or special characters
        if location.replace(' ', '').replace(',', '').isdigit():
            return False, None, f"'{location}' doesn't appear to be a valid location. Please enter a city name."
        
        # Try to validate using SerpAPI geocoding if available
        if self.serp_api_key:
            is_valid, normalized, error = self._validate_with_serpapi(location)
            if is_valid:
                return True, normalized, None
            if error:
                return False, None, error
        
        # Fallback: basic pattern matching
        # Accept if it contains letters and has reasonable length
        if any(c.isalpha() for c in location) and len(location) >= 3:
            # Normalize: capitalize properly
            normalized = self._normalize_location(location)
            return True, normalized, None
        
        return False, None, f"'{location}' doesn't appear to be a valid location. Please enter a city name (e.g., 'New York', 'London', 'Los Angeles')"
    
    def _validate_with_serpapi(self, location: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate location using SerpAPI geocoding"""
        try:
            params = {
                'q': location,
                'engine': 'google',
                'api_key': self.serp_api_key,
                'hl': 'en',
                'gl': 'us'
            }
            
            response = requests.get(
                'https://serpapi.com/search',
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got location results
                if 'local_results' in data or 'organic_results' in data:
                    # Try to extract location from results
                    results = data.get('local_results') or data.get('organic_results', [])
                    if results:
                        # Found location results, location is valid
                        normalized = self._extract_location_from_results(results, location)
                        return True, normalized, None
                
                # Check for "did you mean" suggestions
                if 'search_information' in data:
                    suggestions = data.get('search_information', {}).get('query_displayed')
                    if suggestions and suggestions != location:
                        return False, None, f"Location not found. Did you mean '{suggestions}'?"
                
                # No results found
                return False, None, f"'{location}' is not a recognized location. Please enter a valid city name (e.g., 'New York', 'London', 'Los Angeles')"
            
            # API error - fall back to basic validation
            return False, None, None
            
        except Exception as e:
            # API call failed - fall back to basic validation
            print(f"⚠️ Location validation API error: {e}")
            return False, None, None
    
    def _extract_location_from_results(self, results: list, original: str) -> str:
        """Extract normalized location from API results"""
        if not results:
            return self._normalize_location(original)
        
        # Try to get location from first result
        first_result = results[0] if results else {}
        
        # Check for address or location fields
        address = first_result.get('address') or first_result.get('location')
        if address:
            # Extract city name from address
            if isinstance(address, str):
                parts = address.split(',')
                if parts:
                    return self._normalize_location(parts[0].strip())
        
        # Fallback to normalized original
        return self._normalize_location(original)
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string (capitalize properly)"""
        # Handle common formats
        parts = location.split(',')
        normalized_parts = []
        
        for part in parts:
            part = part.strip()
            # Capitalize each word
            words = part.split()
            capitalized = ' '.join(word.capitalize() for word in words)
            normalized_parts.append(capitalized)
        
        return ', '.join(normalized_parts)
    
    def validate_date_range(self, start_date: str, end_date: str) -> Tuple[bool, Optional[str], Optional[datetime], Optional[datetime]]:
        """
        Validate date range and ensure it's within 3 months
        
        Returns:
            (is_valid, error_message, start_datetime, end_datetime)
        """
        
        # Parse dates
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)
        
        if not start_dt:
            return False, f"Invalid start date format: '{start_date}'. Please use YYYY-MM-DD format (e.g., 2025-01-15)", None, None
        
        if not end_dt:
            return False, f"Invalid end date format: '{end_date}'. Please use YYYY-MM-DD format (e.g., 2025-04-15)", None, None
        
        # Check if start date is in the past
        today = datetime.now().date()
        if start_dt.date() < today:
            return False, f"Start date '{start_date}' is in the past. Please select a future date.", None, None
        
        # Check if end date is before start date
        if end_dt < start_dt:
            return False, f"End date '{end_date}' must be after start date '{start_date}'.", None, None
        
        # Check if date range exceeds 3 months (90 days)
        days_diff = (end_dt.date() - start_dt.date()).days
        if days_diff > 90:
            max_end = start_dt + timedelta(days=90)
            return False, f"Date range exceeds 3 months (90 days). Maximum end date: {max_end.strftime('%Y-%m-%d')}", None, None
        
        # Check if end date is too far in the future (more than 3 months from today)
        max_future_date = today + timedelta(days=90)
        if end_dt.date() > max_future_date:
            return False, f"End date '{end_date}' is more than 3 months in the future. Maximum date: {max_future_date.strftime('%Y-%m-%d')}", None, None
        
        return True, None, start_dt, end_dt
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        
        # Try multiple date formats
        formats = [
            '%Y-%m-%d',      # 2025-01-15 (ISO format - preferred)
            '%m/%d/%Y',      # 01/15/2025
            '%d/%m/%Y',      # 15/01/2025
            '%B %d, %Y',     # January 15, 2025
            '%b %d, %Y',     # Jan 15, 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None

