# Design Document: GA Full Schedule Generation

## Overview

This design enhances the existing `scheduler_service.py` GA engine to support full-semester schedule generation for all CHE faculty and sections. The architecture preserves the current Gene/Chromosome model while adding reference semester seeding, enhanced constraint handling, a local-search repair pass, and integration hooks for the CHE AI Assistant.

## Architecture

### System Components

```
┌───────────────────────────────────────────────────────────────┐
│                      Frontend (schedule.html)                   │
│  - Timetable grid with drag-and-drop                          │
│  - CHE AI chat panel (triggers via JSON action blocks)         │
│  - School year / semester dropdowns (localStorage)            │
└────────────────────────────┬──────────────────────────────────┘
                             │ HTTP (AJAX / fetch)
┌────────────────────────────▼──────────────────────────────────┐
│                      Flask App (app.py)                         │
│  - POST /api/schedule/generate-full                           │
│  - POST /api/che/chat (CHE assistant endpoint)                │
└────────┬──────────────────────────────────┬───────────────────┘
         │                                  │
┌────────▼─────────┐            ┌───────────▼───────────────────┐
│ scheduler_service │            │       che_service.py           │
│ (Enhanced GA)     │            │  (Groq/Llama - NLP only)      │
│                   │◄───────────┤  Emits generate_full_schedule │
│ - run_full_ga()   │            │  action block                 │
│ - fitness_v2()    │            └───────────────────────────────┘
│ - repair_pass()   │
│ - seed_from_ref() │
└────────┬──────────┘
         │
┌────────▼──────────────────────────────────────────────────────┐
│                   Supabase (PostgreSQL)                         │
│  - schedules table (with type="generated" for GA output)      │
│  - members table (availability, teaching_load fields)          │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Trigger**: Admin sends natural language command via CHE chat → `che_service.py` parses intent → emits `generate_full_schedule` JSON action → frontend calls `/api/schedule/generate-full`
2. **Load**: Backend fetches reference semester from `schedules` table, faculty data from `members` table
3. **Compute**: `scheduler_service.run_full_ga()` executes locally (CPU-only, no network)
4. **Repair**: If best chromosome has violations, `repair_pass()` applies targeted local search
5. **Persist**: Results saved to `schedules` table with `type="generated"`, response sent to frontend
6. **Display**: Frontend refreshes timetable grid with new data

## Detailed Design

### 1. Enhanced Data Models

#### Input Configuration (passed to `run_full_ga`)

```python
@dataclass
class FullGAConfig:
    reference_semester: Optional[str]    # e.g. "2nd"
    reference_school_year: Optional[str] # e.g. "2025-2026"
    subjects: List[SubjectInput]         # all subject-section combos
    rooms: List[str]                     # available room names
    faculty_overrides: Dict[str, Any]    # per-faculty modifications
    teaching_loads: Dict[str, int]       # faculty_name -> max units
    subject_allocations: Dict[str, List[str]]  # subj_code -> [faculty names]
    pop_size: int = 100
    max_generations: int = 500
    time_limit_seconds: float = 10.0

@dataclass
class SubjectInput:
    code: str
    name: str
    section: str
    units: int
    weekly_hours: float
    allocated_professors: List[str]
```

#### Enhanced Gene (backward-compatible)

The existing `Gene` class is preserved. New fields added via `__slots__` extension:

```python
class Gene:
    __slots__ = ('subj_code', 'subj_name', 'professor', 'room',
                 'section', 'units', 'day', 'start_slot', 'duration',
                 'year_level', 'type')
```

### 2. Reference Semester Seeding

```python
def seed_from_reference(reference_schedules: List[Dict], 
                        overrides: Dict[str, Any],
                        pop_size: int) -> List[List[Gene]]:
    """
    Convert reference semester data into seed chromosomes.
    At least 20% of initial population comes from reference.
    Remaining 80% are random variations of the reference.
    """
```

**Strategy:**
- Parse reference `schedules` rows into Gene objects
- Apply overrides (changed availability, new professors)
- Create seed_count = max(pop_size * 0.2, 1) direct copies
- Fill remaining population with mutated variants of reference

### 3. Enhanced Fitness Function (v2)

The fitness function is extended with new hard and soft constraints:

```python
HARD_PENALTY = 1000
SOFT_PENALTY = 10

