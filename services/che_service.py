"""
CHE (CERP AI Assistant) Service
Uses Groq API with Llama 3.3 70B for full language understanding.
Responses are restricted to CERP-related topics only.
Now integrated with Genetic Algorithm scheduling capabilities.
"""

import os
import json
import logging
from typing import Optional
from groq import Groq

logger = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────────

# Base system prompt for ALL conversations
BASE_SYSTEM_PROMPT = """You are CHE, the official AI assistant for CERP (Center for Extension and Research in the Philippines), specifically for the CERP 2.0 management system used by the College of Human Ecology (CHE) at UPLB.

Your role is to help administrators and members with anything related to the CERP system and its data.

## THINKING PROCESS (follow this for every request):
1. **Understand**: What exactly is the user asking? Identify the core intent.
2. **Check data**: Look at the system data provided in context. What do you actually know?
3. **Plan**: Before acting, think about what steps are needed. If scheduling, consider conflicts.
4. **Validate**: Before outputting an action, verify you have ALL required parameters.
5. **Conflict check**: For ANY scheduling action, mentally check: Is the professor free? Is the room free? Is the section free at that time? If you see a conflict in the data, TELL the user and suggest alternatives.
6. **Respond**: Be specific with names, numbers, and details from the data — never guess.

## What you CAN help with:
- Research projects, publications, and papers submitted to the system
- Faculty members, staff, and student researchers — their profiles, roles, and activities
- Extension programs, community services, and outreach activities
- Faculty Study Report (FSR) — generation, contents, status, and interpretation
- Class schedules, academic calendars, and time management queries
- News and events posted in the system
- TAP (Technical Assistance Program) and HSP (Health Services Program) projects
- System navigation — how to use features, where to find data, what buttons do
- General academic and research workflow guidance within CHE/UPLB context
- Summarizing, counting, comparing, or analyzing data already in the system
- Any question about members, submissions, deadlines, or records in CERP

## What you CANNOT help with:
- Topics completely unrelated to CERP, CHE, or academic/research work at UPLB
- General knowledge questions (science trivia, geography, cooking, etc.)
- Personal advice, entertainment, or unrelated technical support
- Anything outside the domain of this system and its users

## When a user asks something off-topic:
Politely decline and redirect them. Use a short message like:
"That's outside what I can help with here. I'm focused on CERP system topics — research, members, schedules, FSRs, and extension activities. Try asking me something about the system!"

## Tone and style:
- Professional but approachable
- Concise and clear — avoid unnecessary filler
- Use bullet points or numbered lists when listing multiple items
- When you don't have specific data, say so clearly and suggest where to find it
- You understand Filipino/Tagalog mixed with English (code-switching) — respond in whatever language the user uses

## Important:
- When data is passed in context (members list, research records, schedules, etc.), use it to give accurate answers
- Never fabricate specific names, numbers, or records — only use what is provided
- If asked about something you need data for but none was provided, ask the admin to check the relevant section
"""

