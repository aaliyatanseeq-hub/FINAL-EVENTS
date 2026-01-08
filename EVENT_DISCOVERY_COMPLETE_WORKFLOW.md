# 🎯 Event Discovery - Complete End-to-End Workflow

## 📋 Overview
This document explains the **complete flow** from when a user clicks "Discover Events" in the frontend, through the backend API, to database storage and response.

---

## 🔄 **STEP-BY-STEP WORKFLOW**

### **PHASE 1: FRONTEND (User Interaction)**

#### **1.1 User Fills Form** (`frontend/index.html` + `frontend/js/app.js`)
```javascript
// User enters:
- Location: "New York"
- Start Date: "2024-01-01"
- End Date: "2024-03-31"
- Categories: ["Music", "Sports"]
- Max Results: 50
```

#### **1.2 User Clicks "Discover Events" Button**
- Button triggers `discoverEvents()` function in `app.js` (line 201)

#### **1.3 Frontend Validation** (`frontend/js/app.js:201-219`)
```javascript
async function discoverEvents() {
    // ✅ Check 1: Location required
    if (!location) {
        alert('Please enter a location');
        return;
    }
    
    // ✅ Check 2: At least one category selected
    if (categories.length === 0) {
        alert('Please select at least one category');
        return;
    }
    
    // Show loading spinner
    showLoading(`Discovering ${maxResults} events in ${location}...`);
}
```

#### **1.4 Frontend Sends HTTP Request** (`frontend/js/app.js:223-233`)
```javascript
const response = await fetch(`${API_BASE_URL}/discover-events`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        location: "New York",
        start_date: "2024-01-01",
        end_date: "2024-03-31",
        categories: ["Music", "Sports"],
        max_results: 50
    })
});
```

**Request goes to:** `http://localhost:8000/api/discover-events`

---

### **PHASE 2: BACKEND API (FastAPI Endpoint)**

#### **2.1 Request Received** (`Backend/app.py:138-142`)
```python
@app.post("/api/discover-events")
async def discover_events(
    request: EventDiscoveryRequest,  # Pydantic schema validates input
    db: Session = Depends(get_db)    # Database session injected
):
```

#### **2.2 Location Validation** (`Backend/app.py:148-171`)
```python
from services.location_validator import LocationValidator
validator = LocationValidator()

# Validate location using SerpAPI
is_valid_location, normalized_location, location_error = validator.validate_location(request.location)

if not is_valid_location:
    # ❌ Return HTTP 400 error
    raise HTTPException(
        status_code=400,
        detail={
            "error": "Invalid location",
            "message": location_error,
            "suggestion": "Please enter a valid city name"
        }
    )

# ✅ Location validated: "New York" → "New York, NY, USA"
request.location = normalized_location
```

**What happens:**
- Calls SerpAPI Google Locations endpoint
- Checks if location is a valid city/region
- Normalizes location (e.g., "NYC" → "New York, NY, USA")
- **If invalid:** Returns error immediately, stops workflow

#### **2.3 Date Range Validation** (`Backend/app.py:173-194`)
```python
is_valid_dates, date_error, start_dt, end_dt = validator.validate_date_range(
    request.start_date, 
    request.end_date
)

if not is_valid_dates:
    # ❌ Return HTTP 400 error
    raise HTTPException(
        status_code=400,
        detail={
            "error": "Invalid date range",
            "message": date_error
        }
    )

# ✅ Validates:
# - Dates are in YYYY-MM-DD format
# - Start date is not in the past
# - End date is after start date
# - Date range ≤ 3 months
```

**What happens:**
- Parses dates from strings
- Checks date format
- Validates date logic (start < end, not in past)
- Enforces 3-month maximum range
- **If invalid:** Returns error immediately, stops workflow

#### **2.4 Update Analytics** (`Backend/app.py:206-213`)
```python
crud.update_analytics(db, "event_search")
# Increments event_searches counter in analytics table
```

#### **2.5 Check Cache** (`Backend/app.py:215-234`)
```python
cache_key = generate_cache_key("event_discovery", request.model_dump())
cached_result = crud.get_cache(db, cache_key)

if cached_result:
    # ✅ Return cached results immediately
    return {
        "success": True,
        "events": cached_result.get("events", []),
        "source": "cache"
    }
```

