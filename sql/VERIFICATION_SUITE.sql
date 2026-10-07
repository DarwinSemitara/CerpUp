-- ═══════════════════════════════════════════════════════════════════
-- COMPLETE V1 → V2 VERIFICATION SUITE
-- Run ALL these queries and verify results before removing V1
-- ═══════════════════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════════════════
-- QUERY 1: Faculty Eligibility Comparison
-- V1 stores globally, V2 uses same table - should be identical
-- ═══════════════════════════════════════════════════════════════════
SELECT 
    'Faculty Eligibility Check' as verification_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT faculty_id) as unique_faculty,
    COUNT(DISTINCT course_id) as unique_courses,
    'Same table used by V1 and V2' as notes
FROM public.faculty_eligible_courses;

-- Expected: Should show all eligibility records (both systems use same table)


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 2: Section Configuration Comparison
-- Compare sections in course_term_offerings vs sections actually used in schedules
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_sections AS (
    SELECT DISTINCT
        c.id as course_id,
        c.course_code,
        s.section,
        s.school_year,
        s.semester
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
),
configured_sections AS (
    SELECT 
        cto.course_id,
        c.course_code,
        section_value as section,
        cto.school_year,
        cto.semester
    FROM public.course_term_offerings cto
    JOIN public.courses c ON c.id = cto.course_id
    CROSS JOIN LATERAL jsonb_array_elements_text(cto.available_sections) as section_value
    WHERE cto.school_year = '2026-2027'
      AND cto.semester = '1'
)
SELECT 
    'Section Configuration vs Schedules' as verification_type,
    (SELECT COUNT(DISTINCT course_code || '-' || section) FROM schedule_sections) as sections_in_schedules,
    (SELECT COUNT(DISTINCT course_code || '-' || section) FROM configured_sections) as sections_in_v2_config,
    (SELECT COUNT(DISTINCT ss.course_code || '-' || ss.section) 
     FROM schedule_sections ss
     WHERE NOT EXISTS (
         SELECT 1 FROM configured_sections cs
         WHERE cs.course_code = ss.course_code AND cs.section = ss.section
     )) as missing_sections_in_v2,
    CASE 
        WHEN (SELECT COUNT(DISTINCT ss.course_code || '-' || ss.section) 
              FROM schedule_sections ss
              WHERE NOT EXISTS (
                  SELECT 1 FROM configured_sections cs
                  WHERE cs.course_code = ss.course_code AND cs.section = ss.section
              )) = 0 
        THEN '✅ ALL SECTIONS CONFIGURED'
        ELSE '❌ MISSING SECTIONS'
    END as status;

-- Expected: missing_sections_in_v2 should be 0


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 3: List Missing Sections (if any)
-- Shows which sections are in schedules but not in V2 configuration
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_sections AS (
    SELECT DISTINCT
        c.id as course_id,
        c.course_code,
        s.section,
        COUNT(*) as schedule_entries
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
    GROUP BY c.id, c.course_code, s.section
),
configured_sections AS (
    SELECT 
        cto.course_id,
        c.course_code,
        section_value as section
    FROM public.course_term_offerings cto
    JOIN public.courses c ON c.id = cto.course_id
    CROSS JOIN LATERAL jsonb_array_elements_text(cto.available_sections) as section_value
    WHERE cto.school_year = '2026-2027'
      AND cto.semester = '1'
)
SELECT 
    'Missing Sections Detail' as verification_type,
    ss.course_code,
    ss.section,
    ss.schedule_entries as times_in_schedules,
    '❌ NOT IN V2 CONFIG' as issue
FROM schedule_sections ss
WHERE NOT EXISTS (
    SELECT 1 FROM configured_sections cs
    WHERE cs.course_code = ss.course_code AND cs.section = ss.section
)
ORDER BY ss.course_code, ss.section;

