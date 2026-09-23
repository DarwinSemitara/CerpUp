# Genetic Algorithm Schedule Generation: Technical Documentation

## Table of Contents
1. [Overview](#overview)
2. [How the Genetic Algorithm Works](#how-the-genetic-algorithm-works)
3. [Fitness Computation](#fitness-computation)
4. [Why the GA Fails Sometimes](#why-the-ga-fails-sometimes)
5. [Configuration & Tuning](#configuration--tuning)
6. [Troubleshooting Common Failures](#troubleshooting-common-failures)

---

## Overview

The CERP 2.0 schedule generation system uses a **Genetic Algorithm (GA)** - an evolutionary computation technique inspired by natural selection - to automatically create class schedules. The GA treats schedule generation as an optimization problem where it "evolves" better schedules over many generations.

**Key Files:**
- `services/scheduler_service.py` - Complete GA implementation (2900+ lines)
- `app.py` - API endpoints and integration with frontend

**Main Entry Point:** `run_full_ga_v3()` function

---

## How the Genetic Algorithm Works

### 1. **Core Concepts**

#### **Gene** (Scheduling Block)
A "Gene" represents a single class session with these properties:
```python
class Gene:
    subj_code       # Course code (e.g., "CERP 122")
    subj_name       # Course name
    professor       # Assigned faculty member
    room            # Classroom location
    section         # Section identifier (e.g., "G")
    units           # Credit units (typically 3)
    day             # Day of week (Monday-Saturday)
    start_slot      # Time slot (0 = 7:00 AM, each slot = 30 min)
    duration        # Length in slots (3 slots = 1.5 hours)
```

#### **Chromosome** (Complete Schedule)
A "chromosome" is a **list of genes** representing a complete schedule for all faculty and sections for the entire semester.

Example: If you have 50 courses with 3 hours each split into 1.5-hour blocks, you'd have ~100 genes per chromosome.

#### **Population**
A collection of chromosomes (candidate schedules). Default size: **100 chromosomes**.

#### **Fitness Score**
A numerical measure of schedule quality. **Lower = Better**.
- Score of **0** = Perfect schedule (no violations)
- Score of **5000** = Poor schedule (many conflicts)

---

### 2. **GA Algorithm Flow**

```
START
  ↓
1. INITIALIZATION (Generation 0)
  ├─ Create initial population of random schedules
  ├─ If reference semester exists: seed 50% from previous schedule
  └─ Fill rest with random valid combinations
  ↓
2. EVALUATION
  ├─ Calculate fitness score for each chromosome
  ├─ Count hard constraint violations (conflicts)
  └─ Count soft constraint violations (preferences)
  ↓
3. SELECTION (Tournament Selection)
  ├─ Pick 4 random chromosomes
  ├─ Choose the best one (lowest fitness)
  └─ Repeat to select parents for breeding
  ↓
4. CROSSOVER (Breeding)
  ├─ Take two parent schedules
  ├─ Combine them using uniform crossover
  │   • Each gene has 50% chance from parent A or B
  └─ Create offspring (child schedule)
  ↓
5. MUTATION (Random Changes)
  ├─ For each gene in offspring (15% probability):
  │   ├─ Change day (respecting faculty availability)
  │   ├─ Change time slot (random valid slot)
  │   └─ Occasionally change room (30% probability)
  ├─ CRITICAL: For 1.5-hour blocks, maintain MW/WF/TTH pairing
  └─ Result: slightly modified schedule
  ↓
6. REPAIR (Conflict Resolution)
  ├─ Identify genes with hard violations
  ├─ Try up to 100 re-slotting attempts
  │   • Find valid (day, time, room) combinations
  │   • Check if conflicts are resolved
  └─ Keep best version
  ↓
7. ELITISM (Preserve Best)
  ├─ Keep top 2-3 chromosomes unchanged
  └─ Ensures we never lose good solutions
  ↓
8. NEXT GENERATION
  ├─ Replace old population with new offspring
  └─ Repeat from step 2
  ↓
9. TERMINATION (Stop Conditions)
  ├─ Perfect solution found (fitness = 0)
  ├─ Max generations reached (default: 1000)
  ├─ Time limit exceeded (default: 120 seconds)
  └─ Plateau detected (no improvement for 50 generations)
  ↓
END: Return best schedule found
```

---

### 3. **Detailed GA Operations**

#### **A. Tournament Selection** (`tournament_select_v3`)
- Randomly picks **4 chromosomes** from population
- Compares their fitness scores
- Returns the **best one** (lowest score)
- **Why?** Balances exploration vs exploitation better than pure random selection

#### **B. Uniform Crossover** (`crossover_uniform`)
For each gene position:
```
Parent A: [GeneA1, GeneA2, GeneA3, GeneA4, ...]
Parent B: [GeneB1, GeneB2, GeneB3, GeneB4, ...]

Child:    [GeneA1, GeneB2, GeneA3, GeneA4, ...] (50/50 choice each)
```
**Why uniform over one-point?** Timetabling problems don't have gene locality - swapping random genes works better than cutting at a single point.

#### **C. Mutation** (`mutate_v3`)
For each gene (15% probability):
1. **Day mutation:**
   - Get faculty availability days (e.g., M/W/F only)
   - **For 1.5-hour blocks:** MUST pick from paired days (MW, WF, or TTH)
   - Otherwise: pick any available day
   
2. **Time mutation:**
   - Pick random valid start slot (ensuring class doesn't run past 5 PM)
   
3. **Room mutation (30% chance):**
   - Try to match room type (lecture vs lab)
   - Otherwise pick random available room

**Adaptive Mutation Rate:**
- Starts at **20%** (high exploration early)
- Decreases to **8%** (fine-tuning later)
- Formula: `rate = 0.20 - (0.20 - 0.08) * (generation / max_generations)`

#### **D. Repair Mechanism** (`repair_chromosome`)
After crossover, children often inherit incompatible genes:
- **Example:** Parent A assigned Prof. Smith to Monday 8 AM
            Parent B assigned Prof. Smith to Monday 9 AM
            → Child might get BOTH → conflict!

**Repair process:**
1. Check all genes for hard violations
2. Pick first violated gene
3. Try 20 random (day, time, room) combinations
4. If valid slot found → apply fix
5. Repeat for up to 100 iterations
6. Return best-effort repaired chromosome

---

## Fitness Computation

### **Two-Tier Scoring System**

#### **Tier 1: Hard Constraints** (Penalty: 1000 per violation)
These **MUST** be satisfied for a valid schedule:

| Constraint | Description | Penalty |
|------------|-------------|---------|
| **H1: Faculty Time Conflict** | Professor teaches 2+ classes simultaneously | 1000 per overlapping slot |
| **H2: Room Time Conflict** | Room hosts 2+ classes simultaneously | 1000 per overlapping slot |
| **H3: Section Time Conflict** | Section attends 2+ classes simultaneously | 1000 per overlapping slot |
| **H4: Faculty Qualification** | Faculty not assigned to teach this course-section | 1000 |
| **H5: Room Type Mismatch** | Lab course in lecture room (or vice versa) | 1000 |
| **H6: Room Capacity** | Room too small for section size | 1000 |
| **H7: Faculty Availability** | Class on day faculty is unavailable | 1000 |
| **H8: Operating Hours** | Class outside 7 AM - 5 PM window | 1000 |
| **H9: Block Too Long** | Single class session exceeds 3 hours | 1000 per excess slot |
| **H10: Course-Section Uniqueness** | Course-section taught by multiple faculty OR exceeds 3 units total | 1000 per violation |

**Example Calculation:**
```
Professor "Dr. Smith" scheduled Monday 8:00-9:30 (2 slots)
AND Monday 9:00-10:30 (2 slots)
→ Overlap: 2 slots (9:00-9:30)
→ Penalty: 1000 × 2 = 2000 points
```

#### **Tier 2: Soft Constraints** (Penalty: 10-100 per violation)
These are **preferences** - violating them doesn't invalidate the schedule but reduces quality:

| Constraint | Description | Penalty |
|------------|-------------|---------|
| **S1: Minimum Load** | Faculty below 12-unit minimum | 100 per unit short |
| **S2: Maximum Load** | Faculty exceeds teaching load limit | 1000 per unit over |
| **S3: Load Balance** | Faculty load unevenly distributed across days | 10 × variance |
| **S4: Continuity Bonus** | Same faculty teaching same course as last semester | -5 (bonus!) |
| **S5: Consecutive Hours** | Faculty teaching >4 hours without break | 10 per excess slot |
| **S6: Section Gaps** | Section has >2 hour gap between classes same day | 10 per occurrence |
| **S7: Same Day Concentration** | All sessions of a course on single day | 20 |
| **S8: Part-Time Campus Days** | Part-time faculty on campus >3 days/week | 20 per excess day |
| **S9: Time Preferences** | Faculty scheduled during non-preferred times | 10 per violation |

**Total Fitness Formula:**
```
Total Score = (Sum of Hard Penalties) + (Sum of Soft Penalties)

Lower score = Better schedule
Target: 0 (perfect schedule)
```

---

### **Fitness Function** (`fitness_v3`)

```python
def fitness_v3(chromosome, config):
    hard_violations = []
    soft_violations = []
    
    # Check all hard constraints for each gene
    for gene_idx in range(len(chromosome)):
        violations = check_all_hard_constraints(chromosome, gene_idx, config)
        hard_violations.extend(violations)
    
    # Calculate penalties
    hard_penalty = sum(v.penalty for v in hard_violations)
    
    # Score soft constraints (chromosome-level)
    soft_penalty, soft_viols = score_all_soft_constraints(chromosome, config)
    soft_violations.extend(soft_viols)
    
    total_score = hard_penalty + soft_penalty
    is_feasible = (len(hard_violations) == 0)
    
    return FitnessBreakdown(
        total_score=total_score,
        hard_penalty=hard_penalty,
        soft_penalty=soft_penalty,
        hard_violations=hard_violations,
        soft_violations=soft_violations,
        is_feasible=is_feasible
    )
```

---

## Why the GA Fails Sometimes

### **Failure Mode 1: Cannot Find Feasible Solution** ⚠️

**Symptom:** GA runs for max generations/time but best schedule still has hard constraint violations.

**Root Causes:**

#### 1. **Insufficient Resources (Most Common)**
```
Example:
- 10 courses requiring lab rooms
- Only 2 lab rooms available
- Each course needs 3 hours/week across M-F (5 days × 10 hours/day = 50 room-hours)
- Total lab room capacity: 2 rooms × 50 hours = 100 room-hours
- Required: 10 courses × 3 hours = 30 hours
- BUT: Factoring in faculty availability, room conflicts, etc. → Not enough flexibility
```

**Detection in Code:** `validate_schedule_config()` checks:
```python
total_room_hours = len(rooms) * 20_slots * 5_days / 2.0  # Total available
total_required_hours = sum(s.weekly_hours for s in subjects)

if total_room_hours < total_required_hours:
    ERROR: "Insufficient room capacity"
```

#### 2. **Over-Constrained Faculty Availability**
```
Example:
- Professor A only available Monday/Wednesday
- Professor B only available Tuesday/Thursday  
- Course X assigned to both A and B (but only one should teach it)
- Course Y (3 hours) needs MW or WF pairing
- BUT: Professor teaching it only available on Monday
- → IMPOSSIBLE to schedule Course Y correctly
```

**Code Check:** `check_faculty_availability()`
```python
avail = prof_availability.get(professor, [])
if avail and gene.day not in avail:
    return Hard Violation (penalty: 1000)
```

#### 3. **Conflicting Course-Section Assignments**
```
Example:
- CERP 122 Section G assigned to Prof. Smith
- CERP 122 Section G ALSO assigned to Prof. Jones  
- Constraint H10: One course-section = ONE faculty only
- GA can't resolve this — it's a data configuration error
```

**Code Check:** `check_course_section_uniqueness()`

#### 4. **Paired Block Issues (1.5-Hour Classes)**
```
Example:
- Course requires 1.5 hours × 2 = 3 hours/week
- System expects MW or WF or TTH pairing
- Professor only available Monday and Friday (not a valid pair!)
- → Can't properly schedule as paired blocks
```

**Why This Matters:** The UI expects 1.5-hour blocks to come in MW/WF/TTH pairs for visual grouping. If faculty availability breaks this pattern, the GA struggles.

---

### **Failure Mode 2: Detects Conflicts Multiple Times** 🔄

**Symptom:** GA keeps finding violations in the same spots generation after generation, making no progress.

**Root Causes:**

#### 1. **Local Optima Trap**
The population converges to a "good but not perfect" solution and can't escape:
```
Generation 100: Best fitness = 2000 (2 faculty conflicts)
Generation 200: Best fitness = 2000 (still 2 conflicts)
Generation 300: Best fitness = 2000 (same conflicts!)
...
Generation 500: Plateau detection triggered → STOP
```

**Why?** 
- Crossover keeps mixing the same flawed patterns
- Mutation rate too low to explore radically different arrangements
- Elitism preserves the "locally good" but globally flawed schedule

**Code Detection:** Plateau mechanism
```python
if generation - last_improvement_gen >= plateau_generations:
    termination_reason = "Plateau detected - no improvement for 50 generations"
    STOP
```

#### 2. **Repair Mechanism Insufficient**
```python
def repair_chromosome(chromosome, config, max_attempts=100):
    attempts = 0
    while attempts < max_attempts:
        violations_found = find_hard_violations(chromosome)
        if not violations_found:
            break  # Success!
        
        # Try to fix first violation
        gene_idx = violations_found[0]
        found_valid = False
        for _ in range(20):  # Try 20 random slots
            new_slot = random_valid_slot()
            if no_conflicts(new_slot):
                apply_fix(gene_idx, new_slot)
                found_valid = True
                break
        
        if not found_valid:
            pass  # Couldn't fix this gene, move on
        
        attempts += 1
    
    return chromosome  # Best effort result
```

**Problem:** 
- Fixing one conflict might CREATE a new conflict elsewhere
- With only 100 attempts × 20 retries = 2000 total tries, might not explore all possibilities
- For highly constrained schedules, this isn't enough

#### 3. **Crossover Introducing Conflicts**
```
Parent A (valid):
  Gene 1: Prof. Smith, Monday 8:00-9:30, Room 101
  Gene 2: Prof. Jones, Monday 8:00-9:30, Room 102

Parent B (valid):
  Gene 1: Prof. Smith, Monday 10:00-11:30, Room 103  
  Gene 2: Prof. Jones, Tuesday 8:00-9:30, Room 104

Child (INVALID after uniform crossover):
  Gene 1: Prof. Smith, Monday 8:00-9:30, Room 101  (from A)
  Gene 2: Prof. Jones, Tuesday 8:00-9:30, Room 104 (from B)
  Gene 3: Prof. Smith, Monday 10:00-11:30, Room 103 (from B)
  → Prof. Smith now on Monday 8:00-9:30 AND Monday 10:00-11:30 from separate genes!
```

**Why This Happens:** Uniform crossover doesn't understand the RELATIONSHIPS between genes. It treats each gene independently.

**Mitigation:** Repair pass after crossover, but repair has limits.

---

### **Failure Mode 3: Configuration Errors** ❌

**Symptom:** GA fails immediately or produces nonsensical results.

**Root Causes:**

#### 1. **Missing Qualified Faculty**
```python
# subjects.json
{
  "code": "CERP 150",
  "section": "A",
  "allocated_professors": []  # ← EMPTY!
}
```
**Result:** `validate_schedule_config()` returns error:
```
"Subject CERP 150 section A: No qualified faculty assigned"
```

#### 2. **Invalid Time Constraints**
```python
# Faculty availability
prof_availability = {
    "Dr. Smith": []  # ← No days available!
}
```
**Result:** Can't schedule any classes for Dr. Smith.

#### 3. **Conflicting Weekly Hours**
```python
{
  "code": "CERP 101",
  "units": 3,
  "weekly_hours": 10.0  # ← 10 hours for a 3-unit course?!
}
```
**Result:** `validate_schedule_config()` warns:
```
"Subject CERP 101: 10.0 hours/week is high. Verify this is correct."
```

---

### **Failure Mode 4: Termination Before Finding Solution** ⏱️

**Symptom:** GA stops early before exploring enough possibilities.

**Root Causes:**

#### 1. **Time Limit Too Aggressive**
```python
config.time_limit_seconds = 60.0  # Only 1 minute!
config.pop_size = 100
config.max_generations = 1000

# But with fitness evaluation, the GA can only run ~200 generations in 60s
# Not enough for complex schedules
```

**Fix:** Use "quality" preset:
```python
config.time_limit_seconds = 300.0  # 5 minutes
config.max_generations = 2000
config.pop_size = 150
```

#### 2. **Plateau Detection Too Sensitive**
```python
config.plateau_generations = 20  # Stop if no improvement for 20 generations
```
**Problem:** For complex schedules, it might take 100+ generations to escape local optima.

**Fix:**
```python
config.plateau_generations = 100
```

#### 3. **Population Too Small**
```python
config.pop_size = 30  # Very small!
```
**Problem:** Limited diversity → quick convergence to mediocre solution → plateau

**Fix:**
```python
config.pop_size = 100  # or more
```

---

## Configuration & Tuning

### **GA Configuration Presets**

#### **1. Default (Balanced)**
```python
config = create_default_ga_config()
# pop_size = 100
# max_generations = 1000
# time_limit_seconds = 120.0
# mutation_rate = 0.15
# crossover_rate = 0.8
# plateau_generations = 50
```
**Use for:** Standard schedules with moderate complexity.

#### **2. Fast (Quick Results)**
```python
config = create_fast_ga_config()
# pop_size = 50
# max_generations = 300
# time_limit_seconds = 60.0
# plateau_generations = 30
```
**Use for:** Testing, demos, or when speed matters more than quality.

#### **3. Quality (Best Solutions)**
```python
config = create_quality_ga_config()
# pop_size = 150
# max_generations = 2000
# time_limit_seconds = 300.0
# plateau_generations = 100
# elitism_count = 5
# tournament_size = 5
```
**Use for:** Production schedules, complex constraints, or when quality is critical.

---

### **Key Parameters Explained**

| Parameter | Effect | Tuning Guidance |
|-----------|--------|-----------------|
| `pop_size` | Larger = more diversity, slower | 50-150; increase if stuck in local optima |
| `max_generations` | More = better exploration, longer runtime | 500-2000; increase for complex schedules |
| `time_limit_seconds` | Hard stop regardless of progress | 60-300s; increase if hitting time limit |
| `mutation_rate` | Higher = more exploration, less stability | 0.10-0.20; increase if plateau early |
| `crossover_rate` | Probability of breeding vs cloning | 0.7-0.9; usually keep ~0.8 |
| `elitism_count` | Preserve top N solutions | 2-5; too many = less diversity |
| `tournament_size` | Selection pressure | 3-5; larger = faster convergence |
| `plateau_generations` | Stop if no improvement for N gens | 30-100; increase for complex problems |

---

### **Constraint Weight Tuning**

```python
# Hard constraints (MUST be much larger than soft)
config.weight_hard_violations = 1000.0
config.weight_faculty_conflicts = 1000.0
config.weight_room_conflicts = 1000.0
config.weight_section_conflicts = 1000.0
config.weight_max_load_violation = 1000.0

# Soft constraints (preferences)
config.weight_min_load_violation = 100.0  # Less critical than max
config.weight_continuity_bonus = 5.0      # Small reward
config.weight_load_balance = 10.0         # Moderate penalty
config.weight_gap_penalty = 10.0          # Moderate penalty
```

**Rule of Thumb:** Hard constraint weights should be **100x** larger than soft constraints to ensure feasibility is prioritized over preferences.

---

## Troubleshooting Common Failures

### **Problem:** "No feasible solution found after 1000 generations"

**Diagnosis Steps:**

1. **Check validation report:**
```python
validation = validate_schedule_config(config)
if not validation['valid']:
    print(validation['errors'])  # Show critical issues
```

2. **Check room capacity:**
```
Total room-hours needed: (sum of all weekly_hours)
Total room-hours available: (num_rooms × 50 hours/week)
If needed > 80% of available → Add more rooms
```

3. **Check faculty availability:**
```python
for subject in subjects:
    profs = subject.allocated_professors
    for prof in profs:
        avail_days = prof_availability.get(prof, [])
        if len(avail_days) < 2:
            print(f"WARNING: {prof} only available {len(avail_days)} days")
```

4. **Check for over-assignment:**
```python
faculty_units = {}
for subject in subjects:
    for prof in subject.allocated_professors:
        faculty_units[prof] = faculty_units.get(prof, 0) + subject.units

for prof, units in faculty_units.items():
    max_load = teaching_loads.get(prof, 18)
    if units > max_load:
        print(f"ERROR: {prof} assigned {units} units (max: {max_load})")
```

**Solutions:**
- Add more rooms (especially labs if needed)
- Expand faculty availability (add more days)
- Reduce faculty overload (redistribute courses)
- Use "quality" preset (more time to find solution)

---

### **Problem:** "GA stuck at fitness score 2000+ for many generations"

**Diagnosis:**
```python
# Check plateau status
if termination_reason == "Plateau detected":
    print("GA converged to local optimum")
```

**Solutions:**

1. **Increase mutation rate:**
```python
config.mutation_rate = 0.25  # More exploration
```

2. **Increase population diversity:**
```python
config.pop_size = 150
```

3. **Disable plateau detection temporarily:**
```python
config.enable_plateau_detection = False
config.max_generations = 2000  # Let it run longer
```

4. **Use targeted mutation:**
```python
# In mutate_v3, the 'targeted' parameter prioritizes mutating violated genes
# This is already enabled in run_full_ga_v3 when hard_penalty > 0
```

5. **Check for impossible constraints:**
```python
# Review violation report
violation_report = result['violation_report']
for detail in violation_report['details']:
    if detail['severity'] == 'hard':
        print(f"{detail['constraint']}: {detail['count']} violations")
        print(f"Sample: {detail['sample_message']}")
```

---

### **Problem:** "Paired blocks not moving together / UI shows unpaired 1.5-hour blocks"

**Root Cause:** Professor availability doesn't align with MW/WF/TTH pairing requirements.

**Diagnosis:**
```python
# Check faculty availability for paired day patterns
for prof, days in prof_availability.items():
    has_valid_pair = False
    for day1, day2 in [('Monday', 'Wednesday'), ('Wednesday', 'Friday'), ('Tuesday', 'Thursday')]:
        if day1 in days and day2 in days:
            has_valid_pair = True
            break
    if not has_valid_pair:
        print(f"WARNING: {prof} availability {days} doesn't support paired blocks")
```

**Solutions:**
1. Expand faculty availability to include paired days
2. Use 3-hour single blocks instead of 1.5-hour pairs
3. Add `pairedWith` column to database (as noted in previous fixes)

---

### **Problem:** "Time limit reached before finding solution"

**Solutions:**

1. **Increase time budget:**
```python
config.time_limit_seconds = 300.0  # 5 minutes
```

2. **Use greedy initialization:**
```python
# run_full_ga_v3 already includes Phase 2 greedy_feasible_schedule()
# This seeds population with a valid starting point
```

3. **Reduce problem size:**
- Schedule fewer subjects per run
- Split into multiple smaller scheduling runs
- Schedule by department or year level separately

---

### **Problem:** "Conflicts keep appearing in same faculty/room"

**Diagnosis:** Likely a bottleneck resource.

**Example:**
```
Dr. Smith teaches 7 courses (21 units)
Max load: 18 units
→ IMPOSSIBLE to schedule without violation
```

**Solutions:**
1. Redistribute courses among multiple faculty
2. Increase max teaching load (if acceptable)
3. Hire additional faculty for that subject area

---

### **Best Practices Summary**

✅ **DO:**
- Start with validation: `validate_schedule_config()` before running GA
- Use "quality" preset for production schedules
- Provide reference semester data (improves convergence by 30-40%)
- Ensure faculty availability includes paired days (MW, WF, or TTH)
- Monitor violation reports to identify systemic issues
- Allow 2-5 minutes runtime for complex schedules

❌ **DON'T:**
- Over-constrain faculty availability (minimum 2-3 days/week)
- Assign faculty beyond their max teaching load
- Use tiny populations (< 50) for complex problems
- Ignore validation warnings
- Expect instant results (GA needs time to explore)

---

## Summary

The GA works by:
1. **Creating** a population of random candidate schedules
2. **Evaluating** each based on constraint violations (fitness)
3. **Selecting** the best candidates as parents
4. **Combining** parents via crossover to create offspring
5. **Mutating** offspring to introduce variation
6. **Repairing** conflicts when possible
7. **Repeating** for many generations until a good solution emerges

**It fails when:**
- Resources are insufficient (not enough rooms, faculty overloaded)
- Constraints are contradictory (impossible requirements)
- Time/iteration budget is too small (stopped too early)
- Population converges to local optimum (needs more exploration)
- Configuration errors (missing data, invalid assignments)

**Success factors:**
- Adequate resources with 20%+ buffer
- Realistic constraints (not over-constrained)
- Sufficient time (2-5 minutes for complex schedules)
- Proper validation before running
- Reference semester data for seeding

---

**For developers:** See `services/scheduler_service.py` for full implementation details.

**For configuration:** Use preset configs (`create_default_ga_config()`, `create_fast_ga_config()`, `create_quality_ga_config()`) and tune parameters based on schedule complexity.