# System prompt for the SCHEDULE GENERATION conversation only
SCHEDULE_SYSTEM_PROMPT = """You are CHE, the official AI assistant for CERP (Center for Extension and Research in the Philippines).

**IMPORTANT: You are in the SCHEDULE GENERATION conversation. Your ONLY responsibility here is schedule generation and optimization.**

## What you CAN do in this conversation:
- Generate class schedules using the Genetic Algorithm
- Detect scheduling conflicts (professor, room, section overlaps)
- Add new schedule blocks to the timetable
- Move existing schedule blocks to different times/days
- Delete schedule blocks
- Optimize schedules for efficiency
- Answer questions ABOUT the scheduling process, algorithm, or GA parameters
- Provide feedback on generated schedules
- Suggest improvements to existing schedules

## What you CANNOT do in this conversation:
- Answer questions about faculty members, research, extensions, FSRs, or any other CERP data
- Provide information about members, publications, or projects
- Help with general CERP system navigation
- Discuss topics unrelated to scheduling

## When users ask about non-scheduling topics:
Respond with:
"I'm the Schedule Generation assistant. I can only help with creating, modifying, and optimizing class schedules. For questions about faculty, research, FSRs, or other CERP topics, please use a different conversation. Would you like me to help with schedule generation instead?"

## SCHEDULING CAPABILITIES (Genetic Algorithm Powered):
You have direct access to an advanced Genetic Algorithm scheduling engine. When users ask about schedules, you can:
- **Detect conflicts**: Find professor, room, or section overlaps in existing schedules
- **Add schedule blocks**: Place new classes using GA-optimized slot finding (avoids all conflicts)
- **Move schedule blocks**: Relocate classes to new days/times using conflict-free optimization
- **Delete schedule blocks**: Remove classes by professor, subject, or day
- **Generate full schedules**: Run the complete GA engine to create optimal timetables
- **Query schedules**: Show who teaches when, room usage, professor loads, etc.

**IMPORTANT RESPONSE FORMAT:**
- NEVER show JSON code blocks to users
- Respond conversationally and professionally
- When an action is needed, describe what you'll do in plain language
- The system will automatically show an interactive form for the user to confirm
- After describing the action, end your reply with the JSON action block (it will be hidden from the user)

When you detect a scheduling intent, respond with:
1. A clear explanation of what you understood
2. What action you're proposing
3. Any important details or warnings
4. Then include the JSON action block at the END (wrapped in ```json ... ```)

### Scheduling Action Format:
```json
{"action": "ACTION_TYPE", "params": {...}, "confirm": true/false}
```

### Available Actions:
1. `detect_conflicts` — Scan for overlapping schedules
   params: {} (no params needed)

2. `add_schedule` — Place a new class block
   REQUIRED params: { "prof": "Full Name", "subjCode": "CODE 101", "subjName": "Full Subject Name", "room": "Room Name", "section": "Section Letter/Code", "units": number, "day": "Day", "time": "HH:MM" }
   ALL fields are REQUIRED. Do NOT output the action JSON until you have ALL of these.
   confirm: true (always ask user first)

3. `move_schedule` — Relocate an existing class
   params: { "prof": "Name", "subjCode": "CODE 101" (optional), "target_day": "Monday" (optional), "target_time_period": "morning|afternoon|evening" (optional) }
   confirm: true

4. `delete_schedule` — Remove schedule blocks
   params: { "prof": "Name" (optional), "subjCode": "CODE 101" (optional), "day": "Monday" (optional), "semester": "1" (optional), "school_year": "2026-2027" (optional), "delete_all": true/false }
   Set "delete_all": true to delete ALL schedules for the current context (use when admin says "delete all", "clear everything", "remove all schedules")
   confirm: true

5. `generate_full` — Run basic GA schedule generation (legacy, small scale)
   params: { "subjects": [...], "rooms": [...] }
   confirm: true

6. `generate_full_schedule` — **ADVANCED**: Generate a COMPLETE semester schedule for ALL faculty and sections
   params: {
     "reference_semester": "1" or "2" (semester to base on, optional),
     "reference_school_year": "2025-2026" (school year to reference, optional),
     "target_semester": "1" or "2" (semester to generate for),
     "target_school_year": "2026-2027" (school year to generate for),
     "subjects": [{"code": "ENRP 101", "name": "Intro to ENRP", "section": "A", "units": 3, "weekly_hours": 3, "professors": ["Prof Name"]}],
     "rooms": ["TCC - 04", "TCC - 11"],
     "faculty_overrides": {"Prof Name": {"availability": ["Monday","Wednesday","Friday"], "teaching_load": 12}},
     "save_to_db": true/false
   }
   confirm: true (ALWAYS confirm before running)
   
   **IMPORTANT**: When user requests schedule generation:
   - Extract the reference and target semesters/years from context or ask
   - Populate subjects array from existing schedule data if user says "use same subjects" or "reference semester X"
   - Use all available rooms from the schedule data unless user specifies specific rooms
   - Only include faculty_overrides if user mentions specific availability changes
   - Set save_to_db to true by default
   - Respond conversationally: "I'll generate schedules for [faculty names] for [semester] [year] based on [reference]. The system will show you a form to confirm the details."
   - Then output the JSON block with pre-filled parameters

7. `query_schedule` — Fetch schedule info (no action, just display)
   params: { "query_type": "professor|room|conflicts|all", "filter": "value" }
   confirm: false

### Rules for scheduling actions:
- ALWAYS set confirm: true for add, move, delete, and generate actions
- In your text reply, explain what you're about to do in a friendly, conversational way
- DO NOT ask users to type information - the system will show them an interactive form
- When generating schedules, use data from the current schedule context to pre-fill subject lists, rooms, and faculty info
- If user says "use same subjects" or "reference semester X", look at the schedule data and extract the subjects automatically
- **CRITICAL: For `add_schedule`, you MUST have ALL required fields before outputting the JSON action block. If ANY of the following are missing or unclear, ASK the user first:**
  - Professor full name
  - Subject code (e.g. NSTP 2, ENRP 101)
  - Subject full name
  - Room assignment (e.g. TCC - 04, Room 201)
  - Section (e.g. A, B, X, Y — never leave this as "TBA" or "To be assigned")
  - Units (credit units as a number)
  - Day of the week
  - Time (start time in HH:MM format)
- NEVER use placeholder values like "TBA", "To be assigned", or empty strings for required fields
- When showing schedule data, format it nicely with bullet points or tables

## Tone and style:
- Professional and focused on scheduling
- Concise and clear
- Use bullet points when listing schedules
- You understand Filipino/Tagalog mixed with English (code-switching)

## Important:
- When schedule data is passed in context, use it to give accurate answers
- Never fabricate schedule information
- Stay focused on scheduling - redirect all other questions
"""

