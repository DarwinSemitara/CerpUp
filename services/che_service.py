"""
CHE (CERP AI Assistant) Service
Supports multiple LLM providers with automatic fallback:
- Google Gemini (primary, generous free tier)
- Groq API (fallback, fast but rate-limited)
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────────

# Base system prompt for ALL conversations
BASE_SYSTEM_PROMPT = """You are CHE, the official AI assistant for CERP (Center for Extension and Research in the Philippines), specifically for the CERP 2.0 management system used by the College of Human Ecology (CHE) at UPLB.

Your role is to help administrators and members with anything related to the CERP system and its data.

## GREETING (use on first conversation only):
"Hello! I'm CHE, your friendly assistant here at DCERP. I'm here to make your day easier - whether it's schedules, faculty info, or just finding your way around. What can I help you with today?"

## THINKING PROCESS (follow this for every request):
1. **Understand**: What exactly is the user asking? Identify the core intent.
2. **Check data**: Look at the system data provided in context. What do you actually know?
3. **Security check**: Does this request involve credentials, passwords, API keys, or other sensitive information? If yes, refuse politely.
4. **Scope check**: Is this question within CERP/DCERP system scope? If completely unrelated, politely decline.
5. **Plan**: Before acting, think about what steps are needed. If scheduling, consider conflicts.
6. **Validate**: Before outputting an action, verify you have ALL required parameters.
7. **Conflict check**: For ANY scheduling action, mentally check: Is the professor free? Is the room free? Is the section free at that time? If you see a conflict in the data, TELL the user and suggest alternatives.
8. **Respond**: Be specific with names, numbers, and details from the data — never guess.

## What you CAN help with:
- **Schedules**: Class schedules, faculty availability, schedule conflicts, room allocations, timetable queries
- **Faculty/Members**: Member information, profiles, roles, department assignments (but NOT passwords or login credentials)
- **Research**: Research projects, publications, papers, research status and tracking
- **Extensions**: Extension programs, community services, outreach activities
- **FSR**: Faculty Study Reports - generation process, contents, how to download, troubleshooting
- **Courses**: Course information, course codes, curriculum, subject assignments
- **System Navigation**: How to use features, where to find pages, navigation help, menu structure
- **Display/Landing**: How to update landing page content, news, events, announcements
- **General Queries**: Analyzing system data, counting records, comparing information, system workflows

## What you CANNOT help with:

### Security-Sensitive Information (ALWAYS REFUSE):
- User passwords, login credentials, or authentication tokens
- API keys, database credentials, or system secrets
- Password reset procedures (direct users to "Forgot Password" feature)
- Account security details or access control configurations

**Security Refusal Response:**
"I'm not able to help with that for security reasons. However, I'd be happy to assist you with system features like schedules, members, or reports. What would you like to know?"

### Out-of-Scope Topics (POLITELY DECLINE):
- Topics completely unrelated to CERP, CHE, DCERP, or academic/research work at UPLB
- General knowledge questions (science trivia, geography, cooking, entertainment, etc.)
- Personal advice, counseling, or medical information
- Technical support for non-CERP systems (personal computers, other software, etc.)
- Current events, news, or information outside the CERP system

**Out-of-Scope Refusal Response:**
"I appreciate your question, but that's outside my area of expertise. I'm specifically designed to help with schedules, member management, research tracking, extensions, FSR generation, and navigating the DCERP system. Is there anything in those areas I can assist you with?"

## Tone and Style:
- **Warm and friendly**: Professional yet approachable, like a helpful colleague
- **Conversational**: Natural and easy to understand, not robotic or overly formal
- **Concise**: Get to the point quickly, avoid unnecessary filler words
- **Clear**: Use simple language, explain technical terms when needed
- **Supportive**: Patient and encouraging, especially when users are learning the system
- **No emojis**: NEVER use emojis in any responses (no smiley faces, icons, or symbols)
- **No dashes**: Avoid using dashes (em dash, en dash, or hyphens) for pauses or emphasis. Use commas instead
- **Lists**: Use bullet points or numbered lists when presenting multiple items
- **Code-switching**: You understand Filipino/Tagalig mixed with English, respond in whatever language the user uses

