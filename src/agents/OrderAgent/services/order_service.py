"""
Order Service Layer - Bulletproof Database Schema Implementation
Handles all order-related database operations with Supabase using modern Python approaches
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal, ROUND_HALF_UP
from contextlib import contextmanager

from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel, Field, EmailStr, validator, ValidationError

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type-safe data models matching exact Supabase schema
class OrderItemCreate(BaseModel):
    """Validated order item for creation"""
    sku: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., gt=0, le=1000)
    
    @validator('sku')
    def validate_sku(cls, v):
        return v.strip().upper()

class OrderItemValidated(BaseModel):
    """Validated order item with product details"""
    sku: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    
    class Config:
        arbitrary_types_allowed = True

class UserCreate(BaseModel):
    """User creation model"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=20)

class OrderCreate(BaseModel):
    """Order creation model matching database schema"""
    user_id: str
    total_amount: Decimal
    shipping_address: str = Field(..., min_length=10, max_length=500)
    billing_address: str = Field(..., min_length=10, max_length=500)
    payment_method: Optional[str] = Field(None, max_length=50)
    
    class Config:
        arbitrary_types_allowed = True

class OrderService:
    """Service class for order management operations with bulletproof data handling."""
    
    # Business rules constants
    MIN_ORDER_VALUE = Decimal('10.00')
    MAX_ORDER_VALUE = Decimal('10000.00')
    MAX_ITEMS_PER_ORDER = 50
    VALID_ORDER_STATUSES = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
    NON_CANCELLABLE_STATUSES = ['shipped', 'delivered', 'cancelled']
    
    def __init__(self):
        """Initialize Supabase client and logger."""
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.logger.info("OrderService initialized successfully")
    
    @contextmanager
    def _error_handler(self, operation: str):
        """Context manager for consistent error handling and logging."""
        try:
            yield
        except ValidationError as e:
            self.logger.error(f"Validation error in {operation}: {e}")
            raise ValueError(f"Invalid input data: {e}")
        except Exception as e:
            self.logger.error(f"Error in {operation}: {str(e)}")
            raise
    
    def _normalize_decimal(self, value: Union[str, int, float, Decimal]) -> Decimal:
        """Safely convert to Decimal with proper rounding for financial calculations."""
        try:
            decimal_value = Decimal(str(value))
            return decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric value: {value}") from e
    
    def _validate_uuid(self, uuid_str: str, field_name: str) -> str:
        """Validate UUID format."""
        try:
            uuid.UUID(uuid_str)
            return uuid_str
        except ValueError:
            raise ValueError(f"Invalid UUID format for {field_name}: {uuid_str}")
    
    def _get_utc_timestamp(self) -> str:
        """Get UTC timestamp in ISO format for database storage."""
        return datetime.now(timezone.utc).isoformat()
    
    def create_order(self, customer_email: str, customer_name: str, items: List[Dict[str, Any]], 
                    shipping_address: str = "TBD - Address collection needed",
                    billing_address: str = "TBD - Address collection needed",
                    payment_method: str = "credit_card") -> Dict[str, Any]:
        """
        Create a new order with order items following exact database schema.
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's full name
            items: List of order items with 'sku' and 'quantity' fields
            shipping_address: Shipping address (required by database)
            billing_address: Billing address (required by database)
            payment_method: Payment method (optional)
        
        Returns:
            Dict with order details and order_id
        """
        with self._error_handler("create_order"):
            # Validate inputs
            if not customer_email or not customer_name:
                return {
                    'success': False,
                    'error': 'Missing required customer information',
                    'message': 'Customer email and name are required'
                }
            
            if not items or not isinstance(items, list):
                return {
                    'success': False,
                    'error': 'Invalid items',
                    'message': 'Items must be a non-empty list'
                }
            
            # Validate business rules
            if len(items) > self.MAX_ITEMS_PER_ORDER:
                return {
                    'success': False,
                    'error': 'Too many items',
                    'message': f"Order has {len(items)} items, exceeding maximum of {self.MAX_ITEMS_PER_ORDER} items per order"
                }
            
            # Validate and enrich items with product data
            validation_result = self.validate_products(items)
            
            if not validation_result['all_valid']:
                invalid_items = [r for r in validation_result['results'] if not r['valid']]
                return {
                    'success': False,
                    'error': 'Product validation failed',
                    'message': 'Some products are invalid or out of stock',
                    'invalid_items': invalid_items
                }
            
            # Calculate total amount using Decimal for precision
            validated_items = validation_result['results']
            total_amount = sum(
                self._normalize_decimal(item['quantity']) * self._normalize_decimal(item['unit_price'])
                for item in validated_items
            )
            
            # Validate total amount
            if total_amount < self.MIN_ORDER_VALUE:
                return {
                    'success': False,
                    'error': 'Order value too low',
                    'message': f"Order total ${total_amount} is below minimum order value of ${self.MIN_ORDER_VALUE}"
                }
            
            if total_amount > self.MAX_ORDER_VALUE:
                return {
                    'success': False,
                    'error': 'Order value too high',
                    'message': f"Order total ${total_amount} exceeds maximum order value of ${self.MAX_ORDER_VALUE}"
                }
            
            # Find or create user
            user = self._find_or_create_user(customer_email, customer_name)
            if not user:
                return {
                    'success': False,
                    'error': 'User creation failed',
                    'message': 'Failed to find or create customer account'
                }
            
            # Generate UUIDs
            order_id = str(uuid.uuid4())
            timestamp = self._get_utc_timestamp()
            
            # Create order record matching exact database schema
            order_data = {
                'id': order_id,
                'user_id': user['id'],
                'order_date': timestamp,
                'total_amount': float(total_amount),  # Convert to float for JSON serialization
                'status': 'pending',
                'shipping_address': shipping_address,
                'billing_address': billing_address,
                'payment_method': payment_method,
                'created_at': timestamp,
                'updated_at': timestamp
            }
            
            try:
                # Insert order (database will auto-generate timestamps if not provided)
                order_result = self.supabase.table('orders').insert(order_data).execute()
                
                if not order_result.data:
                    raise Exception("Failed to create order record")
                
                # Create order items using exact schema
                order_items_data = []
                for item in validated_items:
                    item_data = {
                        'id': str(uuid.uuid4()),
                        'order_id': order_id,
                        'product_id': item['product_id'],
                        'quantity': int(item['quantity']),
                        'unit_price': float(self._normalize_decimal(item['unit_price'])),
                        'created_at': timestamp,
                        'updated_at': timestamp
                    }
                    order_items_data.append(item_data)
                
                # Insert order items
                items_result = self.supabase.table('order_items').insert(order_items_data).execute()
                
                if not items_result.data:
                    # Rollback order if items creation fails
                    self.supabase.table('orders').delete().eq('id', order_id).execute()
                    raise Exception("Failed to create order items")
                
                # Update inventory (decrement stock)
                self._update_inventory_for_order(validated_items, decrease=True)
                
                self.logger.info(f"Order {order_id} created successfully for {customer_email}")
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'status': 'pending',
                    'total_amount': float(total_amount),
                    'items_count': len(validated_items),
                    'customer_email': customer_email,
                    'customer_name': customer_name,
                    'message': f"Order {order_id} created successfully",
                    'items': [
                        {
                            'sku': item['sku'],
                            'product_name': item['product_name'],
                            'quantity': item['quantity'],
                            'unit_price': float(item['unit_price']),
                            'line_total': float(item['quantity'] * self._normalize_decimal(item['unit_price']))
                        }
                        for item in validated_items
                    ]
                }
                
            except Exception as e:
                self.logger.error(f"Failed to create order: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"Failed to create order: {str(e)}"
                }
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get order status and details using exact database schema.
        
        Args:
            order_id: The order ID to check
        
        Returns:
            Dict with order details or error message
        """
        with self._error_handler("get_order_status"):
            # Validate UUID format
            self._validate_uuid(order_id, "order_id")
            
            try:
                # Get order details with user information using exact column names
                order_result = self.supabase.table('orders').select('''
                    id, order_date, total_amount, status, shipping_address, 
                    billing_address, payment_method, created_at, updated_at,
                    users!inner(full_name, email, phone_number)
                ''').eq('id', order_id).execute()
                
                if not order_result.data:
                    return {
                        'success': False,
                        'error': 'Order not found',
                        'message': f"No order found with ID: {order_id}"
                    }
                
                order = order_result.data[0]
                
                # Get order items with product details using exact column names
                items_result = self.supabase.table('order_items').select('''
                    quantity, unit_price,
                    products!inner(sku, name, description, category)
                ''').eq('order_id', order_id).execute()
                
                return {
                    'success': True,
                    'order_id': order['id'],
                    'status': order['status'],
                    'customer_email': order['users']['email'],
                    'customer_name': order['users']['full_name'],
                    'customer_phone': order['users'].get('phone_number'),
                    'total_amount': float(order['total_amount']),
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
                            'product_description': item['products'].get('description'),
                            'product_category': item['products'].get('category'),
                            'quantity': item['quantity'],
                            'unit_price': float(item['unit_price']),
                            'line_total': float(item['quantity'] * Decimal(str(item['unit_price'])))
                        }
                        for item in items_result.data or []
                    ],
                    'items_count': len(items_result.data or [])
                }
                
            except Exception as e:
                self.logger.error(f"Error getting order status for {order_id}: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"Failed to get order status: {str(e)}"
                }
    
    def update_order_status(self, order_id: str, new_status: str) -> Dict[str, Any]:
        """
        Update order status with validation.
        
        Args:
            order_id: The order ID to update
            new_status: New status (must be in VALID_ORDER_STATUSES)
        
        Returns:
            Dict with success status and message
        """
        with self._error_handler("update_order_status"):
            # Validate inputs
            self._validate_uuid(order_id, "order_id")
            
            if new_status not in self.VALID_ORDER_STATUSES:
                return {
                    'success': False,
                    'error': 'Invalid status',
                    'message': f"Status must be one of: {', '.join(self.VALID_ORDER_STATUSES)}"
                }
            
            try:
                # Check if order exists and get current status
                order_check = self.supabase.table('orders').select('status').eq('id', order_id).execute()
                
                if not order_check.data:
                    return {
                        'success': False,
                        'error': 'Order not found',
                        'message': f"No order found with ID: {order_id}"
                    }
                
                current_status = order_check.data[0]['status']
                
                # Business rule: Can't change status from shipped/delivered back to earlier status
                status_hierarchy = ['pending', 'confirmed', 'processing', 'shipped', 'delivered']
                if (current_status in status_hierarchy and new_status in status_hierarchy and
                    status_hierarchy.index(new_status) < status_hierarchy.index(current_status) and
                    new_status != 'cancelled'):
                    return {
                        'success': False,
                        'error': 'Invalid status transition',
                        'message': f"Cannot change status from '{current_status}' to '{new_status}'"
                    }
                
                # Update order status with timestamp
                update_data = {
                    'status': new_status,
                    'updated_at': self._get_utc_timestamp()
                }
                
                result = self.supabase.table('orders').update(update_data).eq('id', order_id).execute()
                
                if result.data:
                    self.logger.info(f"Order {order_id} status updated from '{current_status}' to '{new_status}'")
                    return {
                        'success': True,
                        'order_id': order_id,
                        'old_status': current_status,
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
                self.logger.error(f"Error updating order status for {order_id}: {str(e)}")
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
        with self._error_handler("cancel_order"):
            self._validate_uuid(order_id, "order_id")
            
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
                if current_status in self.NON_CANCELLABLE_STATUSES:
                    return {
                        'success': False,
                        'error': 'Cannot cancel order',
                        'message': f"Order {order_id} with status '{current_status}' cannot be cancelled"
                    }
                
                # Get order items for inventory restoration
                items_result = self.supabase.table('order_items').select('''
                    product_id, quantity,
                    products!inner(sku, name)
                ''').eq('order_id', order_id).execute()
                
                # Update status to cancelled
                cancel_result = self.update_order_status(order_id, 'cancelled')
                
                if cancel_result['success']:
                    # Restore inventory
                    inventory_items = [
                        {
                            'sku': item['products']['sku'],
                            'product_id': item['product_id'],
                            'product_name': item['products']['name'],
                            'quantity': item['quantity']
                        }
                        for item in items_result.data or []
                    ]
                    
                    self._update_inventory_for_order(inventory_items, decrease=False)
                    
                    self.logger.info(f"Order {order_id} cancelled and inventory restored")
                
                return cancel_result
                
            except Exception as e:
                self.logger.error(f"Error cancelling order {order_id}: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"Failed to cancel order: {str(e)}"
                }
    
    def validate_products(self, items: List[Dict]) -> Dict[str, Any]:
        """
        Validate that all products exist and have sufficient stock using exact schema.
        
        Args:
            items: List of items with 'sku' and 'quantity' fields
        
        Returns:
            Dict with validation results
        """
        with self._error_handler("validate_products"):
            results = []
            all_valid = True
            
            for item in items:
                sku = item.get('sku', '').strip().upper()
                quantity = item.get('quantity', 1)
                
                if not sku:
                    results.append({
                        'sku': '',
                        'valid': False,
                        'error': 'SKU is required'
                    })
                    all_valid = False
                    continue
                
                try:
                    quantity = int(quantity)
                    if quantity <= 0:
                        raise ValueError("Quantity must be positive")
                except (ValueError, TypeError):
                    results.append({
                        'sku': sku,
                        'valid': False,
                        'error': f'Invalid quantity: {quantity}'
                    })
                    all_valid = False
                    continue
                
                # Get product details using exact column names
                product_response = self.supabase.table('products').select(
                    'id, sku, name, description, price, category'
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
                
                # Check inventory using exact schema
                inventory_response = self.supabase.table('inventory').select(
                    'quantity_in_stock, last_adjusted'
                ).eq('product_id', product['id']).execute()
                
                if not inventory_response.data:
                    # No inventory record - treat as out of stock
                    results.append({
                        'sku': sku,
                        'valid': False,
                        'error': 'No inventory record found'
                    })
                    all_valid = False
                    continue
                
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
                        'product_id': product['id'],
                        'product_name': product['name'],
                        'product_description': product.get('description'),
                        'product_category': product.get('category'),
                        'unit_price': float(product['price']),
                        'quantity': quantity,
                        'available_stock': stock,
                        'line_total': quantity * float(product['price'])
                    })
            
            return {
                'all_valid': all_valid,
                'results': results,
                'total_items': len(items),
                'valid_items': len([r for r in results if r['valid']])
            }
    
    def _update_inventory_for_order(self, items: List[Dict], decrease: bool = True):
        """
        Update inventory quantities for order items.
        
        Args:
            items: List of items with product_id and quantity
            decrease: If True, decrease stock; if False, increase (for cancellations)
        """
        try:
            timestamp = self._get_utc_timestamp()
            
            for item in items:
                product_id = item['product_id']
                quantity = int(item['quantity'])
                adjustment = -quantity if decrease else quantity                # Update inventory with atomic RPC operation
                self.supabase.rpc('update_inventory_stock', {
                    'p_product_id': product_id,
                    'p_adjustment': adjustment,
                    'p_timestamp': timestamp
                }).execute()
                
            action = "decreased" if decrease else "increased"
            self.logger.info(f"Inventory {action} for {len(items)} products")
            
        except Exception as e:
            self.logger.error(f"Error updating inventory: {str(e)}")
            # Don't raise exception to avoid blocking order creation
    
    def _find_or_create_user(self, email: str, full_name: str) -> Optional[Dict]:
        """
        Find existing user by email or create a new one using exact schema.
        
        Args:
            email: User's email address
            full_name: User's full name
        
        Returns:
            User record or None if creation fails
        """
        try:
            # Validate email format
            try:
                UserCreate(email=email, full_name=full_name)
            except ValidationError as e:
                self.logger.error(f"Invalid user data: {e}")
                return None
            
            # Try to find existing user
            user_response = self.supabase.table('users').select(
                'id, email, full_name, phone_number'
            ).eq('email', email.lower()).execute()
            
            if user_response.data:
                return user_response.data[0]
            
            # Create new user with exact schema
            user_data = {
                'id': str(uuid.uuid4()),
                'email': email.lower(),
                'full_name': full_name.strip(),
                'phone_number': None,  # Optional field
                'created_at': self._get_utc_timestamp(),
                'updated_at': self._get_utc_timestamp()
            }
            
            create_response = self.supabase.table('users').insert(user_data).execute()
            
            if create_response.data:
                self.logger.info(f"Created new user: {email}")
                return create_response.data[0]
            else:
                self.logger.error(f"Failed to create user: {email}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error finding/creating user {email}: {str(e)}")
            return None
    
    def get_available_products(self, limit: int = 20, category: str = None) -> Dict[str, Any]:
        """
        Get list of available products to help customers discover what they can order.
        
        Args:
            limit: Maximum number of products to return (default 20)
            category: Optional category filter
        
        Returns:
            Dict with products list and metadata
        """
        with self._error_handler("get_available_products"):
            try:
                # Build query
                query = self.supabase.table('products').select(
                    'sku, name, description, price, category'
                )
                
                # Add category filter if specified
                if category:
                    query = query.eq('category', category.strip())
                
                # Execute query with limit
                response = query.limit(limit).execute()
                
                if response.data:
                    # Format products for display
                    products = []
                    for product in response.data:
                        products.append({
                            'sku': product['sku'],
                            'name': product['name'],
                            'description': product['description'],
                            'price': f"${float(product['price']):.2f}",
                            'category': product['category']
                        })
                    
                    return {
                        'success': True,
                        'products': products,
                        'count': len(products),
                        'message': f"Found {len(products)} available products" + (f" in category '{category}'" if category else "")
                    }
                else:
                    return {
                        'success': True,
                        'products': [],
                        'count': 0,
                        'message': "No products found" + (f" in category '{category}'" if category else "")
                    }
                    
            except Exception as e:
                self.logger.error(f"Error fetching available products: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'message': f"Failed to fetch products: {str(e)}"
                }
