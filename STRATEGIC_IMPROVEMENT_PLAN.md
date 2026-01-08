# 🎯 Strategic Improvement Plan - Event Intelligence Platform

## Executive Summary

**Current State:** Production-ready system with solid architecture, but heuristic-heavy matching logic.

**Target State:** Industry-standard system with ML-based matching, evaluation infrastructure, and scalable abstractions.

**Timeline:** Phased approach over 3-6 months

---

## 📊 Current Strengths (Keep & Enhance)

### ✅ What's Working Well

1. **Architecture & Layering**
   - Clear separation: API → Engine → Service → DB
   - Explicit caching strategy
   - Quality filter as separate component
   - Multi-source aggregation

2. **Multi-Source Event Logic**
   - Source weighting (50/25/25)
   - Strict date filtering
   - Hash + similarity deduplication
   - Provider-specific parsing

3. **Operational Thinking**
   - Cache keys & TTLs
   - Analytics tracking
   - Rate-limit awareness
   - Graceful degradation

**Action:** Keep these patterns, enhance with better abstractions.

---

## 🚨 Critical Gaps Identified

### Gap 1: ML/Relevance is Too Heuristic-Heavy
**Current:** Keyword if/else logic for attendee matching
**Problem:** False positives/negatives at scale, doesn't generalize across domains
**Impact:** High - Core functionality limitation

### Gap 2: No Offline Evaluation Loop
**Current:** No labeled datasets, test sets, or metrics
**Problem:** Can't measure improvements, no regression detection
**Impact:** High - Blocks systematic improvement

### Gap 3: Event Model is Flat
**Current:** Simple events table with basic fields
**Problem:** No entity extraction, relations, or canonicalization
**Impact:** Medium - Limits search and matching capabilities

### Gap 4: Attendee/Location Inference is Basic
**Current:** Country-level, keyword-based only
**Problem:** Misses nuanced signals, limited accuracy
**Impact:** Medium - Affects targeting quality

### Gap 5: Missing Operational Readiness
**Current:** Basic logging
**Problem:** Hard to debug at scale, no tracing
**Impact:** Medium - Operational burden

---

## 🎯 Strategic Improvement Plan

### Phase 1: Foundation (Weeks 1-4)
**Goal:** Build evaluation infrastructure and data collection

#### 1.1 Create Evaluation Infrastructure
- **Labeled Dataset Creation**
  - Collect 500-1000 high-quality (event, post) pairs
  - Cover multiple domains: sports, music, conferences, festivals
  - Label: relevant (1) / not relevant (0)
  - Store in `evaluation_dataset` table

- **Test Set Management**
  - Split: 70% train, 20% validation, 10% test
  - Version control for datasets
  - Track dataset versions used for each model

- **Metrics Framework**
  - Precision, Recall, F1-score per domain
  - Top-K accuracy (top 10, top 50)
  - False positive/negative analysis
  - Confusion matrix per domain

- **Evaluation Script**
  ```python
  # Backend/evaluation/evaluator.py
  class EventPostEvaluator:
      def evaluate_model(model, test_set):
          # Run model on test set
          # Calculate metrics
          # Generate report
          # Track regressions
  ```

**Deliverables:**
- `Backend/evaluation/` directory
- Labeled dataset (500+ pairs)
- Evaluation script with metrics
- Baseline metrics report

---

#### 1.2 Implement Structured Logging
- **Structured Logs**
  - Use `structlog` (already in requirements)
  - Log units: "event_search", "attendee_search"
  - Track: candidates per layer, drop reasons, timing

- **Log Schema**
  ```python
  {
      "event": "attendee_search",
      "event_name": "...",
      "candidates_twitter": 150,
      "candidates_reddit": 30,
      "filtered_relevance": 45,
      "filtered_quality": 12,
      "final_count": 33,
      "drop_reasons": {
          "low_relevance": 105,
          "duplicate": 8
      },
      "duration_ms": 1234
  }
  ```

- **Tracing**
  - Add request IDs to trace full request lifecycle
  - Log each decision point (cache hit, DB hit, API call)

**Deliverables:**
- Structured logging throughout
- Request tracing
- Log aggregation setup

---

### Phase 2: ML-Based Matching (Weeks 5-8)
**Goal:** Replace heuristic matching with ML-based ranking