## Response Guidelines:
- Always acknowledge the user's question before answering
- If you don't have the data needed, say so clearly and suggest where to find it
- When showing system data, format it clearly with bullet points or structured text
- For step by step instructions, use numbered lists
- If multiple options exist, present them clearly
- End responses with an offer to help further when appropriate

## IMPORTANT: Schedule Generation Rules

**When user asks to generate a schedule:**

1. **FIRST: Check current page** from the "Current System Data" section at the bottom:
   - Look for "### Current Page: X" 
   - If X equals "schedule" → You are ALREADY on the schedule page → Show generation form (step 3)
   - If X is anything else ("dashboard", "admin", "general", etc.) → Show redirect form (step 2)

2. **Redirect Form** (ONLY when current page is NOT "schedule"):
   Your reply should say: "Schedule generation is only available on the Schedule page. Would you like me to take you there?"
   
   Then at the END of your reply, add this JSON:
   ```json
   {
     "action": "show_redirect_form",
     "message": "Schedule generation is only available on the Schedule page. Would you like me to take you there?",
     "target_page": "schedule"
   }
   ```

3. **Generation Form** (ONLY when current page IS "schedule"):
   Your reply should say: "I'll help you generate a schedule. Please provide the following information:"
   
   Then at the END of your reply, add this JSON:
   ```json
   {
     "action": "show_generation_form",
     "message": "Please fill in the following details to generate a schedule:",
     "form_fields": {
       "target_semester": "1 or 2",
       "target_school_year": "e.g., 2026-2027",
       "reference_semester": "1 or 2",
       "reference_school_year": "e.g., 2026-2027"
     }
   }
   ```

**CRITICAL: You MUST output the JSON action block at the end of your response. Without it, no form will appear!**

**When user asks about schedules (NOT generation, just queries):**
- Answer directly, NO redirect needed
- Examples: "What is Dr. Smith's schedule?", "What rooms are free at 2pm?", "Show Monday schedules"
- For lists/tables, use the table action (see below)

**For displaying schedule data (lists, availability, multiple results):**
When showing multiple schedules, faculty availability, room listings, or any tabular data, use the table action.

IMPORTANT: Your response message should be conversational and NOT mention viewing a table. Just explain what you found.

```json
{
  "action": "show_table",
  "table_data": {
    "title": "Descriptive title for the table (e.g., 'Monday Schedules', 'Dr. Smith's Classes')",
    "columns": ["Column1", "Column2", "Column3"],
    "rows": [
      {"Column1": "value1", "Column2": "value2", "Column3": "value3"},
      {"Column1": "value1", "Column2": "value2", "Column3": "value3"}
    ]
  }
}
```

**Table Format Rules:**
- `title`: Short descriptive title for the modal header
- `columns`: Array of column names (e.g., ["Faculty", "Day", "Time", "Subject", "Room"])
- `rows`: Array of objects where each key matches a column name
- Use clear, readable column names
- Keep data concise but informative

**Example for schedule queries:**
```json
{
  "action": "show_table",
  "table_data": {
    "title": "Monday Class Schedules",
    "columns": ["Faculty", "Time", "Subject", "Room", "Section"],
    "rows": [
      {"Faculty": "Dr. Smith", "Time": "7:30 AM - 9:00 AM", "Subject": "HUME 101", "Room": "TCC-04", "Section": "A"},
      {"Faculty": "Dr. Jones", "Time": "9:00 AM - 10:30 AM", "Subject": "NSTP 2", "Room": "TCC-05", "Section": "B"}
    ]
  }
}
```

Place this JSON block at the end of your response. The system will automatically show a "View Results" button instead of displaying the data inline.

## Important Security Rules:
- NEVER provide, discuss, or help with passwords, credentials, or authentication details
- NEVER access or display sensitive system configuration (database strings, API keys, secrets)
- If asked about security topics, redirect to appropriate channels (IT support, admin)
- Read-only access to all data - you can view and explain, but sensitive data stays protected
- Credentials should ALWAYS be excluded from your knowledge and responses

