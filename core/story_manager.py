# core/story_manager.py
import datetime 
from .prompts import BENNET_STYLE_INITIAL_SCENE_PROMPT 
from .agent_factory import generate_agent_profile, describe_agent
from .narration import get_active_voice_description, VOICE_OPTIONS_MAP
from .utils import is_primarily_story_content
from .story_engine import build_agent_context_for_prompt 

from .langchain_chains import (
    create_author_style_snippet_chain,
    create_slide_generation_chain,
    create_story_compilation_pipeline
)

XAI_API_KEY_CONFIGURED = False 

def log_message(message: str): # Logging helper
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"LOG [{timestamp}]: {message}")

# --- StoryState, initialize_story_state, _get_narration_snippet_instruction_for_chain, 
# --- _is_new_story_context, _prime_bennet_context_if_new_story remain the same as Message #33 ---
class StoryState: # ... same ...
    def __init__(self, messages, agents, story_config, narration_voice_id, last_story_slide_text, ui_inputs=None):
        self.messages = list(messages); self.agents = list(agents); self.story_config = dict(story_config)
        self.narration_voice_id = narration_voice_id; self.last_story_slide_text = last_story_slide_text
        self.ui_inputs = ui_inputs if ui_inputs else {}
    def to_dict(self):
        return {
            "messages": self.messages, "agents": self.agents, "story_config": self.story_config,
            "narration_voice_id": self.narration_voice_id, "last_story_slide_text": self.last_story_slide_text,
            "new_char_name_val": self.ui_inputs.get("new_char_name_val", ""),
            "new_char_role_val": self.ui_inputs.get("new_char_role_val", ""),
            "custom_author_name_val": self.ui_inputs.get("custom_author_name_val", "")
        }
def initialize_story_state() -> dict: # ... same ...
    log_message("Initializing new story state.")
    initial_config = {"genre": None, "setting": None, "tone": None, "narration_style": get_active_voice_description("DEFAULT")}
    return {
        "messages": [{"role": "system", "content": "System Initialized. Welcome to the AI Story Weaver!"}, 
                     {"role": "assistant", "content": "Hello! Let's co-create a story..."}],
        "agents": [], "story_config": initial_config, "narration_voice_id": "DEFAULT",
        "last_story_slide_text": None, "new_char_name_val": "", "new_char_role_val": "", "custom_author_name_val":""
    }
def _get_narration_snippet_instruction_for_chain(narration_style_details: dict, context_label="current operation") -> str: # ... same ...
    if narration_style_details and narration_style_details.get("source_text_snippet"):
        return (f"\nCRITICAL STYLE REFERENCE (Emulate this style for the {context_label}):\n"
                f"---\n{narration_style_details['source_text_snippet'][:300]}...\n---") 
    return f"\n(No specific example snippet provided for the {context_label}; rely on tone and inspiration.)"
def _is_new_story_context(current_state: StoryState) -> bool: # ... same ...
    # True if very few messages and no story content generated yet.
    # User's first real input after initial assistant message and potential style setting.
    story_messages_count = sum(1 for msg in current_state.messages if msg['role'] == 'assistant' and is_primarily_story_content(msg['content'])[0])
    return len(current_state.messages) <= 5 and not current_state.last_story_slide_text and story_messages_count == 0

