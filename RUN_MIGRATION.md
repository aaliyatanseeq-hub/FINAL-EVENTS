# 🚀 Run Database Migration - Quick Guide

## ⚠️ **CRITICAL: Database Migration Required**

The error `column events.is_rreal_event does not exist` means the database migration hasn't been run yet.

---

## ✅ **Quick Fix (Choose One Method)**

### **Method 1: Python Script (Easiest)**
```powershell
cd Backend
python database/add_quality_fields.py
```

### **Method 2: Direct SQL (pgAdmin)**
1. Open pgAdmin
2. Connect to database: `event_intelligence`
3. Right-click database → Query Tool
4. Run this SQL:
```sql
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS is_real_event BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS quality_score FLOAT DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS clean_category VARCHAR(100),
ADD COLUMN IF NOT EXISTS rejection_reasons JSON,
ADD COLUMN IF NOT EXISTS quality_confidence FLOAT DEFAULT 1.0;

CREATE INDEX IF NOT EXISTS idx_events_is_real_event ON events(is_real_event);
CREATE INDEX IF NOT EXISTS idx_events_quality_score ON events(quality_score);
```

### **Method 3: Helper Script**
```powershell
python Backend/run_migration.py
```

---

## ✅ **What Gets Added**

- `is_real_event` (boolean) - Marks noise vs real events
- `quality_score` (float) - Event quality 0.0-1.0
- `clean_category` (varchar) - Cleaned category name
- `rejection_reasons` (json) - Why event was filtered (if any)
- `quality_confidence` (float) - Confidence in quality assessment

---

## 🎯 **After Migration**

Events will store successfully! No more database errors. 🎉

