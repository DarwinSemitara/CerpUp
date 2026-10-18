-- Landing Page Content Management Tables
-- For managing News, Research Showcase, and Alumni Spotlight

-- News & Updates table
CREATE TABLE IF NOT EXISTS landing_news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT NOT NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_published BOOLEAN DEFAULT true,
    publish_date TIMESTAMPTZ DEFAULT NOW()
);

-- Research Showcase table
CREATE TABLE IF NOT EXISTS landing_research (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT NOT NULL,
    researchers TEXT,
    project_url TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_published BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0
);

-- Alumni Spotlight table
CREATE TABLE IF NOT EXISTS landing_alumni (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    graduation_year INTEGER,
    degree TEXT,
    current_position TEXT,
    company TEXT,
    achievement TEXT NOT NULL,
    image_url TEXT NOT NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_published BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0
);

-- Enable RLS
ALTER TABLE landing_news ENABLE ROW LEVEL SECURITY;
ALTER TABLE landing_research ENABLE ROW LEVEL SECURITY;
ALTER TABLE landing_alumni ENABLE ROW LEVEL SECURITY;

-- RLS Policies for landing_news
CREATE POLICY "Allow authenticated users to view published news"
    ON landing_news FOR SELECT
    TO authenticated
    USING (is_published = true);

CREATE POLICY "Allow authenticated users to insert news"
    ON landing_news FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow users to update their own news"
    ON landing_news FOR UPDATE
    TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY "Allow users to delete their own news"
    ON landing_news FOR DELETE
    TO authenticated
    USING (created_by = auth.uid());

-- RLS Policies for landing_research
CREATE POLICY "Allow authenticated users to view published research"
    ON landing_research FOR SELECT
    TO authenticated
    USING (is_published = true);

CREATE POLICY "Allow authenticated users to insert research"
    ON landing_research FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow users to update their own research"
    ON landing_research FOR UPDATE
    TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY "Allow users to delete their own research"
    ON landing_research FOR DELETE
    TO authenticated
    USING (created_by = auth.uid());

-- RLS Policies for landing_alumni
CREATE POLICY "Allow authenticated users to view published alumni"
    ON landing_alumni FOR SELECT
    TO authenticated
    USING (is_published = true);

CREATE POLICY "Allow authenticated users to insert alumni"
    ON landing_alumni FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Allow users to update their own alumni"
    ON landing_alumni FOR UPDATE
    TO authenticated
    USING (created_by = auth.uid());

CREATE POLICY "Allow users to delete their own alumni"
    ON landing_alumni FOR DELETE
    TO authenticated
    USING (created_by = auth.uid());

-- Public access policies (for landing page display)
CREATE POLICY "Allow public to view published news"
    ON landing_news FOR SELECT
    TO anon
    USING (is_published = true);

CREATE POLICY "Allow public to view published research"
    ON landing_research FOR SELECT
    TO anon
    USING (is_published = true);

CREATE POLICY "Allow public to view published alumni"
    ON landing_alumni FOR SELECT
    TO anon
    USING (is_published = true);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_landing_news_published ON landing_news(is_published, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_landing_research_published ON landing_research(is_published, display_order);
CREATE INDEX IF NOT EXISTS idx_landing_alumni_published ON landing_alumni(is_published, display_order);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_landing_news_updated_at BEFORE UPDATE ON landing_news
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_landing_research_updated_at BEFORE UPDATE ON landing_research
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_landing_alumni_updated_at BEFORE UPDATE ON landing_alumni
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
