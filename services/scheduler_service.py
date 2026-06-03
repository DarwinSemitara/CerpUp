"""
Genetic Algorithm – Class Schedule Generator
============================================
Enhanced version with smart schedule manipulation capabilities
"""

import random
import copy
from typing import List, Dict, Any, Optional, Tuple

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
# 30-min slots: 0 = 7:00, 1 = 7:30, … 19 = 16:30  (20 slots per day)
SLOTS_PER_DAY = 20
START_HOUR = 7   # 7:00 AM
MAX_BLOCK_SLOTS = 6   # 3 hours max per block

# ── helpers ──────────────────────────────────────────────────────────────────


def slot_to_time(slot: int) -> str:
    h = START_HOUR + slot // 2
    m = 30 if slot % 2 else 0
    return f"{h}:{m:02d}"


def time_to_slot(t: str) -> int:
    h, m = map(int, t.split(':'))
    return (h - START_HOUR) * 2 + (1 if m >= 30 else 0)


def slots_for_duration(hours: float) -> int:
    """Convert hours to number of 30-min slots."""
    return int(hours * 2)


# ── Gene & Chromosome ─────────────────────────────────────────────────────────

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
        self.duration = duration   # in 30-min slots

    def end_slot(self):
        return self.start_slot + self.duration

    def to_dict(self):
        return {
            'subjCode':  self.subj_code,
            'subjName':  self.subj_name,
            'prof':      self.professor,
            'room':      self.room,
            'section':   self.section,
            'units':     self.units,
            'day':       self.day,
            'start':     slot_to_time(self.start_slot),
            'end':       slot_to_time(self.end_slot()),
        }


def random_gene(subject: Dict, rooms: List[str]) -> Gene:
    """Create a random valid-looking gene for one subject block."""
    day = random.choice(DAYS)
    duration = min(subject['block_slots'], MAX_BLOCK_SLOTS)
    max_start = SLOTS_PER_DAY - duration
    start = random.randint(0, max_start)
    room = random.choice(rooms) if rooms else 'TBA'
    return Gene(
        subj_code=subject['code'],
        subj_name=subject['name'],
        professor=subject['professor'],
        room=room,
        section=subject['section'],
        units=subject['units'],
        day=day,
        start_slot=start,
        duration=duration,
    )


def build_chromosome(subjects: List[Dict], rooms: List[str]) -> List[Gene]:
    """
    Build one chromosome.  Each subject may need multiple blocks to cover
    its weekly hours (e.g. 4 hrs/week = two 2-hr blocks).
    """
    genes = []
    for subj in subjects:
        remaining = subj['weekly_slots']
        while remaining > 0:
            block = min(remaining, MAX_BLOCK_SLOTS)
            s = dict(subj)
            s['block_slots'] = block
            genes.append(random_gene(s, rooms))
            remaining -= block
    return genes


# ── Fitness ───────────────────────────────────────────────────────────────────

HARD_PENALTY = 1000
SOFT_PENALTY = 10


def fitness(chromosome: List[Gene],
            prof_availability: Dict[str, List[str]],
            constraints: Dict) -> float:
    """Lower score = better."""
    score = 0

    # Build occupancy maps
    prof_occ: Dict[str, set] = {}   # prof -> set of (day, slot)
    room_occ: Dict[str, set] = {}   # room -> set of (day, slot)
    sect_occ: Dict[str, set] = {}   # section -> set of (day, slot)
    subj_days: Dict[str, set] = {}  # subj_code -> set of days used

    for g in chromosome:
        slots_used = [(g.day, g.start_slot + i) for i in range(g.duration)]

        # H1 – professor conflict
        if g.professor not in prof_occ:
            prof_occ[g.professor] = set()
        for key in slots_used:
            if key in prof_occ[g.professor]:
                score += HARD_PENALTY
            prof_occ[g.professor].add(key)

        # H2 – room conflict
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

        # S1 – professor availability
        avail = prof_availability.get(g.professor, [])
        if avail and g.day not in avail:
            score += SOFT_PENALTY

        # S3 – spread across days
        if g.subj_code not in subj_days:
            subj_days[g.subj_code] = set()
        subj_days[g.subj_code].add(g.day)

    # S3 penalty: all blocks on same day
    for days_used in subj_days.values():
        if len(days_used) == 1:
            score += SOFT_PENALTY * 2

    return score


