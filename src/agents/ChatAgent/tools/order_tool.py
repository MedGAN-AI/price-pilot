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

from langchain_core.tools import Tool
import json
import uuid
from datetime import datetime

def _check_order_status(order_id: str) -> str:
    """
    Check the status of a customer order by order ID.
    Returns order details, items, and delivery information.
    """
    try:
        # Import here to handle potential import errors gracefully
        from src.integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the order system is currently unavailable. Please try again later."
        
        # Clean the order ID (remove any extra whitespace/quotes)
        order_id = order_id.strip().strip('"\'')
        
        # Get order details with user information
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

def _place_simple_order(order_request: str) -> str:
    """
    Place a simple order. For demo purposes, this creates a basic order.
    In production, this would integrate with your full order processing system.
    """
    try:
        from src.integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the ordering system is currently unavailable. Please try again later."
        
        # For now, return a helpful message about order placement
        # In a real system, you'd parse the order_request and create the order
        return (
            "To place an order, I'll need the following information:\n"
            "• Your email address\n"
            "• Product SKUs and quantities you want to order\n"
            "• Shipping address\n"
            "• Payment method preference\n\n"
            "Please provide these details and I'll help you place your order. "
            "You can also browse our products first by asking me to search for items you're interested in."
        )
        
    except Exception as e:
        return f"Sorry, I encountered an error with the ordering system: {str(e)}. Please try again later."

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

# Additional tool for order placement (you can add this to your tools list if needed)
place_order_tool = Tool(
    name="PlaceOrderTool", 
    func=_place_simple_order,
    description=(
        "Help customers place new orders. "
        "Input: order request information. "
        "Output: Order placement guidance or confirmation."
    )
)
