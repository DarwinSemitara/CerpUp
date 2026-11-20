"""
Schedule Generator V3 - HYBRID APPROACH

Strategy:
1. Copy ALL schedules from reference (preserving units, duration, patterns)
2. Use lightweight GA ONLY for conflict resolution (adjusts time/day/room)
3. Never add/remove/merge genes - structure is locked
4. Preserve meeting patterns (MWF stays MWF, TTH stays TTH)

Benefits:
✅ Guaranteed structure preservation
✅ GA focused on what it's good at (optimization)
✅ Predictable results
✅ Fast (small population, conflict-focused)
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
import copy
import random
from services.scheduler_service import (
    Gene, time_to_slot, slot_to_time
)
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


def detect_room_conflicts(schedules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect room conflicts in generated schedules.
    Same logic as frontend detection:
    - Excludes Saturday schedules
    - Excludes grad school rooms
    - Excludes co-teaching (same course+section, different faculty)
    - Excludes stacked schedules (same course+section+time)

    Returns list of conflicts with details.
    """
    logger.info(f"🔍 Starting conflict detection on {len(schedules)} schedules")

    conflicts = []
    conflict_keys = {}  # Track unique conflicts

    # Helper function to convert time to minutes
    def time_to_minutes(time_str):
        if not time_str:
            return 0
        # Handle both "HH:MM" and "HH:MM:SS" formats
        parts = str(time_str).split(':')
        return int(parts[0]) * 60 + int(parts[1])

    # Helper function to check time overlap
    def times_overlap(start1, end1, start2, end2):
        s1 = time_to_minutes(start1)
        e1 = time_to_minutes(end1)
        s2 = time_to_minutes(start2)
        e2 = time_to_minutes(end2)
        # Overlap if: start1 < end2 AND start2 < end1
        overlaps = (s1 < e2 and s2 < e1)
        return overlaps

    # Filter schedules
    filtered_schedules = []
    saturday_count = 0
    grad_count = 0

    for s in schedules:
        # Exclude Saturday
        if s.get('day') == 'Saturday':
            saturday_count += 1
            continue
        # Exclude grad school rooms
        if s.get('room') and 'Graduate School' in s.get('room', ''):
            grad_count += 1
            continue
        filtered_schedules.append(s)

    logger.info(
        f"📊 Filtered: {len(filtered_schedules)} schedules (excluded {saturday_count} Saturday, {grad_count} grad school)")

    # Group by room and day
    room_day_schedules = {}
    for schedule in filtered_schedules:
        room = schedule.get('room', '').strip()
        day = schedule.get('day', '').strip()

        if not room or not day:
            continue

        key = f"{room}|{day}"
        if key not in room_day_schedules:
            room_day_schedules[key] = []
        room_day_schedules[key].append(schedule)

    logger.info(
        f"📊 Grouped into {len(room_day_schedules)} room+day combinations")

    # Check for overlaps in each room+day
    total_pairs_checked = 0
    overlaps_found = 0
    co_teaching_skipped = 0
    stacked_skipped = 0

    for key, schedule_list in room_day_schedules.items():
        if len(schedule_list) < 2:
            continue

        # Log rooms with multiple schedules
        if len(schedule_list) > 2:
            logger.debug(f"  Checking {key}: {len(schedule_list)} schedules")

        for i in range(len(schedule_list)):
            for j in range(i + 1, len(schedule_list)):
                sched1 = schedule_list[i]
                sched2 = schedule_list[j]
                total_pairs_checked += 1

                # Check if times overlap
                if times_overlap(
                    sched1.get('start', ''),
                    sched1.get('end', ''),
                    sched2.get('start', ''),
                    sched2.get('end', '')
                ):
                    overlaps_found += 1

                    # Check if co-teaching (same course+section, different faculty)
                    course1 = f"{sched1.get('subjCode', '')}-{sched1.get('section', '')}"
                    course2 = f"{sched2.get('subjCode', '')}-{sched2.get('section', '')}"

                    is_co_teaching = (
                        course1 == course2 and
                        sched1.get('prof', '') != sched2.get('prof', '')
                    )

                    # Check if stacked (same course+section+time)
                    is_stacked = (
                        course1 == course2 and
                        sched1.get('start', '') == sched2.get('start', '') and
                        sched1.get('end', '') == sched2.get('end', '')
                    )

                    if is_co_teaching:
                        co_teaching_skipped += 1
                        logger.debug(
                            f"  ⏭️ Skipping co-teaching: {course1} ({sched1.get('prof', '')} + {sched2.get('prof', '')})")
                        continue

                    if is_stacked:
                        stacked_skipped += 1
                        logger.debug(f"  ⏭️ Skipping stacked: {course1}")
                        continue

                    # Real conflict - create unique key to avoid duplicates
                    ids = sorted([
                        str(sched1.get('id', str(i))),
                        str(sched2.get('id', str(j)))
                    ])
                    conflict_key = f"{ids[0]}|{ids[1]}"

                    if conflict_key not in conflict_keys:
                        conflict_keys[conflict_key] = True
                        conflicts.append({
                            'room': sched1.get('room', ''),
                            'day': sched1.get('day', ''),
                            'schedules': [
                                {
                                    'id': sched1.get('id'),
                                    'subjCode': sched1.get('subjCode', ''),
                                    'section': sched1.get('section', ''),
                                    'prof': sched1.get('prof', ''),
                                    'start': sched1.get('start', ''),
                                    'end': sched1.get('end', '')
                                },
                                {
                                    'id': sched2.get('id'),
                                    'subjCode': sched2.get('subjCode', ''),
                                    'section': sched2.get('section', ''),
                                    'prof': sched2.get('prof', ''),
                                    'start': sched2.get('start', ''),
                                    'end': sched2.get('end', '')
                                }
                            ]
                        })
                        logger.debug(
                            f"  ⚠️ CONFLICT: {key} - {course1} vs {course2}")

    logger.info(f"📊 Detection summary:")
    logger.info(f"  - Checked {total_pairs_checked} schedule pairs")
    logger.info(f"  - Found {overlaps_found} time overlaps")
    logger.info(f"  - Skipped {co_teaching_skipped} co-teaching")
    logger.info(f"  - Skipped {stacked_skipped} stacked")
    logger.info(f"  - Result: {len(conflicts)} REAL conflicts")

    return conflicts


# Graduate courses (completely frozen)
GRAD_COURSES = [
    'CERP 200', 'CERP 201', 'CERP 211', 'CERP 220', 'CERP 221',
    'CERP 270', 'CERP 271', 'CERP 290', 'CERP 295', 'CERP 298', 'CERP 299'
]

# Available rooms
V2_AVAILABLE_ROOMS = [
    # Undergrad room pool for GA mutations (must match DB format exactly)
    'DCERP AVR', 'DCERP Conf Room', 'CHE Lecture Hall', 'Geomatics Room', 'CHE MPH',
    'TCC 01', 'TCC 02', 'TCC 04', 'TCC 05',
    'NEW Graduate School Bldg Lecture Room 201',
    'NEW Graduate School Bldg Lecture Room 202'
]