# ── GA operators ──────────────────────────────────────────────────────────────

def mutate(chromosome: List[Gene], rooms: List[str], rate: float = 0.15) -> List[Gene]:
    result = copy.deepcopy(chromosome)
    for g in result:
        if random.random() < rate:
            g.day = random.choice(DAYS)
            duration = g.duration
            max_start = SLOTS_PER_DAY - duration
            g.start_slot = random.randint(0, max_start)
            if rooms:
                g.room = random.choice(rooms)
    return result


def crossover(p1: List[Gene], p2: List[Gene]) -> List[Gene]:
    if len(p1) < 2:
        return copy.deepcopy(p1)
    point = random.randint(1, len(p1) - 1)
    return copy.deepcopy(p1[:point]) + copy.deepcopy(p2[point:])


def tournament_select(population, scores, k=3):
    contestants = random.sample(
        list(zip(population, scores)), min(k, len(population)))
    return min(contestants, key=lambda x: x[1])[0]


# ── Main entry point ──────────────────────────────────────────────────────────

def run_ga(subjects: List[Dict],
           rooms: List[str],
           prof_availability: Dict[str, List[str]],
           constraints: Dict,
           pop_size: int = 80,
           generations: int = 300) -> List[Dict]:
    """
    subjects: list of {
        code, name, professor, section, units,
        weekly_hours  (e.g. 4 for 4 hrs/week)
    }
    rooms: list of room name strings
    prof_availability: {professor_name: [list of available days]}
    constraints: dict (reserved for future hard-constraint params)

    Returns list of schedule entry dicts.
    """
    # Pre-process: convert weekly_hours → weekly_slots
    for s in subjects:
        s['weekly_slots'] = slots_for_duration(float(s.get('weekly_hours', 3)))

    if not subjects:
        return []

    # Initial population
    population = [build_chromosome(subjects, rooms) for _ in range(pop_size)]

    best_chrom = None
    best_score = float('inf')

    for gen in range(generations):
        scores = [fitness(c, prof_availability, constraints)
                  for c in population]

        # Track best
        gen_best_idx = min(range(len(scores)), key=lambda i: scores[i])
        if scores[gen_best_idx] < best_score:
            best_score = scores[gen_best_idx]
            best_chrom = copy.deepcopy(population[gen_best_idx])

        # Early exit if perfect
        if best_score == 0:
            break

        # Build next generation
        next_gen = [copy.deepcopy(best_chrom)]  # elitism
        while len(next_gen) < pop_size:
            p1 = tournament_select(population, scores)
            p2 = tournament_select(population, scores)
            child = crossover(p1, p2)
            child = mutate(child, rooms)
            next_gen.append(child)
        population = next_gen

    if best_chrom is None:
        best_chrom = population[0]

    return [g.to_dict() for g in best_chrom]


# ══════════════════════════════════════════════════════════════════════════════
# SMART SCHEDULE MANIPULATION (Phase 2)
# ══════════════════════════════════════════════════════════════════════════════