#### 2.1 Build Event↔Post Matcher Component
- **Architecture**
  ```
  Backend/matching/
  ├── event_post_matcher.py    # Main matcher interface
  ├── models/
  │   ├── embedding_matcher.py  # Embedding-based (fast)
  │   ├── cross_encoder.py      # Cross-encoder (accurate)
  │   └── hybrid_matcher.py     # Combines both
  ├── features/
  │   ├── text_features.py      # Text similarity
  │   ├── temporal_features.py   # Time delta
  │   ├── geo_features.py        # Geo delta
  │   └── entity_features.py    # Entity overlap
  └── training/
      ├── train_model.py
      └── evaluate_model.py
  ```

- **Feature Engineering**
  ```python
  class EventPostFeatures:
      def extract_features(event, post):
          return {
              # Text features
              "text_similarity": cosine_similarity(
                  embed(event.name), embed(post.text)
              ),
              "keyword_overlap": jaccard_similarity(
                  extract_keywords(event.name),
                  extract_keywords(post.text)
              ),
              
              # Temporal features
              "time_delta_days": abs(
                  event.date - post.created_at
              ),
              "is_same_day": event.date.date() == post.created_at.date(),
              
              # Geo features
              "geo_distance": haversine(
                  event.location, post.location
              ),
              "same_country": event.country == post.country,
              
              # Entity features
              "entity_overlap": len(
                  set(event.entities) & set(post.entities)
              ),
              "entity_coverage": entity_overlap / len(event.entities)
          }
  ```

- **Model Options**
  1. **Embedding-Based (Fast)**
     - Use sentence-transformers (all-MiniLM-L6-v2)
     - Cosine similarity threshold
     - Good for: Real-time, high-volume

  2. **Cross-Encoder (Accurate)**
     - Fine-tuned BERT/RoBERTa
     - Binary classification: relevant/not relevant
     - Good for: High precision, lower volume

  3. **Hybrid (Recommended)**
     - Embedding for candidate retrieval (top 100)
     - Cross-encoder for final ranking (top 10)
     - Best of both worlds

- **Training Pipeline**
  ```python
  # 1. Load labeled dataset
  # 2. Extract features
  # 3. Train cross-encoder on (event, post) pairs
  # 4. Evaluate on test set
  # 5. Save model
  # 6. Deploy with versioning
  ```

**Deliverables:**
- Event↔Post matcher component
- Feature extraction pipeline
- Trained model (baseline)
- Integration with attendee engine

---

#### 2.2 Replace Heuristic Scoring
- **Migration Strategy**
  1. Keep heuristic as fallback
  2. Add ML matcher as primary
  3. A/B test: 50% heuristic, 50% ML
  4. Monitor metrics, gradually shift to 100% ML

- **Integration Points**
  ```python
  # Backend/engines/attendee_engine.py
  def _calculate_tweet_relevance_priority(self, tweet_text, event_name):
      # NEW: Use ML matcher
      ml_score = self.event_post_matcher.score(event_name, tweet_text)
      
      # FALLBACK: Keep heuristic for edge cases
      if ml_score is None:
          return self._heuristic_score(tweet_text, event_name)
      
      return ml_score
  ```

**Deliverables:**
- ML matcher integrated
- A/B testing framework
- Gradual rollout plan

---

### Phase 3: Richer Event Model (Weeks 9-12)
**Goal:** Extract entities, build relations, enable better search

#### 3.1 Entity Extraction & Canonicalization
- **Entity Types**
  - Teams/Artists (e.g., "New York Knicks", "Taylor Swift")
  - Venues (e.g., "Madison Square Garden", "MSG")
  - Locations (e.g., "New York", "NYC")
  - Dates/Times (structured datetime objects)

- **Entity Extraction**
  ```python
  # Backend/entities/entity_extractor.py
  class EntityExtractor:
      def extract_entities(event_name, venue, location):
          # Use NER model or rule-based
          # Extract: teams, artists, venues, locations
          # Return: structured entity objects
  ```

- **Canonicalization**
  - "Knicks" → "New York Knicks"
  - "MSG" → "Madison Square Garden"
  - "NYC" → "New York"
  - Store in `entity_canonical_forms` table

- **Database Schema**
  ```sql
  CREATE TABLE entities (
      id SERIAL PRIMARY KEY,
      entity_type VARCHAR(50),  -- team, artist, venue, location
      canonical_name VARCHAR(200),
      aliases JSON,  -- ["Knicks", "NY Knicks", "New York Knicks"]
      created_at TIMESTAMP
  );
  
  CREATE TABLE event_entities (
      event_id INTEGER REFERENCES events(id),
      entity_id INTEGER REFERENCES entities(id),
      PRIMARY KEY (event_id, entity_id)
  );
  ```

**Deliverables:**
- Entity extraction pipeline
- Canonicalization system
- Database schema updates
- Entity-event relations

---

#### 3.2 Search Index Integration
- **Option 1: PostgreSQL Full-Text Search**
  - Use `tsvector` for event name search
  - Good for: Simple, no new dependencies

- **Option 2: Meilisearch (Recommended)**
  - Fast, typo-tolerant search
  - Good for: Better UX, fuzzy matching

- **Option 3: OpenSearch/Elasticsearch**
  - Full-featured, complex
  - Good for: Enterprise scale

**Recommendation:** Start with PostgreSQL full-text, migrate to Meilisearch if needed.

**Deliverables:**
- Search index setup
- Search API endpoint
- Integration with event discovery

---

### Phase 4: Enhanced Location Inference (Weeks 13-16)
**Goal:** More nuanced location signals while maintaining privacy

#### 4.1 Multi-Signal Location Inference
- **Current:** Country-level, keyword-based
- **Enhanced:** Multiple signals with privacy bounds

- **New Signals (Privacy-Safe)**
  1. **Tweet Place Data** (already implemented)
  2. **User Location Field** (already implemented)
  3. **Content Inference** (already implemented)
  4. **Timezone Inference** (already implemented)
  5. **Network Signals** (NEW - privacy-safe)
     - Followers' locations (aggregated, anonymized)
     - Not individual tracking, just aggregate patterns
  6. **Behavioral Patterns** (NEW - privacy-safe)
     - Event attendance history (if user mentions past events)
     - Not tracking individuals, just patterns

- **Privacy Policy**
  - Only aggregate data
  - No individual tracking
  - Country-level only (no city/precise)
  - Documented in privacy policy

**Deliverables:**
- Enhanced location inference
- Privacy policy documentation
- Multi-signal scoring

---

### Phase 5: Stronger Abstractions (Weeks 17-20)
**Goal:** Make system scalable to 10+ sources

#### 5.1 Source Adapter Interface
```python
# Backend/sources/base.py
from abc import ABC, abstractmethod

class SourceAdapter(ABC):
    """Base class for all event sources"""
    
    @abstractmethod
    def fetch_events(self, location, start_date, end_date, categories):
        """Fetch events from this source"""
        pass
    
    @abstractmethod
    def parse_event(self, raw_data):
        """Parse raw API response to ResearchEvent"""
        pass
    
    @property
    @abstractmethod
    def source_name(self):
        """Return source identifier"""
        pass
    
    @property
    @abstractmethod
    def priority(self):
        """Return priority (1-10)"""
        pass
    
    @property
    @abstractmethod
    def weight(self):
        """Return weight for ratio distribution"""
        pass

# Backend/sources/serpapi_adapter.py
class SerpAPIAdapter(SourceAdapter):
    source_name = "serpapi"
    priority = 1
    weight = 0.5  # 50%
    
    def fetch_events(self, ...):
        # SerpAPI-specific implementation
        pass

# Backend/sources/predicthq_adapter.py
class PredictHQAdapter(SourceAdapter):
    source_name = "predicthq"
    priority = 2
    weight = 0.25  # 25%
    
    def fetch_events(self, ...):
        # PredictHQ-specific implementation
        pass
```

**Benefits:**
- Easy to add new sources (just implement interface)
- Consistent error handling
- Unified configuration
- Testable in isolation

**Deliverables:**
- Source adapter interface
- Refactor existing sources
- Documentation for adding new sources

---

#### 5.2 Quality Policy Objects
```python
# Backend/quality/policies.py
class QualityPolicy(ABC):
    """Base class for quality policies"""
    
    @abstractmethod
    def should_accept(self, event):
        """Return (accept: bool, reason: str, score: float)"""
        pass

class DefaultQualityPolicy(QualityPolicy):
    """Default quality policy"""
    def should_accept(self, event):
        # Current quality filter logic
        pass

class StrictQualityPolicy(QualityPolicy):
    """Stricter quality policy for premium tier"""
    def should_accept(self, event):
        # More aggressive filtering
        pass

class LenientQualityPolicy(QualityPolicy):
    """More lenient for discovery mode"""
    def should_accept(self, event):
        # Less aggressive filtering
        pass
```

