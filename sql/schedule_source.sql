-- Label how a timetable block was created (GA vs manual).
-- Run this in the Supabase SQL editor, then NOTIFY pgrst, 'reload schema';

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS source text;

COMMENT ON COLUMN schedules.source IS
    'Origin of the block: GA Generated, Manual, or CHE.';
