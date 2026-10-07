-- ═══════════════════════════════════════════════════════════════════
-- SECTION ROOM ALLOCATIONS TABLE
-- Maps course sections to specific rooms for a given term
-- This is Step 3 in the Courses V2 workflow.
-- ═══════════════════════════════════════════════════════════════════

-- Drop existing table if it exists
DROP TABLE IF EXISTS public.section_room_allocations CASCADE;

-- Create section_room_allocations table
CREATE TABLE public.section_room_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES public.courses(id) ON DELETE CASCADE,
    section_letter TEXT NOT NULL,
    school_year TEXT NOT NULL,
    semester TEXT NOT NULL,
    
    -- Room can be either predefined or custom
    room_id UUID REFERENCES public.rooms(id) ON DELETE SET NULL,
    custom_room_name TEXT, -- For custom blocks or one-off rooms
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique room allocation per section per term
    UNIQUE(course_id, section_letter, school_year, semester)
);

-- Add indexes for common queries
CREATE INDEX idx_section_rooms_course ON public.section_room_allocations(course_id);
CREATE INDEX idx_section_rooms_term ON public.section_room_allocations(school_year, semester);
CREATE INDEX idx_section_rooms_room ON public.section_room_allocations(room_id) WHERE room_id IS NOT NULL;

-- Add RLS policies
ALTER TABLE public.section_room_allocations ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read
CREATE POLICY "Allow authenticated read access" 
    ON public.section_room_allocations 
    FOR SELECT 
    TO authenticated 
    USING (true);

-- Allow authenticated users to insert
CREATE POLICY "Allow authenticated insert access" 
    ON public.section_room_allocations 
    FOR INSERT 
    TO authenticated 
    WITH CHECK (true);

-- Allow authenticated users to update
CREATE POLICY "Allow authenticated update access" 
    ON public.section_room_allocations 
    FOR UPDATE 
    TO authenticated 
    USING (true);

-- Allow authenticated users to delete
CREATE POLICY "Allow authenticated delete access" 
    ON public.section_room_allocations 
    FOR DELETE 
    TO authenticated 
    USING (true);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_section_room_allocations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_section_room_allocations_updated_at
    BEFORE UPDATE ON public.section_room_allocations
    FOR EACH ROW
    EXECUTE FUNCTION update_section_room_allocations_updated_at();

-- Grant permissions
GRANT ALL ON public.section_room_allocations TO authenticated;
GRANT ALL ON public.section_room_allocations TO service_role;

-- Add helpful comment
COMMENT ON TABLE public.section_room_allocations IS 
    'Maps course sections to specific rooms for scheduling. Part of Courses V2 Step 3 (Room Allocation).';

COMMENT ON COLUMN public.section_room_allocations.room_id IS 
    'Reference to predefined room. NULL if using custom_room_name';

COMMENT ON COLUMN public.section_room_allocations.custom_room_name IS 
    'Custom room name for one-off allocations or custom blocks';