# Meeting pattern groups (LOCKED - never change)
PATTERN_GROUPS = {
    'MWF': ['Monday', 'Wednesday', 'Friday'],
    'TTH': ['Tuesday', 'Thursday'],
    'MW': ['Monday', 'Wednesday'],
    'TH': ['Tuesday', 'Thursday'],
    'WF': ['Wednesday', 'Friday'],
    'SAT': ['Saturday'],
    'M': ['Monday'],
    'T': ['Tuesday'],
    'W': ['Wednesday'],
    'R': ['Thursday'],
    'F': ['Friday']
}

# Constraints
MAX_FACULTY_HOURS_PER_DAY = 6.0
MAX_CONSECUTIVE_HOURS = 4.5
UNDERGRAD_MIN_SLOT = 2  # 8:00am
UNDERGRAD_MAX_SLOT = 22  # 6:00pm

# Valid weekdays for scheduling
VALID_WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']


def is_grad_course(course_code: str) -> bool:
    """Check if course is graduate (frozen)."""
    return course_code.strip() in GRAD_COURSES


def calculate_fitness(chromosome: List[Gene]) -> Tuple[float, Dict]:
    """
    Calculate fitness based on conflicts and constraint violations.
    Lower is better (0 = perfect schedule).
    """
    conflicts = 0
    violations = []

    # Check room conflicts - same room cannot host DIFFERENT classes at the same time
    # UNLESS it's co-teaching (same course+section+time with different faculty)
    room_schedule = {}
    room_conflicts_found = 0
    for i, gene in enumerate(chromosome):
        # Only check room conflicts if room is assigned (skip empty rooms)
        if not gene.room or gene.room.strip() == '':
            continue

        for day in get_meeting_days(gene):
            for slot in range(gene.start_slot, gene.start_slot + gene.duration):
                key = (gene.room, day, slot)
                if key in room_schedule:
                    existing_idx = room_schedule[key]
                    existing_gene = chromosome[existing_idx]

                    # Check if this is co-teaching (same course+section, different faculty)
                    is_co_teaching = (
                        gene.subj_code == existing_gene.subj_code and
                        gene.section == existing_gene.section and
                        gene.professor != existing_gene.professor
                    )

                    if is_co_teaching:
                        # Co-teaching is allowed - skip conflict
                        continue

                    # Different courses or sections = real conflict
                    conflicts += 1000  # CRITICAL: Room cannot host two classes at once!
                    room_conflicts_found += 1
                    violations.append(
                        f"Room conflict: {gene.room} on {day} slot {slot} - {gene.subj_code} {gene.section} ({gene.professor}) vs {existing_gene.subj_code} {existing_gene.section} ({existing_gene.professor})")
                else:
                    room_schedule[key] = i

    if room_conflicts_found > 0:
        logger.debug(
            f"Found {room_conflicts_found} room conflicts in fitness calculation")

    # Check faculty conflicts
    faculty_schedule = {}
    for i, gene in enumerate(chromosome):
        for day in get_meeting_days(gene):
            for slot in range(gene.start_slot, gene.start_slot + gene.duration):
                key = (gene.professor, day, slot)
                if key in faculty_schedule:
                    conflicts += 1000  # CRITICAL: Faculty cannot be in two places at once!
                    existing_idx = faculty_schedule[key]
                    existing_gene = chromosome[existing_idx]
                    violations.append(
                        f"Faculty conflict: {gene.professor} on {day} slot {slot} - {gene.subj_code} {gene.section} vs {existing_gene.subj_code} {existing_gene.section}")
                else:
                    faculty_schedule[key] = i

    # Check section conflicts - same section cannot attend DIFFERENT classes at same time
    # UNLESS it's co-teaching (same course+section+time with different faculty = OK)
    section_schedule = {}
    for i, gene in enumerate(chromosome):
        # Only check if section is defined
        if not gene.section or gene.section.strip() == '':
            continue

        for day in get_meeting_days(gene):
            for slot in range(gene.start_slot, gene.start_slot + gene.duration):
                key = (gene.section, day, slot)
                if key in section_schedule:
                    existing_idx = section_schedule[key]
                    existing_gene = chromosome[existing_idx]

                    # Check if this is co-teaching (same course+section, different faculty)
                    is_co_teaching = (
                        gene.subj_code == existing_gene.subj_code and
                        gene.section == existing_gene.section and
                        gene.professor != existing_gene.professor
                    )

                    if is_co_teaching:
                        # Co-teaching is allowed - skip conflict
                        continue

                    # Different courses = students can't be in two places at once
                    conflicts += 1000  # CRITICAL: Section cannot attend different classes at once!
                    violations.append(
                        f"Section conflict: Section {gene.section} on {day} slot {slot} - {gene.subj_code} ({gene.professor}) vs {existing_gene.subj_code} ({existing_gene.professor})")
                else:
                    section_schedule[key] = i

    # Check 6h daily max
    faculty_daily_hours = {}
    for gene in chromosome:
        for day in get_meeting_days(gene):
            key = (gene.professor, day)
            hours = gene.duration * 0.5  # slots to hours
            faculty_daily_hours[key] = faculty_daily_hours.get(key, 0) + hours

    for (prof, day), hours in faculty_daily_hours.items():
        if hours > MAX_FACULTY_HOURS_PER_DAY:
            conflicts += 100  # VERY heavy penalty - this should rarely be violated
            violations.append(
                f"{prof} on {day}: {hours:.1f}h > {MAX_FACULTY_HOURS_PER_DAY}h")

    # Check 4.5h consecutive max
    faculty_day_slots = {}
    for gene in chromosome:
        for day in get_meeting_days(gene):
            key = (gene.professor, day)
            if key not in faculty_day_slots:
                faculty_day_slots[key] = set()
            faculty_day_slots[key].update(
                range(gene.start_slot, gene.start_slot + gene.duration))

    for (prof, day), slots in faculty_day_slots.items():
        sorted_slots = sorted(slots)
        max_consecutive = 1
        current_consecutive = 1
        for i in range(1, len(sorted_slots)):
            if sorted_slots[i] == sorted_slots[i-1] + 1:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1

        max_hours = max_consecutive * 0.5
        if max_hours > MAX_CONSECUTIVE_HOURS:
            conflicts += 50  # Increased penalty for consecutive violations
            violations.append(
                f"{prof} on {day}: {max_hours:.1f}h consecutive > {MAX_CONSECUTIVE_HOURS}h")

    # Check grad-reserved slots (before 8am, after 6pm)
    for gene in chromosome:
        # Course must END before 6pm (not just start before 6pm)
        if gene.start_slot < UNDERGRAD_MIN_SLOT or gene.start_slot + gene.duration > UNDERGRAD_MAX_SLOT:
            conflicts += 500  # High penalty - undergrad classes must be 8am-6pm
            violations.append(
                f"{gene.subj_code} outside 8am-6pm (starts {slot_to_time(gene.start_slot)}, ends {slot_to_time(gene.start_slot + gene.duration)})")

    # Room balancing: strongly encourage even distribution across available rooms
    room_usage = {}
    for gene in chromosome:
        if gene.room and gene.room.strip():
            room_usage[gene.room] = room_usage.get(gene.room, 0) + 1

    if room_usage:
        # Calculate how many courses per room would be ideal
        total_courses = sum(room_usage.values())
        num_available_rooms = len(V2_AVAILABLE_ROOMS)
        ideal_per_room = total_courses / \
            num_available_rooms if num_available_rooms > 0 else 10

        # Penalize rooms that are overused (more than 1.5x ideal)
        for room, count in room_usage.items():
            if room in V2_AVAILABLE_ROOMS:
                if count > ideal_per_room * 1.5:
                    overuse = count - (ideal_per_room * 1.5)
                    conflicts += overuse * 20  # Strong penalty for overuse
                    violations.append(
                        f"Room {room} overused: {count} courses (ideal: {ideal_per_room:.1f})")

        # Bonus: reward using underutilized rooms
        for room in V2_AVAILABLE_ROOMS:
            if room not in room_usage:
                conflicts += 10  # Penalty for completely unused rooms

    return float(conflicts), {'conflicts': conflicts, 'violations': violations[:10]}