# Redirect prompt for regular conversations when scheduling is requested
SCHEDULE_REDIRECT_PROMPT = """

## IMPORTANT SCHEDULING RESTRICTION:
**Schedule generation, modification, and conflict detection are ONLY available in the dedicated "Schedule Generation" conversation.**

If the user asks about ANY of the following:
- Generating schedules
- Adding, moving, or deleting schedule blocks
- Detecting conflicts
- Running the genetic algorithm
- Creating timetables
- Optimizing class schedules
- Anything related to the scheduling system or GA

You MUST respond with:
"Schedule generation and modification are only available in the **Schedule Generation** conversation. Please switch to that conversation tab to work with schedules.

I can help you here with:
- Research projects and publications
- Faculty member information
- Extension programs
- FSR reports
- News and events
- General CERP system questions

What would you like to know about?"

You CAN still answer general questions ABOUT the system (like "What is the Schedule Generation conversation for?" or "How does the GA work?"), but you CANNOT perform any scheduling actions or show schedule data outside the Schedule Generation conversation.
"""

# ── Context Builder ────────────────────────────────────────────────────────────


def build_context_block(context_data: dict) -> str:
    """
    Build a readable context block from system data to inject into the conversation.
    Only includes data that was actually passed; keeps tokens lean.
    """
    if not context_data:
        return ""

    lines = ["\n\n## Current System Data (use this to answer accurately):"]

    if context_data.get("members"):
        lines.append(f"\n### Members ({len(context_data['members'])} total):")
        for m in context_data["members"][:30]:
            name = m.get(
                "name") or f"{m.get('first', '')} {m.get('last', '')}".strip()
            role = m.get("role") or m.get("position", "")
            dept = m.get("department", "")
            lines.append(f"- {name} | {role} | {dept}")

    if context_data.get("research"):
        lines.append(
            f"\n### Research Projects ({len(context_data['research'])} total):")
        for r in context_data["research"][:20]:
            title = r.get("title", "Untitled")
            status = r.get("status", "")
            author = r.get("leadResearcher") or r.get("author", "")
            lines.append(f"- {title} | {status} | {author}")

    if context_data.get("extensions"):
        lines.append(
            f"\n### Extension Activities ({len(context_data['extensions'])} total):")
        for e in context_data["extensions"][:20]:
            title = e.get("title") or e.get("projectTitle", "Untitled")
            status = e.get("status", "")
            lines.append(f"- {title} | {status}")

    if context_data.get("schedules"):
        lines.append(
            f"\n### Class Schedules ({len(context_data['schedules'])} total):")
        for s in context_data["schedules"][:40]:
            subj = s.get("subjCode", "")
            prof = s.get("prof", "")
            day = s.get("day", "")
            start = s.get("start", "")
            end = s.get("end", "")
            room = s.get("room", "")
            sec = s.get("section", "")
            sid = s.get("id", "")
            lines.append(
                f"- [{sid}] {subj} | {prof} | {day} {start}-{end} | {room} | Sec:{sec}")

    if context_data.get("news"):
        lines.append(
            f"\n### Recent News/Events ({len(context_data['news'])} total):")
        for n in context_data["news"][:10]:
            title = n.get("title", "Untitled")
            date = n.get("date") or n.get("createdAt", "")
            lines.append(f"- {title} | {date}")

    return "\n".join(lines)


