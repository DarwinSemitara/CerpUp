"""
NLP Service for Schedule Assistant
Processes natural language commands and extracts scheduling intents
"""

import re
from typing import Dict, List, Optional, Tuple


class ScheduleIntent:
    """Represents a parsed scheduling intent"""

    # Intent types
    ADD_SCHEDULE = "add_schedule"
    REMOVE_SCHEDULE = "remove_schedule"
    MOVE_SCHEDULE = "move_schedule"
    GENERATE_FULL = "generate_full"
    SHOW_CONFLICTS = "show_conflicts"
    MODIFY_CONSTRAINT = "modify_constraint"
    QUERY_INFO = "query_info"
    QUERY_SCHEDULE_BY_DAY = "query_schedule_by_day"
    QUERY_FREE_SLOTS = "query_free_slots"
    QUERY_FACULTY_LOAD = "query_faculty_load"
    QUERY_FACULTY_SCHEDULE = "query_faculty_schedule"
    QUERY_FACULTY_FREE_TIME = "query_faculty_free_time"
    UNKNOWN = "unknown"

    def __init__(self, intent_type: str, confidence: float = 1.0, **params):
        self.intent_type = intent_type
        self.confidence = confidence
        self.params = params

    def to_dict(self):
        return {
            'intent': self.intent_type,
            'confidence': self.confidence,
            'params': self.params
        }


