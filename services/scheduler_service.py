"""
Genetic Algorithm – Class Schedule Generator
============================================
Advanced version with:
  - Full semester generation for all faculty/sections
  - Reference semester seeding
  - Faculty availability & teaching load enforcement
  - Subject-faculty allocation
  - Room conflict avoidance
  - Professional block spreading
  - Conflict detection + local-search repair
  - CHE AI integration
  - Smart single-block manipulation (add/move/delete)

All computation is local — zero external API calls, completes in seconds.
"""

import random
import copy
import time as _time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
SLOTS_PER_DAY = 20        # 30-min slots: 0=7:00 … 19=16:30
START_HOUR = 7             # 7:00 AM
MAX_BLOCK_SLOTS = 6        # 3 hours max per block
HARD_PENALTY = 1000
SOFT_PENALTY = 10
DEFAULT_TEACHING_LOAD = 18  # units

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def slot_to_time(slot: int) -> str:
    h = START_HOUR + slot // 2
    m = 30 if slot % 2 else 0
    return f"{h}:{m:02d}"


def time_to_slot(t: str) -> int:
    parts = str(t).split(':')
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    return (h - START_HOUR) * 2 + (1 if m >= 30 else 0)


def slots_for_duration(hours: float) -> int:
    return max(1, int(hours * 2))


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SubjectInput:
    code: str
    name: str
    section: str
    units: int
    weekly_hours: float
    allocated_professors: List[str] = field(default_factory=list)


@dataclass
class FullGAConfig:
    subjects: List[SubjectInput] = field(default_factory=list)
    rooms: List[str] = field(default_factory=list)
    prof_availability: Dict[str, List[str]] = field(default_factory=dict)
    teaching_loads: Dict[str, int] = field(default_factory=dict)
    subject_allocations: Dict[str, List[str]] = field(default_factory=dict)
    reference_schedules: List[Dict] = field(default_factory=list)
    faculty_overrides: Dict[str, Any] = field(default_factory=dict)
    pop_size: int = 100
    max_generations: int = 500
    time_limit_seconds: float = 10.0


# ══════════════════════════════════════════════════════════════════════════════
# GENE & CHROMOSOME
# ══════════════════════════════════════════════════════════════════════════════

class Gene:
    __slots__ = ('subj_code', 'subj_name', 'professor', 'room',
                 'section', 'units', 'day', 'start_slot', 'duration')

    def __init__(self, subj_code, subj_name, professor, room,
                 section, units, day, start_slot, duration):
        self.subj_code = subj_code
        self.subj_name = subj_name
        self.professor = professor
        self.room = room
        self.section = section
        self.units = units
        self.day = day
        self.start_slot = start_slot
        self.duration = duration

    def end_slot(self):
        return self.start_slot + self.duration

    def to_dict(self):
        return {
            'subjCode': self.subj_code,
            'subjName': self.subj_name,
            'prof': self.professor,
            'room': self.room,
            'section': self.section,
            'units': self.units,
            'day': self.day,
            'start': slot_to_time(self.start_slot),
            'end': slot_to_time(self.end_slot()),
        }


def random_gene(subject: Dict, rooms: List[str],
                prof_availability: Dict[str, List[str]] = None) -> Gene:
    """Create a random gene, respecting professor availability if provided."""
    prof = subject['professor']
    avail_days = WEEKDAYS  # default

    if prof_availability and prof in prof_availability:
        avail = prof_availability[prof]
        if avail:
            avail_days = avail

    day = random.choice(avail_days)
    duration = min(subject['block_slots'], MAX_BLOCK_SLOTS)
    max_start = SLOTS_PER_DAY - duration
    start = random.randint(0, max(0, max_start))
    room = random.choice(rooms) if rooms else 'TBA'

    return Gene(
        subj_code=subject['code'],
        subj_name=subject['name'],
        professor=prof,
        room=room,
        section=subject['section'],
        units=subject['units'],
        day=day,
        start_slot=start,
        duration=duration,
    )