-- Expected: No rows returned (0 missing sections)


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 4: Faculty Assignment Comparison
-- Compare assignments in faculty_courses (term-specific) vs schedules
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_assignments AS (
    SELECT DISTINCT
        c.id as course_id,
        c.course_code,
        s.section,
        s.prof as faculty_name,
        COUNT(*) as schedule_blocks
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
    GROUP BY c.id, c.course_code, s.section, s.prof
),
v2_assignments AS (
    SELECT 
        fc.course_id,
        c.course_code,
        fc.section,
        m.first || ' ' || m.last as faculty_name
    FROM public.faculty_courses fc
    JOIN public.courses c ON c.id = fc.course_id
    JOIN public.members m ON m.id = fc.faculty_id
    WHERE fc.school_year = '2026-2027'
      AND fc.semester = '1'
)
SELECT 
    'Faculty Assignment Comparison' as verification_type,
    (SELECT COUNT(*) FROM schedule_assignments) as assignments_in_schedules,
    (SELECT COUNT(*) FROM v2_assignments) as assignments_in_v2,
    (SELECT COUNT(*) 
     FROM schedule_assignments sa
     WHERE NOT EXISTS (
         SELECT 1 FROM v2_assignments v2a
         WHERE v2a.course_code = sa.course_code 
           AND v2a.section = sa.section
           AND v2a.faculty_name = sa.faculty_name
     )) as missing_assignments_in_v2,
    CASE 
        WHEN (SELECT COUNT(*) 
              FROM schedule_assignments sa
              WHERE NOT EXISTS (
                  SELECT 1 FROM v2_assignments v2a
                  WHERE v2a.course_code = sa.course_code 
                    AND v2a.section = sa.section
                    AND v2a.faculty_name = sa.faculty_name
              )) = 0
        THEN '✅ ALL ASSIGNMENTS MATCH'
        ELSE '❌ MISSING ASSIGNMENTS'
    END as status;

-- Expected: missing_assignments_in_v2 should be 0


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 5: List Missing Assignments (if any)
-- Shows which faculty-course-section combinations are in schedules but not in V2
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_assignments AS (
    SELECT DISTINCT
        c.id as course_id,
        c.course_code,
        s.section,
        s.prof as faculty_name
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
),
v2_assignments AS (
    SELECT 
        fc.course_id,
        c.course_code,
        fc.section,
        m.first || ' ' || m.last as faculty_name
    FROM public.faculty_courses fc
    JOIN public.courses c ON c.id = fc.course_id
    JOIN public.members m ON m.id = fc.faculty_id
    WHERE fc.school_year = '2026-2027'
      AND fc.semester = '1'
)
SELECT 
    'Missing Assignments Detail' as verification_type,
    sa.course_code,
    sa.section,
    sa.faculty_name,
    '❌ IN SCHEDULES BUT NOT IN V2' as issue
FROM schedule_assignments sa
WHERE NOT EXISTS (
    SELECT 1 FROM v2_assignments v2a
    WHERE v2a.course_code = sa.course_code 
      AND v2a.section = sa.section
      AND v2a.faculty_name = sa.faculty_name
)
ORDER BY sa.course_code, sa.section;

-- Expected: No rows returned (0 missing assignments)


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 6: Room Allocation Comparison
-- Compare rooms in section_room_allocations vs schedules
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_rooms AS (
    SELECT DISTINCT
        c.id as course_id,
        c.course_code,
        s.section,
        s.room,
        COUNT(*) as times_used
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
      AND s.room IS NOT NULL
      AND s.room != ''
      AND s.room != 'TBA'
    GROUP BY c.id, c.course_code, s.section, s.room
),
v2_rooms AS (
    SELECT 
        sra.course_id,
        c.course_code,
        sra.section_letter as section,
        sra.custom_room_name as room
    FROM public.section_room_allocations sra
    JOIN public.courses c ON c.id = sra.course_id
    WHERE sra.school_year = '2026-2027'
      AND sra.semester = '1'
),
most_used_rooms AS (
    SELECT 
        course_id,
        course_code,
        section,
        room,
        times_used,
        ROW_NUMBER() OVER (PARTITION BY course_id, section ORDER BY times_used DESC) as rn
    FROM schedule_rooms
)
SELECT 
    'Room Allocation Comparison' as verification_type,
    (SELECT COUNT(DISTINCT course_code || '-' || section) FROM most_used_rooms WHERE rn = 1) as sections_with_rooms_in_schedules,
    (SELECT COUNT(DISTINCT course_code || '-' || section) FROM v2_rooms) as sections_with_rooms_in_v2,
    (SELECT COUNT(DISTINCT mur.course_code || '-' || mur.section)
     FROM most_used_rooms mur
     WHERE mur.rn = 1
       AND NOT EXISTS (
           SELECT 1 FROM v2_rooms v2r
           WHERE v2r.course_code = mur.course_code 
             AND v2r.section = mur.section
       )) as missing_room_assignments_in_v2,
    CASE 
        WHEN (SELECT COUNT(DISTINCT mur.course_code || '-' || mur.section)
              FROM most_used_rooms mur
              WHERE mur.rn = 1
                AND NOT EXISTS (
                    SELECT 1 FROM v2_rooms v2r
                    WHERE v2r.course_code = mur.course_code 
                      AND v2r.section = mur.section
                )) = 0
        THEN '✅ ALL ROOMS CONFIGURED'
        ELSE '❌ MISSING ROOM ASSIGNMENTS'
    END as status;

