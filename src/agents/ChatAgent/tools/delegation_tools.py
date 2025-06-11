"""
ChatAgent Delegation Tools
Tools for delegating requests to specialized agents and managing conversation context
"""
import json
from typing import Dict, Any, List
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage

# Import all specialized agents
from src.agents.OrderAgent.agent import order_agent_graph, initialize_state as order_init_state
from src.agents.InventoryAgent.agent import inventory_assistant, initialize_state as inventory_init_state
from src.agents.RecommendAgent.agent import recommend_assistant, initialize_state as recommend_init_state
from src.agents.LogisticsAgent.agent import logistics_assistant, initialize_state as logistics_init_state
from src.agents.ForecastAgent.agent import forecast_assistant, initialize_state as forecast_init_state

def delegate_to_order_agent(request: str) -> str:
    """
    Delegate order-related requests to OrderAgent.
    Handles order creation, status checking, updates, cancellation.
    """
    try:
        # Initialize OrderAgent state
        state = order_init_state()
        state["messages"] = [HumanMessage(content=request)]
        
        # Invoke OrderAgent
        result = order_agent_graph.invoke(state)
        
        # Extract and clean response
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            # Return clean response without agent prefix to prevent verbosity
            return response
        else:
            return "I wasn't able to process your order request. Please provide more details or try again."
            
    except Exception as e:
        return f"I encountered an issue processing your order: {str(e)}. Please try again."

def delegate_to_inventory_agent(request: str) -> str:
    """
    Delegate inventory-related requests to InventoryAgent.
    Handles stock checks, availability queries.
    """
    try:
        # Initialize InventoryAgent state
        state = inventory_init_state()
        state["messages"] = [HumanMessage(content=request)]
        
        # Invoke InventoryAgent
        result = inventory_assistant.invoke(state)
        
        # Extract and clean response
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            return response
        else:
            return "I wasn't able to check inventory. Please try again with more specific details."
            
    except Exception as e:
        return f"I encountered an issue checking inventory: {str(e)}. Please try again."

def delegate_to_recommend_agent(request: str) -> str:
    """
    Delegate recommendation requests to RecommendAgent.
    Handles product discovery, recommendations, search.
    """
    try:
        # Initialize RecommendAgent state
        state = recommend_init_state()
        state["messages"] = [HumanMessage(content=request)]
        
        # Invoke RecommendAgent
        result = recommend_assistant.invoke(state)
        
        # Extract and clean response
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            return response
        else:
            return "I wasn't able to find recommendations. Please try with different search terms."
            
    except Exception as e:
        return f"I encountered an issue finding recommendations: {str(e)}. Please try again."

def delegate_to_logistics_agent(request: str) -> str:
    """
    Delegate logistics requests to LogisticsAgent.
    Handles tracking, shipping, delivery management.
    """
    try:
        # Initialize LogisticsAgent state
        state = logistics_init_state()
        state["messages"] = [HumanMessage(content=request)]
        
        # Invoke LogisticsAgent
        result = logistics_assistant.invoke(state)
        
        # Extract response
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            return f"🚚 Logistics Agent: {response}"
        else:
            return "❌ LogisticsAgent didn't provide a response. Please try again."
            
    except Exception as e:
        return f"❌ I encountered an issue while handling your logistics request: {str(e)}. Please try again."

def delegate_to_forecast_agent(request: str) -> str:
    """
    Delegate forecasting requests to ForecastAgent.
    Handles demand prediction, sales forecasting, trend analysis.
    """
    try:
        # Initialize ForecastAgent state
        state = forecast_init_state()
        state["messages"] = [HumanMessage(content=request)]
        
        # Invoke ForecastAgent
        result = forecast_assistant.invoke(state)
        
        # Extract response
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            return f"📈 Forecast Agent: {response}"
        else:
            return "❌ ForecastAgent didn't provide a response. Please try again."
            
    except Exception as e:
        return f"❌ I encountered an issue while generating forecasts: {str(e)}. Please try again."

# Create LangChain Tools
order_delegation_tool = Tool(
    name="DelegateToOrderAgent",
    func=delegate_to_order_agent,
    description="Delegate order creation, status checking, updates, or cancellation to the specialized OrderAgent."
)

inventory_delegation_tool = Tool(
    name="DelegateToInventoryAgent", 
    func=delegate_to_inventory_agent,
    description="Delegate stock checks, availability queries, or inventory management to the specialized InventoryAgent."
)

recommend_delegation_tool = Tool(
    name="DelegateToRecommendAgent",
    func=delegate_to_recommend_agent, 
    description="Delegate product recommendations, search, or discovery to the specialized RecommendAgent."
)

logistics_delegation_tool = Tool(
    name="DelegateToLogisticsAgent",
    func=delegate_to_logistics_agent,
    description="Delegate shipping, tracking, delivery, or logistics queries to the specialized LogisticsAgent."
)

forecast_delegation_tool = Tool(
    name="DelegateToForecastAgent",
    func=delegate_to_forecast_agent,
    description="Delegate demand forecasting, sales prediction, or trend analysis to the specialized ForecastAgent."
)

# Export all delegation tools
delegation_tools = [
    order_delegation_tool,
    inventory_delegation_tool,
    recommend_delegation_tool,
    logistics_delegation_tool,
    forecast_delegation_tool
]