def build_chromosome(subjects: List[Dict], rooms: List[str],
                     prof_availability: Dict[str, List[str]] = None) -> List[Gene]:
    """Build one chromosome covering all subject-section blocks."""
    genes = []
    for subj in subjects:
        remaining = subj['weekly_slots']
        while remaining > 0:
            block = min(remaining, MAX_BLOCK_SLOTS)
            s = dict(subj)
            s['block_slots'] = block
            genes.append(random_gene(s, rooms, prof_availability))
            remaining -= block
    return genes


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCED FITNESS FUNCTION (v2)
# ══════════════════════════════════════════════════════════════════════════════

def fitness_v2(chromosome: List[Gene],
               prof_availability: Dict[str, List[str]],
               teaching_loads: Dict[str, int],
               subject_allocations: Dict[str, List[str]]) -> float:
    """
    Enhanced fitness: lower = better.
    Hard constraints (1000 penalty each violation slot):
      H1: Professor time conflict
      H2: Room time conflict
      H3: Section time conflict
      H4: Block too long (>3hrs)
      H5: Professor scheduled outside availability days
      H6: Professor exceeds teaching load
      H7: Professor not in subject allocation list
    Soft constraints (10 penalty each):
      S1: All sessions of subject on same day
      S2: Professor has 4+ consecutive hours no break
      S3: Class outside core hours (7:00-17:00)
      S4: Large gap (>2hrs) between section classes same day
      S5: Uneven weekly spread
    """
    score = 0

    # Occupancy maps
    prof_occ: Dict[str, set] = {}
    room_occ: Dict[str, set] = {}
    sect_occ: Dict[str, set] = {}
    subj_days: Dict[str, set] = {}
    prof_units: Dict[str, float] = {}
    # prof -> day -> [slots]
    prof_daily_slots: Dict[str, Dict[str, List[int]]] = {}
    # section -> day -> [slots]
    sect_daily_slots: Dict[str, Dict[str, List[int]]] = {}

    for g in chromosome:
        slots_used = [(g.day, g.start_slot + i) for i in range(g.duration)]

        # Track professor units
        if g.professor not in prof_units:
            prof_units[g.professor] = 0
        prof_units[g.professor] += g.units

        # Track professor daily slots for consecutive check
        if g.professor not in prof_daily_slots:
            prof_daily_slots[g.professor] = {}
        if g.day not in prof_daily_slots[g.professor]:
            prof_daily_slots[g.professor][g.day] = []
        prof_daily_slots[g.professor][g.day].extend(
            range(g.start_slot, g.end_slot()))

        # Track section daily slots for gap check
        if g.section not in sect_daily_slots:
            sect_daily_slots[g.section] = {}
        if g.day not in sect_daily_slots[g.section]:
            sect_daily_slots[g.section][g.day] = []
        sect_daily_slots[g.section][g.day].extend(
            range(g.start_slot, g.end_slot()))

        # H1 – professor conflict
        if g.professor not in prof_occ:
            prof_occ[g.professor] = set()
        for key in slots_used:
            if key in prof_occ[g.professor]:
                score += HARD_PENALTY
            prof_occ[g.professor].add(key)

        # H2 – room conflict
        if g.room and g.room != 'TBA':
            if g.room not in room_occ:
                room_occ[g.room] = set()
            for key in slots_used:
                if key in room_occ[g.room]:
                    score += HARD_PENALTY
                room_occ[g.room].add(key)

        # H3 – section conflict
        if g.section not in sect_occ:
            sect_occ[g.section] = set()
        for key in slots_used:
            if key in sect_occ[g.section]:
                score += HARD_PENALTY
            sect_occ[g.section].add(key)

        # H4 – block too long
        if g.duration > MAX_BLOCK_SLOTS:
            score += HARD_PENALTY * (g.duration - MAX_BLOCK_SLOTS)

        # H5 – professor outside availability
        avail = prof_availability.get(g.professor, [])
        if avail and g.day not in avail:
            score += HARD_PENALTY

        # H7 – professor not in subject allocation
        alloc = subject_allocations.get(g.subj_code, [])
        if alloc and g.professor not in alloc:
            score += HARD_PENALTY

        # S1 – track days per subject
        key_subj = f"{g.subj_code}_{g.section}"
        if key_subj not in subj_days:
            subj_days[key_subj] = set()
        subj_days[key_subj].add(g.day)

        # S3 – outside core hours (slot 20 = 17:00)
        if g.end_slot() > SLOTS_PER_DAY:
            score += SOFT_PENALTY

    # H6 – teaching load exceeded
    for prof, units in prof_units.items():
        max_load = teaching_loads.get(prof, DEFAULT_TEACHING_LOAD)
        if units > max_load:
            score += HARD_PENALTY * int(units - max_load)

    # S1 – all blocks on same day penalty
    for days_used in subj_days.values():
        if len(days_used) == 1:
            score += SOFT_PENALTY * 2

    # S2 – consecutive hours > 4 (8 slots)
    for prof, days in prof_daily_slots.items():
        for day, slots in days.items():
            if not slots:
                continue
            sorted_slots = sorted(set(slots))
            consecutive = 1
            for i in range(1, len(sorted_slots)):
                if sorted_slots[i] == sorted_slots[i-1] + 1:
                    consecutive += 1
                    if consecutive > 8:  # > 4 hours
                        score += SOFT_PENALTY
                else:
                    consecutive = 1

    # S4 – large gaps between section classes on same day
    for section, days in sect_daily_slots.items():
        for day, slots in days.items():
            if len(slots) < 2:
                continue
            sorted_slots = sorted(set(slots))
            max_gap = 0
            i = 0
            while i < len(sorted_slots) - 1:
                # Find end of current block
                j = i
                while j < len(sorted_slots) - 1 and sorted_slots[j+1] == sorted_slots[j] + 1:
                    j += 1
                # Gap to next block
                if j < len(sorted_slots) - 1:
                    gap = sorted_slots[j+1] - sorted_slots[j] - 1
                    if gap > max_gap:
                        max_gap = gap
                i = j + 1
            if max_gap > 4:  # > 2 hours gap
                score += SOFT_PENALTY

    return score


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCED GA OPERATORS
# ══════════════════════════════════════════════════════════════════════════════

