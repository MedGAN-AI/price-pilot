"""
Gemini-Powered Intent Detection System
Production-ready intent detection using Google Gemini embeddings
"""
import os
import json
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-generativeai not available")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiIntentDetector:
    """
    Production-ready Gemini-powered intent detection system
    Uses Google's text-embedding-004 for high-accuracy intent classification
    """
    
    def __init__(self):
        """Initialize the detector with Gemini configuration"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package is required")
            
        # Configure Gemini API
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
            
        genai.configure(api_key=self.api_key)
        
        # Use the same embedding model as RecommendAgent (working model)
        self.embedding_model = "models/text-embedding-004"
        
        # Define intent training examples
        self.training_data = {
            "price": [
                "What is the price of iPhone 15?",
                "How much does a Samsung Galaxy cost?",
                "Show me the cost of MacBook Pro",
                "What's the price range for tablets?",
                "How expensive is the iPhone 14?",
                "Price check for Dell laptop",
                "Cost of wireless headphones",
                "What does this product cost?",
                "Show pricing information",
                "How much is this item?"
            ],
            "order": [
                "I want to buy 5 laptops",
                "Place an order for 3 tablets",
                "Add 2 phones to my cart",
                "I need to purchase 10 smartphones",
                "Buy me a MacBook",
                "Order 4 wireless mice",
                "I want to order this product",
                "Purchase 2 gaming headsets",
                "Add to cart",
                "I'll take 3 of these"
            ],
            "inventory": [
                "How many smartphones are in stock?",
                "Do you have any MacBooks available?",
                "Check stock for gaming laptops",
                "Are there tablets in inventory?",
                "Stock levels for iPhone 15",
                "What's available in the warehouse?",
                "How many units do we have?",
                "Inventory status for laptops",
                "Stock check for wireless earbuds",
                "Available quantity for this item"
            ],
            "recommend": [
                "Can you recommend a good tablet for work?",
                "What's the best smartphone under $500?",
                "Suggest a laptop for gaming",
                "Which headphones would you recommend?",
                "Best tablet for students",
                "Recommend a budget phone",
                "What laptop is good for programming?",
                "Suggest wireless earbuds",
                "Best phone for photography",
                "Recommend a work laptop"
            ],
            "status": [
                "Show me the order status for order #12345",
                "Track my recent purchase",
                "What's the status of my order?",
                "Order tracking information",
                "When will my package arrive?",
                "Check delivery status",
                "Where is my order?",
                "Order #67890 status",
                "Track shipment",
                "Delivery information"
            ]
        }
        
        # Cache for embeddings to avoid repeated API calls
        self.embedding_cache = {}
        
        # Pre-compute training embeddings
        self._initialize_training_embeddings()
        
        logger.info("GeminiIntentDetector initialized successfully")
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text using Gemini API (same approach as RecommendAgent)"""
        if text in self.embedding_cache:
            return self.embedding_cache[text]
            
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="semantic_similarity"
            )
            
            if result and 'embedding' in result:
                embedding = np.array(result['embedding'])
                self.embedding_cache[text] = embedding
                return embedding
            else:
                logger.warning(f"No embedding returned for: {text[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"Embedding API error: {e}")
            return None
    
    def _initialize_training_embeddings(self):
        """Pre-compute embeddings for all training examples"""
        logger.info("Computing training embeddings...")
        self.training_embeddings = {}
        
        for intent, examples in self.training_data.items():
            self.training_embeddings[intent] = []
            for example in examples:
                embedding = self._get_embedding(example)
                if embedding is not None:
                    self.training_embeddings[intent].append(embedding)
                    
        logger.info(f"Training embeddings computed for {len(self.training_embeddings)} intents")
    
    def _compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        try:
            # Normalize vectors
            embedding1_norm = embedding1 / np.linalg.norm(embedding1)
            embedding2_norm = embedding2 / np.linalg.norm(embedding2)
            
            # Compute cosine similarity
            similarity = np.dot(embedding1_norm, embedding2_norm)
            return float(similarity)
        except:
            return 0.0
    
    def detect_intent(self, query: str) -> Dict[str, Any]:
        """
        Detect intent for a given query
        Returns: {
            "intent": str,
            "confidence": float,
            "query": str,
            "timestamp": str
        }
        """
        # Get query embedding
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to generate embedding"
            }
        
        # Find best matching intent
        best_intent = "unknown"
        best_confidence = 0.0
        intent_scores = {}
        
        for intent, embeddings in self.training_embeddings.items():
            if not embeddings:
                continue
                
            # Compute similarity with all training examples for this intent
            similarities = []
            for training_embedding in embeddings:
                similarity = self._compute_similarity(query_embedding, training_embedding)
                similarities.append(similarity)
            
            # Use max similarity as the score for this intent
            intent_score = max(similarities) if similarities else 0.0
            intent_scores[intent] = intent_score
            
            if intent_score > best_confidence:
                best_confidence = intent_score
                best_intent = intent
        
        # Apply confidence threshold
        if best_confidence < 0.6:  # Lower threshold for better recall
            best_intent = "unknown"
            best_confidence = 0.0
        
        return {
            "intent": best_intent,
            "confidence": best_confidence,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "all_scores": intent_scores
        }
    
    def add_training_example(self, intent: str, example: str):
        """Add a new training example and update embeddings"""
        if intent not in self.training_data:
            self.training_data[intent] = []
            self.training_embeddings[intent] = []
        
        self.training_data[intent].append(example)
        
        # Compute embedding for the new example
        embedding = self._get_embedding(example)
        if embedding is not None:
            self.training_embeddings[intent].append(embedding)
            logger.info(f"Added training example for '{intent}': {example}")
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents"""
        return list(self.training_data.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics"""
        total_training_examples = sum(len(examples) for examples in self.training_data.values())
        total_embeddings = sum(len(embeddings) for embeddings in self.training_embeddings.values())
        
        return {
            "model": self.embedding_model,
            "supported_intents": self.get_supported_intents(),
            "total_training_examples": total_training_examples,
            "total_embeddings": total_embeddings,
            "embedding_cache_size": len(self.embedding_cache)
        }

# Test function
def test_detector():
    """Test the detector with sample queries"""
    print("🧪 Testing Clean Gemini Intent Detector")
    print("=" * 50)
    
    try:
        detector = GeminiIntentDetector()
        
        test_queries = [
            "What is the price of iPhone 15?",
            "I want to buy 5 laptops", 
            "How many smartphones are in stock?",
            "Can you recommend a good tablet for work?",
            "Show me the order status for order #12345",
            "What's the best phone under $300?"
        ]
        
        for query in test_queries:
            result = detector.detect_intent(query)
            print(f"Query: \"{query}\"")
            print(f"Intent: {result['intent']} (confidence: {result['confidence']:.3f})")
            print()
        
        # Show stats
        stats = detector.get_stats()
        print("📊 Detector Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_detector()
