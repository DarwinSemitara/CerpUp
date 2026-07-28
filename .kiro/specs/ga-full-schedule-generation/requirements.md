# Requirements Document

## Introduction

This feature enhances the existing Genetic Algorithm (GA) in CERP 2.0's `scheduler_service.py` to support full semester schedule generation for all faculty members and all sections in the College of Human Ecology (CHE) at UPLB. The enhanced GA will reference previous semesters as templates, respect individual faculty time availability and teaching load limits, handle room allocation, spread blocks professionally across the week, detect and resolve conflicts automatically, and integrate with the CHE AI Assistant for natural language triggering. The entire computation runs locally with zero external API costs and completes within seconds.

## Glossary

- **GA_Engine**: The enhanced Genetic Algorithm schedule generator module in `services/scheduler_service.py`
- **Schedule_Entry**: A single class session record stored in the `schedules` Supabase table containing professor, subject, day, time, room, section, and semester info
- **Faculty_Member**: A record in the `members` Supabase table where `is_faculty` is true, containing availability and teaching load configuration
- **Availability**: The list of days (and optionally time windows) a Faculty_Member is available to teach, stored in the `members.availability` field
- **Teaching_Load**: The maximum number of credit units an individual Faculty_Member may be assigned per semester, configurable by the admin
- **Reference_Semester**: A previously completed semester's schedule data used as the starting template for generating a new semester schedule
- **Conflict**: A situation where a professor, room, or section is double-booked in overlapping time slots on the same day
- **Chromosome**: A candidate full-semester schedule represented as a list of Gene objects in the GA population
- **Fitness_Score**: A numeric value (lower is better) measuring how well a Chromosome satisfies hard and soft constraints
- **CHE_Assistant**: The Groq/Llama 3.3 70B powered AI chatbot that interprets admin natural language commands and triggers GA_Engine actions via JSON action blocks
- **Subject_Allocation**: The mapping of which Faculty_Members are eligible or assigned to teach specific subjects/courses
- **Block_Spread**: The distribution pattern of class sessions across weekdays, favoring even distribution over clustering

## Requirements

### Requirement 1: Reference Semester Loading

**User Story:** As an admin, I want to base a new schedule on a previous semester's data, so that I can retain proven arrangements and only adjust for known changes.

#### Acceptance Criteria

1. WHEN the admin specifies a reference semester and school year, THE GA_Engine SHALL retrieve all Schedule_Entry records for that semester from the Supabase `schedules` table
2. WHEN the admin provides modifications (e.g., changed faculty availability, new subject allocations), THE GA_Engine SHALL apply those modifications to the reference data before seeding the initial population
3. IF the specified reference semester contains no Schedule_Entry records, THEN THE GA_Engine SHALL return a descriptive error message indicating no reference data exists
4. WHEN a Reference_Semester is loaded, THE GA_Engine SHALL use it to seed at least 20% of the initial population with chromosomes derived from that reference data

### Requirement 2: Faculty Availability Enforcement

**User Story:** As an admin, I want the GA to respect each faculty member's individual time availability, so that no one is scheduled outside their declared available days and times.

#### Acceptance Criteria

1. WHEN generating schedules, THE GA_Engine SHALL retrieve the Availability field for every Faculty_Member from the `members` table
2. THE GA_Engine SHALL treat scheduling a Faculty_Member outside their declared Availability as a hard constraint violation with maximum penalty
3. WHEN a Faculty_Member has no Availability data defined, THE GA_Engine SHALL treat them as available on all weekdays (Monday through Friday)
4. IF all valid time slots for a Faculty_Member are exhausted, THEN THE GA_Engine SHALL report that faculty member as over-allocated in the generation results

### Requirement 3: Teaching Load Limits

**User Story:** As an admin, I want to set a maximum teaching load per faculty member, so that no one is over-assigned beyond their capacity.

#### Acceptance Criteria

1. THE GA_Engine SHALL accept a teaching load limit (in credit units) for each Faculty_Member
2. WHEN a Chromosome assigns more total units to a Faculty_Member than their Teaching_Load limit, THE GA_Engine SHALL apply a hard constraint penalty to that Chromosome's Fitness_Score
3. WHEN no explicit Teaching_Load is configured for a Faculty_Member, THE GA_Engine SHALL use a default limit of 18 units
4. WHEN generation completes, THE GA_Engine SHALL include each Faculty_Member's assigned unit total in the output summary

### Requirement 4: Subject-Faculty Allocation

**User Story:** As an admin, I want to control which faculty members teach which subjects, so that schedules respect expertise and departmental assignments.

#### Acceptance Criteria

1. WHEN generating a full schedule, THE GA_Engine SHALL accept a Subject_Allocation mapping specifying which Faculty_Members can teach each subject
2. THE GA_Engine SHALL only assign a subject to a Faculty_Member listed in that subject's allocation
3. IF a subject has no Faculty_Members allocated, THEN THE GA_Engine SHALL mark it as unassigned in the output and exclude it from conflict penalties
4. WHEN using a Reference_Semester, THE GA_Engine SHALL preserve professor-subject assignments from the reference unless the admin explicitly overrides them

