"""
OrderAgent - Handles order creation, status checking, and order management
Uses the shared base agent framework for consistency across agents
"""
import os
import yaml
from typing import List

# Import base agent framework
from core.base_agent import build_agent, create_llm_from_config, load_prompt_from_file, AgentState, initialize_state

# Import order tools
from .tools.order_tools import (
    create_order_tool,
    check_order_status_tool,
    update_order_status_tool,
    cancel_order_tool
)

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Create LLM from config
llm = create_llm_from_config(config)

# Load system prompt
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "order_prompt.txt")
prompt = load_prompt_from_file(PROMPT_PATH)

# Define tools for this agent
tools = [
    create_order_tool,
    check_order_status_tool,
    update_order_status_tool,
    cancel_order_tool
]

# Build the agent using shared framework
max_iterations = config.get("max_iterations", 10)
order_agent_graph = build_agent(llm, tools, prompt, max_iterations)

# Export the compiled graph and utilities
__all__ = [
    'order_agent_graph',
    'initialize_state',
    'AgentState',
    'config',
    'OrderAgent'
]

# Create a simple wrapper class for testing
class OrderAgent:
    """Simple wrapper for the OrderAgent for easier testing"""
    
    def __init__(self):
        self.graph = order_agent_graph
    
    def process_query(self, query: str) -> str:
        """Process a query using the order agent"""
        state = initialize_state()
        state['messages'] = [{"type": "human", "content": query}]
        
        result = self.graph.invoke(state)
        
        # Extract the final message content
        if result.get('messages'):
            final_message = result['messages'][-1]
            # Handle different message types - AIMessage has .content attribute, not .get()
            if hasattr(final_message, 'content'):
                return final_message.content
            elif isinstance(final_message, dict):
                return final_message.get('content', 'No response')
            else:
                return str(final_message)
        return 'No response'

# Convenience function for direct invocation
def run_order_agent(message: str) -> str:
    """
    Convenience function to run the OrderAgent with a single message.
    
    Args:
        message: The user's message/request
    
    Returns:
        The agent's response as a string
    """
    from langchain_core.messages import HumanMessage
    
    # Initialize state
    state = initialize_state()
    state["messages"] = [HumanMessage(content=message)]
    
    # Run the agent
    result = order_agent_graph.invoke(state)
    
    # Extract the response
    if result and "messages" in result and result["messages"]:
        return result["messages"][-1].content
    else:
        return "I apologize, but I encountered an issue processing your request."


if __name__ == "__main__":
    # Simple test interface
    print("OrderAgent Test Interface")
    print("=" * 50)
    print("Available commands:")
    print("- Create order: create order for customer@example.com with items [{'sku': 'ABC123', 'quantity': 2}]")
    print("- Check status: check status of order ORDER_ID")
    print("- Update status: update order ORDER_ID to confirmed")
    print("- Cancel order: cancel order ORDER_ID")
    print("- Type 'quit' to exit")
    print()
    
    while True:
        try:
            user_input = input("OrderAgent> ").strip()
            
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if not user_input:
                continue
                
            response = run_order_agent(user_input)
            print(f"Response: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print()