def _prime_bennet_context_if_new_story(current_state: StoryState): # ... same ...
    if current_state.narration_voice_id == "BENNET_REGENCY" and _is_new_story_context(current_state):
        log_message("BENNET_REGENCY style selected for new story. Priming context.")
        # Set defaults only if not already set by user (e.g., via sidebar before style selection)
        if not current_state.story_config.get("genre"): current_state.story_config['genre'] = "Historical Romance (Regency)"
        if not current_state.story_config.get("setting"): current_state.story_config['setting'] = "Early 19th Century England, Upper-Class Society"
        if not current_state.story_config.get("tone"): current_state.story_config['tone'] = "Elegant, Introspective, Emotionally Layered"
        if not current_state.agents:
            log_message("No agents exist. Adding default protagonist for Bennet style.")
            default_protagonist_name = "Eleanor Vance" 
            default_protagonist_role = "Lady's Maid (or Governess)"
            default_protagonist = generate_agent_profile(name=default_protagonist_name, role=default_protagonist_role, traits=["observant", "intelligent", "quietly yearning"], goal="Seek a life of meaning beyond her current station", conflict="Duty to her employers vs. her own desires and principles")
            current_state.agents.append(default_protagonist)
            current_state.messages.append({"role": "assistant", "content": (f"For 'Bennet (Regency Romance)' style, I've set up: {default_protagonist_name}, a {default_protagonist_role}. The story will begin per style guidelines. What would you like to happen?")})
        log_message(f"Bennet context primed: Genre='{current_state.story_config['genre']}', Setting='{current_state.story_config['setting']}', Agents: {len(current_state.agents)}")


