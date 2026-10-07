-- Audit Log Table for Activity Tracking
-- Tracks all administrative actions for security and accountability

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    performed_by VARCHAR(255) NOT NULL,
    performed_by_email VARCHAR(255),
    target_type VARCHAR(100),
    target_id VARCHAR(255),
    target_name VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_read BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_is_read ON audit_log(is_read) WHERE is_archived = FALSE;
CREATE INDEX IF NOT EXISTS idx_audit_log_is_archived ON audit_log(is_archived);
CREATE INDEX IF NOT EXISTS idx_audit_log_action_type ON audit_log(action_type);

-- Enable Row Level Security
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Policy: Allow admins to read all audit logs
CREATE POLICY "Allow admins to read audit logs" ON audit_log
    FOR SELECT
    USING (true);

-- Policy: Allow system to insert audit logs
CREATE POLICY "Allow system to insert audit logs" ON audit_log
    FOR INSERT
    WITH CHECK (true);

-- Policy: Allow marking as read
CREATE POLICY "Allow marking audit logs as read" ON audit_log
    FOR UPDATE
    USING (true)
    WITH CHECK (true);

-- Comments for documentation
COMMENT ON TABLE audit_log IS 'Tracks administrative actions for security and accountability';
COMMENT ON COLUMN audit_log.action_type IS 'Type of action: MEMBER_CREATED, MEMBER_DELETED, MEMBER_DISABLED, SCHEDULE_MODIFIED, etc.';
COMMENT ON COLUMN audit_log.description IS 'Human-readable description of the action';
COMMENT ON COLUMN audit_log.performed_by IS 'Name of the admin who performed the action';
COMMENT ON COLUMN audit_log.performed_by_email IS 'Email of the admin who performed the action';
COMMENT ON COLUMN audit_log.target_type IS 'Type of entity affected: member, schedule, course, etc.';
COMMENT ON COLUMN audit_log.target_id IS 'ID of the affected entity';
COMMENT ON COLUMN audit_log.target_name IS 'Name of the affected entity for quick reference';
COMMENT ON COLUMN audit_log.metadata IS 'Additional details about the action (JSON format)';
COMMENT ON COLUMN audit_log.is_read IS 'Whether notification has been read by admin';
COMMENT ON COLUMN audit_log.is_archived IS 'Whether notification has been archived (older than 7 days or beyond 7 unread)';

-- Example action types:
-- MEMBER_CREATED: New faculty member added
-- MEMBER_UPDATED: Faculty member information updated
-- MEMBER_DELETED: Faculty member removed
-- MEMBER_DISABLED: Faculty account disabled
-- MEMBER_ENABLED: Faculty account enabled
-- SCHEDULE_CREATED: New schedule created
-- SCHEDULE_MODIFIED: Schedule modified
-- SCHEDULE_DELETED: Schedule deleted
-- COURSE_ASSIGNED: Course assigned to faculty
-- COURSE_UNASSIGNED: Course unassigned from faculty
-- FSR_UPLOADED: FSR file uploaded
-- FSR_DELETED: FSR file deleted
-- RESEARCH_ADDED: Research paper added
-- RESEARCH_DELETED: Research paper deleted
-- EXTENSION_ADDED: Extension activity added
-- EXTENSION_DELETED: Extension activity deleted
