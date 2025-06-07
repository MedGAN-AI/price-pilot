from src.agents.LogisticsAgent.agent import logistics_assistant

def build_logistics_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for LogisticsAgent.
    """
    return logistics_assistant
