import os
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
from typing import List, Dict, Any, Optional
import logging
from contextlib import contextmanager
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration class"""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str = "postgresql"  # postgresql, sqlite, mysql

class SQLConnector:
    """
    SQL Database connector for inventory operations.
    Supports PostgreSQL, SQLite, and can be extended for other SQL databases.
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the SQL connector with database configuration.
        If no config provided, tries to load from environment variables.
        """
        self.config = config or self._load_config_from_env()
        self.connection = None
        
    def _load_config_from_env(self) -> DatabaseConfig:
        """Load database configuration from environment variables"""
        db_type = os.getenv("DB_TYPE", "postgresql").lower()
        
        if db_type == "sqlite":
            return DatabaseConfig(
                host="",
                port=0,
                database=os.getenv("DB_NAME", "inventory.db"),
                username="",
                password="",
                db_type="sqlite"
            )
        else:
            return DatabaseConfig(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "inventory"),
                username=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", ""),
                db_type=db_type
            )
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            if self.config.db_type == "sqlite":
                connection = sqlite3.connect(self.config.database)
                connection.row_factory = sqlite3.Row  # Enable dict-like access
            elif self.config.db_type == "postgresql":
                connection = psycopg2.connect(
                    host=self.config.host,
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.username,
                    password=self.config.password,
                    cursor_factory=RealDictCursor
                )
            else:
                raise ValueError(f"Unsupported database type: {self.config.db_type}")
            
            yield connection
            
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                
                if self.config.db_type == "sqlite":
                    # Convert sqlite3.Row to dict
                    return [dict(row) for row in cursor.fetchall()]
                else:
                    return cursor.fetchall()
                    
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                return cursor.rowcount
                
        except Exception as e:
            logger.error(f"Update execution error: {e}")
            raise
    
    def get_product_inventory(self, sku: str) -> Optional[Dict[str, Any]]:
        """Get inventory information for a specific SKU"""
        query = """
        SELECT p.id, p.sku, p.name, p.price, p.category,
               i.quantity_in_stock, i.min_stock_level, i.max_stock_level,
               i.location, i.last_adjusted, i.updated_at
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        WHERE p.sku = %s
        """
        
        if self.config.db_type == "sqlite":
            query = query.replace("%s", "?")
        
        results = self.execute_query(query, (sku,))
        return results[0] if results else None
    
    def get_low_stock_products(self, threshold: int = 10, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products with stock below threshold"""
        query = """
        SELECT p.id, p.sku, p.name, p.price, p.category,
               i.quantity_in_stock, i.min_stock_level, i.max_stock_level,
               i.location, i.last_adjusted
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        WHERE i.quantity_in_stock <= %s OR i.quantity_in_stock <= i.min_stock_level
        ORDER BY i.quantity_in_stock ASC
        LIMIT %s
        """
        
        if self.config.db_type == "sqlite":
            query = query.replace("%s", "?")
        
        return self.execute_query(query, (threshold, limit))
    
    def update_inventory_quantity(self, sku: str, new_quantity: int, reason: str = "Manual update") -> bool:
        """Update inventory quantity for a specific SKU"""
        try:
            # First get the current product info
            product = self.get_product_inventory(sku)
            if not product:
                logger.error(f"Product with SKU {sku} not found")
                return False
            
            # Update inventory table
            update_query = """
            UPDATE inventory 
            SET quantity_in_stock = %s, 
                last_adjusted = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE product_id = %s
            """
            
            if self.config.db_type == "sqlite":
                update_query = update_query.replace("%s", "?").replace("CURRENT_TIMESTAMP", "datetime('now')")
            
            affected_rows = self.execute_update(update_query, (new_quantity, product['id']))
            
            if affected_rows > 0:
                # Log the change in audit table (if exists)
                try:
                    self._log_inventory_change(
                        product['id'], 
                        sku, 
                        product['quantity_in_stock'], 
                        new_quantity, 
                        reason
                    )
                except Exception as audit_error:
                    logger.warning(f"Failed to log inventory change: {audit_error}")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update inventory for {sku}: {e}")
            return False
    
    def _log_inventory_change(self, product_id: int, sku: str, old_qty: int, new_qty: int, reason: str):
        """Log inventory changes to audit table"""
        audit_query = """
        INSERT INTO inventory_audit 
        (product_id, sku, old_quantity, new_quantity, change_quantity, reason, timestamp, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'system')
        """
        
        if self.config.db_type == "sqlite":
            audit_query = audit_query.replace("%s", "?").replace("CURRENT_TIMESTAMP", "datetime('now')")
        
        change_qty = new_qty - old_qty
        self.execute_update(audit_query, (product_id, sku, old_qty, new_qty, change_qty, reason))
    
    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all products in a specific category with inventory info"""
        query = """
        SELECT p.id, p.sku, p.name, p.price, p.category,
               i.quantity_in_stock, i.min_stock_level, i.max_stock_level,
               i.location
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        WHERE p.category = %s
        ORDER BY p.name
        """
        
        if self.config.db_type == "sqlite":
            query = query.replace("%s", "?")
        
        return self.execute_query(query, (category,))
    
    def search_products_by_name(self, name_pattern: str) -> List[Dict[str, Any]]:
        """Search products by name pattern"""
        query = """
        SELECT p.id, p.sku, p.name, p.price, p.category,
               i.quantity_in_stock, i.min_stock_level, i.max_stock_level,
               i.location
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        WHERE p.name ILIKE %s
        ORDER BY p.name
        LIMIT 20
        """
        
        if self.config.db_type == "sqlite":
            query = query.replace("ILIKE", "LIKE").replace("%s", "?")
        
        return self.execute_query(query, (f"%{name_pattern}%",))
    
    def get_overstock_products(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products with stock above their maximum level"""
        query = """
        SELECT p.id, p.sku, p.name, p.price, p.category,
               i.quantity_in_stock, i.min_stock_level, i.max_stock_level,
               i.location, 
               (i.quantity_in_stock - i.max_stock_level) as excess_quantity
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        WHERE i.quantity_in_stock > i.max_stock_level
        ORDER BY excess_quantity DESC
        LIMIT %s
        """
        
        if self.config.db_type == "sqlite":
            query = query.replace("%s", "?")
        
        return self.execute_query(query, (limit,))
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get overall inventory summary statistics"""
        summary_query = """
        SELECT 
            COUNT(*) as total_products,
            SUM(CASE WHEN i.quantity_in_stock <= 0 THEN 1 ELSE 0 END) as out_of_stock,
            SUM(CASE WHEN i.quantity_in_stock <= i.min_stock_level AND i.quantity_in_stock > 0 THEN 1 ELSE 0 END) as low_stock,
            SUM(CASE WHEN i.quantity_in_stock > i.max_stock_level THEN 1 ELSE 0 END) as overstock,
            SUM(i.quantity_in_stock * p.price) as total_inventory_value
        FROM products p
        INNER JOIN inventory i ON p.id = i.product_id
        """
        
        results = self.execute_query(summary_query)
        return results[0] if results else {}
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if self.config.db_type == "sqlite":
                    cursor.execute("SELECT 1")
                else:
                    cursor.execute("SELECT 1")
                cursor.fetchone()
                logger.info(f"Database connection successful ({self.config.db_type})")
                return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

# Factory function to create SQL connector
def create_sql_connector(config: Optional[DatabaseConfig] = None) -> SQLConnector:
    """Factory function to create SQL connector instance"""
    return SQLConnector(config)

# Example usage and testing
if __name__ == "__main__":
    # Test the connector
    print("=== Testing SQL Connector ===")
    
    connector = create_sql_connector()
    
    # Test connection
    if connector.test_connection():
        print("✅ Database connection successful")
        
        # Test basic query
        try:
            summary = connector.get_inventory_summary()
            print(f"📊 Inventory Summary: {summary}")
        except Exception as e:
            print(f"❌ Query test failed: {e}")
    else:
        print("❌ Database connection failed")
        
    print("=== SQL Connector Test Complete ===")