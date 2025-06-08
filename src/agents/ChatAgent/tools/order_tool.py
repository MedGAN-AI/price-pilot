from langchain_core.tools import Tool
import json
import uuid
from datetime import datetime

def _check_order_status(order_id: str) -> str:
    """
    Check the status of a customer order by order ID.
    Returns order details, items, and delivery information.
    """
    try:        # Import here to handle potential import errors gracefully
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
          # Clean the order ID (remove any extra whitespace/quotes)
        order_id = order_id.strip().strip('"\'')
        
        # Validate UUID format
        try:
            uuid.UUID(order_id)
        except ValueError:
            return (
                f"❌ Invalid order ID format: '{order_id}'\n\n"
                "Order IDs should be in UUID format (e.g., 123e4567-e89b-12d3-a456-426614174000).\n"
                "You can find your order ID in your confirmation email or account dashboard."
            )# Get order details with user information
        order_response = (
            supabase
            .table("orders")
            .select("""
                id, order_date, total_amount, status, shipping_address, 
                payment_method,
                users!inner(full_name, email)
            """)
            .eq("id", order_id)
            .execute()
        )
        
        if not order_response.data:
            return f"Order {order_id} not found. Please check your order ID and try again."
        
        order = order_response.data[0]
        
        # Get order items with product details
        items_response = (
            supabase
            .table("order_items")
            .select("""
                quantity, unit_price,
                products!inner(name, sku)
            """)
            .eq("order_id", order_id)
            .execute()
        )
        
        # Get delivery status if available
        delivery_response = (
            supabase
            .table("delivery_status")
            .select("carrier, tracking_number, status, last_location, estimated_delivery")
            .eq("order_id", order_id)
            .execute()
        )
        
        # Format the response
        result_lines = [
            f"📋 Order Details",
            f"Order ID: {order['id']}",
            f"Customer: {order['users']['full_name']} ({order['users']['email']})",
            f"Order Date: {order['order_date'][:10]}",
            f"Status: {order['status'].replace('_', ' ').title()}",
            f"Total Amount: ${order['total_amount']:.2f}",
            f"Payment: {order['payment_method'].replace('_', ' ').title()}",
            f"Shipping To: {order['shipping_address']}",
            "",
            "📦 Items Ordered:"
        ]
        
        # Add items
        for item in items_response.data:
            product = item['products']
            item_total = item['quantity'] * item['unit_price']
            result_lines.append(
                f"  • {product['name']} (SKU: {product['sku']}) "
                f"- Qty: {item['quantity']} @ ${item['unit_price']:.2f} = ${item_total:.2f}"
            )
        
        # Add delivery information if available
        if delivery_response.data:
            delivery = delivery_response.data[0]
            result_lines.extend([
                "",
                "🚚 Delivery Information:",
                f"  • Carrier: {delivery['carrier']}",
                f"  • Tracking: {delivery['tracking_number']}",
                f"  • Status: {delivery['status'].replace('_', ' ').title()}",
                f"  • Last Location: {delivery['last_location']}"
            ])
            
            if delivery['estimated_delivery']:
                est_date = delivery['estimated_delivery'][:10]
                result_lines.append(f"  • Estimated Delivery: {est_date}")
        
        return "\n".join(result_lines)
        
    except ImportError:
        return "Sorry, the order database connection is not configured. Please check your database setup."
    except Exception as e:
        return f"Sorry, I encountered an error while checking your order: {str(e)}. Please try again with a valid order ID."

# Create the main order tool
order_tool = Tool(
    name="OrderTool",
    func=_check_order_status,
    description=(
        "Check the status and details of a customer order. "
        "Input: an order ID (UUID string). "
        "Output: Complete order information including items, status, and delivery details."
    )
)


