import mlflow
import mlflow.sklearn  # For general sklearn-style logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import joblib
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error

# --- Define ARIMA parameters ---
ARIMA_ORDER = (1, 1, 1)

# Start MLflow experiment run
mlflow.set_experiment("Netflix Stock Forecasting")
with mlflow.start_run(run_name="ARIMA_111"):

    # --- Load Dataset ---
    csv_path = "data/nflx_2014_2023.csv"
    data = pd.read_csv(csv_path, parse_dates=["date"], dayfirst=False, index_col="date")
    data.sort_index(inplace=True)
    data["close"] = data["close"].replace(',', '', regex=True)
    data["close"] = pd.to_numeric(data["close"], errors='coerce')
    data["close"].replace([np.inf, -np.inf], np.nan, inplace=True)
    data.dropna(subset=["close"], inplace=True)

    # Log dataset
    dataset_artifact_path = "artifacts/"
    os.makedirs(dataset_artifact_path, exist_ok=True)
    cleaned_csv = os.path.join(dataset_artifact_path, "cleaned_data.csv")
    data.to_csv(cleaned_csv)
    mlflow.log_artifact(cleaned_csv)

    # --- Stationarity Test ---
    result_original = adfuller(data["close"])
    data['Close_Diff'] = data['close'].diff()
    result_diff = adfuller(data['Close_Diff'].dropna())

    # --- Train-Test Split ---
    train_size = int(len(data) * 0.8)
    train, test = data.iloc[:train_size], data.iloc[train_size:]

    # --- Train ARIMA Model ---
    model = ARIMA(train["close"], order=ARIMA_ORDER)
    model_fit = model.fit()

    # --- Forecast ---
    forecast = model_fit.forecast(steps=len(test))
    forecast = forecast[:len(test)]
    test_close = test["close"][:len(forecast)]

    # --- Evaluation ---
    rmse = np.sqrt(mean_squared_error(test_close, forecast))

    # --- Log Parameters and Metrics ---
    mlflow.log_param("arima_order", ARIMA_ORDER)
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("aic", model_fit.aic)
    mlflow.log_metric("bic", model_fit.bic)
    mlflow.log_metric("ADF_pvalue_original", result_original[1])
    mlflow.log_metric("ADF_pvalue_differenced", result_diff[1])

    # --- Save Forecast Plot ---
    plt.figure(figsize=(14, 7))
    plt.plot(train.index, train["close"], label='Train', color='#203147')
    plt.plot(test.index, test["close"], label='Test', color='#01ef63')
    plt.plot(test.index, forecast, label='Forecast', color='orange')
    plt.title('Close Price Forecast')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.legend()
    forecast_plot = os.path.join(dataset_artifact_path, "forecast_plot.png")
    plt.savefig(forecast_plot)
    mlflow.log_artifact(forecast_plot)

    # --- Save ARIMA Model ---
    model_file = os.path.join(dataset_artifact_path, "arima_model.pkl")
    model_fit.save(model_file)
    mlflow.log_artifact(model_file)

    # --- Log Source Code File ---
    try:
        if hasattr(sys, 'argv') and sys.argv[0]:
            source_file = sys.argv[0]
            if os.path.exists(source_file):
                mlflow.log_artifact(source_file)
    except Exception as e:
        print(f"Could not log source file: {e}")

    # --- Create & Log Requirements.txt ---
    requirements_file = os.path.join(dataset_artifact_path, "requirements.txt")
    with open(requirements_file, "w") as f:
        f.write("mlflow\npandas\nnumpy\nmatplotlib\nscikit-learn\nstatsmodels\njoblib\n")
    mlflow.log_artifact(requirements_file)

print("MLflow run logged successfully.")