def fitness_v2(chromosome: List[Gene],
               prof_availability: Dict[str, List[str]],
               teaching_loads: Dict[str, int],
               subject_allocations: Dict[str, List[str]]) -> float:
```

**Hard Constraints (penalty = 1000 each):**
- H1: Professor time conflict (existing)
- H2: Room time conflict (existing)
- H3: Section time conflict (existing)
- H4: Block exceeds MAX_BLOCK_SLOTS (existing)
- H5: Professor scheduled outside Availability days
- H6: Professor exceeds Teaching_Load limit
- H7: Professor not in subject's allocation list

**Soft Constraints (penalty = 10 each):**
- S1: All sessions of a subject on the same day (existing, weight x2)
- S2: Professor has 4+ consecutive hours without break
- S3: Class scheduled outside core hours (7:00-17:00)
- S4: Large gaps (>2 hours) between section classes on same day
- S5: Uneven weekly spread (standard deviation of daily hours)

### 4. GA Operators (Enhanced)

```python
def mutate_v2(chromosome: List[Gene], rooms: List[str], 
              prof_availability: Dict, rate: float = 0.15) -> List[Gene]:
    """Availability-aware mutation: only mutate to valid days for the professor."""

def crossover_v2(p1: List[Gene], p2: List[Gene]) -> List[Gene]:
    """Section-aware crossover: keep all genes of a section together."""

def tournament_select(population, scores, k=4):
    """Tournament selection with size 4 for better selection pressure."""
```

### 5. Repair Pass

```python
def repair_pass(chromosome: List[Gene],
                prof_availability: Dict[str, List[str]],
                rooms: List[str],
                max_iterations: int = 200) -> List[Gene]:
    """
    Local search to fix remaining hard constraint violations.
    For each gene causing a violation:
      1. Try moving to a different time slot on the same day
      2. Try moving to a different day within professor's availability
      3. Try swapping rooms with a non-conflicting entry
    Returns improved chromosome (may still have violations if truly unsolvable).
    """
```

### 6. Main Entry Point

```python
def run_full_ga(config: FullGAConfig,
                prof_availability: Dict[str, List[str]]) -> Dict:
    """
    Full schedule generation entry point.
    
    Returns:
        {
            "schedules": List[Dict],       # generated schedule entries
            "fitness_score": float,        # best chromosome score
            "generations_run": int,        # actual generations executed
            "conflicts_remaining": int,    # hard violations left (0 = perfect)
            "faculty_loads": Dict[str, int], # faculty -> assigned units
            "warnings": List[str],         # any issues/flags
            "elapsed_seconds": float       # wall-clock time
        }
    """
```

**Execution flow:**
1. Validate inputs (subjects, rooms, faculty data)
2. If reference semester specified, call `seed_from_reference()`
3. Fill remaining population with random chromosomes
4. Run GA loop with `fitness_v2`, `mutate_v2`, `crossover_v2`
5. Track time; abort if `time_limit_seconds` exceeded
6. Early exit if fitness reaches 0
7. Apply `repair_pass()` if best chromosome has hard violations
8. Return results dictionary

### 7. Flask API Endpoint

```python
@app.route('/api/schedule/generate-full', methods=['POST'])
def api_generate_full_schedule():
    """
    Request body:
    {
        "reference_semester": "2nd",
        "reference_school_year": "2025-2026",
        "target_semester": "1st",
        "target_school_year": "2026-2027",
        "faculty_overrides": {...},
        "rooms": [...],
        "confirm_overwrite": false
    }
    
    Response:
    {
        "success": true,
        "data": { ...run_full_ga results... },
        "message": "Generated 87 schedule entries in 3.2s with 0 conflicts"
    }
    """
```

### 8. CHE AI Assistant Action Block

New action type added to `che_service.py` system prompt:

```json
{
  "action": "generate_full_schedule",
  "params": {
    "reference_semester": "2nd",
    "reference_school_year": "2025-2026",
    "target_semester": "1st",
    "target_school_year": "2026-2027",
    "faculty_overrides": {
      "Prof. A": {"availability": ["Monday", "Wednesday", "Friday"]},
      "Prof. B": {"teaching_load": 12}
    },
    "rooms": []
  },
  "confirm": true
}
```

### 9. Database Schema Additions

No new tables required. Modifications to existing schema:

**`members` table** — add column (if not exists):
- `teaching_load` (integer, nullable, default 18)

**`schedules` table** — existing `type` column used:
- Value `"generated"` marks GA-produced entries

### 10. Frontend Integration

The existing `schedule.html` chat panel already handles action blocks. New handler for `generate_full_schedule`:

```javascript
// In the action block handler
case 'generate_full_schedule':
    const response = await fetch('/api/schedule/generate-full', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(action.params)
    });
    // Show confirmation modal before overwrite
    // On confirm: save and refresh timetable