class NLPProcessor:
    """Natural Language Processor for schedule commands"""

    def __init__(self):
        # Days of week patterns
        self.days = {
            'monday': 'Monday', 'mon': 'Monday',
            'tuesday': 'Tuesday', 'tue': 'Tuesday', 'tues': 'Tuesday',
            'wednesday': 'Wednesday', 'wed': 'Wednesday',
            'thursday': 'Thursday', 'thu': 'Thursday', 'thur': 'Thursday', 'thurs': 'Thursday',
            'friday': 'Friday', 'fri': 'Friday',
            'saturday': 'Saturday', 'sat': 'Saturday',
            'sunday': 'Sunday', 'sun': 'Sunday'
        }

        # Time of day patterns
        self.time_periods = {
            'morning': ('7:00', '12:00'),
            'mornings': ('7:00', '12:00'),
            'afternoon': ('12:00', '17:00'),
            'afternoons': ('12:00', '17:00'),
            'evening': ('17:00', '21:00'),
            'evenings': ('17:00', '21:00')
        }

    def process(self, message: str) -> ScheduleIntent:
        """
        Process a natural language message and extract intent

        Args:
            message: User's natural language input

        Returns:
            ScheduleIntent object with parsed intent and parameters
        """
        message_lower = message.lower().strip()

        # Check for generate full schedule
        if self._is_generate_intent(message_lower):
            return self._parse_generate_intent(message_lower)

        # Check for add schedule
        if self._is_add_intent(message_lower):
            return self._parse_add_intent(message_lower)

        # Check for remove schedule
        if self._is_remove_intent(message_lower):
            return self._parse_remove_intent(message_lower)

        # Check for move schedule
        if self._is_move_intent(message_lower):
            return self._parse_move_intent(message_lower)

        # Check for show conflicts
        if self._is_conflict_intent(message_lower):
            return ScheduleIntent(ScheduleIntent.SHOW_CONFLICTS)

        # Check for constraint modification
        if self._is_constraint_intent(message_lower):
            return self._parse_constraint_intent(message_lower)

        # Check for query/info request
        if self._is_query_intent(message_lower):
            return self._parse_query_intent(message_lower)

        # Unknown intent
        return ScheduleIntent(ScheduleIntent.UNKNOWN, confidence=0.0)

    # ═══ Intent Detection ═══

    def _is_generate_intent(self, msg: str) -> bool:
        keywords = ['generate', 'create full', 'make schedule', 'build schedule',
                    'full schedule', 'complete schedule', 'entire schedule']
        return any(kw in msg for kw in keywords)

    def _is_add_intent(self, msg: str) -> bool:
        keywords = ['add', 'create', 'schedule', 'insert', 'place', 'put']
        # Must have add-related keyword and subject/class reference
        has_action = any(kw in msg for kw in keywords)
        has_subject = any(word in msg for word in [
                          'class', 'subject', 'course', 'enrp', 'professor', 'prof'])
        return has_action and has_subject

    def _is_remove_intent(self, msg: str) -> bool:
        keywords = ['remove', 'delete', 'cancel', 'drop', 'clear']
        return any(kw in msg for kw in keywords)

    def _is_move_intent(self, msg: str) -> bool:
        keywords = ['move', 'shift', 'change', 'reschedule', 'transfer']
        return any(kw in msg for kw in keywords)

    def _is_conflict_intent(self, msg: str) -> bool:
        keywords = ['conflict', 'overlap', 'clash', 'double book', 'problem']
        return any(kw in msg for kw in keywords)

    def _is_constraint_intent(self, msg: str) -> bool:
        keywords = ['no class', 'avoid', 'prefer',
                    'constraint', 'must', 'should', 'cannot']
        return any(kw in msg for kw in keywords)

    def _is_query_intent(self, msg: str) -> bool:
        keywords = ['show', 'list', 'what',
                    'when', 'who', 'how many', 'tell me',
                    'display', 'free', 'available', 'schedule', 'units', 'load']
        return any(kw in msg for kw in keywords)

    # ═══ Intent Parsing ═══

    def _parse_generate_intent(self, msg: str) -> ScheduleIntent:
        """Parse generate full schedule intent"""
        return ScheduleIntent(
            ScheduleIntent.GENERATE_FULL,
            confidence=0.9
        )

    def _parse_add_intent(self, msg: str) -> ScheduleIntent:
        """Parse add schedule intent"""
        params = {}

        # Extract professor name
        prof_match = re.search(
            r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
        if prof_match:
            params['professor'] = prof_match.group(1).strip().title()

        # Extract subject code (e.g., ENRP 101)
        subj_match = re.search(r'\b([A-Z]{3,4}\s*\d{3})\b', msg, re.IGNORECASE)
        if subj_match:
            params['subject_code'] = subj_match.group(1).upper()

        # Extract day
        day = self._extract_day(msg)
        if day:
            params['day'] = day

        # Extract time
        time = self._extract_time(msg)
        if time:
            params['time'] = time

        # Extract room
        room_match = re.search(r'room\s*(\d+)', msg, re.IGNORECASE)
        if room_match:
            params['room'] = f"Room {room_match.group(1)}"

        confidence = 0.7 if params else 0.5
        return ScheduleIntent(ScheduleIntent.ADD_SCHEDULE, confidence=confidence, **params)

    def _parse_remove_intent(self, msg: str) -> ScheduleIntent:
        """Parse remove schedule intent"""
        params = {}

        # Extract professor
        prof_match = re.search(
            r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
        if prof_match:
            params['professor'] = prof_match.group(1).strip().title()

        # Extract subject
        subj_match = re.search(r'\b([A-Z]{3,4}\s*\d{3})\b', msg, re.IGNORECASE)
        if subj_match:
            params['subject_code'] = subj_match.group(1).upper()

        # Extract day
        day = self._extract_day(msg)
        if day:
            params['day'] = day

        confidence = 0.8 if params else 0.5
        return ScheduleIntent(ScheduleIntent.REMOVE_SCHEDULE, confidence=confidence, **params)

    def _parse_move_intent(self, msg: str) -> ScheduleIntent:
        """Parse move schedule intent"""
        params = {}

        # Extract professor
        prof_match = re.search(
            r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
        if prof_match:
            params['professor'] = prof_match.group(1).strip().title()

        # Extract subject
        subj_match = re.search(r'\b([A-Z]{3,4}\s*\d{3})\b', msg, re.IGNORECASE)
        if subj_match:
            params['subject_code'] = subj_match.group(1).upper()

        # Extract target day
        day = self._extract_day(msg)
        if day:
            params['target_day'] = day

        # Extract target time period
        for period, (start, end) in self.time_periods.items():
            if period in msg:
                params['target_time_period'] = period
                params['target_time_start'] = start
                params['target_time_end'] = end
                break

        confidence = 0.8 if params else 0.5
        return ScheduleIntent(ScheduleIntent.MOVE_SCHEDULE, confidence=confidence, **params)

    def _parse_constraint_intent(self, msg: str) -> ScheduleIntent:
        """Parse constraint modification intent"""
        params = {}

        # No class on specific day
        if 'no class' in msg or 'avoid' in msg:
            day = self._extract_day(msg)
            if day:
                params['constraint_type'] = 'no_class_on_day'
                params['day'] = day

        # Prefer time period
        for period in self.time_periods:
            if period in msg and ('prefer' in msg or 'want' in msg):
                params['constraint_type'] = 'prefer_time_period'
                params['time_period'] = period
                break

        confidence = 0.7 if params else 0.4
        return ScheduleIntent(ScheduleIntent.MODIFY_CONSTRAINT, confidence=confidence, **params)

    def _parse_query_intent(self, msg: str) -> ScheduleIntent:
        """Parse query/info request intent"""
        params = {}

        # Check for specific query types with higher priority

        # Query: Faculty load/units
        if any(word in msg for word in ['how many units', 'units does', 'teaching load', 'load of', 'units of']):
            params['query_type'] = 'faculty_load'
            # Extract faculty name - match capitalized words
            prof_match = re.search(
                r'(?:does|of)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', msg, re.IGNORECASE)
            if prof_match:
                params['faculty_name'] = prof_match.group(1).strip().title()
            return ScheduleIntent(ScheduleIntent.QUERY_FACULTY_LOAD, confidence=0.9, **params)

        # Query: Faculty free time
        if any(word in msg for word in ['when is', 'what time', 'when are']) and any(word in msg for word in ['free', 'available']):
            params['query_type'] = 'faculty_free_time'
            # Extract faculty name - more flexible pattern to catch full names
            # Pattern: any capitalized words before "free" or "available"
            prof_match = re.search(
                r'(?:is|are|does)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:free|available)', msg, re.IGNORECASE)
            if not prof_match:
                # Try alternate pattern: after "of" or "for"
                prof_match = re.search(
                    r'(?:of|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', msg, re.IGNORECASE)
            if prof_match:
                params['faculty_name'] = prof_match.group(1).strip().title()
            day = self._extract_day(msg)
            if day:
                params['day'] = day
            return ScheduleIntent(ScheduleIntent.QUERY_FACULTY_FREE_TIME, confidence=0.9, **params)

        # Query: Faculty schedule
        if any(word in msg for word in ['schedule of', 'schedule for', 'classes of']) and ('professor' in msg or 'prof' in msg or 'teacher' in msg):
            params['query_type'] = 'faculty_schedule'
            # Extract faculty name
            prof_match = re.search(
                r'(?:of|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', msg, re.IGNORECASE)
            if prof_match:
                params['faculty_name'] = prof_match.group(1).strip().title()
            day = self._extract_day(msg)
            if day:
                params['day'] = day
            return ScheduleIntent(ScheduleIntent.QUERY_FACULTY_SCHEDULE, confidence=0.9, **params)

        # Query: Schedule by day
        day = self._extract_day(msg)
        if day and any(word in msg for word in ['what', 'show', 'list', 'schedule', 'classes']):
            params['query_type'] = 'schedule_by_day'
            params['day'] = day
            # Check if asking about a specific time
            time_match = re.search(
                r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', msg, re.IGNORECASE)
            if time_match:
                params['time'] = self._extract_time(msg)
            return ScheduleIntent(ScheduleIntent.QUERY_SCHEDULE_BY_DAY, confidence=0.9, **params)

        # Query: Free slots/time
        if any(word in msg for word in ['free', 'available', 'vacant', 'empty']) and any(word in msg for word in ['slot', 'time', 'period', 'room']):
            params['query_type'] = 'free_slots'
            day = self._extract_day(msg)
            if day:
                params['day'] = day
            # Check for time period
            for period, (start, end) in self.time_periods.items():
                if period in msg:
                    params['time_period'] = period
                    break
            return ScheduleIntent(ScheduleIntent.QUERY_FREE_SLOTS, confidence=0.9, **params)

        # Fallback to old logic for conflicts and general queries
        if 'conflict' in msg or 'overlap' in msg:
            params['query_type'] = 'conflicts'
        elif 'professor' in msg or 'prof' in msg:
            params['query_type'] = 'professor_schedule'
            prof_match = re.search(
                r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
            if prof_match:
                params['professor'] = prof_match.group(1).strip().title()
        elif 'room' in msg:
            params['query_type'] = 'room_usage'
        else:
            params['query_type'] = 'general'

        return ScheduleIntent(ScheduleIntent.QUERY_INFO, confidence=0.6, **params)

    # ═══ Helper Methods ═══

    def _extract_day(self, msg: str) -> Optional[str]:
        """Extract day of week from message"""
        for key, day in self.days.items():
            if key in msg:
                return day
        return None

    def _extract_time(self, msg: str) -> Optional[str]:
        """Extract time from message"""
        # Match time patterns like "8:00", "8am", "8:00 AM"
        time_match = re.search(
            r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', msg, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = time_match.group(2) or '00'
            period = time_match.group(3)

            # Convert to 24-hour format if needed
            if period:
                if period.lower() == 'pm' and hour < 12:
                    hour += 12
                elif period.lower() == 'am' and hour == 12:
                    hour = 0

            return f"{hour}:{minute}"

        return None


# Global NLP processor instance
nlp_processor = NLPProcessor()


def process_message(message: str) -> Dict:
    """
    Process a natural language message

    Args:
        message: User's natural language input

    Returns:
        Dictionary with intent and parameters
    """
    intent = nlp_processor.process(message)
    return intent.to_dict()


def generate_human_response_for_schedules(schedules: List[Dict], query_type: str, params: Dict) -> str:
    """
    Generate human-like plain text response for schedule queries

    Args:
        schedules: List of schedule dictionaries
        query_type: Type of query (schedule_by_day, faculty_load, etc.)
        params: Query parameters

    Returns:
        Human-readable plain text response
    """
    if not schedules:
        return "I couldn't find any schedules matching your query."

    if query_type == 'schedule_by_day':
        day = params.get('day', 'that day')
        response = f"Here's what's scheduled for {day}:\n\n"
        for sched in schedules:
            response += f"• {sched.get('subjCode', 'Unknown')} - {sched.get('subjName', '')} with {sched.get('prof', 'TBA')} at {sched.get('start', '')} to {sched.get('end', '')} in {sched.get('room', 'TBA')}\n"
        return response

    elif query_type == 'faculty_schedule':
        faculty_name = params.get('faculty_name', 'this faculty member')
        day = params.get('day')
        if day:
            response = f"{faculty_name} has these classes on {day}:\n\n"
        else:
            response = f"Here's {faculty_name}'s schedule:\n\n"

        for sched in schedules:
            response += f"• {sched.get('day', 'TBA')} {sched.get('start', '')} - {sched.get('end', '')}: {sched.get('subjCode', '')} {sched.get('section', '')} in {sched.get('room', 'TBA')}\n"
        return response

    elif query_type == 'faculty_load':
        faculty_name = params.get('faculty_name', 'this faculty member')
        # Calculate total units
        total_units = sum(float(sched.get('units', 0)) for sched in schedules)
        response = f"{faculty_name} is teaching {total_units} units this semester.\n\nBreakdown:\n"
        for sched in schedules:
            response += f"• {sched.get('subjCode', '')} {sched.get('section', '')} - {sched.get('units', 0)} units\n"
        return response

    elif query_type == 'free_slots':
        day = params.get('day', 'that day')
        # This would need more complex logic to find free slots
        # For now, return a simple message
        return f"Based on the current schedule for {day}, I can help identify free time slots. This feature calculates available periods between classes."

    else:
        # Generic response
        response = f"I found {len(schedules)} schedule(s):\n\n"
        for sched in schedules:
            response += f"• {sched.get('day', 'TBA')} {sched.get('start', '')} - {sched.get('end', '')}: {sched.get('subjCode', '')} with {sched.get('prof', '')}\n"
        return response


def generate_human_response_for_free_time(faculty_name: str, free_periods: List[Dict], day: str = None, has_schedules: bool = True) -> str:
    """
    Generate human-like response for faculty free time queries

    Args:
        faculty_name: Name of faculty member
        free_periods: List of free time periods
        day: Optional specific day
        has_schedules: Whether faculty has any schedules on that day

    Returns:
        Human-readable plain text response
    """
    if not has_schedules:
        if day:
            return f"{faculty_name} doesn't have any classes scheduled on {day}, so their entire day is free."
        else:
            return f"{faculty_name} doesn't have any classes scheduled, so they're completely free."

    if not free_periods:
        if day:
            return f"{faculty_name} appears to be fully booked on {day} with back-to-back classes. They don't have any free periods between classes that day."
        else:
            return f"{faculty_name} has a packed schedule with back-to-back classes. I couldn't find any significant free periods between their classes."

    if day:
        response = f"{faculty_name} is free on {day} during:\n\n"
    else:
        response = f"Here's when {faculty_name} is available:\n\n"

    for period in free_periods:
        response += f"- {period.get('day', '')} from {period.get('start', '')} to {period.get('end', '')}\n"

    return response
