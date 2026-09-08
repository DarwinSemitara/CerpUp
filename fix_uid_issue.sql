-- FIX FOR NULL UID ISSUE IN SUPABASE USERS TABLE
-- Run this in your Supabase SQL Editor

-- Step 1: Fix all existing records with null uid
UPDATE users 
SET uid = id 
WHERE uid IS NULL;

-- Step 2: Make uid column match id column by default (for future inserts)
-- This ensures that if uid is not provided, it copies from id
ALTER TABLE users 
ALTER COLUMN uid SET DEFAULT id;

-- Note: The above might not work, so as a better solution:
-- Step 3: Create a trigger to auto-set uid = id if uid is null
CREATE OR REPLACE FUNCTION set_uid_from_id()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.uid IS NULL THEN
    NEW.uid := NEW.id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop the trigger if it exists
DROP TRIGGER IF EXISTS ensure_uid_matches_id ON users;

-- Create the trigger
CREATE TRIGGER ensure_uid_matches_id
  BEFORE INSERT OR UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION set_uid_from_id();

-- Step 4: Verify the fix
SELECT id, uid, email, first_login 
FROM users 
WHERE uid IS NULL;

-- If the above returns rows, those need manual fixing:
-- UPDATE users SET uid = id WHERE id = '<specific-id>';

-- Step 5: Make uid NOT NULL to prevent future issues (optional but recommended)
-- First ensure all existing records have uid set (run step 1 again if needed)
-- Then run:
-- ALTER TABLE users ALTER COLUMN uid SET NOT NULL;

-- Done! Now test by creating a new account
