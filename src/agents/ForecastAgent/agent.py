import os
from typing import Annotated, List
import joblib
from langchain_core.prompts import MessagesPlaceholder
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
    return list(map(float, forecast))

# Load the system prompt
prompt_path = os.path.join(BASE_DIR, "prompts", "forecast_prompt.txt")
with open(prompt_path, "r", encoding="utf-8") as f:
    system_message = f.read()

# Construct prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", system_message),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
    ("system", "Available tools: {tool_names}"),
    ("system", "{tools}"),
])

# Initialize LLM and tools
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY", "AIzaSyDijydit4qNeEsYEVjgp_fJyLCs6kewD-A")
)

tools = [forecast_tool]

# Create agent and executor
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

forecast_agent = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors=True
)
