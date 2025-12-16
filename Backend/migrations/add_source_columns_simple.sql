-- Simple Migration: Add source columns
-- This version uses IF NOT EXISTS which works in PostgreSQL 9.5+

-- Add source column to events table
ALTER TABLE events ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'unknown';

-- Create index on events.source
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);

-- Add source column to attendees table
ALTER TABLE attendees ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'unknown';

-- Create index on attendees.source
CREATE INDEX IF NOT EXISTS idx_attendees_source ON attendees(source);

-- Verify columns were added
SELECT 
    table_name, 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name IN ('events', 'attendees') 
    AND column_name = 'source';

