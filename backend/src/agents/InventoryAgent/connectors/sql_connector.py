from typing import Optional, Dict, Any
import logging
from src.integrations.supabase_client import supabase

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_product_by_sku(sku: str) -> Optional[Dict[str, Any]]:
    """
    Given a SKU string, return a dict with 'id', 'name', and 'sku' from products table.
    If not found, return None.
    """
    try:
        logger.info(f"Searching for product with SKU: {sku}")
        
        response = (
            supabase
            .table("products")
            .select("id, name, sku")
            .eq("sku", sku)
            .limit(1)
            .execute()
        )

        # Debug logging
        logger.info(f"Response status_code: {getattr(response, 'status_code', 'No status')}")
        logger.info(f"Response data: {getattr(response, 'data', 'No data')}")
        
        # Check if we have data - this is the key fix!
        # Don't rely on status_code since Supabase client might not set it
        data = getattr(response, "data", None)
        if not data or len(data) == 0:
            logger.info(f"No product found with SKU: {sku}")
            return None

        logger.info(f"Found product: {data[0]}")
        return data[0]  # e.g., { "id": "...", "name": "...", "sku": "..." }
        
    except Exception as e:
        logger.error(f"Exception in get_product_by_sku: {str(e)}")
        return None

def search_product_by_name(name_query: str) -> Optional[Dict[str, Any]]:
    """
    Case-insensitive search on products.name ILIKE '%name_query%'.
    Returns the first matching product (id, name, sku). If none, returns None.
    """
    try:
        logger.info(f"Searching for product with name: {name_query}")
        
        response = (
            supabase
            .table("products")
            .select("id, name, sku")
            .filter("name", "ilike", f"%{name_query}%")
            .limit(1)
            .execute()
        )

        # Debug logging
        logger.info(f"Response status_code: {getattr(response, 'status_code', 'No status')}")
        logger.info(f"Response data: {getattr(response, 'data', 'No data')}")

        # Check if we have data - same fix here
        data = getattr(response, "data", None)
        if not data or len(data) == 0:
            logger.info(f"No product found with name: {name_query}")
            return None

        logger.info(f"Found product: {data[0]}")
        return data[0]
        
    except Exception as e:
        logger.error(f"Exception in search_product_by_name: {str(e)}")
        return None

def get_inventory_by_product_id(product_id: str) -> Optional[int]:
    """
    Given a product_id (UUID), return quantity_in_stock (int).
    If not found or error, return None.
    """
    try:
        logger.info(f"Getting inventory for product_id: {product_id}")
        
        response = (
            supabase
            .table("inventory")
            .select("quantity_in_stock")
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )

        # Debug logging
        logger.info(f"Response status_code: {getattr(response, 'status_code', 'No status')}")
        logger.info(f"Response data: {getattr(response, 'data', 'No data')}")

        # Check if we have data - same fix here
        data = getattr(response, "data", None)
        if not data or len(data) == 0:
            logger.info(f"No inventory found for product_id: {product_id}")
            return 0  # Return 0 instead of None if no inventory record exists

        # data[0] is { "quantity_in_stock": 48 }, etc.
        quantity = data[0].get("quantity_in_stock", 0)
        logger.info(f"Found inventory quantity: {quantity}")
        return quantity
        
    except Exception as e:
        logger.error(f"Exception in get_inventory_by_product_id: {str(e)}")
        return None