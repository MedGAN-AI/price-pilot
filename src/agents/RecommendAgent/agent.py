import os
import sys
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

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

# Import our recommend tool
from tools.recommend_tool import recommend_tool


load_dotenv()

# config.yaml path
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# LLM config
llm_model       = config.get("llm", {}).get("model", "gemini-2.0-flash")
llm_temperature = config.get("llm", {}).get("temperature", 0.0)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY must be set to use google-genai")

llm = ChatGoogleGenerativeAI(
    model=llm_model,
    temperature=llm_temperature,
    api_key=GOOGLE_API_KEY
)

# Tools setup - remove the Final Answer tool as ReAct handles this automatically
tools = [recommend_tool]

# Load prompt
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "recommend_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Create proper ReAct prompt template
react_prompt = PromptTemplate.from_template(
    system_prompt + "\n\nQuestion: {input}\n{agent_scratchpad}"
)

# Create ReAct agent
agent = create_react_agent(
    llm=llm, 
    tools=tools, 
    prompt=react_prompt
)

# Create AgentExecutor
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True
)

# LangGraph state and assistant node
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List

def initialize_state() -> AgentState:
    return {"messages": [], "intermediate_steps": []}

def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        user_message = state["messages"][-1].content

        # Invoke the ReAct agent
        result = agent_executor.invoke({"input": user_message})

        content = result["output"]
        if isinstance(content, dict):
            content = content.get("output", content.get("tool_input", str(content)))

        return {
            "messages": [AIMessage(content=content)],
            "intermediate_steps": []
        }
    except Exception as e:
        err = f"Sorry, I encountered an error: {str(e)}"
        return {"messages": [AIMessage(content=err)], "intermediate_steps": []}

# Build and compile LangGraph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

recommend_assistant = builder.compile()

# Standalone test
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    print("=== RecommendAgent AgentExecutor Test ===")
    try:
        out = agent_executor.invoke({"input": "red running shoes"})
        print(out["output"])
    except Exception as e:
        print("AgentExecutor error:", e)

    print("\n=== RecommendAgent LangGraph Test ===")
    try:
        state = initialize_state()
        state["messages"] = [HumanMessage(content="I want something like SHOES-RED-001")]
        state["intermediate_steps"] = []
        resp = recommend_assistant.invoke(state)
        print(resp["messages"][-1].content)
    except Exception as e:
        print("LangGraph error:", e)