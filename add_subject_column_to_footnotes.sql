-- ============================================================================
-- Add subject column to fsr_footnotes table
-- ============================================================================

-- Add subject column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'fsr_footnotes' 
        AND column_name = 'subject'
    ) THEN
        ALTER TABLE fsr_footnotes ADD COLUMN subject TEXT;
        COMMENT ON COLUMN fsr_footnotes.subject IS 'Subject/course code for this footnote';
    END IF;
END $$;

-- Delete any rows with NULL member_id, semester, or academic_year (old data)
DELETE FROM fsr_footnotes 
WHERE member_id IS NULL 
   OR semester IS NULL 
   OR academic_year IS NULL;

-- Make the required columns NOT NULL
ALTER TABLE fsr_footnotes 
ALTER COLUMN member_id SET NOT NULL,
ALTER COLUMN semester SET NOT NULL,
ALTER COLUMN academic_year SET NOT NULL;

-- Add unique constraint for member/semester/year/number combination
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE table_name = 'fsr_footnotes' 
        AND constraint_name = 'fsr_footnotes_unique_footnote'
    ) THEN
        ALTER TABLE fsr_footnotes 
        ADD CONSTRAINT fsr_footnotes_unique_footnote 
        UNIQUE(member_id, semester, academic_year, footnote_number);
    END IF;
END $$;

-- Verify structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'fsr_footnotes'
ORDER BY ordinal_position;
