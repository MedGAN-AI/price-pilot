from langchain_core.tools import Tool
import json
import re
from datetime import datetime
from typing import Dict, Optional

def _update_inventory_stock(sku: str, quantity: int, operation: str = "set", reason: str = "Manual update") -> str:
    """
    Update inventory stock for a specific SKU.
    
    Args:
        sku: Product SKU
        quantity: Quantity to set/add/subtract
        operation: "set", "add", or "subtract"
        reason: Reason for the update (for audit trail)
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Clean the SKU
        sku = sku.strip().strip('"\'')
        
        if not sku:
            return "Please provide a valid SKU to update inventory."
        
        if quantity < 0 and operation in ["set", "add"]:
            return f"Invalid quantity {quantity} for operation '{operation}'. Quantity must be non-negative."
        
        # First, get current inventory information
        product_response = (
            supabase
            .table("products")
            .select("""
                id, sku, name,
                inventory!inner(
                    id, quantity_in_stock, min_stock_level, max_stock_level, location
                )
            """)
            .eq("sku", sku)
            .execute()
        )
        
        if not product_response.data:
            return f"Product with SKU '{sku}' not found in inventory. Please check the SKU and try again."
        
        product = product_response.data[0]
        inventory = product['inventory']
        current_stock = inventory['quantity_in_stock']
        inventory_id = inventory['id']
        
        # Calculate new stock level based on operation
        if operation.lower() == "set":
            new_stock = quantity
        elif operation.lower() == "add":
            new_stock = current_stock + quantity
        elif operation.lower() == "subtract":
            new_stock = max(0, current_stock - quantity)  # Don't allow negative stock
        else:
            return f"Invalid operation '{operation}'. Use 'set', 'add', or 'subtract'."
        
        # Update the inventory
        update_response = (
            supabase
            .table("inventory")
            .update({
                "quantity_in_stock": new_stock,
                "last_adjusted": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
            .eq("id", inventory_id)
            .execute()
        )
        
        if not update_response.data:
            return f"Failed to update inventory for SKU '{sku}'. Please try again."
        
        # Create audit log entry
        try:
            audit_response = (
                supabase
                .table("inventory_audit")
                .insert({
                    "product_id": product['id'],
                    "sku": sku,
                    "old_quantity": current_stock,
                    "new_quantity": new_stock,
                    "change_quantity": new_stock - current_stock,
                    "operation": operation,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": "system"  # Could be replaced with actual user ID
                })
                .execute()
            )
        except Exception as audit_error:
            # Don't fail the update if audit logging fails
            print(f"Warning: Failed to create audit log: {audit_error}")
        
        # Determine new stock status
        min_level = inventory['min_stock_level']
        max_level = inventory['max_stock_level']
        
        if new_stock <= 0:
            status = "🔴 OUT OF STOCK"
            alert = "⚠️  URGENT: This product is now out of stock!"
        elif new_stock <= min_level:
            status = "🟡 LOW STOCK"
            alert = f"⚠️  WARNING: Stock is now below minimum level ({min_level} units)."
        elif new_stock >= max_level:
            status = "🔵 OVERSTOCK"
            alert = f"💡 INFO: Stock is now at or above maximum level ({max_level} units)."
        else:
            status = "🟢 IN STOCK"
            alert = "✅ Stock level is healthy."
        
        # Format response
        result_lines = [
            f"✅ Inventory Updated Successfully",
            f"Product: {product['name']} ({sku})",
            f"Operation: {operation.title()} {abs(quantity)} units",
            "",
            f"📊 Stock Changes:",
            f"  • Previous Stock: {current_stock} units",
            f"  • New Stock: {new_stock} units",
            f"  • Change: {'+' if new_stock > current_stock else ''}{new_stock - current_stock} units",
            f"  • Status: {status}",
            "",
            f"📍 Location: {inventory.get('location', 'Not specified')}",
            f"🕒 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            alert
        ]
        
        # Add recommendations based on new stock level
        if new_stock <= 0:
            result_lines.extend([
                "",
                "💡 Recommendations:",
                "  • Mark product as unavailable for new orders",
                "  • Contact suppliers for emergency restocking",
                "  • Notify customers about backorder status"
            ])
        elif new_stock <= min_level:
            result_lines.extend([
                "",
                "💡 Recommendations:",
                "  • Schedule restocking within 24-48 hours",
                "  • Monitor sales velocity closely",
                "  • Consider safety stock adjustments"
            ])
        
        return "\n".join(result_lines)
        
    except ImportError:
        return "Sorry, the inventory database connection is not configured. Please check your database setup."
    except Exception as e:
        return f"Sorry, I encountered an error while updating inventory for SKU '{sku}': {str(e)}. Please try again."

def _bulk_inventory_update(updates_data: str) -> str:
    """
    Update inventory for multiple SKUs at once.
    Expected format: "SKU1:operation:quantity,SKU2:operation:quantity"
    Example: "SHOES-001:add:50,SHIRT-002:set:100"
    """
    try:
        from integrations.supabase_client import supabase
        
        if not supabase:
            return "Sorry, the inventory system is currently unavailable. Please try again later."
        
        # Parse the updates data
        updates = []
        for update_str in updates_data.split(','):
            parts = update_str.strip().split(':')
            if len(parts) == 3:
                sku, operation, quantity_str = parts
                try:
                    quantity = int(quantity_str.strip())
                    updates.append({
                        'sku': sku.strip(),
                        'operation': operation.strip(),
                        'quantity': quantity
                    })
                except ValueError:
                    return f"Invalid quantity '{quantity_str}' for SKU '{sku}'. Must be a number."
            else:
                return f"Invalid format for update: '{update_str}'. Use 'SKU:operation:quantity' format."
        
        if not updates:
            return "No valid updates provided. Use format: 'SKU:operation:quantity,SKU:operation:quantity'"
        
        if len(updates) > 20:
            return "Please limit bulk updates to 20 items at a time."
        
        # Process each update
        results = []
        successful_updates = 0
        failed_updates = 0
        
        for update in updates:
            try:
                result = _update_inventory_stock(
                    update['sku'], 
                    update['quantity'], 
                    update['operation'],
                    "Bulk update operation"
                )
                
                if "✅ Inventory Updated Successfully" in result:
                    successful_updates += 1
                    results.append(f"✅ {update['sku']}: {update['operation']} {update['quantity']} units")
                else:
                    failed_updates += 1
                    results.append(f"❌ {update['sku']}: Update failed")
            except Exception as e:
                failed_updates += 1
                results.append(f"❌ {update['sku']}: Error - {str(e)}")
        
        # Summary
        summary_lines = [
            f"📦 Bulk Inventory Update Results",
            f"Total Updates: {len(updates)} | Successful: {successful_updates} | Failed: {failed_updates}",
            "=" * 50,
            ""
        ]
        
        summary_lines.extend(results)
        
        if failed_updates > 0:
            summary_lines.extend([
                "",
                "⚠️  Some updates failed. Please check the SKUs and try again for failed items."
            ])
        
        return "\n".join(summary_lines)
        
    except Exception as e:
        return f"Error processing bulk inventory update: {str(e)}"

def _inventory_adjustment(sku: str, adjustment_data: str) -> str:
    """
    Make inventory adjustments with detailed reasoning.
    Format: "reason:Damaged goods,quantity:-5" or "reason:Found stock,quantity:+10"
    """
    try:
        # Parse adjustment data
        adjustment_info = {}
        for part in adjustment_data.split(','):
            if ':' in part:
                key, value = part.split(':', 1)
                adjustment_info[key.strip().lower()] = value.strip()
        
        reason = adjustment_info.get('reason', 'Inventory adjustment')
        quantity_str = adjustment_info.get('quantity', '0')
        
        # Parse quantity (handle + and - signs)
        if quantity_str.startswith('+'):
            operation = 'add'
            quantity = int(quantity_str[1:])
        elif quantity_str.startswith('-'):
            operation = 'subtract'
            quantity = int(quantity_str[1:])
        else:
            # If no sign, treat as absolute set
            operation = 'set'
            quantity = int(quantity_str)
        
        return _update_inventory_stock(sku, quantity, operation, reason)
        
    except ValueError as e:
        return f"Invalid quantity format. Use +N for additions, -N for subtractions, or N for absolute values."
    except Exception as e:
        return f"Error processing inventory adjustment: {str(e)}"

def _inventory_update_handler(input_str: str) -> str:
    """
    Main inventory update handler that routes to appropriate sub-functions.
    Handles different update formats and operations.
    """
    try:
        input_str = input_str.strip()
        
        if not input_str:
            return "Please provide update information. Examples: 'SKU123:set:100' or 'SKU123 add 50 units'"
        
        # Check for bulk update format (contains commas with colons)
        if ',' in input_str and ':' in input_str:
            return _bulk_inventory_update(input_str)
        
        # Check for adjustment format (contains reason)
        if 'reason:' in input_str.lower():
            # Extract SKU and adjustment data
            parts = input_str.split(' ', 1)
            if len(parts) >= 2:
                sku = parts[0]
                adjustment_data = parts[1]
                return _inventory_adjustment(sku, adjustment_data)
        
        # Parse single update formats
        # Format 1: "SKU:operation:quantity"
        if input_str.count(':') == 2:
            sku, operation, quantity_str = input_str.split(':')
            try:
                quantity = int(quantity_str.strip())
                return _update_inventory_stock(sku.strip(), quantity, operation.strip())
            except ValueError:
                return f"Invalid quantity '{quantity_str}'. Must be a number."
        
        # Format 2: "SKU operation quantity" (natural language)
        parts = input_str.split()
        if len(parts) >= 3:
            sku = parts[0]
            operation_word = parts[1].lower()
            
            # Map natural language to operations
            operation_map = {
                'set': 'set', 'update': 'set', 'change': 'set',
                'add': 'add', 'increase': 'add', 'plus': 'add',
                'subtract': 'subtract', 'decrease': 'subtract', 'minus': 'subtract', 'remove': 'subtract'
            }
            
            operation = operation_map.get(operation_word, 'set')
            
            # Extract quantity from remaining parts
            quantity_str = ' '.join(parts[2:])
            # Remove common words like 'to', 'by', 'units'
            quantity_str = re.sub(r'\b(to|by|units?|items?)\b', '', quantity_str).strip()
            
            try:
                quantity = int(quantity_str)
                return _update_inventory_stock(sku, quantity, operation)
            except ValueError:
                return f"Could not parse quantity from '{quantity_str}'. Please use a clear number."
        
        return """
