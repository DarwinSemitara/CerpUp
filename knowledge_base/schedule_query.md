# Schedule Query Guide

## When to Use
User asks about faculty availability, teaching schedules, or time conflicts.

## What to Do
1. **Identify the professor** mentioned in the query
2. System will load ONLY that professor's schedules
3. Answer based on the schedule data provided in context

## Response Guidelines
- Show actual class times from the data
- Use 12-hour format (7:30 AM, not 07:30)
- Calculate free time between classes
- Don't make up schedules - use only what's provided
- If no data for a professor, say "I don't see schedules for [name] in the current semester"

## Format for Schedule Display
```
Professor [Name]'s [Day] schedule:
- 7:30 AM - 9:00 AM (1.5 hrs): [Subject] in [Room], Section [X]
- (FREE: 9:00 AM - 1:00 PM, 4 hrs)
- 1:00 PM - 2:30 PM (1.5 hrs): [Subject] in [Room], Section [Y]
```

## Room Availability Queries
If user asks "What rooms are free at [time]?":
- Check all schedules for that time slot
- List occupied rooms with professor/subject
- List available rooms from available_rooms context

## Example Queries
- "Is Aaron free on Monday?"
- "What time does Prof Smith teach?"
- "Show me Dr. Jones schedule"
- "What rooms are available at 2 PM?"
- "Does anyone have classes on Friday afternoon?"
