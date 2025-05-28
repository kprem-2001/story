# core/story_agents.py
from crewai import Agent
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Attempt to import SerperDevTool
try:
    from crewai_tools import SerperDevTool
    SERPER_AVAILABLE = True
except ImportError:
    logger.warning("SerperDevTool could not be imported. Web search functionality will be disabled. "
                   "Ensure 'crewai_tools' is installed if you need web search.")
    SERPER_AVAILABLE = False


class StorytellingAgents:
    def __init__(self, xai_api_key_for_env_setting: str):
        self.xai_model_identifier = "grok-3-mini"
        self.model_string_for_litellm = f"openai/{self.xai_model_identifier}"
        
        self.search_tool = None
        if SERPER_AVAILABLE and os.getenv("SERPER_API_KEY"):
            try:
                self.search_tool = SerperDevTool()
                logger.info("SerperDevTool initialized successfully for web search.")
            except Exception as e:
                logger.warning(f"Failed to initialize SerperDevTool even though SERPER_API_KEY is set: {e}")
                self.search_tool = None
        elif not os.getenv("SERPER_API_KEY") and SERPER_AVAILABLE:
            logger.info("SERPER_API_KEY not found in environment. Web search tool will not be available.")
        elif not SERPER_AVAILABLE:
            logger.info("SerperDevTool import failed. Web search tool will not be available.")

    def _get_llm_for_agent(self):
        return self.model_string_for_litellm

    def prompt_architect_agent(self) -> Agent:
        agent_tools = [self.search_tool] if self.search_tool else []
        return Agent(
            role="Master Prompt Architect for Collaborative Storytelling with Research Capability",
            goal="Synthesize user inputs, current story state (genre, setting, tone), character profiles, narration style directives (including persona, characteristics, and 'inspired by' authors/works), and recent conversation history into a single, extremely detailed, and actionable master prompt. This master prompt will serve as the complete blueprint for the Scene Skeleton Agent to outline the next story segment or full story. It must ensure all constraints and creative directions are clearly embedded, especially the nuances of the selected narration style. **If 'inspired by' authors/styles are unfamiliar or need more depth, use the web search tool to gather information about their characteristic styles, themes, and typical vocabulary to inform the prompt accurately.**",
            backstory="You are a renowned literary strategist and prompt engineer, known for your ability to translate abstract ideas and collaborative discussions into precise, inspiration-rich instructions for creative AI writers. Your prompts are legendary for their clarity and effectiveness in eliciting desired narrative outcomes and styles. You understand how to guide AI to adopt specific voices and tones based on descriptions and authorial inspirations, leveraging web research when necessary to deeply understand stylistic influences.",
            verbose=False,
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            tools=agent_tools,
            max_iter=3
        )

    def scene_skeleton_agent(self) -> Agent:
        return Agent(
            role="Expert Story Outliner and Narrative Beat Planner",
            goal="Analyze the master prompt from the Prompt Architect and deconstruct it into a concise, logical sequence of 3-5 key story beats for the upcoming scene or story segment. Each beat should be a descriptive sentence capturing a core action, revelation, or emotional shift, ensuring they align with the overall narrative direction and pacing suggested in the master prompt. Output this as a JSON formatted list of strings.",
            backstory="You are a seasoned screenwriter and novelist, famed for your ability to structure compelling narratives. You see the 'bones' of a story and can lay out a clear path from one plot point to the next, ensuring a satisfying narrative flow and building appropriate tension or emotion as per the master prompt.",
            verbose=False, 
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=2
        )

    def scene_expansion_agent(self) -> Agent:
        return Agent(
            role="Immersive Narrative Prose Writer and Master Stylist",
            goal="Take a list of story beats and the master prompt (containing narration style details: persona, characteristics, and 'inspired by' authors/works). For each beat, expand it into a rich, descriptive paragraph. Concatenate these into a single, cohesive narrative segment. The narration MUST meticulously emulate the specified narration style by drawing deeply from the 'inspired by' authors/works and the 'tone' characteristics provided in the master prompt. Output ONLY the narrated story segment, ensuring it ends with impact (Cliffhanger, Conflict, Poignant, or Revelation) as guided by the master prompt.",
            backstory="You are a celebrated author known for your chameleonic ability to write in diverse, distinctive voices and create deeply immersive worlds. Readers often say your prose makes them feel like they are living the story. You excel at capturing the essence of inspirational authors and styles.",
            verbose=False, 
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=3
        )

    def dialogue_polish_agent(self) -> Agent:
        return Agent(
            role="Specialist Dialogue Scripter and Character Voice Expert",
            goal="Review and refine all dialogue within a provided scene text to make it exceptionally sharp, natural-sounding, and deeply reflective of each character's unique personality, motivations, and background (as per their profiles, which will be part of the context). Ensure dialogue aligns with the scene's emotional context and the overall narration style.",
            backstory="You're the go-to dialogue doctor in Hollywood and Broadway. You have an unparalleled ear for how real people (and fictional ones) talk, and your revisions make characters leap off the page, their voices distinct and memorable.",
            verbose=False, 
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=2
        )

    def voice_keeper_agent(self) -> Agent:
        return Agent(
            role="Narrative Style Quality Assurance Guardian",
            goal="Critically analyze a generated scene text against a target narration style (defined by its persona name, key characteristics/tone, and 'inspired by' authors/works). Provide a precise assessment of how well the scene text emulates the target style, including a match quality (High/Medium/Low), a confidence_score (0-100), and specific, actionable feedback if the match is not High. Base your analysis on your understanding of the 'inspired_by' authors/works. Output this assessment as a JSON object.",
            backstory="You are a meticulous editor with an impeccable sense for literary style and voice. No stylistic deviation, however subtle, escapes your notice. Your feedback is vital for maintaining narrative consistency and quality.",
            verbose=False, 
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=3
        )

    def final_polisher_agent(self) -> Agent:
        return Agent(
            role="Master Style Imitator and Narrative Refinement Artist",
            goal="Take a scene text, feedback from the Voice Keeper Agent, and the target narration style details (persona, characteristics, 'inspired by' authors/works). Meticulously revise the scene text to perfectly align with and embody the target narration style, addressing all noted discrepancies and drawing deeply from your knowledge of the 'inspired by' sources. The final output should be a stylistically impeccable version of the scene.",
            backstory="You are a literary chameleon of the highest caliber, but for good! You can adopt any author's voice and polish a text until it gleams with stylistic perfection. Your work is seamless and true to the target style.",
            verbose=False, 
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=3
        )

    def plot_architect_agent(self) -> Agent:
        """New agent specifically for plot structure and story planning"""
        return Agent(
            role="Master Plot Architect and Story Structure Expert",
            goal="Design a compelling plot structure based on the enhanced genre, setting, tone, and character profiles. Create a detailed story arc including: opening hook, inciting incident, rising action beats, climax, and resolution. Ensure the plot leverages genre conventions while adding surprising twists.",
            backstory="You are a legendary story structure expert who has analyzed thousands of successful narratives. You understand the deep patterns that make stories compelling and know how to craft plots that keep readers engaged from first page to last.",
            verbose=False,
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            max_iter=2
        )

    def style_researcher_agent(self) -> Agent:
        """New agent that researches author styles"""
        agent_tools = [self.search_tool] if self.search_tool else []
        return Agent(
            role="Literary Style Researcher and Analysis Expert",
            goal="When given an author or style to emulate, use web search to research their distinctive writing characteristics, common themes, sentence structures, vocabulary choices, and narrative techniques. Compile a comprehensive style guide that other agents can use to authentically reproduce that style.",
            backstory="You are a literary scholar with expertise in stylistic analysis. You can identify and articulate the unique voice of any author, from their word choices to their thematic preoccupations.",
            verbose=False,
            allow_delegation=False,
            llm=self._get_llm_for_agent(),
            tools=agent_tools,
            max_iter=3
        )

    def full_story_compiler_agent(self) -> Agent:
        agent_tools = [self.search_tool] if self.search_tool else []
        compiler_model_string = f"openai/{self.xai_model_identifier}"
        return Agent(
            role="Epic Story Weaver and Grand Narrator with Research Prowess",
            goal="Take a comprehensive set of final story parameters (genre, setting, overall tone, character profiles, and a CRITICAL final narration style including persona, characteristics, and 'inspired by' authors/works) and weave them into a complete, cohesive, and engaging full-length story. **If needed for deep style emulation or to enrich world-building details, use your web search tool to research the 'inspired_by' authors/works or relevant contextual information.** The entire narrative MUST be told in the specified final narration style.",
            backstory="You are the Bard of Bards, capable of taking scattered elements and forging them into a legendary saga. Your command of narrative, style, and ability to synthesize information (including from web research) is unparalleled.",
            verbose=False,
            allow_delegation=False,
            llm=compiler_model_string,
            tools=agent_tools,
            max_iter=1
        )