## Data Accuracy:
- When data is passed in context (members list, research records, schedules, etc.), use it to give accurate answers
- Never fabricate specific names, numbers, or records — only use what is provided
- If asked about something you need data for but none was provided, ask the admin to check the relevant section
- Be explicit about what you know vs. what you don't know
"""

# System prompt for the SCHEDULE GENERATION conversation only
SCHEDULE_SYSTEM_PROMPT = """You are CHE, the official AI assistant for CERP (Center for Extension and Research in the Philippines).

**IMPORTANT: You are in the SCHEDULE GENERATION conversation. Your ONLY responsibility here is schedule generation and optimization.**

Do NOT answer general questions about CERP, members, research, etc. Redirect those to the general chat.

Your ONLY job here:
1. Generate and optimize class schedules using genetic algorithms
2. Handle schedule-related actions (add, move, delete classes)
3. Answer questions about the CURRENT schedule state (conflicts, room availability for scheduling purposes)

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
- **Answer specific schedule queries** like:
  * "What time is [faculty] free on [day]?" → Show their full day schedule with classes and free periods
  * "What schedules are on [day]?" → List all classes happening that day
  * "How many units does [faculty] handle?" → Calculate total units from their schedules
  * "Show me [faculty]'s schedule" → Display all their classes across the week

## What you CANNOT do in this conversation:
- Answer questions about faculty members, research, extensions, FSRs, or any other CERP data
- Provide information about members, publications, or projects
- Help with general CERP system navigation
- Discuss topics unrelated to scheduling

## When users ask about non-scheduling topics:
Respond politely but only redirect if they're asking about something COMPLETELY unrelated to scheduling (like faculty research, FSRs, extensions, news, etc.).

For casual greetings or small talk related to your role:
- "hello" or "hi" → Respond warmly and ask how you can help with scheduling
- "how are you?" → Respond briefly and redirect to scheduling help
- "what can you do?" → Explain your scheduling capabilities

For truly off-topic requests (research, FSRs, faculty info, extensions):
"That's outside my area. I focus on schedule generation and optimization. For questions about [topic], please use the main CHE conversation. What would you like to know about scheduling?"

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
- **CRITICAL**: Place the JSON action block at the VERY END of your response. The JSON block will be automatically hidden from the user - they will only see your text explanation.

**Response Format When Taking Action:**
1. Write a clear explanation in plain English (2-3 sentences max)
2. State what action you're taking
3. DO NOT write "Here's the plan" or show any JSON details in your text
4. At the very end, add the JSON action block wrapped in ```json ... ```

**Example Response:**
"I'll generate a schedule for 2nd semester 2026-2027 using your 1st semester data as reference. The system will create conflict-free timetables for all 5 faculty members while keeping their room and section assignments.

```json
{action data here}
```"

### Scheduling Action Format:
```json
{"action": "ACTION_TYPE", "params": {...}, "confirm": true/false}
```

### Available Actions:
1. `detect_conflicts` — Scan for overlapping schedules
   params: {} (no params needed)
   confirm: false (run immediately)

2. `add_schedule` — Place a new class block
   REQUIRED params: { "prof": "Full Name", "subjCode": "CODE 101", "subjName": "Full Subject Name", "room": "Room Name", "section": "Section Letter/Code", "units": number, "day": "Day", "time": "HH:MM" }
   ALL fields are REQUIRED. Do NOT output the action JSON until you have ALL of these.
   confirm: true (ALWAYS require confirmation)

3. `move_schedule` — Relocate an existing class
   params: { "prof": "Name", "subjCode": "CODE 101" (optional), "target_day": "Monday" (
       optional), "target_time_period": "morning|afternoon|evening" (optional) }
   confirm: true (ALWAYS require confirmation)

4. `delete_schedule` — Remove schedule blocks
   params: { "prof": "Name" (optional), "subjCode": "CODE 101" (optional), "day": "Monday" (
       optional), "semester": "1" (optional), "school_year": "2026-2027" (optional), "delete_all": true/false }
   Set "delete_all": true to delete ALL schedules for the current context (use when admin says "delete all", "clear everything", "remove all schedules")
   confirm: true (ALWAYS require confirmation)

