"""
SEMANTIC MATCHING ENGINE - ML-Based Event-Attendee Relevance
Uses sentence-transformers for semantic understanding of events and tweets
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Try to import sentence-transformers, fallback to basic matching if not available
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    print("⚠️ sentence-transformers not installed. Using basic keyword matching.")
    print("   Install with: pip install sentence-transformers scikit-learn")

class SemanticMatcher:
    """
    ML-based semantic matcher for event-tweet relevance
    Uses embeddings to understand event context, not just keywords
    """
    
    def __init__(self):
        self.model = None
        self.is_loaded = False
        
        if SEMANTIC_AVAILABLE:
            try:
                # Use a lightweight, fast model for production
                # all-MiniLM-L6-v2 is fast and good for semantic similarity
                print("🤖 Loading ML semantic matching model...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.is_loaded = True
                print("✅ ML semantic matching model loaded successfully")
                print("   📊 Model understands: events, games, matches, concerts, context")
            except Exception as e:
                print(f"⚠️ Failed to load semantic model: {e}")
                print("   Falling back to keyword-based matching")
                self.is_loaded = False
        else:
            self.is_loaded = False
            print("⚠️ sentence-transformers not available. Install with: pip install sentence-transformers scikit-learn")
    
    def _extract_event_entities(self, event_name: str) -> dict:
        """
        Extract key entities from event name to build better context
        Extracts: teams, venues, dates, event types (match, concert, game, etc.)
        """
        import re
        
        entities = {
            'teams': [],
            'venue': None,
            'date': None,
            'event_type': None,
            'keywords': []
        }
        
        event_lower = event_name.lower()
        
        # Extract teams (common patterns: "Team A vs Team B", "Team A v Team B")
        vs_patterns = [
            r'([A-Z][a-zA-Z\s]+?)\s+vs\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|at)',
            r'([A-Z][a-zA-Z\s]+?)\s+v\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|at)',
            r'([A-Z][a-zA-Z\s]+?)\s+vs\.\s+([A-Z][a-zA-Z\s]+?)(?:\s|$|,|at)',
        ]
        
        for pattern in vs_patterns:
            match = re.search(pattern, event_name, re.IGNORECASE)
            if match:
                entities['teams'] = [match.group(1).strip(), match.group(2).strip()]
                break
        
        # Extract venue (common patterns: "at [Venue]", "in [Venue]", "[Venue]")
        venue_patterns = [
            r'at\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,)',
            r'in\s+([A-Z][a-zA-Z\s,]+?)(?:\s|$|,)',
        ]
        for pattern in venue_patterns:
            match = re.search(pattern, event_name, re.IGNORECASE)
            if match:
                entities['venue'] = match.group(1).strip()
                break
        
        # Extract date patterns
        date_patterns = [
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, event_name, re.IGNORECASE)
            if match:
                entities['date'] = match.group(0)
                break
        
        # Extract event type
        event_types = {
            'match': ['match', 'game', 'fixture'],
            'concert': ['concert', 'show', 'performance'],
            'conference': ['conference', 'summit', 'meetup'],
            'festival': ['festival', 'fest'],
            'tournament': ['tournament', 'championship', 'cup'],
        }
        for event_type, keywords in event_types.items():
            if any(kw in event_lower for kw in keywords):
                entities['event_type'] = event_type
                break
        
        # Extract important keywords (capitalized words, numbers)
        words = re.findall(r'\b[A-Z][a-z]+\b|\b\d+\w*\b', event_name)
        entities['keywords'] = [w for w in words if len(w) > 2]
        
        return entities
    
    def _build_enhanced_event_context(self, event_name: str) -> str:
        """
        Build enhanced event context string with extracted entities
        This helps the ML model understand the event better
        """
        entities = self._extract_event_entities(event_name)
        
        context_parts = [event_name]
        
        # Add teams if found
        if entities['teams']:
            context_parts.append(f"Teams: {', '.join(entities['teams'])}")
        
        # Add venue if found
        if entities['venue']:
            context_parts.append(f"Venue: {entities['venue']}")
        
        # Add event type if found
        if entities['event_type']:
            context_parts.append(f"Event type: {entities['event_type']}")
        
        # Add date if found
        if entities['date']:
            context_parts.append(f"Date: {entities['date']}")
        
        # Add keywords
        if entities['keywords']:
            context_parts.append(f"Keywords: {', '.join(entities['keywords'][:5])}")
        
        return ". ".join(context_parts)
    
    def calculate_relevance(self, tweet_text: str, event_name: str, event_context: Optional[str] = None) -> float:
        """
        Calculate semantic relevance between tweet and event
        Uses enhanced context extraction to understand events better
        
        Args:
            tweet_text: The tweet text to match
            event_name: The event name
            event_context: Optional additional context (venue, date, description)
        
        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not self.is_loaded:
            # Fallback to basic keyword matching
            return self._basic_keyword_match(tweet_text, event_name)
        
        try:
            # Build enhanced event context with extracted entities
            enhanced_context = self._build_enhanced_event_context(event_name)
            if event_context:
                enhanced_context = f"{enhanced_context}. {event_context}"
            
            # Get embeddings for both event and tweet
            event_embedding = self.model.encode([enhanced_context], convert_to_numpy=True)
            tweet_embedding = self.model.encode([tweet_text], convert_to_numpy=True)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(event_embedding, tweet_embedding)[0][0]
            
            # Improved normalization: cosine similarity is typically 0.2-0.9 for related text
            # Boost scores to make them more usable
            if similarity > 0.3:
                # High similarity - boost it
                relevance = min(1.0, (similarity - 0.3) * 1.5 + 0.5)
            elif similarity > 0.15:
                # Medium similarity - moderate boost
                relevance = (similarity - 0.15) * 2.0
            else:
                # Low similarity - minimal score
                relevance = similarity * 0.5
            
            # Ensure it's in 0-1 range
            relevance = max(0.0, min(1.0, relevance))
            
            return float(relevance)
            
        except Exception as e:
            print(f"⚠️ Semantic matching error: {e}")
            # Fallback to basic matching
            return self._basic_keyword_match(tweet_text, event_name)
    
    def _basic_keyword_match(self, tweet_text: str, event_name: str) -> float:
        """Fallback basic keyword matching"""
        tweet_lower = tweet_text.lower()
        event_lower = event_name.lower()
        
        score = 0.0
        
        # Exact match
        if event_lower in tweet_lower:
            score += 0.6
        
        # Keyword matches
        keywords = event_name.lower().split()
        for keyword in keywords:
            if len(keyword) > 3 and keyword in tweet_lower:
                score += 0.15
        
        # Engagement signals
        engagement_phrases = ['attending', 'going to', 'see you at', 'got tickets', 'bought tickets']
        for phrase in engagement_phrases:
            if phrase in tweet_lower:
                score += 0.2
                break
        
        return min(1.0, score)
    
    def batch_calculate_relevance(self, tweets: list, event_name: str, event_context: Optional[str] = None) -> list:
        """
        Calculate relevance for multiple tweets at once (more efficient)
        Uses enhanced context extraction
        
        Args:
            tweets: List of tweet texts
            event_name: The event name
            event_context: Optional additional context
        
        Returns:
            List of relevance scores
        """
        if not self.is_loaded or not tweets:
            # Fallback to individual basic matching
            return [self._basic_keyword_match(tweet, event_name) for tweet in tweets]
        
        try:
            # Build enhanced event context
            enhanced_context = self._build_enhanced_event_context(event_name)
            if event_context:
                enhanced_context = f"{enhanced_context}. {event_context}"
            
            # Get embeddings in batch (much faster)
            event_embedding = self.model.encode([enhanced_context], convert_to_numpy=True)
            tweet_embeddings = self.model.encode(tweets, convert_to_numpy=True)
            
            # Calculate similarities
            similarities = cosine_similarity(event_embedding, tweet_embeddings)[0]
            
            # Apply same improved normalization as single calculation
            scores = []
            for sim in similarities:
                if sim > 0.3:
                    score = min(1.0, (sim - 0.3) * 1.5 + 0.5)
                elif sim > 0.15:
                    score = (sim - 0.15) * 2.0
                else:
                    score = sim * 0.5
                scores.append(max(0.0, min(1.0, score)))
            
            return [float(score) for score in scores]
            
        except Exception as e:
            print(f"⚠️ Batch semantic matching error: {e}")
            return [self._basic_keyword_match(tweet, event_name) for tweet in tweets]

# Global instance
_semantic_matcher = None

def get_semantic_matcher() -> SemanticMatcher:
    """Get or create global semantic matcher instance"""
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher

