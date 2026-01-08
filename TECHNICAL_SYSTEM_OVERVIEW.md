# 🏗️ Event Intelligence Platform - Complete Technical Overview

## 📋 Table of Contents
1. [System Architecture](#system-architecture)
2. [Technology Stack](#technology-stack)
3. [Core Components](#core-components)
4. [Data Flow & Workflows](#data-flow--workflows)
5. [Key Algorithms & Logic](#key-algorithms--logic)
6. [API Endpoints](#api-endpoints)
7. [Database Schema](#database-schema)
8. [Caching Strategy](#caching-strategy)
9. [Quality Filtering System](#quality-filtering-system)
10. [Attendee Matching Logic](#attendee-matching-logic)
11. [Rate Limiting & Performance](#rate-limiting--performance)
12. [Security & Privacy](#security--privacy)

---

## 🏛️ System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vanilla JS)                    │
│  - HTML/CSS/JavaScript (No frameworks)                      │
│  - Event discovery form                                     │
│  - Attendee analysis interface                              │
│  - Twitter action management                                │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼─────────────────────────────────────┐
│              BACKEND (FastAPI - Python)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Layer (app.py)                                   │  │
│  │  - /api/discover-events                               │  │
│  │  - /api/discover-attendees                            │  │
│  │  - /api/retweet-posts, /api/like-posts, etc.         │  │
│  └───────────────┬──────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐  │
│  │  Engine Layer                                         │  │
│  │  - SmartEventEngine (Multi-source event discovery)   │  │
│  │  - SmartAttendeeEngine (Twitter/Reddit attendees)   │  │
│  └───────────────┬──────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐  │
│  │  Service Layer                                        │  │
│  │  - TwitterClient (OAuth 1.1 + v2 API)                │  │
│  │  - RedditClient (PRAW)                               │  │
│  │  - EventQualityFilter (Noise removal)                │  │
│  │  - LocationValidator (Geocoding)                     │  │
│  └───────────────┬──────────────────────────────────────┘  │
└──────────────────┼──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│         DATABASE LAYER (PostgreSQL)                         │
│  - events (discovered events)                               │
│  - attendees (social media users)                            │
│  - cache (API response caching)                             │
│  - analytics (usage tracking)                               │
│  - user_actions (Twitter interactions)                      │
└─────────────────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│         EXTERNAL APIs                                        │
│  - SerpAPI (Google Events)                                  │
│  - PredictHQ (Event intelligence)                           │
│  - Ticketmaster (Ticket sales)                              │
│  - Twitter API v2 (Social data)                            │
│  - Reddit API (Forum discussions)                           │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow
```
User Request → FastAPI Endpoint → Validation → Cache Check → 
Database Query → Engine Processing → External API Calls → 
Quality Filtering → Deduplication → Database Storage → Response
```

---

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI** (v0.104.1) - Modern Python web framework
  - Async/await support
  - Automatic API documentation (Swagger/OpenAPI)
  - Pydantic validation
  - CORS middleware

### Database
- **PostgreSQL** - Relational database
- **SQLAlchemy** (ORM) - Database abstraction layer
- **Connection pooling** - Efficient database connections

### External API Clients
- **Tweepy** (v4.14.0) - Twitter API v2 + OAuth 1.1
- **PRAW** (v7.7.1) - Reddit API wrapper
- **Requests** (v2.31.0) - HTTP client for SerpAPI, PredictHQ, Ticketmaster

### Data Processing
- **BeautifulSoup4** - HTML parsing (SerpAPI responses)
- **Python-dateutil** - Date parsing and manipulation
- **Regex** - Pattern matching for entity extraction

### Utilities
- **OpenPyXL** (v3.1.2) - Excel export functionality
- **Python-dotenv** - Environment variable management
- **Hashlib** - MD5 hashing for deduplication

### Optional Dependencies
- **Redis** (optional) - In-memory caching (gracefully handled if missing)
- **Geopy** (optional) - Geocoding (gracefully handled if missing)

---

## 🧩 Core Components

### 1. Event Discovery Engine (`SmartEventEngine`)

**Purpose:** Multi-source event aggregation with intelligent deduplication

**Key Features:**
- **3 Data Sources:** SerpAPI (50%), PredictHQ (25%), Ticketmaster (25%)
- **Ratio Distribution:** Maintains 50/25/25 split even when sources fail
- **Smart Deduplication:** Hash-based + semantic similarity
- **Date Parsing:** Handles multiple date formats (MM-DD-YY, YYYY-MM-DD, etc.)
- **Geocoding:** Dynamic location resolution (no hardcoding)
- **Cache Integration:** 3-month TTL for event data

**Core Methods:**
```python
discover_events(location, start_date, end_date, categories, max_results)
  → Fetches from 3 APIs in parallel
  → Applies quality filter
  → Deduplicates by hash + semantic similarity
  → Returns sorted by hype_score

_fetch_serpapi_events() → Google Events via SerpAPI
_fetch_predicthq_events() → PredictHQ API
_fetch_ticketmaster_events() → Ticketmaster API
```

### 2. Attendee Discovery Engine (`SmartAttendeeEngine`)

**Purpose:** Find social media users discussing specific events

**Key Features:**
- **Primary Source:** Twitter (real-time discussions)
- **Secondary Source:** Reddit (forum discussions)
- **Relevance Scoring:** Keyword-based matching with engagement signals
- **Location Extraction:** Privacy-compliant country-level inference
- **Display Name Cleaning:** Filters bio-like nonsense from names

**Core Methods:**
```python
discover_attendees(event_name, event_date, max_results)
  → Searches Twitter with optimized queries
  → Searches Reddit as fallback
  → Calculates relevance scores
  → Extracts location (country-level only)
  → Returns sorted by relevance_score

_calculate_tweet_relevance_priority() → Scores tweet relevance (0.0-1.0)
_extract_safe_location() → Country-level location inference
_extract_clean_display_name() → Removes bio patterns from names
```

### 3. Quality Filter (`EventQualityFilter`)

**Purpose:** Remove noise from API responses (season passes, test events, etc.)

**3-Layer Filtering:**
1. **Rule-Based Filters:** Regex patterns for noise detection
2. **Quality Scoring:** Multi-factor analysis (name, venue, category, source)
3. **Final Decision:** `is_real_event` boolean + `quality_score` (0.0-1.0)

**Noise Patterns Detected:**
- Season passes, vouchers, bundles
- Test events, placeholders
- Ticket transfers, resales
- Invalid venues (TBD, TBA, Various Venues)
- Location mismatches

### 4. Twitter Client (`TwitterClient`)

**Purpose:** Twitter API integration with OAuth 1.1 + v2 API

**Features:**
- **Dual API Support:** v2 for posting, v1.1 for search
- **Rate Limiting:** Manual tracking (60 searches per 15 minutes)
- **OAuth 1.1:** For retweets, likes, comments, DMs
- **Error Handling:** Graceful degradation

### 5. Location Validator (`LocationValidator`)

**Purpose:** Validate and normalize location inputs

**Features:**
- **Geocoding:** Uses Nominatim (OpenStreetMap) for location resolution
- **Country Extraction:** Extracts country codes from geocoded results
- **Date Validation:** Validates date ranges and formats

---

## 🔄 Data Flow & Workflows

### Event Discovery Workflow

```
1. User submits search (location, date range, categories)
   ↓
2. FastAPI validates input (location, dates)
   ↓
3. Check cache (3-month TTL)
   → If found: Return cached results ✅
   ↓
4. Check database for existing events
   → If 50%+ found: Return from DB ✅
   ↓
5. Call SmartEventEngine
   ├─→ SerpAPI (50% quota)
   ├─→ PredictHQ (25% quota)
   └─→ Ticketmaster (25% quota)
   ↓
6. Apply EventQualityFilter
   → Remove noise events
   ↓
7. Deduplicate events
   → Hash-based + semantic similarity
   ↓
8. Apply ratio filtering (50/25/25)
   → Ensure proper source distribution
   ↓
9. Store in database + cache
   ↓
10. Return JSON response
```

### Attendee Discovery Workflow

```
1. User submits event name
   ↓
2. Check database for existing attendees
   → If found: Return from DB ✅
   ↓
3. Call SmartAttendeeEngine
   ├─→ Twitter search (primary)
   │   ├─→ Build optimized queries
   │   ├─→ Search recent tweets
   │   ├─→ Calculate relevance scores
   │   └─→ Extract location (country-level)
   └─→ Reddit search (secondary)
       ├─→ Search subreddits
       └─→ Extract user data
   ↓
4. Filter by relevance threshold (0.3+)
   ↓
5. Store in database
   ↓
6. Return JSON response
```

---

## 🧮 Key Algorithms & Logic

### 1. Event Deduplication Algorithm

**Hash-Based Deduplication:**
```python
event_hash = MD5(
    normalize(event_name) + 
    normalize(venue) + 
    normalize(date[:10])
)
```

**Semantic Similarity:**
- Uses `SequenceMatcher` (difflib) for text similarity
- Threshold: 0.85 similarity = duplicate
- Compares: event_name, venue, date

### 2. Relevance Scoring Algorithm

**Tweet Relevance Score (0.0-1.0):**
```python
score = 0.0

# 1. Exact match (60% weight)
if event_name.lower() in tweet.lower():
    score += 0.6

# 2. Keyword matches (15% per keyword)
keywords = extract_keywords(event_name)
for keyword in keywords:
    if keyword in tweet.lower():
        score += 0.15

# 3. Engagement signals (20%)
if "attending" or "got tickets" in tweet:
    score += 0.2

# 4. Medium engagement (10%)
if "excited" or "can't wait" in tweet:
    score += 0.1

# 5. Event context (5%)
if "game" or "match" or "concert" in tweet:
    score += 0.05

return min(1.0, score)
```

### 3. Ratio Distribution Algorithm

**Maintains 50/25/25 split:**
```python
total_events = max_results
serpapi_target = int(total_events * 0.5)      # 50%
predicthq_target = int(total_events * 0.25)   # 25%
ticketmaster_target = int(total_events * 0.25) # 25%

# If a source fails, redistribute quota
if serpapi_events < serpapi_target:
    remaining = serpapi_target - len(serpapi_events)
    # Redistribute to other sources proportionally
```

### 4. Cache Key Generation

**Deterministic cache keys:**
```python
cache_key = f"events_{location}_{start_date}_{end_date}_{categories}_{max_results}"
cache_key = normalize(cache_key)  # Lowercase, sorted categories
```

### 5. Date Parsing Logic

**Handles multiple formats:**
- `MM-DD-YY HH:MM AM/PM` (e.g., "12-17-25 08:00 PM")
- `YYYY-MM-DD` (e.g., "2025-12-17")
- `MM/DD/YY` (e.g., "12/17/25")
- Relative dates: "today", "tomorrow", "next week"

**Timezone Preservation:**
- Extracts timezone from API responses
- Preserves in `exact_date` field
- Example: "9:00 AM - 6:00 PM Asia/Tokyo"

---

## 🌐 API Endpoints

### Event Discovery
```
POST /api/discover-events
Body: {
    "location": "New York",
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "categories": ["sports", "music"],
    "max_results": 50
}
Response: {
    "success": true,
    "events": [...],
    "total_events": 50,
    "source": "cache|database|api",
    "cached_count": 0
}
```

### Attendee Discovery
```
POST /api/discover-attendees
Body: {
    "event_name": "New York Knicks vs Minnesota Timberwolves",
    "event_date": "2025-12-18",
    "max_results": 100
}
Response: {
    "success": true,
    "attendees": [...],
    "total_attendees": 100,
    "source": "twitter|reddit"
}
```

### Twitter Actions
```
POST /api/retweet-posts
POST /api/like-posts
POST /api/post-comments
POST /api/post-quote-tweets
POST /api/send-messages
```

### Analytics & Export
```
GET /api/analytics
GET /api/search-history
POST /api/export-events
POST /api/export-attendees
```

---

## 💾 Database Schema

### Events Table
```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(500) NOT NULL,
    exact_date VARCHAR(200),
    exact_venue VARCHAR(500),
    location VARCHAR(200),
    category VARCHAR(100),
    confidence_score FLOAT DEFAULT 0.0,
    source_url VARCHAR(1000),
    posted_by VARCHAR(200),
    hype_score FLOAT DEFAULT 0.0,
    source VARCHAR(50) DEFAULT 'unknown',
    source_data JSON,
    is_real_event BOOLEAN DEFAULT TRUE,
    quality_score FLOAT DEFAULT 1.0,
    clean_category VARCHAR(100),
    rejection_reasons JSON,
    quality_confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Attendees Table
```sql
CREATE TABLE attendees (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    bio TEXT,
    location VARCHAR(200),
    followers_count INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT DEFAULT 0.0,
    engagement_type VARCHAR(50),
    post_content TEXT,
    post_date VARCHAR(100),
    post_link VARCHAR(500),
    relevance_score FLOAT DEFAULT 0.0,
    event_name VARCHAR(500),
    source VARCHAR(50) DEFAULT 'unknown',
    source_data JSON,
    user_id VARCHAR(100),  -- Twitter user ID for DMs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Cache Table
```sql
CREATE TABLE cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
```

### Analytics Table
```sql
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP DEFAULT NOW(),
    event_searches INTEGER DEFAULT 0,
    attendee_searches INTEGER DEFAULT 0,
    twitter_actions INTEGER DEFAULT 0,
    api_calls_saved INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0
);
```

---

## 💿 Caching Strategy

### Cache TTL (Time-To-Live)
- **Events:** 3 months (129,600 minutes)
- **API Responses:** 1 hour (60 minutes)
- **Location Validation:** 24 hours

### Cache Key Structure
```
events_{location}_{start_date}_{end_date}_{categories}_{max_results}
attendees_{event_name}_{event_date}_{max_results}
location_{location_string}
```

### Cache Lookup Logic
1. Generate deterministic cache key
2. Query `cache` table
3. Check `expires_at` timestamp
4. If valid: Return cached data
5. If expired: Delete and fetch fresh data

### Cache Invalidation
- Automatic: Based on `expires_at` timestamp
- Manual: Delete old cache entries on new searches
- Database: Events stored permanently (not just cached)

---

## 🔍 Quality Filtering System

### Layer 1: Rule-Based Filters
- **Noise Pattern Detection:** 30+ regex patterns
- **Invalid Venue Detection:** TBD, TBA, Various Venues
- **Location Consistency:** Ensures event location matches search location
- **Date Reasonableness:** Validates dates are within search range

### Layer 2: Quality Scoring
- **Event Name Quality (0.0-1.0):**
  - Base: 0.5
  - +0.2 for capitalized words (team/artist names)
  - +0.2 for reasonable length (10-100 chars)
  - -0.1 for all caps
  - -0.2 for too many special characters

- **Venue Quality (0.0-1.0):**
  - Base: 0.6
  - +0.3 for specific venue names (not generic)
  - +0.1 for address-like structure

- **Category Quality (0.0-1.0):**
  - Based on category-event name alignment
  - Sports events get higher score for "sports" category

### Layer 3: Final Decision
```python
is_real_event = (
    not matches_noise_patterns AND
    venue_quality > 0.3 AND
    location_matches AND
    quality_score > 0.5
)

quality_score = (
    name_quality * 0.4 +
    venue_quality * 0.3 +
    category_quality * 0.2 +
    source_quality * 0.1
)
```

---

## 🎯 Attendee Matching Logic

### Current Approach: Keyword-Based Matching

**Relevance Score Calculation:**
1. **Exact Match (60%):** Full event name in tweet
2. **Keyword Matching (15% per keyword):** Individual keywords from event name
3. **Engagement Signals (20%):** "attending", "got tickets", etc.
4. **Medium Engagement (10%):** "excited", "can't wait", etc.
5. **Event Context (5%):** "game", "match", "concert", etc.

**Threshold:** 0.3+ relevance score to include attendee

### Query Optimization
- **Priority 1:** Exact event name match (quoted)
- **Priority 2:** Main keywords (2+ keywords)
- **Priority 3:** Engagement phrases ("attending", "going to")
- **Priority 4:** Single keyword fallback

### Location Extraction (Privacy-Compliant)
- **Method 1:** Tweet place.country_code (if available)
- **Method 2:** User location field (user-defined)
- **Method 3:** Content inference (keywords, venues)
- **Method 4:** Timezone inference (coarse signal)
- **Stores:** Country-level only (e.g., "United States", not coordinates)

---

## ⚡ Rate Limiting & Performance

### Twitter API Rate Limits
- **Search:** 60 requests per 15 minutes (Basic tier)
- **Posting:** 300 requests per 15 minutes
- **Manual Tracking:** Tracks remaining quota

### Performance Optimizations
- **Parallel API Calls:** Concurrent fetching from 3 event sources
- **Database Indexing:** Indexed on `location`, `source`, `is_real_event`
- **Connection Pooling:** SQLAlchemy connection pool
- **Cache-First Strategy:** Reduces API calls by 70-80%

### Error Handling
- **Graceful Degradation:** If one source fails, others continue
- **Retry Logic:** Tenacity library for transient failures
- **Fallback Mechanisms:** Database → Cache → API

---

## 🔒 Security & Privacy

### Authentication
- **Twitter OAuth 1.1:** For posting actions
- **API Keys:** Stored in environment variables (.env)
- **No Hardcoded Secrets:** All credentials in .env

### Privacy Compliance
- **Location Data:** Country-level only (no precise coordinates)
- **Public Data Only:** Uses only publicly available Twitter/Reddit data
- **No IP Tracking:** No IP addresses stored
- **User Consent:** Implicit for public social media data

### Data Protection
- **Input Validation:** Pydantic models validate all inputs
- **SQL Injection Prevention:** SQLAlchemy parameterized queries
- **XSS Prevention:** Input sanitization for user-generated content
- **CORS:** Restricted to `http://localhost:4000`

---

## 📊 Key Metrics & Analytics

### Tracked Metrics
- Event searches count
- Attendee searches count
- Twitter actions (retweets, likes, comments)
- API calls saved (via caching)
- Active users

### Analytics Endpoint
```
GET /api/analytics
Response: {
    "event_searches": 1250,
    "attendee_searches": 850,
    "twitter_actions": 3200,
    "api_calls_saved": 4500,
    "active_users": 150
}
```

---

## 🚀 Deployment & Configuration

### Environment Variables Required
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Twitter API
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
TWITTER_BEARER_TOKEN=...

# External APIs
SERP_API_KEY=...
PREDICTHQ_API_KEY=...
TICKETMASTER_API_KEY=...

# Reddit API
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

### Startup Sequence
1. Load environment variables
2. Initialize database connection
3. Create tables (if not exist)
4. Initialize engines (Event, Attendee)
5. Setup Twitter/Reddit clients
6. Start FastAPI server (Uvicorn)

---

## 🔮 Future Enhancements (Not Yet Implemented)

### Potential Improvements
1. **ML-Based Matching:** Embedding-based semantic similarity for attendee matching
2. **Entity Extraction:** Dynamic entity extraction (teams, artists, venues) without hardcoding
3. **Fuzzy Matching:** Levenshtein distance for typo tolerance
4. **Real-Time Updates:** WebSocket support for live event updates
5. **Advanced Analytics:** User behavior tracking, event popularity trends
6. **Multi-Language Support:** Internationalization for non-English events

---

## 📝 Summary

This Event Intelligence Platform is a **production-ready system** that:
- ✅ Aggregates events from 3 sources (SerpAPI, PredictHQ, Ticketmaster)
- ✅ Maintains 50/25/25 ratio distribution
- ✅ Filters noise using 3-layer quality system
- ✅ Discovers attendees from Twitter/Reddit
- ✅ Provides Twitter interaction capabilities (retweet, like, comment, DM)
- ✅ Caches aggressively (3-month TTL for events)
- ✅ Stores data in PostgreSQL with proper indexing
- ✅ Exports data to Excel
- ✅ Tracks analytics and usage

**Technology Stack:** FastAPI + PostgreSQL + SQLAlchemy + Tweepy + PRAW

**Architecture Pattern:** Layered architecture (API → Engine → Service → Database)

**Key Design Principles:**
- Cache-first strategy
- Graceful degradation
- Privacy-compliant location extraction
- Quality over quantity (noise filtering)
- Ratio-based source distribution

---

*Document Version: 1.0*  
*Last Updated: 2025-12-18*  
*System Version: 2.1.0*

