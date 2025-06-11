"""
Order Management Tools
Tools for creating, checking, updating, and canceling orders
"""
import json
from typing import Dict, Any, List
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

from src.agents.OrderAgent.services.order_service import OrderService

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


def create_order_tool_func(*args, **kwargs) -> str:
    """
    Create a new order with the specified items.
    Handles both direct calls and LangChain parameter passing.
    
    Args:
        Can receive parameters as:
        1. create_order_tool_func(customer_email, customer_name, items) - direct call
        2. create_order_tool_func(json_string) - LangChain JSON call
        3. create_order_tool_func(**kwargs) - keyword arguments
    
    Returns:
        JSON string with order creation result
    """
    try:
        # Handle different parameter passing styles
        if len(args) == 3:
            # Direct call with 3 parameters
            customer_email, customer_name, items = args
        elif len(args) == 1 and isinstance(args[0], str):
            # LangChain passing JSON as single string argument
            try:
                data = json.loads(args[0])
                customer_email = data.get('customer_email')
                customer_name = data.get('customer_name') 
                items = data.get('items')
            except (json.JSONDecodeError, AttributeError):
                # Maybe it's just the items string
                customer_email = kwargs.get('customer_email')
                customer_name = kwargs.get('customer_name')
                items = args[0] if args[0].startswith('[') else kwargs.get('items')
        elif kwargs:
            # Keyword arguments
            customer_email = kwargs.get('customer_email')
            customer_name = kwargs.get('customer_name')
            items = kwargs.get('items')
        else:
            return json.dumps({
                "success": False,
                "error": "Invalid parameters",
                "message": "Expected customer_email, customer_name, and items parameters"
            })
        
        # Validate required parameters
        if not all([customer_email, customer_name, items]):
            return json.dumps({
                "success": False,
                "error": "Missing parameters",
                "message": f"Missing: {', '.join([p for p, v in [('customer_email', customer_email), ('customer_name', customer_name), ('items', items)] if not v])}"
            })
        
        # Parse items JSON
        if isinstance(items, str):
            items_list = json.loads(items)
        else:
            items_list = items
        
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
        
        # Rest of the function remains the same...
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
          # Create the order directly with items_list - the service will handle validation internally
        result = order_service.create_order(
            customer_email=customer_email,
            customer_name=customer_name,
            items=items_list,
            shipping_address="TBD - Address collection needed",
            billing_address="TBD - Address collection needed", 
            payment_method="credit_card"
        )
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


def get_available_products_tool_func(*args, **kwargs) -> str:
    """
    Get list of available products to help customers discover what they can order.
    
    Args:
        Can receive parameters as:
        1. get_available_products_tool_func() - no parameters, get default products
        2. get_available_products_tool_func(limit) - specify limit
        3. get_available_products_tool_func(limit, category) - specify limit and category
        4. get_available_products_tool_func(**kwargs) - keyword arguments
    
    Returns:
        JSON string with available products
    """
    try:
        # Handle different parameter formats
        limit = 20  # default
        category = None
        
        # Check if first argument is a JSON string (common with LangChain)
        if len(args) == 1 and isinstance(args[0], str):
            try:
                # Try to parse as JSON
                if args[0].strip() in ['{}', '']:
                    # Empty JSON or empty string - use defaults
                    pass
                else:
                    params = json.loads(args[0])
                    limit = int(params.get('limit', 20))
                    category = params.get('category', None)
            except (json.JSONDecodeError, ValueError):
                # If not valid JSON, treat as category name
                category = args[0] if args[0] else None
        elif len(args) >= 1 and not isinstance(args[0], str):
            # Direct call with positional args (non-string)
            try:
                limit = int(args[0]) if args[0] is not None else 20
            except (ValueError, TypeError):
                limit = 20
            if len(args) >= 2:
                category = args[1] if args[1] else None
        elif kwargs:
            # Keyword arguments
            try:
                limit = int(kwargs.get('limit', 20))
            except (ValueError, TypeError):
                limit = 20
            category = kwargs.get('category', None)
          # Call service method
        result = order_service.get_available_products(limit=limit, category=category)
        
        # Format the response to encourage Final Answer
        if result.get('success') and result.get('products'):
            formatted_response = {
                "success": True,
                "message": f"Here are our available products:\n\n",
                "products": result['products'],
                "instruction": "Please provide Final Answer with this product list to the customer"
            }
            # Add formatted product display
            product_list = []
            for product in result['products']:
                product_list.append(f"• {product['name']} ({product['sku']}) - {product['price']} - {product['description']}")
            
            formatted_response["formatted_display"] = "\n".join(product_list)
            formatted_response["message"] += formatted_response["formatted_display"]
            formatted_response["message"] += "\n\nPlease let me know which items you'd like to order with quantities and your email address."
            
            return json.dumps(formatted_response, indent=2)
        else:
            return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": f"Failed to get available products: {str(e)}"
        })


# Create the tools without args_schema to fix LangChain parameter parsing
create_order_tool = Tool(
    name="create_order",
    description="""Create a new order with customer information and items.
    
    Parameters (in exact order):
    1. customer_email: Customer's email address (string)
    2. customer_name: Customer's full name (string) 
    3. items: JSON string array of items with sku and quantity fields (string)
    
    Example usage: create_order("john@example.com", "John Doe", "[{\"sku\":\"ABC123\",\"quantity\":2}]")""",
    func=create_order_tool_func
)

check_order_status_tool = Tool(
    name="check_order_status", 
    description="""Check the current status and details of an order by order ID.
    
    Parameters:
    1. order_id: The order ID to check (string)
    
    Example usage: check_order_status("12345-67890")""",
    func=check_order_status_tool_func
)

update_order_status_tool = Tool(
    name="update_order_status",
    description="""Update the status of an order.
    
    Parameters (in exact order):
    1. order_id: The order ID to update (string)
    2. new_status: New status - must be one of: pending, confirmed, processing, shipped, delivered, cancelled (string)
    
    Example usage: update_order_status("12345-67890", "confirmed")""",
    func=update_order_status_tool_func
)

cancel_order_tool = Tool(
    name="cancel_order",
    description="""Cancel an order (only allowed if order is not yet shipped).
    
    Parameters:
    1. order_id: The order ID to cancel (string)
    
    Example usage: cancel_order("12345-67890")""",
    func=cancel_order_tool_func
)

get_available_products_tool = Tool(
    name="get_available_products",
    description="""Get list of available products to show customers what they can order. 
    
    CRITICAL: After calling this tool successfully, you MUST immediately provide a Final Answer 
    with the product list. DO NOT call this tool again.
    
    Parameters (optional):
    - limit: Number of products to return (default 20)
    - category: Filter by category (optional)
    
    Example usage: get_available_products()""",
    func=get_available_products_tool_func
)

# Export all tools
__all__ = [
    'create_order_tool',
    'check_order_status_tool', 
    'update_order_status_tool',
    'cancel_order_tool',
    'get_available_products_tool'
]
