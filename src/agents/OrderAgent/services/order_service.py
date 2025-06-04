"""
Order Service Layer
Handles all order-related database operations with Supabase
"""
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class OrderService:
    """Service class for order management operations."""
    
    def __init__(self):
        """Initialize Supabase client."""        # Load environment variables first
        load_dotenv()
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def create_order(self, customer_email: str, customer_name: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new order with order items.
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's name
            items: List of order items with 'sku', 'product_name', 'quantity', 'unit_price'
        
        Returns:
            Dict with order details and order_id
        """
        try:
            # Calculate total amount
            total_amount = sum(Decimal(str(item['quantity'])) * Decimal(str(item['unit_price'])) for item in items)
            
            # Validate business rules
            if total_amount < Decimal('10.00'):
                raise ValueError(f"Order total ${total_amount} is below minimum order value of $10.00")
            
            if total_amount > Decimal('10000.00'):
                raise ValueError(f"Order total ${total_amount} exceeds maximum order value of $10,000.00")
            
            if len(items) > 50:
                raise ValueError(f"Order has {len(items)} items, exceeding maximum of 50 items per order")
            
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Create order record
            order_data = {
                'order_id': order_id,
                'customer_email': customer_email,
                'customer_name': customer_name,
                'status': 'pending',
                'total_amount': float(total_amount),
                'currency': 'USD',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Insert order
            order_result = self.supabase.table('orders').insert(order_data).execute()
            
            if not order_result.data:
                raise Exception("Failed to create order")
            
            # Create order items
            order_items_data = []
            for item in items:
                order_items_data.append({
                    'order_item_id': str(uuid.uuid4()),
                    'order_id': order_id,
                    'product_sku': item['sku'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'unit_price': float(item['unit_price']),
                    'line_total': float(Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))),
                    'created_at': datetime.utcnow().isoformat()
                })
            
            # Insert order items
            items_result = self.supabase.table('order_items').insert(order_items_data).execute()
            
            if not items_result.data:
                # Rollback order if items creation fails
                self.supabase.table('orders').delete().eq('order_id', order_id).execute()
                raise Exception("Failed to create order items")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'pending',
                'total_amount': float(total_amount),
                'items_count': len(items),
                'message': f"Order {order_id} created successfully"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to create order: {str(e)}"
            }
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status and details.
        
        Args:
            order_id: The order ID to check
        
        Returns:
            Dict with order details or error message
        """
        try:
            # Get order details
            order_result = self.supabase.table('orders').select('*').eq('order_id', order_id).execute()
            
            if not order_result.data:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': f"No order found with ID: {order_id}"
                }
            
            order = order_result.data[0]
            
            # Get order items
            items_result = self.supabase.table('order_items').select('*').eq('order_id', order_id).execute()
            
            return {
                'success': True,
                'order_id': order['order_id'],
                'status': order['status'],
                'customer_email': order['customer_email'],
                'customer_name': order['customer_name'],
                'total_amount': order['total_amount'],
                'currency': order['currency'],
                'created_at': order['created_at'],
                'updated_at': order['updated_at'],
                'items': items_result.data or [],
                'items_count': len(items_result.data or [])
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to get order status: {str(e)}"
            }
    
    def update_order_status(self, order_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update order status.
        
        Args:
            order_id: The order ID to update
            new_status: New status (pending, confirmed, processing, shipped, delivered, cancelled)
        
        Returns:
            Dict with success status and message
        """
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        
        if new_status not in valid_statuses:
            return {
                'success': False,
                'error': 'Invalid status',
                'message': f"Status must be one of: {', '.join(valid_statuses)}"
            }
        
        try:
            # Check if order exists
            order_check = self.supabase.table('orders').select('status').eq('order_id', order_id).execute()
            
            if not order_check.data:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': f"No order found with ID: {order_id}"
                }
            
            # Update order status
            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('orders').update(update_data).eq('order_id', order_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'order_id': order_id,
                    'new_status': new_status,
                    'message': f"Order {order_id} status updated to {new_status}"
                }
            else:
                return {
                    'success': False,
                    'error': 'Update failed',
                    'message': f"Failed to update order {order_id}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to update order status: {str(e)}"
            }
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order (only if not yet shipped).
        
        Args:
            order_id: The order ID to cancel
        
        Returns:
            Dict with success status and message
        """
        try:
            # Check current order status
            order_result = self.supabase.table('orders').select('status').eq('order_id', order_id).execute()
            
            if not order_result.data:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': f"No order found with ID: {order_id}"
                }
            
            current_status = order_result.data[0]['status']
            
            # Check if order can be cancelled
            if current_status in ['shipped', 'delivered', 'cancelled']:
                return {
                    'success': False,
                    'error': 'Cannot cancel order',
                    'message': f"Order {order_id} with status '{current_status}' cannot be cancelled"
                }
            
            # Update status to cancelled
            return self.update_order_status(order_id, 'cancelled')
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to cancel order: {str(e)}"
            }
    
    def validate_products(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that products exist and have sufficient stock.
        
        Args:
            items: List of items with 'sku' and 'quantity'
        
        Returns:
            Dict with validation results
        """
        try:
            validation_results = []
            all_valid = True
            
            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                
                # Check if product exists
                product_result = self.supabase.table('products').select('*').eq('sku', sku).execute()
                
                if not product_result.data:
                    validation_results.append({
                        'sku': sku,
                        'valid': False,
                        'error': 'Product not found'
                    })
                    all_valid = False
                    continue
                
                product = product_result.data[0]
                
                # Check stock availability
                if product.get('stock_quantity', 0) < quantity:
                    validation_results.append({
                        'sku': sku,
                        'valid': False,
                        'error': f"Insufficient stock. Available: {product.get('stock_quantity', 0)}, Requested: {quantity}"
                    })
                    all_valid = False
                else:
                    validation_results.append({
                        'sku': sku,
                        'valid': True,
                        'product_name': product.get('name'),
                        'unit_price': product.get('price'),
                        'available_stock': product.get('stock_quantity', 0)
                    })
            
            return {
                'all_valid': all_valid,
                'results': validation_results
            }
            
        except Exception as e:
            return {
                'all_valid': False,
                'error': str(e),
                'results': []
            }
