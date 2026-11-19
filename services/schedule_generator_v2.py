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
            pop_size=50,  # Increased from 30 for better exploration
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

        return {
            'success': True,
            'message': f'V3 Hybrid generation complete ({final_fitness:.0f} conflicts)',
            'schedules': schedules,
            'warnings': warnings,
            'fitness': final_fitness,
            'details': details
        }

    except Exception as e:
        logger.error(f"V3 generation failed: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'V3 error: {str(e)}',
            'schedules': frozen_schedules,
            'warnings': warnings + [str(e)]
        }
