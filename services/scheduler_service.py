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

from typing import Callable
import threading
import random
import copy
import time as _time
from typing import List, Dict, Any, Optional, Tuple, Set
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
# DATA MODEL CONVERSION UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def build_qualification_matrix_from_allocations(subject_allocations: Dict[str, List[str]]):
    """Build qualification matrix from subject allocation dictionary."""
    # Import here to avoid forward reference issue
    qm = globals()['QualificationMatrix']()
    qm.course_to_faculty = dict(subject_allocations)

    # Build reverse mapping
    for course_code, faculty_list in subject_allocations.items():
        for faculty_id in faculty_list:
            if faculty_id not in qm.faculty_to_courses:
                qm.faculty_to_courses[faculty_id] = []
            if course_code not in qm.faculty_to_courses[faculty_id]:
                qm.faculty_to_courses[faculty_id].append(course_code)

    return qm


def legacy_config_to_new_format(config):
    """Convert legacy configuration to new comprehensive format (in-place enhancement)."""

    # Build qualification matrix if not present
    if not config.qualification_matrix and config.subject_allocations:
        config.qualification_matrix = build_qualification_matrix_from_allocations(
            config.subject_allocations)

    # Build faculty objects if not present
    if not config.faculty and config.prof_availability:
        config.faculty = []
        all_profs = set(config.prof_availability.keys())
        all_profs.update(config.teaching_loads.keys())
        for subj_profs in config.subject_allocations.values():
            all_profs.update(subj_profs)

        Faculty = globals()['Faculty']
        for prof_id in all_profs:
            qualified_courses = config.qualification_matrix.faculty_to_courses.get(
                prof_id, []) if config.qualification_matrix else []
            config.faculty.append(Faculty(
                id=prof_id,
                name=prof_id,  # Use ID as name if not available
                employment_status='full-time',  # Default assumption
                qualified_courses=qualified_courses,
                min_units=12,
                max_units=config.teaching_loads.get(
                    prof_id, DEFAULT_TEACHING_LOAD),
                availability=config.prof_availability.get(
                    prof_id, WEEKDAYS.copy()),
            ))

    # Build room objects if not present
    if not config.rooms and config.rooms_legacy:
        config.rooms = []
        Room = globals()['Room']
        for room_name in config.rooms_legacy:
            config.rooms.append(Room(
                id=room_name,
                name=room_name,
                room_type='lecture',  # Default assumption
                capacity=50,  # Default assumption
            ))

    # Build timeslot config if not present
    if not config.timeslot_config:
        Timeslot = globals()['Timeslot']
        config.timeslot_config = Timeslot()

    return config


def extract_legacy_format_from_config(config):
    """Extract legacy format dictionaries from comprehensive config for backward compatibility."""
    legacy = {
        'rooms': config.rooms_legacy if config.rooms_legacy else [r.name for r in config.rooms],
        'prof_availability': {},
        'teaching_loads': {},
        'subject_allocations': {},
    }

    # Extract from faculty objects
    for faculty in config.faculty:
        legacy['prof_availability'][faculty.id] = faculty.availability
        legacy['teaching_loads'][faculty.id] = faculty.max_units

    # Extract from qualification matrix
    if config.qualification_matrix:
        legacy['subject_allocations'] = dict(
            config.qualification_matrix.course_to_faculty)

    # Merge with existing legacy data
    legacy['prof_availability'].update(config.prof_availability)
    legacy['teaching_loads'].update(config.teaching_loads)
    legacy['subject_allocations'].update(config.subject_allocations)

    return legacy


# ══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Faculty:
    """Complete faculty member data model."""
    id: str
    name: str
    employment_status: str  # 'full-time' | 'part-time' | 'affiliate'
    qualified_courses: List[str] = field(default_factory=list)
    min_units: int = 12  # Minimum teaching load
    max_units: int = 18  # Maximum teaching load
    non_teaching_load: float = 0.0  # Admin/research units
    availability: List[str] = field(default_factory=list)  # Days available
    availability_blocks: Dict[str, List[Tuple[int, int]]] = field(
        default_factory=dict)  # day -> [(start_slot, end_slot)]
    soft_preferences: Dict[str, Any] = field(
        default_factory=dict)  # e.g., prefer_no_early_morning
    previous_courses: List[str] = field(
        default_factory=list)  # For continuity scoring


@dataclass
class Room:
    """Complete room data model."""
    id: str
    name: str
    room_type: str  # 'lecture' | 'laboratory' | 'computer_lab' | 'seminar'
    capacity: int
    building: str = ''
    availability_blocks: Dict[str, List[Tuple[int, int]]] = field(
        # day -> [(start_slot, end_slot)] for maintenance
        default_factory=dict)


@dataclass
class Section:
    """Student section data model."""
    id: str
    program: str  # e.g., 'BS HE', 'BS FN'
    year_level: int  # 1, 2, 3, 4
    section_name: str  # e.g., 'A', 'B', '1'
    student_count: int
    required_courses: List[str] = field(default_factory=list)


@dataclass
class Course:
    """Course/subject data model."""
    code: str
    name: str
    units: int
    lecture_hours: float  # Hours per week
    lab_hours: float = 0.0  # Hours per week (if applicable)
    required_room_type: str = 'lecture'  # 'lecture' | 'laboratory' | 'computer_lab'
    is_lab_course: bool = False


@dataclass
class Timeslot:
    """Timeslot configuration."""
    days: List[str] = field(default_factory=lambda: WEEKDAYS.copy())
    start_hour: int = 7
    end_hour: int = 17
    slots_per_day: int = 20
    break_periods: List[Tuple[int, int]] = field(
        default_factory=list)  # [(start_slot, end_slot)]


@dataclass
class SubjectInput:
    """Subject-section combination for scheduling (legacy compatibility)."""
    code: str
    name: str
    section: str
    units: int
    weekly_hours: float
    allocated_professors: List[str] = field(default_factory=list)
    room_type_required: str = 'lecture'
    is_lab: bool = False
    section_student_count: int = 30


@dataclass
class QualificationMatrix:
    """Explicit faculty-course qualification mapping."""
    faculty_to_courses: Dict[str, List[str]] = field(
        default_factory=dict)  # faculty_id -> [course_codes]
    course_to_faculty: Dict[str, List[str]] = field(
        default_factory=dict)  # course_code -> [faculty_ids]

    def is_qualified(self, faculty_id: str, course_code: str) -> bool:
        """Check if faculty is qualified to teach a course."""
        return course_code in self.faculty_to_courses.get(faculty_id, [])

    def get_qualified_faculty(self, course_code: str) -> List[str]:
        """Get all faculty qualified to teach a course."""
        return self.course_to_faculty.get(course_code, [])


@dataclass
class FullGAConfig:
    """Complete GA configuration with all inputs."""
    # Core data (NEW comprehensive models)
    faculty: List[Faculty] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    courses: List[Course] = field(default_factory=list)
    qualification_matrix: Optional[QualificationMatrix] = None
    timeslot_config: Optional[Timeslot] = None

    # Legacy format (for backward compatibility)
    subjects: List[SubjectInput] = field(default_factory=list)
    rooms_legacy: List[str] = field(default_factory=list)
    prof_availability: Dict[str, List[str]] = field(default_factory=dict)
    teaching_loads: Dict[str, int] = field(default_factory=dict)
    subject_allocations: Dict[str, List[str]] = field(default_factory=dict)

    # Previous schedule for seeding and continuity
    reference_schedules: List[Dict] = field(default_factory=list)
    previous_schedule_data: List[Dict] = field(
        default_factory=list)  # For continuity scoring

    # Overrides and preferences
    faculty_overrides: Dict[str, Any] = field(default_factory=dict)

    # GA parameters
    pop_size: int = 100
    max_generations: int = 1000
    time_limit_seconds: float = 120.0
    elitism_count: int = 2
    crossover_rate: float = 0.8
    mutation_rate: float = 0.15
    tournament_size: int = 4

    # Constraint weights (for two-tier fitness)
    weight_hard_violations: float = 1000.0
    weight_soft_violations: float = 10.0
    weight_faculty_conflicts: float = 1000.0
    weight_room_conflicts: float = 1000.0
    weight_section_conflicts: float = 1000.0
    weight_room_capacity: float = 1000.0
    weight_room_type_mismatch: float = 1000.0
    weight_min_load_violation: float = 100.0
    weight_max_load_violation: float = 1000.0
    weight_continuity_bonus: float = 5.0
    weight_load_balance: float = 10.0
    weight_gap_penalty: float = 10.0

    # Termination criteria
    plateau_generations: int = 50  # Stop if no improvement for N generations
    # Stop if fitness reaches this (0 = perfect)
    feasibility_threshold: float = 0.0
    enable_plateau_detection: bool = True
    enable_time_budget: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# HARD CONSTRAINT CHECKERS (Individual testable functions)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConstraintViolation:
    """Record of a constraint violation for reporting."""
    constraint_type: str
    gene_index: int
    severity: str  # 'hard' | 'soft'
    penalty: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


def check_faculty_time_conflict(chromosome: List['Gene'], gene_idx: int) -> Optional[ConstraintViolation]:
    """H1: Check if faculty teaches two classes at the same time."""
    gene = chromosome[gene_idx]
    gene_slots = set(range(gene.start_slot, gene.end_slot()))

    for i, other in enumerate(chromosome):
        if i == gene_idx:
            continue
        if other.professor == gene.professor and other.day == gene.day:
            other_slots = set(range(other.start_slot, other.end_slot()))
            overlap = gene_slots.intersection(other_slots)
            if overlap:
                return ConstraintViolation(
                    constraint_type='faculty_time_conflict',
                    gene_index=gene_idx,
                    severity='hard',
                    penalty=HARD_PENALTY * len(overlap),
                    message=f"Faculty {gene.professor} has time conflict on {gene.day}",
                    details={
                        'conflicting_gene': i,
                        'overlapping_slots': len(overlap),
                        'time_range': f"{slot_to_time(min(overlap))}-{slot_to_time(max(overlap)+1)}"
                    }
                )
    return None


def check_room_time_conflict(chromosome: List['Gene'], gene_idx: int) -> Optional[ConstraintViolation]:
    """H2: Check if room hosts two classes at the same time."""
    gene = chromosome[gene_idx]
    if not gene.room or gene.room == 'TBA':
        return None

    gene_slots = set(range(gene.start_slot, gene.end_slot()))

    for i, other in enumerate(chromosome):
        if i == gene_idx:
            continue
        if other.room == gene.room and other.day == gene.day and other.room != 'TBA':
            other_slots = set(range(other.start_slot, other.end_slot()))
            overlap = gene_slots.intersection(other_slots)
            if overlap:
                return ConstraintViolation(
                    constraint_type='room_time_conflict',
                    gene_index=gene_idx,
                    severity='hard',
                    penalty=HARD_PENALTY * len(overlap),
                    message=f"Room {gene.room} has time conflict on {gene.day}",
                    details={
                        'conflicting_gene': i,
                        'overlapping_slots': len(overlap),
                        'time_range': f"{slot_to_time(min(overlap))}-{slot_to_time(max(overlap)+1)}"
                    }
                )
    return None


def check_section_time_conflict(chromosome: List['Gene'], gene_idx: int) -> Optional[ConstraintViolation]:
    """H3: Check if section attends two classes at the same time."""
    gene = chromosome[gene_idx]
    gene_slots = set(range(gene.start_slot, gene.end_slot()))

    for i, other in enumerate(chromosome):
        if i == gene_idx:
            continue
        if other.section == gene.section and other.day == gene.day:
            other_slots = set(range(other.start_slot, other.end_slot()))
            overlap = gene_slots.intersection(other_slots)
            if overlap:
                return ConstraintViolation(
                    constraint_type='section_time_conflict',
                    gene_index=gene_idx,
                    severity='hard',
                    penalty=HARD_PENALTY * len(overlap),
                    message=f"Section {gene.section} has time conflict on {gene.day}",
                    details={
                        'conflicting_gene': i,
                        'overlapping_slots': len(overlap),
                        'time_range': f"{slot_to_time(min(overlap))}-{slot_to_time(max(overlap)+1)}"
                    }
                )
    return None