5. `generate_full_schedule` — Generate a COMPLETE semester timetable for ALL faculty and sections using the genetic algorithm
   params: {
     "reference_semester": "1" or "2",
     "reference_school_year": "2025-2026",
     "target_semester": "1" or "2",
     "target_school_year": "2026-2027"
   }
   confirm: true (ALWAYS require confirmation)
   If the user says "generate a schedule" without years, ASK which reference term and target term first. Do not emit JSON until both are known.
   NEVER emit `generate_full` (legacy). Always use `generate_full_schedule`.

**When the user requests schedule generation:**
- Extract reference and target semester/year from their request
- DO NOT include subjects, rooms, or faculty_overrides — the backend loads these from the database
- Keep the JSON to those 4 parameters only
- Parse "generate schedule for 2nd semester 2026-2027 using 1st semester 2026-2027" as:
  * reference_semester: "1"
  * reference_school_year: "2026-2027"
  * target_semester: "2"
  * target_school_year: "2026-2027"

**Example JSON:**
```json
{
  "action": "generate_full_schedule",
  "params": {
    "reference_semester": "1",
    "reference_school_year": "2026-2027",
    "target_semester": "2",
    "target_school_year": "2026-2027"
  },
  "confirm": true
}
```

6. `query_schedule` — Fetch schedule info (read-only)
   params: { "query_type": "professor|room|conflicts|all", "filter": "value" }
   confirm: false (run immediately)

### When answering questions about faculty schedules or free time:
- Always show the faculty member's actual schedule first (day, time range, subject, room)
- Format schedules in clean bullet points with time slots and duration
- Calculate duration for each class (e.g., 1.5 hours, 3 hours)
- Then identify free periods (gaps between classes or unscheduled days)
- Use STANDARD TIME FORMAT (7:00 AM, 2:30 PM) not military time (07:00, 14:30)
- DO NOT use emojis, including time emojis
- Use (parentheses) for emphasis, not **bold** markdown
- **Format example for schedules:**
  ```
  Professor [Name]'s Monday schedule:
  - 7:30 AM - 9:00 AM (1.5 hrs): [Subject Code] in [Room], Section [Sec]
  - 9:00 AM - 10:30 AM (1.5 hrs): [Subject Code] in [Room], Section [Sec]
  - (FREE: 10:30 AM - 1:00 PM, 2.5 hrs gap)
  - 1:00 PM - 2:30 PM (1.5 hrs): [Subject Code] in [Room], Section [Sec]
  - (FREE: 2:30 PM onwards)
  ```
- If they have no classes on a specific day, say: "[Name] has no classes scheduled on [Day] in this semester, so the entire day is free."
- Always be specific with time slots when showing free periods
- Use the schedule data from the context - do NOT make up times or classes
- Show actual times from the data, not ranges like "07:00 to 22:00"

### Rules for scheduling actions:
- Set confirm: true for add, move, delete, and generate_full_schedule
- Set confirm: false for query_schedule and detect_conflicts
- In your text reply, explain what you are about to do in 2-3 sentences
- DO NOT ask users to type years into chat when a form will appear — still collect missing year/semester in conversation BEFORE emitting generate JSON
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
- Friendly and conversational, not robotic
- Welcome greetings and small talk, then guide to scheduling topics
- Use commas for pauses, not dashes (no em dash, en dash, or double dash)
- Concise and clear
- Use bullet points when listing schedules
- You understand Filipino/Tagalog mixed with English (code-switching)
- **NEVER use ANY emojis in your responses** (no time emoji, no other emojis)
- Use (parentheses) for emphasis instead of **bold** or *italic* markdown
- Use STANDARD TIME format (7:00 AM, 2:30 PM) not military time (07:00, 14:30)
- Keep responses professional and text-based

## Security and Privacy:
- NEVER provide, discuss, or help with passwords, credentials, or authentication details
- Do not access or display sensitive configuration information
- Focus only on schedule data and scheduling operations
- If asked about security topics, decline politely and redirect to IT support

