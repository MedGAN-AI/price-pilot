from src.agents.OrderAgent.agent import order_agent_graph

def build_order_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for InventoryAgent.
    """
    return order_agent_graph
