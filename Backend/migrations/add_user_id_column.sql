-- Migration: Add user_id column to attendees table
-- This column stores Twitter user ID for direct messaging functionality
-- Run this SQL directly in pgAdmin or psql

-- Add user_id column to attendees table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='attendees' AND column_name='user_id'
    ) THEN
        ALTER TABLE attendees ADD COLUMN user_id VARCHAR(100) NULL;
        CREATE INDEX IF NOT EXISTS idx_attendees_user_id ON attendees(user_id);
        COMMENT ON COLUMN attendees.user_id IS 'Twitter user ID for DMs';
    END IF;
END $$;

-- Verify column was added
SELECT 
    table_name, 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'attendees' 
    AND column_name = 'user_id';