# Comprehensive order tool that handles multiple operations 
'''
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from langchain_core.tools import Tool
import json

def _check_order_status(order_id: str) -> str:
    """
    Check the status of an existing order by order ID.
    Returns order details, items, and delivery status.
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
        
        # Get order details with user information
        order_response = (
            supabase
            .table("orders")
            .select("""
                id, order_date, total_amount, status, shipping_address, 
                payment_method, created_at,
                users!inner(full_name, email)
            """)
            .eq("id", order_id)
            .execute()
        )
        
        if not order_response.data:
            return f"Order {order_id} not found. Please check your order ID."
        
        order = order_response.data[0]
        
        # Get order items with product details
        items_response = (
            supabase
            .table("order_items")
            .select("""
                quantity, unit_price,
                products!inner(name, sku)
            """)
            .eq("order_id", order_id)
            .execute()
        )
        
        # Get delivery status if available
        delivery_response = (
            supabase
            .table("delivery_status")
            .select("carrier, tracking_number, status, last_location, estimated_delivery")
            .eq("order_id", order_id)
            .execute()
        )
        
        # Format response
        result = [
            f"Order ID: {order['id']}",
            f"Customer: {order['users']['full_name']} ({order['users']['email']})",
            f"Order Date: {order['order_date'][:10]}",
            f"Status: {order['status'].title()}",
            f"Total Amount: ${order['total_amount']:.2f}",
            f"Payment Method: {order['payment_method'].replace('_', ' ').title()}",
            f"Shipping Address: {order['shipping_address']}",
            "",
            "Items Ordered:"
        ]
        
        for item in items_response.data:
            product = item['products']
            result.append(f"  • {product['name']} (SKU: {product['sku']}) - Qty: {item['quantity']} @ ${item['unit_price']:.2f} each")
        
        # Add delivery information if available
        if delivery_response.data:
            delivery = delivery_response.data[0]
            result.extend([
                "",
                "Delivery Information:",
                f"  • Carrier: {delivery['carrier']}",
                f"  • Tracking Number: {delivery['tracking_number']}",
                f"  • Delivery Status: {delivery['status'].replace('_', ' ').title()}",
                f"  • Last Location: {delivery['last_location']}",
                f"  • Estimated Delivery: {delivery['estimated_delivery'][:10] if delivery['estimated_delivery'] else 'TBD'}"
            ])
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error checking order status: {str(e)}"

def _place_order(order_data: str) -> str:
    """
    Place a new order. Expects JSON string with order details.
    Format: {"user_email": "email", "items": [{"sku": "SKU", "quantity": 1}], "shipping_address": "address", "payment_method": "credit_card"}
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
        
        # Parse order data
        try:
            order_info = json.loads(order_data)
        except json.JSONDecodeError:
            return "Invalid order format. Please provide valid JSON order data."
        
        required_fields = ["user_email", "items", "shipping_address", "payment_method"]
        for field in required_fields:
            if field not in order_info:
                return f"Missing required field: {field}"
        
        # Find user by email
        user_response = (
            supabase
            .table("users")
            .select("id, full_name")
            .eq("email", order_info["user_email"])
            .execute()
        )
        
        if not user_response.data:
            return f"User with email {order_info['user_email']} not found. Please register first."
        
        user = user_response.data[0]
        
        # Validate items and calculate total
        total_amount = 0.0
        validated_items = []
        
        for item in order_info["items"]:
            if "sku" not in item or "quantity" not in item:
                return "Each item must have 'sku' and 'quantity' fields."
            
            # Get product details
            product_response = (
                supabase
                .table("products")
                .select("id, name, price")
                .eq("sku", item["sku"])
                .execute()
            )
            
            if not product_response.data:
                return f"Product with SKU {item['sku']} not found."
            
            product = product_response.data[0]
            
            # Check inventory
            inventory_response = (
                supabase
                .table("inventory")
                .select("quantity_in_stock")
                .eq("product_id", product["id"])
                .execute()
            )
            
            if not inventory_response.data:
                return f"No inventory information found for {product['name']}."
            
            available_qty = inventory_response.data[0]["quantity_in_stock"]
            requested_qty = int(item["quantity"])
            
            if available_qty < requested_qty:
                return f"Insufficient stock for {product['name']}. Available: {available_qty}, Requested: {requested_qty}"
            
            validated_items.append({
                "product_id": product["id"],
                "name": product["name"],
                "quantity": requested_qty,
                "unit_price": float(product["price"])
            })
            
            total_amount += requested_qty * float(product["price"])
        
        # Create order
        order_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        order_insert = {
            "id": order_id,
            "user_id": user["id"],
            "order_date": now,
            "total_amount": total_amount,
            "status": "pending",
            "shipping_address": order_info["shipping_address"],
            "billing_address": order_info.get("billing_address", order_info["shipping_address"]),
            "payment_method": order_info["payment_method"],
            "created_at": now,
            "updated_at": now
        }
        
        supabase.table("orders").insert(order_insert).execute()
        
        # Create order items
        for item in validated_items:
            item_id = str(uuid.uuid4())
            order_item = {
                "id": item_id,
                "order_id": order_id,
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "created_at": now,
                "updated_at": now
            }
            supabase.table("order_items").insert(order_item).execute()
            
            # Update inventory
            supabase.table("inventory").update({
                "quantity_in_stock": supabase.rpc("decrease_inventory", {
                    "product_id": item["product_id"],
                    "decrease_by": item["quantity"]
                }),
                "last_adjusted": now,
                "updated_at": now
            }).eq("product_id", item["product_id"]).execute()
        
        # Format success response
        result = [
            f"✅ Order placed successfully!",
            f"Order ID: {order_id}",
            f"Customer: {user['full_name']}",
            f"Total Amount: ${total_amount:.2f}",
            f"Status: Pending",
            "",
            "Items Ordered:"
        ]
        
        for item in validated_items:
            result.append(f"  • {item['name']} - Qty: {item['quantity']} @ ${item['unit_price']:.2f} each")
        
        result.extend([
            "",
            f"Shipping Address: {order_info['shipping_address']}",
            f"Payment Method: {order_info['payment_method'].replace('_', ' ').title()}",
            "",
            "Your order is being processed and you'll receive updates via email."
        ])
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error placing order: {str(e)}"

def _update_order_status(update_data: str) -> str:
    """
    Update order status. Expects JSON string with order_id and new_status.
    Format: {"order_id": "uuid", "status": "confirmed|shipped|delivered|cancelled"}
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
        
        try:
            update_info = json.loads(update_data)
        except json.JSONDecodeError:
            return "Invalid update format. Please provide valid JSON data."
        
        if "order_id" not in update_info or "status" not in update_info:
            return "Missing required fields: order_id and status"
        
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        if update_info["status"] not in valid_statuses:
            return f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        # Update order status
        response = (
            supabase
            .table("orders")
            .update({
                "status": update_info["status"],
                "updated_at": datetime.now().isoformat()
            })
            .eq("id", update_info["order_id"])
            .execute()
        )
        
        if not response.data:
            return f"Order {update_info['order_id']} not found."
        
        return f"✅ Order {update_info['order_id']} status updated to: {update_info['status'].title()}"
        
    except Exception as e:
        return f"Error updating order status: {str(e)}"

def _get_user_orders(user_email: str) -> str:
    """
    Get all orders for a specific user by email.
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
        
        # Get user orders
        orders_response = (
            supabase
            .table("orders")
            .select("""
                id, order_date, total_amount, status,
                users!inner(full_name, email)
            """)
            .eq("users.email", user_email)
            .order("order_date", desc=True)
            .execute()
        )
        
        if not orders_response.data:
            return f"No orders found for {user_email}."
        
        result = [f"Orders for {user_email}:", ""]
        
        for order in orders_response.data:
            result.extend([
                f"Order ID: {order['id']}",
                f"Date: {order['order_date'][:10]}",
                f"Status: {order['status'].title()}",
                f"Total: ${order['total_amount']:.2f}",
                "---"
            ])
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error retrieving user orders: {str(e)}"

# Create the comprehensive order tool that handles multiple order operations
def _order_handler(input_str: str) -> str:
    """
    Main order handler that routes to appropriate sub-functions based on input.
    Supports: check_status, place_order, update_status, get_user_orders
    """
    try:
        # Try to parse as JSON for structured operations
        try:
            data = json.loads(input_str)
            action = data.get("action", "").lower()
            
            if action == "check_status":
                return _check_order_status(data.get("order_id", ""))
            elif action == "place_order":
                return _place_order(json.dumps(data.get("order_data", {})))
            elif action == "update_status":
                return _update_order_status(json.dumps({
                    "order_id": data.get("order_id", ""),
                    "status": data.get("status", "")
                }))
            elif action == "get_user_orders":
                return _get_user_orders(data.get("user_email", ""))
            else:
                return "Invalid action. Supported actions: check_status, place_order, update_status, get_user_orders"
        
        except json.JSONDecodeError:
            # If not JSON, treat as simple order ID for status check
            return _check_order_status(input_str.strip())
            
    except Exception as e:
        return f"Error processing order request: {str(e)}"

# Main order tool
order_tool = Tool(
    name="OrderTool",
    func=_order_handler,
    description="""
    Comprehensive order management tool. Supports multiple operations:
    
    1. Check order status (simple): Just provide order ID as string
    2. Structured operations (JSON format):
       - {"action": "check_status", "order_id": "uuid"}
       - {"action": "place_order", "order_data": {"user_email": "email", "items": [{"sku": "SKU", "quantity": 1}], "shipping_address": "address", "payment_method": "credit_card"}}
       - {"action": "update_status", "order_id": "uuid", "status": "confirmed|shipped|delivered|cancelled"}
       - {"action": "get_user_orders", "user_email": "email"}
    
    For simple order status checks, just provide the order ID.
    For complex operations, use JSON format with appropriate action and parameters.
    """
)
'''