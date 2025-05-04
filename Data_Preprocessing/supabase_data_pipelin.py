'''
Online Retail Data Pipeline - Supabase ETL Process

This script:
1. Extracts data from Supabase
2. Transforms/cleans it (like in eda_online_retail.ipynb)
3. Loads the cleaned data back to Supabase

.env required:
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_api_key
'''

import os
import pandas as pd
import datetime as dt
from dotenv import load_dotenv
from supabase import create_client, Client
import logging
import sys
import io

# ---------------------
# SETUP: Logging with UTF-8
# ---------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formatter
tfmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(fmt=tfmt)

# File handler (UTF-8)
file_handler = logging.FileHandler("pipeline.log", encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Console handler (UTF-8)
stream_handler = logging.StreamHandler()
# Wrap stdout to enforce UTF-8
stream_handler.stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# ---------------------
# Load environment and Supabase client
# ---------------------
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# ---------------------
# 1) Extract
# ---------------------
def extract_data_from_supabase(table_name: str = "data") -> pd.DataFrame:
    logger.info(f"Extracting data from {table_name}...")
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        logger.info(f"Successfully extracted {len(df)} rows from {table_name}")
        return df
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        raise

# ---------------------
# 2) Clean & RFM
# ---------------------
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    logger.info("Starting data cleaning process...")
    df = df.copy()

    # Drop missing Customer ID and duplicates
    df = df.dropna(subset=["Customer ID"])
    df = df.drop_duplicates()

    # Remove cancellations (Invoice starting with 'C')
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    # Keep only positive Quantity and Price
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]

    # Convert types
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Quantity"] = df["Quantity"].astype(int)
    df["Price"] = df["Price"].astype(float)

    # Clean string columns
    for col in ["Description", "Invoice", "Country", "Customer ID"]:
        df[col] = df[col].astype(str).str.strip()
    df["Country"] = df["Country"].str.title()

    # Remove top 5% outliers
    for col in ["Quantity", "Price"]:
        high = df[col].quantile(0.95)
        df = df[df[col] <= high]

    # Clip using IQR
    for col in ["Quantity", "Price"]:
        Q1, Q3 = df[col].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        df[col] = df[col].clip(lower, upper)

    # Compute TotalPrice and clean
    df["TotalPrice"] = df["Quantity"] * df["Price"]
    tp_high = df["TotalPrice"].quantile(0.95)
    df = df[df["TotalPrice"] <= tp_high]
    Q1, Q3 = df["TotalPrice"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    df["TotalPrice"] = df["TotalPrice"].clip(Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)

    logger.info(f"Final cleaned shape: {df.shape}")

    # RFM analysis
    snapshot_date = df["InvoiceDate"].max() + dt.timedelta(days=1)
    rfm = (
        df.groupby("Customer ID")
          .agg(
              Recency=("InvoiceDate", lambda x: (snapshot_date - x.max()).days),
              Frequency=("Invoice", "nunique"),
              Monetary=("TotalPrice", "sum")
          )
          .reset_index()
    )

    # Format InvoiceDate for Supabase
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return df, rfm

# ---------------------
# 3) Load (Upsert with Deduplication)
# ---------------------
def load_data_to_supabase(
    df: pd.DataFrame,
    table_name: str,
    upsert: bool = False,
    conflict_cols: str | None = None
) -> bool:
    logger.info(f"Loading {len(df)} rows to {table_name}...")
    records = df.to_dict(orient="records")
    chunk_size = 1000

    try:
        for start in range(0, len(records), chunk_size):
            chunk = records[start:start + chunk_size]

            # Deduplicate by conflict keys
            if upsert and conflict_cols:
                keys = [k.strip() for k in conflict_cols.split(",")]
                uniq = {}
                for rec in chunk:
                    key = tuple(rec[k] for k in keys)
                    uniq[key] = rec
                chunk = list(uniq.values())

            logger.info(f"Processing chunk {start//chunk_size + 1}: {len(chunk)} unique rows")

            if upsert:
                if not conflict_cols:
                    raise ValueError("conflict_cols must be provided for upsert operations")
                supabase.table(table_name).upsert(chunk, on_conflict=conflict_cols).execute()
            else:
                supabase.table(table_name).insert(chunk).execute()

        logger.info(f"Data loaded to {table_name} successfully")
        return True

    except Exception as e:
        logger.error(f"Error loading data to {table_name}: {e}")
        return False

# ---------------------
# Main Pipeline
# ---------------------
def main():
    try:
        raw_df = extract_data_from_supabase("data")
        cleaned_df, rfm_df = clean_data(raw_df)

        # Ensure you have SQL: ALTER TABLE online_retail_clean ADD CONSTRAINT unique_invoice_stock UNIQUE ("Invoice", "StockCode");
        tx_loaded = load_data_to_supabase(
            cleaned_df,
            "online_retail_clean",
            upsert=True,
            conflict_cols="Invoice,StockCode"
        )

        rfm_loaded = load_data_to_supabase(
            rfm_df,
            "customer_rfm",
            upsert=True,
            conflict_cols="Customer ID"
        )

        if tx_loaded and rfm_loaded:
            logger.info("🎉 ETL pipeline completed successfully!")
        else:
            logger.warning("⚠️ ETL pipeline completed with issues.")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()

