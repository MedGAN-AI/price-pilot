import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from llm_config import summary_chain

# Load and embed product data
class RecommendAgent:
    def __init__(self, data_path="data/products.csv"):
        self.df = pd.read_csv(data_path)
        self.df["combined"] = self.df["product_name"] + " - " + self.df["description"]
        self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = self.embed_model.encode(self.df["combined"].tolist(), show_progress_bar=True)
        self.index = faiss.IndexFlatL2(self.embeddings.shape[1])
        self.index.add(np.array(self.embeddings))

    def recommend(self, query: str, top_k=3):
        query_vec = self.embed_model.encode([query])
        D, I = self.index.search(np.array(query_vec), top_k)
        recommendations = []
        for idx in I[0]:
            product = self.df.iloc[idx]
            summary = summary_chain.invoke({"product_description": product["combined"]})
            recommendations.append({
                "product_name": product["product_name"],
                "category": product["category"],
                "price": product["price"],
                "summary": summary
            })
        return recommendations
