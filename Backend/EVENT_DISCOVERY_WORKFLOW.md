# Event Discovery Workflow - Complete Documentation

## 📋 Overview
This document explains the complete workflow for the Events phase, including validation, API calls, and data processing.

---

## 🔄 Complete Workflow

### **STEP 1: User Input** (Frontend)
```
User enters:
- Location: "New York" (or "khj" - invalid)
- Start Date: "2025-01-15"
- End Date: "2025-04-15"
- Categories: ["music", "sports"]
- Max Events: 10
```

### **STEP 2: API Request** (Frontend → Backend)
```javascript
POST /api/discover-events
{
  "location": "New York",
  "start_date": "2025-01-15",
  "end_date": "2025-04-15",
  "categories": ["music", "sports"],
  "max_results": 10
}
```

### **STEP 3: Location Validation** (Backend - `app.py`)
```python
LocationValidator.validate_location("New York")
→ Returns: (True, "New York", None)  # Valid

LocationValidator.validate_location("khj")
→ Returns: (False, None, "'khj' is not a recognized location...")
→ HTTPException 400: Invalid location error
```

**What happens:**
1. Checks if location is at least 3 characters
2. Validates using SerpAPI geocoding (if available)
3. Normalizes location (capitalizes properly)
4. **If invalid → Returns error immediately, stops workflow**

### **STEP 4: Date Range Validation** (Backend - `app.py`)
```python
LocationValidator.validate_date_range("2025-01-15", "2025-04-15")
→ Checks:
   - Dates are valid format (YYYY-MM-DD)
   - Start date is not in the past
   - End date is after start date
   - Range is ≤ 90 days (3 months)
   - End date is ≤ 90 days from today
```

**Validation Rules:**
- ✅ **Format**: Must be YYYY-MM-DD (e.g., "2025-01-15")
- ✅ **Range**: Maximum 90 days (3 months)
- ✅ **Future**: Start date must be today or later
- ✅ **Order**: End date must be after start date
- ❌ **If invalid → Returns error immediately, stops workflow**

### **STEP 5: Cache Check** (Backend - `app.py`)
```python
cache_key = generate_cache_key("event_discovery", request_data)
cached_result = crud.get_cache(db, cache_key)

if cached_result:
    return cached_events  # Skip API calls
```

### **STEP 6: Database Check** (Backend - `app.py`)
```python
db_events = crud.get_events_by_location_date(
    location="New York",
    start_date="2025-01-15",
    end_date="2025-04-15",
    categories=["music", "sports"],
    limit=10
)

if len(db_events) >= 5:  # 50% of requested
    return db_events  # Skip API calls
```

### **STEP 7: Event Discovery Engine** (Backend - `event_engine.py`)

#### **7.1: Date Parsing & Validation**
```python
start_dt = _parse_user_date("2025-01-15")  # → datetime(2025, 1, 15)
end_dt = _parse_user_date("2025-04-15")    # → datetime(2025, 4, 15)

# Additional validation in engine:
if (end_dt - start_dt).days > 90:
    raise ValueError("Date range exceeds 3 months")
```

#### **7.2: Multi-Source Query (Priority Order)**

**Source Priority:**
1. **SerpAPI** (Google Events) - Priority 1
2. **PredictHQ** - Priority 2  
3. **Ticketmaster** - Priority 3

**For each source:**

##### **A. SerpAPI Query**
```python
queries = [
    "events in New York January 2025",
    "upcoming events New York January 2025",
    "New York events January 2025",
    "concert New York",
    "sports game New York"
]

for query in queries:
    response = requests.get('https://serpapi.com/search', params={
        'q': query,
        'engine': 'google_events',
        'api_key': SERP_API_KEY
    })
    
    events = _parse_serpapi_response(response.json(), "New York")
```

**Venue Extraction (SerpAPI):**
```python
venue_obj = event_data.get('venue', {})
if isinstance(venue_obj, dict):
    venue = venue_obj.get('name', '')
    if not venue:
        venue = event_data.get('address', '').split(',')[0]
```

