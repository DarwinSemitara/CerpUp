-- FIX FOR NULL EMAIL ISSUE IN SUPABASE USERS TABLE
-- Run this in your Supabase SQL Editor

-- Option 1: Make email nullable (RECOMMENDED if email is not critical in this table)
ALTER TABLE users 
ALTER COLUMN email DROP NOT NULL;

-- Option 2: Set a default email for existing null records (if you want to keep NOT NULL)
-- UPDATE users 
-- SET email = CONCAT(id, '@placeholder.local')
-- WHERE email IS NULL;

-- Option 3: Create a trigger to auto-fill email from auth.users table
CREATE OR REPLACE FUNCTION set_email_from_auth()
RETURNS TRIGGER AS $$
DECLARE
  auth_email TEXT;
BEGIN
  -- If email is null, try to get it from auth.users
  IF NEW.email IS NULL THEN
    SELECT email INTO auth_email
    FROM auth.users
    WHERE id = NEW.id;
    
    IF auth_email IS NOT NULL THEN
      NEW.email := auth_email;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS ensure_email_set ON users;

-- Create trigger
CREATE TRIGGER ensure_email_set
  BEFORE INSERT OR UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION set_email_from_auth();

-- Verify: Check for any users with null email
SELECT id, uid, email, role 
FROM users 
WHERE email IS NULL;
