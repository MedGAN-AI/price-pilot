"""
Setup Script for Supabase Tables

This script creates the necessary tables in Supabase for the data pipeline.
It will create:
1. A cleaned transactions table
2. A customer RFM summary table

Note: You need Supabase permissions to create tables.
"""

import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# Load env vars
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SERVICE_ROLE_KEY")

# Initialize Supabase client for RPC calls
supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)  # uses service role key :contentReference[oaicite:6]{index=6}

# Logger setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def execute_sql(sql: str) -> bool:
    """Run raw SQL via the void-returning RPC."""
    res = supabase.rpc("execute_sql", {"p_sql": sql}).execute()
    if res.error:
        logger.error("RPC error: %s", res.error.message)
        return False
    return True

# SQL to create the cleaned transactions table
create_clean_table_sql = """
CREATE TABLE IF NOT EXISTS online_retail_clean (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "Invoice" TEXT,
    "StockCode" TEXT,
    "Description" TEXT,
    "Quantity" INTEGER,
    "InvoiceDate" TIMESTAMP,
    "Price" DECIMAL(10,2),
    "Customer ID" TEXT,
    "Country" TEXT,
    "TotalPrice" DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_online_retail_clean_invoice ON online_retail_clean("Invoice");
CREATE INDEX IF NOT EXISTS idx_online_retail_clean_customer ON online_retail_clean("Customer ID");
CREATE INDEX IF NOT EXISTS idx_online_retail_clean_date ON online_retail_clean("InvoiceDate");
"""

# SQL to create the RFM summary table
create_rfm_table_sql = """
CREATE TABLE IF NOT EXISTS customer_rfm (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "CustomerID" TEXT UNIQUE,
    "Recency" INTEGER,
    "Frequency" INTEGER,
    "Monetary" DECIMAL(12,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_customer_rfm_customer ON customer_rfm("CustomerID");
"""

def main():
    logger.info("Creating online_retail_clean…")
    if execute_sql(create_clean_table_sql):
        logger.info("✅ online_retail_clean table created or already exists")
    logger.info("Creating customer_rfm…")
    if execute_sql(create_rfm_table_sql):
        logger.info("✅ customer_rfm table created or already exists")

if __name__ == "__main__":
    main()
