from langchain_core.tools import Tool
import yaml
import os
from typing import List, Dict

def _get_low_stock_items(params: str = "") -> str:
    """
    Get list of products with stock levels at or below the minimum threshold.
    Returns up to max_low_stock_items (from config) with details.
    """
    try:
        # Import here to handle potential import errors gracefully
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            # Use default values if config file not found
            config = {
                "low_stock_threshold": 10,
                "max_low_stock_items": 5,
                "verbose": True
            }
        
        low_stock_threshold = config.get("low_stock_threshold", 10)
        max_items = config.get("max_low_stock_items", 5)
        
        # Parse optional parameters
        custom_threshold = None
        custom_limit = None
        
        if params:
            try:
                # Try to parse parameters like "threshold:5" or "limit:10"
                for param in params.split(','):
                    if ':' in param:
                        key, value = param.strip().split(':')
                        if key.lower() == 'threshold':
                            custom_threshold = int(value)
                        elif key.lower() == 'limit':
                            custom_limit = int(value)
            except:
                pass  # Ignore parsing errors, use defaults
        
        threshold = custom_threshold or low_stock_threshold
        limit = custom_limit or max_items
        
        # Query for low stock items
        # Products where quantity_in_stock <= threshold OR quantity_in_stock <= min_stock_level
        low_stock_response = (
            supabase
            .table("products")
            .select("""
                sku, name, price, category,
                inventory!inner(
                    quantity_in_stock, 
                    min_stock_level,
                    max_stock_level,
                    location,
                    last_adjusted
                )
            """)
            .or_(f"inventory.quantity_in_stock.lte.{threshold},inventory.quantity_in_stock.lte.inventory.min_stock_level")
            .order("inventory.quantity_in_stock", desc=False)  # Show lowest stock first
            .limit(limit)
            .execute()
        )
        
        if not low_stock_response.data:
            return f"✅ Good news! No products found with stock levels below {threshold} units or their minimum levels."
        
        # Separate into categories
        out_of_stock = []
        critically_low = []
        low_stock = []
        
        for product in low_stock_response.data:
            inventory = product['inventory']
            current_stock = inventory['quantity_in_stock']
            min_level = inventory['min_stock_level']
            
            if current_stock <= 0:
                out_of_stock.append(product)
            elif current_stock <= min_level * 0.5:  # Less than 50% of minimum
                critically_low.append(product)
            else:
                low_stock.append(product)
        
        # Build response
        result_lines = [
            f"🚨 Low Stock Alert Report",
            f"Threshold: {threshold} units | Showing top {len(low_stock_response.data)} items",
            "=" * 50
        ]
        
        # Out of stock items (highest priority)
        if out_of_stock:
            result_lines.extend([
                "",
                "🔴 OUT OF STOCK (URGENT - Immediate Action Required):"
            ])
            for product in out_of_stock:
                inventory = product['inventory']
                result_lines.append(
                    f"  • {product['name']} ({product['sku']}) - {inventory['quantity_in_stock']} units"
                    f" | Location: {inventory.get('location', 'N/A')}"
                )
        
        # Critically low items
        if critically_low:
            result_lines.extend([
                "",
                "🟡 CRITICALLY LOW (High Priority):"
            ])
            for product in critically_low:
                inventory = product['inventory']
                result_lines.append(
                    f"  • {product['name']} ({product['sku']}) - {inventory['quantity_in_stock']} units"
                    f" (Min: {inventory['min_stock_level']}) | Location: {inventory.get('location', 'N/A')}"
                )
        
        # Low stock items
        if low_stock:
            result_lines.extend([
                "",
                "🟠 LOW STOCK (Medium Priority):"
            ])
            for product in low_stock:
                inventory = product['inventory']
                result_lines.append(
                    f"  • {product['name']} ({product['sku']}) - {inventory['quantity_in_stock']} units"
                    f" (Min: {inventory['min_stock_level']}) | Location: {inventory.get('location', 'N/A')}"
                )
        
        # Add summary statistics
        total_items = len(low_stock_response.data)
        total_out_of_stock = len(out_of_stock)
        total_critical = len(critically_low)
        total_low = len(low_stock)
        
        result_lines.extend([
            "",
            "📊 Summary:",
            f"  • Total Low Stock Items: {total_items}",
            f"  • Out of Stock: {total_out_of_stock}",
            f"  • Critically Low: {total_critical}",
            f"  • Low Stock: {total_low}"
        ])
        
        # Add recommendations
        if out_of_stock:
            result_lines.extend([
                "",
                "💡 Recommendations:",
                "  • Prioritize restocking out-of-stock items immediately",
                "  • Check for alternative suppliers for urgent items",
                "  • Consider customer notification for unavailable products"
            ])
        elif critically_low:
            result_lines.extend([
                "",
                "💡 Recommendations:",
                "  • Schedule restocking for critically low items within 24-48 hours",
                "  • Monitor sales velocity for these products"
            ])
        
        return "\n".join(result_lines)
        
    except ImportError:
        return "Sorry, the inventory database connection is not configured. Please check your database setup."
    except Exception as e:
        return f"Sorry, I encountered an error while checking low stock items: {str(e)}. Please try again."

