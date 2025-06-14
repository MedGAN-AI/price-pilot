"""
LogisticsAgent - Shipment tracking and logistics management using core framework
Handles Aramex and Naqel logistics operations
"""
import os
import sys
from typing import List

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core framework
from src.core import (
    build_agent,
    create_llm_from_config,
    AgentState,
    initialize_state,
    AgentType,
    standardize_agent_config,
    load_config,
    create_agent_error_handler
)

# Import logistics tools
from src.agents.LogisticsAgent.tools.logistics_tools import create_logistics_tools

# Load and standardize configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
raw_config = load_config(CONFIG_PATH)
config = standardize_agent_config(raw_config)

# Create LLM using core framework
llm = create_llm_from_config(config)

# Initialize error handler
error_handler = create_agent_error_handler("LogisticsAgent")

# Setup tools
tools = create_logistics_tools()

# Load prompt template
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "logistics_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Build the LogisticsAgent using core framework
agent_config = config.get("agent", {})
specialized_config = config.get("specialized_config", {})

build_config = {
    "early_stopping_method": agent_config.get("early_stopping_method", "force"),
    "max_execution_time": agent_config.get("max_execution_time", 30),
    "delay_threshold_hours": specialized_config.get("delay_threshold_hours", 4),
    "context_key": specialized_config.get("context_key", "logistics_context")
}

logistics_assistant = build_agent(
    llm=llm,
    tools=tools,
    prompt_template=system_prompt,
    max_iterations=agent_config.get("max_iterations", 10),
    agent_type=AgentType.REACT,  # LogisticsAgent uses ReAct pattern
    agent_config=build_config
)

# Create wrapper class for easy testing and integration
class LogisticsAgent:
    """Enhanced LogisticsAgent using core framework"""

    def __init__(self):
        self.graph = logistics_assistant
        self.error_handler = error_handler
        self.config = config

    def process_query(self, query: str, context: dict = None) -> str:
        """Process a logistics query"""
        try:
            # Initialize state with logistics context
            state = initialize_state()

            # Add context if provided
            if context:
                state["context"] = {"logistics_context": context}

            # Add user message
            from langchain_core.messages import HumanMessage
            state["messages"] = [HumanMessage(content=query)]

            # Invoke agent
            result = self.graph.invoke(state)

            # Extract response
            if result.get("messages"):
                final_message = result["messages"][-1]
                if hasattr(final_message, "content"):
                    response = final_message.content
                elif isinstance(final_message, dict):
                    response = final_message.get("content", "No response")
                else:
                    response = str(final_message)

                return response

            return "No response generated"

        except Exception as e:
            return self.error_handler.handle_llm_error(e)

    def track_shipment(self, tracking_number: str) -> str:
        """Quick shipment tracking"""
        return self.process_query(f"Track shipment {tracking_number}")

    def schedule_pickup(self, details: dict) -> str:
        """Quick pickup scheduling"""
        return self.process_query(f"Schedule pickup with details: {details}")

    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_name": "LogisticsAgent",
            "status": "active",
            "tools_count": len(tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

# Export the compiled graph and utilities for orchestrator
__all__ = [
    "logistics_assistant",
    "initialize_state",
    "AgentState",
    "config",
    "LogisticsAgent"
]

# Convenience function for direct invocation
def run_logistics_agent(message: str, context: dict = None) -> str:
    """Simple interface for running LogisticsAgent"""
    agent = LogisticsAgent()
    return agent.process_query(message, context)

# Test interface when run directly
if __name__ == "__main__":
    print("🚚 LogisticsAgent Test Interface - Core Framework Version")
    print("=" * 60)
    
    # Create agent instance
    logistics_agent = LogisticsAgent()
    
    print("Available capabilities:")
    print("- Shipment tracking")
    print("- Pickup scheduling") 
    print("- Carrier status checking")
    print("- Delivery rerouting")
    print("\nTest queries:")
    print("- 'Track shipment TR12345'")
    print("- 'Schedule pickup for package PKG-001'")
    print("- 'What is the status of delivery DEL-456?'")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input:
                response = logistics_agent.process_query(user_input)
                print(f"LogisticsAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")