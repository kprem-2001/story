# core/langchain_chains.py
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain

# Import the Bennet specific prompt from core.prompts
from core.prompts import BENNET_STYLE_INITIAL_SCENE_PROMPT 

# --- Configuration for Grok/xAI LLM ---
XAI_BASE_URL = "https://api.x.ai/v1" 
XAI_MODEL_NAME = "grok-3-mini" 

def get_grok_llm(api_key: str, temperature: float = 0.7):
    if not api_key:
        raise ValueError("xAI API key not provided for Langchain LLM initialization.")
    return ChatOpenAI(
        model_name=XAI_MODEL_NAME,
        openai_api_key=api_key, 
        openai_api_base=XAI_BASE_URL,
        temperature=temperature,
    )

# --- Prompt Templates ---

# Agent 2.1: Author Style Snippet Generator
author_style_snippet_template = """
You are a literary analyst. Generate a concise (around 200-300 words) narrative passage 
that clearly exemplifies the distinct writing style of the author: {author_name}.
Focus on characteristic vocabulary, sentence structure, pacing, common themes (if applicable to style), 
and typical narrative voice. This passage should serve as a strong example for another AI to emulate.
Do not write a biography or analysis of the author; write a piece *as if* it were by them.
Output only the narrative passage itself.
"""
AUTHOR_STYLE_SNIPPET_PROMPT = PromptTemplate(
    input_variables=["author_name"], 
    template=author_style_snippet_template
)

# Agent 3: Plot Outline Generator
plot_outline_template = """
You are a master story plotter. Based on the following story elements:
- Genre: {genre}
- Setting: {setting}
- Overall Story Tone: {tone}
- Characters: {characters_summary}

Generate a concise 5-7 point plot outline for a compelling short story.
This outline should include:
1. Inciting Incident
2. Rising Action (2-3 key points)
3. Climax
4. Falling Action (1-2 points)
5. Resolution

For each point, provide a brief (1-2 sentence) description.
Output only the plot outline.
"""
PLOT_OUTLINE_PROMPT = PromptTemplate(
    input_variables=["genre", "setting", "tone", "characters_summary"],
    template=plot_outline_template
)

# Agent 4: Story Draft Generator (Uses more explicit data unpacking instructions)
story_draft_template = """
You are a masterful and meticulous storyteller AI.

IMPORTANT SCENARIO DIRECTIVE:
{initial_scene_directive_draft} 
If the above directive is not empty, it is MANDATORY for shaping the opening of your story. You MUST use the protagonist type, setting, themes, and opening moment described. This directive OVERRIDES any conflicting generic genre/setting/character information if it's provided for an initial scene.

Your primary task is to write a complete and cohesive story based ONLY on the following parameters and plot outline.

--- NARRATION STYLE GUIDE (CRITICAL - ADHERE STRICTLY FOR THE ENTIRE STORY) ---
Style Persona: '{narration_name_display}'
Core Characteristics & Specific Writing Guidelines: 
{narration_tone}  
Literary Inspiration: '{narration_inspired_by}'
Source Text Snippet for Stylistic Emulation (Study this carefully for voice, sentence structure, and tone):
{narration_style_snippet_instruction} 
--- END NARRATION STYLE GUIDE ---

FINAL STORY PARAMETERS (Use these if not overridden by the SCENARIO DIRECTIVE for the opening):
- Genre: {genre}
- Setting: {setting}
- Overall Story Tone (should align with Narration Style Guide): {tone}

FINAL CHARACTERS (Use these if not overridden by the SCENARIO DIRECTIVE for the opening, or adapt them to fit):
{characters_full_profiles}

CRITICAL PLOT OUTLINE TO FOLLOW (Expand these beats into a narrative, infused with the above Narration Style):
{plot_outline}

Based ONLY on ALL the above details, write the full story (approx. 1000-1500 words).
Begin the story directly. No preambles, meta-commentary, or questions to the user.
"""
STORY_DRAFT_PROMPT = PromptTemplate(
    input_variables=[
        "initial_scene_directive_draft", 
        "genre", "setting", "tone",
        "narration_name_display", "narration_tone", "narration_inspired_by", "narration_style_snippet_instruction",
        "characters_full_profiles",
        "plot_outline", # Output from plot_outline_chain
    ],
    template=story_draft_template
)

