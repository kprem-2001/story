# app.py
import streamlit as st
import os
import sys 
import datetime # For logging

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

# --- Logging Helper (can be shared if you make a utils.py for logging) ---
def log_app_message(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"APP LOG [{timestamp}]: {message}")

try:
    from core import story_manager 
    from core.narration import VOICE_OPTIONS_MAP, initialize_pinecone
    from core.story_engine import build_agent_context_for_prompt 
except ImportError as e:
    st.error(f"CRITICAL IMPORT ERROR: {e}. Check structure & __init__.py files."); st.stop() 

# --- API Key Setup --- (Same as before)
story_manager.XAI_API_KEY_CONFIGURED = False 
XAI_API_KEY_FOR_CHAINS = None 
# ... (rest of API key setup logic from Message #18)
try:
    from dotenv import load_dotenv
    if os.path.exists(os.path.join(PROJECT_ROOT, '.env')): load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    env_key = os.getenv("XAI_API_KEY")
    if env_key: XAI_API_KEY_FOR_CHAINS = env_key; story_manager.XAI_API_KEY_CONFIGURED = True
except ImportError: pass 

if not story_manager.XAI_API_KEY_CONFIGURED and os.getenv("XAI_API_KEY"): 
    XAI_API_KEY_FOR_CHAINS = os.getenv("XAI_API_KEY"); story_manager.XAI_API_KEY_CONFIGURED = True

if not story_manager.XAI_API_KEY_CONFIGURED: 
    try:
        if hasattr(st, 'secrets') and "XAI_API_KEY" in st.secrets and st.secrets["XAI_API_KEY"]: 
            XAI_API_KEY_FOR_CHAINS = st.secrets["XAI_API_KEY"]; story_manager.XAI_API_KEY_CONFIGURED = True
    except Exception: pass 

if not story_manager.XAI_API_KEY_CONFIGURED:
    log_app_message("CRITICAL: xAI API key NOT CONFIGURED.")
    st.error("CRITICAL: xAI API key (XAI_API_KEY) is NOT configured. Application will not function."); st.stop()
else:
    log_app_message("xAI API Key configured successfully.")


# --- Initialize Pinecone --- (Same as before)
if 'pinecone_initialized_app' not in st.session_state:
    log_app_message("Initializing Pinecone for narration styles...")
    st.session_state.pinecone_initialized_app = initialize_pinecone() 
    if not st.session_state.pinecone_initialized_app:
        log_app_message("Pinecone initialization FAILED.")
        st.warning("Pinecone for narration could not be initialized. Some styles may use fallbacks.")
    else:
        log_app_message("Pinecone initialized successfully.")

# --- Page and Session State Setup --- (Same as before)
st.set_page_config(page_title="Story Weaver (Langchain Edition)", layout="wide")
st.title("📖 AI Story Weaver (Powered by Langchain & xAI/Grok)")

if 'story_state_object' not in st.session_state:
    log_app_message("Session state 'story_state_object' not found. Initializing.")
    initial_state_dict = story_manager.initialize_story_state()
    st.session_state.story_state_object = story_manager.StoryState(
        messages=initial_state_dict["messages"], agents=initial_state_dict["agents"],
        story_config=initial_state_dict["story_config"], narration_voice_id=initial_state_dict["narration_voice_id"],
        last_story_slide_text=initial_state_dict["last_story_slide_text"],
        ui_inputs={ 
            "new_char_name_val": initial_state_dict.get("new_char_name_val", ""),
            "new_char_role_val": initial_state_dict.get("new_char_role_val", ""),
            "custom_author_name_val": initial_state_dict.get("custom_author_name_val", "")
        }
    )
    log_app_message("Initial 'story_state_object' created.")
else:
    log_app_message("Found existing 'story_state_object' in session state.")


def get_current_story_state_with_ui_inputs() -> story_manager.StoryState: # Same as before
    s_obj = st.session_state.story_state_object
    ui_inputs = {
        "xai_api_key": XAI_API_KEY_FOR_CHAINS, 
        "new_char_name_val": st.session_state.get("new_char_name_input_sidebar_ui_key", ""),
        "new_char_role_val": st.session_state.get("new_char_role_input_sidebar_ui_key", ""),
        "custom_author_name_val": st.session_state.get("custom_author_name_input_ui_key", "")
    }
    s_obj.ui_inputs = ui_inputs
    return s_obj

def update_session_state_from_story_manager(returned_story_state: story_manager.StoryState): # Same as before
    st.session_state.story_state_object = returned_story_state
    if returned_story_state.ui_inputs.get("clear_char_inputs"):
        st.session_state.new_char_name_input_sidebar_ui_key = "" 
        st.session_state.new_char_role_input_sidebar_ui_key = "" 
        returned_story_state.ui_inputs["clear_char_inputs"] = False 
    if returned_story_state.ui_inputs.get("clear_author_input"):
        st.session_state.custom_author_name_input_ui_key = "" 
        returned_story_state.ui_inputs["clear_author_input"] = False 

