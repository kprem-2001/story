# core/embedding_utils.py
from sentence_transformers import SentenceTransformer

MODEL_NAME = 'all-MiniLM-L6-v2' 
try:
    embedding_model = SentenceTransformer(MODEL_NAME)
    EMBEDDING_DIMENSION = embedding_model.get_sentence_embedding_dimension()
    print(f"Sentence Transformer model '{MODEL_NAME}' loaded. Dimension: {EMBEDDING_DIMENSION}")
except Exception as e:
    print(f"Error loading Sentence Transformer model '{MODEL_NAME}': {e}")
    embedding_model = None
    EMBEDDING_DIMENSION = 384 

def get_embedding(text: str) -> list[float] | None:
    if not embedding_model:
        print("Embedding model not loaded. Cannot generate embedding.")
        return None
    if not text or not isinstance(text, str):
        print("Invalid text provided for embedding.")
        return None
    try:
        embedding = embedding_model.encode(text, convert_to_tensor=False) 
        return embedding.tolist() 
    except Exception as e:
        print(f"Error generating embedding for text: '{text[:50]}...': {e}")
        return None

def get_embedding_dimension() -> int:
    return EMBEDDING_DIMENSION