# agent implementation
import os
import base64
from typing import Any, Dict, List, Optional, Sequence, TypedDict, Union, Annotated

# Environment setup
from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import UnstructuredExcelLoader

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# Project-specific imports
from tools import (
    scrape_shopify_store, 
    scrape_woocommerce_store, 
    scrape_wix_store, 
    scrape_squarespace_store,
    predict_sales, 
    segment_customers, 
    forecast_sales
)
from retriever import retrieval_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.0)

# Collect all tools from tools.py and add the retrieval_tool
tools = [retrieval_tool, scrape_shopify_store, scrape_woocommerce_store, scrape_wix_store,
         scrape_squarespace_store, predict_sales, segment_customers, forecast_sales]

# Create the prompt with system message following the proper format
system = '''Respond to the human as helpfully and accurately as possible. You are a helpful shopping assistant for a retail company.
You help customers find products, compare prices, and answer questions.

You have access to the following tools:

{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per $JSON_BLOB, as shown:

Follow this format:

Question: input question to answer
Thought: consider previous and subsequent steps
Action:

Observation: action result
... (repeat Thought/Action/Observation N times)
Thought: I know what to respond
Action:


Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation'''

human = '''{input}

{agent_scratchpad}

(reminder to respond in a JSON blob no matter what)'''

# Setup the agent with tools
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", human),
    ]
)

# Create the agent with the correct prompt
agent = create_structured_chat_agent(llm, tools, prompt)

# Create agent executor which handles intermediate steps
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,  # Important for handling formatting issues
    max_iterations=10  # Add a limit to prevent infinite loops
)

# Define state with messages and intermediate steps
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intermediate_steps: list

# Initialize empty intermediate steps
def initialize_state() -> AgentState:
    return {
        "messages": [],
        "intermediate_steps": []
    }


# Assistant node that uses AgentExecutor correctly
def assistant(state: AgentState) -> Dict[str, Any]:
    """Process user input with agent and return response"""
    # Get the user's message
    user_message = state["messages"][-1].content
    chat_history = state["messages"][:-1]
    
    # Invoke the agent executor with the correct input structure
    result = agent_executor.invoke({
        "input": user_message,
        "chat_history": chat_history
        # Remove intermediate_steps from here as it's causing the conflict
    })
    
    # Create and return AI message with result
    return {
        "messages": [AIMessage(content=result["output"])],
        "intermediate_steps": result.get("intermediate_steps", [])
    }

# ToolNode for executing tools and storing results
def tool_node(state: AgentState) -> Dict[str, Any]:
    """Process tool execution and store results"""
    # This is handled by the AgentExecutor, but we keep this for LangGraph structure
    return state

## The graph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)

# Define edges
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    lambda state: len(state["intermediate_steps"]) > 0,  # Check if tools were used
    {
        True: "tools",
        False: END
    }
)
builder.add_edge("tools", "assistant")

# Compile the graph
shopping_assistant = builder.compile()

# Test the agent (standalone without graph, for debugging)
if __name__ == "__main__":
    # Simple test with agent executor directly
    result = agent_executor.invoke({
        "input": "What is the price of red Christmas decorations?",
        # Remove intermediate_steps from here too
    })
    print(result["output"])
    
    # Test with graph
    response = shopping_assistant.invoke(
        {
            "messages": [
                SystemMessage(
                    content="You are a helpful shopping assistant for a retail company."
                ),
                HumanMessage(content="What is the price of red Christmas decorations?"),
            ],
            "intermediate_steps": []  # This is OK as it's for the graph state initialization
        }
    )
    print("\nLangGraph response:")
    print(response["messages"][-1].content)