def mutate_v2(chromosome: List[Gene], rooms: List[str],
              prof_availability: Dict[str, List[str]],
              rate: float = 0.15) -> List[Gene]:
    """Availability-aware mutation."""
    result = copy.deepcopy(chromosome)
    for g in result:
        if random.random() < rate:
            # Mutate day (respect availability)
            avail = prof_availability.get(g.professor, [])
            valid_days = avail if avail else WEEKDAYS
            g.day = random.choice(valid_days)
            # Mutate start time
            max_start = SLOTS_PER_DAY - g.duration
            g.start_slot = random.randint(0, max(0, max_start))
            # Occasionally mutate room
            if rooms and random.random() < 0.3:
                g.room = random.choice(rooms)
    return result


def crossover_v2(p1: List[Gene], p2: List[Gene]) -> List[Gene]:
    """Section-aware crossover: keep section genes together."""
    if len(p1) < 2:
        return copy.deepcopy(p1)

    # Group genes by section
    sections_p1: Dict[str, List[int]] = {}
    for i, g in enumerate(p1):
        if g.section not in sections_p1:
            sections_p1[g.section] = []
        sections_p1[g.section].append(i)

    # Pick random sections from p1, rest from p2
    all_sections = list(sections_p1.keys())
    if len(all_sections) < 2:
        point = random.randint(1, len(p1) - 1)
        return copy.deepcopy(p1[:point]) + copy.deepcopy(p2[point:])

    split = random.randint(1, len(all_sections) - 1)
    from_p1_sections = set(all_sections[:split])

    child = []
    for g in p1:
        if g.section in from_p1_sections:
            child.append(copy.deepcopy(g))
    for g in p2:
        if g.section not in from_p1_sections:
            child.append(copy.deepcopy(g))

    return child if child else copy.deepcopy(p1)


