-- Administrative Works Table
-- Tracks faculty administrative responsibilities, committee work, and service roles

CREATE TABLE IF NOT EXISTS administrative_works (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uid UUID NOT NULL,
    
    -- Classification
    type VARCHAR(50) NOT NULL CHECK (type IN ('department', 'committee', 'special', 'organization', 'college_level')),
    type_code VARCHAR(20) NOT NULL, -- 'II.A.1', 'II.A.2', etc.
    
    -- Basic Info
    title VARCHAR(500) NOT NULL, -- e.g., "Department Chair", "Curriculum Committee Chair"
    role VARCHAR(200), -- 'Chair', 'Member', 'Coordinator', 'Adviser'
    description TEXT,
    
    -- Timeline
    start_date DATE NOT NULL,
    end_date DATE,
    is_ongoing BOOLEAN DEFAULT FALSE,
    
    -- Additional Details
    department VARCHAR(200), -- For department-level admin
    committee_name VARCHAR(300), -- For committee work
    organization_name VARCHAR(300), -- For student organizations
    scope VARCHAR(100), -- 'Department', 'College', 'University', 'External'
    members TEXT, -- Comma-separated list of other committee members
    accomplishments TEXT, -- Key achievements during tenure
    
    -- Workload
    credit_units DECIMAL(4,2), -- For FSR calculation
    hours_per_week DECIMAL(4,2), -- Average time commitment
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_admin_works_uid ON administrative_works(uid);
CREATE INDEX IF NOT EXISTS idx_admin_works_type ON administrative_works(type);
CREATE INDEX IF NOT EXISTS idx_admin_works_dates ON administrative_works(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_admin_works_created ON administrative_works(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_works_ongoing ON administrative_works(is_ongoing) WHERE is_ongoing = TRUE;

-- Enable Row Level Security
ALTER TABLE administrative_works ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own submissions
CREATE POLICY "Users can view own admin work"
    ON administrative_works FOR SELECT
    USING (auth.uid() = uid);

-- Policy: Users can insert their own submissions
CREATE POLICY "Users can insert own admin work"
    ON administrative_works FOR INSERT
    WITH CHECK (auth.uid() = uid);

-- Policy: Users can update their own submissions
CREATE POLICY "Users can update own admin work"
    ON administrative_works FOR UPDATE
    USING (auth.uid() = uid);

-- Policy: Users can delete their own submissions
CREATE POLICY "Users can delete own admin work"
    ON administrative_works FOR DELETE
    USING (auth.uid() = uid);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_administrative_works_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_administrative_works_updated_at_trigger
    BEFORE UPDATE ON administrative_works
    FOR EACH ROW
    EXECUTE FUNCTION update_administrative_works_updated_at();

-- Comments for documentation
COMMENT ON TABLE administrative_works IS 'Stores faculty administrative work, committee roles, and service activities';
COMMENT ON COLUMN administrative_works.type IS 'Category: department, committee, special, organization, college_level';
COMMENT ON COLUMN administrative_works.type_code IS 'FSR code reference (II.A.1 through II.A.5)';
COMMENT ON COLUMN administrative_works.credit_units IS 'Credit units for FSR workload calculation';
