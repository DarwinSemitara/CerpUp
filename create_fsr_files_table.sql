-- ============================================================================
-- FSR Files Table
-- ============================================================================
-- Stores metadata about generated FSR files stored in Supabase Storage
-- ============================================================================

CREATE TABLE IF NOT EXISTS fsr_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id TEXT NOT NULL,  -- Firebase uid of the faculty member
    
    -- Member info (denormalized for quick access)
    member_name TEXT NOT NULL,
    member_email TEXT,
    
    -- FSR details
    semester TEXT NOT NULL,
    academic_year TEXT NOT NULL,
    
    -- File storage info
    file_path TEXT NOT NULL,  -- Path in Supabase Storage bucket
    file_name TEXT NOT NULL,  -- Original filename
    file_size BIGINT,         -- File size in bytes
    storage_bucket TEXT DEFAULT 'fsr-files',  -- Supabase storage bucket name
    
    -- Download tracking
    download_count INTEGER DEFAULT 0,
    last_downloaded_at TIMESTAMPTZ,
    
    -- Metadata
    generated_by TEXT,  -- User who generated it (admin uid)
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- For soft delete
    deleted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT fsr_files_member_semester_year UNIQUE (member_id, semester, academic_year, deleted_at)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_fsr_files_member_id ON fsr_files(member_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_fsr_files_semester_year ON fsr_files(semester, academic_year) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_fsr_files_generated_at ON fsr_files(generated_at DESC) WHERE deleted_at IS NULL;

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_fsr_files_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_fsr_files_updated_at ON fsr_files;
CREATE TRIGGER update_fsr_files_updated_at
    BEFORE UPDATE ON fsr_files
    FOR EACH ROW
    EXECUTE FUNCTION update_fsr_files_updated_at();

-- Comments
COMMENT ON TABLE fsr_files IS 'Metadata for FSR files stored in Supabase Storage';
COMMENT ON COLUMN fsr_files.file_path IS 'Path in Supabase Storage bucket (e.g., 2025-2026/2nd-Semester/FSR_LastName_timestamp.xlsx)';
COMMENT ON COLUMN fsr_files.storage_bucket IS 'Supabase Storage bucket name';
COMMENT ON COLUMN fsr_files.download_count IS 'Number of times this file has been downloaded';


-- ============================================================================
-- Sample queries
-- ============================================================================

-- Get all FSR files for a member
-- SELECT * FROM fsr_files 
-- WHERE member_id = 'MEMBER_UID' AND deleted_at IS NULL
-- ORDER BY generated_at DESC;

-- Get FSR file for specific semester/year
-- SELECT * FROM fsr_files
-- WHERE member_id = 'MEMBER_UID' 
--   AND semester = '2nd Semester'
--   AND academic_year = '2025-2026'
--   AND deleted_at IS NULL
-- LIMIT 1;

-- Track download
-- UPDATE fsr_files
-- SET download_count = download_count + 1,
--     last_downloaded_at = NOW()
-- WHERE id = 'FSR_FILE_ID';

-- Soft delete
-- UPDATE fsr_files
-- SET deleted_at = NOW()
-- WHERE id = 'FSR_FILE_ID';
