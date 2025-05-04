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
# 1) Extract - Get all data in chunks to handle large datasets
# ---------------------
def extract_data_from_supabase(table_name: str = "data") -> pd.DataFrame:
    logger.info(f"Extracting data from {table_name}...")
    try:
        # Initialize an empty DataFrame to store all results
        all_data = []
        offset = 0
        page_size = 1000  # Set to a safer value to avoid timeouts
        
        # Keep fetching until we get all data
        while True:
            logger.info(f"Fetching data from offset {offset}...")
            response = supabase.table(table_name).select("*").range(offset, offset + page_size - 1).execute()
            data = response.data
            
            # Stop if no more data
            if not data:
                break
                
            all_data.extend(data)
            logger.info(f"Fetched {len(data)} rows (total so far: {len(all_data)})")
            
            # Stop if we got less than a full page (indicating we've reached the end)
            if len(data) < page_size:
                break
                
            # Increment offset for next batch
            offset += page_size
        
        # Convert all results to DataFrame
        df = pd.DataFrame(all_data)
        logger.info(f"Successfully extracted {len(df)} total rows from {table_name}")
        return df
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

    # Convert types - MATCH EXACTLY WITH SUPABASE TABLE SCHEMA
    logger.info(f"Column types before conversion: {df.dtypes}")
    
    # Convert dates
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    
    # TEXT fields - ensure they're all strings and stripped
    for col in ["Invoice", "StockCode", "Description", "Customer ID", "Country"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    
    if "Country" in df.columns:
        df["Country"] = df["Country"].str.title()
        
    # INTEGER fields
    # Quantity is INTEGER in Supabase
    df["Quantity"] = df["Quantity"].astype(float).round().astype(int)
    
    # DECIMAL fields (Price and TotalPrice are DECIMAL(10,2))
    df["Price"] = df["Price"].astype(float).round(2)

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

    # Compute TotalPrice and clean - ensure it's also DECIMAL(10,2)
    df["TotalPrice"] = (df["Quantity"] * df["Price"]).round(2)
    tp_high = df["TotalPrice"].quantile(0.95)
    df = df[df["TotalPrice"] <= tp_high]
    Q1, Q3 = df["TotalPrice"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    df["TotalPrice"] = df["TotalPrice"].clip(Q1 - 1.5 * IQR, Q3 + 1.5 * IQR).round(2)

    # Log column types after conversion
    logger.info(f"Column types after cleaning: {df.dtypes}")
    logger.info(f"Final cleaned shape: {df.shape}")

    # RFM analysis - ensure RFM types match Supabase schema
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
    
    # Ensure RFM values match Supabase schema
    rfm["Recency"] = rfm["Recency"].astype(int)
    rfm["Frequency"] = rfm["Frequency"].astype(int)
    rfm["Monetary"] = rfm["Monetary"].round(2)

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
    
    # Check column types for debugging
    logger.info(f"DataFrame types before loading: {df.dtypes}")
    
    # Convert DataFrame to list of dictionaries
    records = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            value = row[col]
            # Handle NaN values
            if pd.isna(value):
                record[col] = None
            else:
                # Preserve the value as is - don't try to convert it
                # This ensures we maintain the correct data types established in clean_data
                record[col] = value
        records.append(record)
    
    # Process in smaller chunks for better stability
    chunk_size = 250  # Even smaller chunk size for better error isolation
    total_chunks = (len(records) + chunk_size - 1) // chunk_size
    
    try:
        successful_chunks = 0
        for i, start in enumerate(range(0, len(records), chunk_size)):
            try:
                end = min(start + chunk_size, len(records))
                chunk = records[start:end]

                # Deduplicate by conflict keys
                if upsert and conflict_cols:
                    keys = [k.strip() for k in conflict_cols.split(",")]
                    uniq = {}
                    for rec in chunk:
                        key = tuple(str(rec.get(k, '')) for k in keys)
                        uniq[key] = rec
                    chunk = list(uniq.values())

                logger.info(f"Processing chunk {i+1}/{total_chunks}: {len(chunk)} unique rows")
                
                # Print first record for debugging (only on first chunk)
                if i == 0 and chunk:
                    sample = chunk[0]
                    logger.info(f"Sample record types:")
                    for k, v in sample.items():
                        logger.info(f"  {k}: {v} ({type(v).__name__})")

                if upsert:
                    if not conflict_cols:
                        raise ValueError("conflict_cols must be provided for upsert operations")
                    supabase.table(table_name).upsert(chunk, on_conflict=conflict_cols).execute()
                else:
                    supabase.table(table_name).insert(chunk).execute()
                    
                successful_chunks += 1
                logger.info(f"Successfully processed chunk {i+1}/{total_chunks}")
                
            except Exception as e:
                logger.error(f"Error processing chunk {i+1}: {e}")
                
                # Print the first record from the failing chunk for debugging
                if chunk:
                    logger.error(f"First record in failing chunk:")
                    for k, v in chunk[0].items():
                        logger.error(f"  {k}: {v} ({type(v).__name__})")
                
                import traceback
                logger.error(traceback.format_exc())
                # Continue with next chunk
        
        logger.info(f"Data loaded to {table_name}: {successful_chunks}/{total_chunks} chunks successfully processed")
        return successful_chunks > 0

    except Exception as e:
        logger.error(f"Error loading data to {table_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# ---------------------
# Main Pipeline
# ---------------------
def main():
    try:
        # Extract - this now gets ALL data using pagination
        raw_df = extract_data_from_supabase("data")
        
        # Check if data was retrieved
        if raw_df.empty:
            logger.error("No data retrieved from Supabase")
            return
            
        # Clean and transform
        cleaned_df, rfm_df = clean_data(raw_df)

        # Load cleaned transactions - handle all data in chunks
        tx_loaded = load_data_to_supabase(
            cleaned_df,
            "online_retail_clean",
            upsert=True,
            conflict_cols="Invoice,StockCode"
        )

        # Load RFM data
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
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()