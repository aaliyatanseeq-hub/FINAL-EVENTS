# Database Migration: Add Source Columns

## Quick Migration (Recommended)

Run the SQL file directly in pgAdmin:

1. Open pgAdmin
2. Connect to your database: `event_intelligence`
3. Right-click on the database → Query Tool
4. Open `add_source_columns.sql`
5. Execute (F5)

## Alternative: Using Python Script

If you have a compatible Python environment:

```powershell
cd Backend
python migrations/add_source_columns.py
```

## What This Migration Does

- Adds `source` column to `events` table (VARCHAR(50), default 'unknown')
- Adds `source` column to `attendees` table (VARCHAR(50), default 'unknown')
- Creates indexes on both columns for better query performance
- Safe to run multiple times (checks if columns exist first)

## Manual SQL (if needed)

If the DO block doesn't work, run these commands directly:

```sql
ALTER TABLE events ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'unknown';
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

ALTER TABLE attendees ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'unknown';
CREATE INDEX IF NOT EXISTS idx_attendees_source ON attendees(source);
```