### Requirement 5: Room Allocation and Conflict Avoidance

**User Story:** As an admin, I want rooms to be assigned without overlaps, so that no two classes occupy the same room at the same time.

#### Acceptance Criteria

1. THE GA_Engine SHALL treat two Schedule_Entries assigned to the same room with overlapping time slots on the same day as a hard constraint violation
2. WHEN generating schedules, THE GA_Engine SHALL accept a list of available rooms and their capacity or type metadata
3. WHEN a room list is not provided, THE GA_Engine SHALL extract distinct rooms from the Reference_Semester data
4. IF no rooms are available for a time slot, THEN THE GA_Engine SHALL assign "TBA" and apply a soft constraint penalty

### Requirement 6: Professional Block Spreading

**User Story:** As an admin, I want class blocks spread evenly across the week, so that schedules look professional and avoid clustering everything on one or two days.

#### Acceptance Criteria

1. WHEN a subject requires multiple sessions per week, THE GA_Engine SHALL distribute those sessions across different days
2. THE GA_Engine SHALL apply a soft penalty when all sessions of a subject fall on the same day
3. THE GA_Engine SHALL apply a soft penalty when a Faculty_Member has more than 4 consecutive hours of teaching without a break
4. THE GA_Engine SHALL prefer placing classes within core hours (7:00 AM to 5:00 PM) by penalizing slots outside this range
5. WHEN a section has classes on a given day, THE GA_Engine SHALL prefer minimizing gaps between consecutive classes for that section

### Requirement 7: Conflict Detection and Auto-Resolution

**User Story:** As an admin, I want the GA to automatically detect and fix all scheduling conflicts, so that the generated schedule is immediately usable.

#### Acceptance Criteria

1. THE GA_Engine SHALL detect professor conflicts (same professor, overlapping times, same day)
2. THE GA_Engine SHALL detect room conflicts (same room, overlapping times, same day)
3. THE GA_Engine SHALL detect section conflicts (same section, overlapping times, same day)
4. WHEN the best Chromosome after all generations still contains hard constraint violations, THE GA_Engine SHALL run a targeted local-search repair pass to resolve remaining conflicts
5. WHEN a conflict cannot be resolved without violating another hard constraint, THE GA_Engine SHALL flag the specific entries in the output with a conflict warning

### Requirement 8: Performance Requirements

**User Story:** As an admin, I want full schedule generation to complete in seconds, so that the system remains responsive during use.

#### Acceptance Criteria

1. WHEN generating a full semester schedule for up to 30 Faculty_Members and 120 subject-section combinations, THE GA_Engine SHALL complete within 10 seconds on a standard desktop machine
2. THE GA_Engine SHALL execute entirely locally without making external API calls during the optimization process
3. THE GA_Engine SHALL support early termination when a zero-penalty Chromosome is found before reaching the maximum generation count
4. WHEN generation takes longer than 10 seconds, THE GA_Engine SHALL return the best solution found so far with a warning that optimization was incomplete

### Requirement 9: CHE AI Assistant Integration

**User Story:** As an admin, I want to trigger full schedule generation through natural language commands to the CHE AI Assistant, so that I can describe what I want conversationally.

#### Acceptance Criteria

1. WHEN the admin sends a natural language request to generate a full schedule (e.g., "generate full schedules like 2nd semester SY 2025-2026"), THE CHE_Assistant SHALL parse the reference semester, school year, and any specified modifications
2. THE CHE_Assistant SHALL emit a `generate_full_schedule` JSON action block with parameters including reference semester, school year, faculty overrides, and room list
3. WHEN the GA_Engine completes generation, THE CHE_Assistant SHALL present a summary of the result including total entries generated, conflicts resolved, and any warnings
4. IF the admin's request is ambiguous (missing semester or school year), THEN THE CHE_Assistant SHALL ask clarifying questions before emitting the action block

### Requirement 10: Output and Persistence

**User Story:** As an admin, I want generated schedules saved to the database and displayed in the timetable UI, so that I can review and further adjust them.

#### Acceptance Criteria

1. WHEN the GA_Engine completes generation, THE system SHALL save all generated Schedule_Entry records to the Supabase `schedules` table with the correct semester and school_year values
2. WHEN saving generated schedules, THE system SHALL set the `type` field to "generated" to distinguish them from manually created entries
3. WHEN schedule generation is triggered, THE system SHALL prompt the admin to confirm before overwriting existing schedules for the target semester
4. WHEN schedules are saved, THE frontend SHALL refresh the timetable grid to display the newly generated schedule data

### Requirement 11: Section Handling

**User Story:** As an admin, I want the GA to schedule all sections for each subject, so that the generated timetable covers every student group.

#### Acceptance Criteria

1. WHEN generating a full schedule, THE GA_Engine SHALL create Schedule_Entries for every subject-section combination provided in the input
2. THE GA_Engine SHALL ensure no section has overlapping classes at the same time on the same day
3. WHEN a subject has multiple sections, THE GA_Engine SHALL attempt to schedule them at different times to allow shared resource usage (rooms, labs)
4. WHEN using a Reference_Semester, THE GA_Engine SHALL preserve the section structure from the reference data unless explicitly modified

