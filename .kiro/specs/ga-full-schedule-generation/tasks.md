# Tasks: GA Full Schedule Generation

## Task 1: Enhance Data Models and Configuration
- [x] 1.1 Add `FullGAConfig` dataclass and `SubjectInput` dataclass to `services/scheduler_service.py`
- [x] 1.2 Extend `Gene.__slots__` with backward-compatible fields
- [ ] 1.3 Add `teaching_load` column to `members` table in Supabase (integer, nullable, default 18)
- [x] 1.4 Update `services/supabase_service.py` to include helper functions for fetching faculty with availability and teaching load data

## Task 2: Reference Semester Seeding
- [x] 2.1 Implement `load_reference_semester(semester, school_year)` function that queries the `schedules` table and returns a list of schedule dicts
- [x] 2.2 Implement `apply_overrides(reference_data, faculty_overrides)` function that modifies reference data with admin-specified changes (availability, professor swaps, load changes)
- [x] 2.3 Implement `seed_from_reference(reference_schedules, overrides, pop_size)` function that converts reference data into seed chromosomes with at least 20% direct copies
- [x] 2.4 Add error handling: return descriptive error when reference semester has no data

## Task 3: Enhanced Fitness Function
- [x] 3.1 Implement `fitness_v2()` with hard constraints H1-H7 (professor conflict, room conflict, section conflict, block length, availability violation, teaching load exceeded, allocation violation)
- [x] 3.2 Implement soft constraints S1-S5 (same-day clustering, consecutive hours >4, outside core hours, section gaps >2hrs, uneven weekly spread)
- [ ] 3.3 Write property test: availability hard constraint — scheduling outside availability adds HARD_PENALTY
- [ ] 3.4 Write property test: teaching load hard constraint — exceeding load adds HARD_PENALTY
- [ ] 3.5 Write property test: room conflict detection — overlapping room bookings detected and penalized

## Task 4: Enhanced GA Operators
- [x] 4.1 Implement `mutate_v2()` with availability-aware mutation (only mutate day to days in professor's availability)
- [x] 4.2 Implement `crossover_v2()` with section-aware crossover (keep section genes together)
- [x] 4.3 Implement adaptive mutation rate (starts 0.20, decays to 0.08 as best fitness improves)
- [x] 4.4 Update tournament selection to size k=4 for better selection pressure

## Task 5: Repair Pass
- [x] 5.1 Implement `repair_pass(chromosome, prof_availability, rooms, max_iterations=200)` with three repair strategies: move time slot, move day, swap room
- [ ] 5.2 Write property test: repair pass monotonicity — `fitness_v2(repair_pass(c)) <= fitness_v2(c)` for all chromosomes
- [x] 5.3 Add conflict flagging: when repair cannot resolve a violation, flag the specific genes in output with a conflict warning message

## Task 6: Main `run_full_ga()` Implementation
- [x] 6.1 Implement `run_full_ga(config, prof_availability)` orchestrating: validation → seeding → GA loop → repair → result assembly
- [x] 6.2 Add time-limit enforcement (10-second wall-clock cutoff, return best-so-far with warning)
- [x] 6.3 Add early termination when best fitness reaches 0
- [x] 6.4 Build result dictionary with schedules, fitness_score, generations_run, conflicts_remaining, faculty_loads, warnings, elapsed_seconds
- [ ] 6.5 Write property test: section coverage completeness — all input subject-section pairs appear in output
- [ ] 6.6 Write property test: early termination — if fitness=0 exists at generation G, GA stops at or before G

## Task 7: Flask API Endpoint
- [x] 7.1 Add `POST /api/schedule/generate-full` endpoint in `app.py` with request validation
- [x] 7.2 Implement reference semester loading from Supabase in the endpoint handler
- [x] 7.3 Implement faculty data loading (availability, teaching loads) from `members` table
- [x] 7.4 Add overwrite confirmation logic: check if target semester already has schedules, require `confirm_overwrite: true`
- [x] 7.5 Save generated schedules to Supabase `schedules` table with `type="generated"`, correct `semester` and `school_year`

## Task 8: CHE AI Assistant Integration
- [x] 8.1 Update `che_service.py` SYSTEM_PROMPT to add `generate_full_schedule` action type with parameter documentation
- [x] 8.2 Add parsing logic in the CHE action handler (in `app.py` or `schedule.html`) to handle the `generate_full_schedule` action block
- [x] 8.3 Add response formatting: after generation completes, CHE presents summary (entries generated, conflicts resolved, warnings)
- [x] 8.4 Add clarification flow: if the user's request is missing semester or school year, CHE asks before emitting action block

## Task 9: Frontend Integration
- [ ] 9.1 Add `generate_full_schedule` case to the action block handler in `templates/partials/schedule.html`
- [ ] 9.2 Add confirmation modal before overwriting existing semester schedules
- [ ] 9.3 Add loading state and progress indicator during generation (spinner + "Generating schedule..." message)
- [ ] 9.4 Refresh timetable grid and report table after successful generation
- [ ] 9.5 Display warnings/conflicts from GA output in toast notifications

## Task 10: Integration Testing and Validation
- [ ] 10.1 Write integration test: end-to-end generation with 15 faculty, 60 subject-sections, verify completion under 10 seconds
- [ ] 10.2 Write integration test: reference semester loading and override application
- [ ] 10.3 Write test: verify all generated entries have `type="generated"` field
- [ ] 10.4 Manual test: trigger generation via CHE AI chat with natural language command
- [ ] 10.5 Manual test: verify timetable UI displays generated schedule correctly with no visual conflicts
