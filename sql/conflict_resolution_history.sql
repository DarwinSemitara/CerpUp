-- ═══════════════════════════════════════════════════════════════════════════
-- Conflict Resolution History Table
-- ═══════════════════════════════════════════════════════════════════════════
-- Tracks all conflict resolutions for auditing and undo functionality
--
-- Features:
-- • Logs every schedule change made during conflict resolution
-- • Stores original and new values for rollback
-- • Groups changes by resolution session
-- • Tracks who initiated the resolution (admin/system)
-- • Enables undo functionality
--
-- Run this in your Supabase SQL editor
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS conflict_resolution_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Resolution session info
    resolution_session_id UUID NOT NULL,  -- Group all changes from one resolution run
    school_year VARCHAR(20) NOT NULL,
    semester VARCHAR(10) NOT NULL,
    
    -- Conflict details
    conflict_type VARCHAR(50) NOT NULL,  -- 'room', 'faculty', 'section', 'time_overlap'
    conflict_description TEXT,
    
    -- Schedule being modified
    schedule_id UUID NOT NULL,  -- References schedules table
    subject_code VARCHAR(20),
    section VARCHAR(50),
    professor VARCHAR(255),
    
    -- Original values (before resolution)
    original_day VARCHAR(20),
    original_start VARCHAR(10),
    original_end VARCHAR(10),
    original_room VARCHAR(50),
    
    -- New values (after resolution)
    new_day VARCHAR(20),
    new_start VARCHAR(10),
    new_end VARCHAR(10),
    new_room VARCHAR(50),
    
    -- Resolution metadata
    resolution_strategy VARCHAR(100),  -- 'time_shift', 'room_change', 'day_shift', 'combined'
    emergency_exception_used BOOLEAN DEFAULT FALSE,  -- True if 8-hour limit was used
    paired_schedule_count INTEGER DEFAULT 1,  -- How many schedules moved together (MW/TTH/MWF)
    
    -- Audit fields
    resolved_at TIMESTAMP DEFAULT NOW(),
    resolved_by VARCHAR(255),  -- User who triggered resolution
    notes TEXT,
    
    -- Undo tracking
    is_undone BOOLEAN DEFAULT FALSE,
    undone_at TIMESTAMP,
    undone_by VARCHAR(255)
);

-- Indexes for performance
CREATE INDEX idx_conflict_history_session ON conflict_resolution_history(resolution_session_id);
CREATE INDEX idx_conflict_history_schedule ON conflict_resolution_history(schedule_id);
CREATE INDEX idx_conflict_history_semester ON conflict_resolution_history(school_year, semester);
CREATE INDEX idx_conflict_history_resolved_at ON conflict_resolution_history(resolved_at);

-- ═══════════════════════════════════════════════════════════════════════════
-- Resolution Summary View
-- ═════���═════════════════════════════════════════════════════════════════════
-- Quick view of resolution sessions

CREATE OR REPLACE VIEW conflict_resolution_summary AS
SELECT 
    resolution_session_id,
    school_year,
    semester,
    COUNT(*) as total_changes,
    COUNT(DISTINCT schedule_id) as schedules_affected,
    COUNT(DISTINCT conflict_type) as conflict_types_resolved,
    SUM(CASE WHEN emergency_exception_used THEN 1 ELSE 0 END) as emergency_exceptions,
    SUM(CASE WHEN is_undone THEN 1 ELSE 0 END) as undone_changes,
    MIN(resolved_at) as resolution_started,
    MAX(resolved_at) as resolution_completed,
    resolved_by
FROM conflict_resolution_history
GROUP BY resolution_session_id, school_year, semester, resolved_by
ORDER BY resolution_started DESC;

-- ═══════════════════════════════════════════════════════════════════════════
-- Sample Queries
-- ═══════════════════════════════════════════════════════════════════════════

-- View recent resolutions
-- SELECT * FROM conflict_resolution_summary LIMIT 10;

-- View details of a specific resolution session
-- SELECT * FROM conflict_resolution_history 
-- WHERE resolution_session_id = '<session-id>' 
-- ORDER BY resolved_at;

-- Find all changes for a specific schedule
-- SELECT * FROM conflict_resolution_history 
-- WHERE schedule_id = '<schedule-id>' 
-- ORDER BY resolved_at DESC;

-- Count resolutions by conflict type
-- SELECT conflict_type, COUNT(*) as count
-- FROM conflict_resolution_history
-- WHERE is_undone = FALSE
-- GROUP BY conflict_type
-- ORDER BY count DESC;
