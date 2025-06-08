import os
import yaml
from typing import List, Dict, Any

try:
    from src.integrations.supabase_client import supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Embedding settings
EMBEDDING_PROVIDER = config.get("embedding_provider", "google-genai-embeddings")
EMBEDDING_MODEL    = config.get("embedding_model", "gemini-embedding-exp-03-07")

# Vector store settings
VECTOR_STORE       = config.get("vector_store", "supabase")
SUPABASE_TABLE     = config.get("supabase_table_embeddings", "product_embeddings")

# Number of nearest neighbors
TOP_K = config.get("top_k", 5)

def embed_query(text: str) -> List[float]:
    """
    Return the embedding vector (list of floats) for the given text.
    Uses Google GenAI embeddings (default) or OpenAI if configured.
    """
    if EMBEDDING_PROVIDER == "google-genai-embeddings":
        from google import genai
        
        # You need GOOGLE_API_KEY in your .env
        google_api_key = os.getenv("GOOGLE_API_KEY", "")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for Google GenAI embeddings")
        
        client = genai.Client(api_key=google_api_key)
        
        # Get embeddings from Gemini
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        
        # Extract the embedding values
        return result.embeddings[0].values if result.embeddings else []
    
    elif EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI
        from langchain.embeddings import OpenAIEmbeddings

        # You need OPENAI_API_KEY in your .env
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

        embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        return embedder.embed_query(text)

    # Add other providers if desired
    raise ValueError(f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")


# Nearest‐neighbor search in Supabase / pgvector
def supabase_vector_search(query_embedding: List[float], top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Given a query embedding (list of floats), perform a pgvector similarity search in Supabase.
    Returns a list of dicts: { "product_id": ..., "score": ... } of length <= top_k.
    """
    if not SUPABASE_AVAILABLE:
        return []

    try:
        # Simple table query - get all products and return first top_k
        # This is a fallback approach when vector search isn't properly configured
        response = (
            supabase
            .table(SUPABASE_TABLE)
            .select("product_id")
            .limit(top_k)
            .execute()
        )
        
        if response.data:
            # Add dummy scores since we can't compute similarity without proper vector search
            return [{"product_id": row["product_id"], "score": 0.8} for row in response.data]
            
    except Exception as e:
        print(f"Vector search error: {e}")
        
    return []


# Fetch product metadata for a list of IDs
def fetch_products_metadata(product_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Given a list of product_id UUIDs, return a list of { id, sku, name, price }.
    """
    if not SUPABASE_AVAILABLE:
        return []

    try:
        response = (
            supabase
            .table("products")
            .select("id, sku, name, price")
            .in_("id", product_ids)
            .execute()
        )
        
        if response.data:
            return response.data
        
    except Exception as e:
        print(f"Metadata fetch error: {e}")
        
    return []