def check_faculty_qualification(gene: 'Gene', qualification_matrix: Optional[QualificationMatrix],
                                subject_allocations: Dict[str, List[str]]) -> Optional[ConstraintViolation]:
    """H4: Check if faculty is qualified to teach the course."""
    # Use qualification matrix if available, otherwise fall back to subject_allocations
    if qualification_matrix:
        if not qualification_matrix.is_qualified(gene.professor, gene.subj_code):
            qualified_faculty = qualification_matrix.get_qualified_faculty(
                gene.subj_code)
            return ConstraintViolation(
                constraint_type='faculty_qualification',
                gene_index=-1,  # Will be set by caller
                severity='hard',
                penalty=HARD_PENALTY,
                message=f"Faculty {gene.professor} not qualified to teach {gene.subj_code}",
                details={
                    'course': gene.subj_code,
                    'faculty': gene.professor,
                    'qualified_faculty': qualified_faculty
                }
            )
    else:
        # Legacy check
        alloc = subject_allocations.get(gene.subj_code, [])
        if alloc and gene.professor not in alloc:
            return ConstraintViolation(
                constraint_type='faculty_qualification',
                gene_index=-1,
                severity='hard',
                penalty=HARD_PENALTY,
                message=f"Faculty {gene.professor} not in allocation list for {gene.subj_code}",
                details={
                    'course': gene.subj_code,
                    'faculty': gene.professor,
                    'allocated_faculty': alloc
                }
            )
    return None


def check_room_type_match(gene: 'Gene', rooms: List[Room], room_type_required: str) -> Optional[ConstraintViolation]:
    """H5: Check if room type matches course requirement (lecture vs lab)."""
    if not rooms or not gene.room or gene.room == 'TBA':
        return None

    # Find room object
    room_obj = next((r for r in rooms if r.name ==
                    gene.room or r.id == gene.room), None)
    if not room_obj:
        return None  # Room not in database, can't validate

    if room_obj.room_type != room_type_required:
        return ConstraintViolation(
            constraint_type='room_type_mismatch',
            gene_index=-1,
            severity='hard',
            penalty=HARD_PENALTY,
            message=f"Room {gene.room} type '{room_obj.room_type}' doesn't match required '{room_type_required}'",
            details={
                'room': gene.room,
                'room_type': room_obj.room_type,
                'required_type': room_type_required,
                'course': gene.subj_code
            }
        )
    return None


def check_room_capacity(gene: 'Gene', rooms: List[Room], section_student_count: int) -> Optional[ConstraintViolation]:
    """H6: Check if room capacity >= section's student count."""
    if not rooms or not gene.room or gene.room == 'TBA':
        return None

    # Find room object
    room_obj = next((r for r in rooms if r.name ==
                    gene.room or r.id == gene.room), None)
    if not room_obj:
        return None  # Room not in database, can't validate

    if room_obj.capacity < section_student_count:
        return ConstraintViolation(
            constraint_type='room_capacity_exceeded',
            gene_index=-1,
            severity='hard',
            penalty=HARD_PENALTY,
            message=f"Room {gene.room} capacity {room_obj.capacity} < section size {section_student_count}",
            details={
                'room': gene.room,
                'room_capacity': room_obj.capacity,
                'section_size': section_student_count,
                'overflow': section_student_count - room_obj.capacity
            }
        )
    return None


def check_faculty_availability(gene: 'Gene', prof_availability: Dict[str, List[str]]) -> Optional[ConstraintViolation]:
    """H7: Check if class falls within faculty's declared availability."""
    avail = prof_availability.get(gene.professor, [])
    if avail and gene.day not in avail:
        return ConstraintViolation(
            constraint_type='faculty_availability',
            gene_index=-1,
            severity='hard',
            penalty=HARD_PENALTY,
            message=f"Faculty {gene.professor} not available on {gene.day}",
            details={
                'faculty': gene.professor,
                'scheduled_day': gene.day,
                'available_days': avail
            }
        )
    return None


def check_operating_hours(gene: 'Gene', timeslot_config: Optional[Timeslot]) -> Optional[ConstraintViolation]:
    """H8: Check if class falls within institutional operating hours."""
    if not timeslot_config:
        # Default check: 7:00 AM to 5:00 PM (slot 0-20)
        if gene.end_slot() > SLOTS_PER_DAY:
            return ConstraintViolation(
                constraint_type='operating_hours',
                gene_index=-1,
                severity='hard',
                penalty=HARD_PENALTY,
                message=f"Class ends after operating hours: {slot_to_time(gene.end_slot())}",
                details={
                    'end_time': slot_to_time(gene.end_slot()),
                    'max_allowed': slot_to_time(SLOTS_PER_DAY)
                }
            )
    else:
        max_slot = (timeslot_config.end_hour - timeslot_config.start_hour) * 2
        if gene.end_slot() > max_slot:
            return ConstraintViolation(
                constraint_type='operating_hours',
                gene_index=-1,
                severity='hard',
                penalty=HARD_PENALTY,
                message=f"Class ends after operating hours: {slot_to_time(gene.end_slot())}",
                details={
                    'end_time': slot_to_time(gene.end_slot()),
                    'max_allowed': slot_to_time(max_slot)
                }
            )
    return None


def check_block_length(gene: 'Gene', is_lab: bool) -> Optional[ConstraintViolation]:
    """H9: Check if block duration is valid (not too long)."""
    if gene.duration > MAX_BLOCK_SLOTS:
        return ConstraintViolation(
            constraint_type='block_too_long',
            gene_index=-1,
            severity='hard',
            penalty=HARD_PENALTY * (gene.duration - MAX_BLOCK_SLOTS),
            message=f"Block duration {gene.duration} slots exceeds maximum {MAX_BLOCK_SLOTS}",
            details={
                'duration_slots': gene.duration,
                'duration_hours': gene.duration / 2.0,
                'max_slots': MAX_BLOCK_SLOTS,
                'max_hours': MAX_BLOCK_SLOTS / 2.0
            }
        )
    return None


def check_all_hard_constraints(chromosome: List['Gene'], gene_idx: int, config: FullGAConfig) -> List[ConstraintViolation]:
    """Run all hard constraint checks on a specific gene and return violations."""
    gene = chromosome[gene_idx]
    violations = []

    # H1: Faculty time conflict
    v = check_faculty_time_conflict(chromosome, gene_idx)
    if v:
        violations.append(v)

    # H2: Room time conflict
    v = check_room_time_conflict(chromosome, gene_idx)
    if v:
        violations.append(v)

    # H3: Section time conflict
    v = check_section_time_conflict(chromosome, gene_idx)
    if v:
        violations.append(v)

    # H4: Faculty qualification
    v = check_faculty_qualification(
        gene, config.qualification_matrix, config.subject_allocations)
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    # H7: Faculty availability
    legacy = extract_legacy_format_from_config(config)
    v = check_faculty_availability(gene, legacy['prof_availability'])
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    # H8: Operating hours
    v = check_operating_hours(gene, config.timeslot_config)
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    # H9: Block length
    # Determine if this is a lab from the gene or config
    is_lab = False
    for subj in config.subjects:
        if subj.code == gene.subj_code and subj.section == gene.section:
            is_lab = subj.is_lab
            break
    v = check_block_length(gene, is_lab)
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    # H5: Room type match (requires SubjectInput with room_type_required)
    room_type_required = 'lecture'
    for subj in config.subjects:
        if subj.code == gene.subj_code and subj.section == gene.section:
            room_type_required = subj.room_type_required
            break
    v = check_room_type_match(gene, config.rooms, room_type_required)
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    # H6: Room capacity (requires SubjectInput with section_student_count)
    section_student_count = 30  # Default
    for subj in config.subjects:
        if subj.code == gene.subj_code and subj.section == gene.section:
            section_student_count = subj.section_student_count
            break
    v = check_room_capacity(gene, config.rooms, section_student_count)
    if v:
        v.gene_index = gene_idx
        violations.append(v)

    return violations


# ══════════════════════════════════════════════════════════════════════════════
# SOFT CONSTRAINT SCORING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def score_minimum_load_violation(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S1: Penalize faculty below 12-unit minimum teaching load."""
    violations = []
    penalty = 0.0

    # Calculate faculty loads
    faculty_loads: Dict[str, float] = {}
    for g in chromosome:
        if g.professor not in faculty_loads:
            faculty_loads[g.professor] = 0
        faculty_loads[g.professor] += g.units

    # Check minimum loads
    for faculty_id, load in faculty_loads.items():
        # Get min_units from faculty objects or use default
        min_units = 12
        for f in config.faculty:
            if f.id == faculty_id or f.name == faculty_id:
                min_units = f.min_units
                break

        if load < min_units:
            shortage = min_units - load
            penalty += config.weight_min_load_violation * shortage
            violations.append(ConstraintViolation(
                constraint_type='minimum_load_violation',
                gene_index=-1,
                severity='soft',
                penalty=config.weight_min_load_violation * shortage,
                message=f"Faculty {faculty_id} below minimum load: {load}/{min_units} units",
                details={
                    'faculty': faculty_id,
                    'current_load': load,
                    'minimum_load': min_units,
                    'shortage': shortage
                }
            ))

    return penalty, violations


