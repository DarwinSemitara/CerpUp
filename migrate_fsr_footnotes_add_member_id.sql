-- ============================================================================
-- Migrate FSR Footnotes Table - Add member_id Column
-- ============================================================================
-- This script adds the member_id column to the existing fsr_footnotes table
-- and removes the old fsr_id column if it exists
-- ============================================================================

-- Step 1: Add member_id column if it doesn't exist (without foreign key constraint first)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fsr_footnotes' 
        AND column_name = 'member_id'
    ) THEN
        -- Add column without constraint first
        ALTER TABLE fsr_footnotes 
        ADD COLUMN member_id UUID;
        
        COMMENT ON COLUMN fsr_footnotes.member_id IS 'Faculty member who owns this FSR';
    END IF;
END $$;

-- Step 2: Add semester column if it doesn't exist (should be TEXT not UUID)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fsr_footnotes' 
        AND column_name = 'semester'
    ) THEN
        ALTER TABLE fsr_footnotes 
        ADD COLUMN semester TEXT;
        
        COMMENT ON COLUMN fsr_footnotes.semester IS 'Semester number (1 or 2)';
    END IF;
END $$;

-- Step 3: Add academic_year column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fsr_footnotes' 
        AND column_name = 'academic_year'
    ) THEN
        ALTER TABLE fsr_footnotes 
        ADD COLUMN academic_year TEXT;
        
        COMMENT ON COLUMN fsr_footnotes.academic_year IS 'Academic year in format YYYY-YYYY';
    END IF;
END $$;

-- Step 4: Drop old fsr_id column if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fsr_footnotes' 
        AND column_name = 'fsr_id'
    ) THEN
        -- Remove foreign key constraint first
        ALTER TABLE fsr_footnotes DROP CONSTRAINT IF EXISTS fsr_footnotes_fsr_id_fkey;
        
        -- Drop the column
        ALTER TABLE fsr_footnotes DROP COLUMN fsr_id;
    END IF;
END $$;

-- Step 5: Drop old unique constraint if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'fsr_footnotes' 
        AND constraint_type = 'UNIQUE'
        AND constraint_name LIKE '%fsr_id%'
    ) THEN
        ALTER TABLE fsr_footnotes 
        DROP CONSTRAINT IF EXISTS fsr_footnotes_fsr_id_footnote_number_key;
    END IF;
END $$;

-- Step 6: Add new unique constraint
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'fsr_footnotes' 
        AND constraint_name = 'fsr_footnotes_member_semester_year_number_key'
    ) THEN
        ALTER TABLE fsr_footnotes 
        ADD CONSTRAINT fsr_footnotes_member_semester_year_number_key 
        UNIQUE(member_id, semester, academic_year, footnote_number);
    END IF;
END $$;

-- Step 7: Create or replace index
DROP INDEX IF EXISTS idx_fsr_footnotes_member;
CREATE INDEX idx_fsr_footnotes_member 
    ON fsr_footnotes(member_id, semester, academic_year);

-- Step 8: Add foreign key constraint if members table has uid as primary key
DO $$ 
BEGIN
    -- Check if members.uid is a primary key or has unique constraint
    IF EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.table_name = 'members' 
        AND kcu.column_name = 'uid'
        AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
    ) THEN
        -- Add foreign key constraint
        ALTER TABLE fsr_footnotes 
        ADD CONSTRAINT fsr_footnotes_member_id_fkey 
        FOREIGN KEY (member_id) REFERENCES members(uid) ON DELETE CASCADE;
    ELSE
        RAISE NOTICE 'Skipping foreign key constraint - members.uid is not a primary key or unique';
    END IF;
END $$;

-- Step 9: Update column to NOT NULL if data exists
DO $$ 
BEGIN
    -- Only set NOT NULL if all rows have member_id
    IF NOT EXISTS (
        SELECT 1 FROM fsr_footnotes WHERE member_id IS NULL
    ) AND EXISTS (
        SELECT 1 FROM fsr_footnotes
    ) THEN
        ALTER TABLE fsr_footnotes 
        ALTER COLUMN member_id SET NOT NULL;
        
        ALTER TABLE fsr_footnotes 
        ALTER COLUMN semester SET NOT NULL;
        
        ALTER TABLE fsr_footnotes 
        ALTER COLUMN academic_year SET NOT NULL;
    END IF;
END $$;

-- Verify the structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'fsr_footnotes'
ORDER BY ordinal_position;
