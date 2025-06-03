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
from .tools.order_tool import order_tool, place_order_tool
from .tools.recommend_tool import recommend_tool

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Must be set in your .env

# Instantiate the Google generative AI LLM (Gemini)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    api_key=GOOGLE_API_KEY
)

# Collect all tools (order_tool, recommend_tool) plus a "Final Answer" tool
tools = [
    order_tool,
    place_order_tool,
    recommend_tool,
    Tool(
        name="Final Answer",
        func=lambda x: x,  
        description="Use this tool to output your final answer to the user."
    )
]

# Fixed system prompt - removed problematic variables and improved format
system_prompt = """You are a helpful shopping assistant for a retail company.
You help customers find products, compare prices, and answer questions.

You have access to the following tools:
{tools}

Use a json blob to specify a tool by providing an action key (tool name) and an action_input key (tool input).

Valid "action" values: "Final Answer" or {tool_names}

Provide only ONE action per JSON blob, as shown:

```json
{{
  "action": "tool_name",
  "action_input": "tool input"
}}
```

Follow this format:
Question: input question to answer
Thought: consider previous and subsequent steps
Action:
```json
{{
  "action": "tool_name", 
  "action_input": "input"
}}
```
Observation: action result
... (repeat Thought/Action/Observation N times)
Thought: I know what to respond
Action:
```json
{{
  "action": "Final Answer",
  "action_input": "final response"
}}
```

Begin! Reminder to ALWAYS respond with a valid json blob of a single action. Use tools if necessary. Respond directly if appropriate."""

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
        "messages": [],
        "intermediate_steps": []
    }

# "assistant" node: calls the AgentExecutor on the last user message
def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        # Extract the user's latest message content
        user_message = state["messages"][-1].content
        chat_history = state["messages"][:-1]

        # Invoke the AgentExecutor
        result = agent_executor.invoke({
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
        error_msg = f"I apologize, but I encountered an error: {str(e)}. Please try again or rephrase your request."
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": []
        }

# "tools" node: placeholder (AgentExecutor already ran the tool), just return state
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
    print("Testing AgentExecutor...")
    try:
        test_result = agent_executor.invoke({
            "input": "What is the price of red Christmas decorations?"
        })
        print("AgentExecutor output:\n", test_result["output"])
    except Exception as e:
        print(f"AgentExecutor test failed: {e}")

    # Test 2: run via LangGraph
    print("\nTesting LangGraph...")
    try:
        initial_state = initialize_state()
        # Seed with a SystemMessage + HumanMessage
        initial_state["messages"] = [
            SystemMessage(content="You are a helpful shopping assistant for a retail company."),
            HumanMessage(content="What is the price of red Christmas decorations?")
        ]
        initial_state["intermediate_steps"] = []
        response_state = shopping_assistant.invoke(initial_state)
        print("LangGraph response:\n", response_state["messages"][-1].content)
    except Exception as e:
        print(f"LangGraph test failed: {e}")