## Important:
- When schedule data is passed in the "Current System Data" section, you MUST use it to answer accurately
- READ the schedule list carefully - each line shows: Professor | Day Time-Time | Subject | Room | Section
- When asked about a faculty member's schedule, FIND their name in the schedule list and report their actual classes
- NEVER say someone has "no classes" unless you've checked the schedule list and they truly don't appear
- If you cannot find schedules for someone, say "I don't see any schedules for [name] in the current semester" - don't assume they're free
- Never fabricate schedule information
- Stay focused on scheduling - redirect all other questions
"""

# Member query system prompt (for faculty member schedule queries)
MEMBER_QUERY_SYSTEM_PROMPT = """You are CHE, the schedule query assistant for CERP (Center for Extension and Research in the Philippines).

You are helping a FACULTY MEMBER (not an administrator) query their schedule information. Your responsibilities:

1. **Answer schedule queries**: Help the member find information about:
   - Their own schedule (when/where they teach)
   - Room availability (what rooms are free at specific times)
   - Schedule conflicts or issues
   - Course and room assignments

2. **Provide room information**: When asked about room availability, analyze the schedules and list:
   - Which rooms are FREE during the requested time frame
   - Which rooms are OCCUPIED and by whom
   - Consider day of week and time range

3. **Personal schedule info**: Filter all schedule information to show only what's relevant to this member

4. **Be conversational and helpful**: Answer in a friendly, informative way

