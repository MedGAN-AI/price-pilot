from src.agents.ForecastAgent.agent import forecast_assistant

def build_forecast_graph():
    """
    Returns the pre-compiled LangGraph StateGraph for ForecastAgent.
    """
    return forecast_assistant

