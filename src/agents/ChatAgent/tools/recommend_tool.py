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

from typing import List
from langchain_core.tools import Tool

def _recommend_products(query: str) -> str:
    """
    Perform a case-insensitive search on `products` by name or description,
    returning up to 5 matching items (name, SKU, price). If Supabase returns
    an HTTP error code, or no data is found, we return an appropriate message.

    Input:
        query (str): free-text search, e.g. "red shoes size 10"
    Returns:
        str: formatted list of up to 5 matching products, or an error/no-results message.
    """
    try:
        # Import here to handle potential import errors gracefully
        from src.integrations.supabase_client import supabase
        
        # Test if supabase client is properly initialized
        if not supabase:
            return "Sorry, the product database is currently unavailable. Please try again later."
        
        # 1) Query Supabase: search name ILIKE '%query%' OR description ILIKE '%query%'
        #    Note: we build a filter string for OR, since supabase-py requires .or_() format.
        or_filter = f"name.ilike.%{query}%,description.ilike.%{query}%"
        
        response = (
            supabase
            .table("products")
            .select("id, sku, name, price")
            .or_(or_filter)
            .limit(5)
            .execute()
        )

        # 2) Check for response and data
        if not response:
            return "Sorry, I couldn't search products due to a database connection issue."
        
        # Check for errors in the response
        if hasattr(response, 'error') and response.error:
            return f"Sorry, I couldn't search products due to an error: {response.error}"

        # 3) Retrieve data
        products = getattr(response, "data", None)
        if not products:
            # No matches
            return f"No products found matching '{query}'. Try different keywords like 'shoes', 'shirt', 'jacket', etc."

        # 4) Format up to 5 results
        lines: List[str] = [f"Top matches for '{query}':"]
        for idx, prod in enumerate(products, start=1):
            name = prod.get("name", "(no name)")
            sku = prod.get("sku", "(no sku)")
            price = prod.get("price", 0.00)
            lines.append(f"{idx}. {name} (SKU: {sku}) — ${price:.2f}")

        return "\n".join(lines)
        
    except ImportError as e:
        return "Sorry, the product database connection is not configured. Please check your database setup."
    except Exception as e:
        return f"Sorry, I encountered an error while searching for products: {str(e)}. Please try again with different keywords."

# Wrap it as a LangChain Tool
recommend_tool = Tool(
    name="RecommendTool",
    func=_recommend_products,
    description=(
        "Searches for products in the catalog. Input: a free-text query string "
        "(e.g., 'red running shoes size 10'). Output: up to 5 matching products "
        "with name, SKU, and price."
    )
)