def get_meeting_days(gene: Gene) -> List[str]:
    """Get list of days this gene meets."""
    days = [gene.day]
    if gene.pair_day:
        # Handle both single day and comma-separated days (for MWF patterns)
        if ',' in gene.pair_day:
            days.extend(gene.pair_day.split(','))
        else:
            days.append(gene.pair_day)
    return days


def find_free_slot_for_gene(gene: Gene, chromosome: List[Gene], rooms: List[str]) -> Optional[Tuple[int, str]]:
    """
    Intelligently find a free time slot and room for a gene that avoids conflicts.
    Returns (start_slot, room) tuple or None if no free slot found.
    """
    # Get all days this gene needs to meet
    meeting_days = get_meeting_days(gene)

    # Build occupancy map: (room, day, slot) -> gene_index
    occupancy = {}
    for i, g in enumerate(chromosome):
        if g.professor == gene.professor or g.section == gene.section or (g.room and g.room == gene.room):
            for day in get_meeting_days(g):
                for slot in range(g.start_slot, g.start_slot + g.duration):
                    # Track by professor (faculty conflict)
                    key_prof = (g.professor, day, slot)
                    occupancy[key_prof] = i
                    # Track by section (student conflict)
                    if g.section:
                        key_section = (g.section, day, slot)
                        occupancy[key_section] = i
                    # Track by room (room conflict)
                    if g.room:
                        key_room = (g.room, day, slot)
                        occupancy[key_room] = i

    # Try each room and time slot
    candidate_slots = []
    slots_checked = 0
    conflicts_found = {'faculty': 0, 'section': 0, 'room': 0}

    for room in rooms:
        for start_slot in range(UNDERGRAD_MIN_SLOT, UNDERGRAD_MAX_SLOT - gene.duration + 1):
            slots_checked += 1
            # Check if this slot is free for ALL meeting days
            is_free = True
            conflict_type = None
            for day in meeting_days:
                for slot in range(start_slot, start_slot + gene.duration):
                    # Check faculty conflict
                    if (gene.professor, day, slot) in occupancy:
                        is_free = False
                        conflict_type = 'faculty'
                        break
                    # Check section conflict
                    if gene.section and (gene.section, day, slot) in occupancy:
                        is_free = False
                        conflict_type = 'section'
                        break
                    # Check room conflict
                    if (room, day, slot) in occupancy:
                        is_free = False
                        conflict_type = 'room'
                        break
                if not is_free:
                    if conflict_type:
                        conflicts_found[conflict_type] += 1
                    break

            if is_free:
                candidate_slots.append((start_slot, room))

    # Debug logging
    if len(candidate_slots) > 0:
        logger.debug(
            f"✓ Smart slot finder: {gene.subj_code}-{gene.section} ({gene.professor}) - Found {len(candidate_slots)}/{slots_checked} free slots")
    else:
        logger.debug(
            f"✗ Smart slot finder: {gene.subj_code}-{gene.section} ({gene.professor}) - NO free slots found! Checked {slots_checked}, Conflicts: faculty={conflicts_found['faculty']}, section={conflicts_found['section']}, room={conflicts_found['room']}")

    # Return a random free slot if any found
    if candidate_slots:
        return random.choice(candidate_slots)
    return None


def mutate_time_only(gene: Gene, rooms: List[str], chromosome: Optional[List[Gene]] = None) -> Gene:
    """
    Mutate gene by changing time, day pattern, or room (preserving meeting frequency).
    If chromosome is provided, will try to find conflict-free slots intelligently.
    """
    mutated = copy.deepcopy(gene)

    # If we have the full chromosome context, try smart conflict-free mutation first
    used_smart = False
    smart_success = False
    if chromosome and random.random() < 0.7:  # 70% chance to use smart mutation
        used_smart = True
        free_slot = find_free_slot_for_gene(gene, chromosome, rooms)
        if free_slot:
            mutated.start_slot, mutated.room = free_slot
            smart_success = True
            logger.debug(
                f"  → Smart mutation SUCCESS: {gene.subj_code}-{gene.section} moved to slot {free_slot[0]}, room {free_slot[1]}")
            return mutated
        else:
            logger.debug(
                f"  → Smart mutation FAILED: {gene.subj_code}-{gene.section} - falling back to random mutation")

    # Log if we're using random mutation
    if not used_smart:
        logger.debug(
            f"  → Using random mutation (30% chance): {gene.subj_code}-{gene.section}")

    # Otherwise fall back to random mutation
    # Mutate time, day pattern, or room - but preserve number of meeting days
    mutation_type = random.choice(['time', 'day_pattern', 'room'])

    if mutation_type == 'time':
        # Shift time by ±1-2 hours
        shift = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
        new_start = mutated.start_slot + shift
        # Keep in valid range (ensure course ENDS before 6pm)
        new_start = max(UNDERGRAD_MIN_SLOT, min(
            UNDERGRAD_MAX_SLOT - mutated.duration, new_start))
        mutated.start_slot = new_start

    elif mutation_type == 'day_pattern':
        # Change the day pattern while preserving number of meeting days
        current_days = get_meeting_days(gene)
        num_days = len(current_days)

        if num_days == 1:
            # Single day course - can move to any weekday
            available_days = [d for d in VALID_WEEKDAYS if d != gene.day]
            if available_days:
                mutated.day = random.choice(available_days)
                mutated.pair_day = None

        elif num_days == 2:
            # Two-day course - can shift to other 2-day patterns (MW, TTH, WF)
            two_day_patterns = [
                ('Monday', 'Wednesday'),
                ('Tuesday', 'Thursday'),
                ('Wednesday', 'Friday')
            ]
            # Filter out current pattern
            current_pattern = tuple(sorted(current_days))
            other_patterns = [p for p in two_day_patterns if tuple(
                sorted(p)) != current_pattern]
            if other_patterns:
                new_pattern = random.choice(other_patterns)
                mutated.day = new_pattern[0]
                mutated.pair_day = new_pattern[1]

    elif mutation_type == 'room' and rooms:
        # Lock specific courses to specific rooms (HK 12 must stay in Upper Field)
        if gene.subj_code == 'HK 12' or gene.subj_code == 'HK12':
            # Don't mutate room for HK 12
            pass
        else:
            # Smart room mutation - prefer underutilized rooms
            other_rooms = [r for r in rooms if r != gene.room]
            if other_rooms:
                mutated.room = random.choice(other_rooms)
            else:
                mutated.room = random.choice(rooms)

    # Duration and units are NEVER mutated - preserve 1:1:1 hours
    return mutated


