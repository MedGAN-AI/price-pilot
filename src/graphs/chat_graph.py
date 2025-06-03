from src.agents.ChatAgent.llm_agent import shopping_assistant

def build_chat_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for ChatAgent.
    """
    return shopping_assistant