def find_optimal_slot(
    schedule: Dict,
    existing_schedules: List[Dict],
    target_day: Optional[str] = None,
    target_time_start: Optional[str] = None,
    target_time_end: Optional[str] = None,
    rooms: List[str] = None
) -> Optional[Dict]:
    """
    Find optimal time slot for a schedule using mini-GA

    Args:
        schedule: Schedule to place {prof, subjCode, subjName, room, section, units}
        existing_schedules: Current schedules to avoid conflicts
        target_day: Preferred day (optional)
        target_time_start: Preferred start time (optional)
        target_time_end: Preferred end time (optional)
        rooms: Available rooms

    Returns:
        Optimal schedule with day, start, end or None if no valid slot
    """
    duration_slots = slots_for_duration(float(schedule.get('units', 1.5)))
    professor = schedule['prof']
    room = schedule.get('room', 'TBA')
    section = schedule.get('section', '')

    # Build occupancy from existing schedules
    prof_occ = set()
    room_occ = set()
    sect_occ = set()

    for s in existing_schedules:
        start_slot = time_to_slot(s['start'])
        end_slot = time_to_slot(s['end'])
        for slot in range(start_slot, end_slot):
            key = (s['day'], slot)
            if s['prof'] == professor:
                prof_occ.add(key)
            if s['room'] == room:
                room_occ.add(key)
            if s.get('section') == section:
                sect_occ.add(key)

    # Try to find valid slot
    days_to_try = [target_day] if target_day else DAYS
    best_slot = None
    best_score = float('inf')

    for day in days_to_try:
        # Determine time range
        if target_time_start and target_time_end:
            start_range = time_to_slot(target_time_start)
            end_range = time_to_slot(target_time_end)
        else:
            start_range = 0
            end_range = SLOTS_PER_DAY

        # Try each possible start time
        for start_slot in range(start_range, min(end_range, SLOTS_PER_DAY - duration_slots + 1)):
            end_slot = start_slot + duration_slots

            # Check conflicts
            conflict = False
            for slot in range(start_slot, end_slot):
                key = (day, slot)
                if key in prof_occ or key in room_occ or key in sect_occ:
                    conflict = True
                    break

            if not conflict:
                # Calculate score (prefer earlier times, target day)
                score = 0
                if target_day and day != target_day:
                    score += 100
                score += start_slot  # Prefer earlier times

                if score < best_score:
                    best_score = score
                    best_slot = {
                        'day': day,
                        'start': slot_to_time(start_slot),
                        'end': slot_to_time(end_slot)
                    }

    if best_slot:
        result = dict(schedule)
        result.update(best_slot)
        return result

    return None


def add_schedule_smart(
    schedule: Dict,
    existing_schedules: List[Dict],
    rooms: List[str] = None
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Intelligently add a schedule avoiding conflicts

    Returns:
        (success, message, schedule_with_time)
    """
    # Try to find optimal slot
    result = find_optimal_slot(schedule, existing_schedules, rooms=rooms)

    if result:
        return (True, f"Found optimal slot: {result['day']} at {result['start']}", result)
    else:
        return (False, "Could not find a conflict-free time slot. Please adjust existing schedules.", None)


def move_schedule_smart(
    schedule_id: str,
    existing_schedules: List[Dict],
    target_day: Optional[str] = None,
    target_time_period: Optional[str] = None,
    rooms: List[str] = None
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Intelligently move a schedule to new time

    Returns:
        (success, message, new_schedule)
    """
    # Find the schedule to move
    schedule_to_move = None
    other_schedules = []

    for s in existing_schedules:
        if s.get('id') == schedule_id:
            schedule_to_move = s
        else:
            other_schedules.append(s)

    if not schedule_to_move:
        return (False, "Schedule not found", None)

    # Determine target time range
    target_start = None
    target_end = None
    if target_time_period:
        time_periods = {
            'morning': ('7:00', '12:00'),
            'afternoon': ('12:00', '17:00'),
            'evening': ('17:00', '21:00')
        }
        if target_time_period in time_periods:
            target_start, target_end = time_periods[target_time_period]

    # Find new slot
    result = find_optimal_slot(
        schedule_to_move,
        other_schedules,
        target_day=target_day,
        target_time_start=target_start,
        target_time_end=target_end,
        rooms=rooms
    )

    if result:
        return (True, f"Moved to {result['day']} at {result['start']}", result)
    else:
        return (False, "Could not find a conflict-free slot for the move", None)
