"""
Online Retail Data Analysis Script

This script analyzes your retail dataset to help identify issues with data types,
particularly focusing on decimal quantities and other potential data problems.

Usage:
python analyze_retail_data.py --file your_data_file.csv
"""

import pandas as pd
import numpy as np
import argparse
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import time

def analyze_from_file(file_path):
    """Analyze data from a local file"""
    try:
        # Try different formats based on file extension
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            print(f"Unsupported file format: {file_path}")
            return
        
        analyze_dataframe(df)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

def analyze_from_supabase(table_name="data", sample_size=10000):
    """Extract and analyze data from Supabase"""
    try:
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("Error: SUPABASE_URL and SUPABASE_KEY must be set in your .env file")
            return
            
        supabase = create_client(supabase_url, supabase_key)
        
        print(f"Extracting sample data ({sample_size} rows) from Supabase...")
        response = supabase.table(table_name).select("*").limit(sample_size).execute()
        
        if not response.data:
            print(f"No data found in table {table_name}")
            return
            
        df = pd.DataFrame(response.data)
        print(f"Successfully extracted {len(df)} rows from {table_name}")
        
        analyze_dataframe(df)
    except Exception as e:
        print(f"Error extracting data from Supabase: {e}")
        return

def analyze_dataframe(df):
    """Run analysis on the provided dataframe"""
    # Data overview
    print("\n===== DATA OVERVIEW =====")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {', '.join(df.columns)}")
    
    # Basic column statistics
    print("\n===== COLUMN STATISTICS =====")
    for col in df.columns:
        print(f"\nColumn: {col}")
        print(f"  Data type: {df[col].dtype}")
        print(f"  Missing values: {df[col].isna().sum()} ({df[col].isna().mean()*100:.2f}%)")
        
        # For numeric columns
        if pd.api.types.is_numeric_dtype(df[col]):
            print(f"  Min: {df[col].min()}")
            print(f"  Max: {df[col].max()}")
            print(f"  Mean: {df[col].mean()}")
            print(f"  Median: {df[col].median()}")
            
            # Check if numeric column has decimal values
            if col == 'Quantity' or col == 'Price':
                if df[col].dtype in ['float64', 'float32']:
                    non_integer_values = df[~df[col].isna() & (df[col] != df[col].astype(int))]
                    decimal_count = len(non_integer_values)
                    decimal_percentage = (decimal_count / len(df)) * 100
                    
                    print(f"  Records with decimal values: {decimal_count} ({decimal_percentage:.2f}%)")
                    
                    if decimal_count > 0:
                        print("  Sample decimal values:")
                        for i, (idx, row) in enumerate(non_integer_values.head(5).iterrows()):
                            if 'StockCode' in df.columns and 'Description' in df.columns:
                                print(f"    {i+1}. Value: {row[col]}, StockCode: {row['StockCode']}, Description: {row['Description']}")
                            else:
                                print(f"    {i+1}. Value: {row[col]}")
    
    # Analyze the Quantity column specifically
    if 'Quantity' in df.columns:
        print("\n===== QUANTITY COLUMN ANALYSIS =====")
        
        # Distribution of decimal places in Quantity
        if pd.api.types.is_numeric_dtype(df['Quantity']):
            # Create a function to count decimal places
            def count_decimal_places(x):
                if pd.isna(x) or int(x) == x:
                    return 0
                return len(str(x).split('.')[-1])
            
            # Apply function to each value and count occurrences
            decimal_places = df['Quantity'].apply(count_decimal_places)
            decimal_counts = decimal_places.value_counts().sort_index()
            
            print("Distribution of decimal places in Quantity:")
            for places, count in decimal_counts.items():
                print(f"  {places} decimal places: {count} values ({count/len(df)*100:.2f}%)")
            
            # Show some examples of common decimal patterns
            if decimal_counts.sum() > 0:
                print("\nCommon decimal patterns:")
                decimal_df = df[decimal_places > 0]
                common_decimals = decimal_df['Quantity'].value_counts().head(10)
                
                for value, count in common_decimals.items():
                    print(f"  Value {value}: appears {count} times")
                    
                    # Show a few examples of products with this quantity
                    if 'StockCode' in df.columns and 'Description' in df.columns:
                        examples = df[(df['Quantity'] == value)].head(3)
                        for _, example in examples.iterrows():
                            print(f"    - StockCode: {example['StockCode']}, Description: {example['Description']}")
    
    # Check for other anomalies
    print("\n===== OTHER POTENTIAL ISSUES =====")
    
    # Check for extremely large quantities
    if 'Quantity' in df.columns and pd.api.types.is_numeric_dtype(df['Quantity']):
        q99 = df['Quantity'].quantile(0.99)
        extreme_qty = df[df['Quantity'] > q99]
        
        print(f"99th percentile quantity: {q99}")
        print(f"Records with extremely large quantities: {len(extreme_qty)} ({len(extreme_qty)/len(df)*100:.2f}%)")
        
        if not extreme_qty.empty:
            print("\nSamples of unusually large quantities:")
            for _, row in extreme_qty.head(5).iterrows():
                if 'StockCode' in df.columns and 'Description' in df.columns:
                    print(f"  Quantity: {row['Quantity']}, StockCode: {row['StockCode']}, Description: {row['Description']}")
                else:
                    print(f"  Quantity: {row['Quantity']}")
    
    # Check for negative quantities
    if 'Quantity' in df.columns and pd.api.types.is_numeric_dtype(df['Quantity']):
        neg_qty = df[df['Quantity'] < 0]
        
        if not neg_qty.empty:
            print(f"\nRecords with negative quantities: {len(neg_qty)} ({len(neg_qty)/len(df)*100:.2f}%)")
            print("Sample negative quantities:")
            for _, row in neg_qty.head(5).iterrows():
                if 'StockCode' in df.columns and 'Description' in df.columns:
                    print(f"  Quantity: {row['Quantity']}, StockCode: {row['StockCode']}, Description: {row['Description']}")
                else:
                    print(f"  Quantity: {row['Quantity']}")
    
    # Summary of recommendations
    print("\n===== RECOMMENDATIONS =====")
    
    # Recommendations for Quantity column
    if 'Quantity' in df.columns and pd.api.types.is_numeric_dtype(df['Quantity']):
        decimal_qty = df[~df['Quantity'].isna() & (df['Quantity'] != df['Quantity'].astype(int))]
        decimal_percentage = len(decimal_qty) / len(df) * 100
        
        if decimal_percentage > 0:
            print(f"QUANTITY COLUMN: {len(decimal_qty)} values ({decimal_percentage:.2f}%) have decimal places.")
            
            if decimal_percentage > 5:
                print("  FINDING: Significant portion of quantities have decimal values.")
                
                # Check if these are common in specific products
                if 'StockCode' in df.columns:
                    # Get top products with decimal quantities
                    top_decimal_products = decimal_qty['StockCode'].value_counts().head(5)
                    if not top_decimal_products.empty:
                        print("  Common products with decimal quantities:")
                        for code, count in top_decimal_products.items():
                            product_desc = df[df['StockCode'] == code]['Description'].iloc[0] \
                                if not df[df['StockCode'] == code]['Description'].empty else "Unknown"
                            percentage = count / len(df[df['StockCode'] == code]) * 100
                            print(f"    - {code} ({product_desc}): {count} decimal entries ({percentage:.2f}% of this product)")
                
                print("  RECOMMENDATION: Review these products - they might legitimately be sold in decimal quantities")
                print("                  (weight, volume, length). If so, consider keeping decimals in your database.")
            else:
                print("  FINDING: Small percentage of quantities have decimal values.")
                print("  RECOMMENDATION: These are likely errors - rounding to integers is appropriate.")
        else:
            print("QUANTITY COLUMN: No decimal quantities found.")
            print("  RECOMMENDATION: Quantity appears to be properly stored as integers.")
    
    # Recommendations for Price column
    if 'Price' in df.columns and pd.api.types.is_numeric_dtype(df['Price']):
        print("\nPRICE COLUMN:")
        print("  RECOMMENDATION: Keep as decimal with 2 places for proper currency representation.")

def main():
    parser = argparse.ArgumentParser(description='Analyze Online Retail Dataset')
    parser.add_argument('--file', type=str, help='Path to data file (CSV or Excel)')
    parser.add_argument('--supabase', action='store_true', help='Extract data from Supabase instead of file')
    parser.add_argument('--table', type=str, default='data', help='Supabase table name (default: data)')
    parser.add_argument('--sample', type=int, default=10000, help='Number of rows to sample from Supabase')
    
    args = parser.parse_args()
    
    if args.supabase:
        analyze_from_supabase(args.table, args.sample)
    elif args.file:
        analyze_from_file(args.file)
    else:
        print("Error: Please specify either --file or --supabase")
        parser.print_help()

if __name__ == "__main__":
    main()