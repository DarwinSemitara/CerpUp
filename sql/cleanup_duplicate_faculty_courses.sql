-- ============================================================================
-- CLEANUP: Remove Duplicate Faculty Course Assignments (SAFE VERSION)
-- ============================================================================
-- Problem: V1 and V2 both created entries in faculty_courses table
-- Solution: Keep only the most recent entry per faculty+course+section combo
-- NOTE: This does NOT touch your actual schedules (in 'schedules' table)
-- ============================================================================

-- ⚠️ IMPORTANT: Run these queries IN ORDER, one at a time!

-- ============================================================================
-- STEP 1: INVESTIGATE - See what duplicates exist
-- ============================================================================
-- This shows which faculty+course+section combos are duplicated
SELECT 
    fc.faculty_id,
    m.first || ' ' || m.last as faculty_name,
    c.course_code,
    fc.section,
    COUNT(*) as duplicate_count,
    string_agg(fc.id::text, ', ') as all_ids
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
GROUP BY fc.faculty_id, m.first, m.last, c.course_code, fc.section
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Expected result: Should show rows like:
-- | faculty_name | course_code | section | duplicate_count | all_ids |
-- | Juan Cruz    | CERP 140    | V       | 2               | abc-123, xyz-789 |

-- ============================================================================
-- STEP 2: DRY RUN - See what WOULD be deleted (doesn't actually delete)
-- ============================================================================
-- This shows exactly which IDs would be removed
SELECT 
    fc.id as "ID to Delete",
    m.first || ' ' || m.last as faculty_name,
    c.course_code,
    fc.section,
    fc.created_at
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
WHERE fc.id NOT IN (
    SELECT MAX(id)
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
)
ORDER BY faculty_name, c.course_code, fc.section;

-- Review this carefully! These are the OLD duplicates that will be removed.
-- The NEWEST entry (highest ID/created_at) will be KEPT.

-- ============================================================================
-- STEP 3: BACKUP (Optional but Recommended)
-- ============================================================================
-- Create a backup table of duplicates before deleting
CREATE TABLE IF NOT EXISTS faculty_courses_backup_duplicates AS
SELECT fc.*, 
       m.first || ' ' || m.last as faculty_name,
       c.course_code
FROM faculty_courses fc
LEFT JOIN members m ON fc.faculty_id = m.id
LEFT JOIN courses c ON fc.course_id = c.id
WHERE fc.id NOT IN (
    SELECT MAX(id)
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
);

-- Check backup was created
SELECT COUNT(*) as "Backed up duplicates count" FROM faculty_courses_backup_duplicates;

-- ============================================================================
-- STEP 4: ACTUAL CLEANUP (Only run after reviewing Steps 1-3!)
-- ============================================================================
-- ⚠️ This DELETES duplicate rows. Make sure you reviewed the dry run first!

DELETE FROM faculty_courses
WHERE id NOT IN (
    SELECT MAX(id)
    FROM faculty_courses
    GROUP BY faculty_id, course_id, section
);

-- See how many were deleted
-- (Should match the count from Step 2)

-- ============================================================================
-- STEP 5: VERIFICATION - Confirm no duplicates remain
-- ============================================================================
SELECT 
    faculty_id,
    course_id,
    section,
    COUNT(*) as duplicate_count
FROM faculty_courses
GROUP BY faculty_id, course_id, section
HAVING COUNT(*) > 1;

-- Expected result: NO ROWS (means no duplicates remain)

-- ============================================================================
-- STEP 6: SANITY CHECK - Verify your schedules are untouched
-- ============================================================================
-- Check your actual schedules are still there
SELECT 
    COUNT(*) as total_schedules,
    school_year,
    semester
FROM schedules
GROUP BY school_year, semester
ORDER BY school_year, semester;

-- This should show the SAME counts as before cleanup.
-- faculty_courses cleanup does NOT affect the schedules table!

-- ============================================================================
-- RECOVERY (If something goes wrong)
-- ============================================================================
-- Restore from backup (if you need to undo Step 4)
-- INSERT INTO faculty_courses 
-- SELECT id, faculty_id, course_id, section, units, created_at, updated_at
-- FROM faculty_courses_backup_duplicates;

-- ============================================================================
-- NOTES:
-- ✅ This only affects faculty_courses (assignment eligibility)
-- ✅ Does NOT touch schedules table (your actual schedule data)
-- ✅ Keeps the MOST RECENT assignment (highest ID)
-- ✅ Creates backup before deleting
-- ✅ Duplicates just mean staging area shows course twice
-- ============================================================================
