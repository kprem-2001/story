# core/prompt_enhancer.py
import logging
from typing import Dict, Optional
from .story_agents import StorytellingAgents
from crewai import Crew, Process, Task

logger = logging.getLogger(__name__)

def enhance_story_parameters(
    xai_api_key: str,
    genre: str,
    setting: str,
    tone: str
) -> Dict[str, str]:
    """
    Takes basic user inputs and enhances them into rich, detailed prompts
    suitable for story generation.
    """
    logger.info("Enhancing story parameters with AI agents...")
    
    agents = StorytellingAgents(xai_api_key)
    
    # Create a specialized enhancement prompt
    enhancement_prompt = f"""
    User provided these basic story elements:
    - Genre: {genre}
    - Setting: {setting}
    - Tone: {tone}
    
    Your task is to enhance and expand these into rich, detailed descriptions that will guide story creation:
    
    1. GENRE Enhancement: Take '{genre}' and expand it into a detailed genre description including:
       - Specific sub-genres and genre conventions
       - Typical themes and tropes for this genre
       - Audience expectations
       - 2-3 example works in this genre for reference
    
    2. SETTING Enhancement: Take '{setting}' and expand it into a vivid world description including:
       - Time period specifics
       - Geographic/spatial details
       - Cultural and societal elements
       - Technological/magical level (if applicable)
       - Atmosphere and mood of the setting
       - 3-5 specific locations that could feature in the story
    
    3. TONE Enhancement: Take '{tone}' and expand it into a comprehensive tonal guide including:
       - Specific emotional registers
       - Pacing preferences (fast/slow, building tension, etc.)
       - Level of humor, darkness, romance, action, etc.
       - Target audience maturity level
       - Comparable works with similar tone
    
    4. THEMATIC SUGGESTIONS: Based on the genre, setting, and tone, suggest:
       - 2-3 core themes that would work well
       - Central conflicts that naturally arise from this combination
       - Character archetypes that fit this story world
    
    Output as a structured enhancement that maintains the user's core vision while adding professional storytelling depth.
    """
    
    try:
        # Use the prompt architect agent to enhance the parameters
        enhancement_task = Task(
            description=enhancement_prompt,
            expected_output="Enhanced story parameters with rich details for each element",
            agent=agents.prompt_architect_agent()
        )
        
        enhancement_crew = Crew(
            agents=[agents.prompt_architect_agent()],
            tasks=[enhancement_task],
            process=Process.sequential,
            verbose=1
        )
        
        result = enhancement_crew.kickoff()
        
        # Parse the enhanced parameters
        if result and hasattr(result, 'raw_output'):
            enhanced_text = result.raw_output
            
            # Extract enhanced sections (you might want to make this more sophisticated)
            return {
                "enhanced_genre": extract_section(enhanced_text, "GENRE"),
                "enhanced_setting": extract_section(enhanced_text, "SETTING"),
                "enhanced_tone": extract_section(enhanced_text, "TONE"),
                "suggested_themes": extract_section(enhanced_text, "THEMATIC")
            }
    except Exception as e:
        logger.error(f"Error enhancing parameters: {e}")
        # Fallback to original values
        return {
            "enhanced_genre": genre,
            "enhanced_setting": setting,
            "enhanced_tone": tone,
            "suggested_themes": ""
        }

def extract_section(text: str, section_name: str) -> str:
    """Helper to extract sections from enhanced text"""
    # Simple extraction - you might want to improve this
    lines = text.split('\n')
    capturing = False
    section_content = []
    
    for line in lines:
        if section_name in line.upper():
            capturing = True
            continue
        elif any(marker in line.upper() for marker in ['GENRE', 'SETTING', 'TONE', 'THEMATIC']) and capturing:
            break
        elif capturing:
            section_content.append(line)
    
    return '\n'.join(section_content).strip()