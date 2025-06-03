'''from langchain_core.tools import Tool

def _check_order_status(order_id: str) -> str:
    """
    Stub implementation. In a real system, you’d call your order database or API.
    """
    return f"Order {order_id} is currently being processed and should ship soon."

order_tool = Tool(
    name="OrderTool",
    func=_check_order_status,
    description="Gets the status of a customer order. Input: an order ID string."
)'''

# this function for the status we can do other for the ordering

import json
from typing import Dict, Any
from supabase import Client
from langchain_core.tools import Tool
from datetime import datetime

# Import the Supabase client
from src.integrations.supabase_client import supabase

def _place_order(input_str: str) -> str:
    """
    Place an order for a given user. Expects JSON input with keys:
      - user_id: (string UUID)
      - product_sku: (string)
      - quantity: (integer)
      - shipping_address: (string)
      - billing_address: (string, optional; if not provided, uses shipping_address)
    
    Example input_str:
      '{"user_id":"uuid-1234-abcd-...", "product_sku":"SKU123", "quantity":2, "shipping_address":"123 Main St, Amman, Jordan"}'
    
    Process:
      1. Verify that user exists.
      2. Lookup product by SKU → get product_id and unit price.
      3. Check inventory for available `quantity`.
      4. If there's enough inventory, proceed:
         a) Insert into `orders` table.
         b) Insert into `order_items` table (linking order_id, product_id, quantity, unit_price).
         c) Deduct inventory (subtract from `inventory.quantity_in_stock`).
      5. Return a confirmation string with order ID and total amount.
    
    If anything fails, return an error message.
    """
    try:
        data: Dict[str, Any] = json.loads(input_str)
    except json.JSONDecodeError:
        return "Error: OrderTool expects a JSON string. Example: {\"user_id\":\"<UUID>\",\"product_sku\":\"<SKU>\",\"quantity\":<int>,\"shipping_address\":\"<address>\"}."
    
    # Required fields
    user_id = data.get("user_id")
    product_sku = data.get("product_sku")
    quantity = data.get("quantity", 1)
    shipping_address = data.get("shipping_address")
    billing_address = data.get("billing_address") or shipping_address

    # Validate inputs
    if not all([user_id, product_sku, shipping_address]):
        return "Error: Missing one of required fields: user_id, product_sku, or shipping_address."

    # 1) Verify user exists
    user_resp = supabase.table("users").select("id").eq("id", user_id).limit(1).execute()
    if user_resp.error:
        return f"Error checking user existence: {user_resp.error.message}"
    if not user_resp.data:
        return f"Error: User with ID '{user_id}' not found."

    # 2) Lookup product by SKU
    prod_resp = supabase.table("products") \
        .select("id, price") \
        .eq("sku", product_sku) \
        .limit(1) \
        .execute()
    if prod_resp.error:
        return f"Error looking up product '{product_sku}': {prod_resp.error.message}"
    if not prod_resp.data:
        return f"Error: Product with SKU '{product_sku}' not found."

    product_id = prod_resp.data[0]["id"]
    unit_price = float(prod_resp.data[0]["price"])

    # 3) Check inventory
    inv_resp = supabase.table("inventory") \
        .select("quantity_in_stock") \
        .eq("product_id", product_id) \
        .limit(1) \
        .execute()
    if inv_resp.error:
        return f"Error checking inventory: {inv_resp.error.message}"
    if not inv_resp.data:
        return f"Error: No inventory record found for product SKU '{product_sku}'."

    available_stock = int(inv_resp.data[0]["quantity_in_stock"])
    if quantity > available_stock:
        return f"Sorry, only {available_stock} unit(s) of SKU '{product_sku}' are in stock right now."

    # 4) Insert into orders
    total_amount = unit_price * int(quantity)
    order_payload = {
        "user_id": user_id,
        "order_date": datetime.utcnow().isoformat(),
        "total_amount": total_amount,
        "status": "pending",
        "shipping_address": shipping_address,
        "billing_address": billing_address,
        "payment_method": data.get("payment_method", "unspecified")
    }
    order_resp = supabase.table("orders").insert(order_payload).execute()
    if order_resp.error:
        return f"Error creating order: {order_resp.error.message}"
    order_id = order_resp.data[0]["id"]

    # 5) Insert into order_items
    order_item_payload = {
        "order_id": order_id,
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price
    }
    order_item_resp = supabase.table("order_items").insert(order_item_payload).execute()
    if order_item_resp.error:
        return f"Error inserting order item: {order_item_resp.error.message}"

    # 6) Deduct inventory: new_stock = available_stock - quantity
    new_stock = available_stock - int(quantity)
    inventory_update = {
        "quantity_in_stock": new_stock,
        "last_adjusted": datetime.utcnow().isoformat()
    }
    inv_update_resp = supabase.table("inventory") \
        .update(inventory_update) \
        .eq("product_id", product_id) \
        .execute()
    if inv_update_resp.error:
        return f"Error updating inventory: {inv_update_resp.error.message}"

    # Return confirmation
    return (
        f"Success! Your order {order_id} has been placed.\n"
        f"• Product SKU: {product_sku}\n"
        f"• Quantity: {quantity}\n"
        f"• Unit Price: ${unit_price:.2f}\n"
        f"• Total Amount: ${total_amount:.2f}\n"
        f"• Current stock left for SKU '{product_sku}': {new_stock} unit(s).\n"
        f"Thank you for shopping with us!"
    )


# Wrap it as a LangChain Tool
order_tool = Tool(
    name="OrderTool",
    func=_place_order,
    description=(
        "Places an order for a product. Input: a JSON string containing keys "
        "\"user_id\", \"product_sku\", \"quantity\", \"shipping_address\", and optionally "
        "\"billing_address\" and \"payment_method\". "
        "Output: confirmation message with order ID."
    )
)
