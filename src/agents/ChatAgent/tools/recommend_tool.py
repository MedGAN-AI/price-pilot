'''
from langchain_core.tools import Tool

def _recommend_products(query: str) -> str:
    """
    Stub implementation. In a real system, you’d query your vector store,
    embeddings, or recommendation engine.
    """
    return f"Based on '{query}', we recommend: ProductA, ProductB, ProductC."

recommend_tool = Tool(
    name="RecommendTool",
    func=_recommend_products,
    description="Recommends products based on a search query string."
)
'''

import json
from typing import List
from supabase import Client
from langchain_core.tools import Tool

# Import the Supabase client
from src.integrations.supabase_client import supabase

def _recommend_products(query: str) -> str:
    """
    Given a free-form query string, run a simple ILIKE-based search
    against the `products` table in Supabase. Return up to 5 matching products
    (name, SKU, price).
    
    Input:
        query (str): A search string, e.g. "running shoes in size 10"
    Returns:
        A formatted string listing up to 5 products that match.
    """
    # 1) Perform a case-insensitive search on name or description
    #    Use ILIKE '%query%' on both columns. You might also use full-text search
    #    or pg_trgm for better performance. This is a simple ILIKE example.
    response = supabase.table("products") \
        .select("id, sku, name, description, price") \
        .ilike("name", f"%{query}%") \
        .or_(f"description.ilike.%{query}%") \
        .limit(5) \
        .execute()
    
    if response.error:
        # If Supabase returns an error, show a user-friendly message
        return f"Sorry, I encountered an error searching products: {response.error.message}"
    
    products = response.data  # type: List[dict]
    if not products:
        return f"No products found matching '{query}'."
    
    # 2) Build a human-readable list of matches
    lines: List[str] = [f"Top matches for '{query}':"]
    for idx, prod in enumerate(products, start=1):
        name = prod.get("name", "(no name)")
        sku = prod.get("sku", "(no sku)")
        price = prod.get("price", 0.00)
        lines.append(f"{idx}. {name} (SKU: {sku}) — ${price:.2f}")
    
    return "\n".join(lines)

# Wrap it as a LangChain Tool
recommend_tool = Tool(
    name="RecommendTool",
    func=_recommend_products,
    description=(
        "Searches for products in the catalog. Input: a free-text query string (e.g., 'black running shoes size 10'). "
        "Output: up to 5 matching products with name, SKU, and price."
    )
)
