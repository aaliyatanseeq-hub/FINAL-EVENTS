-- Migration: Add source columns to events and attendees tables
-- Run this SQL directly in pgAdmin or psql

-- Add source column to events table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='events' AND column_name='source'
    ) THEN
        ALTER TABLE events ADD COLUMN source VARCHAR(50) DEFAULT 'unknown';
        CREATE INDEX IF NOT EXISTS idx_events_source ON events(source);
    END IF;
END $$;

-- Add source column to attendees table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='attendees' AND column_name='source'
    ) THEN
        ALTER TABLE attendees ADD COLUMN source VARCHAR(50) DEFAULT 'unknown';
        CREATE INDEX IF NOT EXISTS idx_attendees_source ON attendees(source);
    END IF;
END $$;

