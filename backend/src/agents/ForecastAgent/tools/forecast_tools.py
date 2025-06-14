# forecast_tools.py
import os
import pandas as pd
from typing import Optional
from langchain_core.tools import tool

try:
    import joblib
except ImportError:
    raise ImportError("Please install joblib: pip install joblib")

# Define the absolute path to the model file using os.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "..", "models", "arima_model.pkl")

# Load the ARIMA model
try:
    arima_model = joblib.load(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Failed to load ARIMA model from {MODEL_PATH}: {e}")

@tool
def forecast_with_arima_tool(periods: Optional[int] = 7) -> str:
    """
    Generate a forecast for the next `periods` days using the ARIMA model.

    Args:
        periods (int): Number of future periods to forecast. Default is 7.

    Returns:
        str: Forecast summary in plain text.
    """
    try:
        forecast_result = arima_model.forecast(steps=periods)
        forecast_df = pd.DataFrame({"Forecast": forecast_result})
        return forecast_df.to_string()
    except Exception as e:
        return f"Error during forecasting: {str(e)}"
