import os
import yaml
import pickle
from typing import Any, Dict, TypedDict, Annotated, List

from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import the forecasting tool
from tools.forecast_tools import forecast_with_arima_tool

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

llm_provider    = config.get("llm", {}).get("provider", "google-genai")
llm_model       = config.get("llm", {}).get("model", "gemini-1.5-flash")
llm_temperature = config.get("llm", {}).get("temperature", 0.0)

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

# Tools list
tools = [
    forecast_with_arima_tool,
]

# Create a simple prompt template that works better with Gemini
system_message = """You are a ForecastAgent, an AI assistant specialized in generating forecasts and predictions based on data analysis.

Your role is to help users predict future sales, demand, trends, and other time-series data using appropriate forecasting methods.

When a user asks for a forecast:
1. Analyze their request to understand what they want to forecast
2. Use the appropriate forecasting tool to generate predictions
3. Provide clear, actionable insights based on the results

Always respond in a helpful and professional manner."""

# Use ChatPromptTemplate instead of PromptTemplate for better Gemini compatibility
prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

# Use create_tool_calling_agent instead of create_react_agent
agent = create_tool_calling_agent(llm, tools, prompt)

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
        "messages": [],
        "intermediate_steps": []
    }

def is_forecast_related(message: str) -> bool:
    forecast_keywords = ["forecast", "predict", "next", "future", "demand", "sales", "trend"]
    lower_msg = message.lower()
    return any(kw in lower_msg for kw in forecast_keywords)

def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        user_message = state["messages"][-1].content

        if not is_forecast_related(user_message):
            response = (
                "Hello! I'm a ForecastAgent. I can help you predict future sales or trends. "
                "Ask something like: 'What are the expected sales for next month?'")
            return {
                "messages": [AIMessage(content=response)],
                "intermediate_steps": []
            }

        result = agent_executor.invoke({"input": user_message})
        content = result["output"]
        if isinstance(content, dict):
            content = content.get("output") or content.get("tool_input") or str(content)

        return {
            "messages": [AIMessage(content=content)],
            "intermediate_steps": []
        }

    except Exception as e:
        error_msg = f"Forecast error: {str(e)}. Please try again with a clear forecasting question."
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": []
        }

builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
forecast_agent = builder.compile()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    print("=== ForecastAgent AgentExecutor Test ===")
    try:
        test_result = agent_executor.invoke({
            "input": "Can you forecast next month's sales for product X?"
        })
        print("AgentExecutor output:\n", test_result["output"])
    except Exception as e:
        print(f"AgentExecutor test failed: {e}")

    print("\n=== ForecastAgent LangGraph Test ===")
    try:
        state = initialize_state()
        state["messages"] = [
            HumanMessage(content="What is the forecast for next week?")
        ]
        state["intermediate_steps"] = []
        response_state = forecast_agent.invoke(state)
        print("LangGraph response:\n", response_state["messages"][-1].content)
    except Exception as e:
        print(f"LangGraph test failed: {e}")