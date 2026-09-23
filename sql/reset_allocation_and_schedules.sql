-- Courses page only: clear assignment data, keep catalogs and the timetable.
--
-- Removes:
--   faculty_courses            Faculty Assignment (who teaches which course+section)
--   faculty_eligible_courses   Course Assignment (who may teach a course)
--   course_term_offerings      Section Assignment (which sections are offered)
--   custom_term_blocks         Custom blocks for a school year + semester
--   configured_subjects        Legacy custom-block fallback
--   courses.available_sections Checked sections on each course (not the A–Z list)
--
-- Keeps:
--   courses                    Course catalog (CERP / HUME / NSTP, etc.)
--   sections / rooms           Extra section and room names
--   members                    Faculty cards
--   schedules                  Timetable blocks — delete those separately
--
-- Run this in the Supabase SQL editor.

delete from public.faculty_courses;
delete from public.faculty_eligible_courses;
delete from public.course_term_offerings;
delete from public.custom_term_blocks;
delete from public.configured_subjects;

update public.courses
set available_sections = '{}';