def score_maximum_load_violation(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S2: Penalize faculty exceeding maximum teaching load."""
    violations = []
    penalty = 0.0

    # Calculate faculty loads
    faculty_loads: Dict[str, float] = {}
    for g in chromosome:
        if g.professor not in faculty_loads:
            faculty_loads[g.professor] = 0
        faculty_loads[g.professor] += g.units

    # Get teaching loads from config
    legacy = extract_legacy_format_from_config(config)
    teaching_loads = legacy['teaching_loads']

    # Check maximum loads
    for faculty_id, load in faculty_loads.items():
        max_load = teaching_loads.get(faculty_id, DEFAULT_TEACHING_LOAD)
        if load > max_load:
            excess = load - max_load
            penalty += config.weight_max_load_violation * excess
            violations.append(ConstraintViolation(
                constraint_type='maximum_load_violation',
                gene_index=-1,
                severity='soft',
                penalty=config.weight_max_load_violation * excess,
                message=f"Faculty {faculty_id} exceeds maximum load: {load}/{max_load} units",
                details={
                    'faculty': faculty_id,
                    'current_load': load,
                    'maximum_load': max_load,
                    'excess': excess
                }
            ))

    return penalty, violations


def score_load_balance_across_week(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S3: Penalize unbalanced faculty load distribution across days of the week."""
    violations = []
    penalty = 0.0

    # Track faculty loads per day
    faculty_day_loads: Dict[str, Dict[str, float]] = {}

    for g in chromosome:
        if g.professor not in faculty_day_loads:
            faculty_day_loads[g.professor] = {}
        if g.day not in faculty_day_loads[g.professor]:
            faculty_day_loads[g.professor][g.day] = 0
        # Count hours (duration in slots / 2)
        faculty_day_loads[g.professor][g.day] += g.duration / 2.0

    # Calculate variance in daily loads for each faculty
    for faculty_id, day_loads in faculty_day_loads.items():
        if len(day_loads) < 2:
            continue  # Can't have imbalance with only 1 day

        loads = list(day_loads.values())
        mean_load = sum(loads) / len(loads)
        variance = sum((load - mean_load) ** 2 for load in loads) / len(loads)

        # Penalize high variance (imbalanced schedule)
        if variance > 2.0:  # Threshold: 2 hours variance
            penalty += config.weight_load_balance * variance
            violations.append(ConstraintViolation(
                constraint_type='load_imbalance',
                gene_index=-1,
                severity='soft',
                penalty=config.weight_load_balance * variance,
                message=f"Faculty {faculty_id} has unbalanced weekly load (variance: {variance:.2f})",
                details={
                    'faculty': faculty_id,
                    'day_loads': day_loads,
                    'variance': variance,
                    'mean_load': mean_load
                }
            ))

    return penalty, violations


def score_continuity_with_previous_schedule(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S4: Reward keeping same faculty on same course as previous schedule (negative penalty = bonus)."""
    violations = []
    bonus = 0.0  # Negative penalty

    if not config.previous_schedule_data and not config.reference_schedules:
        return 0.0, []

    # Use reference_schedules if previous_schedule_data not available
    previous = config.previous_schedule_data if config.previous_schedule_data else config.reference_schedules

    # Build previous assignment map: course+section -> professor
    prev_assignments: Dict[str, str] = {}
    for entry in previous:
        course = entry.get('subjCode') or entry.get('subj_code', '')
        section = entry.get('section', '')
        prof = entry.get('prof', '')
        key = f"{course}_{section}"
        if key not in prev_assignments:
            prev_assignments[key] = prof

    # Check current chromosome for matches
    current_assignments: Dict[str, Set[str]] = {}
    for g in chromosome:
        key = f"{g.subj_code}_{g.section}"
        if key not in current_assignments:
            current_assignments[key] = set()
        current_assignments[key].add(g.professor)

    # Score continuity
    for key, prev_prof in prev_assignments.items():
        if key in current_assignments:
            current_profs = current_assignments[key]
            if prev_prof in current_profs:
                # Same professor maintained - give bonus
                bonus -= config.weight_continuity_bonus
                violations.append(ConstraintViolation(
                    constraint_type='continuity_bonus',
                    gene_index=-1,
                    severity='soft',
                    penalty=-config.weight_continuity_bonus,
                    message=f"Continuity maintained: {prev_prof} still teaches {key}",
                    details={
                        'course_section': key,
                        'professor': prev_prof,
                        'bonus': config.weight_continuity_bonus
                    }
                ))

    return bonus, violations


def score_faculty_consecutive_hours(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S5: Penalize faculty teaching >4 consecutive hours without break."""
    violations = []
    penalty = 0.0

    # Track professor daily slots
    prof_daily_slots: Dict[str, Dict[str, List[int]]] = {}

    for g in chromosome:
        if g.professor not in prof_daily_slots:
            prof_daily_slots[g.professor] = {}
        if g.day not in prof_daily_slots[g.professor]:
            prof_daily_slots[g.professor][g.day] = []
        prof_daily_slots[g.professor][g.day].extend(
            range(g.start_slot, g.end_slot()))

    # Check consecutive hours
    for prof, days in prof_daily_slots.items():
        for day, slots in days.items():
            if not slots:
                continue
            sorted_slots = sorted(set(slots))
            consecutive = 1
            max_consecutive = 1

            for i in range(1, len(sorted_slots)):
                if sorted_slots[i] == sorted_slots[i-1] + 1:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 1

            # Penalize if >8 slots (4 hours) consecutive
            if max_consecutive > 8:
                excess_slots = max_consecutive - 8
                penalty += SOFT_PENALTY * excess_slots
                violations.append(ConstraintViolation(
                    constraint_type='excessive_consecutive_hours',
                    gene_index=-1,
                    severity='soft',
                    penalty=SOFT_PENALTY * excess_slots,
                    message=f"Faculty {prof} has {max_consecutive/2:.1f} consecutive hours on {day}",
                    details={
                        'faculty': prof,
                        'day': day,
                        'consecutive_slots': max_consecutive,
                        'consecutive_hours': max_consecutive / 2.0,
                        'excess_hours': excess_slots / 2.0
                    }
                ))

    return penalty, violations


def score_section_gaps(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S6: Penalize large gaps (>2 hours) between section classes on same day."""
    violations = []
    penalty = 0.0

    # Track section daily slots
    sect_daily_slots: Dict[str, Dict[str, List[int]]] = {}

    for g in chromosome:
        if g.section not in sect_daily_slots:
            sect_daily_slots[g.section] = {}
        if g.day not in sect_daily_slots[g.section]:
            sect_daily_slots[g.section][g.day] = []
        sect_daily_slots[g.section][g.day].extend(
            range(g.start_slot, g.end_slot()))

    # Check for gaps
    for section, days in sect_daily_slots.items():
        for day, slots in days.items():
            if len(slots) < 2:
                continue
            sorted_slots = sorted(set(slots))

            # Find blocks and gaps
            i = 0
            while i < len(sorted_slots) - 1:
                # Find end of current block
                j = i
                while j < len(sorted_slots) - 1 and sorted_slots[j+1] == sorted_slots[j] + 1:
                    j += 1

                # Check gap to next block
                if j < len(sorted_slots) - 1:
                    gap = sorted_slots[j+1] - sorted_slots[j] - 1
                    if gap > 4:  # >2 hours gap
                        penalty += config.weight_gap_penalty
                        violations.append(ConstraintViolation(
                            constraint_type='large_gap',
                            gene_index=-1,
                            severity='soft',
                            penalty=config.weight_gap_penalty,
                            message=f"Section {section} has {gap/2:.1f} hour gap on {day}",
                            details={
                                'section': section,
                                'day': day,
                                'gap_slots': gap,
                                'gap_hours': gap / 2.0
                            }
                        ))
                i = j + 1

    return penalty, violations


def score_same_day_concentration(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S7: Penalize all sessions of a subject concentrated on same day."""
    violations = []
    penalty = 0.0

    # Track days per subject-section
    subj_days: Dict[str, Set[str]] = {}

    for g in chromosome:
        key = f"{g.subj_code}_{g.section}"
        if key not in subj_days:
            subj_days[key] = set()
        subj_days[key].add(g.day)

    # Penalize single-day subjects
    for key, days in subj_days.items():
        if len(days) == 1:
            penalty += SOFT_PENALTY * 2
            violations.append(ConstraintViolation(
                constraint_type='same_day_concentration',
                gene_index=-1,
                severity='soft',
                penalty=SOFT_PENALTY * 2,
                message=f"Subject {key} concentrated on single day: {list(days)[0]}",
                details={
                    'subject_section': key,
                    'days': list(days)
                }
            ))

    return penalty, violations


def score_part_time_campus_days(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S8: Minimize number of distinct days part-time faculty must be on campus."""
    violations = []
    penalty = 0.0

    # Track days per faculty
    faculty_days: Dict[str, Set[str]] = {}

    for g in chromosome:
        if g.professor not in faculty_days:
            faculty_days[g.professor] = set()
        faculty_days[g.professor].add(g.day)

    # Penalize part-time faculty with many campus days
    for faculty in config.faculty:
        if faculty.employment_status == 'part-time':
            days = faculty_days.get(
                faculty.id, set()) or faculty_days.get(faculty.name, set())
            if len(days) > 3:  # More than 3 days is penalized
                excess_days = len(days) - 3
                penalty += SOFT_PENALTY * excess_days * 2
                violations.append(ConstraintViolation(
                    constraint_type='part_time_excessive_days',
                    gene_index=-1,
                    severity='soft',
                    penalty=SOFT_PENALTY * excess_days * 2,
                    message=f"Part-time faculty {faculty.name} scheduled on {len(days)} days",
                    details={
                        'faculty': faculty.name,
                        'employment_status': 'part-time',
                        'days_scheduled': list(days),
                        'day_count': len(days)
                    }
                ))

    return penalty, violations


def score_soft_time_preferences(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """S9: Penalize violations of faculty soft time preferences (e.g., no early morning)."""
    violations = []
    penalty = 0.0

    for gene_idx, g in enumerate(chromosome):
        # Find faculty preferences
        faculty_prefs = None
        for faculty in config.faculty:
            if faculty.id == g.professor or faculty.name == g.professor:
                faculty_prefs = faculty.soft_preferences
                break

        if not faculty_prefs:
            continue

        # Check "prefer_no_early_morning" (before 8:00 AM = slot 2)
        if faculty_prefs.get('prefer_no_early_morning', False):
            if g.start_slot < 2:  # Before 8:00 AM
                penalty += SOFT_PENALTY
                violations.append(ConstraintViolation(
                    constraint_type='early_morning_preference',
                    gene_index=gene_idx,
                    severity='soft',
                    penalty=SOFT_PENALTY,
                    message=f"Faculty {g.professor} prefers no early morning but scheduled at {slot_to_time(g.start_slot)}",
                    details={
                        'faculty': g.professor,
                        'start_time': slot_to_time(g.start_slot),
                        'preference': 'no_early_morning'
                    }
                ))

        # Check "prefer_no_late_afternoon" (after 4:00 PM = slot 18)
        if faculty_prefs.get('prefer_no_late_afternoon', False):
            if g.start_slot >= 18:
                penalty += SOFT_PENALTY
                violations.append(ConstraintViolation(
                    constraint_type='late_afternoon_preference',
                    gene_index=gene_idx,
                    severity='soft',
                    penalty=SOFT_PENALTY,
                    message=f"Faculty {g.professor} prefers no late afternoon but scheduled at {slot_to_time(g.start_slot)}",
                    details={
                        'faculty': g.professor,
                        'start_time': slot_to_time(g.start_slot),
                        'preference': 'no_late_afternoon'
                    }
                ))

    return penalty, violations


def score_all_soft_constraints(chromosome: List['Gene'], config: FullGAConfig) -> Tuple[float, List[ConstraintViolation]]:
    """Run all soft constraint scoring and return total penalty and all violations."""
    total_penalty = 0.0
    all_violations = []

    # S1: Minimum load violation
    penalty, violations = score_minimum_load_violation(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S2: Maximum load violation
    penalty, violations = score_maximum_load_violation(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S3: Load balance across week
    penalty, violations = score_load_balance_across_week(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S4: Continuity with previous schedule
    penalty, violations = score_continuity_with_previous_schedule(
        chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S5: Faculty consecutive hours
    penalty, violations = score_faculty_consecutive_hours(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S6: Section gaps
    penalty, violations = score_section_gaps(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S7: Same day concentration
    penalty, violations = score_same_day_concentration(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S8: Part-time campus days
    penalty, violations = score_part_time_campus_days(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    # S9: Soft time preferences
    penalty, violations = score_soft_time_preferences(chromosome, config)
    total_penalty += penalty
    all_violations.extend(violations)

    return total_penalty, all_violations


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
# ENHANCED FITNESS FUNCTION (v3 - Two-Tier Scoring)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class FitnessBreakdown:
    """Detailed breakdown of fitness score for logging and reporting."""
    total_score: float
    hard_penalty: float
    soft_penalty: float
    hard_violations: List[ConstraintViolation]
    soft_violations: List[ConstraintViolation]
    is_feasible: bool
    violation_count_by_type: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_score': self.total_score,
            'hard_penalty': self.hard_penalty,
            'soft_penalty': self.soft_penalty,
            'is_feasible': self.is_feasible,
            'hard_violation_count': len(self.hard_violations),
            'soft_violation_count': len(self.soft_violations),
            'violations_by_type': self.violation_count_by_type,
        }


def fitness_v3(chromosome: List[Gene], config: FullGAConfig) -> FitnessBreakdown:
    """
    Enhanced two-tier fitness function with configurable weights.

    Tier 1 (Feasibility): Hard constraint violations heavily penalized
    Tier 2 (Quality): Soft constraint violations lightly penalized

    Lower score = better. Target: 0 = perfect schedule.

    Returns FitnessBreakdown with detailed violation information.
    """
    hard_violations = []
    soft_violations = []

    # TIER 1: Check all hard constraints for each gene
    for gene_idx in range(len(chromosome)):
        violations = check_all_hard_constraints(chromosome, gene_idx, config)
        hard_violations.extend(violations)

    # Calculate hard penalty
    hard_penalty = sum(v.penalty for v in hard_violations)

    # TIER 2: Score all soft constraints (chromosome-level)
    soft_penalty, soft_viols = score_all_soft_constraints(chromosome, config)
    soft_violations.extend(soft_viols)

    # Total fitness (lower = better)
    total_score = hard_penalty + soft_penalty

    # Determine feasibility (no hard violations)
    is_feasible = len(hard_violations) == 0

    # Count violations by type
    violation_counts: Dict[str, int] = {}
    for v in hard_violations + soft_violations:
        violation_counts[v.constraint_type] = violation_counts.get(
            v.constraint_type, 0) + 1

    return FitnessBreakdown(
        total_score=total_score,
        hard_penalty=hard_penalty,
        soft_penalty=soft_penalty,
        hard_violations=hard_violations,
        soft_violations=soft_violations,
        is_feasible=is_feasible,
        violation_count_by_type=violation_counts,
    )


def fitness_v2(chromosome: List[Gene],
               prof_availability: Dict[str, List[str]],
               teaching_loads: Dict[str, int],
               subject_allocations: Dict[str, List[str]]) -> float:
    """
    LEGACY FITNESS FUNCTION - Kept for backward compatibility.
    Use fitness_v3() for new code with comprehensive constraint checking.

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


def fitness_wrapper(chromosome: List[Gene], config: Optional[FullGAConfig] = None,
                    prof_availability: Optional[Dict[str, List[str]]] = None,
                    teaching_loads: Optional[Dict[str, int]] = None,
                    subject_allocations: Optional[Dict[str, List[str]]] = None) -> float:
    """
    Wrapper that routes to appropriate fitness function based on arguments.
    If config is provided, uses fitness_v3 (comprehensive).
    Otherwise, uses fitness_v2 (legacy).
    """
    if config is not None:
        breakdown = fitness_v3(chromosome, config)
        return breakdown.total_score
    else:
        # Legacy path
        return fitness_v2(
            chromosome,
            prof_availability or {},
            teaching_loads or {},
            subject_allocations or {}
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCED GA OPERATORS (v3 - Section/Day-level operations)
# ══════════════════════════════════════════════════════════════════════════════

def mutate_v3(chromosome: List[Gene], config: FullGAConfig,
              rate: float = 0.15, targeted: bool = False) -> List[Gene]:
    """
    Enhanced mutation with availability-awareness and optional targeted mutation.

    Args:
        chromosome: Chromosome to mutate
        config: GA configuration with rooms, availability, etc.
        rate: Base mutation rate (probability per gene)
        targeted: If True, prioritize mutating genes with violations

    Returns:
        Mutated chromosome
    """
    result = copy.deepcopy(chromosome)
    legacy = extract_legacy_format_from_config(config)
    rooms = legacy['rooms']
    prof_availability = legacy['prof_availability']

    # If targeted mutation, identify violated genes
    violated_genes = set()
    if targeted:
        for i in range(len(result)):
            violations = check_all_hard_constraints(result, i, config)
            if violations:
                violated_genes.add(i)

    for i, g in enumerate(result):
        # Higher mutation rate for violated genes in targeted mode
        effective_rate = rate * \
            3 if (targeted and i in violated_genes) else rate

        if random.random() < effective_rate:
            # Mutate day (respect availability)
            avail = prof_availability.get(g.professor, [])
            valid_days = avail if avail else WEEKDAYS
            g.day = random.choice(valid_days)

            # Mutate start time
            max_start = SLOTS_PER_DAY - g.duration
            g.start_slot = random.randint(0, max(0, max_start))

            # Occasionally mutate room (30% chance)
            if rooms and random.random() < 0.3:
                # Try to find rooms of the correct type if available
                suitable_rooms = []
                for subj in config.subjects:
                    if subj.code == g.subj_code and subj.section == g.section:
                        room_type_needed = subj.room_type_required
                        suitable_rooms = [
                            r.name for r in config.rooms if r.room_type == room_type_needed]
                        break

                if suitable_rooms:
                    g.room = random.choice(suitable_rooms)
                elif rooms:
                    g.room = random.choice(rooms)

    return result


def crossover_v3_section_level(p1: List[Gene], p2: List[Gene]) -> List[Gene]:
    """
    Section-level crossover: swap entire section schedules between parents.
    This preserves section coherence and reduces constraint violations.
    """
    if len(p1) < 2:
        return copy.deepcopy(p1)

    # Group genes by section
    p1_sections: Dict[str, List[Gene]] = {}
    p2_sections: Dict[str, List[Gene]] = {}

    for g in p1:
        if g.section not in p1_sections:
            p1_sections[g.section] = []
        p1_sections[g.section].append(g)

    for g in p2:
        if g.section not in p2_sections:
            p2_sections[g.section] = []
        p2_sections[g.section].append(g)

    # Start with p1 as base
    child_genes = []
    sections_used = set()

    # For each section, randomly choose from p1 or p2
    all_sections = set(p1_sections.keys()).union(set(p2_sections.keys()))

    for section in all_sections:
        if random.random() < 0.5 and section in p1_sections:
            # Use p1's version of this section
            child_genes.extend(copy.deepcopy(p1_sections[section]))
        elif section in p2_sections:
            # Use p2's version of this section
            child_genes.extend(copy.deepcopy(p2_sections[section]))
        elif section in p1_sections:
            # Fallback to p1 if p2 doesn't have it
            child_genes.extend(copy.deepcopy(p1_sections[section]))

    return child_genes


def crossover_v3_day_level(p1: List[Gene], p2: List[Gene]) -> List[Gene]:
    """
    Day-level crossover: swap entire days' schedules between parents.
    Preserves daily structure and reduces time conflicts.
    """
    if len(p1) < 2:
        return copy.deepcopy(p1)

    # Group genes by day
    p1_days: Dict[str, List[Gene]] = {}
    p2_days: Dict[str, List[Gene]] = {}

    for g in p1:
        if g.day not in p1_days:
            p1_days[g.day] = []
        p1_days[g.day].append(g)

    for g in p2:
        if g.day not in p2_days:
            p2_days[g.day] = []
        p2_days[g.day].append(g)

    # For each day, randomly choose from p1 or p2
    child_genes = []
    all_days = set(p1_days.keys()).union(set(p2_days.keys()))

    for day in all_days:
        if random.random() < 0.5 and day in p1_days:
            child_genes.extend(copy.deepcopy(p1_days[day]))
        elif day in p2_days:
            child_genes.extend(copy.deepcopy(p2_days[day]))
        elif day in p1_days:
            child_genes.extend(copy.deepcopy(p1_days[day]))

    return child_genes


def crossover_v3(p1: List[Gene], p2: List[Gene], method: str = 'gene') -> List[Gene]:
    """
    Enhanced crossover with multiple strategies.

    Args:
        p1, p2: Parent chromosomes
        method: 'gene' (gene-level), 'section' (section-level), 'day' (day-level), or 'mixed'

    Returns:
        Child chromosome
    """
    if method == 'section':
        return crossover_v3_section_level(p1, p2)
    elif method == 'day':
        return crossover_v3_day_level(p1, p2)
    elif method == 'mixed':
        # Randomly choose strategy
        choice = random.choice(['gene', 'section', 'day'])
        return crossover_v3(p1, p2, method=choice)
    else:
        # Default: gene-preserving crossover (existing v2 logic)
        return crossover_v2(p1, p2)


def tournament_select_v3(population: List[List[Gene]],
                         fitness_scores: List[FitnessBreakdown],
                         config: FullGAConfig) -> List[Gene]:
    """
    Enhanced tournament selection using FitnessBreakdown.
    Prioritizes feasible solutions when available.
    """
    k = config.tournament_size
    contestants_idx = random.sample(
        range(len(population)), min(k, len(population)))

    # Separate feasible and infeasible contestants
    feasible = [(i, fitness_scores[i])
                for i in contestants_idx if fitness_scores[i].is_feasible]
    infeasible = [(i, fitness_scores[i])
                  for i in contestants_idx if not fitness_scores[i].is_feasible]

    # If any feasible solutions exist, pick best among them
    if feasible:
        best_idx = min(feasible, key=lambda x: x[1].total_score)[0]
    else:
        # All infeasible, pick the least bad
        best_idx = min(infeasible, key=lambda x: x[1].total_score)[0]

    return population[best_idx]


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY GA OPERATORS (v2 - kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════════════════

def mutate_v2(chromosome: List[Gene], rooms: List[str],
              prof_availability: Dict[str, List[str]],
              rate: float = 0.15) -> List[Gene]:
    """LEGACY - Availability-aware mutation. Use mutate_v3() for new code."""
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
    """LEGACY - Gene-preserving crossover. Use crossover_v3() for new code."""
    if len(p1) < 2:
        return copy.deepcopy(p1)

    # Use p1 as the base (preserves all subject-section coverage)
    child = copy.deepcopy(p1)

    # For a random subset of genes, copy day+start_slot+room from p2's matching genes
    p2_map = {}
    for g in p2:
        key = f"{g.subj_code}_{g.section}_{g.professor}"
        if key not in p2_map:
            p2_map[key] = []
        p2_map[key].append(g)

    for i, g in enumerate(child):
        if random.random() < 0.5:
            key = f"{g.subj_code}_{g.section}_{g.professor}"
            if key in p2_map and p2_map[key]:
                donor = p2_map[key][0]
                g.day = donor.day
                g.start_slot = donor.start_slot
                g.room = donor.room
                # Rotate through donors
                p2_map[key] = p2_map[key][1:] + [p2_map[key][0]]

    return child


def tournament_select_v2(population, scores, k=4):
    """LEGACY - Tournament selection. Use tournament_select_v3() for new code."""
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

    # Deduplicate: ensure total hours per subject-section don't exceed expected
    # Group by subject+section, keep only enough blocks to fill weekly_hours
    from collections import defaultdict
    gene_groups = defaultdict(list)
    for g in ref_genes:
        key = f"{g.subj_code}_{g.section}"
        gene_groups[key].append(g)

    # Find configured weekly hours from subjects list
    subj_hours = {}
    for s in subjects:
        key = f"{s['code']}_{s['section']}"
        subj_hours[key] = s.get(
            'weekly_slots', slots_for_duration(float(s.get('units', 3))))

    # Trim excess blocks
    trimmed_genes = []
    for key, genes in gene_groups.items():
        max_slots = subj_hours.get(key, 6)  # default 3 hours = 6 slots
        total_slots = 0
        for g in genes:
            if total_slots + g.duration <= max_slots:
                trimmed_genes.append(g)
                total_slots += g.duration
            elif total_slots < max_slots:
                # Trim this gene's duration to fit
                g.duration = max_slots - total_slots
                trimmed_genes.append(g)
                total_slots = max_slots

    ref_genes = trimmed_genes if trimmed_genes else ref_genes

    # Ensure ALL subjects from the subjects list are covered
    # If a subject isn't in the reference, create random genes for it
    ref_keys = set(f"{g.subj_code}_{g.section}" for g in ref_genes)
    for subj in subjects:
        key = f"{subj['code']}_{subj['section']}"
        if key not in ref_keys:
            # This subject wasn't in reference — create from scratch
            remaining = subj.get('weekly_slots', slots_for_duration(
                float(subj.get('units', 3))))
            while remaining > 0:
                block = min(remaining, MAX_BLOCK_SLOTS)
                s = dict(subj)
                s['block_slots'] = block
                ref_genes.append(random_gene(s, rooms, prof_availability))
                remaining -= block

    # Create seeded population — ALL with randomized time slots
    # No direct copies: we want the GA to find NEW optimal placements
    population = []
    for _ in range(pop_size):
        variant = copy.deepcopy(ref_genes)
        for g in variant:
            # Fully randomize day and time (respecting availability)
            avail = prof_availability.get(g.professor, [])
            valid_days = avail if avail else WEEKDAYS
            g.day = random.choice(valid_days)
            max_start = SLOTS_PER_DAY - g.duration
            g.start_slot = random.randint(0, max(0, max_start))
            # Also randomize room occasionally
            if rooms and random.random() < 0.2:
                g.room = random.choice(rooms)
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
# ENHANCED REPAIR STRATEGY (v3 - Comprehensive constraint-aware repair)
# ══════════════════════════════════════════════════════════════════════════════

def repair_pass_v3(chromosome: List[Gene], config: FullGAConfig,
                   max_iterations: int = 300) -> Tuple[List[Gene], int]:
    """
    Enhanced repair pass with comprehensive constraint handling.

    Strategies applied in order:
    1. Fix faculty time conflicts (move time/day)
    2. Fix room conflicts (swap room, move time)
    3. Fix section conflicts (move time/day)
    4. Fix qualification mismatches (swap faculty if possible)
    5. Fix availability violations (move to valid day)
    6. Fix room type/capacity violations (swap to suitable room)

    Returns: (repaired_chromosome, repairs_made_count)
    """
    result = copy.deepcopy(chromosome)
    legacy = extract_legacy_format_from_config(config)
    repairs_made = 0

    for iteration in range(max_iterations):
        # Get all hard violations
        all_violations = []
        for gene_idx in range(len(result)):
            violations = check_all_hard_constraints(result, gene_idx, config)
            for v in violations:
                all_violations.append((gene_idx, v))

        if not all_violations:
            break  # No more violations

        # Pick a random violation to fix
        gene_idx, violation = random.choice(all_violations)

        # Apply appropriate repair strategy based on violation type
        fixed = False

        if violation.constraint_type == 'faculty_time_conflict':
            fixed = _repair_faculty_conflict(result, gene_idx, legacy)
        elif violation.constraint_type == 'room_time_conflict':
            fixed = _repair_room_conflict(result, gene_idx, config)
        elif violation.constraint_type == 'section_time_conflict':
            fixed = _repair_section_conflict(result, gene_idx, legacy)
        elif violation.constraint_type == 'faculty_qualification':
            fixed = _repair_qualification(result, gene_idx, config)
        elif violation.constraint_type == 'faculty_availability':
            fixed = _repair_availability(result, gene_idx, legacy)
        elif violation.constraint_type in ['room_type_mismatch', 'room_capacity_exceeded']:
            fixed = _repair_room_assignment(result, gene_idx, config)
        elif violation.constraint_type == 'operating_hours':
            fixed = _repair_operating_hours(result, gene_idx)

        if fixed:
            repairs_made += 1

    return result, repairs_made


def _repair_faculty_conflict(chromosome: List[Gene], gene_idx: int,
                             legacy: Dict[str, Any]) -> bool:
    """Try to fix faculty time conflict by moving to different time/day."""
    g = chromosome[gene_idx]
    prof_availability = legacy['prof_availability']

    # Get valid days for this faculty
    valid_days = prof_availability.get(g.professor, WEEKDAYS)
    if not valid_days:
        valid_days = WEEKDAYS

    # Try each day
    for day in random.sample(valid_days, len(valid_days)):
        # Get occupied slots for this faculty on this day
        occupied = set()
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            if other.professor == g.professor and other.day == day:
                occupied.update(range(other.start_slot, other.end_slot()))

        # Try all possible start times
        for start_slot in range(0, SLOTS_PER_DAY - g.duration + 1):
            gene_slots = set(range(start_slot, start_slot + g.duration))
            if not gene_slots.intersection(occupied):
                # Found a free slot
                g.day = day
                g.start_slot = start_slot
                return True

    return False


def _repair_room_conflict(chromosome: List[Gene], gene_idx: int,
                          config: FullGAConfig) -> bool:
    """Try to fix room conflict by changing room or moving time."""
    g = chromosome[gene_idx]
    legacy = extract_legacy_format_from_config(config)

    # Strategy 1: Try a different room on same day/time
    available_rooms = []
    for room_name in legacy['rooms']:
        if room_name == g.room or room_name == 'TBA':
            continue

        # Check if this room is free
        conflict = False
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            if other.room == room_name and other.day == g.day:
                other_slots = set(range(other.start_slot, other.end_slot()))
                gene_slots = set(range(g.start_slot, g.end_slot()))
                if other_slots.intersection(gene_slots):
                    conflict = True
                    break

        if not conflict:
            available_rooms.append(room_name)

    if available_rooms:
        g.room = random.choice(available_rooms)
        return True

    # Strategy 2: Keep room, try different time on same day
    if g.room and g.room != 'TBA':
        occupied = set()
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            if other.room == g.room and other.day == g.day:
                occupied.update(range(other.start_slot, other.end_slot()))

        for start_slot in range(0, SLOTS_PER_DAY - g.duration + 1):
            gene_slots = set(range(start_slot, start_slot + g.duration))
            if not gene_slots.intersection(occupied):
                g.start_slot = start_slot
                return True

    return False


def _repair_section_conflict(chromosome: List[Gene], gene_idx: int,
                             legacy: Dict[str, Any]) -> bool:
    """Try to fix section conflict by moving to different time/day."""
    g = chromosome[gene_idx]

    # Try each day
    for day in random.sample(WEEKDAYS, len(WEEKDAYS)):
        # Get occupied slots for this section on this day
        occupied = set()
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            if other.section == g.section and other.day == day:
                occupied.update(range(other.start_slot, other.end_slot()))

        # Try all possible start times
        for start_slot in range(0, SLOTS_PER_DAY - g.duration + 1):
            gene_slots = set(range(start_slot, start_slot + g.duration))
            if not gene_slots.intersection(occupied):
                g.day = day
                g.start_slot = start_slot
                return True

    return False


def _repair_qualification(chromosome: List[Gene], gene_idx: int,
                          config: FullGAConfig) -> bool:
    """Try to fix qualification mismatch by swapping with a qualified faculty."""
    g = chromosome[gene_idx]

    # Get qualified faculty for this course
    qualified = []
    if config.qualification_matrix:
        qualified = config.qualification_matrix.get_qualified_faculty(
            g.subj_code)
    else:
        qualified = config.subject_allocations.get(g.subj_code, [])

    if not qualified or g.professor in qualified:
        return False  # Already qualified or no alternatives

    # Try to swap with a qualified faculty member
    for qualified_prof in qualified:
        # Check if swapping would create conflicts
        conflict = False
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            if other.professor == qualified_prof and other.day == g.day:
                other_slots = set(range(other.start_slot, other.end_slot()))
                gene_slots = set(range(g.start_slot, g.end_slot()))
                if other_slots.intersection(gene_slots):
                    conflict = True
                    break

        if not conflict:
            g.professor = qualified_prof
            return True

    return False


def _repair_availability(chromosome: List[Gene], gene_idx: int,
                         legacy: Dict[str, Any]) -> bool:
    """Fix availability violation by moving to a day the faculty is available."""
    g = chromosome[gene_idx]
    prof_availability = legacy['prof_availability']

    valid_days = prof_availability.get(g.professor, [])
    if not valid_days or g.day in valid_days:
        return False  # Already valid or no availability data

    # Try to move to a valid day
    for day in random.sample(valid_days, len(valid_days)):
        # Check for conflicts on this day
        occupied = set()
        for i, other in enumerate(chromosome):
            if i == gene_idx:
                continue
            # Check faculty conflict
            if other.professor == g.professor and other.day == day:
                occupied.update(range(other.start_slot, other.end_slot()))
            # Check section conflict
            if other.section == g.section and other.day == day:
                occupied.update(range(other.start_slot, other.end_slot()))

        # Try to find a free slot
        for start_slot in range(0, SLOTS_PER_DAY - g.duration + 1):
            gene_slots = set(range(start_slot, start_slot + g.duration))
            if not gene_slots.intersection(occupied):
                g.day = day
                g.start_slot = start_slot
                return True

    return False


def _repair_room_assignment(chromosome: List[Gene], gene_idx: int,
                            config: FullGAConfig) -> bool:
    """Fix room type/capacity violation by assigning suitable room."""
    g = chromosome[gene_idx]

    # Determine required room type and capacity
    room_type_required = 'lecture'
    capacity_required = 30

    for subj in config.subjects:
        if subj.code == g.subj_code and subj.section == g.section:
            room_type_required = subj.room_type_required
            capacity_required = subj.section_student_count
            break

    # Find suitable rooms
    suitable_rooms = []
    for room in config.rooms:
        if room.room_type == room_type_required and room.capacity >= capacity_required:
            # Check if room is available at this time
            conflict = False
            for i, other in enumerate(chromosome):
                if i == gene_idx:
                    continue
                if (other.room == room.name or other.room == room.id) and other.day == g.day:
                    other_slots = set(
                        range(other.start_slot, other.end_slot()))
                    gene_slots = set(range(g.start_slot, g.end_slot()))
                    if other_slots.intersection(gene_slots):
                        conflict = True
                        break

            if not conflict:
                suitable_rooms.append(room.name)

    if suitable_rooms:
        g.room = random.choice(suitable_rooms)
        return True

    return False


def _repair_operating_hours(chromosome: List[Gene], gene_idx: int) -> bool:
    """Fix operating hours violation by moving to earlier time."""
    g = chromosome[gene_idx]

    # Move to earliest possible slot that fits
    max_start = SLOTS_PER_DAY - g.duration
    if max_start < 0:
        # Duration too long, can't fix
        return False

    # Try to move to earliest available slot
    g.start_slot = max(0, min(g.start_slot, max_start))
    return True


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY REPAIR PASS (kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════════════════

def repair_pass(chromosome: List[Gene],
                prof_availability: Dict[str, List[str]],
                rooms: List[str],
                teaching_loads: Dict[str, int],
                subject_allocations: Dict[str, List[str]],
                max_iterations: int = 200) -> List[Gene]:
    """
    LEGACY - Local search repair. Use repair_pass_v3() for new code.

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
# ASYNC EXECUTION WITH PROGRESS TRACKING
# ══════════════════════════════════════════════════════════════════════════════


# Global storage for active GA runs (in production, use Redis or database)
_active_ga_runs: Dict[str, Dict[str, Any]] = {}
_ga_runs_lock = threading.Lock()


@dataclass
class AsyncGAStatus:
    """Status of an async GA execution."""
    session_id: str
    status: str  # 'running', 'completed', 'failed', 'cancelled'
    progress: Optional[GAProgress] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: float = 0.0
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            'session_id': self.session_id,
            'status': self.status,
            'started_at': self.started_at,
        }

        if self.progress:
            data['progress'] = self.progress.to_dict()

        if self.completed_at:
            data['completed_at'] = self.completed_at
            data['elapsed_total'] = self.completed_at - self.started_at

        if self.result:
            data['result'] = self.result

        if self.error:
            data['error'] = self.error

        return data


def run_ga_async(config: FullGAConfig, session_id: str) -> str:
    """
    Start GA execution asynchronously in a background thread.

    Args:
        config: GA configuration
        session_id: Unique identifier for this run

    Returns:
        session_id for tracking
    """
    # Initialize status
    status = AsyncGAStatus(
        session_id=session_id,
        status='running',
        started_at=_time.time()
    )

    with _ga_runs_lock:
        _active_ga_runs[session_id] = {
            'status': status,
            'cancel_requested': False
        }

    # Start GA in background thread
    thread = threading.Thread(
        target=_run_ga_worker,
        args=(config, session_id),
        daemon=True
    )
    thread.start()

    return session_id


def _run_ga_worker(config: FullGAConfig, session_id: str):
    """Worker function that runs GA in background thread."""
    try:
        # Progress callback that updates status
        def progress_callback(progress: GAProgress):
            with _ga_runs_lock:
                if session_id in _active_ga_runs:
                    _active_ga_runs[session_id]['status'].progress = progress

                    # Check for cancellation
                    if _active_ga_runs[session_id]['cancel_requested']:
                        raise KeyboardInterrupt("GA run cancelled by user")

        # Run GA with progress tracking
        result = run_full_ga_v3(config, progress_callback=progress_callback)

        # Update status with result
        with _ga_runs_lock:
            if session_id in _active_ga_runs:
                _active_ga_runs[session_id]['status'].status = 'completed'
                _active_ga_runs[session_id]['status'].result = result
                _active_ga_runs[session_id]['status'].completed_at = _time.time()

    except KeyboardInterrupt:
        # Cancellation requested
        with _ga_runs_lock:
            if session_id in _active_ga_runs:
                _active_ga_runs[session_id]['status'].status = 'cancelled'
                _active_ga_runs[session_id]['status'].error = 'Cancelled by user'
                _active_ga_runs[session_id]['status'].completed_at = _time.time()

    except Exception as e:
        # Error occurred
        with _ga_runs_lock:
            if session_id in _active_ga_runs:
                _active_ga_runs[session_id]['status'].status = 'failed'
                _active_ga_runs[session_id]['status'].error = str(e)
                _active_ga_runs[session_id]['status'].completed_at = _time.time()


def get_ga_status(session_id: str) -> Optional[AsyncGAStatus]:
    """
    Get status of an async GA run.

    Args:
        session_id: Session identifier

    Returns:
        AsyncGAStatus or None if not found
    """
    with _ga_runs_lock:
        if session_id in _active_ga_runs:
            return _active_ga_runs[session_id]['status']
    return None


def cancel_ga_run(session_id: str) -> bool:
    """
    Request cancellation of a running GA.

    Args:
        session_id: Session identifier

    Returns:
        True if cancellation requested, False if session not found
    """
    with _ga_runs_lock:
        if session_id in _active_ga_runs:
            if _active_ga_runs[session_id]['status'].status == 'running':
                _active_ga_runs[session_id]['cancel_requested'] = True
                return True
    return False


def cleanup_old_ga_runs(max_age_seconds: float = 3600):
    """
    Clean up old completed GA runs from memory.

    Args:
        max_age_seconds: Remove runs older than this (default 1 hour)
    """
    current_time = _time.time()
    with _ga_runs_lock:
        sessions_to_remove = []
        for session_id, data in _active_ga_runs.items():
            status = data['status']
            if status.completed_at:
                age = current_time - status.completed_at
                if age > max_age_seconds:
                    sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            del _active_ga_runs[session_id]

    return len(sessions_to_remove)


def list_active_ga_runs() -> List[Dict[str, Any]]:
    """
    List all active GA runs.

    Returns:
        List of status dictionaries
    """
    with _ga_runs_lock:
        return [data['status'].to_dict() for data in _active_ga_runs.values()]


# Update chatbot integration to support async execution

def handle_chatbot_request_async(request: ChatbotRequest) -> ChatbotResponse:
    """
    Enhanced chatbot handler with async support.

    If request includes async=True in custom_params, starts async execution.
    Otherwise, runs synchronously (backward compatible).
    """
    # Check if async execution requested
    run_async = False
    if request.custom_params and request.custom_params.get('async', False):
        run_async = True

    # Generate session ID if not provided
    session_id = request.session_id
    if not session_id and run_async:
        import uuid
        session_id = str(uuid.uuid4())

    if request.action in ['generate', 'regenerate']:
        if run_async:
            # Start async execution
            config = _build_config_from_request(request)
            session_id = run_ga_async(config, session_id)

            return ChatbotResponse(
                success=True,
                action=request.action,
                message=f"GA execution started asynchronously. Session ID: {session_id}",
                status='running',
                progress={'session_id': session_id}
            )
        else:
            # Synchronous execution (existing behavior)
            if request.action == 'generate':
                return _handle_generate(request)
            else:
                return _handle_regenerate(request)

    elif request.action == 'get_status':
        # Get status of async run
        if not session_id:
            return ChatbotResponse(
                success=False,
                action='get_status',
                message="session_id required for get_status action",
                suggestions=["Provide session_id from async execution"]
            )

        status = get_ga_status(session_id)
        if not status:
            return ChatbotResponse(
                success=False,
                action='get_status',
                message=f"Session not found: {session_id}",
                suggestions=["Check session_id or run may have expired"]
            )

        # Build response based on status
        response_data = {
            'success': True,
            'action': 'get_status',
            'message': f"GA status: {status.status}",
            'status': status.status,
            'progress': status.to_dict()
        }

        # If completed, include results
        if status.status == 'completed' and status.result:
            response_data['schedules'] = status.result.get('schedules')
            response_data['fitness_breakdown'] = status.result.get(
                'fitness_breakdown')
            response_data['violation_report'] = status.result.get(
                'violation_report')
            response_data['faculty_loads'] = status.result.get('faculty_loads')
            response_data['termination_reason'] = status.result.get(
                'termination_reason')
            response_data['generations_run'] = status.result.get(
                'generations_run')
            response_data['elapsed_seconds'] = status.result.get(
                'elapsed_seconds')

        # If failed, include error
        if status.status == 'failed':
            response_data['error_details'] = {'error': status.error}

        return ChatbotResponse(**response_data)

    elif request.action == 'cancel':
        # Cancel running GA
        if not session_id:
            return ChatbotResponse(
                success=False,
                action='cancel',
                message="session_id required for cancel action",
                suggestions=["Provide session_id from async execution"]
            )

        cancelled = cancel_ga_run(session_id)
        if cancelled:
            return ChatbotResponse(
                success=True,
                action='cancel',
                message=f"Cancellation requested for session {session_id}",
                status='cancelling'
            )
        else:
            return ChatbotResponse(
                success=False,
                action='cancel',
                message=f"Cannot cancel session {session_id} (not found or not running)",
                suggestions=["Session may have already completed or cancelled"]
            )

    else:
        # Other actions handled by original handler
        return handle_chatbot_request(request)


# ══════════════════════════════════════════════════════════════════════════════
# CHATBOT INTEGRATION INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChatbotRequest:
    """Structured request from chatbot to GA system."""
    action: str  # 'generate', 'regenerate', 'explain', 'adjust_params', 'get_status'

    # For 'generate' and 'regenerate'
    subjects: Optional[List[Dict[str, Any]]] = None
    rooms: Optional[List[str]] = None
    faculty_availability: Optional[Dict[str, List[str]]] = None
    teaching_loads: Optional[Dict[str, int]] = None
    subject_allocations: Optional[Dict[str, List[str]]] = None
    reference_schedules: Optional[List[Dict[str, Any]]] = None
    faculty_overrides: Optional[Dict[str, Any]] = None

    # For 'adjust_params'
    config_preset: Optional[str] = None  # 'default', 'fast', 'quality'
    custom_params: Optional[Dict[str, Any]] = None

    # For 'regenerate'
    constraint_adjustments: Optional[Dict[str, Any]] = None

    # Session tracking
    session_id: Optional[str] = None


@dataclass
class ChatbotResponse:
    """Structured response from GA system to chatbot."""
    success: bool
    action: str
    message: str

    # For 'generate' and 'regenerate'
    schedules: Optional[List[Dict[str, Any]]] = None
    fitness_breakdown: Optional[Dict[str, Any]] = None
    violation_report: Optional[Dict[str, Any]] = None
    faculty_loads: Optional[Dict[str, float]] = None
    termination_reason: Optional[str] = None
    generations_run: Optional[int] = None
    elapsed_seconds: Optional[float] = None

    # For 'explain'
    config_explanation: Optional[Dict[str, Any]] = None

    # For 'get_status'
    status: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None

    # Error details
    error_details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'success': self.success,
            'action': self.action,
            'message': self.message,
        }

        if self.schedules is not None:
            result['schedules'] = self.schedules
        if self.fitness_breakdown is not None:
            result['fitness_breakdown'] = self.fitness_breakdown
        if self.violation_report is not None:
            result['violation_report'] = self.violation_report
        if self.faculty_loads is not None:
            result['faculty_loads'] = self.faculty_loads
        if self.termination_reason is not None:
            result['termination_reason'] = self.termination_reason
        if self.generations_run is not None:
            result['generations_run'] = self.generations_run
        if self.elapsed_seconds is not None:
            result['elapsed_seconds'] = self.elapsed_seconds
        if self.config_explanation is not None:
            result['config_explanation'] = self.config_explanation
        if self.status is not None:
            result['status'] = self.status
        if self.progress is not None:
            result['progress'] = self.progress
        if self.error_details is not None:
            result['error_details'] = self.error_details
        if self.suggestions is not None:
            result['suggestions'] = self.suggestions

        return result


def handle_chatbot_request(request: ChatbotRequest) -> ChatbotResponse:
    """
    Main entry point for chatbot integration.
    Handles all chatbot actions with proper validation and error handling.

    Supported actions:
    - 'generate': Create new schedule from scratch
    - 'regenerate': Regenerate with adjustments
    - 'explain': Explain current configuration
    - 'adjust_params': Update GA parameters
    - 'get_status': Get current GA run status (for async execution)
    """
    try:
        if request.action == 'generate':
            return _handle_generate(request)
        elif request.action == 'regenerate':
            return _handle_regenerate(request)
        elif request.action == 'explain':
            return _handle_explain(request)
        elif request.action == 'adjust_params':
            return _handle_adjust_params(request)
        elif request.action == 'get_status':
            return _handle_get_status(request)
        else:
            return ChatbotResponse(
                success=False,
                action=request.action,
                message=f"Unknown action: {request.action}",
                suggestions=[
                    'Valid actions: generate, regenerate, explain, adjust_params, get_status']
            )

    except Exception as e:
        return ChatbotResponse(
            success=False,
            action=request.action,
            message=f"Error processing request: {str(e)}",
            error_details={'exception': str(e), 'type': type(e).__name__}
        )


def _handle_generate(request: ChatbotRequest) -> ChatbotResponse:
    """Handle 'generate' action - create new schedule."""
    # Validate input
    if not request.subjects:
        return ChatbotResponse(
            success=False,
            action='generate',
            message="No subjects provided",
            suggestions=["Provide 'subjects' list with course information"]
        )

    # Build config
    config = _build_config_from_request(request)

    # Run GA
    result = run_full_ga_v3(config)

    if result['success']:
        return ChatbotResponse(
            success=True,
            action='generate',
            message=result['message'],
            schedules=result['schedules'],
            fitness_breakdown=result['fitness_breakdown'],
            violation_report=result['violation_report'],
            faculty_loads=result['faculty_loads'],
            termination_reason=result['termination_reason'],
            generations_run=result['generations_run'],
            elapsed_seconds=result['elapsed_seconds'],
        )
    else:
        return ChatbotResponse(
            success=False,
            action='generate',
            message=result.get('message', 'Generation failed'),
            error_details=result,
            suggestions=result.get('warnings', [])
        )


def _handle_regenerate(request: ChatbotRequest) -> ChatbotResponse:
    """Handle 'regenerate' action - regenerate with adjustments."""
    # Build config with adjustments
    config = _build_config_from_request(request)

    # Apply constraint adjustments if provided
    if request.constraint_adjustments:
        for key, value in request.constraint_adjustments.items():
            if hasattr(config, key):
                setattr(config, key, value)

    # Run GA
    result = run_full_ga_v3(config)

    adjustments_applied = list(request.constraint_adjustments.keys(
    )) if request.constraint_adjustments else []
    message_suffix = f" (applied adjustments: {', '.join(adjustments_applied)})" if adjustments_applied else ""

    if result['success']:
        return ChatbotResponse(
            success=True,
            action='regenerate',
            message=result['message'] + message_suffix,
            schedules=result['schedules'],
            fitness_breakdown=result['fitness_breakdown'],
            violation_report=result['violation_report'],
            faculty_loads=result['faculty_loads'],
            termination_reason=result['termination_reason'],
            generations_run=result['generations_run'],
            elapsed_seconds=result['elapsed_seconds'],
        )
    else:
        return ChatbotResponse(
            success=False,
            action='regenerate',
            message=result.get('message', 'Regeneration failed'),
            error_details=result,
            suggestions=result.get('warnings', [])
        )


def _handle_explain(request: ChatbotRequest) -> ChatbotResponse:
    """Handle 'explain' action - explain configuration."""
    config = _build_config_from_request(request)
    explanation = explain_ga_config(config)

    return ChatbotResponse(
        success=True,
        action='explain',
        message="Current GA configuration explained",
        config_explanation=explanation
    )


def _handle_adjust_params(request: ChatbotRequest) -> ChatbotResponse:
    """Handle 'adjust_params' action - update parameters."""
    # Start with preset if specified
    if request.config_preset == 'fast':
        config = create_fast_ga_config()
        message = "Parameters adjusted to 'fast' preset"
    elif request.config_preset == 'quality':
        config = create_quality_ga_config()
        message = "Parameters adjusted to 'quality' preset"
    else:
        config = create_default_ga_config()
        message = "Parameters adjusted to 'default' preset"

    # Apply custom params if provided
    if request.custom_params:
        config = update_config_from_dict(config, request.custom_params)
        custom_keys = ', '.join(request.custom_params.keys())
        message += f" with custom adjustments: {custom_keys}"

    explanation = explain_ga_config(config)

    return ChatbotResponse(
        success=True,
        action='adjust_params',
        message=message,
        config_explanation=explanation
    )


def _handle_get_status(request: ChatbotRequest) -> ChatbotResponse:
    """Handle 'get_status' action - get current execution status."""
    # This is a placeholder for async execution status
    # In Task #11, we'll implement actual status tracking
    return ChatbotResponse(
        success=True,
        action='get_status',
        message="Status tracking not yet implemented",
        status='not_implemented',
        suggestions=["This will be implemented in async execution (Task #11)"]
    )


def _build_config_from_request(request: ChatbotRequest) -> FullGAConfig:
    """Build FullGAConfig from chatbot request."""
    # Start with preset if specified, otherwise default
    if request.config_preset == 'fast':
        config = create_fast_ga_config()
    elif request.config_preset == 'quality':
        config = create_quality_ga_config()
    else:
        config = create_default_ga_config()

    # Apply custom params if provided
    if request.custom_params:
        config = update_config_from_dict(config, request.custom_params)

    # Set data from request
    if request.subjects:
        config.subjects = [SubjectInput(
            **s) if isinstance(s, dict) else s for s in request.subjects]

    if request.rooms:
        config.rooms_legacy = request.rooms

    if request.faculty_availability:
        config.prof_availability = request.faculty_availability

    if request.teaching_loads:
        config.teaching_loads = request.teaching_loads

    if request.subject_allocations:
        config.subject_allocations = request.subject_allocations

    if request.reference_schedules:
        config.reference_schedules = request.reference_schedules

    if request.faculty_overrides:
        config.faculty_overrides = request.faculty_overrides

    return config


def format_violation_report_for_chat(violation_report: Dict[str, Any]) -> str:
    """
    Format violation report as natural language for chatbot.

    Returns human-readable summary suitable for chat display.
    """
    if not violation_report:
        return "No violation report available."

    lines = []

    # Status
    if violation_report.get('is_feasible'):
        lines.append("✅ **Schedule is feasible!**")
        lines.append("All hard constraints are satisfied.")
    else:
        hard_count = violation_report.get('hard_violations', 0)
        lines.append(
            f"⚠️ **Schedule has {hard_count} hard constraint violations**")
        lines.append("These must be resolved for a valid schedule.")

    # Summary points
    if violation_report.get('summary'):
        lines.append("\n**Summary:**")
        for item in violation_report['summary']:
            lines.append(f"• {item}")

    # Violation details
    if violation_report.get('details'):
        lines.append("\n**Violation Details:**")
        for detail in violation_report['details'][:5]:  # Show top 5
            severity_icon = "🔴" if detail['severity'] == 'hard' else "🟡"
            lines.append(
                f"{severity_icon} **{detail['constraint']}**: {detail['count']} occurrence(s)")
            if detail.get('sample_message'):
                lines.append(f"   ↳ {detail['sample_message']}")

    return "\n".join(lines)


def suggest_improvements(violation_report: Dict[str, Any]) -> List[str]:
    """
    Analyze violation report and suggest improvements.

    Returns list of actionable suggestions for the user.
    """
    suggestions = []

    if not violation_report:
        return suggestions

    details = violation_report.get('details', [])

    # Analyze violations and provide targeted advice
    for detail in details:
        constraint = detail['constraint']
        count = detail['count']

        if 'faculty_time_conflict' in constraint:
            suggestions.append(
                f"Faculty time conflicts ({count}): Check if faculty availability is too restrictive. Consider allowing more days.")

        elif 'room_time_conflict' in constraint:
            suggestions.append(
                f"Room conflicts ({count}): More rooms may be needed, or spread classes across more time slots.")

        elif 'section_time_conflict' in constraint:
            suggestions.append(
                f"Section conflicts ({count}): Sections are overbooked. Review course requirements.")

        elif 'room_capacity' in constraint:
            suggestions.append(
                f"Room capacity issues ({count}): Assign larger rooms or split sections.")

        elif 'qualification' in constraint:
            suggestions.append(
                f"Qualification mismatches ({count}): Review faculty-course assignments. Add qualified faculty or adjust allocations.")

        elif 'minimum_load' in constraint:
            suggestions.append(
                f"Faculty under minimum load ({count}): Assign more courses to underloaded faculty.")

        elif 'maximum_load' in constraint:
            suggestions.append(
                f"Faculty over maximum load ({count}): Reduce assignments or increase max load limits.")

    # Add general suggestions if many violations
    total_violations = violation_report.get('total_violations', 0)
    if total_violations > 20:
        suggestions.append(
            "High violation count: Consider running with 'quality' preset for better optimization.")

    if not violation_report.get('is_feasible'):
        suggestions.append(
            "Try adjusting constraints or increasing time budget to allow more optimization.")

    return suggestions[:5]  # Return top 5 suggestions


# ══════════════════════════════════════════════════════════════════════════════
# GA CONFIGURATION BUILDER & PRESETS
# ══════════════════════════════════════════════════════════════════════════════

def create_default_ga_config() -> FullGAConfig:
    """
    Create a FullGAConfig with sensible default parameters.

    Returns a config that balances convergence speed and solution quality.
    Suitable for most scheduling problems.
    """
    return FullGAConfig(
        # Core data (to be filled by caller)
        subjects=[],
        rooms_legacy=[],

        # GA parameters - balanced defaults
        pop_size=100,
        max_generations=1000,
        time_limit_seconds=120.0,
        elitism_count=3,
        crossover_rate=0.8,
        mutation_rate=0.15,
        tournament_size=4,

        # Constraint weights - hard constraints heavily penalized
        weight_hard_violations=1000.0,
        weight_soft_violations=10.0,
        weight_faculty_conflicts=1000.0,
        weight_room_conflicts=1000.0,
        weight_section_conflicts=1000.0,
        weight_room_capacity=1000.0,
        weight_room_type_mismatch=1000.0,
        weight_min_load_violation=100.0,
        weight_max_load_violation=1000.0,
        weight_continuity_bonus=5.0,
        weight_load_balance=10.0,
        weight_gap_penalty=10.0,

        # Termination criteria - all enabled
        plateau_generations=50,
        feasibility_threshold=0.0,
        enable_plateau_detection=True,
        enable_time_budget=True,
    )


def create_fast_ga_config() -> FullGAConfig:
    """
    Create a FullGAConfig optimized for speed (good for testing/demos).

    Smaller population, fewer generations, but may produce lower-quality schedules.
    """
    config = create_default_ga_config()
    config.pop_size = 50
    config.max_generations = 300
    config.time_limit_seconds = 60.0
    config.plateau_generations = 30
    return config


def create_quality_ga_config() -> FullGAConfig:
    """
    Create a FullGAConfig optimized for solution quality.

    Larger population, more generations, stricter termination.
    Suitable for production schedules where quality matters most.
    """
    config = create_default_ga_config()
    config.pop_size = 150
    config.max_generations = 2000
    config.time_limit_seconds = 300.0
    config.plateau_generations = 100
    config.elitism_count = 5
    config.tournament_size = 5
    return config


def update_config_from_dict(config: FullGAConfig, params: Dict[str, Any]) -> FullGAConfig:
    """
    Update config parameters from a dictionary (useful for API/chatbot integration).

    Args:
        config: Base config to update
        params: Dictionary of parameter overrides

    Returns:
        Updated config

    Example:
        config = create_default_ga_config()
        config = update_config_from_dict(config, {
            'pop_size': 80,
            'max_generations': 500,
            'weight_continuity_bonus': 10.0
        })
    """
    for key, value in params.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


def explain_ga_config(config: FullGAConfig) -> Dict[str, Any]:
    """
    Generate human-readable explanation of config parameters.
    Useful for chatbot to explain current settings to users.

    Returns dict with parameter explanations and current values.
    """
    return {
        'algorithm_parameters': {
            'population_size': {
                'value': config.pop_size,
                'description': 'Number of candidate schedules in each generation',
                'recommendation': '50-150 (larger = more diversity, slower)'
            },
            'max_generations': {
                'value': config.max_generations,
                'description': 'Maximum evolutionary cycles before stopping',
                'recommendation': '500-2000 (more = better quality, longer runtime)'
            },
            'time_limit': {
                'value': config.time_limit_seconds,
                'description': 'Maximum runtime in seconds',
                'recommendation': '60-300s depending on urgency'
            },
            'elitism_count': {
                'value': config.elitism_count,
                'description': 'Top solutions preserved unchanged each generation',
                'recommendation': '2-5 (protects best solutions)'
            },
            'crossover_rate': {
                'value': config.crossover_rate,
                'description': 'Probability of combining two parent schedules',
                'recommendation': '0.7-0.9 (higher = more exploration)'
            },
            'mutation_rate': {
                'value': config.mutation_rate,
                'description': 'Probability of random changes per gene',
                'recommendation': '0.1-0.2 (higher = more randomness)'
            },
            'tournament_size': {
                'value': config.tournament_size,
                'description': 'Candidates competing in selection',
                'recommendation': '3-5 (higher = stronger selection pressure)'
            },
        },
        'termination_criteria': {
            'plateau_generations': {
                'value': config.plateau_generations,
                'enabled': config.enable_plateau_detection,
                'description': 'Stop if no improvement for N generations',
                'recommendation': '30-100 depending on patience'
            },
            'feasibility_threshold': {
                'value': config.feasibility_threshold,
                'description': 'Stop if score reaches this target (0 = perfect)',
                'recommendation': '0.0 for perfect solution'
            },
        },
        'constraint_priorities': {
            'hard_constraints': {
                'weight': config.weight_hard_violations,
                'description': 'Conflicts that make schedule invalid (faculty/room/section overlaps, qualifications, capacity)',
            },
            'soft_constraints': {
                'weight': config.weight_soft_violations,
                'description': 'Preferences to optimize (load balance, gaps, continuity)',
            },
            'continuity_bonus': {
                'weight': config.weight_continuity_bonus,
                'description': 'Reward for keeping same professor on same course as previous term',
            },
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# TERMINATION CRITERIA MANAGER
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TerminationState:
    """Tracks state for termination criteria evaluation."""
    best_score: float = float('inf')
    generations_without_improvement: int = 0
    start_time: float = 0.0
    current_generation: int = 0
    termination_reason: Optional[str] = None

    def should_terminate(self, config: FullGAConfig, current_score: float,
                         current_time: float, is_feasible: bool) -> Tuple[bool, str]:
        """
        Evaluate all termination criteria and determine if GA should stop.

        Returns: (should_stop, reason)
        """
        # Check time budget
        if config.enable_time_budget:
            elapsed = current_time - self.start_time
            if elapsed >= config.time_limit_seconds:
                return True, f"Time budget reached ({config.time_limit_seconds}s)"

        # Check max generations
        if self.current_generation >= config.max_generations:
            return True, f"Max generations reached ({config.max_generations})"

        # Check feasibility threshold (perfect solution found)
        if config.feasibility_threshold is not None:
            if current_score <= config.feasibility_threshold and is_feasible:
                return True, f"Feasibility threshold reached (score: {current_score:.2f})"

        # Check plateau detection
        if config.enable_plateau_detection:
            if self.generations_without_improvement >= config.plateau_generations:
                return True, f"Plateau detected ({config.plateau_generations} generations without improvement)"

        return False, ""

    def update(self, current_score: float, is_feasible: bool):
        """Update state after a generation."""
        self.current_generation += 1

        # Check for improvement (consider feasibility for tie-breaking)
        improvement_threshold = 0.01  # Ignore tiny fluctuations
        if current_score < self.best_score - improvement_threshold:
            self.best_score = current_score
            self.generations_without_improvement = 0
        else:
            self.generations_without_improvement += 1


@dataclass
class GAProgress:
    """Progress information for logging and UI updates."""
    generation: int
    best_score: float
    best_hard_penalty: float
    best_soft_penalty: float
    is_feasible: bool
    population_avg_score: float
    generations_without_improvement: int
    elapsed_seconds: float
    violations_by_type: Dict[str, int]
    repairs_made: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'generation': self.generation,
            'best_score': round(self.best_score, 2),
            'best_hard_penalty': round(self.best_hard_penalty, 2),
            'best_soft_penalty': round(self.best_soft_penalty, 2),
            'is_feasible': self.is_feasible,
            'population_avg_score': round(self.population_avg_score, 2),
            'generations_without_improvement': self.generations_without_improvement,
            'elapsed_seconds': round(self.elapsed_seconds, 2),
            'violations_by_type': self.violations_by_type,
            'repairs_made': self.repairs_made,
        }

    def format_summary(self) -> str:
        """Format as human-readable summary string."""
        status = "✓ Feasible" if self.is_feasible else "✗ Infeasible"
        return (f"Gen {self.generation}: {status} | "
                f"Score: {self.best_score:.1f} "
                f"(H:{self.best_hard_penalty:.0f} S:{self.best_soft_penalty:.1f}) | "
                f"Stale: {self.generations_without_improvement} | "
                f"Time: {self.elapsed_seconds:.1f}s")


# ══════════════════════════════════════════════════════════════════════════════
# FULL SCHEDULE GENERATION (Main Entry Point - Enhanced v3)
# ══════════════════════════════════════════════════════════════════════════════

def run_full_ga_v3(config: FullGAConfig, progress_callback=None) -> Dict:
    """
    Enhanced full semester schedule generation with comprehensive features.

    Args:
        config: Complete GA configuration
        progress_callback: Optional function(GAProgress) called after each generation

    Returns dict with:
        success, message, schedules, fitness_breakdown, generations_run,
        termination_reason, faculty_loads, warnings, elapsed_seconds,
        progress_log, violation_report
    """
    # Initialize termination state
    term_state = TerminationState(start_time=_time.time())
    warnings = []
    progress_log = []

    # Ensure config has comprehensive models
    config = legacy_config_to_new_format(config)

    # Validate
    if not config.subjects:
        return {
            'success': False,
            'message': 'No subjects provided.',
            'schedules': [],
            'warnings': ['No subject data to generate from.']
        }

    # Prepare subjects (same as legacy)
    subjects_for_ga = []
    for subj in config.subjects:
        prof_list = subj.allocated_professors or config.subject_allocations.get(
            subj.code, [])
        if not prof_list:
            warnings.append(
                f"{subj.code} has no allocated professor — skipping")
            continue

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
        return {
            'success': False,
            'message': 'No subjects with allocated professors.',
            'schedules': [],
            'warnings': warnings
        }

    # Get legacy format for compatibility
    legacy = extract_legacy_format_from_config(config)
    rooms = legacy['rooms']
    prof_availability = legacy['prof_availability']

    # Build initial population
    population = []

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

    while len(population) < config.pop_size:
        population.append(build_chromosome(
            subjects_for_ga, rooms, prof_availability))

    # GA Loop with enhanced features
    best_chrom = None
    best_breakdown = None
    initial_mutation_rate = config.mutation_rate
    min_mutation_rate = config.mutation_rate * 0.5
    total_repairs = 0

    while True:
        current_time = _time.time()

        # Evaluate fitness using v3
        fitness_breakdowns = [fitness_v3(c, config) for c in population]

        # Track best
        gen_best_idx = min(range(len(fitness_breakdowns)),
                           key=lambda i: fitness_breakdowns[i].total_score)
        gen_best_breakdown = fitness_breakdowns[gen_best_idx]

        if best_breakdown is None or gen_best_breakdown.total_score < best_breakdown.total_score:
            best_breakdown = gen_best_breakdown
            best_chrom = copy.deepcopy(population[gen_best_idx])

        # Update termination state
        term_state.update(best_breakdown.total_score,
                          best_breakdown.is_feasible)

        # Calculate population average
        pop_avg = sum(fb.total_score for fb in fitness_breakdowns) / \
            len(fitness_breakdowns)

        # Create progress report
        progress = GAProgress(
            generation=term_state.current_generation,
            best_score=best_breakdown.total_score,
            best_hard_penalty=best_breakdown.hard_penalty,
            best_soft_penalty=best_breakdown.soft_penalty,
            is_feasible=best_breakdown.is_feasible,
            population_avg_score=pop_avg,
            generations_without_improvement=term_state.generations_without_improvement,
            elapsed_seconds=current_time - term_state.start_time,
            violations_by_type=best_breakdown.violation_count_by_type,
        )
        progress_log.append(progress.to_dict())

        # Call progress callback if provided
        if progress_callback:
            progress_callback(progress)

        # Check termination criteria
        should_stop, reason = term_state.should_terminate(
            config, best_breakdown.total_score, current_time, best_breakdown.is_feasible
        )

        if should_stop:
            term_state.termination_reason = reason
            break

        # Adaptive mutation rate
        progress_ratio = term_state.current_generation / \
            max(config.max_generations, 1)
        mutation_rate = initial_mutation_rate - \
            (initial_mutation_rate - min_mutation_rate) * progress_ratio

        # Use targeted mutation if stuck (plateau for >20 generations)
        use_targeted = term_state.generations_without_improvement > 20

        # Build next generation with elitism
        sorted_indices = sorted(range(len(fitness_breakdowns)),
                                key=lambda i: fitness_breakdowns[i].total_score)
        next_gen = []

        # Elitism: preserve best N solutions
        for i in range(min(config.elitism_count, len(sorted_indices))):
            next_gen.append(copy.deepcopy(population[sorted_indices[i]]))

        # Generate offspring
        while len(next_gen) < config.pop_size:
            if random.random() < config.crossover_rate:
                p1 = tournament_select_v3(
                    population, fitness_breakdowns, config)
                p2 = tournament_select_v3(
                    population, fitness_breakdowns, config)
                child = crossover_v3(p1, p2, method='mixed')
            else:
                # No crossover, just select one parent
                child = copy.deepcopy(tournament_select_v3(
                    population, fitness_breakdowns, config))

            # Mutation
            child = mutate_v3(
                child, config, rate=mutation_rate, targeted=use_targeted)

            # Optional repair pass (only if many violations)
            if use_targeted and random.random() < 0.3:
                child, repairs = repair_pass_v3(
                    child, config, max_iterations=50)
                total_repairs += repairs

            next_gen.append(child)

        population = next_gen

    # Final repair pass if needed
    if best_breakdown.hard_penalty > 0:
        best_chrom, repairs = repair_pass_v3(
            best_chrom, config, max_iterations=300)
        total_repairs += repairs
        # Re-evaluate after repair
        best_breakdown = fitness_v3(best_chrom, config)

    # Calculate faculty loads
    faculty_loads: Dict[str, float] = {}
    for g in best_chrom:
        if g.professor not in faculty_loads:
            faculty_loads[g.professor] = 0
        faculty_loads[g.professor] += g.units

    # Generate violation report for chatbot
    violation_report = _generate_violation_report(
        best_breakdown, faculty_loads, config)

    elapsed = _time.time() - term_state.start_time

    return {
        'success': True,
        'message': f"Generated {len(best_chrom)} entries in {elapsed:.1f}s. {term_state.termination_reason}",
        'schedules': [g.to_dict() for g in best_chrom],
        'fitness_breakdown': best_breakdown.to_dict(),
        'generations_run': term_state.current_generation,
        'termination_reason': term_state.termination_reason,
        'faculty_loads': faculty_loads,
        'warnings': warnings,
        'elapsed_seconds': round(elapsed, 2),
        'progress_log': progress_log,
        'violation_report': violation_report,
        'total_repairs_made': total_repairs,
    }


def _generate_violation_report(breakdown: FitnessBreakdown, faculty_loads: Dict[str, float],
                               config: FullGAConfig) -> Dict[str, Any]:
    """Generate human-readable violation report for chatbot."""
    report = {
        'is_feasible': breakdown.is_feasible,
        'total_violations': len(breakdown.hard_violations) + len(breakdown.soft_violations),
        'hard_violations': len(breakdown.hard_violations),
        'soft_violations': len(breakdown.soft_violations),
        'summary': [],
        'details': [],
    }

    # Summary
    if breakdown.is_feasible:
        report['summary'].append(
            "✓ Schedule is feasible (no hard constraint violations)")
    else:
        report['summary'].append(
            f"✗ Schedule has {len(breakdown.hard_violations)} hard constraint violations")

    if breakdown.soft_violations:
        report['summary'].append(
            f"⚠ {len(breakdown.soft_violations)} soft constraint issues")

    # Group violations by type
    violation_groups: Dict[str, List[ConstraintViolation]] = {}
    for v in breakdown.hard_violations + breakdown.soft_violations:
        if v.constraint_type not in violation_groups:
            violation_groups[v.constraint_type] = []
        violation_groups[v.constraint_type].append(v)

    # Generate details
    for constraint_type, violations in violation_groups.items():
        count = len(violations)
        severity = violations[0].severity
        report['details'].append({
            'constraint': constraint_type,
            'severity': severity,
            'count': count,
            'sample_message': violations[0].message if violations else '',
        })

    # Faculty load summary
    underloaded = [f for f, load in faculty_loads.items() if load < 12]
    overloaded = []
    for f in config.faculty:
        load = faculty_loads.get(f.id, 0) or faculty_loads.get(f.name, 0)
        if load > f.max_units:
            overloaded.append(f.name)

    if underloaded:
        report['summary'].append(
            f"⚠ {len(underloaded)} faculty below 12-unit minimum")
    if overloaded:
        report['summary'].append(
            f"⚠ {len(overloaded)} faculty exceed maximum load")

    return report


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY FULL SCHEDULE GENERATION (kept for backward compatibility)
# ══════════════════════════════════════════════════════════════════════════════

def run_full_ga(config: FullGAConfig) -> Dict:
    """
    LEGACY - Full semester schedule generation. Use run_full_ga_v3() for new code.

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

    # Normalize for case-insensitive matching
    professor_lower = professor.lower().strip()
    room_lower = room.lower().strip()
    section_lower = section.lower().strip()

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
            # Professor conflict (case-insensitive)
            if (s.get('prof') or '').lower().strip() == professor_lower:
                prof_occ.add(key)
            # Room conflict (case-insensitive, skip TBA)
            if room_lower and room_lower != 'tba' and (s.get('room') or '').lower().strip() == room_lower:
                room_occ.add(key)
            # Section conflict (case-insensitive)
            if section_lower and (s.get('section') or '').lower().strip() == section_lower:
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
