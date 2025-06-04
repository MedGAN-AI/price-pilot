"""
Order Service Layer - Fixed for Actual Database Schema
Handles all order-related database operations with Supabase
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class OrderService:
    """Service class for order management operations."""
    
    def __init__(self):
        """Initialize Supabase client and logger."""
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def create_order(self, customer_email: str, customer_name: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new order with order items following actual database schema.
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's name
            items: List of order items with 'sku', 'product_name', 'quantity', 'unit_price', 'product_id'
        
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
            
            # Find or create user
            user = self._find_or_create_user(customer_email, customer_name)
            if not user:
                raise Exception("Failed to find or create user")
            
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Create order record using actual database schema
            order_data = {
                'id': order_id,
                'user_id': user['id'],
                'order_date': datetime.utcnow().isoformat(),
                'total_amount': float(total_amount),
                'status': 'pending',
                'shipping_address': 'TBD - Address collection needed',  # Placeholder
                'billing_address': 'TBD - Address collection needed',   # Placeholder
                'payment_method': 'credit_card',  # Default
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Insert order
            order_result = self.supabase.table('orders').insert(order_data).execute()
            
            if not order_result.data:
                raise Exception("Failed to create order")
            
            # Create order items using actual schema (product_id, not sku)
            order_items_data = []
            for item in items:
                order_items_data.append({
                    'id': str(uuid.uuid4()),
                    'order_id': order_id,
                    'product_id': item['product_id'],  # Use product_id from validation
                    'quantity': item['quantity'],
                    'unit_price': float(item['unit_price']),
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                })
            
            # Insert order items
            items_result = self.supabase.table('order_items').insert(order_items_data).execute()
            
            if not items_result.data:
                # Rollback order if items creation fails
                self.supabase.table('orders').delete().eq('id', order_id).execute()
                raise Exception("Failed to create order items")
            
            return {
                'success': True,
                'order_id': order_id,
                'status': 'pending',
                'total_amount': float(total_amount),
                'items_count': len(items),
                'customer_email': customer_email,
                'customer_name': customer_name,
                'message': f"Order {order_id} created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to create order: {str(e)}"
            }
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status and details using actual database schema.
        
        Args:
            order_id: The order ID to check
        
        Returns:
            Dict with order details or error message
        """
        try:
            # Get order details with user information
            order_result = self.supabase.table('orders').select('''
                id, order_date, total_amount, status, shipping_address, 
                billing_address, payment_method, created_at, updated_at,
                users!inner(full_name, email)
            ''').eq('id', order_id).execute()
            
            if not order_result.data:
                return {
                    'success': False,
                    'error': 'Order not found',
                    'message': f"No order found with ID: {order_id}"
                }
            
            order = order_result.data[0]
            
            # Get order items with product details
            items_result = self.supabase.table('order_items').select('''
                quantity, unit_price,
                products!inner(sku, name)
            ''').eq('order_id', order_id).execute()
            
            return {
                'success': True,
                'order_id': order['id'],
                'status': order['status'],
                'customer_email': order['users']['email'],
                'customer_name': order['users']['full_name'],
                'total_amount': order['total_amount'],
                'order_date': order['order_date'],
                'shipping_address': order['shipping_address'],
                'billing_address': order['billing_address'],
                'payment_method': order['payment_method'],
                'created_at': order['created_at'],
                'updated_at': order['updated_at'],
                'items': [
                    {
                        'sku': item['products']['sku'],
                        'product_name': item['products']['name'],
                        'quantity': item['quantity'],
                        'unit_price': item['unit_price'],
                        'line_total': item['quantity'] * item['unit_price']
                    }
                    for item in items_result.data
                ],
                'items_count': len(items_result.data or [])
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order status: {str(e)}")
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
            order_check = self.supabase.table('orders').select('status').eq('id', order_id).execute()
            
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
            
            result = self.supabase.table('orders').update(update_data).eq('id', order_id).execute()
            
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
            self.logger.error(f"Error updating order status: {str(e)}")
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
            order_result = self.supabase.table('orders').select('status').eq('id', order_id).execute()
            
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
            self.logger.error(f"Error cancelling order: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to cancel order: {str(e)}"
            }
    
    def validate_products(self, items: List[Dict]) -> Dict:
        """
        Validate that all products exist and have sufficient stock
        """
        try:
            results = []
            all_valid = True
            
            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 1)
                
                # Get product details - use 'name' column, not 'product_name'
                product_response = self.supabase.table('products').select(
                    'id, sku, name, price'
                ).eq('sku', sku).execute()
                
                if not product_response.data:
                    results.append({
                        'sku': sku,
                        'valid': False,
                        'error': 'Product not found'
                    })
                    all_valid = False
                    continue
                
                product = product_response.data[0]
                
                # Check inventory
                inventory_response = self.supabase.table('inventory').select(
                    'quantity_in_stock'
                ).eq('product_id', product['id']).execute()
                
                if not inventory_response.data:
                    # If no inventory record, assume unlimited stock for now
                    stock = 999999
                else:
                    stock = inventory_response.data[0]['quantity_in_stock']
                
                if stock < quantity:
                    results.append({
                        'sku': sku,
                        'valid': False,
                        'error': f'Insufficient stock. Available: {stock}, Requested: {quantity}'
                    })
                    all_valid = False
                else:
                    results.append({
                        'sku': sku,
                        'valid': True,
                        'product_id': product['id'],  # Add product_id for order_items
                        'product_name': product['name'],  # Use 'name' from database
                        'unit_price': float(product['price']),
                        'available_stock': stock
                    })
            
            return {
                'all_valid': all_valid,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Error validating products: {str(e)}")
            return {
                'all_valid': False,
                'error': str(e)
            }
    
    def _find_or_create_user(self, email: str, full_name: str) -> Optional[Dict]:
        """
        Find existing user by email or create a new one.
        
        Args:
            email: User's email address
            full_name: User's full name
        
        Returns:
            User record or None if creation fails
        """
        try:
            # Try to find existing user
            user_response = self.supabase.table('users').select('id, email, full_name').eq('email', email).execute()
            
            if user_response.data:
                return user_response.data[0]
            
            # Create new user
            user_data = {
                'id': str(uuid.uuid4()),
                'email': email,
                'full_name': full_name,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            create_response = self.supabase.table('users').insert(user_data).execute()
            
            if create_response.data:
                return create_response.data[0]
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error finding/creating user: {str(e)}")
            return None