**What happens:**
- Generates unique cache key from request parameters
- Checks database `cache` table for existing result
- **If found:** Returns immediately, skips API calls
- **If not found:** Continues to next step

#### **2.6 Check Database** (`Backend/app.py:242-294`)
```python
db_events = crud.get_events_by_location_date(
    db=db,
    location=request.location,
    start_date=request.start_date,
    end_date=request.end_date,
    categories=request.categories,
    limit=request.max_results
)

if len(db_events) >= request.max_results * 0.5:  # If 50%+ in DB
    # ✅ Return from database
    return {
        "success": True,
        "events": events,
        "source": "database"
    }
```

**What happens:**
- Queries `events` table for matching events
- Filters by location, date range, categories
- **If 50%+ found in DB:** Returns from database, skips API calls
- **If < 50% found:** Continues to API discovery

#### **2.7 Call Event Discovery Engine** (`Backend/app.py:296-320`)
```python
from engines.event_engine import SmartEventEngine
event_engine = SmartEventEngine()

engine_events = event_engine.discover_events(
    location=request.location,
    start_date=request.start_date,
    end_date=request.end_date,
    categories=request.categories,
    max_results=request.max_results
)
```

**What happens:**
- Engine calls multiple APIs (SerpAPI, PredictHQ, Ticketmaster)
- Aggregates and deduplicates events
- Filters venues (removes "Various Venues", etc.)
- Returns list of `ResearchEvent` objects

---

### **PHASE 3: EVENT ENGINE (Multi-Source Discovery)**

#### **3.1 Engine Initialization** (`Backend/engines/event_engine.py:54-100`)
```python
class SmartEventEngine:
    def __init__(self):
        self.serp_api_key = os.getenv('SERP_API_KEY')
        self.ticketmaster_api_key = os.getenv('TICKETMASTER_KEY')
        self.predicthq_api_key = os.getenv('PREDICTHQ_TOKEN')
        
        # Source priorities:
        # 1. SerpAPI (priority 1, weight 1.2)
        # 2. PredictHQ (priority 2, weight 1.1)
        # 3. Ticketmaster (priority 3, weight 1.0)
```

#### **3.2 Multi-Source API Calls** (`Backend/engines/event_engine.py`)
```python
def discover_events(self, location, start_date, end_date, categories, max_results):
    all_events = []
    
    # 1. SerpAPI (Primary source)
    serpapi_events = self._fetch_serpapi_events(location, start_date, end_date, categories)
    all_events.extend(serpapi_events)
    
    # 2. PredictHQ (Secondary source)
    predicthq_events = self._fetch_predicthq_events(location, start_date, end_date, categories)
    all_events.extend(predicthq_events)
    
    # 3. Ticketmaster (Tertiary source)
    ticketmaster_events = self._fetch_ticketmaster_events(location, start_date, end_date, categories)
    all_events.extend(ticketmaster_events)
    
    # Deduplicate by event_hash
    unique_events = self._deduplicate_events(all_events)
    
    # Sort by hype_score (weighted by source priority)
    sorted_events = sorted(unique_events, key=lambda x: x.hype_score, reverse=True)
    
    return sorted_events[:max_results]
```

**What happens:**
- Calls 3 APIs in parallel (if keys available)
- Each API returns events in different formats
- Engine normalizes all events to `ResearchEvent` dataclass
- Filters out generic venues ("Various Venues", "TBD", etc.)
- Deduplicates by event name + venue + date hash
- Sorts by hype_score (confidence × source_weight)
- Returns top N events

#### **3.3 Event Parsing** (`Backend/engines/event_engine.py`)
Each source has a parser:
- `_parse_serpapi_event()` - Extracts from SerpAPI JSON
- `_parse_predicthq_event()` - Extracts from PredictHQ JSON
- `_parse_ticketmaster_event()` - Extracts from Ticketmaster JSON

**Common fields extracted:**
- `event_name`: Name of event
- `exact_date`: Date string
- `exact_venue`: Venue name (filtered)
- `location`: City/region
- `category`: Event category
- `confidence_score`: 0.0-1.0
- `source_url`: Link to event
- `hype_score`: Calculated score
- `source`: "serpapi" | "predicthq" | "ticketmaster"

---

### **PHASE 4: DATABASE STORAGE**

