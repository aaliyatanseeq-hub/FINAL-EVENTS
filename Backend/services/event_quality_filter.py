"""
Enterprise-Grade Event Quality Filter
Removes noise from SerpAPI/Ticketmaster data using rule-based filters + classification
"""
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class QualityScore:
    """Event quality metrics"""
    is_real_event: bool
    quality_score: float  # 0.0 to 1.0
    clean_category: str
    rejection_reasons: list
    confidence: float

class EventQualityFilter:
    """
    Multi-layer filtering system:
    1. Rule-based filters (cheap, deterministic)
    2. Pattern matching for noise detection
    3. Location validation
    4. Quality scoring
    """
    
    # Noise patterns - events matching these are likely not real events
    # TIGHTENED: More aggressive filtering to catch all noise
    NOISE_PATTERNS = [
        # Season passes and tickets (enhanced patterns)
        r'\b(season\s+pass|season\s+ticket|full\s+season|half\s+season|season\s+package)\b',
        r'\b(voucher|vouchers|discount\s+pass|membership\s+card|access\s+card)\b',
        r'\b(bundle|bundles|package|packages|ticket\s+package)\b',
        r'\b(id\s+card|member\s+card|access\s+card|pass\s+card)\b',
        # Season ID patterns: "24-25 Diamond ID", "24-25 Gold ID", etc.
        r'\d{2}-\d{2}\s+(diamond|gold|silver|platinum|regions|staff|bronze|premium|vip|premium|elite)\s+id\b',
        r'\d{2}-\d{2}\s+[a-z]+\s+id\b',  # Any "XX-XX [word] ID" pattern
        r'\b\d{2}-\d{2}\s+id\b',  # "24-25 ID" pattern
        r'\b\d{2}-\d{2}\s+(diamond|gold|silver|platinum|regions|staff)\b',  # "24-25 Diamond" without ID
        
        # Test and placeholder events (enhanced)
        r'\b(test\s+event|test\s+scan|test\s+only|non-manifested|test\s+locations|test\s+venue|test\s+data)\b',
        r'\btest\s+\w+',  # "Test [anything]" - catches "Test Locations", "Test Event", etc.
        r'\b(dnc|do\s+not\s+contact|placeholder|dummy|sample)\b',
        r'\b(shell\s+event|overtime\s+experience|mock\s+event)\b',
        
        # Generic utility events
        r'\b(share|sharing|transfer|resale|exchange)\b.*\b(ticket|pass)\b',
        r'\b(gift\s+card|store\s+credit|refund|credit)\b',
        r'\b(ticket\s+transfer|ticket\s+resale|ticket\s+exchange)\b',
        
        # Offers and promotions (not real events) - TIGHTENED
        r'\b(buffet\s+offer|dining\s+offer|food\s+offer|meal\s+offer|special\s+offer)\b',
        r'\b\w+\s+offer$',  # Any "[word] Offer" at end - catches "Buffet Offer", "Special Offer", etc.
        r'\b(vip\s+experience|igloo\s+experience|premium\s+experience|exclusive\s+experience)\b',  # Experience add-ons
        r'\b(upgrade|add-on|addon|package\s+deal)\b',  # Upgrades/add-ons
        
        # Venue TBD patterns (too generic)
        r'\b(venue\s+tbd|venue\s+tba|venue\s+tbc|tbd\s+venue|various\s+venues)\b',
        r'\(venue\s+tbd\)',  # "(Venue TBD)" pattern
        
        # Suspicious patterns
        r'^\d+$',  # Just numbers
        r'^[A-Z0-9]{10,}$',  # Long alphanumeric codes
        r'^\d{2}-\d{2}\s+\w+$',  # "24-25 [word]" without context (likely season pass)
        r'^\d{2}-\d{2}$',  # Just "24-25" (season identifier)
    ]
    
    # Invalid venue patterns
    # Note: We allow location-only venues for sports events (e.g., "Kuwait" is valid for sports)
    INVALID_VENUE_PATTERNS = [
        r'\b(test|tbd|tba|tbc|various|multiple|online|virtual)\b',
        r'\b(ga\s+events|general\s+admission\s+only)\b',
        r'^\s*$',  # Empty or whitespace only
        r'\(venue\s+tbd\)',  # "(Venue TBD)" pattern - reject this
        r'\(venue\s+tba\)',  # "(Venue TBA)" pattern
    ]
    
    # Location mismatch indicators
    LOCATION_MISMATCH_INDICATORS = {
        'US': ['United States', 'USA', 'America', 'US'],
        'Europe': ['Europe', 'EU', 'European'],
        'Asia': ['Asia', 'Asian', 'China', 'Japan', 'Korea'],
    }
    
    def __init__(self):
        # Compile regex patterns for performance
        self.noise_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.NOISE_PATTERNS]
        self.venue_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.INVALID_VENUE_PATTERNS]
    
    def filter_event(self, event: Dict[str, Any], search_location: str) -> QualityScore:
        """
        Main filtering function - returns quality score and filtering decision
        
        Args:
            event: Event dictionary with fields: event_name, exact_venue, location, exact_date, category
            search_location: The location user searched for (e.g., "Hongkong")
        
        Returns:
            QualityScore with is_real_event, quality_score, clean_category, rejection_reasons
        """
        rejection_reasons = []
        quality_score = 1.0
        confidence = 1.0
        
        # Extract event fields
        event_name = str(event.get('event_name', '')).strip()
        venue = str(event.get('exact_venue', '')).strip()
        location = str(event.get('location', '')).strip()
        date_str = event.get('exact_date', '')
        category = event.get('category', 'other')
        source = event.get('source', 'unknown')
        
        # === LAYER 1: Rule-Based Filters (Cheap, Deterministic) ===
        
        # 1.1: Check for noise patterns in event name
        if self._matches_noise_pattern(event_name):
            rejection_reasons.append(f"Event name matches noise pattern: '{event_name[:50]}'")
            return QualityScore(
                is_real_event=False,
                quality_score=0.0,
                clean_category='noise',
                rejection_reasons=rejection_reasons,
                confidence=1.0
            )
        
        # 1.2: Check for invalid venue
        # Allow location-only venues for sports events (e.g., "Kuwait" is valid for sports matches)
        is_sports_event = 'sports' in category.lower() or any(
            keyword in event_name.lower() 
            for keyword in ['vs', 'match', 'championship', 'tournament', 'cup', 'league', 'game']
        )
        
        if venue and self._matches_invalid_venue(venue):
            # For sports events, if venue is just a location (no "(Venue TBD)" suffix), allow it
            if is_sports_event and not re.search(r'\(venue\s+tbd\)|\(venue\s+tba\)', venue, re.IGNORECASE):
                # Sports event with location-only venue is acceptable - don't reject
                pass
            else:
                rejection_reasons.append(f"Invalid venue pattern: '{venue[:50]}'")
                quality_score -= 0.5
        
        # 1.3: Validate location consistency
        location_issue = self._validate_location_consistency(location, venue, search_location)
        if location_issue:
            rejection_reasons.append(location_issue)
            quality_score -= 0.3
        
        # 1.4: Check date reasonableness
        date_issue = self._validate_date_reasonableness(date_str, event_name)
        if date_issue:
            rejection_reasons.append(date_issue)
            quality_score -= 0.2
        
        # 1.5: Check for suspicious combinations
        if self._has_suspicious_combination(event_name, venue, date_str):
            rejection_reasons.append("Suspicious combination of fields")
            quality_score -= 0.4
        
        # === LAYER 2: Quality Scoring ===
        
        # 2.1: Event name quality
        name_score = self._score_event_name(event_name)
        quality_score = (quality_score * 0.6) + (name_score * 0.4)
        
        # 2.2: Venue quality
        venue_score = self._score_venue(venue)
        quality_score = (quality_score * 0.7) + (venue_score * 0.3)
        
        # 2.3: Category quality
        category_score = self._score_category(category, event_name)
        quality_score = (quality_score * 0.8) + (category_score * 0.2)
        
        # 2.4: Source quality
        source_score = self._score_source(source)
        quality_score = (quality_score * 0.9) + (source_score * 0.1)
        
        # 2.5: Date proximity bonus
        date_proximity_bonus = self._calculate_date_proximity_bonus(date_str)
        quality_score = min(1.0, quality_score + date_proximity_bonus)
        
        # === LAYER 3: Final Decision ===
        
        # Determine clean category
        clean_category = self._determine_clean_category(category, event_name, venue)
        
        # Calculate confidence
        confidence = self._calculate_confidence(quality_score, rejection_reasons, event_name, venue)
        
        # Final decision: is_real_event
        is_real_event = quality_score >= 0.5 and len(rejection_reasons) == 0
        
        # If quality is very low, mark as noise even if no explicit rejection
        if quality_score < 0.3:
            is_real_event = False
            if not rejection_reasons:
                rejection_reasons.append("Quality score too low")
        
        return QualityScore(
            is_real_event=is_real_event,
            quality_score=max(0.0, min(1.0, quality_score)),
            clean_category=clean_category,
            rejection_reasons=rejection_reasons,
            confidence=confidence
        )
    
    def _matches_noise_pattern(self, text: str) -> bool:
        """Check if text matches any noise pattern"""
        if not text:
            return True
        text_lower = text.lower()
        for pattern in self.noise_patterns:
            if pattern.search(text_lower):
                return True
        return False
    
    def _matches_invalid_venue(self, venue: str) -> bool:
        """Check if venue matches invalid patterns"""
        if not venue or len(venue.strip()) < 3:
            return True
        venue_lower = venue.lower()
        for pattern in self.venue_patterns:
            if pattern.search(venue_lower):
                return True
        return False
    
    def _validate_location_consistency(self, location: str, venue: str, search_location: str) -> Optional[str]:
        """
        Validate location consistency
        Returns error message if inconsistency detected, None otherwise
        """
        if not location or not search_location:
            return None
        
        location_lower = location.lower()
        search_lower = search_location.lower()
        venue_lower = venue.lower() if venue else ''
        
        # Check for obvious mismatches
        # If searching in Hongkong but venue/location suggests US/Europe
        if 'hongkong' in search_lower or 'hong kong' in search_lower:
            if any(indicator in location_lower or indicator in venue_lower 
                   for indicator in ['united states', 'usa', 'america', 'new york', 'los angeles', 'london', 'paris']):
                return f"Location mismatch: searching '{search_location}' but found US/Europe indicators"
        
        # If searching in US but venue suggests Asia
        if any(indicator in search_lower for indicator in ['united states', 'usa', 'america']):
            if any(indicator in location_lower or indicator in venue_lower 
                   for indicator in ['hong kong', 'hongkong', 'tokyo', 'beijing', 'shanghai']):
                return f"Location mismatch: searching '{search_location}' but found Asia indicators"
        
        return None
    
    def _validate_date_reasonableness(self, date_str: str, event_name: str) -> Optional[str]:
        """Validate date is reasonable given event name"""
        if not date_str or date_str == 'Date not specified':
            return "Missing date"
        
        # Check if date is very far in future AND event name has season/test words
        try:
            # Try multiple date formats
            date_obj = None
            date_formats = ['%B %d, %Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
            date_str_clean = date_str.split()[0] if ' ' in date_str else date_str
            
            for fmt in date_formats:
                fmt_clean = fmt.split()[0] if ' ' in fmt else fmt
                try:
                    date_obj = datetime.strptime(date_str_clean, fmt_clean)
                    break
                except:
                    continue
            
            if date_obj:
                days_ahead = (date_obj - datetime.now()).days
                
                # If more than 2 years ahead and has suspicious words
                if days_ahead > 730 and any(word in event_name.lower() for word in ['season', 'pass', 'voucher', 'test', 'id']):
                    return f"Date too far in future ({days_ahead} days) with suspicious event name"
        except:
            pass
        
        return None
    
    def _has_suspicious_combination(self, event_name: str, venue: str, date_str: str) -> bool:
        """Check for suspicious combinations of fields"""
        event_lower = event_name.lower()
        
        # Very short event name + generic venue
        if len(event_name) < 5 and venue.lower() in ['various', 'tbd', 'tba']:
            return True
        
        # Event name is just numbers/codes + no proper venue
        if re.match(r'^[A-Z0-9\s-]{5,}$', event_name) and not venue:
            return True
        
        # Season ID patterns: "24-25 [Type] ID" - these are always noise
        if re.search(r'\d{2}-\d{2}\s+\w+\s+id', event_lower):
            return True
        
        # "Test" followed by any word (not just specific words)
        if re.search(r'\btest\s+\w+', event_lower):
            return True
        
        # "[Word] Offer" patterns (buffet offers, dining offers, etc.)
        # Catch any "[word] Offer" pattern - these are usually promotions, not events
        if re.search(r'\w+\s+offer$', event_lower):
            return True
        
        # "VIP Experience", "Igloo Experience" - utility add-ons
        if 'experience' in event_lower and any(word in event_lower for word in ['vip', 'igloo', 'premium', 'exclusive']):
            return True
        
        return False
    
    def _score_event_name(self, event_name: str) -> float:
        """Score event name quality (0.0 to 1.0)"""
        if not event_name or len(event_name.strip()) < 3:
            return 0.0
        
        score = 0.5  # Base score
        
        # Bonus for having artist/team names (capitalized words)
        words = event_name.split()
        capitalized_words = [w for w in words if w and w[0].isupper()]
        if len(capitalized_words) >= 2:
            score += 0.2
        
        # Bonus for reasonable length (10-100 chars)
        if 10 <= len(event_name) <= 100:
            score += 0.2
        
        # Penalty for all caps (shouting)
        if event_name.isupper() and len(event_name) > 10:
            score -= 0.1
        
        # Penalty for too many special characters
        special_char_ratio = sum(1 for c in event_name if not c.isalnum() and c != ' ') / len(event_name)
        if special_char_ratio > 0.3:
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _score_venue(self, venue: str) -> float:
        """Score venue quality (0.0 to 1.0)"""
        if not venue or len(venue.strip()) < 3:
            return 0.0
        
        score = 0.6  # Base score
        
        # Bonus for specific venue names (not generic)
        if venue.lower() not in ['various venues', 'tbd', 'tba', 'online', 'virtual']:
            score += 0.3
        
        # Bonus for having address-like structure (contains comma or street indicators)
        if ',' in venue or any(word in venue.lower() for word in ['street', 'avenue', 'road', 'st', 'ave', 'blvd']):
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _score_category(self, category: str, event_name: str) -> float:
        """Score category quality (0.0 to 1.0)"""
        # High-value categories
        high_value = ['music', 'sports', 'arts', 'theater', 'comedy', 'food']
        if category.lower() in high_value:
            return 1.0
        
        # Medium-value categories
        medium_value = ['conferences', 'networking', 'workshops', 'festivals']
        if category.lower() in medium_value:
            return 0.7
        
        # Low-value or unknown
        if category.lower() == 'other':
            # Check if event name suggests a category
            if any(word in event_name.lower() for word in ['concert', 'game', 'match', 'show', 'festival']):
                return 0.5
            return 0.3
        
        return 0.5
    
    def _score_source(self, source: str) -> float:
        """Score source quality (0.0 to 1.0)"""
        source_scores = {
            'serpapi': 0.9,
            'ticketmaster': 0.8,
            'predicthq': 0.7,
            'unknown': 0.5
        }
        return source_scores.get(source.lower(), 0.5)
    
    def _calculate_date_proximity_bonus(self, date_str: str) -> float:
        """Calculate bonus for events happening soon"""
        if not date_str or date_str == 'Date not specified':
            return 0.0
        
        try:
            date_obj = datetime.strptime(date_str, '%B %d, %Y')
            days_ahead = (date_obj - datetime.now()).days
            
            # Bonus for events within 30 days
            if 0 <= days_ahead <= 30:
                return 0.1
            # Bonus for events within 90 days
            elif 31 <= days_ahead <= 90:
                return 0.05
            # Penalty for events more than 1 year away
            elif days_ahead > 365:
                return -0.05
        except:
            pass
        
        return 0.0
    
    def _determine_clean_category(self, category: str, event_name: str, venue: str) -> str:
        """Determine clean category from event data"""
        # If category is already good, use it
        if category and category.lower() not in ['other', 'unknown', '']:
            return category.lower()
        
        # Infer from event name
        event_lower = event_name.lower()
        venue_lower = venue.lower() if venue else ''
        
        # Music indicators
        if any(word in event_lower for word in ['concert', 'music', 'band', 'singer', 'dj', 'live music']):
            return 'music'
        
        # Sports indicators
        if any(word in event_lower for word in ['game', 'match', 'championship', 'tournament', 'cup', 'league', 'vs', 'versus']):
            return 'sports'
        
        # Arts indicators
        if any(word in event_lower for word in ['exhibition', 'gallery', 'art', 'museum']):
            return 'arts'
        
        # Theater indicators
        if any(word in event_lower for word in ['theater', 'theatre', 'play', 'drama', 'show']):
            return 'theater'
        
        # Food indicators
        if any(word in event_lower or word in venue_lower for word in ['food', 'restaurant', 'dining', 'culinary', 'tasting']):
            return 'food'
        
        # Default
        return 'other'
    
    def _calculate_confidence(self, quality_score: float, rejection_reasons: list, 
                             event_name: str, venue: str) -> float:
        """Calculate confidence in the quality assessment"""
        confidence = quality_score
        
        # Higher confidence if we have good event name and venue
        if event_name and len(event_name) > 10 and venue and len(venue) > 5:
            confidence = min(1.0, confidence + 0.1)
        
        # Lower confidence if we have rejection reasons but still passing
        if rejection_reasons and quality_score >= 0.5:
            confidence = max(0.3, confidence - 0.2)
        
        return max(0.0, min(1.0, confidence))

