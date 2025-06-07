import os
from typing import Any, Dict, TypedDict, Annotated, List

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

# Import each agent’s compiled StateGraph
from src.agents.ChatAgent.llm_agent import shopping_assistant
from src.agents.InventoryAgent.agent import inventory_assistant
from src.agents.RecommendAgent.agent import recommend_assistant
from src.agents.ForecastAgent.agent import forecast_assistant
from src.agents.OrderAgent.agent import order_assistant
from src.agents.LogisticsAgent.agent import logistics_assistant

def detect_intent(text: str) -> str:
    """
    Rudimentary intent detection by keyword matching.
    Returns one of: "inventory", "recommend", "forecast", "order", "logistics", else "chat".
    """
    lower = text.lower()
    # Inventory keywords
    if any(k in lower for k in ["stock", "inventory", "sku", "available", "units", "in stock"]):
        return "inventory"
    # Recommend keywords
    if any(k in lower for k in ["recommend", "suggest", "similar", "like"]):
        return "recommend"
    # Forecast keywords
    if any(k in lower for k in ["forecast", "predict", "projection", "trend"]):
        return "forecast"
    # Order keywords
    if any(k in lower for k in ["order", "purchase", "buy", "place order"]):
        return "order"
    # Logistics / shipping keywords
    if any(k in lower for k in ["ship", "delivery", "tracking", "arrive", "status"]):
        return "logistics"
    # Default to chat
    return "chat"

# Define the shared orchestration state
class OrchestrationState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    intermediate_steps: List[Any]
    intent: str

def initialize_state() -> OrchestrationState:
    return {"messages": [], "intermediate_steps": [], "intent": ""}

def intent_router(state: OrchestrationState) -> OrchestrationState:
    """
    Reads the last HumanMessage, detects intent, and stores it in state['intent'].
    """
    last_msg = state["messages"][-1].content
    intent = detect_intent(last_msg)
    # Reset intermediate_steps for the next subgraph
    return {
        "messages": state["messages"],
        "intermediate_steps": [],
        "intent": intent
    }

def dispatch(state: OrchestrationState) -> OrchestrationState:
    """
    Based on state['intent'], invokes the corresponding agent subgraph.
    """
    intent = state["intent"]
    # Choose the appropriate StateGraph
    if intent == "inventory":
        subgraph = inventory_assistant
    elif intent == "recommend":
        subgraph = recommend_assistant
    elif intent == "forecast":
        subgraph = forecast_assistant
    elif intent == "order":
        subgraph = order_assistant
    elif intent == "logistics":
        subgraph = logistics_assistant
    else:
        subgraph = shopping_assistant

    # Prepare sub-state (only messages & intermediate_steps)
    sub_state = {
        "messages": state["messages"],
        "intermediate_steps": []
    }
    # Invoke the chosen agent
    result = subgraph.invoke(sub_state)

    # Return combined state, preserving intent if needed
    return {
        "messages": result["messages"],
        "intermediate_steps": [],
        "intent": intent
    }

# Build the orchestration graph
builder = StateGraph(OrchestrationState)
builder.add_node("intent_router", intent_router)
builder.add_node("dispatch", dispatch)

builder.add_edge(START, "intent_router")
builder.add_edge("intent_router", "dispatch")
builder.add_edge("dispatch", END)

# Compile once
orchestrator = builder.compile()
