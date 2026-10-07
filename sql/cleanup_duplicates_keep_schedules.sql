-- ============================================================================
-- CLEANUP: Remove V1 Duplicate Assignments While Preserving Schedules
-- ============================================================================
-- PROBLEM:
--   V1 created faculty_courses entries -> those got scheduled
--   V2 ALSO created faculty_courses entries for same courses
--   Result: Staging area shows duplicates because both V1 and V2 entries exist
--
-- SOLUTION:
--   Remove older (V1) faculty_courses entries
--   Keep newer (V2) faculty_courses entries  
--   Schedules table is INDEPENDENT - uses subj_code/section/prof matching
--   Your "okay schedules" remain intact!
-- ============================================================================

-- ============================================================================
-- STEP 1: INVESTIGATE - See the current situation
-- ============================================================================

-- 1A: See which faculty+course+section combos are duplicated
SELECT 
    m.first || ' ' || m.last as faculty_name,
    c.course_code,
    fc.section,
    COUNT(*) as duplicate_count,
    string_agg(fc.id || ' (created: ' || fc.created_at::date::text || ')', E'\n') as entries
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
GROUP BY fc.faculty_id, m.first, m.last, c.course_code, fc.section
HAVING COUNT(*) > 1
ORDER BY faculty_name, c.course_code;

-- 1B: Check how many schedules exist (for verification later)
SELECT 
    school_year,
    semester,
    COUNT(*) as schedule_count,
    COUNT(DISTINCT subj_code || '-' || section) as unique_course_sections
FROM schedules
GROUP BY school_year, semester
ORDER BY school_year, semester;

-- ============================================================================
-- STEP 2: UNDERSTAND THE RELATIONSHIP
-- ============================================================================

-- See a sample duplicate with its schedules
-- Replace 'CERP 140' and 'V' with one of your duplicates from Step 1A
/*
SELECT 
    'Faculty Assignment' as type,
    fc.id,
    fc.created_at,
    m.first || ' ' || m.last as name,
    c.course_code,
    fc.section,
    fc.units,
    NULL as day,
    NULL as time
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
WHERE c.course_code = 'CERP 140' AND fc.section = 'V'

UNION ALL

SELECT 
    'Actual Schedule' as type,
    s.id,
    s.created_at,
    s.prof as name,
    s.subj_code as course_code,
    s.section,
    s.units,
    s.day,
    s.start || '-' || s.end as time
FROM schedules s
WHERE s.subj_code = 'CERP140' AND s.section = 'V'
ORDER BY type DESC, created_at;
*/

-- This shows:
-- - Multiple faculty_courses entries (duplicates)
-- - Schedules that exist independently
-- - Schedules DON'T reference faculty_courses.id

-- ============================================================================
-- STEP 3: DRY RUN - What will be deleted
-- ============================================================================

-- 3A: Show OLD entries that would be removed (V1 data)
WITH duplicates AS (
    SELECT 
        faculty_id,
        course_id,
        section,
        MAX(id) as keep_id  -- Highest ID = newest = V2
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
    HAVING COUNT(*) > 1
)
SELECT 
    fc.id as "Will Delete (V1 entry)",
    m.first || ' ' || m.last as faculty_name,
    c.course_code,
    fc.section,
    fc.created_at as old_created_date,
    d.keep_id as "Will Keep (V2 entry)"
FROM faculty_courses fc
JOIN duplicates d ON 
    fc.faculty_id = d.faculty_id AND
    fc.course_id = d.course_id AND
    fc.section = d.section
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
WHERE fc.id != d.keep_id  -- This is the OLD one
ORDER BY faculty_name, c.course_code;

-- Review this! These are V1 entries that will be removed.
-- V2 entries (higher ID, newer date) will be KEPT.

-- 3B: Verify schedules will NOT be affected
-- Check if any schedules match the courses we're cleaning
WITH to_delete AS (
    SELECT 
        fc.faculty_id,
        fc.course_id,
        fc.section,
        c.course_code,
        m.first || ' ' || m.last as prof_name
    FROM faculty_courses fc
    LEFT JOIN courses c ON fc.course_id = c.id
    LEFT JOIN members m ON fc.faculty_id = m.id
    WHERE fc.id NOT IN (
        SELECT MAX(id)
        FROM faculty_courses
        GROUP BY faculty_id, course_id, section
    )
)
SELECT 
    td.course_code,
    td.section,
    td.prof_name,
    'Has ' || COUNT(s.id) || ' scheduled time blocks' as schedule_info