-- Expected: missing_room_assignments_in_v2 should be 0


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 7: Room Assignment Accuracy Check
-- Verify that rooms in V2 match the most-used rooms in schedules
-- ═══════════════════════════════════════════════════════════════════
WITH schedule_rooms AS (
    SELECT 
        c.id as course_id,
        c.course_code,
        s.section,
        s.room,
        COUNT(*) as times_used,
        ROW_NUMBER() OVER (PARTITION BY c.id, s.section ORDER BY COUNT(*) DESC) as rn
    FROM public.schedules s
    JOIN public.courses c ON c.course_code = s.subj_code
    WHERE s.school_year = '2026-2027'
      AND s.semester = '1'
      AND s.room IS NOT NULL
      AND s.room != ''
      AND s.room != 'TBA'
    GROUP BY c.id, c.course_code, s.section, s.room
),
v2_rooms AS (
    SELECT 
        sra.course_id,
        c.course_code,
        sra.section_letter as section,
        sra.custom_room_name as room
    FROM public.section_room_allocations sra
    JOIN public.courses c ON c.id = sra.course_id
    WHERE sra.school_year = '2026-2027'
      AND sra.semester = '1'
)
SELECT 
    sr.course_code,
    sr.section,
    sr.room as room_in_schedules,
    sr.times_used as schedule_usage,
    v2r.room as room_in_v2,
    CASE 
        WHEN v2r.room = sr.room THEN '✅ MATCH'
        WHEN v2r.room IS NULL THEN '❌ NOT IN V2'
        ELSE '⚠️ DIFFERENT ROOM'
    END as status
FROM schedule_rooms sr
LEFT JOIN v2_rooms v2r ON v2r.course_code = sr.course_code AND v2r.section = sr.section
WHERE sr.rn = 1
ORDER BY 
    CASE 
        WHEN v2r.room = sr.room THEN 3
        WHEN v2r.room IS NULL THEN 1
        ELSE 2
    END,
    sr.course_code, sr.section;

-- Expected: All rows should show '✅ MATCH'


-- ═══════════════════════════════════════════════════════════════════
-- QUERY 8: Data Completeness Summary
-- Final verification - all counts should match
-- ═══════════════════════════════════════════════════════════════════
SELECT 
    'FINAL VERIFICATION SUMMARY' as check_type,
    (SELECT COUNT(DISTINCT course_code || '-' || section) 
     FROM schedules s 
     JOIN courses c ON c.course_code = s.subj_code
     WHERE school_year = '2026-2027' AND semester = '1') as unique_sections_in_schedules,
    (SELECT COUNT(DISTINCT c.course_code || '-' || section_value)
     FROM course_term_offerings cto
     JOIN courses c ON c.id = cto.course_id
     CROSS JOIN LATERAL jsonb_array_elements_text(cto.available_sections) as section_value
     WHERE cto.school_year = '2026-2027' AND cto.semester = '1') as unique_sections_in_v2,
    (SELECT COUNT(*)
     FROM faculty_courses
     WHERE school_year = '2026-2027' AND semester = '1') as assignments_in_v2,
    (SELECT COUNT(*)
     FROM section_room_allocations
     WHERE school_year = '2026-2027' AND semester = '1') as room_allocations_in_v2,
    (SELECT COUNT(*) FROM faculty_eligible_courses) as eligibility_records,
    CASE 
        WHEN (SELECT COUNT(DISTINCT course_code || '-' || section) 
              FROM schedules s 
              JOIN courses c ON c.course_code = s.subj_code
              WHERE school_year = '2026-2027' AND semester = '1') = 
             (SELECT COUNT(DISTINCT c.course_code || '-' || section_value)
              FROM course_term_offerings cto
              JOIN courses c ON c.id = cto.course_id
              CROSS JOIN LATERAL jsonb_array_elements_text(cto.available_sections) as section_value
              WHERE cto.school_year = '2026-2027' AND cto.semester = '1')
        THEN '✅ READY TO REPLACE V1'
        ELSE '❌ DATA MISMATCH - DO NOT REPLACE V1'
    END as final_verdict;

-- Expected: final_verdict should be '✅ READY TO REPLACE V1'
