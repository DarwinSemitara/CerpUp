-- ============================================================================
-- Create FSR Footnotes Table
-- ============================================================================
-- Stores footnotes for Faculty Service Reports (FSR)
-- Each footnote represents team teaching or relay teaching arrangements
-- ============================================================================

CREATE TABLE IF NOT EXISTS fsr_footnotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Faculty member and semester identification
    member_id UUID NOT NULL REFERENCES members(uid) ON DELETE CASCADE,
    semester TEXT NOT NULL,           -- Semester number: "1" or "2"
    academic_year TEXT NOT NULL,      -- e.g., "2025-2026"
    
    -- Footnote details
    footnote_number INTEGER NOT NULL, -- 1, 2, or 3
    subject TEXT,                     -- Subject/course code
    footnote_type TEXT NOT NULL,      -- "Team teaching" or "Relay teaching"
    faculty_name TEXT NOT NULL,       -- Co-faculty member name
    load_sharing TEXT,                -- e.g., "50-50 load sharing"
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one footnote per number per member/semester/year
    UNIQUE(member_id, semester, academic_year, footnote_number)
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_fsr_footnotes_member 
    ON fsr_footnotes(member_id, semester, academic_year);

-- Comments
COMMENT ON TABLE fsr_footnotes IS 'Footnotes for FSR documents indicating team/relay teaching arrangements';
COMMENT ON COLUMN fsr_footnotes.member_id IS 'Faculty member who owns this FSR';
COMMENT ON COLUMN fsr_footnotes.semester IS 'Semester number (1 or 2)';
COMMENT ON COLUMN fsr_footnotes.academic_year IS 'Academic year in format YYYY-YYYY';
COMMENT ON COLUMN fsr_footnotes.footnote_number IS 'Footnote number (1-3)';
COMMENT ON COLUMN fsr_footnotes.subject IS 'Subject/course code this footnote applies to';
COMMENT ON COLUMN fsr_footnotes.footnote_type IS 'Type: Team teaching or Relay teaching';
COMMENT ON COLUMN fsr_footnotes.faculty_name IS 'Name of co-faculty member';
COMMENT ON COLUMN fsr_footnotes.load_sharing IS 'Load sharing arrangement description';