def tournament_select_v2(population, scores, k=4):
    """Tournament selection with size 4."""
    contestants = random.sample(
        list(zip(population, scores)), min(k, len(population)))
    return min(contestants, key=lambda x: x[1])[0]


# ══════════════════════════════════════════════════════════════════════════════
# REFERENCE SEMESTER SEEDING
# ══════════════════════════════════════════════════════════════════════════════

def seed_from_reference(reference_schedules: List[Dict],
                        subjects: List[Dict],
                        rooms: List[str],
                        prof_availability: Dict[str, List[str]],
                        overrides: Dict[str, Any],
                        pop_size: int) -> List[List[Gene]]:
    """
    Convert reference semester data into seed chromosomes.
    At least 20% from reference, rest are mutated variants.
    """
    if not reference_schedules:
        return []

    # Apply overrides to reference
    ref_data = apply_overrides(reference_schedules, overrides)

    # Convert reference to genes
    ref_genes = []
    for s in ref_data:
        try:
            start_slot = time_to_slot(s.get('start', '7:00'))
            end_slot = time_to_slot(s.get('end', '8:00'))
            duration = end_slot - start_slot
            if duration <= 0:
                continue
            ref_genes.append(Gene(
                subj_code=s.get('subjCode', s.get('subj_code', '')),
                subj_name=s.get('subjName', s.get('subj_name', '')),
                professor=s.get('prof', ''),
                room=s.get('room', 'TBA'),
                section=s.get('section', ''),
                units=int(s.get('units', 3)),
                day=s.get('day', 'Monday'),
                start_slot=start_slot,
                duration=duration,
            ))
        except (ValueError, IndexError):
            continue

    if not ref_genes:
        return []

    # Create seeded population
    seed_count = max(int(pop_size * 0.2), 1)
    population = []

    # Direct copies
    for _ in range(seed_count):
        population.append(copy.deepcopy(ref_genes))

    # Mutated variants of reference
    remaining = pop_size - seed_count
    for _ in range(remaining):
        variant = mutate_v2(ref_genes, rooms, prof_availability, rate=0.25)
        population.append(variant)

    return population


def apply_overrides(reference_data: List[Dict], overrides: Dict[str, Any]) -> List[Dict]:
    """Apply admin overrides to reference data (changed profs, availability, etc.)."""
    if not overrides:
        return reference_data

    result = []
    for entry in reference_data:
        e = dict(entry)
        prof = e.get('prof', '')

        # Check if this professor has overrides
        if prof in overrides:
            prof_override = overrides[prof]
            # Professor swap
            if 'new_professor' in prof_override:
                e['prof'] = prof_override['new_professor']
            # Remove entries for this professor if marked as removed
            if prof_override.get('removed', False):
                continue

        result.append(e)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# REPAIR PASS (Local Search)
# ══════════════════════════════════════════════════════════════════════════════

def repair_pass(chromosome: List[Gene],
                prof_availability: Dict[str, List[str]],
                rooms: List[str],
                teaching_loads: Dict[str, int],
                subject_allocations: Dict[str, List[str]],
                max_iterations: int = 200) -> List[Gene]:
    """
    Local search to fix remaining hard constraint violations.
    Strategies: move time, move day, swap room.
    """
    result = copy.deepcopy(chromosome)

    for iteration in range(max_iterations):
        # Find violations
        violations = _find_violations(
            result, prof_availability, teaching_loads, subject_allocations)
        if not violations:
            break

        # Pick a random violated gene
        gene_idx = random.choice(violations)
        g = result[gene_idx]

        # Strategy 1: Move to different time on same day
        fixed = _try_move_time(result, gene_idx)
        if fixed:
            continue

        # Strategy 2: Move to different day within availability
        fixed = _try_move_day(result, gene_idx, prof_availability)
        if fixed:
            continue

        # Strategy 3: Change room
        if rooms:
            fixed = _try_swap_room(result, gene_idx, rooms)

    return result