#### **4.1 Convert Events to Database Format** (`Backend/app.py:322-353`)
```python
events_data = []
for event in engine_events:
    # Convert ResearchEvent dataclass to dict
    event_dict = {}
    for key, value in event.__dict__.items():
        if key not in excluded_fields:
            event_dict[key] = value
    
    # Store extra fields in source_data JSON
    source_data = {
        'ticket_url': event.ticket_url,
        'price_range': event.price_range,
        ...event_dict
    }
    event_dict['source_data'] = source_data
    
    events_data.append(event_dict)
```

#### **4.2 Save to Database** (`Backend/app.py:355-362`)
```python
for event_dict in events_data:
    try:
        crud.create_event(db, event_dict)
    except Exception as e:
        print(f"⚠️ Failed to store event in DB: {e}")
        # Continue even if one fails
```

**What happens in `crud.create_event()`** (`Backend/database/crud.py:13-45`):
```python
def create_event(db: Session, event_data: Dict[str, Any]):
    # 1. Filter valid fields (only columns that exist in Event model)
    valid_fields = {col.name for col in models.Event.__table__.columns}
    filtered_data = {k: v for k, v in event_data.items() if k in valid_fields}
    
    # 2. Check if event already exists
    existing = db.query(models.Event).filter(
        models.Event.event_name == filtered_data.get('event_name'),
        models.Event.exact_date == filtered_data.get('exact_date'),
        models.Event.location == filtered_data.get('location')
    ).first()
    
    if existing:
        # 3a. Update existing event
        for key, value in filtered_data.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        # 3b. Create new event
        db_event = models.Event(**filtered_data)
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event
```

**Database Table Structure** (`Backend/database/models.py:38-55`):
```python
class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    event_name = Column(String(500))
    exact_date = Column(String(200))
    exact_venue = Column(String(500))
    location = Column(String(200))
    category = Column(String(100))
    confidence_score = Column(Float)
    source_url = Column(String(1000))
    posted_by = Column(String(200))
    hype_score = Column(Float)
    source = Column(String(50))  # "serpapi", "predicthq", "ticketmaster"
    source_data = Column(JSON)   # Extra fields (ticket_url, price_range, etc.)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
```

#### **4.3 Cache Results** (`Backend/app.py:364-372`)
```python
cache_data = {
    "events": events_data,
    "total_events": len(events_data)
}
crud.set_cache(db, cache_key, cache_data, ttl_minutes=60)
```

**What happens:**
- Stores full response in `cache` table
- Sets TTL (Time To Live) = 60 minutes
- Next identical request will return from cache (step 2.5)

---

### **PHASE 5: RESPONSE BACK TO FRONTEND**

#### **5.1 Backend Returns JSON** (`Backend/app.py:374-380`)
```python
return {
    "success": True,
    "events": events_data,  # List of event dictionaries
    "total_events": len(events_data),
    "requested_limit": request.max_results,
    "source": "api"  # "cache" | "database" | "api"
}
```

#### **5.2 Frontend Receives Response** (`frontend/js/app.js:258-273`)
```javascript
const result = await response.json();

if (result.success) {
    currentEvents = result.events || [];
    displayEvents(currentEvents, result);
    updateEventDropdown(currentEvents);
} else {
    throw new Error('Failed to discover events');
}
```

#### **5.3 Frontend Displays Events** (`frontend/js/app.js:276-320`)
```javascript
function displayEvents(events, metadata) {
    const tableBody = document.getElementById('eventsTableBody');
    
    // Show stats
    statsElement.innerHTML = `
        <span>Found: ${metadata.total_events}</span>
        <span>Limit: ${metadata.requested_limit}</span>
        <span>Source: ${metadata.source}</span>
    `;
    
    // Populate table
    events.forEach(event => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${event.event_name}</td>
            <td>${event.exact_date}</td>
            <td>${event.exact_venue}</td>
            <td>${event.category}</td>
            <td>${event.source}</td>
            ...
        `;
        tableBody.appendChild(row);
    });
}
```

---

## 🔍 **DATA FLOW DIAGRAM**

```
┌─────────────┐
│   USER     │
│  Frontend  │
└─────┬───────┘
      │ 1. User fills form & clicks "Discover Events"
      │
      ▼
┌─────────────────────────────────────┐
│  Frontend Validation                │
│  - Location required?               │
│  - Categories selected?             │
└─────┬───────────────────────────────┘
      │ 2. POST /api/discover-events
      │    {location, dates, categories, max_results}
      │
      ▼
