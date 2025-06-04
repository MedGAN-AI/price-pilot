import os
from typing import Any, Dict, TypedDict, Annotated, List

from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import our two inventory tools
from .tools.check_stock_tools import stock_by_sku_tool, stock_by_name_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Must be set in your .env

# Initialize the LLM (Gemini)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    temperature=0.0,
    api_key=GOOGLE_API_KEY
)

# Collect all tools
tools = [
    stock_by_sku_tool,    # CheckStockBySKU
    stock_by_name_tool,   # CheckStockByName
]

# Create a ReAct prompt template
prompt = PromptTemplate.from_template("""
You are an InventoryAgent for a retail company. Customers ask you about stock levels.

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")

# Create ReAct agent instead of structured chat agent
agent = create_react_agent(llm, tools, prompt)

# Wrap in an AgentExecutor
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True
)

# Define the shared state type for LangGraph
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List

# Helper to initialize a fresh state
def initialize_state() -> AgentState:
    return {
        "messages": [],           # will hold SystemMessage/HumanMessage/AIMessage
        "intermediate_steps": []  # for the AgentExecutor
    }

def is_inventory_related(message: str) -> bool:
    """
    Check if the message is related to inventory/stock queries.
    More comprehensive keyword detection.
    """
    inventory_keywords = [
        'stock', 'inventory', 'sku', 'product', 'item', 'available', 
        'units', 'left', 'have', 'shoes', 'shirt', 'pants', 'clothing',
        'red', 'blue', 'green', 'black', 'white', 'running', 'sports',
        'how many', 'check', 'do we have', 'in stock', 'quantity'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in inventory_keywords)

# "assistant" node: calls the AgentExecutor on the last user message
def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        # Extract the user's latest message content
        user_message = state["messages"][-1].content
        
        # Check if this is an inventory-related question
        if not is_inventory_related(user_message):
            response = "Hello! I'm an inventory assistant. I can help you check stock levels for products. You can ask me about stock by product name or SKU. How can I help you today?"
            return {
                "messages": [AIMessage(content=response)],
                "intermediate_steps": []
            }

        # For inventory-related questions, use the AgentExecutor
        result = agent_executor.invoke({
            "input": user_message
        })

        # The result["output"] is typically a string
        content = result["output"]
        
        # Handle case where content might be a dict
        if isinstance(content, dict):
            if "output" in content:
                content = content["output"]
            elif "Final Answer" in content:
                content = content["Final Answer"]
            else:
                content = str(content)

        # Wrap as AIMessage and return empty intermediate_steps to end the loop
        return {
            "messages": [AIMessage(content=content)],
            "intermediate_steps": []  # Always empty to end the loop
        }
    except Exception as e:
        error_msg = f"I apologize, but I encountered an error: {str(e)}. Please try again or ask me about product inventory."
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": []
        }

# Build the LangGraph StateGraph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)

# Simple flow: START -> assistant -> END
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

# Compile the graph
inventory_assistant = builder.compile()

# Allow running this file standalone for a quick test
if __name__ == "__main__":
    from langchain_core.messages import SystemMessage, HumanMessage

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