def _find_violations(chromosome: List[Gene],
                     prof_availability: Dict[str, List[str]],
                     teaching_loads: Dict[str, int],
                     subject_allocations: Dict[str, List[str]]) -> List[int]:
    """Return indices of genes causing hard constraint violations."""
    violations = set()
    prof_occ: Dict[str, set] = {}
    room_occ: Dict[str, set] = {}
    sect_occ: Dict[str, set] = {}

    for i, g in enumerate(chromosome):
        slots_used = [(g.day, g.start_slot + j) for j in range(g.duration)]

        # Professor conflict
        if g.professor not in prof_occ:
            prof_occ[g.professor] = set()
        for key in slots_used:
            if key in prof_occ[g.professor]:
                violations.add(i)
            prof_occ[g.professor].add(key)

        # Room conflict
        if g.room and g.room != 'TBA':
            if g.room not in room_occ:
                room_occ[g.room] = set()
            for key in slots_used:
                if key in room_occ[g.room]:
                    violations.add(i)
                room_occ[g.room].add(key)

        # Section conflict
        if g.section not in sect_occ:
            sect_occ[g.section] = set()
        for key in slots_used:
            if key in sect_occ[g.section]:
                violations.add(i)
            sect_occ[g.section].add(key)

        # Availability violation
        avail = prof_availability.get(g.professor, [])
        if avail and g.day not in avail:
            violations.add(i)

        # Allocation violation
        alloc = subject_allocations.get(g.subj_code, [])
        if alloc and g.professor not in alloc:
            violations.add(i)

    return list(violations)


def _try_move_time(chromosome: List[Gene], idx: int) -> bool:
    """Try moving gene to a different time slot on the same day."""
    g = chromosome[idx]
    occupied = set()
    for i, other in enumerate(chromosome):
        if i == idx:
            continue
        if other.day == g.day and other.professor == g.professor:
            for s in range(other.start_slot, other.end_slot()):
                occupied.add(s)
        if other.day == g.day and other.room == g.room and g.room != 'TBA':
            for s in range(other.start_slot, other.end_slot()):
                occupied.add(s)
        if other.day == g.day and other.section == g.section:
            for s in range(other.start_slot, other.end_slot()):
                occupied.add(s)

    # Try all possible start times
    for start in range(0, SLOTS_PER_DAY - g.duration + 1):
        conflict = False
        for s in range(start, start + g.duration):
            if s in occupied:
                conflict = True
                break
        if not conflict:
            g.start_slot = start
            return True
    return False


def _try_move_day(chromosome: List[Gene], idx: int,
                  prof_availability: Dict[str, List[str]]) -> bool:
    """Try moving gene to a different day within professor's availability."""
    g = chromosome[idx]
    avail = prof_availability.get(g.professor, [])
    valid_days = avail if avail else WEEKDAYS

    random.shuffle(valid_days)
    for day in valid_days:
        if day == g.day:
            continue
        # Check if this day works
        occupied = set()
        for i, other in enumerate(chromosome):
            if i == idx:
                continue
            if other.day == day and other.professor == g.professor:
                for s in range(other.start_slot, other.end_slot()):
                    occupied.add(s)
            if other.day == day and other.room == g.room and g.room != 'TBA':
                for s in range(other.start_slot, other.end_slot()):
                    occupied.add(s)
            if other.day == day and other.section == g.section:
                for s in range(other.start_slot, other.end_slot()):
                    occupied.add(s)

        for start in range(0, SLOTS_PER_DAY - g.duration + 1):
            conflict = False
            for s in range(start, start + g.duration):
                if s in occupied:
                    conflict = True
                    break
            if not conflict:
                g.day = day
                g.start_slot = start
                return True
    return False


