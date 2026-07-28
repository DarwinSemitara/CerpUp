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

SYSTEM_PROMPT = """You are CHE, the official AI assistant for CERP (Center for Extension and Research in the Philippines), specifically for the CERP 2.0 management system used by the College of Human Ecology (CHE) at UPLB.

Your role is to help administrators and members with anything related to the CERP system and its data.

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

## SCHEDULING CAPABILITIES (Genetic Algorithm Powered):
You have direct access to an advanced Genetic Algorithm scheduling engine. When users ask about schedules, you can:
- **Detect conflicts**: Find professor, room, or section overlaps in existing schedules
- **Add schedule blocks**: Place new classes using GA-optimized slot finding (avoids all conflicts)
- **Move schedule blocks**: Relocate classes to new days/times using conflict-free optimization
- **Delete schedule blocks**: Remove classes by professor, subject, or day
- **Generate full schedules**: Run the complete GA engine to create optimal timetables
- **Query schedules**: Show who teaches when, room usage, professor loads, etc.

When you detect a scheduling intent, respond with a JSON action block wrapped in ```json ... ``` at the END of your reply. The system will parse this and execute the action.

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

4. `delete_schedule` — Remove a schedule block
   params: { "prof": "Name" (optional), "subjCode": "CODE 101" (optional), "day": "Monday" (optional) }
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
   NOTE: This is the FULL generation engine. Use when admin asks to "generate full schedules", "create a complete schedule", or "make schedules like last semester". Ask for:
   - Which semester/year to reference (if they want to base on previous)
   - Which semester/year to generate for
   - Any faculty changes (availability, load, professor swaps)
   - The subject list with professors and sections
   - Available rooms

7. `query_schedule` — Fetch schedule info (no action, just display)
   params: { "query_type": "professor|room|conflicts|all", "filter": "value" }
   confirm: false

### Rules for scheduling actions:
- ALWAYS set confirm: true for add, move, delete, and generate actions
- In your text reply, explain what you're about to do and ask "Shall I proceed?"
- **CRITICAL: For `add_schedule`, you MUST have ALL required fields before outputting the JSON action block. If ANY of the following are missing or unclear, ASK the user first:**
  - Professor full name
  - Subject code (e.g. NSTP 2, ENRP 101)
  - Subject full name
  - Room assignment (e.g. TCC - 04, Room 201)
  - Section (e.g. A, B, X, Y — never leave this as "TBA" or "To be assigned")
  - Units (credit units as a number)
  - Day of the week
  - Time (start time in HH:MM format)
- If the user hasn't provided enough details, ask for the missing info (do NOT output JSON)
- NEVER use placeholder values like "TBA", "To be assigned", or empty strings for required fields
- When showing schedule data, format it nicely with bullet points or tables

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

        matches = []
        for s in existing_schedules:
            match = True
            if prof and prof.lower() not in (s.get('prof') or '').lower():
                match = False
            if subj and subj.upper() not in (s.get('subjCode') or '').upper():
                match = False
            if day and day != s.get('day'):
                match = False
            if match:
                matches.append(s)

        if matches:
            return {
                'success': True,
                'message': f"Found {len(matches)} schedule(s) to delete.",
                'data': {'schedules_to_delete': [s.get('id') for s in matches], 'details': matches}
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
    context_data: Optional[dict] = None
) -> dict:
    """
    Send a message to CHE and get a response.

    Args:
        message:      The user's latest message
        history:      List of prior turns: [{"role": "user"|"assistant", "content": "..."}]
        context_data: Optional dict with live system data (members, research, etc.)

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
        system_content = SYSTEM_PROMPT
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

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.6,
            max_tokens=1500,
            top_p=0.9,
        )

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