def _call_langchain_slide_chain(current_state: StoryState, latest_user_input_override: str = None) -> StoryState:
    log_message(f"Entering _call_langchain_slide_chain. Override input: '{latest_user_input_override[:100] if latest_user_input_override else 'None'}...'")
    xai_api_key = current_state.ui_inputs.get("xai_api_key")
    if not XAI_API_KEY_CONFIGURED or not xai_api_key:
        log_message("API Key missing in _call_langchain_slide_chain. Aborting.")
        current_state.messages.append({"role": "assistant", "content": "Cannot contact AI: API Key missing."}); return current_state

    narration_details = current_state.story_config.get("narration_style", get_active_voice_description("DEFAULT"))
    
    # Prepare chat history: last ~5 turns, excluding the current user input if it's not an override
    history_limit = 5 
    relevant_messages = []
    user_turns = 0
    assistant_turns = 0
    for msg in reversed(current_state.messages):
        if msg['role'] == 'user' and not latest_user_input_override and msg['content'] == current_state.messages[-1].get('content'): # Skip current user input unless overridden
            continue
        if msg['role'] == 'user' and user_turns >= history_limit: continue
        if msg['role'] == 'assistant' and assistant_turns >= history_limit: continue
        
        relevant_messages.insert(0, f"{msg['role']}: {msg['content']}")
        if msg['role'] == 'user': user_turns +=1
        if msg['role'] == 'assistant': assistant_turns +=1
        if user_turns >= history_limit and assistant_turns >= history_limit: break
        
    formatted_chat_history = "\n".join(relevant_messages)
    
    effective_user_input = latest_user_input_override
    if not effective_user_input: 
        if current_state.messages and current_state.messages[-1]['role'] == 'user':
            effective_user_input = current_state.messages[-1]['content']
        else: 
            effective_user_input = "Continue the story or await my specific instruction based on the history." # Fallback
    log_message(f"Effective user input for slide chain (first 100 chars): '{effective_user_input[:100]}...'")

    initial_scene_directive_slide = ""
    # Default plot focus: Respond to user, or continue from last AI story part.
    current_plot_focus = f"User input is: '{effective_user_input[:100]}...'. Analyze this within the context of the chat history. If it's a story continuation, build upon the last AI-generated story segment. If it's a question or command, address it directly."

    # Check for Bennet style and new story context to apply specific initial scene prompt
    is_new_story_for_bennet = _is_new_story_context(current_state)
    if current_state.narration_voice_id == "BENNET_REGENCY" and is_new_story_for_bennet:
        initial_scene_directive_slide = BENNET_STYLE_INITIAL_SCENE_PROMPT
        log_message("Applying BENNET_STYLE_INITIAL_SCENE_PROMPT for slide generation.")
        current_plot_focus = "This is the first story segment with 'Bennet (Regency Romance)' style. Your primary task is to generate an opening scene that STRICTLY follows the 'Initial Scene Directive' provided. Ensure character profiles are integrated."
        # Further guide the AI if the user input was generic after setting the style.
        if effective_user_input.lower() in ["let's begin.", "start the story.", "ok.", "next.", "continue."]:
            effective_user_input = f"System Task: Initiate the story using the 'Bennet (Regency Romance)' style. Strictly follow the provided 'IMPORTANT SCENARIO DIRECTIVE FOR STORY OPENING' to craft this first scene."
            log_message(f"Modified effective_user_input for initial Bennet scene start: '{effective_user_input[:150]}...'")
    elif "re-narrate" in effective_user_input.lower() and current_state.last_story_slide_text: # If re-narration directive
        current_plot_focus = f"The user has requested a re-narration of the previous slide text ('{current_state.last_story_slide_text[:50]}...') due to a style change to '{narration_details.get('name_display')}'. Re-write ONLY that text."
    
    chain_input = {
        "user_input": effective_user_input,
        "narration_name_display": narration_details.get("name_display", "Default AI"),
        "narration_tone": narration_details.get("tone", "Neutral"), 
        "narration_inspired_by": narration_details.get("inspired_by", "Clarity"),
        "narration_style_snippet_instruction_slide": _get_narration_snippet_instruction_for_chain(narration_details, "next story slide"),
        "initial_scene_directive_slide": initial_scene_directive_slide,
        "current_plot_focus_or_user_goal": current_plot_focus, 
        "last_story_slide_text": (current_state.last_story_slide_text or ""),
        "characters_full_profiles": build_agent_context_for_prompt(current_state.agents),
        "genre": current_state.story_config.get("genre", "Not set"),
        "setting": current_state.story_config.get("setting", "Not set"),
        "tone": current_state.story_config.get("tone", "Not set"),
        "chat_history": formatted_chat_history,
    }
    log_message(f"Invoking slide_generation_chain. Initial directive populated: {bool(initial_scene_directive_slide)}. Plot focus: '{current_plot_focus[:70]}...'")
    
    try:
        slide_chain = create_slide_generation_chain(api_key=xai_api_key) 
        response = slide_chain.invoke(chain_input)
        ai_response_text = response.get("ai_response", "Sorry, I had trouble generating a response.")
        log_message(f"slide_generation_chain response (first 100 chars): '{ai_response_text[:100]}...'")
        
        # Do not add AI's entire meta-response if it includes self-correction/analysis steps
        # The prompt now asks for "Output only your complete response (acknowledgment, story segment, and follow-up question...)"
        # So, we assume ai_response_text is the final user-facing output.
        current_state.messages.append({"role": "assistant", "content": ai_response_text})
        
        is_story, extracted_story_text = is_primarily_story_content(ai_response_text)
        if is_story and extracted_story_text:
            current_state.last_story_slide_text = extracted_story_text
            log_message(f"Extracted story slide. New last_story_slide_text (first 100): '{extracted_story_text[:100]}...'")
        else:
            # If it's not story content (e.g., just an acknowledgement or question), clear last_story_slide_text
            # to avoid re-narrating this non-story response if style changes again.
            current_state.last_story_slide_text = None 
            log_message("AI response was not primarily story content. last_story_slide_text cleared.")
            
    except Exception as e:
        log_message(f"ERROR in _call_langchain_slide_chain: {e}")
        import traceback
        print(f"Detailed error in _call_langchain_slide_chain: {e}\n{traceback.format_exc()}")
        current_state.messages.append({"role": "assistant", "content": f"Langchain slide error: {e}"})
    log_message("Exiting _call_langchain_slide_chain.")
    return current_state

