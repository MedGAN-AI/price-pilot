'''
Online Retail Data Pipeline - Supabase ETL Process (Enhanced Version with Pagination)

This script:
1. Extracts data from Supabase with pagination to avoid timeouts
2. Transforms/cleans it (handling data type issues)
3. Loads the cleaned data back to Supabase with smaller chunks and retries

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
import argparse
import time
from typing import List, Optional
import random

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
# 1) Extract with Pagination
# ---------------------
def extract_data_from_supabase(
    table_name: str = "data", 
    sample: bool = False, 
    sample_size: int = 10000,
    page_size: int = 1000,
    max_retries: int = 5
) -> pd.DataFrame:
    """
    Extract data from Supabase table with pagination to handle large datasets
    
    Args:
        table_name: Name of the source table
        sample: If True, only extract a sample of the data
        sample_size: Number of rows to extract in sample mode
        page_size: Number of rows per page
        max_retries: Maximum number of retry attempts for each page
    """
    logger.info(f"Extracting data from {table_name}..." + (" (SAMPLE MODE)" if sample else ""))
    
    all_data = []
    page = 0
    total_rows = 0
    
    try:
        while True:
            retries = 0
            success = False
            
            while not success and retries < max_retries:
                try:
                    query = supabase.table(table_name).select("*")
                    
                    # Apply pagination
                    start = page * page_size
                    query = query.range(start, start + page_size - 1)
                    
                    # For sample mode, we'll just use the first few pages
                    if sample and total_rows >= sample_size:
                        break
                        
                    response = query.execute()
                    page_data = response.data
                    
                    if not page_data:  # No more data to fetch
                        break
                        
                    all_data.extend(page_data)
                    total_rows += len(page_data)
                    logger.info(f"Page {page+1}: Retrieved {len(page_data)} rows (Total: {total_rows})")
                    
                    page += 1
                    success = True
                    
                    # Add a small delay between requests to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    retries += 1
                    backoff = 2 ** retries + random.random()  # Exponential backoff with jitter
                    logger.warning(f"Error on page {page+1}, retry {retries}/{max_retries} after {backoff:.2f}s: {e}")
                    time.sleep(backoff)
            
            if not success:
                logger.error(f"Failed to retrieve page {page+1} after {max_retries} retries")
                
            # Exit conditions
            if sample and total_rows >= sample_size:
                logger.info(f"Sample size of {sample_size} reached, stopping extraction")
                break
                
            if len(page_data) < page_size:  # Last page has fewer rows than page_size
                break
        
        df = pd.DataFrame(all_data)
        
        # If in sample mode, ensure we don't exceed sample_size
        if sample and len(df) > sample_size:
            df = df.head(sample_size)
            
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
    
    # Fix data types - particularly the Price column which is text in the source
    logger.info("Fixing data types...")
    
    # Handle Price column (from text to numeric)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    
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
    df["Customer ID"] = df["Customer ID"].astype(str)  # Ensure Customer ID is string

    # Clean string columns
    for col in ["Description", "Invoice", "Country", "Customer ID"]:
        if col in df.columns:  # Only process if column exists
            df[col] = df[col].astype(str).str.strip()
    
    # Add Country column if missing
    if "Country" not in df.columns:
        df["Country"] = "Unknown"
    else:
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
    
    # Ensure proper types for RFM data
    rfm["Recency"] = rfm["Recency"].astype(int)
    rfm["Frequency"] = rfm["Frequency"].astype(int)
    rfm["Monetary"] = rfm["Monetary"].astype(float)
    rfm["Customer ID"] = rfm["Customer ID"].astype(str)

    # Format InvoiceDate for Supabase
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%dT%H:%M:%S")

    return df, rfm

# ---------------------
# 3) Load with Smaller Chunks and Retries
# ---------------------

# Type conversion for Supabase's expectations
def prepare_record_types(record: dict) -> dict:
    """
    Ensure all values have the correct type for Supabase
    Converts float integers (like 1.0) to actual integers where appropriate
    """
    result = {}
    for key, value in record.items():
        # Convert float integers to int
        if isinstance(value, float):
            if value.is_integer() and key in ["Quantity", "Frequency", "Recency"]:  # Fields that should be integers
                result[key] = int(value)
            else:
                result[key] = round(value, 2)  # Round other float values to 2 decimal places
        else:
            result[key] = value
    return result
def load_data_to_supabase(
    df: pd.DataFrame,
    table_name: str,
    upsert: bool = False,
    conflict_cols: Optional[str] = None,
    chunk_size: int = 200,  # Reduced chunk size
    max_retries: int = 5
) -> bool:
    logger.info(f"Loading {len(df)} rows to {table_name}...")
    records = df.to_dict(orient="records")
    
    success_count = 0
    total_chunks = (len(records) + chunk_size - 1) // chunk_size

    try:
        for start in range(0, len(records), chunk_size):
            chunk = records[start:start + chunk_size]
            chunk_num = start // chunk_size + 1

            # Deduplicate by conflict keys and fix data types
            processed_chunk = []
            if upsert and conflict_cols:
                keys = [k.strip() for k in conflict_cols.split(",")]
                uniq = {}
                for rec in chunk:
                    fixed_rec = prepare_record_types(rec)  # Fix data types
                    key = tuple(fixed_rec[k] for k in keys if k in fixed_rec)
                    uniq[key] = fixed_rec
                processed_chunk = list(uniq.values())
            else:
                for rec in chunk:
                    processed_chunk.append(prepare_record_types(rec))  # Fix data types
                    
            chunk = processed_chunk

            logger.info(f"Processing chunk {chunk_num}/{total_chunks}: {len(chunk)} unique rows")

            # Retry logic
            retries = 0
            success = False
            
            while not success and retries < max_retries:
                try:
                    if upsert:
                        if not conflict_cols:
                            raise ValueError("conflict_cols must be provided for upsert operations")
                        supabase.table(table_name).upsert(chunk, on_conflict=conflict_cols).execute()
                    else:
                        supabase.table(table_name).insert(chunk).execute()
                    
                    success = True
                    success_count += 1
                    logger.info(f"Chunk {chunk_num}/{total_chunks} loaded successfully")
                    
                except Exception as e:
                    retries += 1
                    backoff = 2 ** retries + random.random()  # Exponential backoff with jitter
                    logger.warning(f"Error loading chunk {chunk_num}, retry {retries}/{max_retries} after {backoff:.2f}s: {e}")
                    time.sleep(backoff)
            
            
            if not success:
                logger.error(f"Failed to load chunk {chunk_num} after {max_retries} retries")
            
            # Add a small delay between chunks
            time.sleep(1)

        success_rate = success_count / total_chunks
        if success_rate == 1.0:
            logger.info(f"All data loaded to {table_name} successfully")
            return True
        else:
            logger.warning(f"Data loaded to {table_name} with {success_rate:.1%} success rate")
            return success_rate > 0.9  # Consider it successful if >90% chunks loaded

    except Exception as e:
        logger.error(f"Error loading data to {table_name}: {e}")
        return False

# ---------------------
# Main Pipeline
# ---------------------
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ETL Pipeline for Online Retail Data')
    parser.add_argument('--sample', action='store_true', help='Run in sample mode with limited data')
    parser.add_argument('--sample-size', type=int, default=10000, help='Number of rows for sample mode')
    parser.add_argument('--page-size', type=int, default=1000, help='Number of rows per page during extraction')
    parser.add_argument('--upload-chunk-size', type=int, default=200, help='Number of rows per chunk during upload')
    parser.add_argument('--retries', type=int, default=5, help='Maximum number of retry attempts')
    args = parser.parse_args()
    
    try:
        # Extract data with pagination
        raw_df = extract_data_from_supabase(
            "data", 
            sample=args.sample, 
            sample_size=args.sample_size,
            page_size=args.page_size,
            max_retries=args.retries
        )
        
        # Clean the data
        cleaned_df, rfm_df = clean_data(raw_df)

        # Load data to Supabase with smaller chunks and retries
        tx_loaded = load_data_to_supabase(
            cleaned_df,
            "online_retail_clean",
            upsert=True,
            conflict_cols="Invoice,StockCode",
            chunk_size=args.upload_chunk_size,
            max_retries=args.retries
        )

        rfm_loaded = load_data_to_supabase(
            rfm_df,
            "customer_rfm",
            upsert=True,
            conflict_cols="Customer ID",
            chunk_size=args.upload_chunk_size,
            max_retries=args.retries
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