"""
ChatAgent - Enhanced conversational agent using core framework
Handles complex conversations, agent coordination, and delegation
"""
import os
from typing import Any, Dict, List
from langchain_core.tools import Tool

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

# ChatAgent specific tools
from src.agents.ChatAgent.tools.delegation_tools import delegation_tools
from src.agents.ChatAgent.tools.memory_tools import memory_tools, save_interaction

# Load and standardize configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
raw_config = load_config(CONFIG_PATH)
config = standardize_agent_config(raw_config)

# Create LLM using core framework
llm = create_llm_from_config(config)

# Initialize error handler
error_handler = create_agent_error_handler("ChatAgent")

# Setup tools - delegation tools, memory tools, plus Final Answer
tools = delegation_tools + memory_tools + [
    Tool(
        name="Final Answer",
        func=lambda x: x,  
        description="Use this tool to output your final answer to the user."
    )
]

# Load system prompt from file
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "chat_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Build the ChatAgent using core framework
agent_config = config.get("agent", {})
specialized_config = config.get("specialized_config", {})

build_config = {
    "early_stopping_method": agent_config.get("early_stopping_method", "force"),
    "max_execution_time": agent_config.get("max_execution_time", 60),
    "delegation_enabled": specialized_config.get("delegation_enabled", True),
    "memory_enabled": specialized_config.get("memory_enabled", True),
    "context_key": specialized_config.get("context_key", "conversation_context")
}

shopping_assistant = build_agent(
    llm=llm,
    tools=tools,
    prompt_template=system_prompt,
    max_iterations=agent_config.get("max_iterations", 10),
    agent_type=AgentType.STRUCTURED_CHAT,
    agent_config=build_config
)

# Create wrapper class for easy testing and integration
class ChatAgent:
    """Enhanced ChatAgent using core framework"""
    
    def __init__(self):
        self.graph = shopping_assistant
        self.error_handler = error_handler
        self.config = config
    
    def process_query(self, query: str, chat_history: List = None) -> str:
        """Process a conversational query"""
        try:
            # Import required message types
            from langchain_core.messages import HumanMessage
            
            # Initialize state with conversation context
            state = initialize_state()
            
            # Add chat history if provided
            if chat_history:
                state["context"] = {"conversation_context": chat_history}
            
            # FIXED: Ensure we're using the exact user input, not any hardcoded examples
            # Add user message directly without modification
            state["messages"] = [HumanMessage(content=query)]
            
            # Invoke agent
            result = self.graph.invoke(state)
            
            # Extract response
            if result.get("messages"):
                final_message = result["messages"][-1]
                if hasattr(final_message, 'content'):
                    response = final_message.content
                elif isinstance(final_message, dict):
                    response = final_message.get('content', 'No response')
                else:
                    response = str(final_message)
                
                # Save interaction for memory
                save_interaction(query, response)
                return response
            
            return 'No response generated'
            
        except Exception as e:
            return self.error_handler.handle_llm_error(e)
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation"""
        # This would integrate with memory tools
        return "Conversation summary feature coming soon!"
    
    def reset_conversation(self):
        """Reset conversation context"""
        # This would clear conversation memory
        pass
    
    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_name": "ChatAgent",
            "status": "active",
            "tools_count": len(tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

# Export the compiled graph and utilities for orchestrator
__all__ = [
    'shopping_assistant',
    'initialize_state',
    'AgentState',
    'config',
    'ChatAgent'
]

# Convenience function for direct invocation
def run_chat_agent(message: str, chat_history: List = None) -> str:
    """Simple interface for running ChatAgent"""
    agent = ChatAgent()
    return agent.process_query(message, chat_history)

# Test interface when run directly
if __name__ == "__main__":
    print("🤖 ChatAgent Test Interface - Core Framework Version")
    print("=" * 60)
    
    # Create agent instance
    chat_agent = ChatAgent()
    
    print("Available capabilities:")
    print("- Complex conversation handling")
    print("- Agent delegation and coordination") 
    print("- Memory and context management")
    print("- Error handling and recovery")
    print("\nTest queries:")
    print("- 'What products do you have?'")
    print("- 'I need to track my order'")
    print("- 'Can you recommend something for me?'")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input:
                response = chat_agent.process_query(user_input)
                print(f"ChatAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")