# Agent 5: Story Refinement Generator (CORRECTED to use {plot_outline})
story_refinement_template = """
You are an expert story editor with an impeccable eye for detail. Review the following story draft:

--- STORY DRAFT START ---
{story_draft}
--- STORY DRAFT END ---

The story MUST be refined to strictly adhere to ALL of the following:

--- NARRATION STYLE GUIDE (MANDATORY ADHERENCE) ---
Style Persona: '{narration_name_display}'
Core Characteristics & Specific Writing Guidelines for this Style: 
{narration_tone}
Literary Inspiration: '{narration_inspired_by}'
Source Text Snippet for Stylistic Emulation (CRITICAL - Ensure refined draft's voice matches this):
{narration_style_snippet_instruction_refine}
--- END NARRATION STYLE GUIDE ---

=== SCENARIO & PLOT DIRECTIVES (Check for adherence in the draft) ===
Initial Scene Directive (If this shaped the story's opening, ensure the refined draft maintains its core elements and intent):
{initial_scene_directive_refine}

Main Plot Outline (The refined story MUST still follow this original plot structure):
{plot_outline} 
--- END SCENARIO & PLOT DIRECTIVES ---

=== CHARACTER CONSISTENCY (Check for adherence in the draft) ===
Active Characters & Their Core Profiles (Ensure their actions/dialogue in the refined draft are consistent with these):
{characters_full_profiles_for_refinement_context}
--- END CHARACTER CONSISTENCY ---

Contextual Story Elements (for reference):
- Genre: {genre}
- Setting: {setting}
- Overall Tone: {tone}

*** YOUR REFINEMENT TASK ***
Meticulously rewrite and polish the draft. Your primary focus is:
1.  **Absolute Adherence to the Narration Style Guide above.** This is paramount.
2.  **Faithful Adherence to Plot Outline and Initial Scene Directives (if applicable).**
3.  **Deep Character Consistency** based on their provided profiles.
4.  Enhanced Imagery, Sensory Details, Pacing, Flow, Emotional Impact.
5.  Elimination of Clichés, Awkward Phrasing, and anything "AI-generated." Ensure Chekhov's Gun principle is respected if noted in guidelines.
6.  Cohesion and compelling language.

Do NOT add new major plot points or fundamentally change the story's core events from the draft. Elevate the existing material based on ALL the provided directives.
Output ONLY the revised story. No preamble.
"""
STORY_REFINEMENT_PROMPT = PromptTemplate(
    input_variables=[
        "story_draft", # From previous chain (story_draft_chain)
        "plot_outline", # From first chain (plot_outline_chain), passed through by SequentialChain
        "initial_scene_directive_refine", 
        "narration_name_display", "narration_tone", "narration_inspired_by", "narration_style_snippet_instruction_refine",
        "characters_full_profiles_for_refinement_context", 
        "genre", "setting", "tone",
    ],
    template=story_refinement_template
)

# Agent E: Slide/Segment Generator (Uses more explicit data unpacking instructions)
slide_generation_template = """
System Note: You are a creative storytelling AI. Your primary goal is to co-create a story with the user, segment by segment.

**STEP 1: ANALYZE USER'S LATEST REQUEST**
User's Latest Request/Input: {user_input}
   - Is this a command/directive (e.g., "System Update: ...", "System Directive: Style changed...")?
   - Is this a request to start a new story or apply an initial scene directive?
   - Is this a request to continue the existing story (e.g., "next slide", "continue", "what does Tom do?")?
   - Is this a question about the story or characters?
   - Is this a request to revise the previous story segment?

**STEP 2: INTERNALIZE CURRENT NARRATION STYLE (MANDATORY ADHERENCE)**
Style Persona: '{narration_name_display}'
Core Characteristics & Specific Writing Guidelines for this Style: 
{narration_tone}
Literary Inspiration: '{narration_inspired_by}'
Source Text Snippet for Stylistic Emulation (CRITICAL: Emulate voice, sentence structure, tone):
{narration_style_snippet_instruction_slide} 

**STEP 3: DETERMINE SCENARIO & PLOT FOCUS FOR THIS TURN**
Initial Scene Directive (Use ONLY if User's Request from Step 1 indicates starting a brand new story with these specific instructions, AND this directive is not empty. This OVERRIDES generic genre/setting for the opening):
{initial_scene_directive_slide}

Previous Story Slide Text (Use ONLY if User's Request from Step 1 is a "System Directive" to re-narrate due to a style change, AND this text is not empty. Re-narrate ONLY this text): 
{last_story_slide_text}

Current Plot Focus / User's Goal for this Segment (Derived from User's Request in Step 1 and Chat History):
{current_plot_focus_or_user_goal} 

**STEP 4: DEEPLY INTEGRATE CHARACTER DIRECTIVES (MANDATORY)**
Active Characters & Their Profiles:
{characters_full_profiles} 
   - How will each character's listed traits, goals, and internal conflicts specifically manifest in THIS segment/response, aligning with the Plot Focus from Step 3?

**STEP 5: REFERENCE STORY CONTEXT & HISTORY**
Story Theme/Genre (Use if not overridden by Initial Scene Directive): {genre}
Story Setting (Use if not overridden by Initial Scene Directive): {setting}
Overall Story Tone (Must align with Narration Style): {tone}
Conversation/Story History (The story so far. The last assistant message containing story is your direct continuation point if generating new story content):
{chat_history}

**STEP 6: GENERATE RESPONSE / STORY SEGMENT**
Based on your analysis from Steps 1-5:

   A. **IF User's Request (Step 1) was a "System Directive" for Style Change AND `last_story_slide_text` (Step 3) is provided:**
      - Acknowledge the style change.
      - Provide ONLY the re-narrated version of `last_story_slide_text` in the new style (Step 2).
      - THEN, ask the user if they are happy or want changes. (e.g., "Here's the segment in the new style! How does it feel?")

   B. **IF User's Request (Step 1) was a "System Directive" for Style Change AND `last_story_slide_text` (Step 3) is EMPTY (or style set for a new story):**
      - Acknowledge the style change (e.g., "Style set to {narration_name_display}.").
      - If `initial_scene_directive_slide` (Step 3) is provided AND User's Request indicates starting with it: Generate the initial story segment (approx. 300 words) strictly following `initial_scene_directive_slide`, character profiles (Step 4), and narration style (Step 2).
      - ELSE (no initial scene directive, or not starting new): State that the new style will be applied to the next story segment the user requests. Do NOT generate story content.
      - THEN, ask the user how they'd like to proceed or for their first story prompt.

   C. **IF User's Request (Step 1) is to CONTINUE an existing story (e.g., "next slide", "continue", or implies continuation):**
      - Generate the next story segment (approx. 300 words).
      - This segment MUST logically follow the last assistant-generated story part in `chat_history` (Step 5).
      - It MUST advance the `current_plot_focus_or_user_goal` (Step 3).
      - It MUST deeply integrate characters (Step 4).
      - It MUST flawlessly maintain narration style (Step 2).
      - End with impact (cliffhanger, conflict, poignant moment, revelation).
      - THEN, ALWAYS conclude by briefly asking the user for their input: "What are your thoughts? Shall we continue, or would you like to suggest a twist or make a revision?"

   D. **IF User's Request (Step 1) is a question or other non-story-continuation interaction:**
      - Respond appropriately, thoughtfully, and in character if asking about a character's thoughts.
      - Maintain the narration style (Step 2) in your response tone if appropriate.

Output only your complete response (acknowledgment, story segment, and follow-up question, as applicable per A, B, C, or D).
"""
SLIDE_GENERATION_PROMPT = PromptTemplate(
    input_variables=[
        "user_input", 
        "narration_name_display", "narration_tone", "narration_inspired_by", 
        "narration_style_snippet_instruction_slide", "initial_scene_directive_slide", 
        "current_plot_focus_or_user_goal", "last_story_slide_text",
        "characters_full_profiles",
        "genre", "setting", "tone",
        "chat_history",
    ],
    template=slide_generation_template
)


