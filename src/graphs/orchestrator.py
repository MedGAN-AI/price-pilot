import yaml
from typing import Any, Dict, TypedDict, Annotated, List

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage

# Import subgraphs
from src.agents.ChatAgent.llm_agent import shopping_assistant
from src.agents.InventoryAgent.agent import inventory_assistant
from src.agents.RecommendAgent.agent import recommend_assistant

# Simple intent keyword mapping
def detect_intent(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["stock", "inventory", "sku", "available"]):
        return "inventory"
    if any(k in lower for k in ["recommend", "suggest", "like", "similar"]):
        return "recommend"
    return "chat"

# State and typedict
class OrchestrationState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    intermediate_steps: List
    intent: str  # Remove the invalid annotation

# Initialize state
def initialize_state() -> OrchestrationState:
    return {"messages": [], "intermediate_steps": [], "intent": ""}

# Node: intent detection
def intent_router(state: OrchestrationState) -> Dict[str, Any]:
    last = state["messages"][-1].content
    intent = detect_intent(last)
    return {"messages": state["messages"], "intermediate_steps": [], "intent": intent}

# Node: dispatch
def dispatch(state: OrchestrationState) -> Dict[str, Any]:
    intent = state["intent"]
    # pick subgraph
    if intent == "inventory":
        sub = inventory_assistant
    elif intent == "recommend":
        sub = recommend_assistant
    else:
        sub = shopping_assistant
    # invoke subgraph
    sub_state = {"messages": state["messages"], "intermediate_steps": []}
    res = sub.invoke(sub_state)
    return {"messages": res["messages"], "intermediate_steps": [], "intent": intent}

# Build orchestration graph
builder = StateGraph(OrchestrationState)
builder.add_node("intent_router", intent_router)
builder.add_node("dispatch", dispatch)

builder.add_edge(START, "intent_router")
builder.add_edge("intent_router", "dispatch")
builder.add_edge("dispatch", END)

orchestrator = builder.compile()