def _try_swap_room(chromosome: List[Gene], idx: int, rooms: List[str]) -> bool:
    """Try assigning a different room to resolve room conflicts."""
    g = chromosome[idx]
    for room in rooms:
        if room == g.room:
            continue
        conflict = False
        for i, other in enumerate(chromosome):
            if i == idx:
                continue
            if other.day == g.day and other.room == room:
                for s in range(other.start_slot, other.end_slot()):
                    if g.start_slot <= s < g.end_slot():
                        conflict = True
                        break
            if conflict:
                break
        if not conflict:
            g.room = room
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# FULL SCHEDULE GENERATION (Main Entry Point)
# ══════════════════════════════════════════════════════════════════════════════

def run_full_ga(config: FullGAConfig) -> Dict:
    """
    Full semester schedule generation.

    Returns dict with:
      schedules, fitness_score, generations_run, conflicts_remaining,
      faculty_loads, warnings, elapsed_seconds
    """
    start_time = _time.time()
    warnings = []

    # Validate
    if not config.subjects:
        return {'success': False, 'message': 'No subjects provided.', 'schedules': [],
                'warnings': ['No subject data to generate from.']}

    # Prepare subject dicts for chromosome building
    subjects_for_ga = []
    for subj in config.subjects:
        prof_list = subj.allocated_professors or config.subject_allocations.get(
            subj.code, [])
        if not prof_list:
            warnings.append(
                f"{subj.code} has no allocated professor — skipping")
            continue

        # For each subject-section, assign the first available professor
        # GA mutation will explore alternatives from the allocation list
        professor = prof_list[0]

        weekly_slots = slots_for_duration(subj.weekly_hours)
        subjects_for_ga.append({
            'code': subj.code,
            'name': subj.name,
            'professor': professor,
            'section': subj.section,
            'units': subj.units,
            'weekly_slots': weekly_slots,
            'allocated_professors': prof_list,
        })

    if not subjects_for_ga:
        return {'success': False, 'message': 'No subjects with allocated professors.',
                'schedules': [], 'warnings': warnings}

    rooms = config.rooms if config.rooms else ['TBA']
    prof_availability = dict(config.prof_availability)
    teaching_loads = dict(config.teaching_loads)
    subject_allocations = dict(config.subject_allocations)

    # Apply faculty overrides
    for prof, override in config.faculty_overrides.items():
        if 'availability' in override:
            prof_availability[prof] = override['availability']
        if 'teaching_load' in override:
            teaching_loads[prof] = override['teaching_load']

    # Build initial population
    population = []

    # Seed from reference if available
    if config.reference_schedules:
        seeded = seed_from_reference(
            config.reference_schedules,
            subjects_for_ga,
            rooms,
            prof_availability,
            config.faculty_overrides,
            config.pop_size
        )
        population.extend(seeded)

    # Fill remaining with random chromosomes
    while len(population) < config.pop_size:
        population.append(build_chromosome(
            subjects_for_ga, rooms, prof_availability))

    # GA Loop
    best_chrom = None
    best_score = float('inf')
    generations_run = 0
    initial_mutation_rate = 0.20
    min_mutation_rate = 0.08

    for gen in range(config.max_generations):
        # Time check
        elapsed = _time.time() - start_time
        if elapsed > config.time_limit_seconds:
            warnings.append(
                f"Time limit reached ({config.time_limit_seconds}s) at generation {gen}")
            break

        generations_run = gen + 1

        # Evaluate fitness
        scores = [fitness_v2(c, prof_availability, teaching_loads, subject_allocations)
                  for c in population]

        # Track best
        gen_best_idx = min(range(len(scores)), key=lambda i: scores[i])
        if scores[gen_best_idx] < best_score:
            best_score = scores[gen_best_idx]
            best_chrom = copy.deepcopy(population[gen_best_idx])

        # Early exit on perfect solution
        if best_score == 0:
            break

        # Adaptive mutation rate
        progress = gen / max(config.max_generations, 1)
        mutation_rate = initial_mutation_rate - \
            (initial_mutation_rate - min_mutation_rate) * progress

        # Build next generation (elitism: top 2)
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i])
        next_gen = [copy.deepcopy(population[sorted_indices[0]]),
                    copy.deepcopy(population[sorted_indices[1]])]

        while len(next_gen) < config.pop_size:
            p1 = tournament_select_v2(population, scores)
            p2 = tournament_select_v2(population, scores)
            child = crossover_v2(p1, p2)
            child = mutate_v2(child, rooms, prof_availability,
                              rate=mutation_rate)
            next_gen.append(child)

        population = next_gen

    if best_chrom is None:
        best_chrom = population[0]

    # Repair pass if violations remain
    if best_score > 0:
        best_chrom = repair_pass(best_chrom, prof_availability, rooms,
                                 teaching_loads, subject_allocations)
        best_score = fitness_v2(
            best_chrom, prof_availability, teaching_loads, subject_allocations)

    # Count remaining hard conflicts
    conflicts_remaining = 0
    violations = _find_violations(
        best_chrom, prof_availability, teaching_loads, subject_allocations)
    conflicts_remaining = len(violations)

    if conflicts_remaining > 0:
        warnings.append(
            f"{conflicts_remaining} conflict(s) could not be fully resolved")

    # Calculate faculty loads
    faculty_loads: Dict[str, float] = {}
    for g in best_chrom:
        if g.professor not in faculty_loads:
            faculty_loads[g.professor] = 0
        faculty_loads[g.professor] += g.units

    elapsed = _time.time() - start_time

    return {
        'success': True,
        'message': f"Generated {len(best_chrom)} schedule entries in {elapsed:.1f}s with {conflicts_remaining} conflict(s)",
        'schedules': [g.to_dict() for g in best_chrom],
        'fitness_score': best_score,
        'generations_run': generations_run,
        'conflicts_remaining': conflicts_remaining,
        'faculty_loads': faculty_loads,
        'warnings': warnings,
        'elapsed_seconds': round(elapsed, 2),
    }


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY run_ga (backward compatible)
# ══════════════════════════════════════════════════════════════════════════════

