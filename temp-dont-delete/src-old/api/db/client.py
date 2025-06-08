import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Get the Supabase URL and key from environment
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Initialize the Supabase client
supabase: Optional[Client] = None

def get_client() -> Client:
    """Get or initialize the Supabase client"""
    global supabase
    if supabase is None:
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        supabase = create_client(url, key)
    return supabase

# Product data operations
def get_products(skip: int = 0, limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get products from database
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Optional category filter
        
    Returns:
        List of product records
    """
    query = get_client().table("products").select("*")
    
    # Apply category filter if provided
    if category:
        query = query.eq("category", category)
    
    # Apply pagination
    query = query.range(skip, skip + limit - 1)
    
    # Execute query
    response = query.execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    return response.data

def get_product(product_id: int) -> Dict[str, Any]:
    """
    Get a single product by ID
    
    Args:
        product_id: Unique identifier for the product
        
    Returns:
        Product record
    """
    response = get_client().table("products").select("*").eq("id", product_id).limit(1).execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    # Check if product was found
    if not response.data:
        raise ValueError(f"Product with ID {product_id} not found")
    
    return response.data[0]

def create_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new product
    
    Args:
        product_data: Product data to insert
        
    Returns:
        Created product record
    """
    # Add timestamps
    product_data["created_at"] = datetime.now().isoformat()
    product_data["updated_at"] = datetime.now().isoformat()
    
    # Insert product
    response = get_client().table("products").insert(product_data).execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    return response.data[0]

def update_product(product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing product
    
    Args:
        product_id: Unique identifier for the product
        product_data: Product data to update
        
    Returns:
        Updated product record
    """
    # Add updated_at timestamp
    product_data["updated_at"] = datetime.now().isoformat()
    
    # Update product
    response = get_client().table("products").update(product_data).eq("id", product_id).execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    # Check if product was found and updated
    if not response.data:
        raise ValueError(f"Product with ID {product_id} not found")
    
    return response.data[0]

# Price recommendation operations
def save_recommendation(recommendation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a price recommendation
    
    Args:
        recommendation_data: Recommendation data to insert
        
    Returns:
        Created recommendation record
    """
    # Add timestamp if not present
    if "timestamp" not in recommendation_data:
        recommendation_data["timestamp"] = datetime.now().isoformat()
    
    # Insert recommendation
    response = get_client().table("price_recommendations").insert(recommendation_data).execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    return response.data[0]

def get_price_history(product_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get price change history for a product
    
    Args:
        product_id: Unique identifier for the product
        days: Number of days of history to retrieve
        
    Returns:
        List of price change records
    """
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Query price changes
    response = get_client().table("price_changes") \
        .select("*") \
        .eq("product_id", product_id) \
        .gte("timestamp", cutoff_date) \
        .order("timestamp", desc=True) \
        .execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    return response.data

def get_sales_history(product_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get sales history for a product
    
    Args:
        product_id: Unique identifier for the product
        days: Number of days of history to retrieve
        
    Returns:
        List of sales records
    """
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Query sales
    response = get_client().table("sales") \
        .select("*") \
        .eq("product_id", product_id) \
        .gte("date", cutoff_date) \
        .order("date", desc=True) \
        .execute()
    
    # Check for errors
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Supabase error: {response.error}")
    
    return response.data