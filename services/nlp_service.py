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
        has_subject = any(word in msg for word in ['class', 'subject', 'course', 'enrp', 'professor', 'prof'])
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
        keywords = ['no class', 'avoid', 'prefer', 'constraint', 'must', 'should', 'cannot']
        return any(kw in msg for kw in keywords)
    
    def _is_query_intent(self, msg: str) -> bool:
        keywords = ['show', 'list', 'what', 'when', 'who', 'how many', 'tell me']
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
        prof_match = re.search(r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
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
        prof_match = re.search(r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
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
        prof_match = re.search(r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
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
        
        if 'conflict' in msg or 'overlap' in msg:
            params['query_type'] = 'conflicts'
        elif 'professor' in msg or 'prof' in msg:
            params['query_type'] = 'professor_schedule'
            prof_match = re.search(r'(?:prof(?:essor)?|dr\.?)\s+([a-z]+(?:\s+[a-z]+)?)', msg, re.IGNORECASE)
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
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', msg, re.IGNORECASE)
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