def run_ga(subjects: List[Dict],
           rooms: List[str],
           prof_availability: Dict[str, List[str]],
           constraints: Dict,
           pop_size: int = 80,
           generations: int = 300) -> List[Dict]:
    """Legacy entry point — kept for backward compatibility."""
    for s in subjects:
        s['weekly_slots'] = slots_for_duration(float(s.get('weekly_hours', 3)))

    if not subjects:
        return []

    population = [build_chromosome(subjects, rooms, prof_availability)
                  for _ in range(pop_size)]

    best_chrom = None
    best_score = float('inf')

    for gen in range(generations):
        scores = [fitness_v2(population[i], prof_availability, {}, {})
                  for i in range(len(population))]

        gen_best_idx = min(range(len(scores)), key=lambda i: scores[i])
        if scores[gen_best_idx] < best_score:
            best_score = scores[gen_best_idx]
            best_chrom = copy.deepcopy(population[gen_best_idx])

        if best_score == 0:
            break

        next_gen = [copy.deepcopy(best_chrom)]
        while len(next_gen) < pop_size:
            p1 = tournament_select_v2(population, scores)
            p2 = tournament_select_v2(population, scores)
            child = crossover_v2(p1, p2)
            child = mutate_v2(child, rooms, prof_availability)
            next_gen.append(child)
        population = next_gen

    if best_chrom is None:
        best_chrom = population[0]

    return [g.to_dict() for g in best_chrom]