def handle_story_details_update(current_state: StoryState, genre: str, setting: str, tone: str) -> tuple[StoryState, bool, str]:
    log_message(f"Entering handle_story_details_update. Genre: '{genre}', Setting: '{setting}', Tone: '{tone}'")
    updated = False; status_msg = "No changes in story details."
    if genre != (current_state.story_config.get("genre") or ""): current_state.story_config["genre"] = genre or None; updated = True
    if setting != (current_state.story_config.get("setting") or ""): current_state.story_config["setting"] = setting or None; updated = True
    if tone != (current_state.story_config.get("tone") or ""): current_state.story_config["tone"] = tone or None; updated = True
    if updated:
        log_message("Story details updated. Preparing AI acknowledgement.")
        user_confirmation = f"✅ Story elements updated: Genre='{current_state.story_config.get('genre', 'N/A')}', Setting='{current_state.story_config.get('setting', 'N/A')}', Tone='{current_state.story_config.get('tone', 'N/A')}'."
        current_state.messages.append({"role": "assistant", "content": user_confirmation}) # User confirmation first
        # Then craft the directive for the AI
        directive = f"System Update: Core story elements have been updated by the user. Genre is now '{current_state.story_config.get('genre', 'N/A')}', Setting is '{current_state.story_config.get('setting', 'N/A')}', Tone is '{current_state.story_config.get('tone', 'N/A')}'. Please acknowledge this change and, based on the current setup state (e.g., if characters are defined, if initial story elements are complete), ask the next logical question for story setup or await user input to begin the story."
        current_state = _call_langchain_slide_chain(current_state, latest_user_input_override=directive)
        status_msg = ""
    else: log_message("No story details changed.")
    log_message("Exiting handle_story_details_update.")
    return current_state, updated, status_msg

def handle_narration_voice_change(current_state: StoryState, new_voice_id: str) -> tuple[StoryState, bool]:
    log_message(f"Entering handle_narration_voice_change. New voice ID: '{new_voice_id}'")
    if new_voice_id != current_state.narration_voice_id:
        current_state.narration_voice_id = new_voice_id
        voice_desc = get_active_voice_description(new_voice_id)
        current_state.story_config["narration_style"] = voice_desc 
        log_message(f"Narration style set to: '{voice_desc.get('name_display')}'. Tone (first 50): '{voice_desc.get('tone', '')[:50]}...'")
        
        # Prime context AFTER setting new style ID, so it knows if it's Bennet
        _prime_bennet_context_if_new_story(current_state) 
        
        user_confirmation_message = f"✅ Narration voice set to: {voice_desc['name_display']}."
        directive_for_ai = f"System Directive: Narration style has changed to '{voice_desc['name_display']}'."

        if current_state.last_story_slide_text: 
            log_message("Previous slide exists. Triggering re-narration.")
            user_confirmation_message += " The previous segment will now be re-narrated in this style."
            directive_for_ai += " You MUST re-narrate the content provided in 'last_story_slide_text' using this new style. Focus ONLY on re-writing the text in the new voice; do NOT add new plot or change core events."
            current_state.messages.append({"role": "assistant", "content": user_confirmation_message}) # Show user confirmation
            current_state = _call_langchain_slide_chain(current_state, latest_user_input_override=directive_for_ai)
        else: # No previous slide
            log_message("No previous slide. Style will apply to next generation.")
            # If _prime_bennet_context_if_new_story added a message, don't overwrite or duplicate simple confirmations.
            # Check if the last message was the specific Bennet priming message.
            is_bennet_primed_message_last = False
            if current_state.messages and current_state.messages[-1]['role'] == 'assistant':
                if "For 'Bennet (Regency Romance)' style, I've set up" in current_state.messages[-1]['content']:
                    is_bennet_primed_message_last = True
            
            if not is_bennet_primed_message_last:
                user_confirmation_message += " This new style will be applied to the next part of the story. What would you like to do next?"
                current_state.messages.append({"role": "assistant", "content": user_confirmation_message})
            # No LLM call here just for style set without re-narration. AI will get context on next user input.
        
        log_message("Exiting handle_narration_voice_change (updated).")
        return current_state, True
    log_message("Exiting handle_narration_voice_change (no change).")
    return current_state, False

