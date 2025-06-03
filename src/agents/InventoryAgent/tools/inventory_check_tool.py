from langchain_core.tools import Tool
from typing import Optional

def _check_inventory_stock(sku: str) -> str:
    """
    Check the current stock level for a specific product SKU.
    Returns detailed inventory information including quantity, location, and status.
    """
    try:
        # Import here to handle potential import errors gracefully
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Clean the SKU (remove any extra whitespace/quotes)
        sku = sku.strip().strip('"\'')
        
        if not sku:
            return "Please provide a valid SKU to check inventory."
        
        # Get product information with inventory details
        product_response = (
            supabase
            .table("products")
            .select("""
                id, sku, name, price, category,
                inventory!inner(
                    quantity_in_stock, 
                    min_stock_level, 
                    max_stock_level,
                    location,
                    last_adjusted,
                    updated_at
                )
            """)
            .eq("sku", sku)
            .execute()
        )
        
        if not product_response.data:
            return f"Product with SKU '{sku}' not found in inventory. Please check the SKU and try again."
        
        product = product_response.data[0]
        inventory = product['inventory']
        
        # Determine stock status
        current_stock = inventory['quantity_in_stock']
        min_level = inventory['min_stock_level']
        max_level = inventory['max_stock_level']
        
        if current_stock <= 0:
            stock_status = "🔴 OUT OF STOCK"
        elif current_stock <= min_level:
            stock_status = "🟡 LOW STOCK"
        elif current_stock >= max_level:
            stock_status = "🔵 OVERSTOCK"
        else:
            stock_status = "🟢 IN STOCK"
        
        # Format the response
        result_lines = [
            f"📦 Inventory Status for {product['name']}",
            f"SKU: {product['sku']}",
            f"Category: {product.get('category', 'N/A')}",
            f"Price: ${product['price']:.2f}",
            "",
            f"📊 Stock Information:",
            f"  • Current Stock: {current_stock} units",
            f"  • Status: {stock_status}",
            f"  • Minimum Level: {min_level} units",
            f"  • Maximum Level: {max_level} units",
            f"  • Location: {inventory.get('location', 'Not specified')}",
            "",
            f"📅 Last Updated: {inventory['updated_at'][:19].replace('T', ' ')}"
        ]
        
        # Add additional warnings or recommendations
        if current_stock <= 0:
            result_lines.append("\n⚠️  URGENT: This product is out of stock. Immediate restocking required.")
        elif current_stock <= min_level:
            result_lines.append(f"\n⚠️  WARNING: Stock is below minimum level. Consider reordering soon.")
        elif current_stock >= max_level:
            result_lines.append(f"\n💡 INFO: Stock level is at or above maximum. Consider adjusting procurement.")
        
        # Calculate stock days (if we had sales velocity data)
        # For now, just show a general recommendation
        if min_level > 0:
            stock_ratio = current_stock / min_level
            if stock_ratio > 2:
                result_lines.append(f"📈 Stock appears healthy (Stock ratio: {stock_ratio:.1f}x minimum level)")
            elif stock_ratio < 1:
                result_lines.append(f"📉 Stock is critically low (Stock ratio: {stock_ratio:.1f}x minimum level)")
        
        return "\n".join(result_lines)
        
    except ImportError:
        return "Sorry, the inventory database connection is not configured. Please check your database setup."
    except Exception as e:
        return f"Sorry, I encountered an error while checking inventory for SKU '{sku}': {str(e)}. Please verify the SKU is correct and try again."

