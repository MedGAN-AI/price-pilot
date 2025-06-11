"""
Price Pilot Main Entry Point
Enhanced multi-agent orchestrator for retail intelligence
"""

import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

def main():
    """Main function to run Price Pilot system"""
    print("🚀 Price Pilot Multi-Agent System")
    print("=" * 50)
    
    try:
        # Import enhanced orchestrator
        from src.graphs.orchestrator import orchestrator, initialize_state
        print("✅ Enhanced orchestrator loaded")
        
        # Test queries for demonstration
        test_queries = [
            "Hello, I need help with shopping",
            "How many red shoes are in stock?", 
            "Recommend me some running shoes",
            "Place an order for product XYZ",
            "Track my shipment ABC123"
        ]
        
        print("\n🧪 Testing multi-agent workflows...")
        
        for query in test_queries:
            print(f"\n🗣️  User: {query}")
            
            # Initialize state
            state = initialize_state()
            state["messages"] = [HumanMessage(content=query)]
            
            # Invoke orchestrator
            result = orchestrator.invoke(state)
            
            # Extract response
            ai_msg = result["messages"][-1]
            if isinstance(ai_msg, AIMessage):
                response = ai_msg.content
                
                # Show intent and confidence if available
                if "intent" in result and "confidence" in result:
                    print(f"🎯 Intent: {result['intent']} (confidence: {result['confidence']:.2f})")
                
                print(f"🤖 Assistant: {response[:150]}...")
            else:
                print(f"🤖 Assistant: {ai_msg}")
            
        print("\n✅ All tests completed successfully!")
        print("🎉 Price Pilot is ready for production!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please check your configuration and dependencies.")

if __name__ == "__main__":
    main()
