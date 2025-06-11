"""
InventoryAgent - Stock checking and inventory management using core framework
Handles stock queries, availability checks, and inventory operations
"""
import os
import re
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

# Import inventory tools
from src.agents.InventoryAgent.tools.check_stock_tools import stock_by_sku_tool, stock_by_name_tool

# Load and standardize configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
raw_config = load_config(CONFIG_PATH)
config = standardize_agent_config(raw_config)

# Create LLM using core framework
llm = create_llm_from_config(config)

# Initialize error handler
error_handler = create_agent_error_handler("InventoryAgent")

# Setup tools
tools = [
    stock_by_sku_tool,    # CheckStockBySKU
    stock_by_name_tool,   # CheckStockByName
]

# Load prompt template
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "inventory_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Get specialized configuration
specialized_config = config.get("specialized_config", {})
sku_pattern_str = specialized_config.get("sku_pattern", "^[A-Z0-9\\-]{5,}$")
SKU_PATTERN = re.compile(sku_pattern_str)

# Build the InventoryAgent using core framework
agent_config = config.get("agent", {})
build_config = {
    "early_stopping_method": agent_config.get("early_stopping_method"),
    "max_execution_time": agent_config.get("max_execution_time"),
    "stop_keywords": specialized_config.get("stop_keywords", []),
    "context_key": specialized_config.get("context_key", "inventory_context")
}

inventory_assistant = build_agent(
    llm=llm,
    tools=tools,
    prompt_template=system_prompt,
    max_iterations=agent_config.get("max_iterations", 10),
    agent_type=AgentType.REACT,  # InventoryAgent uses ReAct pattern
    agent_config=build_config
)

# Helper functions for inventory operations
def is_inventory_related(message: str) -> bool:
    """Check if message is related to inventory/stock"""
    inventory_keywords = ["stock", "inventory", "available", "units", "in stock", "quantity", "how many"]
    return any(keyword in message.lower() for keyword in inventory_keywords)

def validate_sku(sku: str) -> bool:
    """Validate SKU format using configured pattern"""
    return bool(SKU_PATTERN.match(sku))

# Create wrapper class for easy testing and integration
class InventoryAgent:
    """Enhanced InventoryAgent using core framework"""
    
    def __init__(self):
        self.graph = inventory_assistant
        self.error_handler = error_handler
        self.config = config
        self.sku_pattern = SKU_PATTERN
    
    def process_query(self, query: str, context: dict = None) -> str:
        """Process an inventory query"""
        try:
            # Initialize state with inventory context
            state = initialize_state()
            
            # Add context if provided
            if context:
                state["context"] = {"inventory_context": context}
            
            # Add user message
            from langchain_core.messages import HumanMessage
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
                
                return response
            
            return 'No response generated'
            
        except Exception as e:
            return self.error_handler.handle_llm_error(e)
    
    def check_stock_by_sku(self, sku: str) -> str:
        """Quick stock check by SKU"""
        if not self.validate_sku(sku):
            return f"Invalid SKU format: {sku}"
        
        return self.process_query(f"How many units of {sku} are in stock?")
    
    def check_stock_by_name(self, product_name: str) -> str:
        """Quick stock check by product name"""
        return self.process_query(f"Do we have {product_name} in stock?")
    
    def validate_sku(self, sku: str) -> bool:
        """Validate SKU format"""
        return validate_sku(sku)
    
    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_name": "InventoryAgent",
            "status": "active",
            "tools_count": len(tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

# Export the compiled graph and utilities for orchestrator
__all__ = [
    'inventory_assistant',
    'initialize_state',
    'AgentState',
    'config',
    'InventoryAgent',
    'is_inventory_related',
    'validate_sku'
]

# Convenience function for direct invocation
def run_inventory_agent(message: str, context: dict = None) -> str:
    """Simple interface for running InventoryAgent"""
    agent = InventoryAgent()
    return agent.process_query(message, context)

# Test interface when run directly
if __name__ == "__main__":
    print("📦 InventoryAgent Test Interface - Core Framework Version")
    print("=" * 60)
    
    # Create agent instance
    inventory_agent = InventoryAgent()
    
    print("Available capabilities:")
    print("- Stock checking by SKU")
    print("- Stock checking by product name") 
    print("- Inventory availability queries")
    print("- SKU validation")
    print("\nTest queries:")
    print("- 'How many units of ABC-123 are in stock?'")
    print("- 'Do we have red shoes available?'")
    print("- 'Check inventory for SHOES-RED-001'")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input:
                response = inventory_agent.process_query(user_input)
                print(f"InventoryAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")