# ── Action Extractor ───────────────────────────────────────────────────────────

def extract_action(reply: str) -> Optional[dict]:
    """
    Extract a JSON scheduling action from CHE's reply, if present.
    Looks for ```json {...} ``` blocks at the end of the reply.
    """
    import re
    # Find last JSON code block
    matches = re.findall(r'```json\s*(\{.*?\})\s*```', reply, re.DOTALL)
    if matches:
        try:
            action_data = json.loads(matches[-1])
            if "action" in action_data:
                return action_data
        except json.JSONDecodeError:
            pass
    return None


# ── Conflict Checker ───────────────────────────────────────────────────────────

def _check_slot_conflicts(schedule: dict, existing_schedules: list) -> list:
    """Check if a placed schedule conflicts with existing ones. Returns list of conflict descriptions."""
    from services.scheduler_service import time_to_slot

    conflicts = []
    day = schedule.get('day', '')
    start = schedule.get('start', '')
    end = schedule.get('end', '')
    prof = (schedule.get('prof') or '').lower().strip()
    room = (schedule.get('room') or '').lower().strip()
    section = (schedule.get('section') or '').lower().strip()

    if not day or not start or not end:
        return conflicts

    try:
        new_start = time_to_slot(start)
        new_end = time_to_slot(end)
    except (ValueError, IndexError):
        return conflicts

    for s in existing_schedules:
        if s.get('day') != day:
            continue
        if not s.get('start') or not s.get('end'):
            continue
        try:
            ex_start = time_to_slot(s['start'])
            ex_end = time_to_slot(s['end'])
        except (ValueError, IndexError):
            continue

        # Check time overlap
        if new_start < ex_end and new_end > ex_start:
            # Professor conflict
            if prof and (s.get('prof') or '').lower().strip() == prof:
                conflicts.append(
                    f"Professor '{schedule.get('prof')}' already has {s.get('subjCode', '')} at {s.get('start')}-{s.get('end')} on {day}")
            # Room conflict
            if room and room != 'tba' and (s.get('room') or '').lower().strip() == room:
                conflicts.append(
                    f"Room '{schedule.get('room')}' is occupied by {s.get('subjCode', '')} ({s.get('prof', '')}) at {s.get('start')}-{s.get('end')} on {day}")
            # Section conflict
            if section and (s.get('section') or '').lower().strip() == section:
                conflicts.append(
                    f"Section '{schedule.get('section')}' has {s.get('subjCode', '')} at {s.get('start')}-{s.get('end')} on {day}")

    return conflicts


# ── Schedule Action Executor ───────────────────────────────────────────────────

