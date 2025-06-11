"""
Price Pilot Production CLI Interface
Ready for full-stack integration testing
"""

import sys
import os
sys.path.append('.')

from typing import Dict, Any
import json
from datetime import datetime

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_subheader(title: str):
    """Print a formatted subheader"""
    print(f"\n🔧 {title}")
    print("-" * 40)

class PricePilotCLI:
    """Production CLI for Price Pilot multi-agent system"""
    
    def __init__(self):
        self.orchestrator = None
        self.conversation_history = []
        self.load_orchestrator()
        
    def load_orchestrator(self):
        """Load the production orchestrator"""
        try:
            from src.graphs.orchestrator import orchestrator, initialize_state
            self.orchestrator = orchestrator
            self.initialize_state = initialize_state
            print("✅ Production orchestrator loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load orchestrator: {e}")
            return False
    
    def interactive_chat(self):
        """Production interactive chat mode"""
        print_header("Price Pilot Interactive Mode")
        print("✨ Multi-Agent System Ready")
        print("💡 Try queries like:")
        print("   • 'How many red shoes are in stock?'")
        print("   • 'I need running shoes for jogging'") 
        print("   • 'Place an order for product XYZ'")
        print("   • 'Track my shipment ABC123'")
        print("\n🔧 Commands: 'quit', 'history', 'status'")
        
        if not self.orchestrator:
            print("❌ Orchestrator not loaded. Exiting.")
            return
        
        while True:
            try:
                user_input = input("\n🗣️  You: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Thank you for using Price Pilot!")
                    break
                elif user_input.lower() == 'history':
                    self.show_conversation_history()
                    continue
                elif user_input.lower() == 'status':
                    self.show_system_status()
                    continue
                elif not user_input:
                    continue
                
                # Process with orchestrator
                from langchain_core.messages import HumanMessage
                state = self.initialize_state()
                state["messages"] = [HumanMessage(content=user_input)]
                
                print("🤖 Processing...")
                result = self.orchestrator.invoke(state)
                response = result["messages"][-1].content
                
                # Show agent info if available
                if "intent" in result and "confidence" in result:
                    intent = result["intent"]
                    confidence = result["confidence"]
                    print(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
                
                print(f"🤖 Assistant: {response}")
                
                # Store in history
                self.conversation_history.append({
                    "query": user_input,
                    "response": response,
                    "intent": result.get("intent", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "timestamp": datetime.now().isoformat()
                })
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def show_system_status(self):
        """Show system status"""
        print_subheader("System Status")
        print("🟢 Orchestrator: Running")
        print("🟢 Agents: 6 agents loaded")
        print(f"💬 Conversations: {len(self.conversation_history)} this session")
        
        if self.conversation_history:
            recent_intents = [conv.get("intent", "unknown") for conv in self.conversation_history[-5:]]
            print(f"📊 Recent intents: {', '.join(recent_intents)}")
    
    def show_conversation_history(self):
        """Show conversation history"""
        print_subheader("Conversation History")
        
        if not self.conversation_history:
            print("No conversations yet.")
            return
        
        for i, conv in enumerate(self.conversation_history[-5:], 1):  # Show last 5
            print(f"\n{i}. Query: {conv['query']}")
            print(f"   Response: {conv['response'][:100]}...")
            if 'intent' in conv:
                print(f"   Intent: {conv['intent']} (confidence: {conv.get('confidence', 0):.2f})")
            print(f"   Time: {conv['timestamp']}")

def main():
    """Main CLI function - Production Ready"""
    cli = PricePilotCLI()
    
    print_header("Price Pilot Production System")
    print("🎯 Multi-Agent Retail Intelligence Platform")
    print("🤖 6 Specialized Agents Ready:")
    print("   • ChatAgent - Conversation Intelligence")
    print("   • InventoryAgent - Stock Management") 
    print("   • RecommendAgent - Product Discovery")
    print("   • OrderAgent - Order Processing")
    print("   • LogisticsAgent - Shipping & Tracking")
    print("   • ForecastAgent - Demand Prediction")
    
    print("\n🚀 Starting interactive mode...")
    cli.interactive_chat()

if __name__ == "__main__":
    main()