def handle_custom_author_style_change(current_state: StoryState, author_name: str) -> tuple[StoryState, bool]:
    # ... (similar logic to handle_narration_voice_change for conditional LLM call) ...
    log_message(f"Entering handle_custom_author_style_change. Author: '{author_name}'")
    xai_api_key = current_state.ui_inputs.get("xai_api_key")
    if not XAI_API_KEY_CONFIGURED or not xai_api_key: log_message("API Key missing."); current_state.messages.append({"role": "assistant", "content": "Cannot set style: API Key missing."}); return current_state, False
    if not author_name.strip(): log_message("Author name empty."); current_state.messages.append({"role": "assistant", "content": "Author name is empty."}); return current_state, False
    
    current_state.messages.append({"role": "user", "content": f"System Command: User wants to emulate author: {author_name}"}) 
    current_state.messages.append({"role": "assistant", "content": f"Attempting to generate a style example for {author_name}..."})
    try:
        log_message(f"Invoking author_style_snippet_chain for '{author_name}'.")
        snippet_chain = create_author_style_snippet_chain(api_key=xai_api_key)
        response = snippet_chain.invoke({"author_name": author_name})
        style_snippet = response.get("style_snippet")
        log_message(f"Snippet chain response (first 50 chars): '{style_snippet[:50] if style_snippet else 'None'}'")
        if not style_snippet: log_message(f"Snippet generation failed for {author_name}."); current_state.messages.append({"role": "assistant", "content": f"Could not generate snippet for {author_name}."}); return current_state, False
        
        dynamic_id = f"custom_{author_name.replace(' ', '_').lower()}"
        current_state.narration_voice_id = dynamic_id
        dynamic_desc = {"name_display": f"{author_name} (Dynamically Emulated)", "tone": f"Emulating style of {author_name}.", "inspired_by": f"Works of {author_name} & generated snippet.", "source_text_snippet": style_snippet}
        current_state.story_config["narration_style"] = dynamic_desc 
        log_message(f"Custom author style '{dynamic_desc['name_display']}' set.")

        user_confirmation_message = f"✅ Narration style set to emulate: {dynamic_desc['name_display']}."
        directive_for_ai = f"System Directive: Narration style changed to emulate '{dynamic_desc['name_display']}' using a generated snippet."

        if current_state.last_story_slide_text:
            log_message("Previous slide exists. Triggering re-narration for custom author.")
            user_confirmation_message += " The previous segment will now be re-narrated."
            directive_for_ai += " You MUST re-narrate 'last_story_slide_text'. Do NOT add new plot."
            current_state.messages.append({"role": "assistant", "content": user_confirmation_message})
            current_state = _call_langchain_slide_chain(current_state, latest_user_input_override=directive_for_ai)
        else:
            log_message("No previous slide. Custom author style will apply next.")
            user_confirmation_message += " This new style will be applied to the next part of the story. What's next?"
            current_state.messages.append({"role": "assistant", "content": user_confirmation_message})
        
        log_message("Exiting handle_custom_author_style_change (success).")
        return current_state, True
    except Exception as e:
        log_message(f"ERROR in handle_custom_author_style_change: {e}"); current_state.messages.append({"role": "assistant", "content": f"Error setting custom author style: {e}"}); return current_state, False

def handle_add_character_sidebar(current_state: StoryState, name: str, role: str) -> tuple[StoryState, bool, str]: # ... same structure as #31
    log_message(f"Entering handle_add_character_sidebar. Name: '{name}', Role: '{role}'")
    if not name: log_message("Character name empty. Aborting."); return current_state, False, "Character name needed."
    agent = generate_agent_profile(name=name, role=role or "character"); current_state.agents.append(agent)
    desc = describe_agent(agent); current_state.ui_inputs["clear_char_inputs"] = True
    log_message(f"Character '{name}' added. Description: '{desc}'")
    user_confirmation = f"✅ Character added: {desc}"
    current_state.messages.append({"role": "assistant", "content": user_confirmation})
    directive = f"System Update: New character '{name}' ({role or 'character'}) added. Description: {desc}. Please acknowledge this and, based on current setup state, ask the next logical setup question or await user input for story."
    current_state.last_story_slide_text = None 
    current_state = _call_langchain_slide_chain(current_state, latest_user_input_override=directive)
    log_message("Exiting handle_add_character_sidebar.")
    return current_state, True, ""

