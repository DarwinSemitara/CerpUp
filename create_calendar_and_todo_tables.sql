-- ================================================================
-- SQL Script: Calendar Events and To-Do Items Tables
-- Description: Creates tables for storing calendar events and todo tasks
-- ================================================================

-- Table: calendar_events
-- Stores calendar events with date, name, and importance level
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    importance VARCHAR(10) NOT NULL CHECK (importance IN ('low', 'medium', 'high')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, event_date)  -- One event per user per date
);

-- Index for faster queries by user and date
CREATE INDEX IF NOT EXISTS idx_calendar_events_user_date ON calendar_events(user_id, event_date);

-- Index for querying by date range
CREATE INDEX IF NOT EXISTS idx_calendar_events_date ON calendar_events(event_date);

-- Table: todo_items
-- Stores to-do list items with completion status
CREATE TABLE IF NOT EXISTS todo_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    task_text TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_todo_items_user ON todo_items(user_id);

-- Index for filtering by completion status
CREATE INDEX IF NOT EXISTS idx_todo_items_completed ON todo_items(user_id, completed);

-- Trigger: Update updated_at timestamp for calendar_events
CREATE OR REPLACE FUNCTION update_calendar_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_calendar_events_timestamp
    BEFORE UPDATE ON calendar_events
    FOR EACH ROW
    EXECUTE FUNCTION update_calendar_events_updated_at();

-- Trigger: Update updated_at timestamp for todo_items
CREATE OR REPLACE FUNCTION update_todo_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_todo_items_timestamp
    BEFORE UPDATE ON todo_items
    FOR EACH ROW
    EXECUTE FUNCTION update_todo_items_updated_at();

-- Trigger: Set completed_at timestamp when todo is marked as completed
CREATE OR REPLACE FUNCTION set_todo_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed = TRUE AND OLD.completed = FALSE THEN
        NEW.completed_at = NOW();
    ELSIF NEW.completed = FALSE THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_todo_completed_at
    BEFORE UPDATE ON todo_items
    FOR EACH ROW
    WHEN (OLD.completed IS DISTINCT FROM NEW.completed)
    EXECUTE FUNCTION set_todo_completed_at();

-- Enable Row Level Security (RLS)
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE todo_items ENABLE ROW LEVEL SECURITY;

-- RLS Policies for calendar_events
-- Policy: Users can only see their own calendar events
CREATE POLICY calendar_events_select_policy ON calendar_events
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can only insert their own calendar events
CREATE POLICY calendar_events_insert_policy ON calendar_events
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only update their own calendar events
CREATE POLICY calendar_events_update_policy ON calendar_events
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only delete their own calendar events
CREATE POLICY calendar_events_delete_policy ON calendar_events
    FOR DELETE
    USING (auth.uid() = user_id);

-- RLS Policies for todo_items
-- Policy: Users can only see their own todo items
CREATE POLICY todo_items_select_policy ON todo_items
    FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can only insert their own todo items
CREATE POLICY todo_items_insert_policy ON todo_items
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only update their own todo items
CREATE POLICY todo_items_update_policy ON todo_items
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can only delete their own todo items
CREATE POLICY todo_items_delete_policy ON todo_items
    FOR DELETE
    USING (auth.uid() = user_id);

-- ================================================================
-- Comments for documentation
-- ================================================================

COMMENT ON TABLE calendar_events IS 'Stores calendar events with importance levels for admin dashboard';
COMMENT ON COLUMN calendar_events.event_date IS 'Date of the calendar event';
COMMENT ON COLUMN calendar_events.event_name IS 'Name or description of the event';
COMMENT ON COLUMN calendar_events.importance IS 'Importance level: low (faded green), medium (light green), high (solid green)';

COMMENT ON TABLE todo_items IS 'Stores to-do list items for admin dashboard';
COMMENT ON COLUMN todo_items.task_text IS 'Description of the task';
COMMENT ON COLUMN todo_items.completed IS 'Whether the task has been completed';
COMMENT ON COLUMN todo_items.completed_at IS 'Timestamp when the task was marked as completed';

-- ================================================================
-- Sample data (optional - remove in production)
-- ================================================================

-- Example calendar events (replace 'YOUR_USER_ID' with actual user ID)
-- INSERT INTO calendar_events (user_id, event_date, event_name, importance) 
-- VALUES 
--     ('YOUR_USER_ID', '2026-08-15', 'Faculty Meeting', 'high'),
--     ('YOUR_USER_ID', '2026-08-20', 'Research Presentation', 'medium'),
--     ('YOUR_USER_ID', '2026-08-25', 'Department Lunch', 'low');

-- Example todo items (replace 'YOUR_USER_ID' with actual user ID)
-- INSERT INTO todo_items (user_id, task_text, completed) 
-- VALUES 
--     ('YOUR_USER_ID', 'Review research proposals', false),
--     ('YOUR_USER_ID', 'Update extension records', false),
--     ('YOUR_USER_ID', 'Prepare monthly report', false);