def _get_category_low_stock(category: str) -> str:
    """
    Get low stock items for a specific product category.
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Load configuration for threshold
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            threshold = config.get("low_stock_threshold", 10)
        except:
            threshold = 10
        
        # Query for low stock items in specific category
        category_response = (
            supabase
            .table("products")
            .select("""
                sku, name, price, category,
                inventory!inner(
                    quantity_in_stock, 
                    min_stock_level,
                    location
                )
            """)
            .eq("category", category)
            .or_(f"inventory.quantity_in_stock.lte.{threshold},inventory.quantity_in_stock.lte.inventory.min_stock_level")
            .order("inventory.quantity_in_stock", desc=False)
            .execute()
        )
        
        if not category_response.data:
            return f"✅ No low stock items found in category '{category}'."
        
        result_lines = [
            f"📦 Low Stock Items in Category: {category}",
            f"Found {len(category_response.data)} items below stock threshold:",
            ""
        ]
        
        for product in category_response.data:
            inventory = product['inventory']
            current_stock = inventory['quantity_in_stock']
            min_level = inventory['min_stock_level']
            
            if current_stock <= 0:
                status = "🔴 OUT OF STOCK"
            elif current_stock <= min_level:
                status = "🟡 LOW STOCK"
            else:
                status = "🟠 BELOW THRESHOLD"
            
            result_lines.append(
                f"  • {product['name']} ({product['sku']}) - {current_stock} units - {status}"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error checking low stock for category '{category}': {str(e)}"

def _get_overstock_items(params: str = "") -> str:
    """
    Get list of products with stock levels above their maximum threshold (overstock).
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Query for overstock items (where current stock > max_stock_level)
        overstock_response = (
            supabase
            .table("products")
            .select("""
                sku, name, price, category,
                inventory!inner(
                    quantity_in_stock, 
                    max_stock_level,
                    min_stock_level,
                    location
                )
            """)
            .filter("inventory.quantity_in_stock", "gt", "inventory.max_stock_level")
            .order("inventory.quantity_in_stock", desc=True)  # Show highest stock first
            .limit(10)
            .execute()
        )
        
        if not overstock_response.data:
            return "✅ No overstock items found. All products are within their maximum stock levels."
        
        result_lines = [
            f"📈 Overstock Report",
            f"Found {len(overstock_response.data)} items above maximum stock levels:",
            ""
        ]
        
        for product in overstock_response.data:
            inventory = product['inventory']
            current_stock = inventory['quantity_in_stock']
            max_level = inventory['max_stock_level']
            excess = current_stock - max_level
            
            result_lines.append(
                f"  • {product['name']} ({product['sku']}) - {current_stock} units"
                f" (Max: {max_level}, Excess: +{excess}) | Location: {inventory.get('location', 'N/A')}"
            )
        
        result_lines.extend([
            "",
            "💡 Overstock Recommendations:",
            "  • Consider promotional pricing to move excess inventory",
            "  • Review procurement schedules to avoid future overstock",
            "  • Evaluate storage costs vs. discount pricing options"
        ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error checking overstock items: {str(e)}"

def _low_stock_handler(input_str: str) -> str:
    """
    Main low stock handler that routes to appropriate sub-functions.
    """
    try:
        input_str = input_str.strip().lower()
        
        # Check for category-specific requests
        if input_str.startswith('category:'):
            category = input_str.replace('category:', '').strip()
            return _get_category_low_stock(category)
        
        # Check for overstock requests
        if 'overstock' in input_str or 'excess' in input_str:
            return _get_overstock_items(input_str)
        
        # Default to general low stock check
        return _get_low_stock_items(input_str)
        
    except Exception as e:
        return f"Error processing low stock request: {str(e)}"

# Create the low stock tool
low_stock_tool = Tool(
    name="LowStockListTool",
    func=_low_stock_handler,
    description="""
    Get list of products with low stock levels. Supports multiple query types:
    1. General low stock: "" (empty string or general terms)
    2. Category-specific: "category:electronics" or "category:clothing"
    3. Overstock items: "overstock" or "excess inventory"
    4. Custom parameters: "threshold:5,limit:10"
    
    Returns categorized lists of low stock items with priority levels and recommendations.
    """
)