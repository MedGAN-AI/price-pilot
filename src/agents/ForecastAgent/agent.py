import os
from typing import Annotated, List
import joblib

from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

# Load the pre-trained ARIMA model
BASE_DIR = os.path.dirname(__file__)
model_path = os.path.join(BASE_DIR, "models", "arima_model.pkl")
model = joblib.load(model_path)

@tool
def forecast_tool(
    sku: Annotated[str, "Stock Keeping Unit identifier"],
    steps: Annotated[int, "Number of future time steps to forecast"],
) -> List[float]:
    """Forecast demand for a given SKU using the pre-trained ARIMA model"""
    try:
        forecast = model.predict(n_periods=steps)
    except TypeError:
        try:
            forecast = model.forecast(steps)
        except Exception:
            forecast = model.predict(steps)
    forecast_values = list(map(float, forecast))
    return forecast_values

# Load the system prompt
prompt_path = os.path.join(BASE_DIR, "prompts", "forecast_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_message = f.read()

prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    temperature=0,
    google_api_key="AIzaSyDijydit4qNeEsYEVjgp_fJyLCs6kewD-A"  # or set as env var: GOOGLE_API_KEY
)
tools = [forecast_tool]

agent = create_tool_calling_agent(llm, tools, prompt)
forecast_agent = AgentExecutor(agent=agent, tools=tools)
