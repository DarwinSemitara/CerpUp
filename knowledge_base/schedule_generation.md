# Schedule Generation Guide

## When to Use
User wants to generate a complete semester schedule for all faculty and sections.

## What You Need
To generate a schedule, you MUST collect these 4 parameters:
1. **reference_semester** - Which semester to copy from (1 or 2)
2. **reference_school_year** - Which year to copy from (e.g., "2026-2027")
3. **target_semester** - Which semester to generate for (1 or 2)
4. **target_school_year** - Which year to generate for (e.g., "2027-2028")

## Response Template
When user asks to generate a schedule:

"I'll generate a schedule for [target] using [reference] as the template. The system will create conflict-free timetables using the genetic algorithm."

Then output this JSON action (the form will appear automatically):
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

## Important Rules
- NEVER load schedules into context for generation requests
- The backend handles all data loading after user confirms
- Keep response under 50 words
- Don't explain how GA works unless asked
- Parse year formats carefully: "2027-2028" or "2027"

## Example Queries
- "generate schedule for 1st semester 2027-2028 using 2nd semester 2026-2027"
- "create schedule for next semester"
- "generate timetable for sem 2"
