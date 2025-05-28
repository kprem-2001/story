# core/story_engine.py
# This module is now simplified. Most LLM logic is handled by langchain_chains.py
# We keep utility functions that might be used by story_manager.py to prepare data for chains.

from .agent_factory import describe_agent # Still used by story_manager

# get_xai_client and other direct OpenAI client interactions for generation
# are now implicitly handled within langchain_chains.py (via get_grok_llm).
# XAI_BASE_URL and xai_client_instance are no longer directly used here
# if all LLM calls for generation go via Langchain.

def build_agent_context_for_prompt(agents: list) -> str: # Still useful for story_manager
    """
    Builds a string describing agent profiles for inclusion in prompts.
    This can be used by story_manager.py when preparing inputs for Langchain chains.
    """
    if not agents: 
        return "No specific characters defined yet." # Provide a default for prompts
    return "\n".join([describe_agent(ag) for ag in agents])

# Functions like:
# - handle_user_input_with_xai
# - compile_full_story_with_xai
# - generate_author_style_example
# - generate_plot_outline_with_xai
# - refine_story_with_xai
# ...are now superseded by their Langchain chain counterparts,
# which are defined in `core/langchain_chains.py` and orchestrated by `core/story_manager.py`.
# They can be removed from this file or commented out for reference.