def run_hybrid_ga(
    initial_chromosome: List[Gene],
    # Indices of genes that must stay synchronized
    gene_groups: List[List[int]],
    rooms: List[str],
    pop_size: int = 30,
    max_generations: int = 500,
    time_limit: float = 180.0,
    progress_callback=None
) -> Tuple[List[Gene], float, Dict]:
    """
    Lightweight GA that only optimizes time/day/room (never touches structure).
    Keeps MWF/TTH course meetings synchronized (same time, same room).
    """
    import time as _time
    start_time = _time.time()

    logger.info("="*70)
    logger.info("HYBRID GA: CONFLICT RESOLUTION MODE")
    logger.info("="*70)
    logger.info(
        f"Population: {pop_size}, Max Gen: {max_generations}, Time Limit: {time_limit}s")
    logger.info(f"Initial genes: {len(initial_chromosome)}")
    logger.info(f"Synchronized groups: {len(gene_groups)} (MWF/TTH patterns)")
    logger.info("Optimizing: time slots, rooms ONLY")
    logger.info("Locked: units, duration, gene count, meeting days")
    logger.info("="*70)

    # Initialize population (variations of initial chromosome)
    population = []

    # 20% exact copies
    for _ in range(max(1, pop_size // 5)):
        population.append(copy.deepcopy(initial_chromosome))

    # 80% mutated variants
    while len(population) < pop_size:
        variant = copy.deepcopy(initial_chromosome)
        # Mutate 30% of genes (but respect groups)
        mutated_indices = set()
        for i in range(len(variant)):
            if i in mutated_indices:
                continue  # Already mutated as part of a group

            if random.random() < 0.3:
                # Check if this gene is part of a synchronized group
                gene_group = None
                for group in gene_groups:
                    if i in group:
                        gene_group = group
                        break

                if gene_group:
                    # Mutate entire group synchronously (same time/day/room)
                    mutation_type = random.choice(['time', 'day', 'room'])

                    if mutation_type == 'time':
                        shift = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                        for idx in gene_group:
                            new_start = variant[idx].start_slot + shift
                            new_start = max(UNDERGRAD_MIN_SLOT, min(
                                UNDERGRAD_MAX_SLOT - variant[idx].duration, new_start))
                            variant[idx].start_slot = new_start
                            mutated_indices.add(idx)

                    elif mutation_type == 'day':
                        # Move entire group with 1:1:1 pattern for pairs
                        group_days = sorted(
                            set([variant[idx].day for idx in gene_group]))

                        if len(group_days) == 2:
                            # Paired schedule - can shift with 1:1:1 pattern
                            # Valid patterns: Mon/Wed, Wed/Fri, Tue/Thu
                            valid_patterns = [
                                ['Monday', 'Wednesday'],
                                ['Wednesday', 'Friday'],
                                ['Tuesday', 'Thursday']
                            ]
                            # Remove current pattern
                            available_patterns = [
                                p for p in valid_patterns if p != group_days]
                            if available_patterns:
                                new_pattern = random.choice(available_patterns)
                                # Map old days to new days
                                day_map = {
                                    group_days[0]: new_pattern[0], group_days[1]: new_pattern[1]}
                                for idx in gene_group:
                                    old_day = variant[idx].day
                                    variant[idx].day = day_map[old_day]
                                    mutated_indices.add(idx)

                        elif len(group_days) == 3:
                            # Triple pattern (MWF) - keep locked
                            pass

                        elif len(group_days) == 1:
                            # Single-day group: can move to any weekday except Saturday
                            available_days = [
                                d for d in VALID_WEEKDAYS if d != group_days[0] and d != 'Saturday']
                            if available_days:
                                new_day = random.choice(available_days)
                                for idx in gene_group:
                                    variant[idx].day = new_day
                                    mutated_indices.add(idx)

                    elif mutation_type == 'room' and rooms:
                        # Prefer different rooms for diversity
                        current_room = variant[gene_group[0]].room
                        other_rooms = [r for r in rooms if r != current_room]
                        new_room = random.choice(
                            other_rooms) if other_rooms else random.choice(rooms)
                        for idx in gene_group:
                            variant[idx].room = new_room
                            mutated_indices.add(idx)
                else:
                    # Single gene, mutate normally with smart conflict avoidance
                    variant[i] = mutate_time_only(variant[i], rooms, variant)
                    mutated_indices.add(i)

        population.append(variant)

    best_chromosome = copy.deepcopy(initial_chromosome)
    best_fitness, best_details = calculate_fitness(best_chromosome)
    generations_without_improvement = 0
    last_best_fitness = best_fitness

    logger.info(f"Initial fitness: {best_fitness:.0f} conflicts")

    for generation in range(max_generations):
        # Check time limit
        if _time.time() - start_time > time_limit:
            logger.info(f"Time limit reached at generation {generation}")
            break

        # Evaluate population
        fitness_scores = [calculate_fitness(
            chromo)[0] for chromo in population]

        # Track best
        gen_best_idx = fitness_scores.index(min(fitness_scores))
        if fitness_scores[gen_best_idx] < best_fitness:
            best_fitness = fitness_scores[gen_best_idx]
            best_chromosome = copy.deepcopy(population[gen_best_idx])
            _, best_details = calculate_fitness(best_chromosome)
            generations_without_improvement = 0
            logger.info(
                f"Gen {generation}: fitness {best_fitness:.0f} conflicts")
        else:
            generations_without_improvement += 1

        # Periodic detailed logging every 50 generations
        if generation % 50 == 0 and generation > 0:
            logger.info(f"--- Gen {generation} Mutation Strategy Check ---")
            logger.info(
                f"Smart slot finder will run ~70% of time for single-gene mutations")
            logger.info(
                f"Check debug logs above for ✓/✗ indicators of smart slot success")

        # Early stop if perfect
        if best_fitness == 0:
            logger.info(f"Perfect solution found at generation {generation}!")
            break

        # Progress callback
        if progress_callback and generation % 10 == 0:
            avg_fitness = sum(fitness_scores) / len(fitness_scores)

            # Count violations by type from best solution
            violations_by_type = {}
            if best_details:
                breakdown = best_details.get('breakdown', {})
                violations_by_type['room_conflicts'] = breakdown.get(
                    'room_conflicts', 0)
                violations_by_type['faculty_conflicts'] = breakdown.get(
                    'faculty_conflicts', 0)
                violations_by_type['daily_max_violations'] = breakdown.get(
                    'daily_max_violations', 0)
                violations_by_type['consecutive_violations'] = breakdown.get(
                    'consecutive_violations', 0)
                violations_by_type['grad_reserved_violations'] = breakdown.get(
                    'grad_reserved_violations', 0)

            progress_callback({
                'generation': generation,
                'best_score': best_fitness,
                'best_hard_penalty': best_fitness,
                'best_soft_penalty': 0,
                'is_feasible': best_fitness == 0,
                'population_avg_score': avg_fitness,
                'generations_without_improvement': generations_without_improvement,
                'violations_by_type': violations_by_type,
                'elapsed_seconds': _time.time() - start_time
            })

        # Selection and reproduction
        # Keep top 20%
        sorted_indices = sorted(
            range(len(fitness_scores)), key=lambda i: fitness_scores[i])
        next_gen = [copy.deepcopy(population[i])
                    for i in sorted_indices[:max(2, pop_size // 5)]]

        # Generate rest through mutation
        while len(next_gen) < pop_size:
            # Select parent (tournament)
            parent_idx = min(random.sample(
                range(len(population)), 3), key=lambda i: fitness_scores[i])
            child = copy.deepcopy(population[parent_idx])

            # Mutate 20% of genes (respect groups)
            mutated_indices = set()
            for i in range(len(child)):
                if i in mutated_indices:
                    continue

                if random.random() < 0.2:
                    # Check if part of synchronized group
                    gene_group = None
                    for group in gene_groups:
                        if i in group:
                            gene_group = group
                            break

                    if gene_group:
                        # Mutate entire group together
                        mutation_type = random.choice(['time', 'day', 'room'])

                        if mutation_type == 'time':
                            shift = random.choice([-4, -3, -2, -1, 1, 2, 3, 4])
                            for idx in gene_group:
                                new_start = child[idx].start_slot + shift
                                new_start = max(UNDERGRAD_MIN_SLOT, min(
                                    UNDERGRAD_MAX_SLOT - child[idx].duration, new_start))
                                child[idx].start_slot = new_start
                                mutated_indices.add(idx)

                        elif mutation_type == 'day':
                            # Move entire group with 1:1:1 pattern for pairs
                            group_days = sorted(
                                set([child[idx].day for idx in gene_group]))

                            if len(group_days) == 2:
                                # Paired schedule - can shift with 1:1:1 pattern
                                valid_patterns = [
                                    ['Monday', 'Wednesday'],
                                    ['Wednesday', 'Friday'],
                                    ['Tuesday', 'Thursday']
                                ]
                                available_patterns = [
                                    p for p in valid_patterns if p != group_days]
                                if available_patterns:
                                    new_pattern = random.choice(
                                        available_patterns)
                                    day_map = {
                                        group_days[0]: new_pattern[0], group_days[1]: new_pattern[1]}
                                    for idx in gene_group:
                                        old_day = child[idx].day
                                        child[idx].day = day_map[old_day]
                                        mutated_indices.add(idx)

                            elif len(group_days) == 3:
                                # Triple pattern (MWF) - keep locked
                                pass

                            elif len(group_days) == 1:
                                # Single-day group
                                available_days = [
                                    d for d in VALID_WEEKDAYS if d != group_days[0] and d != 'Saturday']
                                if available_days:
                                    new_day = random.choice(available_days)
                                    for idx in gene_group:
                                        child[idx].day = new_day
                                        mutated_indices.add(idx)

                        elif mutation_type == 'room' and rooms:
                            new_room = random.choice(rooms)
                            for idx in gene_group:
                                child[idx].room = new_room
                                mutated_indices.add(idx)
                    else:
                        # Single gene with smart conflict avoidance
                        child[i] = mutate_time_only(child[i], rooms, child)
                        mutated_indices.add(i)

            next_gen.append(child)

        population = next_gen

    elapsed = _time.time() - start_time
    logger.info("="*70)
    logger.info(f"Hybrid GA completed in {elapsed:.1f}s")
    logger.info(f"Final fitness: {best_fitness:.0f} conflicts")
    logger.info(f"Generations run: {generation + 1}")
    logger.info("="*70)

    return best_chromosome, best_fitness, best_details


def generate_schedule_v2(
    target_sy: str,
    target_sem: str,
    reference_sy: str,
    reference_sem: str,
    manual_constraints: Optional[Dict[str, Any]] = None,
    supabase_client=None,
    firebase_db=None,
    progress_callback=None
) -> Dict[str, Any]:
    """
    V3 Hybrid Generator:
    1. Copy structure from reference
    2. Use GA only for conflict resolution
    """
    warnings = []
    frozen_schedules = []

    try:
        logger.info("="*70)
        logger.info("V3 HYBRID SCHEDULE GENERATOR")
        logger.info("="*70)
        logger.info(f"Target: {target_sy} Sem {target_sem}")
        logger.info(f"Reference: {reference_sy} Sem {reference_sem}")
        logger.info("="*70)

        # Load reference schedules
        all_reference_schedules = []

        if supabase_client:
            try:
                ref_result = supabase_client.table('schedules').select('*').eq(
                    'semester', reference_sem).eq('school_year', reference_sy).execute()

                print(
                    f"DEBUG: Loaded {len(ref_result.data)} total entries from reference")

                for rd in ref_result.data:
                    subj_code = rd.get('subj_code', rd.get('subjCode', ''))
                    schedule_entry = {
                        'subjCode': subj_code,
                        'subjName': rd.get('subj_name', rd.get('subjName', '')),
                        'prof': rd.get('prof', ''),
                        'room': rd.get('room', ''),
                        'section': rd.get('section', ''),
                        'units': rd.get('units', 3),
                        'day': rd.get('day', ''),
                        'start': str(rd.get('start', '')).rsplit(':', 1)[0] if rd.get('start') and str(rd.get('start')).count(':') > 1 else rd.get('start', ''),
                        'end': str(rd.get('end', '')).rsplit(':', 1)[0] if rd.get('end') and str(rd.get('end')).count(':') > 1 else rd.get('end', ''),
                    }

                    if is_grad_course(subj_code):
                        frozen_schedules.append(schedule_entry)
                        logger.info(
                            f"FROZEN GRAD: {subj_code}-{schedule_entry['section']}")
                    else:
                        all_reference_schedules.append(schedule_entry)

                print(
                    f"DEBUG: Split into {len(all_reference_schedules)} undergrad + {len(frozen_schedules)} grad")
                logger.info(
                    f"Loaded {len(all_reference_schedules)} undergrad + {len(frozen_schedules)} grad")
            except Exception as e:
                logger.error(f"Error loading reference: {e}")
                return {
                    'success': False,
                    'message': f'Failed to load reference: {e}',
                    'schedules': [],
                    'warnings': [str(e)]
                }

        # Convert reference to genes with grouping for MWF/TTH patterns
        # First pass: collect all entries
        # key: (code, section, prof, start, end, room) -> [entries]
        entry_groups = {}
        skipped_count = 0

        for ref_entry in all_reference_schedules:
            try:
                code = ref_entry.get('subjCode', '')
                section = ref_entry.get('section', '')
                professor = ref_entry.get('prof', '')
                day = ref_entry.get('day', '')
                room = ref_entry.get('room', 'TBA')
                units = int(ref_entry.get('units', 3))

                if not code or not section or not professor or not day:
                    skipped_count += 1
                    logger.warning(
                        f"Skipping incomplete entry: code={code}, section={section}, prof={professor}, day={day}")
                    if 'Angelica' in professor:
                        print(
                            f"  SKIPPED (incomplete): {code}-{section} on {day}")
                    continue

                start_str = ref_entry.get('start', '8:00')
                end_str = ref_entry.get('end', '9:00')
                start_slot = time_to_slot(start_str)
                end_slot = time_to_slot(end_str)
                duration = end_slot - start_slot

                if duration <= 0:
                    skipped_count += 1
                    logger.warning(
                        f"Skipping invalid duration: {code}-{section}, start={start_str}, end={end_str}")
                    if 'Angelica' in professor:
                        print(
                            f"  SKIPPED (invalid duration): {code}-{section} on {day} {start_str}-{end_str}")
                    continue

                # Group by course identity (same course/section/prof/time/room = paired meetings)
                group_key = (code, section, professor,
                             start_slot, duration, room, units)
                if group_key not in entry_groups:
                    entry_groups[group_key] = []

                entry_groups[group_key].append({
                    'day': day,
                    'subj_name': ref_entry.get('subjName', code)
                })

            except Exception as e:
                skipped_count += 1
                logger.warning(f"Skipping entry due to error: {e}")
                if 'Angelica' in ref_entry.get('prof', ''):
                    print(
                        f"  SKIPPED (error): {ref_entry.get('subjCode')}-{ref_entry.get('section')} - {e}")
                continue

        # Second pass: create genes with proper pairing
        genes = []
        # Track which genes belong to same course (for synchronized mutation)
        gene_groups = []

        # Helper to sort days in weekday order (not alphabetical)
        def weekday_sort_key(day):
            order = {'Monday': 1, 'Tuesday': 2, 'Wednesday': 3,
                     'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7}
            return order.get(day, 99)

        for group_key, entries in entry_groups.items():
            code, section, professor, start_slot, duration, room, units = group_key
            # Sort days by weekday order (Mon, Tue, Wed, Thu, Fri) not alphabetically
            days = sorted([e['day'] for e in entries], key=weekday_sort_key)
            subj_name = entries[0]['subj_name']

            # Create ONE gene that represents all meeting days
            # For paired courses (MW, TTH, MWF), we only create one gene with the primary day
            # and store other days in pair_day
            if len(days) == 1:
                # Single day course
                pair_day = None
            elif len(days) == 2:
                # Two-day course (MW, TTH, WF) - first day is primary, second is pair
                pair_day = days[1]
            else:
                # Three-day course (MWF) - Monday is primary, W and F are "paired"
                pair_day = ','.join(days[1:])

            gene = Gene(
                subj_code=code,
                subj_name=subj_name,
                professor=professor,
                room=room,
                section=section,
                units=units,  # LOCKED
                day=days[0],  # Primary day (first day of the week)
                start_slot=start_slot,
                duration=duration,  # LOCKED
                pair_day=pair_day,
                is_custom=False
            )
            genes.append(gene)

            # Don't add to gene_groups - pair_day already tracks multi-day patterns
            # The mutation logic will respect pair_day when changing days
            if len(days) > 1:
                logger.debug(
                    f"Created multi-day gene: {code}-{section} ({professor}): {days[0]} + {pair_day}")

        if skipped_count > 0:
            logger.warning(
                f"SKIPPED {skipped_count} entries during gene creation")
            warnings.append(
                f"Skipped {skipped_count} incomplete/invalid reference entries")

        if not genes:
            return {
                'success': False,
                'message': 'No valid genes from reference',
                'schedules': frozen_schedules,
                'warnings': warnings
            }

        logger.info(
            f"Created {len(genes)} genes from reference (structure locked)")
        logger.info(
            f"Found {len(gene_groups)} synchronized course groups (paired courses)")
        logger.info(f"Plus {len(frozen_schedules)} frozen grad schedules")
        logger.info(f"Total expected: {len(genes) + len(frozen_schedules)}")
        logger.info(
            f"Reference had {len(all_reference_schedules)} undergrad entries")

        # CONSOLE OUTPUT (will definitely appear)
        print("=" * 70)
        print(f"V3 GENERATION SUMMARY:")
        print(f"  Reference undergrad entries: {len(all_reference_schedules)}")
        print(f"  Genes created: {len(genes)}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Synchronized groups: {len(gene_groups)}")
        print(f"  Frozen grad schedules: {len(frozen_schedules)}")
        print(f"  Total output expected: {len(genes) + len(frozen_schedules)}")
        print("=" * 70)

        # Debug: Show Angelica's schedules from reference vs genes
        angelica_ref = [
            s for s in all_reference_schedules if 'Angelica' in s.get('prof', '')]
        angelica_genes = [g for g in genes if 'Angelica' in g.professor]
        if angelica_ref:
            print(f"\nDEBUG: Angelica Magpantay")
            print(f"  Reference entries: {len(angelica_ref)}")

            # Track which courses from reference made it to genes
            ref_courses = set()
            for s in angelica_ref:
                course_key = f"{s['subjCode']}-{s['section']}-{s['day']}"
                ref_courses.add(course_key)
                print(
                    f"    {s['subjCode']}-{s['section']} on {s['day']} {s['start']}-{s['end']}")

            print(f"  Genes created: {len(angelica_genes)}")
            gene_courses = set()
            for g in angelica_genes:
                course_key = f"{g.subj_code}-{g.section}-{g.day}"
                gene_courses.add(course_key)
                print(
                    f"    {g.subj_code}-{g.section} on {g.day} slot {g.start_slot}-{g.start_slot+g.duration}")

            # Show which courses are missing
            missing = ref_courses - gene_courses
            if missing:
                print(f"  MISSING IN GENES: {missing}")

        # Log sample of groups for debugging
        if len(gene_groups) > 0:
            logger.info("Sample of synchronized groups:")
            print("Sample synchronized groups:")
            for i, group in enumerate(gene_groups[:5]):
                group_genes = [genes[idx] for idx in group]
                days = [g.day for g in group_genes]
                code = group_genes[0].subj_code
                section = group_genes[0].section
                prof = group_genes[0].professor
                msg = f"  Group {i+1}: {code}-{section} ({prof}) on {days}"
                logger.info(msg)
                print(msg)

        # Run hybrid GA with gene groups for synchronized mutation
        def ga_progress(progress):
            if progress_callback:
                from services.scheduler_service import GAProgress
                ga_prog = GAProgress(
                    generation=progress.get('generation', 0),
                    best_score=progress.get('best_score', 0),
                    best_hard_penalty=progress.get('best_hard_penalty', 0),
                    best_soft_penalty=progress.get('best_soft_penalty', 0),
                    is_feasible=progress.get('is_feasible', False),
                    population_avg_score=progress.get(
                        'population_avg_score', 0),
                    generations_without_improvement=progress.get(
                        'generations_without_improvement', 0),
                    elapsed_seconds=progress.get('elapsed_seconds', 0),
                    violations_by_type=progress.get('violations_by_type', {})
                )
                progress_callback(ga_prog)

        optimized_genes, final_fitness, details = run_hybrid_ga(
            initial_chromosome=genes,
            gene_groups=gene_groups,  # Pass synchronized groups
            rooms=V2_AVAILABLE_ROOMS,
            pop_size=70,  # Increased to 70 for better conflict resolution
            max_generations=800,  # Increased from 500 for more optimization
            time_limit=300.0,  # 5 minutes (increased from 3)
            progress_callback=ga_progress
        )

        # Debug: Check Angelica's genes after GA
        angelica_optimized = [
            g for g in optimized_genes if 'Angelica' in g.professor]
        print(f"\nDEBUG: After GA optimization")
        print(f"  Total genes: {len(optimized_genes)}")
        print(f"  Angelica genes: {len(angelica_optimized)}")
        if angelica_optimized:
            for g in angelica_optimized:
                print(
                    f"    {g.subj_code}-{g.section} on {g.day} slot {g.start_slot}-{g.start_slot+g.duration} room {g.room}")

        # Convert genes to schedule format
        schedules = []
        for gene in optimized_genes:
            start_time = slot_to_time(gene.start_slot)
            end_time = slot_to_time(gene.start_slot + gene.duration)

            # Create schedule entry for primary day
            schedules.append({
                'subjCode': gene.subj_code,
                'subjName': gene.subj_name,
                'prof': gene.professor,
                'room': gene.room,
                'section': gene.section,
                'units': gene.units,
                'day': gene.day,
                'start': start_time,
                'end': end_time
            })

            # If paired schedule, create entries for additional days
            if gene.pair_day:
                # Handle both single day and comma-separated days (for MWF)
                additional_days = gene.pair_day.split(
                    ',') if ',' in gene.pair_day else [gene.pair_day]
                for additional_day in additional_days:
                    schedules.append({
                        'subjCode': gene.subj_code,
                        'subjName': gene.subj_name,
                        'prof': gene.professor,
                        'room': gene.room,
                        'section': gene.section,
                        'units': gene.units,
                        'day': additional_day.strip(),
                        'start': start_time,
                        'end': end_time
                    })

        # Debug: Check Angelica's schedules after conversion
        angelica_schedules = [
            s for s in schedules if 'Angelica' in s.get('prof', '')]
        print(f"\nDEBUG: After gene-to-schedule conversion")
        print(f"  Total schedules: {len(schedules)}")
        print(f"  Angelica schedules: {len(angelica_schedules)}")
        if angelica_schedules:
            for s in angelica_schedules:
                print(
                    f"    {s['subjCode']}-{s['section']} on {s['day']} {s['start']}-{s['end']} room {s['room']}")

        # Add frozen grad schedules
        schedules.extend(frozen_schedules)

        # Validate
        v2_violations = []
        schedules_by_prof_day = {}
        for sched in schedules:
            prof = sched.get('prof', '')
            day = sched.get('day', '')
            key = f"{prof}::{day}"
            if key not in schedules_by_prof_day:
                schedules_by_prof_day[key] = []
            schedules_by_prof_day[key].append({
                'course': sched.get('subjCode', ''),
                'units': sched.get('units', 0)
            })

        for key, day_schedules in schedules_by_prof_day.items():
            prof, day = key.split('::', 1)
            daily_hours = sum(s['units'] for s in day_schedules)
            if daily_hours > MAX_FACULTY_HOURS_PER_DAY:
                v2_violations.append(
                    f"{prof} on {day}: {daily_hours}h > {MAX_FACULTY_HOURS_PER_DAY}h")
                logger.warning(
                    f"V2 VIOLATION: {prof} on {day} has {daily_hours}h (exceeds {MAX_FACULTY_HOURS_PER_DAY}h)")

        if v2_violations:
            logger.warning(
                f"V3: {len(v2_violations)} constraint violations detected!")
        else:
            logger.info("V3: No violations detected!")

        logger.info(f"Generated {len(schedules)} total schedules")

        # Detect room conflicts in generated schedules
        logger.info("=" * 70)
        logger.info("POST-GENERATION CONFLICT DETECTION")
        logger.info("=" * 70)

        room_conflicts = detect_room_conflicts(schedules)
        conflict_count = len(room_conflicts)

        logger.info(
            f"✅ Post-generation conflict detection complete: {conflict_count} room conflicts found")

        if conflict_count > 0:
            logger.warning(
                f"⚠️ CONFLICTS DETECTED: {conflict_count} room conflicts need resolution")
            # Log first few conflicts for debugging
            for i, conflict in enumerate(room_conflicts[:3]):
                logger.warning(
                    f"  Conflict {i+1}: Room {conflict['room']} on {conflict['day']}")
                for sched in conflict['schedules']:
                    logger.warning(
                        f"    - {sched['subjCode']}-{sched['section']} ({sched['prof']}) {sched['start']}-{sched['end']}")
        else:
            logger.info("✅ No room conflicts detected - schedule is clean!")

        logger.info("=" * 70)

        return {
            'success': True,
            'message': f'V3 Hybrid generation complete ({final_fitness:.0f} conflicts)',
            'schedules': schedules,
            'warnings': warnings,
            'fitness': final_fitness,
            'details': details,
            'room_conflicts': conflict_count  # Add conflict count to response
        }

    except Exception as e:
        logger.error(f"V3 generation failed: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'V3 error: {str(e)}',
            'schedules': frozen_schedules,
            'warnings': warnings + [str(e)]
        }


def resolve_room_conflicts(
    schedules: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
    available_rooms: List[str],
    school_year: str,
    semester: str
) -> Dict[str, Any]:
    """
    Automatically resolve room conflicts by reassigning time/room for conflicting schedules.

    Rules:
    1. Preserve MW/TTH/MWF patterns (paired schedules move together)
    2. Keep duration and units unchanged
    3. Try 6-hour daily limit first, allow 8-hour emergency fallback (only 1 day per faculty)
    4. Only modify conflicting schedules, leave others untouched

    Returns:
    {
        'success': bool,
        'resolved_count': int,
        'updated_schedules': List[Dict],
        'emergency_exceptions': List[str],  # Faculty who used 8-hour exception
        'unresolved': List[Dict]  # Conflicts that couldn't be resolved
    }
    """
    logger.info(f"Starting conflict resolution for {len(conflicts)} conflicts")

    # Helper functions
    def time_to_minutes(time_str):
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])

    def minutes_to_time(minutes):
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def get_duration_minutes(start, end):
        return time_to_minutes(end) - time_to_minutes(start)

    def times_overlap(start1, end1, start2, end2):
        s1 = time_to_minutes(start1)
        e1 = time_to_minutes(end1)
        s2 = time_to_minutes(start2)
        e2 = time_to_minutes(end2)
        return (s1 < e2 and s2 < e1)

    # Build schedule index by ID for quick lookup
    schedule_by_id = {s['id']: s for s in schedules if 'id' in s}

    # Track which schedules are part of paired courses (MW, TTH, MWF)
    # Group by: (subjCode, section, prof, start, end, room)
    paired_groups = {}
    for sched in schedules:
        key = (
            sched.get('subjCode', ''),
            sched.get('section', ''),
            sched.get('prof', ''),
            sched.get('start', ''),
            sched.get('end', ''),
            sched.get('room', '')
        )
        if key not in paired_groups:
            paired_groups[key] = []
        paired_groups[key].append(sched['id'])

    # Track faculty daily hours (for 6/8 hour limit)
    faculty_daily_hours = {}
    for sched in schedules:
        prof = sched.get('prof', '')
        day = sched.get('day', '')
        duration = get_duration_minutes(
            sched.get('start', '0:00'), sched.get('end', '0:00')) / 60.0
        key = (prof, day)
        faculty_daily_hours[key] = faculty_daily_hours.get(key, 0) + duration

    # Track which faculty have used their 8-hour exception
    emergency_exceptions = {}  # faculty -> day

    # Updated schedules
    updated_schedules = []
    unresolved = []
    resolved_count = 0

    # Collect all conflicting schedule IDs to avoid processing duplicates
    processed_ids = set()

    # Process each conflict
    for conflict in conflicts:
        conflict_schedules = conflict['schedules']

        # For each schedule in the conflict, try to find a new slot
        for sched_info in conflict_schedules:
            sched_id = sched_info['id']

            if sched_id in processed_ids or sched_id not in schedule_by_id:
                continue

            original_sched = schedule_by_id[sched_id]

            # Find all paired schedules (same course/section/prof/time/room but different days)
            paired_key = (
                original_sched['subjCode'],
                original_sched['section'],
                original_sched['prof'],
                original_sched['start'],
                original_sched['end'],
                original_sched['room']
            )
            paired_schedule_ids = paired_groups.get(paired_key, [sched_id])
            paired_schedules = [schedule_by_id[pid]
                                for pid in paired_schedule_ids if pid in schedule_by_id]

            duration_minutes = get_duration_minutes(
                original_sched['start'], original_sched['end'])
            duration_hours = duration_minutes / 60.0

            # Get days this course meets
            meeting_days = [s['day'] for s in paired_schedules]

            logger.info(
                f"Trying to resolve conflict for {original_sched['subjCode']}-{original_sched['section']} ({len(meeting_days)} days: {meeting_days})")

            # Try to find a free slot
            found_slot = False
            attempts = 0
            max_attempts_to_log = 5

            # Time slots to try (8am to 6pm, every 30 minutes)
            for start_minutes in range(8*60, 18*60 - duration_minutes, 30):
                end_minutes = start_minutes + duration_minutes
                new_start = minutes_to_time(start_minutes)
                new_end = minutes_to_time(end_minutes)

                # Try each available room
                for room in available_rooms:
                    attempts += 1

                    # Debug first few attempts
                    if attempts <= max_attempts_to_log:
                        logger.debug(
                            f"  Attempt {attempts}: Testing {new_start}-{new_end} in {room}")

                    # Check if this slot works for ALL meeting days
                    slot_works = True
                    exceeds_6hour_limit = False
                    needs_emergency = False
                    conflict_reason = None

                    for day in meeting_days:
                        # Check room availability - ONLY against same semester/year
                        for other_sched in schedules:
                            if other_sched['id'] in paired_schedule_ids:
                                continue  # Skip own paired schedules

                            # IMPORTANT: Only check schedules in the same semester/year
                            if (other_sched.get('school_year') != school_year or
                                    other_sched.get('semester') != semester):
                                continue

                            if (other_sched.get('room') == room and
                                other_sched.get('day') == day and
                                    times_overlap(new_start, new_end, other_sched['start'], other_sched['end'])):
                                slot_works = False
                                conflict_reason = f"Room {room} occupied on {day} by {other_sched.get('subjCode')}"
                                break

                        if not slot_works:
                            break

                        # Check faculty availability - ONLY against same semester/year
                        prof = original_sched['prof']
                        for other_sched in schedules:
                            if other_sched['id'] in paired_schedule_ids:
                                continue

                            # IMPORTANT: Only check schedules in the same semester/year
                            if (other_sched.get('school_year') != school_year or
                                    other_sched.get('semester') != semester):
                                continue

                            if (other_sched.get('prof') == prof and
                                other_sched.get('day') == day and
                                    times_overlap(new_start, new_end, other_sched['start'], other_sched['end'])):
                                slot_works = False
                                conflict_reason = f"Prof {prof} teaching {other_sched.get('subjCode')} on {day}"
                                break

                        if not slot_works:
                            break

                        # Check 6-hour daily limit
                        faculty_key = (prof, day)
                        current_hours = faculty_daily_hours.get(faculty_key, 0)

                        # Subtract old hours from this schedule if it was on this day
                        for ps in paired_schedules:
                            if ps['day'] == day:
                                old_duration = get_duration_minutes(
                                    ps['start'], ps['end']) / 60.0
                                current_hours -= old_duration

                        # Add new hours
                        new_total_hours = current_hours + duration_hours

                        if new_total_hours > 6:
                            if new_total_hours <= 8:
                                # Check if faculty hasn't already used emergency exception
                                if prof not in emergency_exceptions or emergency_exceptions[prof] == day:
                                    exceeds_6hour_limit = True
                                    needs_emergency = True
                                else:
                                    # Faculty already used exception on a different day
                                    slot_works = False
                                    conflict_reason = f"Prof {prof} already used 8h exception on {emergency_exceptions[prof]}"
                                    break
                            else:
                                # Exceeds even emergency 8-hour limit
                                slot_works = False
                                conflict_reason = f"Would exceed 8h limit ({new_total_hours:.1f}h on {day})"
                                break

                    # Log why first few attempts failed
                    if not slot_works and attempts <= max_attempts_to_log:
                        logger.debug(f"    ✗ Failed: {conflict_reason}")

                    if slot_works:
                        # Found a valid slot!
                        logger.info(
                            f"  ✓ Found slot: {new_start}-{new_end} in {room} ({meeting_days})")

                        # Update all paired schedules
                        for ps in paired_schedules:
                            ps['start'] = new_start
                            ps['end'] = new_end
                            ps['room'] = room
                            updated_schedules.append(ps)
                            processed_ids.add(ps['id'])

                        # Mark emergency exception if needed
                        if needs_emergency:
                            for day in meeting_days:
                                faculty_key = (original_sched['prof'], day)
                                new_hours = faculty_daily_hours.get(
                                    faculty_key, 0)
                                # Recalculate
                                for ps in paired_schedules:
                                    if ps['day'] == day:
                                        new_hours = sum(
                                            get_duration_minutes(
                                                s['start'], s['end']) / 60.0
                                            for s in schedules
                                            if s.get('prof') == original_sched['prof'] and s.get('day') == day
                                        )
                                        if new_hours > 6:
                                            emergency_exceptions[original_sched['prof']] = day
                                            logger.warning(
                                                f"  ⚠️ Emergency 8-hour exception used for {original_sched['prof']} on {day}")

                        found_slot = True
                        resolved_count += 1
                        break

                if found_slot:
                    break

            if not found_slot:
                logger.warning(
                    f"  ✗ Could not resolve conflict for {original_sched['subjCode']}-{original_sched['section']}")
                unresolved.append(conflict)

    return {
        'success': len(unresolved) == 0,
        'resolved_count': resolved_count,
        'updated_schedules': updated_schedules,
        'emergency_exceptions': list(emergency_exceptions.keys()),
        'unresolved': unresolved
    }
