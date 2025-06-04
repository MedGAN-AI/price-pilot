import os
import re
import yaml
from typing import Any, Dict, TypedDict, Annotated, List

from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import our two inventory tools
from .tools.check_stock_tools import stock_by_sku_tool, stock_by_name_tool

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# LLM configuration
llm_provider   = config.get("llm", {}).get("provider", "google-genai")
llm_model      = config.get("llm", {}).get("model", "gemini-2.0-flash")
llm_temperature= config.get("llm", {}).get("temperature", 0.0)

# Inventory connector toggle (not strictly used here; connectors detect SUPABASE_AVAILABLE internally)
use_supabase = config.get("use_supabase", False)

# SKU regex (compile for reuse)
sku_pattern_str = config.get("sku_pattern", "^[A-Z0-9\\-]{5,}$")
SKU_PATTERN = re.compile(sku_pattern_str)

if llm_provider != "google-genai":
    raise ValueError(f"Unsupported llm.provider in config: {llm_provider}")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set in .env to use google-genai provider.")

llm = ChatGoogleGenerativeAI(
    model=llm_model,
    temperature=llm_temperature,
    api_key=GOOGLE_API_KEY
)

tools = [
    stock_by_sku_tool,    # CheckStockBySKU
    stock_by_name_tool,   # CheckStockByName
]

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "inventory_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

prompt = PromptTemplate.from_template(system_prompt)

agent = create_react_agent(llm, tools, prompt)

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True
)

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List


def initialize_state() -> AgentState:
    return {
        "messages": [],           # will hold HumanMessage/AIMessage
        "intermediate_steps": []  # used by AgentExecutor
    }

def is_inventory_related(message: str) -> bool:
    """
    Check if the message is related to inventory/stock queries.
    This example uses a small set of keywords plus a SKU pattern match.
    """
    inventory_keywords = [
        'stock', 'inventory', 'sku', 'product', 'item', 'available', 
        'units', 'left', 'have', 'in stock', 'quantity', 'how many'
    ]
    lower_msg = message.lower()

    # If any inventory keyword appears, return True
    for kw in inventory_keywords:
        if kw in lower_msg:
            return True

    # If the message contains something that matches the SKU regex, return True
    if SKU_PATTERN.search(message.upper()):
        return True

    return False

def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        # Extract the user's latest message content
        user_message = state["messages"][-1].content

        # If not inventory-related, respond with a help message
        if not is_inventory_related(user_message):
            response = (
                "Hello! I'm an InventoryAgent. I can help you check stock levels for products by name or SKU. "
                "Please ask me something like: 'How many units of SHOES-RED-001 are in stock?'"
            )
            return {
                "messages": [AIMessage(content=response)],
                "intermediate_steps": []
            }

        # Otherwise, pass the question into the AgentExecutor
        result = agent_executor.invoke({"input": user_message})

        # The result["output"] is typically a string; if it’s a dict, normalize to text
        content = result["output"]
        if isinstance(content, dict):
            # If nested, try common keys
            if "output" in content:
                content = content["output"]
            elif "tool_input" in content:
                content = content["tool_input"]
            else:
                content = str(content)

        # Return just that single AIMessage; clearing intermediate_steps to end the loop
        return {
            "messages": [AIMessage(content=content)],
            "intermediate_steps": []
        }

    except Exception as e:
        error_msg = (
            f"I apologize, but I encountered an error: {str(e)}. "
            "Please try again or ask me about product inventory."
        )
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": []
        }
    
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
inventory_assistant = builder.compile()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    print("=== InventoryAgent AgentExecutor Test ===")
    try:
        test_result = agent_executor.invoke({
            "input": "How many units of SHOES-RED-001 are in stock?"
        })
        print("AgentExecutor output:\n", test_result["output"])
    except Exception as e:
        print(f"AgentExecutor test failed: {e}")

    print("\n=== InventoryAgent LangGraph Test ===")
    try:
        state = initialize_state()
        state["messages"] = [
            HumanMessage(content="Do we have any Red Running Shoes left?")
        ]
        state["intermediate_steps"] = []
        response_state = inventory_assistant.invoke(state)
        print("LangGraph response:\n", response_state["messages"][-1].content)
    except Exception as e:
        print(f"LangGraph test failed: {e}")
