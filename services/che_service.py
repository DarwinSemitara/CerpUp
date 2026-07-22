"""
CHE (CERP AI Assistant) Service
Uses Groq API with Llama 3.3 70B for full language understanding.
Responses are restricted to CERP-related topics only.
"""

import os
import json
import logging
from typing import Optional
from groq import Groq

logger = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────────
# This is what shapes CHE's personality and restricts its scope.

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

## What you CANNOT help with:
- Topics completely unrelated to CERP, CHE, or academic/research work at UPLB
- General knowledge questions (science trivia, geography, cooking, etc.)
- Personal advice, entertainment, or unrelated technical support
- Anything outside the domain of this system and its users

## When a user asks something off-topic:
Politely decline and redirect them. Be friendly but firm. Do NOT answer off-topic questions even partially. Use a short, direct message like:
"That's outside what I can help with here. I'm focused on CERP system topics — research, members, schedules, FSRs, and extension activities. Try asking me something about the system!"

## Tone and style:
- Professional but approachable
- Concise and clear — avoid unnecessary filler
- Use bullet points or numbered lists when listing multiple items
- When you don't have specific data, say so clearly and suggest where to find it in the system
- You understand Filipino/Tagalog mixed with English (code-switching) — respond in whatever language the user uses

## Important:
- You do NOT have live access to the database unless data is provided in the message
- When data is passed in context (members list, research records, etc.), use it to give accurate answers
- Never fabricate specific names, numbers, or records — only use what is provided
- If asked about something you need data for but none was provided, ask the admin to check the relevant section of the system
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
        for m in context_data["members"][:30]:  # cap at 30 to save tokens
            name = m.get(
                "name") or f"{m.get('firstName', '')} {m.get('lastName', '')}".strip()
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
        for s in context_data["schedules"][:20]:
            subj = s.get("subjCode", "")
            prof = s.get("prof", "")
            day = s.get("day", "")
            start = s.get("start", "")
            end = s.get("end", "")
            room = s.get("room", "")
            lines.append(f"- {subj} | {prof} | {day} {start}-{end} | {room}")

    if context_data.get("news"):
        lines.append(
            f"\n### Recent News/Events ({len(context_data['news'])} total):")
        for n in context_data["news"][:10]:
            title = n.get("title", "Untitled")
            date = n.get("date") or n.get("createdAt", "")
            lines.append(f"- {title} | {date}")

    return "\n".join(lines)


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
        dict with 'reply' (str) and 'error' (bool)
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
            max_tokens=1024,
            top_p=0.9,
        )

        reply = response.choices[0].message.content.strip()
        return {"reply": reply, "error": False}

    except Exception as e:
        logger.error(f"CHE service error: {e}")
        error_msg = str(e)

        # Friendly error messages for common issues
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