Invalid update format. Please use one of these formats:
1. SKU:operation:quantity (e.g., "SHOES-001:add:50")
2. SKU operation quantity (e.g., "SHOES-001 add 50")
3. SKU reason:description,quantity:±N (e.g., "SHOES-001 reason:Damaged,quantity:-5")
4. Bulk: SKU1:op:qty,SKU2:op:qty (e.g., "SHOES-001:add:50,SHIRT-002:set:100")

Operations: set, add, subtract (or increase, decrease, etc.)
        """.strip()
        
    except Exception as e:
        return f"Error processing inventory update: {str(e)}"

# Create the inventory update tool
inventory_update_tool = Tool(
    name="InventoryUpdateTool",
    func=_inventory_update_handler,
    description="""
    Update inventory stock levels for products. Supports multiple formats:
    1. Single update: "SKU:operation:quantity" (e.g., "SHOES-001:add:50")
    2. Natural language: "SKU operation quantity" (e.g., "SHOES-001 add 50 units")
    3. Adjustment with reason: "SKU reason:description,quantity:±N"
    4. Bulk updates: "SKU1:op:qty,SKU2:op:qty" (comma-separated)
    
    Operations: set (absolute), add (increase), subtract (decrease)
    Includes audit logging and stock level validation with recommendations.
    """
)