┌─────────────────────────────────────┐
│  Backend API (FastAPI)              │
│  /api/discover-events               │
└─────┬───────────────────────────────┘
      │
      ├─► 3. Validate Location (SerpAPI)
      │   └─► Invalid? → Return 400 Error
      │
      ├─► 4. Validate Date Range
      │   └─► Invalid? → Return 400 Error
      │
      ├─► 5. Check Cache
      │   └─► Found? → Return cached results ✅
      │
      ├─► 6. Check Database
      │   └─► 50%+ found? → Return from DB ✅
      │
      └─► 7. Call Event Engine
          │
          ▼
      ┌─────────────────────────────────────┐
      │  Event Discovery Engine             │
      │  (Multi-Source)                     │
      └─────┬───────────────────────────────┘
            │
            ├─► 8a. SerpAPI → Events
            ├─► 8b. PredictHQ → Events
            ├─► 8c. Ticketmaster → Events
            │
            ├─► 9. Deduplicate & Sort
            └─► 10. Return Top N Events
                │
                ▼
      ┌─────────────────────────────────────┐
      │  Save to Database                   │
      │  - Insert/Update events table        │
      │  - Store in cache table              │
      └─────┬───────────────────────────────┘
            │
            ▼
      ┌─────────────────────────────────────┐
      │  Return JSON Response               │
      │  {success, events, total, source}   │
      └─────┬───────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────┐
│  Frontend Receives & Displays       │
│  - Populate table                    │
│  - Show stats                        │
│  - Update dropdown                   │
└─────────────────────────────────────┘
```

---

## 📊 **KEY COMPONENTS**

### **1. Frontend Files**
- `frontend/index.html` - Form UI
- `frontend/js/app.js` - JavaScript logic (lines 201-274)
- `frontend/styles/main.css` - Styling

### **2. Backend Files**
- `Backend/app.py` - FastAPI endpoint (lines 138-389)
- `Backend/engines/event_engine.py` - Multi-source discovery
- `Backend/services/location_validator.py` - Location/date validation
- `Backend/database/crud.py` - Database operations
- `Backend/database/models.py` - SQLAlchemy models
- `Backend/database/schemas.py` - Pydantic schemas

### **3. Database Tables**
- `events` - Stores discovered events
- `cache` - Stores API responses (TTL-based)
- `analytics` - Tracks search counts
- `search_history` - Logs user searches

---

## 🎯 **IMPORTANT POINTS**

1. **Validation First**: Location and dates validated before any API calls
2. **Cache Priority**: Checks cache before database, database before APIs
3. **Database as Source**: If 50%+ events exist in DB, returns immediately
4. **Multi-Source**: Aggregates from 3 APIs, deduplicates, sorts by quality
5. **Error Handling**: Each step has try-catch, failures don't crash the flow
6. **Analytics**: Every search increments counters for tracking

---

## 🔧 **HOW TO TEST**

1. **Start Backend:**
   ```powershell
   cd Backend
   ..\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
   ```

2. **Open Frontend:**
   - Navigate to `http://localhost:8000`
   - Go to "Discover Events" tab

3. **Fill Form:**
   - Location: "New York"
   - Start Date: Today's date
   - End Date: 3 months from now
   - Select categories
   - Click "Discover Events"

4. **Check Backend Console:**
   - See validation logs
   - See API calls
   - See database saves

5. **Check Database:**
   ```sql
   SELECT * FROM events ORDER BY created_at DESC LIMIT 10;
   SELECT * FROM cache ORDER BY created_at DESC LIMIT 5;
   ```

---

## ✅ **SUMMARY**

**Complete Flow:**
1. User → Frontend form submission
2. Frontend → Backend API POST request
3. Backend → Validate location & dates
4. Backend → Check cache → Check database → Call APIs
5. Engine → Aggregate from 3 sources → Deduplicate → Sort
6. Backend → Save to database → Cache result
7. Backend → Return JSON response
8. Frontend → Display events in table

**Data Sources (Priority Order):**
1. Cache (fastest, 60min TTL)
2. Database (fast, if 50%+ exists)
3. APIs (slowest, but most complete)

**This ensures:**
- Fast responses (cache/database)
- Fresh data (API fallback)
- No duplicates (deduplication)
- Quality results (sorting by hype_score)

