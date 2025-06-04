"""
Order Management Tools
Tools for creating, checking, updating, and canceling orders
"""
import json
from typing import Dict, Any, List
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from ..services.order_service import OrderService

# Initialize order service
order_service = OrderService()


class CreateOrderInput(BaseModel):
    """Input model for create_order tool."""
    customer_email: str = Field(description="Customer's email address")
    customer_name: str = Field(description="Customer's full name")
    items: str = Field(description="JSON string of order items with sku, quantity fields")


class OrderStatusInput(BaseModel):
    """Input model for order status tool."""
    order_id: str = Field(description="The order ID to check status for")


class UpdateOrderInput(BaseModel):
    """Input model for update order tool."""
    order_id: str = Field(description="The order ID to update")
    new_status: str = Field(description="New status: pending, confirmed, processing, shipped, delivered, cancelled")


class CancelOrderInput(BaseModel):
    """Input model for cancel order tool."""
    order_id: str = Field(description="The order ID to cancel")


def create_order_tool_func(customer_email: str, customer_name: str, items: str) -> str:
    """
    Create a new order with the specified items.
    
    Args:
        customer_email: Customer's email address
        customer_name: Customer's full name  
        items: JSON string with list of items [{"sku": "ABC123", "quantity": 2}, ...]
    
    Returns:
        JSON string with order creation result
    """
    try:
        # Parse items JSON
        items_list = json.loads(items)
        
        if not isinstance(items_list, list):
            return json.dumps({
                "success": False,
                "error": "Items must be a list",
                "message": "Items parameter must be a JSON array"
            })
        
        # Validate required fields
        for item in items_list:
            if not isinstance(item, dict) or 'sku' not in item or 'quantity' not in item:
                return json.dumps({
                    "success": False,
                    "error": "Invalid item format",
                    "message": "Each item must have 'sku' and 'quantity' fields"
                })
        
        # Validate products first
        validation_result = order_service.validate_products(items_list)
        
        if not validation_result['all_valid']:
            invalid_items = [r for r in validation_result['results'] if not r['valid']]
            return json.dumps({
                "success": False,
                "error": "Product validation failed",
                "message": "Some products are invalid or out of stock",
                "invalid_items": invalid_items
            })
        
        # Enrich items with product details
        enriched_items = []
        for item in items_list:
            # Find validation result for this SKU
            validation_item = next(r for r in validation_result['results'] if r['sku'] == item['sku'])
            enriched_items.append({
                'sku': item['sku'],
                'product_name': validation_item['product_name'],
                'quantity': item['quantity'],
                'unit_price': validation_item['unit_price']
            })
        
        # Create the order
        result = order_service.create_order(customer_email, customer_name, enriched_items)
        return json.dumps(result, indent=2)
        
    except json.JSONDecodeError:
        return json.dumps({
            "success": False,
            "error": "Invalid JSON format",
            "message": "Items parameter must be valid JSON"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to create order: {str(e)}"
        })


def check_order_status_tool_func(order_id: str) -> str:
    """
    Check the status and details of an order.
    
    Args:
        order_id: The order ID to check
    
    Returns:
        JSON string with order details
    """
    try:
        result = order_service.get_order_status(order_id)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to check order status: {str(e)}"
        })


def update_order_status_tool_func(order_id: str, new_status: str) -> str:
    """
    Update the status of an order.
    
    Args:
        order_id: The order ID to update
        new_status: New status (pending, confirmed, processing, shipped, delivered, cancelled)
    
    Returns:
        JSON string with update result
    """
    try:
        result = order_service.update_order_status(order_id, new_status)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to update order status: {str(e)}"
        })


def cancel_order_tool_func(order_id: str) -> str:
    """
    Cancel an order (only if not yet shipped).
    
    Args:
        order_id: The order ID to cancel
    
    Returns:
        JSON string with cancellation result
    """
    try:
        result = order_service.cancel_order(order_id)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to cancel order: {str(e)}"
        })


# Create the tools
create_order_tool = Tool(
    name="create_order",
    description="Create a new order with customer information and items. Items should be JSON string with sku and quantity fields.",
    func=create_order_tool_func,
    args_schema=CreateOrderInput
)

check_order_status_tool = Tool(
    name="check_order_status", 
    description="Check the current status and details of an order by order ID.",
    func=check_order_status_tool_func,
    args_schema=OrderStatusInput
)

update_order_status_tool = Tool(
    name="update_order_status",
    description="Update the status of an order. Valid statuses: pending, confirmed, processing, shipped, delivered, cancelled.",
    func=update_order_status_tool_func,
    args_schema=UpdateOrderInput
)

cancel_order_tool = Tool(
    name="cancel_order",
    description="Cancel an order (only allowed if order is not yet shipped).",
    func=cancel_order_tool_func,
    args_schema=CancelOrderInput
)

# Export all tools
__all__ = [
    'create_order_tool',
    'check_order_status_tool', 
    'update_order_status_tool',
    'cancel_order_tool'
]
