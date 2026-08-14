-- Create configured_subjects table in Supabase
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS configured_subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subj_code TEXT NOT NULL,
    subj_name TEXT NOT NULL,
    prof TEXT NOT NULL,
    section TEXT NOT NULL,
    units NUMERIC DEFAULT 1.5,
    school_year TEXT NOT NULL,
    semester TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_configured_subjects_school_year_semester 
ON configured_subjects(school_year, semester);

CREATE INDEX IF NOT EXISTS idx_configured_subjects_prof 
ON configured_subjects(prof);

-- Enable Row Level Security (RLS)
ALTER TABLE configured_subjects ENABLE ROW LEVEL SECURITY;

-- Create policy to allow authenticated users to read/write
CREATE POLICY "Allow authenticated users full access to configured_subjects"
ON configured_subjects
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);