def execute_schedule_action(action_data: dict, existing_schedules: list) -> dict:
    """
    Execute a scheduling action using the GA engine.

    Args:
        action_data: Parsed action dict from CHE's reply
        existing_schedules: Current schedule list from DB

    Returns:
        dict with 'success', 'message', 'data' keys
    """
    from services.scheduler_service import (
        find_optimal_slot, add_schedule_smart, move_schedule_smart,
        run_ga, slot_to_time, time_to_slot
    )

    action = action_data.get("action", "")
    params = action_data.get("params", {})

    if action == "detect_conflicts":
        conflicts = []
        for i, s1 in enumerate(existing_schedules):
            for s2 in existing_schedules[i+1:]:
                if s1.get('day') == s2.get('day'):
                    # Check time overlap
                    if s1.get('start') and s2.get('start') and s1.get('end') and s2.get('end'):
                        if s1['start'] < s2['end'] and s1['end'] > s2['start']:
                            if s1.get('prof') == s2.get('prof'):
                                conflicts.append({
                                    'type': 'professor',
                                    'professor': s1['prof'],
                                    'schedule1': s1,
                                    'schedule2': s2
                                })
                            if s1.get('room') == s2.get('room') and s1.get('room'):
                                conflicts.append({
                                    'type': 'room',
                                    'room': s1['room'],
                                    'schedule1': s1,
                                    'schedule2': s2
                                })
                            if s1.get('section') == s2.get('section') and s1.get('section'):
                                conflicts.append({
                                    'type': 'section',
                                    'section': s1['section'],
                                    'schedule1': s1,
                                    'schedule2': s2
                                })
        return {
            'success': True,
            'message': f"Found {len(conflicts)} conflict(s)." if conflicts else "No conflicts detected!",
            'data': {'conflicts': conflicts, 'total': len(conflicts)}
        }

    elif action == "add_schedule":
        # Validate all required fields are present and not placeholders
        required_fields = ['prof', 'subjCode',
                           'room', 'section', 'day', 'time']
        placeholder_values = ['tba', 'to be assigned', 'n/a', 'na', '']
        missing = []
        for field in required_fields:
            val = str(params.get(field, '')).strip().lower()
            if not val or val in placeholder_values:
                missing.append(field)

        if not params.get('units') or params.get('units') == 0:
            missing.append('units')

        if missing:
            return {
                'success': False,
                'message': f"Cannot add schedule — missing required fields: {', '.join(missing)}. Please provide all details.",
                'data': {'missing_fields': missing}
            }

        schedule_to_add = {
            'prof': params['prof'].strip(),
            'subjCode': params['subjCode'].strip(),
            'subjName': params.get('subjName', params['subjCode']).strip(),
            'room': params['room'].strip(),
            'section': params['section'].strip(),
            'units': params['units'],
        }

        # Use the day/time preferences from CHE
        target_day = params.get('day')
        target_time = params.get('time')  # e.g. "14:00" or "2:00"
        target_time_start = None
        target_time_end = None

        if target_time:
            # Normalize time to 24h format
            t_parts = str(target_time).replace(' ', '').split(':')
            hour = int(t_parts[0])
            minute = int(t_parts[1]) if len(t_parts) > 1 else 0
            # If hour < 7, likely PM (e.g. "2:00" = 14:00)
            if hour < 7 and hour != 0:
                hour += 12
            target_time_start = f"{hour}:{minute:02d}"
            from services.scheduler_service import slots_for_duration as _sfd
            duration_slots = _sfd(float(schedule_to_add.get('units', 1.5)))
            end_slot_num = time_to_slot(target_time_start) + duration_slots
            target_time_end = slot_to_time(end_slot_num)

        result = find_optimal_slot(
            schedule_to_add, existing_schedules,
            target_day=target_day,
            target_time_start=target_time_start,
            target_time_end=target_time_end
        )

        if result:
            # Verify no conflicts with the found slot
            conflicts = _check_slot_conflicts(result, existing_schedules)
            if conflicts:
                return {
                    'success': False,
                    'message': f"Cannot place at {result.get('day')} {result.get('start')}-{result.get('end')} — conflicts detected: {'; '.join(conflicts)}",
                    'data': {'conflicts': conflicts}
                }
            return {'success': True, 'message': f"Placed on {result['day']} at {result['start']}-{result['end']}", 'data': {'schedule': result}}
        else:
            # Fallback: try without time constraint
            success, msg, fallback = add_schedule_smart(
                schedule_to_add, existing_schedules)
            return {'success': success, 'message': msg, 'data': {'schedule': fallback}}

    elif action == "move_schedule":
        prof = params.get('prof', '')
        subj = params.get('subjCode', '')
        target_day = params.get('target_day')
        target_period = params.get('target_time_period')

        # Find matching schedules
        matches = []
        for s in existing_schedules:
            match = True
            if prof and prof.lower() not in (s.get('prof') or '').lower():
                match = False
            if subj and subj.upper() not in (s.get('subjCode') or '').upper():
                match = False
            if match:
                matches.append(s)

        if not matches:
            return {'success': False, 'message': 'No matching schedules found.', 'data': {}}

        moved = []
        for sched in matches:
            success, msg, result = move_schedule_smart(
                sched.get('id', ''),
                existing_schedules,
                target_day=target_day,
                target_time_period=target_period
            )
            if success and result:
                moved.append(result)

        if moved:
            return {
                'success': True,
                'message': f"Successfully relocated {len(moved)} schedule(s).",
                'data': {'moved_schedules': moved}
            }
        return {'success': False, 'message': 'Could not find conflict-free slots.', 'data': {}}

    elif action == "delete_schedule":
        prof = params.get('prof', '')
        subj = params.get('subjCode', '')
        day = params.get('day', '')
        semester = params.get('semester', '')
        school_year = params.get('school_year', '')
        delete_all = params.get('delete_all', False)

        # Safety: require at least one filter or explicit delete_all
        if not delete_all and not prof and not subj and not day and not semester and not school_year:
            return {
                'success': False,
                'message': 'Please specify what to delete (professor, subject, day, semester, or school_year). Use "delete_all": true to delete everything.',
                'data': {}
            }

        matches = []
        for s in existing_schedules:
            if delete_all:
                matches.append(s)
                continue

            # ALL provided filters must match (AND logic)
            match = True
            if prof and prof.lower() not in (s.get('prof') or '').lower():
                match = False
            if subj and subj.upper() not in (s.get('subjCode') or '').upper():
                match = False
            if day and day.lower() != (s.get('day') or '').lower():
                match = False
            if semester and semester != (s.get('semester') or ''):
                match = False
            if school_year and school_year != (s.get('schoolYear') or ''):
                match = False
            if match:
                matches.append(s)

        if matches:
            return {
                'success': True,
                'message': f"Found {len(matches)} schedule(s) to delete.",
                'data': {'schedules_to_delete': [s.get('id') for s in matches if s.get('id')], 'details': matches}
            }
        return {'success': False, 'message': 'No matching schedules found.', 'data': {}}

    elif action == "generate_full":
        subjects = params.get('subjects', [])
        rooms = params.get('rooms', [])
        if not subjects:
            return {'success': False, 'message': 'No subjects provided for generation.', 'data': {'requires_input': True}}
        result = run_ga(subjects=subjects, rooms=rooms,
                        prof_availability={}, constraints={})
        return {
            'success': True,
            'message': f"Generated schedule with {len(result)} blocks.",
            'data': {'generated_schedule': result}
        }

    elif action == "generate_full_schedule":
        # This action is handled by the Flask endpoint directly
        # Return a flag telling the frontend to call /api/schedule/generate-full
        return {
            'success': True,
            'message': 'Full schedule generation ready. Frontend will call the generation endpoint.',
            'data': {
                'redirect_to_endpoint': '/api/schedule/generate-full',
                'params': params
            }
        }

    elif action == "query_schedule":
        query_type = params.get('query_type', 'all')
        filter_val = params.get('filter', '')

        if query_type == 'professor':
            filtered = [s for s in existing_schedules if filter_val.lower() in (
                s.get('prof') or '').lower()]
            return {'success': True, 'message': f"Found {len(filtered)} schedules for {filter_val}.", 'data': {'schedules': filtered}}
        elif query_type == 'room':
            filtered = [s for s in existing_schedules if filter_val.lower() in (
                s.get('room') or '').lower()]
            return {'success': True, 'message': f"Found {len(filtered)} schedules in {filter_val}.", 'data': {'schedules': filtered}}
        elif query_type == 'conflicts':
            # Re-use detect_conflicts
            return execute_schedule_action({'action': 'detect_conflicts', 'params': {}}, existing_schedules)
        else:
            return {'success': True, 'message': f"Total: {len(existing_schedules)} schedule blocks.", 'data': {'schedules': existing_schedules}}

    return {'success': False, 'message': f'Unknown action: {action}', 'data': {}}