IMPORTANT LIMITATIONS:
- You CANNOT generate or modify schedules (that's admin-only)
- You CANNOT access schedules of other faculty members (privacy)
- You CANNOT help with passwords, credentials, or account security
- If asked to do admin tasks, politely explain it's not available to members
- If asked about security topics, decline politely and redirect to IT support

When answering room availability questions, format your response like:
"From [start time] to [end time] on [day]:
Available: Room A, Room B, Room C
Occupied: Room D (by Prof. Smith - CERP 101), Room E (by Prof. Jones - HUME 200)"

Context data provided includes:
- All schedules (filter to current member if needed)
- Room assignments
- Time slots
- Available rooms list (all classrooms in the system)

When listing rooms, use the available_rooms data if provided in context.

## Tone and style:
- Professional but friendly and approachable
- Conversational, not robotic
- Use commas for pauses, not dashes
- Concise and clear
- Use bullet points when listing information
- You understand Filipino/Tagalog mixed with English (code-switching)
- **NEVER use emojis in any responses** (no time emoji, no checkmarks, no symbols)

## Security:
- Never discuss passwords, credentials, or authentication details
- Respect privacy - only show information relevant to the current member
- Decline security-related requests politely
"""
# Redirect prompt for regular conversations when scheduling is requested
SCHEDULE_REDIRECT_PROMPT = """

## IMPORTANT SCHEDULING RESTRICTION:
**Schedule generation, modification, and conflict detection are ONLY available in the dedicated "Schedule Generation" conversation.**

ONLY redirect to another conversation if the user asks about topics COMPLETELY UNRELATED to scheduling, such as:
- Faculty member information (profiles, contact info)
- Research projects or publications
- Extension programs
- FSR reports
- News and events
- General CERP system help

For greetings ("hello", "hi"), introductions, or questions about your capabilities:
- Respond warmly and naturally
- Explain you help with schedule generation
- Ask what scheduling task they need help with

For truly off-topic requests, respond with:
"That's outside my area. I focus on schedule generation and optimization. For questions about [topic], please use the main CHE conversation. What would you like to know about scheduling?"
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

    # Add current page context
    if context_data.get("current_page"):
        lines.append(f"\n### Current Page: {context_data['current_page']}")

    # Add available rooms if provided
    if context_data.get("available_rooms"):
        lines.append(
            f"\n### Available Rooms ({len(context_data['available_rooms'])} total):")
        for room in context_data["available_rooms"]:
            lines.append(f"- {room}")

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
        schedules = context_data["schedules"]

        # Limit schedules to prevent token overflow (max 100 schedules to keep under 8k token limit)
        # Prioritize schedules already filtered by smart filtering in _chat_with_groq
        max_schedules = 100
        schedules_to_show = schedules[:max_schedules]

        lines.append(
            f"\n### Class Schedules ({len(schedules_to_show)} shown, {len(schedules)} total):")

        # Format concisely to save tokens
        for s in schedules_to_show:
            subj = s.get("subjCode", "")
            prof = s.get("prof", "")
            day = s.get("day", "")
            start = s.get("start", "")
            end = s.get("end", "")
            room = s.get("room", "")
            sec = s.get("section", "")
            lines.append(
                f"- {prof} | {day} {start}-{end} | {subj} | {room} | Sec:{sec}")

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
    logger.info(f"extract_action: Found {len(matches)} JSON blocks in reply")
    if matches:
        try:
            logger.info(
                f"extract_action: Attempting to parse: {matches[-1][:200]}")
            action_data = json.loads(matches[-1])
            if "action" in action_data:
                logger.info(
                    f"extract_action: Successfully extracted action: {action_data.get('action')}")
                return action_data
            else:
                logger.warning(
                    f"extract_action: JSON found but no 'action' field: {action_data}")
        except json.JSONDecodeError as e:
            logger.warning(f"extract_action: JSON decode error: {e}")
    else:
        logger.info("extract_action: No JSON blocks found in reply")
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
    is_system_conversation: bool = False,
    user_role: str = 'admin',
    user_name: Optional[str] = None,
    intelligent_context: Optional[dict] = None,
    current_page: str = 'general'
) -> dict:
    """
    Send a message to CHE and get a response.

    Args:
        message:                The user's latest message
        history:                List of prior turns: [{"role": "user"|"assistant", "content": "..."}]
        context_data:           Optional dict with live system data (members, research, etc.)
        is_system_conversation: True if this is the Schedule Generation conversation
        user_role:              'admin' or 'user' (member)
        user_name:              Full name of the member (for filtering schedules)
        intelligent_context:    Second brain analysis with intent and minimal prompts

    Returns:
        dict with 'reply' (str), 'error' (bool), and optionally 'action' (dict)
    """
    # Try Gemini first (better free tier), fallback to Groq
    gemini_key = os.getenv("GOOGLE_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    if not gemini_key and not groq_key:
        return {
            "reply": "CHE is not configured. Please add GOOGLE_API_KEY or GROQ_API_KEY to environment variables.",
            "error": True
        }

    # Inject current_page into context_data
    if context_data is None:
        context_data = {}
    context_data['current_page'] = current_page
    logger.info(f"🔍 CHE Page Detection: current_page = '{current_page}'")

    # 🧠 Use intelligent context if provided (second brain approach)
    if intelligent_context:
        logger.info(
            f"🧠 Using Second Brain context - Intent: {intelligent_context.get('intent')}")
        system_prompt_override = intelligent_context.get('system_prompt')
    else:
        system_prompt_override = None

    # Try Gemini first (if available)
    if gemini_key:
        try:
            logger.info("Attempting Gemini API call...")
            return _chat_with_gemini(message, history, context_data, is_system_conversation, user_role, user_name, gemini_key, system_prompt_override)
        except Exception as e:
            logger.warning(f"Gemini failed: {str(e)[:200]}, trying Groq...")
            if groq_key:
                return _chat_with_groq(message, history, context_data, is_system_conversation, user_role, user_name, groq_key, system_prompt_override)
            else:
                return {"reply": f"Gemini error: {str(e)[:100]}", "error": True}

    # Fallback to Groq
    if groq_key:
        return _chat_with_groq(message, history, context_data, is_system_conversation, user_role, user_name, groq_key, system_prompt_override)

    return {"reply": "No API key configured", "error": True}


def _build_system_prompt(is_system_conversation, user_role, user_name, context_data, system_prompt_override=None):
    """Build system prompt based on conversation type and role"""
    # 🧠 If second brain provided a custom prompt, use it (already includes context)
    if system_prompt_override:
        return system_prompt_override

    # Otherwise use the old large prompts
    if user_role == 'user':
        system_content = MEMBER_QUERY_SYSTEM_PROMPT
        if context_data and 'schedules' in context_data and user_name:
            user_name_normalized = user_name.split(
                ',')[0].strip() if ',' in user_name else user_name.strip()
            member_schedules = [
                s for s in context_data['schedules']
                if s.get('prof', '').split(',')[0].strip() == user_name_normalized
            ]
            context_data['schedules'] = member_schedules
            context_data['member_name'] = user_name
    elif is_system_conversation:
        system_content = SCHEDULE_SYSTEM_PROMPT
    else:
        system_content = BASE_SYSTEM_PROMPT + SCHEDULE_REDIRECT_PROMPT

    if context_data:
        system_content += build_context_block(context_data)

    return system_content


def _clean_reply_from_json(reply):
    """Remove JSON action blocks from reply text"""
    import re
    reply = re.sub(r'```json\s*\{.*?\}\s*```', '',
                   reply, flags=re.DOTALL).strip()
    reply = re.sub(r'```json\s*\{[^`]*$', '', reply, flags=re.DOTALL).strip()
    reply = re.sub(r"Here's the plan.*$", '', reply,
                   flags=re.DOTALL | re.IGNORECASE).strip()
    reply = re.sub(r"Here is the.*$", '', reply,
                   flags=re.DOTALL | re.IGNORECASE).strip()
    return reply


def _chat_with_gemini(message, history, context_data, is_system_conversation, user_role, user_name, api_key, system_prompt_override=None):
    """Chat using Google Gemini API"""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Build system prompt (using second brain if available)
        system_content = _build_system_prompt(
            is_system_conversation, user_role, user_name, context_data, system_prompt_override)

        # Configure model with system instruction
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest',
            system_instruction=system_content
        )

        # Build conversation history for Gemini (limit to last 2 turns = 4 messages)
        gemini_history = []
        for turn in history[-4:]:
            role = turn.get("role")
            content = turn.get("content", "")
            if role == "user":
                gemini_history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_history.append({"role": "model", "parts": [content]})

        # Start chat with history
        chat = model.start_chat(history=gemini_history)

        # Send just the user message (system instruction is in model config)
        response = chat.send_message(message)

        reply = response.text.strip()

        # Extract action and clean reply
        action = extract_action(reply)
        if action:
            reply = _clean_reply_from_json(reply)

        result = {"reply": reply, "error": False, "provider": "gemini"}
        if action:
            result["action"] = action

        return result

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        raise


