-- ============================================================================
-- Update FSR Footnotes Table - Add Subject Column
-- ============================================================================
-- Run this if the fsr_footnotes table already exists without the subject column
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