def handle_compile_full_story(current_state: StoryState) -> StoryState: # ... same structure as #31, using updated pipeline
    log_message("Entering handle_compile_full_story.")
    xai_api_key = current_state.ui_inputs.get("xai_api_key")
    if not XAI_API_KEY_CONFIGURED or not xai_api_key: log_message("API Key missing."); current_state.messages.append({"role": "assistant", "content": "Cannot compile: API Key missing."}); return current_state

    current_state.messages.append({"role": "assistant", "content": "Initiating Langchain multi-agent story compilation..."})
    try:
        narration_details = current_state.story_config.get("narration_style", get_active_voice_description(current_state.narration_voice_id))
        if not current_state.narration_voice_id.startswith("custom_"): 
            narration_details = get_active_voice_description(current_state.narration_voice_id)
            current_state.story_config["narration_style"] = narration_details
        log_message(f"Compile: Using narration style '{narration_details.get('name_display')}'.")

        initial_scene_directive = ""
        bennet_active_for_compile = False
        if current_state.narration_voice_id == "BENNET_REGENCY":
            initial_scene_directive = BENNET_STYLE_INITIAL_SCENE_PROMPT
            bennet_active_for_compile = True
            log_message("Compile: Applying BENNET_STYLE_INITIAL_SCENE_PROMPT.")
            if not current_state.story_config.get("genre"): current_state.story_config['genre'] = "Historical Romance (Regency)"
            if not current_state.story_config.get("setting"): current_state.story_config['setting'] = "Early 19th Century England"
            if not current_state.story_config.get("tone"): current_state.story_config['tone'] = "Elegant, Introspective"
            if not current_state.agents: _prime_bennet_context_if_new_story(current_state) 

        snippet_instr_draft = _get_narration_snippet_instruction_for_chain(narration_details, "full story draft")
        snippet_instr_refine = _get_narration_snippet_instruction_for_chain(narration_details, "story refinement")
        characters_full_profiles_str = build_agent_context_for_prompt(current_state.agents)
        
        pipeline_input = {
            "initial_scene_directive_draft": initial_scene_directive, 
            "initial_scene_directive_refine": initial_scene_directive, 
            "genre": current_state.story_config.get("genre"), 
            "setting": current_state.story_config.get("setting"),
            "tone": current_state.story_config.get("tone"),
            "characters_summary": "Key characters: " + ", ".join([ag['name'] for ag in current_state.agents]) if current_state.agents else "As defined by genre and style directives.",
            "narration_name_display": narration_details.get("name_display", "Default AI"),
            "narration_tone": narration_details.get("tone", "Neutral"), 
            "narration_inspired_by": narration_details.get("inspired_by", "Clarity"),
            "narration_style_snippet_instruction": snippet_instr_draft, 
            "narration_style_snippet_instruction_refine": snippet_instr_refine, 
            "characters_full_profiles": characters_full_profiles_str,
            # For refinement context, plot_outline will be passed by SequentialChain
            "characters_full_profiles_for_refinement_context": characters_full_profiles_str 
        }
        log_message(f"Invoking story_compilation_pipeline. Bennet active: {bennet_active_for_compile}")
        story_pipeline = create_story_compilation_pipeline(api_key=xai_api_key, bennet_style_active=bennet_active_for_compile)
        current_state.messages.append({"role": "assistant", "content": "Pipeline invoked. Generating Plot Outline..."})
        response = story_pipeline.invoke(pipeline_input) 
        log_message("story_compilation_pipeline finished.")
        plot_gen = response.get("plot_outline", "Plot not captured.") 
        log_message(f"--- AGENT OUTPUT: PLOT OUTLINE ---\n{plot_gen}\n--- END PLOT OUTLINE ---")
        current_state.messages.append({"role": "assistant", "content": f"Plot Outline Generated.\nNow generating story draft..."})
        draft_gen = response.get("story_draft", "Draft not captured.")
        log_message(f"--- AGENT OUTPUT: STORY DRAFT ---\n{draft_gen[:500]}...\n--- END STORY DRAFT (Preview) ---")
        current_state.messages.append({"role": "assistant", "content": f"Initial Story Draft Generated.\nNow refining the story..."})
        refined_story = response.get("refined_story")
        log_message(f"--- AGENT OUTPUT: REFINED STORY ---\n{refined_story[:500]}...\n--- END REFINED STORY (Preview) ---")
        if not refined_story: 
            fallback_message = "Pipeline finished, but refined story missing."
            if draft_gen and draft_gen != "Draft not captured.": fallback_message += " Providing draft:\n\n" + draft_gen
            else: fallback_message += " No draft available."
            current_state.messages.append({"role": "assistant", "content": fallback_message}); return current_state
        current_state.messages.append({"role": "assistant", "content": "✨ Langchain story compilation complete! Here's your polished story:\n\n" + refined_story})
    except Exception as e: 
        log_message(f"ERROR in handle_compile_full_story: {e}")
        import traceback; print(f"Langchain compilation error: {e}\n{traceback.format_exc()}") 
        current_state.messages.append({"role": "assistant", "content": f"Langchain compilation error: {e}"})
    log_message("Exiting handle_compile_full_story.")
    return current_state

