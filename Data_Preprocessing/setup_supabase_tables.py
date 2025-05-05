"""
Script to create the necessary tables in Supabase for the ETL pipeline.
"""
#Currently this script is not used in the pipeline, but it can be used to create the tables manually if needed.




import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Check for required environment variables
if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

# SQL to create the tables
create_tables_sql = """
-- Create the cleaned transactions table
CREATE TABLE IF NOT EXISTS online_retail_clean (
    "Invoice" TEXT NOT NULL,
    "StockCode" TEXT NOT NULL,
    "Description" TEXT,
    "Quantity" INTEGER,
    "InvoiceDate" TIMESTAMP WITH TIME ZONE,
    "Price" NUMERIC(10, 2),
    "Customer ID" TEXT,
    "Country" TEXT,
    "TotalPrice" NUMERIC(10, 2),
    PRIMARY KEY ("Invoice", "StockCode")
);

-- Create table for RFM analysis
CREATE TABLE IF NOT EXISTS customer_rfm (
    "Customer ID" TEXT PRIMARY KEY,
    "Recency" INTEGER,
    "Frequency" INTEGER,
    "Monetary" NUMERIC(12, 2)
);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_online_retail_clean_customer ON online_retail_clean ("Customer ID");
CREATE INDEX IF NOT EXISTS idx_online_retail_clean_invoice_date ON online_retail_clean ("InvoiceDate");
"""

def create_tables():
    print("Creating tables in Supabase...")
    try:
        # Execute the SQL
        result = supabase.rpc('exec_sql', {'query': create_tables_sql}).execute()
        print("Tables created successfully!")
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()