"""
ForecastAgent - Demand forecasting and ML prediction using core framework
Handles ARIMA modeling, sales forecasting, and trend analysis
"""
import os
from typing import List

# Import core framework
from src.core import (
    build_agent,
    create_llm_from_config,
    AgentState,
    initialize_state,
    AgentType,
    standardize_agent_config,
    load_config,
    create_agent_error_handler
)

# Import forecast tools
from src.agents.ForecastAgent.tools.forecast_tools import forecast_with_arima_tool

# Load and standardize configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
raw_config = load_config(CONFIG_PATH)
config = standardize_agent_config(raw_config)

# Create LLM using core framework
llm = create_llm_from_config(config)

# Initialize error handler
error_handler = create_agent_error_handler("ForecastAgent")

# Setup tools
tools = [forecast_with_arima_tool]

# Load prompt template
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "forecast_prompt.txt")
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    system_prompt = f.read()

# Build the ForecastAgent using core framework
agent_config = config.get("agent", {})
specialized_config = config.get("specialized_config", {})

build_config = {
    "early_stopping_method": agent_config.get("early_stopping_method", "generate"),
    "max_execution_time": agent_config.get("max_execution_time", 60),
    "default_forecast_periods": specialized_config.get("default_forecast_periods", 7),
    "max_forecast_periods": specialized_config.get("max_forecast_periods", 30),
    "context_key": specialized_config.get("context_key", "forecast_context")
}

forecast_assistant = build_agent(
    llm=llm,
    tools=tools,
    prompt_template=system_prompt,
    max_iterations=agent_config.get("max_iterations", 10),
    agent_type=AgentType.TOOL_CALLING,  # ForecastAgent uses Tool Calling pattern
    agent_config=build_config
)

# Helper function for forecast validation
def is_forecast_related(message: str) -> bool:
    """Check if message is related to forecasting"""
    forecast_keywords = ["forecast", "predict", "next", "future", "demand", "sales", "trend", "arima"]
    lower_msg = message.lower()
    return any(kw in lower_msg for kw in forecast_keywords)

# Create wrapper class for easy testing and integration
class ForecastAgent:
    """Enhanced ForecastAgent using core framework"""

    def __init__(self):
        self.graph = forecast_assistant
        self.error_handler = error_handler
        self.config = config

    def process_query(self, query: str, context: dict = None) -> str:
        """Process a forecasting query"""
        try:
            # Initialize state with forecast context
            state = initialize_state()

            # Add context if provided
            if context:
                state["context"] = {"forecast_context": context}

            # Add user message
            from langchain_core.messages import HumanMessage
            state["messages"] = [HumanMessage(content=query)]

            # Check if query is forecast-related
            if not is_forecast_related(query):
                return ("Hello! I'm a ForecastAgent. I can help you predict future sales or trends. "
                       "Ask something like: 'What are the expected sales for next month?'")

            # Invoke agent
            result = self.graph.invoke(state)

            # Extract response
            if result.get("messages"):
                final_message = result["messages"][-1]
                if hasattr(final_message, "content"):
                    response = final_message.content
                elif isinstance(final_message, dict):
                    response = final_message.get("content", "No response")
                else:
                    response = str(final_message)

                return response

            return "No response generated"

        except Exception as e:
            return self.error_handler.handle_llm_error(e)

    def forecast_periods(self, periods: int = 7) -> str:
        """Quick forecast for specified periods"""
        return self.process_query(f"Generate a {periods}-day forecast")

    def analyze_trends(self, timeframe: str = "monthly") -> str:
        """Analyze trends for specified timeframe"""
        return self.process_query(f"Analyze {timeframe} trends and patterns")

    def get_status(self) -> dict:
        """Get agent status"""
        return {
            "agent_name": "ForecastAgent",
            "status": "active",
            "tools_count": len(tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

# Export the compiled graph and utilities for orchestrator
__all__ = [
    "forecast_assistant",
    "initialize_state",
    "AgentState",
    "config",
    "ForecastAgent",
    "is_forecast_related"
]

# Convenience function for direct invocation
def run_forecast_agent(message: str, context: dict = None) -> str:
    """Simple interface for running ForecastAgent"""
    agent = ForecastAgent()
    return agent.process_query(message, context)

# Test interface when run directly
if __name__ == "__main__":
    print("📈 ForecastAgent Test Interface - Core Framework Version")
    print("=" * 60)
    
    # Create agent instance
    forecast_agent = ForecastAgent()
    
    print("Available capabilities:")
    print("- ARIMA-based forecasting")
    print("- Demand prediction") 
    print("- Trend analysis")
    print("- ML model integration")
    print("\nTest queries:")
    print("- 'What are the sales forecast for next 7 days?'")
    print("- 'Predict demand for next month'")
    print("- 'Analyze trends in our sales data'")
    print("\nEnter 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye! 👋")
                break
            
            if user_input:
                response = forecast_agent.process_query(user_input)
                print(f"ForecastAgent: {response}\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}\n")