##### **B. PredictHQ Query**
```python
response = requests.get('https://api.predicthq.com/v1/events/', params={
    'q': 'New York',
    'active.gte': '2025-01-15',
    'active.lte': '2025-04-15',
    'category': 'concerts,sports',
    'limit': 20
})

events = _parse_predicthq_response(response.json(), "New York")
```

**Venue Extraction (PredictHQ) - WITH FILTERING:**
```python
venue_info = event_data.get('venue', {})
venue_name = venue_info.get('name', 'Various Venues')

# Build venue string
venue_parts = [venue_name] if venue_name != 'Various Venues' else []
if venue_info.get('address'):
    venue_parts.append(venue_info.get('address'))
if venue_info.get('city'):
    venue_parts.append(venue_info.get('city'))

venue_name = ', '.join(venue_parts) if venue_parts else 'Various Venues'

# ⚠️ FILTER OUT "Various Venues" - USER REQUIREMENT
if venue_name == 'Various Venues' or venue_name.lower() in ['various', 'multiple venues', 'tbd', 'tba']:
    return None  # Skip this event - no specific venue
```

**Filter Applied:**
- ❌ Events with venue = "Various Venues" → **SKIPPED**
- ❌ Events with venue = "Various" → **SKIPPED**
- ❌ Events with venue = "TBD" or "TBA" → **SKIPPED**
- ✅ Events with specific venue name → **INCLUDED**

##### **C. Ticketmaster Query**
```python
response = requests.get('https://app.ticketmaster.com/discovery/v2/events.json', params={
    'apikey': TICKETMASTER_KEY,
    'city': 'New York',
    'startDateTime': '2025-01-15T00:00:00Z',
    'endDateTime': '2025-04-15T23:59:59Z',
    'size': 50
})

events = _parse_ticketmaster_response(response.json(), "New York")
```

**Venue Extraction (Ticketmaster):**
```python
venues = event_data.get('_embedded', {}).get('venues', [])
if venues:
    venue = venues[0]
    venue_name = venue.get('name', 'Various Venues')
    address = venue.get('address', {}).get('line1', '')
    city = venue.get('city', {}).get('name', '')
    
    venue_parts = [venue_name, address, city]
    venue_name = ', '.join([p for p in venue_parts if p])
```

#### **7.3: Date Filtering**
```python
# Filter events to exact date range
filtered_events = []
for event in all_events:
    if event.start_datetime:
        if start_dt <= event.start_datetime <= end_dt:
            filtered_events.append(event)
    elif event.exact_date:
        # Loose matching for events without datetime
        if date_string_matches_range(event.exact_date, start_dt, end_dt):
            filtered_events.append(event)
```

#### **7.4: Deduplication**
```python
seen_hashes = set()
unique_events = []
for event in filtered_events:
    if event.event_hash not in seen_hashes:
        seen_hashes.add(event.event_hash)
        unique_events.append(event)
```

#### **7.5: Scoring & Sorting**
```python
# Score events by:
# - Source priority (SerpAPI > PredictHQ > Ticketmaster)
# - Hype score (keywords, venue quality)
# - Has datetime (bonus)
# - Title length (bonus)

scored_events = _score_events(unique_events)
final_events = scored_events[:max_results]  # Top N events
```

### **STEP 8: Database Storage** (Backend - `app.py`)
```python
for event in final_events:
    crud.create_event(db, {
        "event_name": event.event_name,
        "exact_date": event.exact_date,
        "exact_venue": event.exact_venue,  # ✅ Properly extracted, no "Various Venues"
        "location": event.location,
        "category": event.category,
        "source": event.source,
        ...
    })
```

### **STEP 9: Response** (Backend → Frontend)
```json
{
  "success": true,
  "events": [
    {
      "event_name": "Concert at Madison Square Garden",
      "exact_date": "January 20, 2025",
      "exact_venue": "Madison Square Garden, New York",  // ✅ Specific venue
      "location": "New York",
      "category": "music",
      "source": "serpapi",
      "confidence_score": 0.85
    },
    ...
  ],
  "total_events": 10,
  "requested_limit": 10
}
```

