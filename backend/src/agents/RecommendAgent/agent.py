"""
RecommendAgent - Product recommendation using core framework
Handles vector-based product search and personalized recommendations
"""
import os
from typing import List

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

# Import recommendation tools
from src.agents.RecommendAgent.tools.recommend_tool import recommend_tool

# Import memory tools for user context access
from src.agents.ChatAgent.tools.memory_tools import memory_tools

# Load and standardize configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
raw_config = load_config(CONFIG_PATH)
config = standardize_agent_config(raw_config)

# Create LLM using core framework
llm = create_llm_from_config(config)

# Initialize error handler
error_handler = create_agent_error_handler("RecommendAgent")

# Setup tools
tools = [recommend_tool] + memory_tools

# Load prompt template
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "recommend_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Build the RecommendAgent using core framework
agent_config = config.get("agent", {})
specialized_config = config.get("specialized_config", {})

build_config = {
    "early_stopping_method": agent_config.get("early_stopping_method", "generate"),
    "max_execution_time": agent_config.get("max_execution_time", 30),
    "top_k": specialized_config.get("top_k", 5),
    "similarity_threshold": specialized_config.get("similarity_threshold", 0.7),
    "context_key": specialized_config.get("context_key", "recommendation_context")
}

recommend_assistant = build_agent(
    llm=llm,
    tools=tools,
    prompt_template=system_prompt,
    max_iterations=agent_config.get("max_iterations", 10),
    agent_type=AgentType.REACT,  # RecommendAgent uses ReAct pattern
    agent_config=build_config
)

# Create wrapper class for easy testing and integration
class RecommendAgent:
    """Enhanced RecommendAgent using core framework"""

    def __init__(self):
        self.graph = recommend_assistant
        self.error_handler = error_handler
        self.config = config

    def process_query(self, query: str, context: dict = None) -> str:
        """Process a recommendation query"""
        try:
            # Initialize state with recommendation context
            state = initialize_state()

            # Add context if provided
            if context:
                state["context"] = {"recommendation_context": context}

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

    def recommend_products(self, query: str) -> str:
        """Quick product recommendation"""
        return self.process_query(f"Find products similar to: {query}")

    def search_by_category(self, category: str) -> str:
        """Search products by category"""
        return self.process_query(f"Show me products in the {category} category")

    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_name": "RecommendAgent",
            "status": "active",
            "tools_count": len(tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

# Export the compiled graph and utilities for orchestrator
__all__ = [
    "recommend_assistant",
    "initialize_state",
    "AgentState",
    "config",
    "RecommendAgent"
]

# Convenience function for direct invocation
def run_recommend_agent(message: str, context: dict = None) -> str:
    """Simple interface for running RecommendAgent"""
    agent = RecommendAgent()
    return agent.process_query(message, context)

# Test interface when run directly
if __name__ == "__main__":
    print("🎯 RecommendAgent Test Interface - Core Framework Version")
    print("=" * 60)
    
    # Create agent instance
    recommend_agent = RecommendAgent()
    
    print("Available capabilities:")
    print("- Vector-based product search")
    print("- Personalized recommendations") 
    print("- Category-based browsing")
    print("- Similarity scoring")
    print("\nTest queries:")
    print("- 'I'm looking for red running shoes'")
    print("- 'Find products similar to SHOES-RED-001'")
    print("- 'Show me electronics under $100'")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input:
                response = recommend_agent.process_query(user_input)
                print(f"RecommendAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")
