from src.agents.InventoryAgent.agent import inventory_assistant

def build_inventory_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for InventoryAgent.
    """
    return inventory_assistant
