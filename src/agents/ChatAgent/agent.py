# Agent’s business‐logic class (pure Python, easy to test in isolation). 
# classes we do it last after everything else is worked out

# Test script to verify the agent works correctly
import os
import sys
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.append('src')

def test_agent():
    """Test the shopping assistant agent"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if Google API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return False
    
    try:
        # Import the agent
        from agents.ChatAgent.llm_agent import agent_executor, shopping_assistant, initialize_state
        from langchain_core.messages import HumanMessage, SystemMessage
        
        print("=== Testing Shopping Assistant ===\n")
        
        # Test 1: Simple greeting
        print("Test 1: Simple greeting")
        result = agent_executor.invoke({"input": "hi"})
        print(f"Response: {result['output']}\n")
        
        # Test 2: Product search
        print("Test 2: Product search")
        result = agent_executor.invoke({"input": "I want shoes"})
        print(f"Response: {result['output']}\n")
        
        # Test 3: LangGraph version
        print("Test 3: LangGraph version")
        initial_state = initialize_state()
        initial_state["messages"] = [
            SystemMessage(content="You are a helpful shopping assistant."),
            HumanMessage(content="hello")
        ]
        
        response_state = shopping_assistant.invoke(initial_state)
        print(f"LangGraph Response: {response_state['messages'][-1].content}\n")
        
        print("✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_agent()