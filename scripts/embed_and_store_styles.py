# scripts/embed_and_store_styles.py
import os
import sys
import time 
from dotenv import load_dotenv

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from pinecone import Pinecone, ServerlessSpec 
except ImportError:
    print("Pinecone client not installed. Please install with 'pip install pinecone-client'.")
    sys.exit(1)

try:
    from core.embedding_utils import get_embedding, get_embedding_dimension 
except ImportError:
    print("Could not import from core.embedding_utils.")
    sys.exit(1)

# --- Configuration ---
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f".env file loaded from {dotenv_path}")
else:
    print(f"Warning: .env file not found at {dotenv_path}.")


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "narration-styles" 

# --- Narration Styles to Add/Update ---
NARRATION_STYLES_DATA = {
    "GEET": {
        "text_file": os.path.join(project_root, "narration_examples", "geet_narration_example.txt"), 
        "style_name": "Geet - Spunky Bollywood Queen",
        "description": "A very spunky, witty, energetic, and modern Bollywood-inspired narration. Think vibrant dialogue, a touch of irreverence, and the feel of a modern Indian rom-com. Prioritize lively banter and character voice.",
        "keywords": ["spunky", "witty", "bollywood", "energetic", "modern rom-com", "vibrant dialogue", "hindi-english mix (subtle)", "geet"]
    },
    "BENNET_REGENCY": { # NEW STYLE
        "text_file": os.path.join(project_root, "narration_examples", "bennet.txt"), # Assumes bennet.txt is in narration_examples
        "style_name": "Bennet (Regency Romance)", 
        "description": (
            "A classic Regency romance style, focusing on societal intricacies, duty, and heartfelt emotions. "
            "Features eloquent prose and detailed character introspection.\n"
            "SPECIFIC GUIDELINES FOR THIS 'Bennet (Regency Romance)' STYLE:\n"
            "- Steer clear of feathery, purple prose. Especially avoid repetitive phrases and flourishes.\n"
            "- Avoid directly lifting concepts from popular Regency tropes like 'diamond of the first water' (e.g., from Julia Quinn).\n"
            "- Avoid stock characterization. Instead, follow the 'Chekhov's gun' principle: every significant character introduced "
            "should ideally prove important to the plot later."
        ),
        "keywords": ["regency", "historical romance", "jane austen", "eloquent", "emotional", "bennet", "historical fiction", "chekhovs gun", "originality"]
    },
}

def main():
    if not PINECONE_API_KEY:
        print("Error: Missing PINECONE_API_KEY."); return

    if get_embedding_dimension() is None:
        print("Error: Embedding model failed to load."); return
    embedding_dim = get_embedding_dimension()

    try:
        print("Initializing Pinecone client...")
        pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
        print("Pinecone client initialized.")
        
        current_indexes_response = pinecone_client.list_indexes()
        index_names = [idx_spec.name for idx_spec in current_indexes_response.indexes]

        if PINECONE_INDEX_NAME not in index_names:
            print(f"Index '{PINECONE_INDEX_NAME}' not found. Creating it with dimension {embedding_dim}...")
            pinecone_client.create_index(
                name=PINECONE_INDEX_NAME, dimension=embedding_dim, metric="cosine", 
                spec=ServerlessSpec(cloud="aws", region="us-east-1") # Choose your cloud/region
            )
            print(f"Index '{PINECONE_INDEX_NAME}' creation initiated. Waiting for initialization (30-90s)...")
            time.sleep(75) 
        else:
            print(f"Pinecone index '{PINECONE_INDEX_NAME}' already exists.")

        index = pinecone_client.Index(PINECONE_INDEX_NAME)
        print(f"Successfully connected to Pinecone index: {PINECONE_INDEX_NAME}")
        
        try:
            stats = index.describe_index_stats()
            print(f"Index stats: {stats}")
        except Exception as e_stats:
            print(f"Could not get index stats: {e_stats}")

    except Exception as e:
        print(f"Error during Pinecone initialization or index connection: {e}"); return

    vectors_to_upsert = []
    for style_id, style_data in NARRATION_STYLES_DATA.items():
        print(f"\nProcessing style: {style_id} - {style_data['style_name']}")
        
        if not os.path.exists(style_data["text_file"]):
            print(f"Error: Text file not found: {style_data['text_file']}. Skipping '{style_id}'.")
            continue
            
        try:
            with open(style_data["text_file"], "r", encoding="utf-8") as f:
                narration_text = f.read()
            if not narration_text.strip():
                print(f"Warning: Text file for '{style_id}' is empty. Skipping."); continue
            # For bennet.txt, it has repeated content. We only need one instance for the snippet.
            # Let's ensure we take a clean segment if there are obvious markers.
            # For now, assuming the first part is representative.
            # The script already takes narration_text[:500] for the snippet.
            print(f"Read text from {style_data['text_file']} (length: {len(narration_text)} chars)")
        except Exception as e:
            print(f"Error reading file for '{style_id}': {e}. Skipping."); continue

        print(f"Generating embedding for style '{style_id}'...")
        # The embedding is generated on the full text to capture its overall semantic meaning for potential similarity search.
        # The snippet for direct LLM guidance is taken from the raw text.
        embedding = get_embedding(narration_text) 
        if embedding is None:
            print(f"Failed to generate embedding for '{style_id}'. Skipping."); continue

        # Determine the snippet to store. If bennet.txt has duplicate "Episode 1", take first one.
        effective_text_for_snippet = narration_text
        if style_id == "BENNET_REGENCY": # Specific handling if needed for bennet.txt structure
            parts = narration_text.split("Episode 1: A Dance of Duty")
            if len(parts) > 1: # Found the marker
                 # Take the content after the first marker, up to a reasonable length for a snippet,
                 # or before the next potential marker if it's very long.
                 # For simplicity, we rely on the [:500] general rule below.
                 # This simple split just ensures we don't start mid-way if the file is messy.
                 # A more robust way would be to find the end of the first logical episode.
                 # For now, the default [:500] on the whole text is likely fine given the file content.
                 pass # No change to effective_text_for_snippet, default handling is okay.


        vector = {
            "id": style_id, 
            "values": embedding,
            "metadata": {
                "style_name": style_data["style_name"], 
                "description": style_data["description"], # This now contains specific guidelines for Bennet
                "keywords": style_data.get("keywords", []),
                "source_text_snippet": effective_text_for_snippet[:500].strip() + ("..." if len(effective_text_for_snippet) > 500 else "")
            }
        }
        vectors_to_upsert.append(vector)

    if vectors_to_upsert:
        try:
            print(f"\nUpserting {len(vectors_to_upsert)} vectors to Pinecone index '{PINECONE_INDEX_NAME}'...")
            batch_size = 100 
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                upsert_response = index.upsert(vectors=batch)
                print(f"Upserted batch {i//batch_size + 1}. Response: {upsert_response}")
            print(f"Successfully stored/updated styles in Pinecone.")
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")
    else:
        print("\nNo valid vectors to upsert.")

    print("\nEmbedding and storing process finished.")

if __name__ == "__main__":
    main()