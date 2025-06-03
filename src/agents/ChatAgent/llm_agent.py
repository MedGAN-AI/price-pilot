# File: src/agents/ChatAgent/llm_agent.py

import os
from typing import Any, Dict, TypedDict, Annotated, List

# Load environment variables (e.g., GOOGLE_API_KEY)
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
from langgraph.prebuilt import ToolNode, tools_condition

# Import our two Tool objects (relative import since we're inside ChatAgent/)
from .tools.order_tool import order_tool
from .tools.recommend_tool import recommend_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Must be set in your .env

# Instantiate the Google generative AI LLM (Gemini)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    api_key=GOOGLE_API_KEY
)

# Collect all tools (order_tool, recommend_tool) plus a “Final Answer” tool
tools = [
    order_tool,
    recommend_tool,
    Tool(
        name="Final Answer",
        func=lambda x: x,  
        description="Use this tool to output your final answer to the user."
    )
]

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

# Create the structured chat agent
agent = create_structured_chat_agent(llm, tools, prompt)

# Wrap it in an AgentExecutor to handle intermediate steps
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10
)

# Define the shared state type for LangGraph
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List

# Helper to initialize a fresh state
def initialize_state() -> AgentState:
    return {
        "messages": [],
        "intermediate_steps": []
    }

# “assistant” node: calls the AgentExecutor on the last user message
def assistant(state: AgentState) -> Dict[str, Any]:
    # Extract the user’s latest message content
    user_message = state["messages"][-1].content
    chat_history = state["messages"][:-1]

    # Invoke the AgentExecutor
    result = agent_executor.invoke({
        "input": user_message,
        "chat_history": chat_history
    })

    # Wrap the LLM’s output as an AIMessage and carry forward any intermediate steps
    return {
        "messages": [AIMessage(content=result["output"])],
        "intermediate_steps": result.get("intermediate_steps", [])
    }

# “tools” node: placeholder (AgentExecutor already ran the tool), just return state
def tool_node(state: AgentState) -> Dict[str, Any]:
    return state

# Build the LangGraph StateGraph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_node("tools", tool_node)

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
shopping_assistant = builder.compile()

# Allow running this file standalone for a quick test
if __name__ == "__main__":
    # Test 1: run AgentExecutor directly
    test_result = agent_executor.invoke({
        "input": "What is the price of red Christmas decorations?"
    })
    print("AgentExecutor output:\n", test_result["output"])

    # Test 2: run via LangGraph
    initial_state = initialize_state()
    # Seed with a SystemMessage + HumanMessage
    from langchain_core.messages import SystemMessage, HumanMessage
    initial_state["messages"] = [
        SystemMessage(content="You are a helpful shopping assistant for a retail company."),
        HumanMessage(content="What is the price of red Christmas decorations?")
    ]
    initial_state["intermediate_steps"] = []
    response_state = shopping_assistant.invoke(initial_state)
    print("\nLangGraph response:\n", response_state["messages"][-1].content)
