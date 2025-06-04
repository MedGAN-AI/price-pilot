import json
from typing import Optional
from langchain_core.tools import Tool

# Import connector functions (either Supabase‐backed or in‐memory fallback)
from src.agents.InventoryAgent.connectors.sql_connector import (
    get_product_by_sku,
    search_product_by_name,
    get_inventory_by_product_id
)

# Mock data for testing when database is empty
MOCK_PRODUCTS = {
    "SHOES-RED-001": {
        "id": "1",
        "name": "Red Running Shoes",
        "sku": "SHOES-RED-001",
        "stock": 25
    },
    "SHIRT-BLUE-002": {
        "id": "2", 
        "name": "Blue Cotton Shirt",
        "sku": "SHIRT-BLUE-002",
        "stock": 10
    },
    "PANTS-BLACK-003": {
        "id": "3",
        "name": "Black Jeans",
        "sku": "PANTS-BLACK-003", 
        "stock": 0
    }
}

def _get_mock_product_by_sku(sku: str):
    """Fallback to mock data if database lookup fails"""
    return MOCK_PRODUCTS.get(sku.upper())

def _search_mock_product_by_name(name_query: str):
    """Fallback to mock data if database lookup fails"""
    name_lower = name_query.lower()
    for sku, product in MOCK_PRODUCTS.items():
        if name_lower in product["name"].lower():
            return product
    return None

def _stock_by_sku(sku: str) -> str:
    """
    Tool function: Given a SKU, return a string with the current stock level.
    If SKU not found or error, return an error message.
    """
    sku_clean = sku.strip().upper()
    
    # Try database first
    product = get_product_by_sku(sku_clean)
    
    # If not found in database, try mock data
    if not product:
        mock_product = _get_mock_product_by_sku(sku_clean)
        if mock_product:
            stock = mock_product["stock"]
            name = mock_product["name"]
            if stock > 0:
                return f"There are {stock} unit(s) of \"{name}\" (SKU: {sku_clean}) in stock."
            else:
                return f"\"{name}\" (SKU: {sku_clean}) is currently out of stock."
        else:
            return f"Error: SKU '{sku_clean}' not found in product catalog."

    # Database product found - get inventory
    product_id = product["id"]
    name = product["name"]

    stock = get_inventory_by_product_id(product_id)
    if stock is None:
        return f"Error: Could not retrieve inventory for SKU '{sku_clean}'."

    if stock > 0:
        return f"There are {stock} unit(s) of \"{name}\" (SKU: {sku_clean}) in stock."
    else:
        return f"\"{name}\" (SKU: {sku_clean}) is currently out of stock."

stock_by_sku_tool = Tool(
    name="CheckStockBySKU",
    func=_stock_by_sku,
    description=(
        "Use this tool to check inventory by SKU. "
        "Input: a product SKU string (e.g., 'SHOES-RED-001'). "
        "Output: a message about how many units are in stock or if it's out of stock."
    )
)

def _stock_by_name(name_query: str) -> str:
    """
    Tool function: Given a partial or full product name, find the product,
    then return the stock level. If not found or error, return an error message.
    """
    name_clean = name_query.strip()
    
    # Try database first
    product = search_product_by_name(name_clean)
    
    # If not found in database, try mock data
    if not product:
        mock_product = _search_mock_product_by_name(name_clean)
        if mock_product:
            stock = mock_product["stock"]
            name = mock_product["name"]
            sku = mock_product["sku"]
            if stock > 0:
                return f"There are {stock} unit(s) of \"{name}\" (SKU: {sku}) in stock."
            else:
                return f"\"{name}\" (SKU: {sku}) is currently out of stock."
        else:
            return f"Error: No product found matching '{name_clean}'."

    # Database product found - get inventory
    sku = product["sku"]
    product_id = product["id"]
    name = product["name"]

    stock = get_inventory_by_product_id(product_id)
    if stock is None:
        return f"Error: Could not retrieve inventory for product '{name}'."

    if stock > 0:
        return f"There are {stock} unit(s) of \"{name}\" (SKU: {sku}) in stock."
    else:
        return f"\"{name}\" (SKU: {sku}) is currently out of stock."

stock_by_name_tool = Tool(
    name="CheckStockByName",
    func=_stock_by_name,
    description=(
        "Use this tool to check inventory by product name. "
        "Input: a product name or partial name (e.g., 'Red Running Shoes'). "
        "Output: a message about how many units are in stock or if it's out of stock."
    )
)