# ══════════════════════════════════════════════════════════════════════════════
# SMART SCHEDULE MANIPULATION (Single block operations)
# ══════════════════════════════════════════════════════════════════════════════

def find_optimal_slot(
    schedule: Dict,
    existing_schedules: List[Dict],
    target_day: Optional[str] = None,
    target_time_start: Optional[str] = None,
    target_time_end: Optional[str] = None,
    rooms: List[str] = None
) -> Optional[Dict]:
    """Find optimal time slot for a single schedule block."""
    duration_slots = slots_for_duration(float(schedule.get('units', 1.5)))
    professor = schedule.get('prof', '')
    room = schedule.get('room', 'TBA')
    section = schedule.get('section', '')

    prof_occ = set()
    room_occ = set()
    sect_occ = set()

    for s in existing_schedules:
        if not s.get('start') or not s.get('end') or not s.get('day'):
            continue
        try:
            ss = time_to_slot(s['start'])
            es = time_to_slot(s['end'])
        except (ValueError, IndexError):
            continue
        for slot in range(ss, es):
            key = (s['day'], slot)
            if s.get('prof') == professor:
                prof_occ.add(key)
            if s.get('room') == room and room != 'TBA':
                room_occ.add(key)
            if s.get('section') == section:
                sect_occ.add(key)

    days_to_try = [target_day] if target_day else DAYS
    best_slot = None
    best_score = float('inf')

    for day in days_to_try:
        if target_time_start and target_time_end:
            start_range = time_to_slot(target_time_start)
            end_range = time_to_slot(target_time_end)
        else:
            start_range = 0
            end_range = SLOTS_PER_DAY

        for start_slot in range(start_range, min(end_range, SLOTS_PER_DAY - duration_slots + 1)):
            end_slot = start_slot + duration_slots
            conflict = False
            for slot in range(start_slot, end_slot):
                key = (day, slot)
                if key in prof_occ or key in room_occ or key in sect_occ:
                    conflict = True
                    break
            if not conflict:
                score = start_slot
                if target_day and day != target_day:
                    score += 100
                if score < best_score:
                    best_score = score
                    best_slot = {'day': day, 'start': slot_to_time(start_slot),
                                 'end': slot_to_time(end_slot)}

    if best_slot:
        result = dict(schedule)
        result.update(best_slot)
        return result
    return None


def add_schedule_smart(schedule: Dict, existing_schedules: List[Dict],
                       rooms: List[str] = None) -> Tuple[bool, str, Optional[Dict]]:
    """Intelligently add a single schedule block."""
    result = find_optimal_slot(schedule, existing_schedules, rooms=rooms)
    if result:
        return (True, f"Found optimal slot: {result['day']} at {result['start']}", result)
    return (False, "Could not find a conflict-free time slot.", None)


def move_schedule_smart(schedule_id: str, existing_schedules: List[Dict],
                        target_day: Optional[str] = None,
                        target_time_period: Optional[str] = None,
                        rooms: List[str] = None) -> Tuple[bool, str, Optional[Dict]]:
    """Intelligently move a schedule to new time."""
    schedule_to_move = None
    other_schedules = []
    for s in existing_schedules:
        if s.get('id') == schedule_id:
            schedule_to_move = s
        else:
            other_schedules.append(s)

    if not schedule_to_move:
        return (False, "Schedule not found", None)

    target_start = target_end = None
    if target_time_period:
        periods = {'morning': ('7:00', '12:00'), 'afternoon': ('12:00', '17:00'),
                   'evening': ('17:00', '21:00')}
        if target_time_period in periods:
            target_start, target_end = periods[target_time_period]

    result = find_optimal_slot(schedule_to_move, other_schedules,
                               target_day=target_day,
                               target_time_start=target_start,
                               target_time_end=target_end, rooms=rooms)
    if result:
        return (True, f"Moved to {result['day']} at {result['start']}", result)
    return (False, "Could not find a conflict-free slot for the move", None)
