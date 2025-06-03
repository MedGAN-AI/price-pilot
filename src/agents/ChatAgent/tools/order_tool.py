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
from datetime import datetime
from langchain_core.tools import Tool

def _place_order(input_str: str) -> str:
    """
    Place an order for a given user. Expects JSON input with keys:
      - user_id (UUID string)
      - product_sku (text)
      - quantity (integer)
      - shipping_address (text)
      - billing_address (text, optional; defaults to shipping if absent)
      - payment_method (text, optional; defaults to 'unspecified')

    Steps:
      1. Parse input_str as JSON.
      2. Verify user exists in `users` table.
      3. Lookup product by SKU in `products` → get `product_id`, `price`.
      4. Check inventory for available `quantity`.
      5. If enough stock, insert into `orders`, then `order_items`.
      6. Deduct inventory.
      7. Return confirmation with order_id and total.
    Any error (invalid JSON, missing fields, DB error) returns a clear message.
    """
    try:
        # Import here to handle potential import errors gracefully
        from src.integrations.supabase_client import supabase
        
        # Test if supabase client is properly initialized
        if not supabase:
            return "Sorry, the ordering system is currently unavailable. Please try again later."
        
    except ImportError:
        return "Sorry, the ordering system is not configured. Please contact support."
    except Exception as e:
        return f"Sorry, there's an issue with the ordering system: {str(e)}"

    # Parse JSON
    try:
        data: Dict[str, Any] = json.loads(input_str)
    except json.JSONDecodeError:
        return (
            "Error: OrderTool expects a valid JSON string. Example format:\n"
            '{"user_id":"<UUID>","product_sku":"<SKU>","quantity":<int>,' 
            '"shipping_address":"<address>","billing_address":"<address>","payment_method":"<method>"}'
        )

    # Required fields
    user_id = data.get("user_id")
    product_sku = data.get("product_sku")
    quantity = data.get("quantity", 1)
    shipping_address = data.get("shipping_address")
    billing_address = data.get("billing_address") or shipping_address
    payment_method = data.get("payment_method", "unspecified")

    # Validate required fields
    if not user_id or not product_sku or not shipping_address:
        return "Error: Missing required field(s). Please include user_id, product_sku, and shipping_address."

    try:
        # 1) Verify user exists
        user_resp = (
            supabase
            .table("users")
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        
        if not user_resp or not user_resp.data:
            return f"Error: No user found with ID '{user_id}'."

        # 2) Lookup product by SKU
        prod_resp = (
            supabase
            .table("products")
            .select("id, price")
            .eq("sku", product_sku)
            .limit(1)
            .execute()
        )
        
        if not prod_resp or not prod_resp.data:
            return f"Error: No product found with SKU '{product_sku}'."

        product_id = prod_resp.data[0].get("id")
        unit_price = float(prod_resp.data[0].get("price", 0.0))

        # 3) Check inventory
        inv_resp = (
            supabase
            .table("inventory")
            .select("quantity_in_stock")
            .eq("product_id", product_id)
            .limit(1)
            .execute()
        )
        
        if not inv_resp or not inv_resp.data:
            return f"Error: No inventory record found for SKU '{product_sku}'."

        available_stock = int(inv_resp.data[0].get("quantity_in_stock", 0))
        if quantity > available_stock:
            return f"Sorry, only {available_stock} unit(s) of SKU '{product_sku}' are in stock."

        # 4) Insert into orders
        total_amount = unit_price * int(quantity)
        order_payload = {
            "user_id": user_id,
            "order_date": datetime.utcnow().isoformat(),
            "total_amount": total_amount,
            "status": "pending",
            "shipping_address": shipping_address,
            "billing_address": billing_address,
            "payment_method": payment_method
        }
        
        order_resp = supabase.table("orders").insert(order_payload).execute()
        if not order_resp or not order_resp.data:
            return "Error: Failed to create order. Please try again."

        order_id = order_resp.data[0].get("id")

        # 5) Insert into order_items
        order_item_payload = {
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price
        }
        
        order_item_resp = supabase.table("order_items").insert(order_item_payload).execute()
        if not order_item_resp or not order_item_resp.data:
            return "Error: Failed to add items to order. Please contact support."

        # 6) Deduct inventory
        new_stock = available_stock - int(quantity)
        inventory_update = {
            "quantity_in_stock": new_stock,
            "last_adjusted": datetime.utcnow().isoformat()
        }
        
        inv_update_resp = (
            supabase
            .table("inventory")
            .update(inventory_update)
            .eq("product_id", product_id)
            .execute()
        )

        # 7) Return confirmation
        return (
            f"Success! Your order (ID: {order_id}) has been placed.\n"
            f"• Product SKU: {product_sku}\n"
            f"• Quantity: {quantity}\n"
            f"• Unit Price: ${unit_price:.2f}\n"
            f"• Total Amount: ${total_amount:.2f}\n"
            f"• Remaining stock for SKU '{product_sku}': {new_stock} unit(s).\n"
            f"Thank you for shopping with us!"
        )
        
    except Exception as e:
        return f"Sorry, I encountered an error while processing your order: {str(e)}. Please try again or contact support."


# Wrap it as a LangChain Tool
order_tool = Tool(
    name="OrderTool",
    func=_place_order,
    description=(
        "Places an order for a product. Input: a JSON string containing keys "
        "\"user_id\", \"product_sku\", \"quantity\", \"shipping_address\", optionally "
        "\"billing_address\" and \"payment_method\". Output: confirmation message with order ID."
    )
)
