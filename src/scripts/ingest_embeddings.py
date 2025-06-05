import os
import yaml
import time
from typing import List, Dict, Any

from dotenv import load_dotenv

# Attempt to import Supabase client; if missing, error out
try:
    from src.integrations.supabase_client import supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

if not SUPABASE_AVAILABLE:
    raise ImportError("Supabase client not found. Ensure src/integrations/supabase_client.py exists and is configured.")

# Load config.yaml (for RecommendAgent)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "agents", "RecommendAgent", "config.yaml")
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
        embedding = result.get("embedding")
        if not isinstance(embedding, list):
            raise ValueError(f"Unexpected embedding format from Google GenAI: {result}")
        return embedding

    elif EMBEDDING_PROVIDER == "openai":
        # Use OpenAI embeddings via LangChain’s OpenAIEmbeddings wrapper
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
    response = supabase.table("products").select("id, name, description").execute()
    if getattr(response, "status_code", 400) >= 400:
        raise RuntimeError(f"Failed to fetch products: {response.error}")
    data = getattr(response, "data", [])
    return data or []


def upsert_embedding(product_id: str, embedding: List[float]) -> None:
    """
    Upsert a single embedding into the product_embeddings table.
    If a row for this product_id already exists, update it; otherwise insert.
    """
    # Supabase upsert syntax: .upsert() will insert or update based on primary key
    payload = {
        "product_id": product_id,
        "embedding": embedding
    }
    response = supabase.table(SUPABASE_TABLE).upsert(payload).execute()
    if getattr(response, "status_code", 400) >= 400:
        raise RuntimeError(f"Upsert failed for product_id {product_id}: {response.error}")


def main():
    print("\n=== Ingesting Product Embeddings ===\n")

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