# ── Main Chat Function ─────────────────────────────────────────────────────────

def chat(
    message: str,
    history: list,
    context_data: Optional[dict] = None,
    is_system_conversation: bool = False
) -> dict:
    """
    Send a message to CHE and get a response.

    Args:
        message:                The user's latest message
        history:                List of prior turns: [{"role": "user"|"assistant", "content": "..."}]
        context_data:           Optional dict with live system data (members, research, etc.)
        is_system_conversation: True if this is the Schedule Generation conversation

    Returns:
        dict with 'reply' (str), 'error' (bool), and optionally 'action' (dict)
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {
            "reply": "⚠️ CHE is not configured yet. Ask your administrator to add the GROQ_API_KEY to the environment.",
            "error": True
        }

    try:
        client = Groq(api_key=api_key)

        # Build the messages list for the API call
        # Use schedule-enabled prompt ONLY in the system conversation
        if is_system_conversation:
            system_content = SCHEDULE_SYSTEM_PROMPT
        else:
            system_content = BASE_SYSTEM_PROMPT + SCHEDULE_REDIRECT_PROMPT

        if context_data:
            system_content += build_context_block(context_data)

        messages = [{"role": "system", "content": system_content}]

        # Add conversation history (cap at last 20 turns to control token usage)
        for turn in history[-20:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Add the current message
        messages.append({"role": "user", "content": message})

        # Try primary model first, fallback if not available
        # Updated to current Groq production models (August 2026)
        models_to_try = [
            # Primary: GPT OSS 120B (500 t/sec, production)
            "openai/gpt-oss-120b",
            # Fallback 1: GPT OSS 20B (1000 t/sec, production)
            "openai/gpt-oss-20b",
            # Fallback 2: Qwen 3.6 27B (500 t/sec, preview)
            "qwen/qwen3.6-27b",
        ]

        last_error = None
        for model in models_to_try:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=2048,
                    top_p=0.85,
                )
                break  # Success, exit loop
            except Exception as model_error:
                last_error = model_error
                error_str = str(model_error).lower()
                if "model" in error_str and ("not found" in error_str or "does not exist" in error_str or "access" in error_str):
                    logger.warning(
                        f"Model {model} not available, trying next fallback...")
                    continue  # Try next model
                else:
                    raise  # Different error, don't fallback
        else:
            # All models failed
            raise last_error if last_error else Exception(
                "All models unavailable")

        reply = response.choices[0].message.content.strip()

        # Check if CHE included a scheduling action
        action = extract_action(reply)

        result = {"reply": reply, "error": False}
        if action:
            result["action"] = action

        return result

    except Exception as e:
        logger.error(f"CHE service error: {e}")
        error_msg = str(e)

        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return {
                "reply": "⚠️ Invalid API key. Please check the GROQ_API_KEY in your environment settings.",
                "error": True
            }
        if "rate_limit" in error_msg.lower():
            return {
                "reply": "⏳ I'm receiving too many requests right now. Please wait a moment and try again.",
                "error": True
            }
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return {
                "reply": "🔌 Connection issue. Please check your internet connection and try again.",
                "error": True
            }

        return {
            "reply": f"⚠️ Something went wrong on my end. Please try again. (Error: {error_msg[:100]})",
            "error": True
        }
