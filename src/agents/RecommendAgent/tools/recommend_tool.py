from typing import List, Dict
from langchain_core.tools import Tool

from src.agents.RecommendAgent.connectors.vector_connector import (
    embed_query,
    supabase_vector_search,
    fetch_products_metadata
)

def _recommend_products(query: str) -> str:
    """
    Given a user query string, embed it, search the vector store for top_k products,
    fetch product metadata, and return a formatted recommendation list.
    """
    # 1) Get embedding
    embedding = embed_query(query)

    # 2) Vector search (returns list of { product_id, score })
    neighbors: List[Dict] = supabase_vector_search(embedding)

    if not neighbors:
        return f"Sorry, I couldn't find any products matching \"{query}\"."

    # 3) Extract the product_ids in order
    product_ids = [row["product_id"] for row in neighbors]

    # 4) Fetch metadata
    metadata_list = fetch_products_metadata(product_ids)

    # 5) Build a lookup map: product_id -> (name, sku, price)
    meta_map = { item["id"]: item for item in metadata_list }

    # 6) Format the top_k results
    lines = [f"Top {len(product_ids)} matches for \"{query}\":"]
    for idx, row in enumerate(neighbors, start=1):
        pid = row["product_id"]
        score = row.get("score", 0.0)
        meta = meta_map.get(pid, {})
        name = meta.get("name", "(unknown)")
        sku = meta.get("sku", "(unknown)")
        price = meta.get("price", 0.0)
        lines.append(f"{idx}. {name} (SKU: {sku}) — ${price:.2f}  [score: {score:.3f}]")

    return "\n".join(lines)

recommend_tool = Tool(
    name="RecommendProducts",
    func=_recommend_products,
    description=(
        "Given a free-text query (e.g., 'red running shoes'), "
        "return the top-k product matches (name, SKU, price)."
    )
)
