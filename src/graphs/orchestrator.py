"""
Enhanced Production Orchestrator for Price Pilot
Multi-agent coordination with confidence scoring and context management
"""
import os
from typing import Any, Dict, TypedDict, Annotated, List
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

# Import each agent's compiled StateGraph
from src.agents.ChatAgent.agent import shopping_assistant
from src.agents.InventoryAgent.agent import inventory_assistant
from src.agents.RecommendAgent.agent import recommend_assistant
from src.agents.ForecastAgent.agent import forecast_assistant
from src.agents.LogisticsAgent.agent import logistics_assistant
from src.agents.OrderAgent.agent import order_agent_graph

def detect_intent(text: str) -> Dict[str, Any]:
    """
    Enhanced intent detection with confidence scoring
    Returns both intent and confidence level
    """
    intent_keywords = {
        "inventory": ["stock", "inventory", "available", "units", "in stock", "quantity", "how many"],
        "recommend": ["recommend", "suggest", "find", "looking for", "need", "want", "show me", "similar"],
        "order": ["order", "buy", "purchase", "place order", "checkout", "cart", "add to cart", "SHOES-", "TSHIRT-", "HAT-", "SOCKS-"],
        "logistics": ["track", "shipping", "delivery", "shipment", "where is", "when will", "arrive"],
        "forecast": ["forecast", "predict", "future", "trend", "projection", "demand", "sales"]
    }
    
    lower_text = text.lower()
    scores = {}
    
    # Calculate scores for each intent
    for intent, keywords in intent_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in lower_text:
                score += 1
        
        if score > 0:
            scores[intent] = score / len(keywords)  # Normalize by keyword count
    
    if scores:
        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] * 2, 1.0)  # Scale confidence
        return {"intent": best_intent, "confidence": confidence}
    else:
        return {"intent": "chat", "confidence": 0.5}

# Enhanced state with better context management
class OrchestrationState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    intermediate_steps: List[Any]
    intent: str
    confidence: float
    user_context: Dict[str, Any]
    conversation_history: List[Dict]

def initialize_state() -> OrchestrationState:
    return {
        "messages": [], 
        "intermediate_steps": [], 
        "intent": "",
        "confidence": 0.0,
        "user_context": {},
        "conversation_history": []
    }
    return {"messages": [], "intermediate_steps": [], "intent": ""}

def intent_router(state: OrchestrationState) -> OrchestrationState:
    """
    Enhanced intent router with confidence and context tracking
    """
    last_msg = state["messages"][-1].content
    intent_result = detect_intent(last_msg)
    
    # Retrieve existing context
    user_context = state.get("user_context", {})
    
    # Look for email addresses in the message
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, last_msg)
    if email_matches:
        user_context["email"] = email_matches[0]
    
    # Look for product SKUs in the message
    sku_pattern = r'([A-Z]+-[A-Z]+-\d{3})'
    sku_matches = re.findall(sku_pattern, last_msg)
    if sku_matches:
        user_context["product_sku"] = sku_matches[0]
        # If SKU is found, this is likely an order intent
        intent_result["intent"] = "order"
        intent_result["confidence"] = max(intent_result["confidence"], 0.7)
    
    # Look for quantities in the message
    quantity_pattern = r'\b(\d+)\b'
    quantity_matches = re.findall(quantity_pattern, last_msg)
    if quantity_matches and "product_sku" in user_context:
        user_context["quantity"] = quantity_matches[0]
    
    # Update user context with current query and session info
    user_context.update({
        "current_query": last_msg,
        "timestamp": datetime.now().isoformat(),
        "session_id": user_context.get("session_id", "session_" + str(hash(last_msg))[:8]),
        "query_length": len(last_msg),
    })
    
    # Update conversation history
    conversation_history = state.get("conversation_history", [])
    conversation_history.append({
        "query": last_msg,
        "intent": intent_result["intent"],
        "confidence": intent_result["confidence"],
        "timestamp": user_context["timestamp"]
    })
    
    return {
        "messages": state["messages"],
        "intermediate_steps": [],
        "intent": intent_result["intent"],
        "confidence": intent_result["confidence"],
        "user_context": user_context,
        "conversation_history": conversation_history[-10:]  # Keep last 10
    }

def dispatch(state: OrchestrationState) -> OrchestrationState:
    """
    Enhanced dispatch - Routes requests to appropriate specialized agents based on detected intent
    """
    try:
        # Select agent based on intent
        intent = state.get("intent", "chat")
        confidence = state.get("confidence", 0.5)
        
        # Map intents to agent graphs
        agent_map = {
            "chat": shopping_assistant,
            "inventory": inventory_assistant,
            "recommend": recommend_assistant,
            "forecast": forecast_assistant,
            "logistics": logistics_assistant,
            "order": order_agent_graph
        }
        
        # Select appropriate agent based on intent
        subgraph = agent_map.get(intent, shopping_assistant)
        agent_name = intent.capitalize() + "Agent"
        
        # Log which agent is handling the request (for debugging)
        print(f"DEBUG: Routing to {agent_name} with confidence {confidence}")
        
        # Prepare sub-state with full context
        sub_state = {
            "messages": state["messages"],
            "intermediate_steps": [],
            # Pass intent and other context to the agent
            "intent": intent,
            "confidence": confidence,
            "user_context": state.get("user_context", {})
        }
        
        # Invoke selected agent
        result = subgraph.invoke(sub_state)
        
        # Return enhanced state with preserved context
        return {
            "messages": result["messages"],
            "intermediate_steps": [],
            "intent": intent,
            "confidence": confidence,
            "user_context": state["user_context"],
            "conversation_history": state["conversation_history"]
        }
        
    except Exception as e:
        error_response = f"❌ I encountered an error while processing your request: {str(e)}\n\nPlease try rephrasing your question."
        
        return {
            "messages": [AIMessage(content=error_response)],
            "intermediate_steps": [],
            "intent": "error",
            "confidence": 0.0,
            "user_context": state.get("user_context", {}),
            "conversation_history": state.get("conversation_history", [])
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
