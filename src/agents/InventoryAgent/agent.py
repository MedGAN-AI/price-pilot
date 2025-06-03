import os
import yaml
from typing import Any, Dict, TypedDict, Annotated, List

# Load environment variables
from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import inventory tools
from .tools.inventory_check_tool import inventory_check_tool
from .tools.low_stock_tool import low_stock_tool
from .tools.inventory_update_tool import inventory_update_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Instantiate the Google generative AI LLM (Gemini)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    api_key=GOOGLE_API_KEY
)

# Collect all inventory tools plus a "Final Answer" tool
tools = [
    inventory_check_tool,
    low_stock_tool,
    inventory_update_tool,
    Tool(
        name="Final Answer",
        func=lambda x: x,
        description="Use this tool to output your final answer to the user."
    )
]

# Load system prompt from file
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "inventory_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt_template = f.read()

# Format the system prompt with tools information
tool_names = [tool.name for tool in tools if tool.name != "Final Answer"]
tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

system_prompt = system_prompt_template.format(
    tools=tool_descriptions,
    tool_names=", ".join([f'"{name}"' for name in tool_names])
)

# Simplified human template
human_template = """{input}

{agent_scratchpad}"""

# Setup the agent with tools
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", human_template),
])

# Create the structured chat agent
agent = create_structured_chat_agent(llm, tools, prompt)

# Wrap it in an AgentExecutor to handle intermediate steps
inventory_agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=config.get("verbose", True),
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True
)

# Define the shared state type for LangGraph
class InventoryAgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List

# Helper to initialize a fresh state
def initialize_inventory_state() -> InventoryAgentState:
    return {
        "messages": [],
        "intermediate_steps": []
    }

# "assistant" node: calls the AgentExecutor on the last user message
def inventory_assistant(state: InventoryAgentState) -> Dict[str, Any]:
    try:
        # Extract the user's latest message content
        user_message = state["messages"][-1].content
        chat_history = state["messages"][:-1]

        # Invoke the AgentExecutor
        result = inventory_agent_executor.invoke({
            "input": user_message,
            "chat_history": chat_history
        })

        # Check if output is a dictionary with 'tool_input' key (happens with Final Answer)
        content = result["output"]
        if isinstance(content, dict) and "tool_input" in content:
            content = content["tool_input"]

        # Wrap the LLM's output as an AIMessage and carry forward any intermediate steps
        return {
            "messages": [AIMessage(content=content)],
            "intermediate_steps": result.get("intermediate_steps", [])
        }
    except Exception as e:
        error_msg = f"I apologize, but I encountered an error while checking inventory: {str(e)}. Please try again or provide a valid SKU."
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": []
        }

# "tools" node: placeholder (AgentExecutor already ran the tool), just return state
def inventory_tool_node(state: InventoryAgentState) -> Dict[str, Any]:
    return state

# Build the LangGraph StateGraph
builder = StateGraph(InventoryAgentState)
builder.add_node("assistant", inventory_assistant)
builder.add_node("tools", inventory_tool_node)

# If intermediate_steps is non-empty, go to the tools node; else, end
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    lambda st: len(st["intermediate_steps"]) > 0,
    {
        True: "tools",
        False: END
    }
)
builder.add_edge("tools", "assistant")

# Compile the graph
inventory_assistant_graph = builder.compile()

# Class-based approach for easy integration
class InventoryAgent:
    """
    Inventory Agent that handles stock level queries, low stock alerts,
    and basic inventory management operations.
    """
    
    def __init__(self):
        self.agent_executor = inventory_agent_executor
        self.graph = inventory_assistant_graph
        self.config = config
    
    def check_stock(self, sku: str) -> str:
        """Check stock level for a specific SKU"""
        try:
            result = self.agent_executor.invoke({
                "input": f"Check stock level for SKU: {sku}"
            })
            return result["output"]
        except Exception as e:
            return f"Error checking stock for {sku}: {str(e)}"
    
    def get_low_stock_items(self, limit: int = None) -> str:
        """Get list of items with low stock"""
        try:
            limit = limit or self.config.get("max_low_stock_items", 5)
            result = self.agent_executor.invoke({
                "input": f"Show me low stock items (limit: {limit})"
            })
            return result["output"]
        except Exception as e:
            return f"Error getting low stock items: {str(e)}"
    
    def update_inventory(self, sku: str, quantity: int, operation: str = "set") -> str:
        """Update inventory for a specific SKU"""
        try:
            result = self.agent_executor.invoke({
                "input": f"Update inventory for SKU {sku}: {operation} quantity to {quantity}"
            })
            return result["output"]
        except Exception as e:
            return f"Error updating inventory for {sku}: {str(e)}"
    
    def process_query(self, query: str) -> str:
        """Process any inventory-related query"""
        try:
            result = self.agent_executor.invoke({"input": query})
            return result["output"]
        except Exception as e:
            return f"Error processing query: {str(e)}"
    
    def process_with_graph(self, query: str) -> str:
        """Process query using LangGraph"""
        try:
            initial_state = initialize_inventory_state()
            initial_state["messages"] = [
                SystemMessage(content="You are an Inventory Agent for checking product stock levels."),
                HumanMessage(content=query)
            ]
            initial_state["intermediate_steps"] = []
            
            response_state = self.graph.invoke(initial_state)
            return response_state["messages"][-1].content
        except Exception as e:
            return f"Error processing query with graph: {str(e)}"

# Allow running this file standalone for testing
if __name__ == "__main__":
    # Test the inventory agent
    print("=== Testing Inventory Agent ===\n")
    
    agent = InventoryAgent()
    
    # Test 1: Check stock for a specific SKU
    print("Test 1: Check stock for SKU")
    result = agent.check_stock("SHOES-RED-001")
    print(f"Result: {result}\n")
    
    # Test 2: Get low stock items
    print("Test 2: Get low stock items")
    result = agent.get_low_stock_items()
    print(f"Result: {result}\n")
    
    # Test 3: Process general query
    print("Test 3: General inventory query")
    result = agent.process_query("What products are running low on stock?")
    print(f"Result: {result}\n")
    
    # Test 4: LangGraph version
    print("Test 4: LangGraph version")
    result = agent.process_with_graph("Check inventory status for all products")
    print(f"LangGraph Result: {result}\n")
    
    print("✅ All inventory agent tests completed!")