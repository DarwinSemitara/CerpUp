-- Per-assignment units for Faculty Assignment.
-- The schedules page and GA use this as the contact-hour cap for that
-- course+section. The course catalog units stay as the default.
--
-- Run once in the Supabase SQL editor.

alter table public.faculty_courses
    add column if not exists units numeric;

update public.faculty_courses fc
set units = coalesce(c.units, 3)
from public.courses c
where fc.course_id = c.id
  and fc.units is null;

-- Make the new column visible to the REST API
notify pgrst, 'reload schema';
