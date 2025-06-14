from src.agents.RecommendAgent.agent import recommend_assistant

def build_recommend_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for RecommendAgent.
    """
    return recommend_assistant
