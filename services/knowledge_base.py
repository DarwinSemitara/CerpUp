"""
Knowledge Base Service for CHE Assistant

Provides static knowledge without database queries, reducing token usage.
Implements "second brain" approach for intent-based knowledge retrieval.
"""

import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

KNOWLEDGE_BASE_DIR = "knowledge_base"


def detect_intent(message: str) -> str:
    """
    Detect user intent from their message to determine which knowledge to load.
    
    Returns:
        Intent category: 'schedule_generation', 'schedule_query', 'research', 'general'
    """
    message_lower = message.lower()
    
    # Schedule generation intent
    generation_keywords = ['generate', 'create schedule', 'make schedule', 'build schedule']
    if any(keyword in message_lower for keyword in generation_keywords):
        return 'schedule_generation'
    
    # Schedule query intent (availability, teaching times)
    query_keywords = ['free', 'available', 'teach', 'teaching', 'schedule for', 
                     'what time', 'when does', 'show schedule', 'monday', 'tuesday', 
                     'wednesday', 'thursday', 'friday', 'saturday', 'room available']
    if any(keyword in message_lower for keyword in query_keywords):
        return 'schedule_query'
    
    # Research/Extensions intent
    research_keywords = ['research', 'extension', 'submit', 'publication', 'paper', 
                        'project', 'community service', 'outreach']
    if any(keyword in message_lower for keyword in research_keywords):
        return 'research'
    
    # Default: general conversation
    return 'general'


def load_knowledge(intent: str) -> Dict[str, str]:
    """
    Load knowledge file based on detected intent.
    
    Args:
        intent: Detected intent category
        
    Returns:
        Dictionary with 'content' (knowledge text) and 'requires_data' (what data to load)
    """
    knowledge_files = {
        'schedule_generation': 'schedule_generation.md',
        'schedule_query': 'schedule_query.md',
        'research': 'research_extensions.md',
        'general': 'general_conversation.md',
        'system_info': 'system_info.md'
    }
    
    filename = knowledge_files.get(intent, 'general_conversation.md')
    filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Determine what data needs to be loaded
        requires_data = determine_data_requirements(intent, content)
        
        return {
            'content': content,
            'requires_data': requires_data,
            'intent': intent
        }
    except FileNotFoundError:
        logger.warning(f"Knowledge file not found: {filepath}, using fallback")
        return {
            'content': load_fallback_knowledge(),
            'requires_data': [],
            'intent': 'general'
        }
    except Exception as e:
        logger.error(f"Error loading knowledge base: {e}")
        return {
            'content': load_fallback_knowledge(),
            'requires_data': [],
            'intent': 'general'
        }


def determine_data_requirements(intent: str, knowledge_content: str) -> list:
    """
    Determine what live data needs to be fetched based on intent.
    
    Returns:
        List of data types needed: ['schedules', 'rooms', 'members', etc.]
    """
    if intent == 'schedule_generation':
        # Generation doesn't need data upfront - form will collect parameters
        return []
    
    elif intent == 'schedule_query':
        # Need schedules and room list for availability queries
        return ['schedules', 'rooms']
    
    elif intent == 'research':
        # Just navigation help, no data needed
        return []
    
    elif intent == 'general':
        # No data needed for casual conversation
        return []
    
    return []


def load_fallback_knowledge() -> str:
    """
    Fallback knowledge when files can't be loaded.
    """
    return """You are CHE, the CERP AI assistant for UPLB.

I help with:
- Class scheduling and availability queries
- Research and extension submissions
- System navigation and guidance

How can I help you today?"""


def get_minimal_system_prompt(intent: str) -> str:
    """
    Get a minimal system prompt based on intent (replaces the 3,500 token monster).
    
    Args:
        intent: Detected intent category
        
    Returns:
        Short system prompt (< 200 tokens)
    """
    base = "You are CHE, CERP's AI assistant for UPLB College of Human Ecology. "
    
    if intent == 'schedule_generation':
        return base + """Help generate class schedules. Collect: reference semester/year and target semester/year. 
Output JSON action with these 4 parameters. Keep response under 50 words."""
    
    elif intent == 'schedule_query':
        return base + """Answer schedule and availability questions using the data provided. 
Show actual times from schedules. Use 12-hour format. Be specific and accurate."""
    
    elif intent == 'research':
        return base + """Guide users on submitting research/extensions. Provide clear step-by-step navigation help. 
Keep instructions concise."""
    
    else:  # general
        return base + """Be friendly and helpful. Guide users to available features. 
Keep responses brief (under 30 words for greetings). Use natural tone."""


# ── Intent-Based Response Builder ─────────────────────────────────────────────

def build_intelligent_context(message: str, user_role: str = 'admin', 
                             is_system_conversation: bool = False) -> Dict:
    """
    Build context intelligently based on user intent.
    This is the "second brain" - decides what the AI needs before calling it.
    
    Args:
        message: User's message
        user_role: 'admin' or 'user'
        is_system_conversation: True if in schedule generation mode
        
    Returns:
        Dictionary with 'system_prompt', 'requires_data', 'knowledge', 'intent'
    """
    # Detect what the user wants
    intent = detect_intent(message)
    
    logger.info(f"CHE Second Brain - Detected intent: '{intent}' for message: '{message[:50]}...'")
    
    # Load relevant knowledge
    knowledge = load_knowledge(intent)
    
    # Build minimal system prompt
    system_prompt = get_minimal_system_prompt(intent)
    
    # Add the knowledge content to system prompt
    full_prompt = f"{system_prompt}\n\n## Task-Specific Guidance:\n{knowledge['content']}"
    
    return {
        'system_prompt': full_prompt,
        'requires_data': knowledge['requires_data'],
        'knowledge': knowledge['content'],
        'intent': intent,
        'token_estimate': len(full_prompt.split()) * 1.3  # Rough estimate
    }
