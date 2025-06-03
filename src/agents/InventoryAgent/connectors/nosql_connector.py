import os
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from dataclasses import dataclass

# MongoDB imports
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, PyMongoError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NoSQLConfig:
    """NoSQL database configuration class"""
    connection_string: str
    database_name: str
    db_type: str = "mongodb"  # mongodb, firebase, dynamodb
    username: Optional[str] = None
    password: Optional[str] = None

class NoSQLConnector:
    """
    NoSQL Database connector for inventory operations.
    Currently supports MongoDB with extensibility for other NoSQL databases.
    """
    
    def __init__(self, config: Optional[NoSQLConfig] = None):
        """
        Initialize the NoSQL connector with database configuration.
        If no config provided, tries to load from environment variables.
        """
        if not MONGO_AVAILABLE:
            raise ImportError("pymongo is required for NoSQL operations. Install with: pip install pymongo")
        
        self.config = config or self._load_config_from_env()
        self.client = None
        self.database = None
        self._connect()
    
    def _load_config_from_env(self) -> NoSQLConfig:
        """Load database configuration from environment variables"""
        connection_string = os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017/")
        database_name = os.getenv("MONGODB_DATABASE", "inventory_db")
        
        return NoSQLConfig(
            connection_string=connection_string,
            database_name=database_name,
            db_type="mongodb",
            username=os.getenv("MONGODB_USERNAME"),
            password=os.getenv("MONGODB_PASSWORD")
        )
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            if self.config.username and self.config.password:
                # If credentials are provided separately
                connection_string = f"mongodb://{self.config.username}:{self.config.password}@" + \
                                  self.config.connection_string.replace("mongodb://", "")
            else:
                connection_string = self.config.connection_string
            
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.database = self.client[self.config.database_name]
            
            # Test connection
            self.client.admin.command('ismaster')
            logger.info(f"Connected to MongoDB: {self.config.database_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            raise
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_product_inventory(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get inventory information for a specific SKU"""
        try:
            collection = self.database.products
            product = collection.find_one({"sku": sku})
            
            if product:
                # Convert ObjectId to string for JSON serialization
                product['_id'] = str(product['_id'])
                return product
            
            return None
            
        except PyMongoError as e:
            logger.error(f"Error fetching product {sku}: {e}")
            raise
    
    def get_low_stock_products(self, threshold: int = 10, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products with stock below threshold"""
        try:
            collection = self.database.products
            
            # Query for products where inventory.quantity_in_stock <= threshold
            query = {
                "$or": [
                    {"inventory.quantity_in_stock": {"$lte": threshold}},
                    {"$expr": {"$lte": ["$inventory.quantity_in_stock", "$inventory.min_stock_level"]}}
                ]
            }
            
            cursor = collection.find(query).sort("inventory.quantity_in_stock", 1).limit(limit)
            
            products = []
            for product in cursor:
                product['_id'] = str(product['_id'])
                products.append(product)
            
            return products
            
        except PyMongoError as e:
            logger.error(f"Error fetching low stock products: {e}")
            raise
    
    def update_inventory_quantity(self, sku: str, new_quantity: int, reason: str = "Manual update") -> bool:
        """Update inventory quantity for a specific SKU"""
        try:
            collection = self.database.products
            
            # Get current product info for audit trail
            current_product = self.get_product_inventory(sku)
            if not current_product:
                logger.error(f"Product with SKU {sku} not found")
                return False
            
            old_quantity = current_product.get('inventory', {}).get('quantity_in_stock', 0)
            
            # Update the inventory
            update_result = collection.update_one(
                {"sku": sku},
                {
                    "$set": {
                        "inventory.quantity_in_stock": new_quantity,
                        "inventory.last_adjusted": datetime.utcnow(),
                        "inventory.updated_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Log the change in audit collection
                try:
                    self._log_inventory_change(
                        current_product['_id'],
                        sku,
                        old_quantity,
                        new_quantity,
                        reason
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to log inventory change: {audit_error}")
                
                logger.info(f"Updated inventory for {sku}: {old_quantity} -> {new_quantity}")
                return True
            
            return False
            
        except PyMongoError as e:
            logger.error(f"Failed to update inventory for {sku}: {e}")
            return False
    
    def _log_inventory_change(self, product_id: str, sku: str, old_qty: int, new_qty: int, reason: str):
        """Log inventory changes to audit collection"""
        try:
            audit_collection = self.database.inventory_audit
            
            audit_record = {
                "product_id": product_id,
                "sku": sku,
                "old_quantity": old_qty,
                "new_quantity": new_qty,
                "change_quantity": new_qty - old_qty,
                "reason": reason,
                "timestamp": datetime.utcnow(),
                "user_id": "system"
            }
            
            audit_collection.insert_one(audit_record)
            
        except PyMongoError as e:
            logger.error(f"Failed to log audit record: {e}")
            raise
    
    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all products in a specific category with inventory info"""
        try:
            collection = self.database.products
            cursor = collection.find({"category": category}).sort("name", 1)
            
            products = []
            for product in cursor:
                product['_id'] = str(product['_id'])
                products.append(product)
            
            return products
            
        except PyMongoError as e:
            logger.error(f"Error fetching products by category {category}: {e}")
            raise
    
    def search_products_by_name(self, name_pattern: str) -> List[Dict[str, Any]]:
        """Search products by name pattern (case-insensitive)"""
        try:
            collection = self.database.products
            
            # Use regex for case-insensitive search
            query = {"name": {"$regex": name_pattern, "$options": "i"}}
            cursor = collection.find(query).sort("name", 1).limit(20)
            
            products = []
            for product in cursor:
                product['_id'] = str(product['_id'])
                products.append(product)
            
            return products
            
        except PyMongoError as e:
            logger.error(f"Error searching products by name: {e}")
            raise
    
    def get_overstock_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products with stock above their maximum level"""
        try:
            collection = self.database.products
            
            # Use aggregation pipeline to calculate excess
            pipeline = [
                {
                    "$match": {
                        "$expr": {
                            "$gt": ["$inventory.quantity_in_stock", "$inventory.max_stock_level"]
                        }
                    }
                },
                {
                    "$addFields": {
                        "excess_quantity": {
                            "$subtract": ["$inventory.quantity_in_stock", "$inventory.max_stock_level"]
                        }
                    }
                },
                {"$sort": {"excess_quantity": -1}},
                {"$limit": limit}
            ]
            
            cursor = collection.aggregate(pipeline)
            
            products = []
            for product in cursor:
                product['_id'] = str(product['_id'])
                products.append(product)
            
            return products
            
        except PyMongoError as e:
            logger.error(f"Error fetching overstock products: {e}")
            raise
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get overall inventory summary statistics"""
        try:
            collection = self.database.products
            
            # Use aggregation pipeline for summary statistics
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_products": {"$sum": 1},
                        "out_of_stock": {
                            "$sum": {
                                "$cond": [{"$lte": ["$inventory.quantity_in_stock", 0]}, 1, 0]
                            }
                        },
                        "low_stock": {
                            "$sum": {
                                "$cond": [
                                    {
                                        "$and": [
                                            {"$lte": ["$inventory.quantity_in_stock", "$inventory.min_stock_level"]},
                                            {"$gt": ["$inventory.quantity_in_stock", 0]}
                                        ]
                                    },
                                    1, 0
                                ]
                            }
                        },
                        "overstock": {
                            "$sum": {
                                "$cond": [{"$gt": ["$inventory.quantity_in_stock", "$inventory.max_stock_level"]}, 1, 0]
                            }
                        },
                        "total_inventory_value": {
                            "$sum": {"$multiply": ["$inventory.quantity_in_stock", "$price"]}
                        }
                    }
                }
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if result:
                summary = result[0]
                del summary['_id']  # Remove the _id field
                return summary
            
            return {}
            
        except PyMongoError as e:
            logger.error(f"Error getting inventory summary: {e}")
            raise
    
    def create_product(self, product_data: Dict[str, Any]) -> str:
        """Create a new product with inventory data"""
        try:
            collection = self.database.products
            
            # Add timestamps
            product_data['created_at'] = datetime.utcnow()
            product_data['updated_at'] = datetime.utcnow()
            
            # Ensure inventory section exists
            if 'inventory' not in product_data:
                product_data['inventory'] = {
                    'quantity_in_stock': 0,
                    'min_stock_level': 10,
                    'max_stock_level': 100,
                    'location': 'Default',
                    'last_adjusted': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            
            result = collection.insert_one(product_data)
            logger.info(f"Created product with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Error creating product: {e}")
            raise
    
    def delete_product(self, sku: str) -> bool:
        """Delete a product and its inventory data"""
        try:
            collection = self.database.products
            result = collection.delete_one({"sku": sku})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted product with SKU: {sku}")
                return True
            
            return False
            
        except PyMongoError as e:
            logger.error(f"Error deleting product {sku}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            # Ping the database
            self.client.admin.command('ismaster')
            logger.info("MongoDB connection test successful")
            return True
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return False
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        try:
            collection = self.database.products
            
            # Create indexes
            collection.create_index("sku", unique=True)
            collection.create_index("name")
            collection.create_index("category")
            collection.create_index("inventory.quantity_in_stock")
            collection.create_index([("name", "text")])  # Text index for search
            
            logger.info("Created database indexes")
            
        except PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")
            raise

# Factory function to create NoSQL connector
def create_nosql_connector(config: Optional[NoSQLConfig] = None) -> NoSQLConnector:
    """Factory function to create NoSQL connector instance"""
    return NoSQLConnector(config)

# Example usage and testing
if __name__ == "__main__":
    if not MONGO_AVAILABLE:
        print("❌ MongoDB (pymongo) not available. Install with: pip install pymongo")
        exit(1)
    
    print("=== Testing NoSQL Connector ===")
    
    try:
        connector = create_nosql_connector()
        
        # Test connection
        if connector.test_connection():
            print("✅ MongoDB connection successful")
            
            # Create indexes
            connector.create_indexes()
            print("✅ Database indexes created")
            
            # Test basic operations
            try:
                summary = connector.get_inventory_summary()
                print(f"📊 Inventory Summary: {summary}")
                
                # Test search
                products = connector.search_products_by_name("test")
                print(f"🔍 Found {len(products)} products matching 'test'")
                
            except Exception as e:
                print(f"❌ Query test failed: {e}")
        else:
            print("❌ MongoDB connection failed")
            
    except Exception as e:
        print(f"❌ NoSQL Connector initialization failed: {e}")
    finally:
        if 'connector' in locals():
            connector.close_connection()
        
    print("=== NoSQL Connector Test Complete ===")