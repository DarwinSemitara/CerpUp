# Schedule Generation Guide

## When to Use
User wants to generate a complete semester schedule for all faculty and sections.

## CRITICAL: Check Current Page First!

Before doing anything, look at the BOTTOM of this message in the "Current System Data" section. Find the line that says "Current Page: [something]".

### If current page is NOT "schedule" (it says "dashboard", "admin", "general", etc.):

**Step 1:** Write ONE sentence saying the redirect is needed.

**Step 2:** IMMEDIATELY after your sentence, output EXACTLY this JSON block (copy it exactly):

```json
{
  "action": "show_redirect_form",
  "message": "Schedule generation is only available on the Schedule page. Would you like me to take you there?",
  "target_page": "schedule"
}
```

**Your complete response should look like:**

Schedule generation is only available on the Schedule page. Would you like me to take you there?

```json
{
  "action": "show_redirect_form",
  "message": "Schedule generation is only available on the Schedule page. Would you like me to take you there?",
  "target_page": "schedule"
}
```

### If current page IS "schedule":

**Step 1:** Write ONE sentence about helping with generation.

**Step 2:** IMMEDIATELY after your sentence, output EXACTLY this JSON block:

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

**Your complete response should look like:**

I'll help you generate a schedule. Please fill in the details in the form.

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

## CRITICAL RULES
1. You MUST output the JSON code block (the part with ```json)
2. The JSON must come AFTER your text message
3. Do NOT explain the JSON or describe it - just output it
4. Do NOT ask the user to type anything - the form will appear automatically
5. Copy the JSON EXACTLY as shown above