def handle_add_character_chat(current_state: StoryState, user_input: str) -> tuple[StoryState, bool]: # ... same structure as #31
    log_message(f"Entering handle_add_character_chat. User input: '{user_input}'")
    try:
        cmd_part = user_input.split(":", 1)[1].strip()
        name, *role_parts = cmd_part.split(",", 1); name = name.strip()
        role = role_parts[0].strip() if role_parts else "character"
        if not name: raise ValueError("Character name cannot be empty.")
        agent = generate_agent_profile(name=name, role=role); current_state.agents.append(agent)
        desc = describe_agent(agent)
        log_message(f"Character '{name}' added via chat. Description: '{desc}'")
        user_confirmation = f"✅ Character '{name}' added via chat."
        current_state.messages.append({"role": "assistant", "content": user_confirmation})
        directive = f"System Update: Character '{name}' ({role or 'character'}) added via chat. Desc: {desc}. Acknowledge & continue setup."
        current_state = _call_langchain_slide_chain(current_state, latest_user_input_override=directive)
        log_message("Exiting handle_add_character_chat (success).")
        return current_state, True
    except Exception as e:
        log_message(f"ERROR in handle_add_character_chat: {e}")
        current_state.messages.append({"role": "assistant", "content": f"⚠️ Error processing 'add character' command: {e}"}); return current_state, False


def handle_regular_chat_input(current_state: StoryState, user_text: str) -> StoryState: # ... same structure as #31
    log_message(f"Entering handle_regular_chat_input. User text: '{user_text}'") # user_text already in messages via app.py
    if "narration_style" not in current_state.story_config or \
       not current_state.story_config["narration_style"] or \
       (not current_state.narration_voice_id.startswith("custom_") and \
        current_state.story_config["narration_style"].get("name_display") != get_active_voice_description(current_state.narration_voice_id).get("name_display")):
         current_state.story_config["narration_style"] = get_active_voice_description(current_state.narration_voice_id)
         log_message(f"Regular chat: Ensured narration style is '{current_state.story_config['narration_style'].get('name_display')}'.")
    
    current_state.last_story_slide_text = None 
    current_state = _call_langchain_slide_chain(current_state) 
    log_message("Exiting handle_regular_chat_input.")
    return current_state