# --- Chain Creation Functions ---
def create_author_style_snippet_chain(api_key: str) -> LLMChain:
    llm = get_grok_llm(api_key=api_key, temperature=0.7)
    return LLMChain(llm=llm, prompt=AUTHOR_STYLE_SNIPPET_PROMPT, output_key="style_snippet")

def create_slide_generation_chain(api_key: str, temperature_override: float = None) -> LLMChain:
    temp = temperature_override if temperature_override is not None else 0.9
    llm = get_grok_llm(api_key=api_key, temperature=temp)
    return LLMChain(llm=llm, prompt=SLIDE_GENERATION_PROMPT, output_key="ai_response")

def create_story_compilation_pipeline(api_key: str, bennet_style_active: bool = False) -> SequentialChain:
    plot_temp = 0.7
    draft_temp = 0.85 
    refine_temp = 0.6
    # if bennet_style_active: draft_temp = 0.75 # Optional temperature tweak

    plot_outline_chain = LLMChain(
        llm=get_grok_llm(api_key=api_key, temperature=plot_temp),
        prompt=PLOT_OUTLINE_PROMPT,
        output_key="plot_outline" # Output will be passed as 'plot_outline'
    )
    story_draft_chain = LLMChain(
        llm=get_grok_llm(api_key=api_key, temperature=draft_temp),
        prompt=STORY_DRAFT_PROMPT, 
        output_key="story_draft" # Output will be passed as 'story_draft'
    )
    story_refine_chain = LLMChain(
        llm=get_grok_llm(api_key=api_key, temperature=refine_temp),
        prompt=STORY_REFINEMENT_PROMPT, 
        output_key="refined_story" 
    )
    
    # These are the initial inputs the SequentialChain needs that are not outputs of prior chains.
    # `plot_outline` and `story_draft` are intermediate and handled by SequentialChain.
    pipeline_initial_input_variables = [
        "initial_scene_directive_draft", 
        "initial_scene_directive_refine",
        "genre", "setting", "tone", "characters_summary", # For plot_outline_chain
        "narration_name_display", # For draft_chain & refine_chain
        "narration_tone",         # For draft_chain & refine_chain
        "narration_inspired_by",  # For draft_chain & refine_chain
        "narration_style_snippet_instruction", # For draft_chain
        "narration_style_snippet_instruction_refine", # For refine_chain
        "characters_full_profiles", # For draft_chain
        "characters_full_profiles_for_refinement_context" # For refine_chain
    ]

    story_compilation_pipeline = SequentialChain(
        chains=[plot_outline_chain, story_draft_chain, story_refine_chain],
        input_variables=list(set(pipeline_initial_input_variables)), # Use set to ensure uniqueness
        # The output_variables are what the SequentialChain itself will return in its output dictionary.
        # These typically include the final output and any intermediate outputs you want to inspect.
        output_variables=["refined_story", "plot_outline", "story_draft"], 
        verbose=True, 
    )
    return story_compilation_pipeline