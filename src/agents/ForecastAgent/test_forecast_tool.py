import json
from typing import List

# Assuming forecast_tool is defined as:
def forecast_tool(input_json: str) -> List[float]:
    import joblib
    import os

    BASE_DIR = os.path.dirname(__file__)
    model_path = os.path.join(BASE_DIR, "models", "arima_model.pkl")
    model = joblib.load(model_path)

    params = json.loads(input_json)
    sku = params.get("sku")
    steps = params.get("steps")

    try:
        forecast = model.predict(n_periods=steps)
    except TypeError:
        try:
            forecast = model.forecast(steps)
        except Exception:
            forecast = model.predict(steps)
    return list(map(float, forecast))

if __name__ == "__main__":
    # Example input
    test_input = json.dumps({
        "sku": "A123",   # SKU is unused in current model but included for interface consistency
        "steps": 5       # Number of future steps to forecast
    })

    forecast = forecast_tool(test_input)
    print(f"Forecast for SKU 'A123' for next 5 steps: {forecast}")