---

## 🛡️ Validation Summary

### **Location Validation**
| Input | Result | Error Message |
|-------|--------|---------------|
| "New York" | ✅ Valid | None |
| "khj" | ❌ Invalid | "'khj' is not a recognized location. Please enter a valid city name." |
| "123" | ❌ Invalid | "'123' doesn't appear to be a valid location." |
| "" | ❌ Invalid | "Location must be at least 2 characters long" |

### **Date Range Validation**
| Start Date | End Date | Result | Error Message |
|------------|----------|--------|---------------|
| 2025-01-15 | 2025-04-15 | ✅ Valid | None (90 days) |
| 2025-01-15 | 2025-05-15 | ❌ Invalid | "Date range exceeds 3 months (90 days)" |
| 2024-01-15 | 2025-01-15 | ❌ Invalid | "Start date is in the past" |
| 2025-04-15 | 2025-01-15 | ❌ Invalid | "End date must be after start date" |

### **Venue Filtering**
| Source | Venue Value | Result |
|--------|-------------|--------|
| PredictHQ | "Madison Square Garden" | ✅ Included |
| PredictHQ | "Various Venues" | ❌ **SKIPPED** |
| PredictHQ | "TBD" | ❌ **SKIPPED** |
| PredictHQ | "Various" | ❌ **SKIPPED** |
| SerpAPI | "Concert Hall" | ✅ Included |
| Ticketmaster | "Arena Name" | ✅ Included |

---

## 📊 Data Flow Diagram

```
User Input
    ↓
[Location Validation] → ❌ Invalid → Error Response
    ↓ ✅ Valid
[Date Range Validation] → ❌ Invalid → Error Response
    ↓ ✅ Valid
[Cache Check] → ✅ Found → Return Cached
    ↓ ❌ Not Found
[Database Check] → ✅ Found (50%+) → Return DB Events
    ↓ ❌ Not Enough
[Event Engine]
    ↓
[SerpAPI Query] → Parse → Filter Dates → Filter Venues
    ↓
[PredictHQ Query] → Parse → Filter Dates → **Filter "Various Venues"** → Filter Venues
    ↓
[Ticketmaster Query] → Parse → Filter Dates → Filter Venues
    ↓
[Deduplication] → [Scoring] → [Sorting] → Top N Events
    ↓
[Database Storage] → [Cache Storage]
    ↓
[Response to Frontend]
```

---

## 🔧 Key Functions

### **LocationValidator** (`services/location_validator.py`)
- `validate_location(location: str)` → Validates and normalizes location
- `validate_date_range(start, end)` → Validates date range (max 90 days)

### **SmartEventEngine** (`engines/event_engine.py`)
- `discover_events()` → Main discovery function
- `_fetch_serpapi_events()` → SerpAPI queries
- `_fetch_predicthq_events()` → PredictHQ queries (with venue filtering)
- `_fetch_ticketmaster_events()` → Ticketmaster queries
- `_parse_predicthq_event()` → **Filters out "Various Venues"**

### **app.py** (`app.py`)
- `discover_events()` → API endpoint with validation

---

## ✅ Requirements Met

1. ✅ **Location Validation**: Invalid locations (e.g., "khj") return error immediately
2. ✅ **Date Range**: Exact range validation, maximum 3 months (90 days)
3. ✅ **Venue Extraction**: Proper venue extraction from all APIs
4. ✅ **"Various Venues" Filter**: PredictHQ events with "Various Venues" are **SKIPPED**

---

## 🚨 Error Handling

All validation errors return **HTTP 400** with detailed error messages:
```json
{
  "error": "Invalid location",
  "message": "'khj' is not a recognized location. Please enter a valid city name.",
  "location": "khj",
  "suggestion": "Please enter a valid city name (e.g., 'New York', 'London')"
}
```

This ensures users get clear feedback and can correct their input before the system attempts API calls.

