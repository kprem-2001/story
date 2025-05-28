# core/narration.py
import os
from pinecone import Pinecone 

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "narration-styles" 

pinecone_client = None
narration_index = None
PINECONE_INITIALIZED_SUCCESSFULLY = False 

def initialize_pinecone():
    global pinecone_client, narration_index, PINECONE_INITIALIZED_SUCCESSFULLY
    
    if PINECONE_INITIALIZED_SUCCESSFULLY: return True
    if not PINECONE_API_KEY:
        if not hasattr(initialize_pinecone, "api_key_warning_shown"): # Avoid repeated warnings
            print("Narration Error: PINECONE_API_KEY not set. Pinecone features disabled.")
            initialize_pinecone.api_key_warning_shown = True 
        PINECONE_INITIALIZED_SUCCESSFULLY = False
        return False
    if hasattr(initialize_pinecone, "api_key_warning_shown"): # Clear previous warning if key is now present
        del initialize_pinecone.api_key_warning_shown

    try:
        pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
        index_exists = False
        listed_indexes_data = pinecone_client.list_indexes()
        index_names_list = [idx_spec.name for idx_spec in listed_indexes_data.indexes]
        if PINECONE_INDEX_NAME in index_names_list: index_exists = True
        
        if index_exists:
            narration_index = pinecone_client.Index(PINECONE_INDEX_NAME)
            PINECONE_INITIALIZED_SUCCESSFULLY = True
            return True
        else:
            print(f"Narration Error: Pinecone index '{PINECONE_INDEX_NAME}' not found. Please create it or run embed script.")
            PINECONE_INITIALIZED_SUCCESSFULLY = False; return False
    except Exception as e:
        print(f"Narration Error: During Pinecone initialization or index connection: {e}")
        PINECONE_INITIALIZED_SUCCESSFULLY = False; return False

def get_voice_description_from_pinecone(voice_id: str) -> dict | None:
    if not PINECONE_INITIALIZED_SUCCESSFULLY: return None 
    if not narration_index: 
        if not initialize_pinecone() or not narration_index: return None # Try re-init
            
    try:
        fetch_response = narration_index.fetch(ids=[voice_id])
        if fetch_response and fetch_response.vectors and voice_id in fetch_response.vectors:
            vector_object = fetch_response.vectors[voice_id]
            metadata = vector_object.metadata if hasattr(vector_object, 'metadata') else {}
            if metadata is None: metadata = {} 

            keywords_list = metadata.get("keywords", []) 
            inspired_by_text = ", ".join(keywords_list) if keywords_list else "the provided example text"
            
            # The 'description' from metadata will now include the specific guidelines for Bennet
            return {
                "name_display": metadata.get("style_name", voice_id),
                "tone": metadata.get("description", f"Custom style for {voice_id} from Pinecone"), 
                "inspired_by": inspired_by_text, 
                "source_text_snippet": metadata.get("source_text_snippet", None), 
            }
        return None 
    except Exception as e:
        print(f"Narration Error: Fetching style '{voice_id}' from Pinecone: {e}")
        return None

STATIC_VOICE_DESCRIPTIONS = {
    "DEFAULT": {"name_display": "Default AI", "tone": "A neutral, clear, and engaging storytelling voice that adapts to the overall story tone.", "inspired_by": "General good storytelling practices, clarity, and flow.", "source_text_snippet": None},
    "ANJALI_STATIC": {"name_display": "Anjali (Static)", "tone": "Romantic, fluffy, witty, full of charm and light-hearted banter.", "inspired_by": "Anuja Chauhan, modern Indian rom-com authors.", "source_text_snippet": "Example: 'Oh, the drama! He looked at her, she looked at him, and the pigeons probably cooed a romantic Bollywood number right on cue.'"},
}

def get_active_voice_description(voice_id: str) -> dict:
    pinecone_style = None
    if not hasattr(get_active_voice_description, 'pinecone_init_attempted_this_run'):
        initialize_pinecone() 
        get_active_voice_description.pinecone_init_attempted_this_run = True

    if PINECONE_INITIALIZED_SUCCESSFULLY: 
        pinecone_style = get_voice_description_from_pinecone(voice_id)
    
    if pinecone_style:
        return pinecone_style
    
    if voice_id in STATIC_VOICE_DESCRIPTIONS:
        return STATIC_VOICE_DESCRIPTIONS[voice_id]
    
    print(f"Narration Warning: Voice ID '{voice_id}' is unknown. Using generic fallback.")
    return {"name_display": voice_id, "tone": "custom (undefined)", "inspired_by": "User defined", "source_text_snippet": None}


VOICE_OPTIONS_MAP = { 
    "Default (AI's choice)": "DEFAULT",
    "Geet (Spunky Bollywood Queen)": "GEET", 
    "Bennet (Regency Romance)": "BENNET_REGENCY", # NEWLY ADDED
    "Anjali (Romantic, Witty - Static)": "ANJALI_STATIC", 
}