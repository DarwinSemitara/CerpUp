-- Add columns for system conversations (Schedule Generation)
-- Run this in Supabase SQL Editor

ALTER TABLE che_conversations 
ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS undeletable BOOLEAN DEFAULT FALSE;

-- Add index for faster system conversation lookups
CREATE INDEX IF NOT EXISTS idx_che_conversations_system 
ON che_conversations(user_id, is_system) 
WHERE is_system = TRUE;

-- Add comment
COMMENT ON COLUMN che_conversations.is_system IS 'Marks system-created conversations like Schedule Generation';
COMMENT ON COLUMN che_conversations.undeletable IS 'Prevents deletion of important system conversations';