FROM to_delete td
LEFT JOIN schedules s ON 
    REPLACE(s.subj_code, ' ', '') = REPLACE(td.course_code, ' ', '') AND
    s.section = td.section AND
    s.prof = td.prof_name
GROUP BY td.course_code, td.section, td.prof_name
HAVING COUNT(s.id) > 0;

-- This shows schedules exist for courses we're removing duplicates from
-- These schedules will REMAIN INTACT!

-- ============================================================================
-- STEP 4: BACKUP (Recommended)
-- ============================================================================

CREATE TABLE IF NOT EXISTS faculty_courses_backup_before_cleanup AS
SELECT fc.*, 
       m.first || ' ' || m.last as faculty_name,
       c.course_code,
       'V1_duplicate' as reason
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
WHERE fc.id NOT IN (
    SELECT MAX(id)
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
);

-- Verify backup
SELECT COUNT(*) as "Backed up V1 duplicates" 
FROM faculty_courses_backup_before_cleanup;

-- ============================================================================
-- STEP 5: ACTUAL CLEANUP (Only run after Steps 1-4!)
-- ============================================================================
-- ⚠️ This deletes V1 duplicate entries
-- ✅ Keeps V2 entries (newest, highest ID)
-- ✅ Schedules table is untouched

DELETE FROM faculty_courses
WHERE id NOT IN (
    SELECT MAX(id)
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
);

-- Check result
SELECT 
    (SELECT COUNT(*) FROM faculty_courses_backup_before_cleanup) as deleted_count,
    'V1 duplicate entries removed' as status;

-- ============================================================================
-- STEP 6: VERIFICATION
-- ============================================================================

-- 6A: Confirm no duplicates remain
SELECT 
    faculty_id,
    course_id,
    section,
    COUNT(*) as count
FROM faculty_courses
GROUP BY faculty_id, course_id, section
HAVING COUNT(*) > 1;
-- Should return NO ROWS

-- 6B: Verify schedules are UNCHANGED
SELECT 
    school_year,
    semester,
    COUNT(*) as schedule_count,
    COUNT(DISTINCT subj_code || '-' || section) as unique_course_sections
FROM schedules
GROUP BY school_year, semester
ORDER BY school_year, semester;
-- Should show SAME counts as Step 1B

-- 6C: Check staging area calculation
-- Pick a faculty that had duplicates and verify their unscheduled blocks
/*
WITH faculty_assignments AS (
    SELECT 
        c.course_code,
        fc.section,
        fc.units as assigned_units
    FROM faculty_courses fc
    JOIN courses c ON fc.course_id = c.id
    JOIN members m ON fc.faculty_id = m.id
    WHERE m.first || ' ' || m.last = 'Juan Cruz'  -- Replace with actual faculty name
),
scheduled_units AS (
    SELECT 
        subj_code as course_code,
        section,
        SUM(
            (EXTRACT(EPOCH FROM (end::time - start::time)) / 3600)
        ) as scheduled_hours
    FROM schedules
    WHERE prof = 'Juan Cruz'  -- Replace with actual faculty name
    AND school_year = '2026-2027'  -- Replace with current year
    AND semester = '2'  -- Replace with current semester
    GROUP BY subj_code, section
)
SELECT 
    fa.course_code,
    fa.section,
    fa.assigned_units,
    COALESCE(su.scheduled_hours, 0) as scheduled_hours,
    fa.assigned_units - COALESCE(su.scheduled_hours, 0) as remaining_hours
FROM faculty_assignments fa
LEFT JOIN scheduled_units su ON 
    REPLACE(fa.course_code, ' ', '') = REPLACE(su.course_code, ' ', '') AND
    fa.section = su.section
ORDER BY fa.course_code;
*/
-- After cleanup, remaining_hours should match what staging area shows (no more doubles!)

-- ============================================================================
-- RECOVERY (if needed)
-- ============================================================================
/*
-- Restore from backup
INSERT INTO faculty_courses (id, faculty_id, course_id, section, units, created_at)
SELECT id, faculty_id, course_id, section, units, created_at
FROM faculty_courses_backup_before_cleanup;

-- Then delete the backup table
DROP TABLE faculty_courses_backup_before_cleanup;
*/

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- ✅ Removes OLD (V1) duplicate faculty_courses entries
-- ✅ Keeps NEWEST (V2) faculty_courses entries
-- ✅ Schedules table COMPLETELY UNTOUCHED
-- ✅ Schedules don't have foreign keys to faculty_courses
-- ✅ Schedules match by: subj_code + section + prof + year + semester
-- ✅ Your "okay schedules" are preserved
-- ✅ Staging area will show each course-section only once
-- ✅ Full backup created before deletion
-- ============================================================================
