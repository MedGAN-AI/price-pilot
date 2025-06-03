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