# --- Sidebar UI ---
with st.sidebar: # Logging added for button clicks and important selections
    st.caption(f"Using xAI Grok via Langchain")
    st.markdown("---")
    st.header("🛠️ Story Elements")
    
    current_s_state_for_ui_defaults = st.session_state.story_state_object
    genre_val = st.text_input("Genre", value=current_s_state_for_ui_defaults.story_config.get("genre") or "", key="genre_input_field_key")
    setting_val = st.text_input("Setting", value=current_s_state_for_ui_defaults.story_config.get("setting") or "", key="setting_input_field_key")
    tone_val = st.text_input("Overall Tone", value=current_s_state_for_ui_defaults.story_config.get("tone") or "", key="tone_input_field_key")
    
    if st.button("✅ Update Story Details"):
        log_app_message(f"Sidebar Button Click: 'Update Story Details'. Genre='{genre_val}', Setting='{setting_val}', Tone='{tone_val}'")
        s_state_for_handler = get_current_story_state_with_ui_inputs()
        new_s_state, updated, status = story_manager.handle_story_details_update(s_state_for_handler, genre_val.strip(), setting_val.strip(), tone_val.strip())
        update_session_state_from_story_manager(new_s_state)
        if updated: st.rerun()
        else: st.sidebar.info(status)

    st.markdown("---")
    st.header("🎤 Narration Voice")
    voice_options_keys = list(VOICE_OPTIONS_MAP.keys())
    try:
        current_style_id_in_state = current_s_state_for_ui_defaults.narration_voice_id
        if current_style_id_in_state.startswith("custom_"): 
            current_selectbox_idx = 0 
            st.sidebar.caption(f"Current: Emulating {current_s_state_for_ui_defaults.story_config.get('narration_style',{}).get('name_display','Unknown Author')}")
        else:
            selected_display_name = [k for k, v in VOICE_OPTIONS_MAP.items() if v == current_style_id_in_state][0]
            current_selectbox_idx = voice_options_keys.index(selected_display_name)
    except (IndexError, ValueError): current_selectbox_idx = 0
        
    selected_display = st.selectbox("Pre-defined Style:", options=voice_options_keys, index=current_selectbox_idx, key="narration_voice_selectbox_key")
    selected_style_id = VOICE_OPTIONS_MAP[selected_display]

    if selected_style_id != current_s_state_for_ui_defaults.narration_voice_id:
        log_app_message(f"Sidebar Selectbox Change: Narration style to '{selected_display}' (ID: '{selected_style_id}')")
        s_state_for_handler = get_current_story_state_with_ui_inputs()
        if s_state_for_handler.narration_voice_id != selected_style_id: 
            new_s_state, updated = story_manager.handle_narration_voice_change(s_state_for_handler, selected_style_id)
            update_session_state_from_story_manager(new_s_state)
            if updated: st.rerun()

    st.markdown("##### Or, Emulate an Author:")
    author_name_val = st.text_input("Author's Full Name", key="custom_author_name_input_ui_key", value=st.session_state.story_state_object.ui_inputs.get("custom_author_name_val", ""))
    if st.button("✨ Emulate Author Style"):
        log_app_message(f"Sidebar Button Click: 'Emulate Author Style'. Author='{author_name_val}'")
        if author_name_val.strip():
            s_state_for_handler = get_current_story_state_with_ui_inputs()
            new_s_state, success = story_manager.handle_custom_author_style_change(s_state_for_handler, author_name_val.strip())
            new_s_state.ui_inputs["clear_author_input"] = success 
            update_session_state_from_story_manager(new_s_state)
            if success: st.rerun()
        else: st.warning("Please enter an author's name.")
            
    st.markdown("---")
    st.header("👥 Characters")
    char_name_val = st.text_input("Name", key="new_char_name_input_sidebar_ui_key", value=st.session_state.story_state_object.ui_inputs.get("new_char_name_val", ""))
    char_role_val = st.text_input("Role/Archetype", key="new_char_role_input_sidebar_ui_key", value=st.session_state.story_state_object.ui_inputs.get("new_char_role_val", ""))
    if st.button("➕ Add Character"):
        log_app_message(f"Sidebar Button Click: 'Add Character'. Name='{char_name_val}', Role='{char_role_val}'")
        s_state_for_handler = get_current_story_state_with_ui_inputs() 
        new_s_state, success, status = story_manager.handle_add_character_sidebar(s_state_for_handler, char_name_val.strip(), char_role_val.strip())
        update_session_state_from_story_manager(new_s_state)
        if success: st.rerun()
        else: st.warning(status)

    if current_s_state_for_ui_defaults.agents:
        st.write("Current Characters:")
        for agent in current_s_state_for_ui_defaults.agents: st.write(f"- **{agent['name']}** ({agent.get('role', 'N/A')})")

# --- Main Chat Area ---
chat_container = st.container()
active_story_state = st.session_state.story_state_object
for msg_idx, msg in enumerate(active_story_state.messages): # Added index for potential debug
    if msg["role"] == "system" and not msg["content"].startswith("System Update:"): continue 
    with chat_container.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_chat_input = st.chat_input("Your turn to shape the story...")
if user_chat_input:
    log_app_message(f"User Chat Input: '{user_chat_input}'") # LOG USER INPUT
    if not story_manager.XAI_API_KEY_CONFIGURED: st.error("API key missing."); st.stop()
    
    s_state_for_handler = get_current_story_state_with_ui_inputs()
    s_state_for_handler.messages.append({"role": "user", "content": user_chat_input}) # Add user message
    s_state_for_handler.last_story_slide_text = None 
    
    processed_state = None
    input_lower = user_chat_input.lower().strip()
    compile_kw = ["compile story", "full story", "write the story"]

    if any(kw in input_lower for kw in compile_kw):
        log_app_message(f"User command: Compile full story.")
        st.info("📜 Compiling full story with Langchain agents...")
        processed_state = story_manager.handle_compile_full_story(s_state_for_handler)
    elif "add character:" in input_lower:
        log_app_message(f"User command: Add character via chat.")
        processed_state, _ = story_manager.handle_add_character_chat(s_state_for_handler, user_chat_input)
    else:
        log_app_message(f"User command: Regular chat input for story continuation.")
        processed_state = story_manager.handle_regular_chat_input(s_state_for_handler, user_chat_input) # Pass full user_chat_input
    
    if processed_state:
        update_session_state_from_story_manager(processed_state)
        st.rerun()