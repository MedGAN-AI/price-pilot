import os
import numpy as np
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain.docstore.document import Document
from langchain.tools import Tool
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

'''this implementation is for the retriever tool we can change it later to use the write database'''

# Load environment variables
load_dotenv(override=True)

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Initialize embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

class ProductRetriever:
    def __init__(self):
        self.documents = []
        self.embeddings = None
        self._load_data()
    
    def _load_data(self):
        """Load product data from Supabase and create document objects"""
        # Replace with your actual table name and fields
        response = supabase.table("online_retail_clean").select("*").execute()
        products = response.data
        
        if not products:
            print("Warning: No products found in database")
            return
        
        # Create documents from products
        self.documents = []
        for product in products:
            content = (
                f"StockCode: {product.get('StockCode', '')}\n"
                f"Description: {product.get('Description', '')}\n"
                f"Price: {product.get('Price', '')}\n"
                f"Country: {product.get('Country', '')}\n"
                f"Quantity: {product.get('Quantity', '')}"
            )
            doc = Document(page_content=content, metadata=product)
            self.documents.append(doc)
        
        # Generate embeddings for all documents
        if self.documents:
            texts = [doc.page_content for doc in self.documents]
            self.embeddings = model.encode(texts)
            print(f"Generated embeddings for {len(self.documents)} products")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """Retrieve the most relevant documents for a given query"""
        if not self.documents or self.embeddings is None:
            return []
        
        # Encode the query
        query_embedding = model.encode(query)
        
        # Calculate similarities
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Return the most relevant documents
        return [self.documents[i] for i in top_indices]

# Create retriever instance
product_retriever = ProductRetriever()

# Create a tool for the agent to use
retrieval_tool = Tool(
    name="ProductRetriever",
    description="Useful for retrieving product information. Input should be a search query about products.",
    func=lambda query: "\n\n".join([doc.page_content for doc in product_retriever.retrieve(query)])
)

# Example usage as a standalone function (for testing)
def search_products(query: str) -> List[Dict[str, Any]]:
    """Search for products matching the query"""
    docs = product_retriever.retrieve(query)
    return [doc.metadata for doc in docs]

if __name__ == "__main__":
    # Test the retriever
    query = "red christmas decorations"
    results = search_products(query)
    print(f"Found {len(results)} results for '{query}':")
    for i, result in enumerate(results):
        print(f"{i+1}. {result.get('Description', 'No description')} - £{result.get('Price', 'N/A')}")