```

## Correctness Properties

### Property 1: Availability Hard Constraint
**Criteria:** 2.2, 2.3 — Faculty never scheduled outside availability
**Type:** Invariant
**Property:** For all genes in a chromosome where the professor has defined availability, if `gene.day` is not in the professor's availability list, then `fitness_v2(chromosome) >= HARD_PENALTY`

### Property 2: Teaching Load Hard Constraint
**Criteria:** 3.2 — Exceeding load applies penalty
**Type:** Invariant
**Property:** For any chromosome where sum of units for a professor exceeds their teaching load, `fitness_v2(chromosome) >= HARD_PENALTY`

### Property 3: Subject-Faculty Allocation Constraint
**Criteria:** 4.2 — Only allocated faculty teach a subject
**Type:** Invariant
**Property:** For any chromosome produced by `run_full_ga`, every gene's professor is in that subject's `allocated_professors` list (or the subject has no allocation defined)

### Property 4: Room Conflict Detection
**Criteria:** 5.1, 7.2 — Same room overlapping times detected
**Type:** Invariant
**Property:** For any two genes sharing the same room and day with overlapping time ranges, `fitness_v2(chromosome)` includes at least one `HARD_PENALTY` per overlapping slot

### Property 5: Conflict-Free Output (Post-Repair)
**Criteria:** 7.4 — Repair pass reduces or eliminates violations
**Type:** Metamorphic
**Property:** `fitness_v2(repair_pass(chromosome)) <= fitness_v2(chromosome)` — repair never makes things worse

### Property 6: Reference Seeding Population Ratio
**Criteria:** 1.4 — At least 20% from reference
**Type:** Invariant
**Property:** Given non-empty reference data, `len(seed_chromosomes) >= pop_size * 0.2`

### Property 7: Section Coverage Completeness
**Criteria:** 11.1 — All subject-section combos in output
**Type:** Round-trip
**Property:** For any input with N subject-section pairs, the output contains at least one schedule entry for each pair. `set(input_pairs) ⊆ set(output_pairs)`

### Property 8: Early Termination
**Criteria:** 8.3 — Stop on zero-penalty chromosome
**Type:** Idempotence
**Property:** If a chromosome with fitness 0 exists in the population at generation G, the GA terminates at or before generation G (generations_run <= G)

### Property 9: Block Spread Penalty
**Criteria:** 6.1, 6.2 — Same-day clustering penalized
**Type:** Metamorphic
**Property:** A chromosome with all sessions of a multi-session subject on the same day has strictly higher fitness score than one with sessions spread across different days (all else equal)

### Property 10: Type Field Consistency
**Criteria:** 10.2 — All generated entries have type="generated"
**Type:** Invariant
**Property:** For all schedule entries produced by `run_full_ga`, the `type` field equals `"generated"`

## File Structure

```
services/
  scheduler_service.py    # Enhanced with run_full_ga, fitness_v2, repair_pass, seed_from_reference
  che_service.py          # Updated system prompt with generate_full_schedule action
app.py                    # New endpoint: POST /api/schedule/generate-full
templates/
  partials/schedule.html  # Updated action handler for generate_full_schedule
static/js/
  schedule_partial.js     # (backup, no changes needed - main logic in schedule.html)
```

## Performance Strategy

- **Population size**: 100 (up from 80) for better diversity
- **Generations**: 500 max (up from 300) but with time limit
- **Time limit**: 10 second hard wall-clock cutoff
- **Elitism**: Top 2 chromosomes survive each generation
- **Adaptive mutation**: Rate starts at 0.20, drops to 0.08 as fitness improves
- **Early exit**: Terminate immediately on fitness = 0
- **Repair pass**: Only runs if best chromosome has hard violations (avoids unnecessary work)

Expected runtime for typical CHE load (~15-20 faculty, ~60-80 sections): 2-5 seconds.