**Benefits:**
- Per-market tuning (different policies per location)
- A/B testing different policies
- Easy to adjust thresholds

**Deliverables:**
- Quality policy interface
- Multiple policy implementations
- Policy selection mechanism

---

### Phase 6: Operational Readiness (Weeks 21-24)
**Goal:** Production-grade observability and monitoring

#### 6.1 Enhanced Logging & Tracing
- **Structured Logs** (from Phase 1)
- **Distributed Tracing**
  - Add OpenTelemetry or similar
  - Trace requests across services
  - Track timing at each layer

- **Metrics Dashboard**
  - Prometheus metrics
  - Grafana dashboards
  - Track: latency, error rates, cache hit rates

**Deliverables:**
- Distributed tracing
- Metrics collection
- Dashboard setup

---

#### 6.2 Nightly Evaluation Job
```python
# Backend/evaluation/nightly_job.py
def run_nightly_evaluation():
    """Run evaluation on golden dataset every night"""
    # 1. Load test set
    # 2. Run current model
    # 3. Calculate metrics
    # 4. Compare to baseline
    # 5. Alert if regression detected
    # 6. Generate report
```

**Deliverables:**
- Nightly evaluation script
- Regression detection
- Automated alerts

---

## 📋 Implementation Priority

### Must-Have (P0)
1. ✅ Evaluation infrastructure (Phase 1.1)
2. ✅ Structured logging (Phase 1.2)
3. ✅ ML-based matching (Phase 2)

### Should-Have (P1)
4. ✅ Entity extraction (Phase 3.1)
5. ✅ Source adapters (Phase 5.1)
6. ✅ Quality policies (Phase 5.2)

### Nice-to-Have (P2)
7. ✅ Search index (Phase 3.2)
8. ✅ Enhanced location (Phase 4)
9. ✅ Operational monitoring (Phase 6)

---

## 🎯 Success Metrics

### Phase 1 Success
- [ ] 500+ labeled examples collected
- [ ] Evaluation script runs and produces metrics
- [ ] Baseline metrics established
- [ ] Structured logs in place

### Phase 2 Success
- [ ] ML model trained and deployed
- [ ] F1-score > 0.75 on test set
- [ ] False positive rate < 10%
- [ ] A/B test shows ML > heuristic

### Phase 3 Success
- [ ] Entity extraction working
- [ ] 80%+ entities correctly canonicalized
- [ ] Search index operational

### Phase 4 Success
- [ ] Location accuracy improved by 20%
- [ ] Privacy policy documented
- [ ] Multi-signal scoring working

### Phase 5 Success
- [ ] New source can be added in < 1 day
- [ ] Quality policies configurable
- [ ] System handles 10+ sources

### Phase 6 Success
- [ ] Full request tracing
- [ ] Nightly evaluation running
- [ ] Regression alerts working

---

## 🚀 Quick Wins (Do First)

1. **Structured Logging** (2-3 days)
   - Immediate value: Better debugging
   - Low risk: Doesn't change logic

2. **Evaluation Dataset** (1 week)
   - Immediate value: Can measure improvements
   - Low risk: Just data collection

3. **Embedding-Based Matching** (1 week)
   - Immediate value: Better relevance
   - Medium risk: Need to test thoroughly

---

## 📝 Next Steps

1. **Review this plan** with team
2. **Prioritize phases** based on business needs
3. **Start with Quick Wins** (structured logging + evaluation dataset)
4. **Set up project board** with tasks
5. **Begin Phase 1** implementation

---

## 🤔 Questions to Decide

1. **ML Model Choice:**
   - Start with embeddings (fast) or cross-encoder (accurate)?
   - **Recommendation:** Start with embeddings, add cross-encoder later

2. **Search Index:**
   - PostgreSQL full-text or Meilisearch?
   - **Recommendation:** Start with PostgreSQL, migrate if needed

3. **Entity Extraction:**
   - Rule-based or ML-based?
   - **Recommendation:** Start with rule-based, add ML later

4. **Timeline:**
   - Aggressive (3 months) or conservative (6 months)?
   - **Recommendation:** 4-5 months is realistic

---

*This plan addresses all architect feedback while maintaining current strengths.*