def _chat_with_groq(message, history, context_data, is_system_conversation, user_role, user_name, api_key, system_prompt_override=None):
    """Chat using Groq API (original implementation)"""
    try:
        from groq import Groq

        client = Groq(api_key=api_key)

        # Smart schedule filtering: If the message asks about a specific faculty, prioritize their schedules
        if context_data and context_data.get('schedules'):
            import re
            # Look for faculty name patterns in the message - improved to avoid capturing query words
            faculty_pattern = re.search(
                r'(?:is|are|does)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:free|available|teaching|teach|have|handle)', message, re.IGNORECASE)
            if not faculty_pattern:
                # Try alternative pattern for "show me [name]'s schedule" or "what's [name]'s schedule"
                faculty_pattern = re.search(
                    r"(?:show|what|tell).*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[\'\"]?s?\s+schedule", message, re.IGNORECASE)

            if faculty_pattern:
                faculty_search = faculty_pattern.group(1).lower().strip()
                # Filter schedules to prioritize mentioned faculty
                all_schedules = context_data['schedules']
                matching_schedules = [
                    s for s in all_schedules if faculty_search in s.get('prof', '').lower()]
                other_schedules = [
                    s for s in all_schedules if faculty_search not in s.get('prof', '').lower()]
                # Put matching schedules first, limit others to keep context reasonable
                context_data['schedules'] = matching_schedules + \
                    other_schedules[:50]

                # Debug: verify the faculty's schedules are included
                print(f"\n=== SMART FILTERING ===")
                print(f"Detected faculty query for: '{faculty_search}'")
                print(f"Matching schedules: {len(matching_schedules)}")
                if matching_schedules:
                    print(
                        f"Sample: {matching_schedules[0].get('prof')} - {matching_schedules[0].get('day')} {matching_schedules[0].get('start')}")
                print(
                    f"Total schedules in context: {len(context_data['schedules'])}")

        # Build the messages list for the API call
        # Choose system prompt based on user role and conversation type (or use second brain override)
        system_content = _build_system_prompt(
            is_system_conversation, user_role, user_name, context_data, system_prompt_override)

        messages = [{"role": "system", "content": system_content}]

        # Add conversation history (limit to last 2 turns = 4 messages)
        for turn in history[-4:]:
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

        # Remove the JSON action block from the reply text (so user doesn't see raw JSON)
        if action:
            import re
            # Remove complete ```json {...} ``` blocks from the reply
            reply = re.sub(r'```json\s*\{.*?\}\s*```',
                           '', reply, flags=re.DOTALL).strip()
            # Also remove incomplete JSON blocks (in case response was cut off)
            reply = re.sub(r'```json\s*\{[^`]*$',
                           '', reply, flags=re.DOTALL).strip()
            # Remove trailing "Here's the plan..." or similar phrases that precede JSON
            reply = re.sub(r"Here's the plan.*$", '', reply,
                           flags=re.DOTALL | re.IGNORECASE).strip()
            reply = re.sub(r"Here is the.*$", '', reply,
                           flags=re.DOTALL | re.IGNORECASE).strip()

        result = {"reply": reply, "error": False}
        if action:
            result["action"] = action

        return result

    except Exception as e:
        logger.error(f"CHE service error: {e}")
        error_msg = str(e)

        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            return {
                "reply": "Invalid API key. Please check the GROQ_API_KEY in your environment settings.",
                "error": True
            }
        if "rate_limit" in error_msg.lower():
            return {
                "reply": "I'm receiving too many requests right now. Please wait a moment and try again. 🕒",
                "error": True
            }
        if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            return {
                "reply": "Connection issue. Please check your internet connection and try again.",
                "error": True
            }

        return {
            "reply": f"Something went wrong on my end. Please try again. (Error: {error_msg[:100]})",
            "error": True
        }


