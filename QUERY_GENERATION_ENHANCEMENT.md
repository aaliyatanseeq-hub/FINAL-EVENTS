# 🎯 Enhanced Query Generation - 10 Sub-Queries Per Category

## 📋 **Overview**

The query generation system has been enhanced to generate **10 category-specific sub-queries** for each selected category, with location included in every query.

---

## ✅ **What Changed**

### **Before:**
- Only 5 keywords per category
- Simple keyword + location format
- Limited to 15 total queries
- Generic query patterns

### **After:**
- **10 query templates per category**
- **Location included in every query**
- **Category-specific query variations**
- **Up to 50 queries total** (10 per category × 5 categories max)
- **Smart query templates** with variations

---

## 🎨 **Query Templates Per Category**

### **1. Music (10 queries)**
1. `music events in [location]`
2. `top music events [location]`
3. `upcoming music events [location]`
4. `concerts [location]`
5. `live music [location]`
6. `music festival [location]`
7. `music shows [location]`
8. `best music events [location]`
9. `music performances [location]`
10. `music gigs [location]`

### **2. Sports (10 queries)**
1. `sports events in [location]`
2. `top sports events [location]`
3. `upcoming sports events [location]`
4. `sports games [location]`
5. `sports matches [location]`
6. `championship [location]`
7. `tournament [location]`
8. `best sports events [location]`
9. `sports competition [location]`
10. `live sports [location]`

### **3. Tech (10 queries)**
1. `tech events in [location]`
2. `top tech events [location]`
3. `upcoming tech events [location]`
4. `tech conference [location]`
5. `technology summit [location]`
6. `tech workshop [location]`
7. `tech meetup [location]`
8. `best tech events [location]`
9. `tech expo [location]`
10. `tech innovation [location]`

### **4. Arts (10 queries)**
1. `arts events in [location]`
2. `top arts events [location]`
3. `upcoming arts events [location]`
4. `art exhibition [location]`
5. `art gallery [location]`
6. `art show [location]`
7. `art museum [location]`
8. `best arts events [location]`
9. `art fair [location]`
10. `art festival [location]`

### **5. Theater (10 queries)**
1. `theater events in [location]`
2. `top theater events [location]`
3. `upcoming theater events [location]`
4. `theater shows [location]`
5. `plays [location]`
6. `musicals [location]`
7. `broadway [location]`
8. `best theater events [location]`
9. `theater performances [location]`
10. `drama [location]`

### **6. Food (10 queries)**
1. `food events in [location]`
2. `top food events [location]`
3. `upcoming food events [location]`
4. `food festival [location]`
5. `culinary events [location]`
6. `food tasting [location]`
7. `wine tasting [location]`
8. `best food events [location]`
9. `food and wine [location]`
10. `food market [location]`

### **7. Conference (10 queries)**
1. `conference events in [location]`
2. `top conference events [location]`
3. `upcoming conference events [location]`
4. `summit [location]`
5. `convention [location]`
6. `workshop [location]`
7. `seminar [location]`
8. `best conference events [location]`
9. `expo [location]`
10. `forum [location]`

### **8. Comedy (10 queries)**
1. `comedy events in [location]`
2. `top comedy events [location]`
3. `upcoming comedy events [location]`
4. `comedy shows [location]`
5. `stand-up comedy [location]`
6. `comedy club [location]`
7. `comedy night [location]`
8. `best comedy events [location]`
9. `comedy performances [location]`
10. `comedy festival [location]`

### **9. Family (10 queries)**
1. `family events in [location]`
2. `top family events [location]`
3. `upcoming family events [location]`
4. `family activities [location]`
5. `kids events [location]`
6. `family fun [location]`
7. `family entertainment [location]`
8. `best family events [location]`
9. `family festival [location]`
10. `children events [location]`

### **10. Networking (10 queries)**
1. `networking events in [location]`
2. `top networking events [location]`
3. `upcoming networking events [location]`
4. `business networking [location]`
5. `professional networking [location]`
6. `networking meetup [location]`
7. `networking mixer [location]`
8. `best networking events [location]`
9. `networking social [location]`
10. `networking gathering [location]`

### **11. Dance (10 queries)**
1. `dance events in [location]`
2. `top dance events [location]`
3. `upcoming dance events [location]`
4. `dance performances [location]`
5. `dance shows [location]`
6. `ballet [location]`
7. `dance festival [location]`
8. `best dance events [location]`
9. `dance concert [location]`
10. `dance recital [location]`

---

## 🔄 **Query Generation Logic**

### **For Specific Categories:**
1. User selects: `["music", "sports"]`
2. System generates:
   - 10 queries for "music" category
   - 10 queries for "sports" category
   - **Total: 20 queries**

### **For "All" Categories:**
1. User selects: `["all"]` or `[]`
2. System generates:
   - 10 general event queries
   - Includes time phrases
   - **Total: 10 queries**

### **Query Limits:**
- **Per category**: 10 queries
- **Maximum total**: 50 queries (5 categories × 10)
- **For "all"**: 20 queries max

---

## 📊 **Example Output**

### **Input:**
- Location: `"New York"`
- Categories: `["sports", "music"]`
- Date Range: `2025-12-01` to `2025-12-31`

### **Generated Queries (20 total):**

**Sports (10 queries):**
1. `sports events in New York`
2. `top sports events New York`
3. `upcoming sports events New York`
4. `sports games New York`
5. `sports matches New York`
6. `championship New York`
7. `tournament New York`
8. `best sports events New York`
9. `sports competition New York`
10. `live sports New York`

**Music (10 queries):**
1. `music events in New York`
2. `top music events New York`
3. `upcoming music events New York`
4. `concerts New York`
5. `live music New York`
6. `music festival New York`
7. `music shows New York`
8. `best music events New York`
9. `music performances New York`
10. `music gigs New York`

---

## 🎯 **Benefits**

1. **Better Coverage**: 10 queries per category = more comprehensive event discovery
2. **Location-Aware**: Every query includes the user's location
3. **Category-Specific**: Queries tailored to each category's terminology
4. **Varied Patterns**: Different query structures catch different event types
5. **Higher Quality**: More targeted queries = better event results

---

## 🚀 **Performance**

- **Query Execution**: All queries are executed (up to 50)
- **Caching**: Results are cached to avoid redundant API calls
- **Deduplication**: Duplicate events are removed across all queries
- **Ranking**: Events are scored and ranked by quality

---

## 📝 **Implementation Details**

**File**: `Backend/engines/event_engine.py`
**Function**: `_generate_serpapi_queries()`

**Key Changes:**
1. Added `category_query_templates` dictionary with 10 templates per category
2. Removed query limit from execution (was `[:5]`, now uses all queries)
3. Enhanced query formatting with location in every query
4. Added time phrase variations for first 3 queries per category

---

## ✅ **Testing**

To test the enhanced query generation:

1. **Select a category** (e.g., "sports")
2. **Enter a location** (e.g., "New York")
3. **Check backend logs** - you should see 10 queries being executed
4. **Verify results** - should see more comprehensive event coverage

---

**Result**: The system now generates **10 targeted, location-aware queries per category**, significantly improving event discovery coverage! 🎉