def _check_multiple_skus(sku_list: str) -> str:
    """
    Check inventory for multiple SKUs at once.
    Input should be comma-separated SKUs.
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Parse SKU list
        skus = [sku.strip().strip('"\'') for sku in sku_list.split(',') if sku.strip()]
        
        if not skus:
            return "Please provide valid SKUs separated by commas."
        
        if len(skus) > 10:
            return "Please limit your request to 10 SKUs at a time."
        
        # Get products with inventory details
        products_response = (
            supabase
            .table("products")
            .select("""
                sku, name, 
                inventory!inner(quantity_in_stock, min_stock_level)
            """)
            .in_("sku", skus)
            .execute()
        )
        
        if not products_response.data:
            return f"No products found for the provided SKUs: {', '.join(skus)}"
        
        # Create summary
        result_lines = [f"📦 Inventory Summary for {len(products_response.data)} products:", ""]
        
        found_skus = set()
        for product in products_response.data:
            inventory = product['inventory']
            current_stock = inventory['quantity_in_stock']
            min_level = inventory['min_stock_level']
            
            # Determine status
            if current_stock <= 0:
                status = "🔴 OUT OF STOCK"
            elif current_stock <= min_level:
                status = "🟡 LOW STOCK"
            else:
                status = "🟢 IN STOCK"
            
            result_lines.append(
                f"• {product['name']} ({product['sku']}): {current_stock} units - {status}"
            )
            found_skus.add(product['sku'])
        
        # List any SKUs that weren't found
        not_found = set(skus) - found_skus
        if not_found:
            result_lines.extend([
                "",
                f"⚠️  SKUs not found: {', '.join(not_found)}"
            ])
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error checking multiple SKUs: {str(e)}"

def _inventory_search_by_name(product_name: str) -> str:
    """
    Search for products by name and return their inventory status.
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Search products by name (case-insensitive)
        products_response = (
            supabase
            .table("products")
            .select("""
                sku, name, 
                inventory!inner(quantity_in_stock, min_stock_level)
            """)
            .ilike("name", f"%{product_name}%")
            .limit(5)
            .execute()
        )
        
        if not products_response.data:
            return f"No products found matching '{product_name}'. Try different keywords or check product SKUs."
        
        result_lines = [f"📦 Inventory for products matching '{product_name}':", ""]
        
        for product in products_response.data:
            inventory = product['inventory']
            current_stock = inventory['quantity_in_stock']
            min_level = inventory['min_stock_level']
            
            # Determine status
            if current_stock <= 0:
                status = "🔴 OUT OF STOCK"
            elif current_stock <= min_level:
                status = "🟡 LOW STOCK"
            else:
                status = "🟢 IN STOCK"
            
            result_lines.append(
                f"• {product['name']} ({product['sku']}): {current_stock} units - {status}"
            )
        
        return "\n".join(result_lines)
        
    except Exception as e:
        return f"Error searching inventory by name: {str(e)}"

def _inventory_handler(input_str: str) -> str:
    """
    Main inventory check handler that routes to appropriate sub-functions.
    Handles single SKU, multiple SKUs, or product name searches.
    """
    try:
        input_str = input_str.strip()
        
        if not input_str:
            return "Please provide a SKU, product name, or comma-separated list of SKUs to check."
        
        # Check if it's multiple SKUs (contains comma)
        if ',' in input_str:
            return _check_multiple_skus(input_str)
        
        # Check if it looks like a SKU (contains hyphens and/or numbers)
        if '-' in input_str or input_str.replace('-', '').replace('_', '').isalnum():
            return _check_inventory_stock(input_str)
        
        # Otherwise, treat as product name search
        return _inventory_search_by_name(input_str)
        
    except Exception as e:
        return f"Error processing inventory check: {str(e)}"

# Create the inventory check tool
inventory_check_tool = Tool(
    name="InventoryCheckTool",
    func=_inventory_handler,
    description="""
    Check inventory levels for products. Supports multiple input types:
    1. Single SKU: "SHOES-RED-001" 
    2. Multiple SKUs: "SHOES-RED-001,SHIRT-BLUE-002,JACKET-BLACK-003"
    3. Product name search: "red shoes" or "winter jacket"
    
    Returns detailed inventory information including current stock, status, 
    minimum/maximum levels, and recommendations.
    """
)