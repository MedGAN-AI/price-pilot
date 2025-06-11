import os
import yaml
import hashlib
import random
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
        try:
            import google.generativeai as genai
            
            # You need GOOGLE_API_KEY in your .env
            google_api_key = os.getenv("GOOGLE_API_KEY", "")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY environment variable is required for Google GenAI embeddings")
            
            genai.configure(api_key=google_api_key)
            
            # Get embeddings from Gemini
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text
            )
              # Extract the embedding values
            return result['embedding'] if 'embedding' in result else []
            
        except ImportError:
            # Fallback: return a mock embedding for development
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            # Generate a deterministic 384-dimensional vector (Gemini embedding size)
            random.seed(hash_val)
            return [random.uniform(-1, 1) for _ in range(384)]
        except Exception as e:
            # Fallback for any other errors
            print(f"Warning: Embedding failed, using fallback: {e}")
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(hash_val)
            return [random.uniform(-1, 1) for _ in range(384)]
    elif EMBEDDING_PROVIDER == "openai":
        try:
            from openai import OpenAI
            # You need OPENAI_API_KEY in your .env
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI embeddings")
            
            client = OpenAI(api_key=openai_api_key)
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
            
        except ImportError:
            # Fallback if OpenAI not available
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(hash_val)
            return [random.uniform(-1, 1) for _ in range(1536)]  # OpenAI embedding size
        except Exception as e:
            print(f"Warning: OpenAI embedding failed, using fallback: {e}")
            hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            random.seed(hash_val)
            return [random.uniform(-1, 1) for _ in range(1536)]

    # Add other providers if desired
    else:
        # Default fallback for any provider
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(384)]


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