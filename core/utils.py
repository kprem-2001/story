# core/utils.py
import re

def is_primarily_story_content(text: str) -> tuple[bool, str | None]:
    if not text or not isinstance(text, str):
        return False, None
        
    potential_story_part = text
    preambles = [
        r"alright, let's get started with the story!", r"alright, let's start the story with the first slide.",
        r"here's the first slide:", r"here's the next slide:", r"continuing with the story...",
        r"slide \d+:"
    ]
    for preamble_pattern in preambles:
        match = re.search(preamble_pattern, potential_story_part, re.IGNORECASE)
        if match:
            potential_story_part = potential_story_part[match.end():].strip()
            break 

    question_phrases_boundary = [
        r"\(word count: approximately \d+\)", r"how was that\?", r"are you happy with this slide",
        r"would you like to change, add, or update anything", r"would you like me to continue",
        r"would you like to interact", r"would you like any modifications", r"shall i continue", 
        r"should i continue", r"what do you think", "before i continue", "let me know"
    ]
    earliest_question_start = len(potential_story_part)
    for phrase_pattern in question_phrases_boundary:
        match = re.search(phrase_pattern, potential_story_part, re.IGNORECASE)
        if match and match.start() < earliest_question_start:
            earliest_question_start = match.start()
            
    if earliest_question_start < len(potential_story_part):
        potential_story_part = potential_story_part[:earliest_question_start].strip()

    if not potential_story_part: return False, None
    story_part_lower = potential_story_part.lower()
    
    confirmation_starts = ["✅", "ok,", "alright,", "great,", "i see", "perfect!", "understood.", "sounds good.", "sure,"]
    if any(story_part_lower.startswith(start) for start in confirmation_starts): return False, None
        
    if len(potential_story_part.split()) < 15: # Reduced slightly for short affirmations
        # Check if it's not just a question or very short statement
        if "?" in potential_story_part or story_part_lower.count(".") <=1:
             return False, None # Likely not substantial story content

    lingering_question_phrases = ["would you like", "shall i", "how was that"]
    if any(phrase in story_part_lower for phrase in lingering_question_phrases):
        if story_part_lower.endswith("?") and any(phrase in story_part_lower[-50:] for phrase in lingering_question_phrases):
            return False, None

    return True, potential_story_part.strip()