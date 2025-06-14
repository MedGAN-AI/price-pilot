import os
import yaml
import time
from typing import List, Dict, Any

from dotenv import load_dotenv

try:
    import sys
    sys.path.append('/mnt/c/Users/mzlwm/OneDrive/Documents/GitHub/price-pilot')
    from src.integrations.supabase_client import supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

if not SUPABASE_AVAILABLE:
    raise ImportError("Supabase client not found. Ensure src/integrations/supabase_client.py exists and is configured.")

# Load config.yaml (for RecommendAgent)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "agents", "RecommendAgent", "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Read embedding settings
EMBEDDING_PROVIDER = config.get("embedding_provider", "google-genai-embeddings")
EMBEDDING_MODEL    = config.get("embedding_model", "gemini-embedding-exp-03-07")

# Table name (where to upsert embeddings)
SUPABASE_TABLE = config.get("supabase_table_embeddings", "product_embeddings")

# Load API keys from environment
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if EMBEDDING_PROVIDER == "google-genai-embeddings" and not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set in .env for Google GenAI embeddings.")

if EMBEDDING_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in .env for OpenAI embeddings.")


def embed_text(text: str) -> List[float]:
    """
    Return a list of floats representing the embedding of the given text.
    Supports Google GenAI (Gemini) or OpenAI, based on EMBEDDING_PROVIDER.
    """
    if EMBEDDING_PROVIDER == "google-genai-embeddings":
        # Use Google GenAI Gemini embedding API
        from google import genai

        client = genai.Client(api_key=GOOGLE_API_KEY)
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text
        )
        
        # Debug the response structure
        print(f"DEBUG - Response type: {type(result)}")
        
        # Extract embeddings from response
        embedding = None
        if hasattr(result, "embeddings") and result.embeddings:
            # Convert ContentEmbedding object to a list of floats
            embedding_obj = result.embeddings[0]
            if hasattr(embedding_obj, "values"):
                embedding = list(embedding_obj.values)
            elif hasattr(embedding_obj, "embedding"):
                embedding = list(embedding_obj.embedding)
        
        # Try model_dump method if above failed
        if embedding is None and hasattr(result, "model_dump"):
            response_dict = result.model_dump()
            if "embeddings" in response_dict and response_dict["embeddings"]:
                embedding_data = response_dict["embeddings"][0]
                if isinstance(embedding_data, dict) and "values" in embedding_data:
                    embedding = list(embedding_data["values"])
        
        # Last resort: try dictionary conversion
        if embedding is None:
            try:
                if hasattr(result, "dict"):
                    response_dict = result.dict()
                else:
                    response_dict = vars(result)
                
                if "embeddings" in response_dict and response_dict["embeddings"]:
                    embedding_obj = response_dict["embeddings"][0]
                    if hasattr(embedding_obj, "values"):
                        embedding = list(embedding_obj.values)
                    elif isinstance(embedding_obj, dict) and "values" in embedding_obj:
                        embedding = list(embedding_obj["values"])
            except Exception as e:
                raise ValueError(f"Failed to extract embedding: {str(e)}")
        
        if embedding is None:
            raise ValueError("Could not extract embedding values from response")
            
        # Adjust embedding size to match the expected 1536 dimensions
        if len(embedding) == 3072:
            # Option 1: Take every other element to reduce dimensions by half
            embedding = embedding[::2]
            
            # Option 2 (alternative): Use the first 1536 elements
            # embedding = embedding[:1536]
            
            print(f"Reduced embedding dimensions from 3072 to {len(embedding)}")
            
        return embedding

    elif EMBEDDING_PROVIDER == "openai":
        # Use OpenAI embeddings via LangChain's OpenAIEmbeddings wrapper
        from langchain.embeddings import OpenAIEmbeddings

        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        embedder = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        vector = embedder.embed_query(text)
        return vector

    else:
        raise ValueError(f"Unsupported embedding provider: {EMBEDDING_PROVIDER}")


def fetch_all_products() -> List[Dict[str, Any]]:
    """
    Query Supabase for all products (id, name, description).
    Returns a list of dicts with keys: id, name, description.
    """
    try:
        response = supabase.table("products").select("id, name, description").execute()
        # Check if response has data attribute
        if hasattr(response, "data"):
            return response.data or []
        return []
    except Exception as e:
        raise RuntimeError(f"Failed to fetch products: {str(e)}")


def upsert_embedding(product_id: str, embedding: List[float]) -> None:
    """
    Upsert a single embedding into the product_embeddings table.
    If a row for this product_id already exists, update it; otherwise insert.
    """
    # Ensure embedding is a plain list of floats
    if not isinstance(embedding, list):
        raise TypeError(f"Embedding must be a list of floats, got {type(embedding)}")
    
    # Verify embedding contains numeric values
    if not all(isinstance(x, (int, float)) for x in embedding):
        raise ValueError("Embedding must contain only numeric values")
    
    # Supabase upsert syntax: .upsert() will insert or update based on primary key
    payload = {
        "product_id": product_id,
        "embedding": embedding
    }
    
    try:
        # Use the table name from config
        response = supabase.table(SUPABASE_TABLE).upsert(payload).execute()
        print(f"DEBUG - Upsert response: {response}")
        
        # More permissive check to avoid errors
        if hasattr(response, "data") and not response.data:
            print(f"WARNING: Empty data in upsert response for {product_id}")
    except Exception as e:
        raise RuntimeError(f"Upsert failed for product_id {product_id}: {str(e)}")


def main():
    print("\n=== Ingesting Product Embeddings ===\n")
    
    # Print configuration for debugging
    print(f"Using embedding provider: {EMBEDDING_PROVIDER}")
    print(f"Using embedding model: {EMBEDDING_MODEL}")
    print(f"Target Supabase table: {SUPABASE_TABLE}")

    products = fetch_all_products()
    if not products:
        print("No products found in the 'products' table. Exiting.")
        return

    total = len(products)
    print(f"Fetched {total} products. Starting embedding ingestion...\n")

    for idx, prod in enumerate(products, start=1):
        pid = prod.get("id")
        name = prod.get("name", "").strip()
        desc = prod.get("description", "").strip() or ""

        if not pid or not name:
            print(f"[{idx}/{total}] Skipping product with missing id or name: {prod}")
            continue

        # Build text to embed: name + description
        text_to_embed = name if not desc else f"{name}. {desc}"
        print(f"[{idx}/{total}] Embedding product '{name}' (ID: {pid[:8]}...)")

        try:
            vector = embed_text(text_to_embed)
        except Exception as e:
            print(f"Error generating embedding for {pid}: {e}")
            continue

        # Upsert into product_embeddings
        try:
            upsert_embedding(pid, vector)
            print(f"  → Upserted embedding for product_id {pid[:8]}... successfully.\n")
        except Exception as e:
            print(f"Error upserting embedding for {pid}: {e}")

        # Optional: rate‐limit to avoid API throttling
        time.sleep(0.5)  # half‐second delay between calls

    print("\n=== Completed Embedding Ingestion ===\n")


if __name__ == "__main__":
    main()