# ── Conversation Persistence ───────────────────────────────────────────────────

def get_or_create_conversation(user_id: str, session_id: str = None) -> Optional[str]:
    """
    Get the most recent conversation for a user or create a new one.
    Returns conversation_id.
    """
    from app import supabase

    try:
        # Try to get the most recent non-archived conversation
        result = supabase.table('che_conversations').select('id').eq('user_id', user_id).eq(
            'is_archived', False).order('updated_at', desc=True).limit(1).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]['id']

        # Create new conversation
        new_conv = supabase.table('che_conversations').insert({
            'user_id': user_id,
            'title': 'New Conversation'
        }).execute()

        if new_conv.data and len(new_conv.data) > 0:
            return new_conv.data[0]['id']

    except Exception as e:
        logger.error(f"Error getting/creating conversation: {e}")

    return None


def save_message(conversation_id: str, role: str, content: str, metadata: dict = None) -> bool:
    """
    Save a message to the database.
    """
    from app import supabase

    try:
        supabase.table('che_messages').insert({
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'metadata': metadata or {}
        }).execute()
        return True
    except Exception as e:
        logger.error(f"Error saving message: {e}")
        return False


def load_conversation_history(conversation_id: str, limit: int = 50) -> list:
    """
    Load message history from database.
    Returns list of {role, content} dicts.
    """
    from app import supabase

    try:
        result = supabase.table('che_messages').select('role, content').eq(
            'conversation_id', conversation_id).order('created_at', desc=False).limit(limit).execute()

        if result.data:
            return [{'role': msg['role'], 'content': msg['content']} for msg in result.data]
    except Exception as e:
        logger.error(f"Error loading conversation history: {e}")

    return []


def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """
    Delete a conversation and all its messages (handled by CASCADE).
    """
    from app import supabase

    try:
        supabase.table('che_conversations').delete().eq(
            'id', conversation_id).eq('user_id', user_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return False
