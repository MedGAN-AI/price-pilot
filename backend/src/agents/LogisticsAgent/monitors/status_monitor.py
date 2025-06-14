import os
import time
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from contextlib import contextmanager
import sys
# Add the parent directory to sys.path to access carriers module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carriers.aramex_client import create_aramex_client
from carriers.naqel_client import create_naqel_client

logger = logging.getLogger(__name__)

@dataclass
class ShipmentMonitor:
    """Shipment monitoring configuration"""
    tracking_number: str
    carrier: str
    reference: str
    status: str
    last_updated: str
    delay_threshold_hours: int = 4
    check_interval_minutes: int = 30
    callback_url: Optional[str] = None
    active: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class StatusMonitor:
    """
    Real-time status monitoring system for shipments across multiple carriers.
    Monitors shipments for delays, status changes, and triggers alerts.
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "shipment_monitor.db")
        self.aramex_client = create_aramex_client()
        self.naqel_client = create_naqel_client()
        
        # Monitoring configuration
        self.check_interval = int(os.getenv("MONITOR_CHECK_INTERVAL", "30"))  # minutes
        self.delay_threshold = int(os.getenv("DELAY_THRESHOLD_HOURS", "4"))   # hours
        self.max_workers = int(os.getenv("MONITOR_MAX_WORKERS", "5"))
        
        # Control flags
        self.monitoring_active = Event()
        self.monitoring_thread = None
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Callbacks for different events
        self.delay_callbacks: List[Callable] = []
        self.status_change_callbacks: List[Callable] = []
        self.delivery_callbacks: List[Callable] = []
        
        # Initialize database
        self._init_database()
        
        logger.info(f"StatusMonitor initialized with DB: {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database for shipment monitoring"""
        with self._get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS shipment_monitors (
                    tracking_number TEXT PRIMARY KEY,
                    carrier TEXT NOT NULL,
                    reference TEXT,
                    status TEXT,
                    last_updated TEXT,
                    delay_threshold_hours INTEGER DEFAULT 4,
                    check_interval_minutes INTEGER DEFAULT 30,
                    callback_url TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_number TEXT,
                    carrier TEXT,
                    status TEXT,
                    location TEXT,
                    timestamp TEXT,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tracking_number) REFERENCES shipment_monitors (tracking_number)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_number TEXT,
                    alert_type TEXT,
                    message TEXT,
                    severity TEXT,
                    triggered_at TEXT,
                    resolved_at TEXT,
                    active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (tracking_number) REFERENCES shipment_monitors (tracking_number)
                )
            ''')
    
    @contextmanager
    def _get_db_connection(self):
        """Get database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def add_shipment_monitor(self, monitor: ShipmentMonitor) -> bool:
        """Add a shipment to monitoring system"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO shipment_monitors 
                    (tracking_number, carrier, reference, status, last_updated, 
                     delay_threshold_hours, check_interval_minutes, callback_url, 
                     active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    monitor.tracking_number,
                    monitor.carrier,
                    monitor.reference,
                    monitor.status,
                    monitor.last_updated,
                    monitor.delay_threshold_hours,
                    monitor.check_interval_minutes,
                    monitor.callback_url,
                    monitor.active,
                    monitor.created_at,
                    datetime.now().isoformat()
                ))
            
            logger.info(f"Added shipment monitor: {monitor.tracking_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add shipment monitor: {e}")
            return False
    
    def remove_shipment_monitor(self, tracking_number: str) -> bool:
        """Remove a shipment from monitoring"""
        try:
            with self._get_db_connection() as conn:
                conn.execute(
                    "UPDATE shipment_monitors SET active = 0 WHERE tracking_number = ?",
                    (tracking_number,)
                )
            
            logger.info(f"Deactivated shipment monitor: {tracking_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove shipment monitor: {e}")
            return False
    
    def get_active_monitors(self) -> List[ShipmentMonitor]:
        """Get all active shipment monitors"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM shipment_monitors 
                    WHERE active = 1 
                    ORDER BY created_at DESC
                ''')
                
                monitors = []
                for row in cursor.fetchall():
                    monitor = ShipmentMonitor(
                        tracking_number=row['tracking_number'],
                        carrier=row['carrier'],
                        reference=row['reference'] or '',
                        status=row['status'] or '',
                        last_updated=row['last_updated'] or '',
                        delay_threshold_hours=row['delay_threshold_hours'],
                        check_interval_minutes=row['check_interval_minutes'],
                        callback_url=row['callback_url'],
                        active=bool(row['active']),
                        created_at=row['created_at']
                    )
                    monitors.append(monitor)
                
                return monitors
                
        except Exception as e:
            logger.error(f"Failed to get active monitors: {e}")
            return []
    
    def check_shipment_status(self, monitor: ShipmentMonitor) -> Dict[str, Any]:
        """Check status of a single shipment"""
        try:
            # Get appropriate client
            if monitor.carrier.lower() == 'aramex':
                client = self.aramex_client
            elif monitor.carrier.lower() == 'naqel':
                client = self.naqel_client
            else:
                raise ValueError(f"Unsupported carrier: {monitor.carrier}")
            
            # Track shipment
            tracking_result = client.track_shipment(monitor.tracking_number)
            
            if tracking_result.get('status') == 'error':
                logger.error(f"Tracking failed for {monitor.tracking_number}: {tracking_result.get('error')}")
                return tracking_result
            
            # Check for status changes
            current_status = tracking_result.get('status', '')
            if current_status != monitor.status:
                self._handle_status_change(monitor, current_status, tracking_result)
            
            # Check for delays
            self._check_for_delays(monitor, tracking_result)
            
            # Save status history
            self._save_status_history(monitor.tracking_number, tracking_result)
            
            # Update monitor record
            self._update_monitor_status(monitor.tracking_number, tracking_result)
            
            return tracking_result
            
        except Exception as e:
            logger.error(f"Status check failed for {monitor.tracking_number}: {e}")
            return {
                'tracking_number': monitor.tracking_number,
                'status': 'error',
                'error': str(e)
            }
    
    def _handle_status_change(self, monitor: ShipmentMonitor, new_status: str, tracking_result: Dict):
        """Handle shipment status changes"""
        try:
            logger.info(f"Status change for {monitor.tracking_number}: {monitor.status} -> {new_status}")
            
            # Check if delivered
            if 'delivered' in new_status.lower():
                self._trigger_delivery_callbacks(monitor, tracking_result)
            
            # Trigger status change callbacks
            self._trigger_status_change_callbacks(monitor, new_status, tracking_result)
            
        except Exception as e:
            logger.error(f"Failed to handle status change: {e}")
    
    def _check_for_delays(self, monitor: ShipmentMonitor, tracking_result: Dict):
        """Check for shipment delays"""
        try:
            estimated_delivery = tracking_result.get('estimated_delivery')
            if not estimated_delivery:
                return
            
            # Parse estimated delivery time
            try:
                est_dt = datetime.fromisoformat(estimated_delivery.replace('Z', '+00:00'))
                current_dt = datetime.now()
                
                # Check if delay exceeds threshold
                if current_dt > est_dt:
                    delay_hours = (current_dt - est_dt).total_seconds() / 3600
                    
                    if delay_hours > monitor.delay_threshold_hours:
                        self._trigger_delay_alert(monitor, delay_hours, tracking_result)
            
            except ValueError as e:
                logger.warning(f"Failed to parse delivery time: {estimated_delivery}, error: {e}")
                
        except Exception as e:
            logger.error(f"Delay check failed: {e}")
    
    def _save_status_history(self, tracking_number: str, tracking_result: Dict):
        """Save status to history table"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO status_history 
                    (tracking_number, carrier, status, location, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tracking_number,
                    tracking_result.get('carrier', ''),
                    tracking_result.get('status', ''),
                    tracking_result.get('current_location', ''),
                    tracking_result.get('last_updated', datetime.now().isoformat()),
                    json.dumps(tracking_result)
                ))
                
        except Exception as e:
            logger.error(f"Failed to save status history: {e}")
    
    def _update_monitor_status(self, tracking_number: str, tracking_result: Dict):
        """Update monitor record with latest status"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    UPDATE shipment_monitors 
                    SET status = ?, last_updated = ?, updated_at = ?
                    WHERE tracking_number = ?
                ''', (
                    tracking_result.get('status', ''),
                    tracking_result.get('last_updated', datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    tracking_number
                ))
                
        except Exception as e:
            logger.error(f"Failed to update monitor status: {e}")
    
    def _trigger_delay_alert(self, monitor: ShipmentMonitor, delay_hours: float, tracking_result: Dict):
        """Trigger delay alert and callbacks"""
        try:
            # Save alert to database
            with self._get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO alerts 
                    (tracking_number, alert_type, message, severity, triggered_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    monitor.tracking_number,
                    'DELAY',
                    f"Shipment delayed by {delay_hours:.1f} hours",
                    'HIGH' if delay_hours > 24 else 'MEDIUM',
                    datetime.now().isoformat()
                ))
            
            # Trigger callbacks
            for callback in self.delay_callbacks:
                try:
                    callback(monitor, delay_hours, tracking_result)
                except Exception as e:
                    logger.error(f"Delay callback failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger delay alert: {e}")
    
    def _trigger_status_change_callbacks(self, monitor: ShipmentMonitor, new_status: str, tracking_result: Dict):
        """Trigger status change callbacks"""
        for callback in self.status_change_callbacks:
            try:
                callback(monitor, new_status, tracking_result)
            except Exception as e:
                logger.error(f"Status change callback failed: {e}")
    
    def _trigger_delivery_callbacks(self, monitor: ShipmentMonitor, tracking_result: Dict):
        """Trigger delivery callbacks"""
        for callback in self.delivery_callbacks:
            try:
                callback(monitor, tracking_result)
            except Exception as e:
                logger.error(f"Delivery callback failed: {e}")
    
    def start_monitoring(self):
        """Start the monitoring service"""
        if self.monitoring_active.is_set():
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active.set()
        self.monitoring_thread = Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Status monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        if not self.monitoring_active.is_set():
            logger.warning("Monitoring is not active")
            return
        
        self.monitoring_active.clear()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=30)
        
        self.executor.shutdown(wait=True)
        logger.info("Status monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        while self.monitoring_active.is_set():
            try:
                monitors = self.get_active_monitors()
                
                if monitors:
                    logger.info(f"Checking {len(monitors)} active shipments")
                    
                    # Submit monitoring tasks to thread pool
                    futures = []
                    for monitor in monitors:
                        future = self.executor.submit(self.check_shipment_status, monitor)
                        futures.append(future)
                    
                    # Wait for all tasks to complete
                    for future in futures:
                        try:
                            future.result(timeout=60)  # 1 minute timeout per task
                        except Exception as e:
                            logger.error(f"Monitoring task failed: {e}")
                
                # Wait for next check interval
                self.monitoring_active.wait(timeout=self.check_interval * 60)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    # Callback registration methods
    def register_delay_callback(self, callback: Callable):
        """Register callback for delay alerts"""
        self.delay_callbacks.append(callback)
    
    def register_status_change_callback(self, callback: Callable):
        """Register callback for status changes"""
        self.status_change_callbacks.append(callback)
    
    def register_delivery_callback(self, callback: Callable):
        """Register callback for deliveries"""
        self.delivery_callbacks.append(callback)
    
    # Query methods
    def get_shipment_history(self, tracking_number: str) -> List[Dict]:
        """Get status history for a shipment"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM status_history 
                    WHERE tracking_number = ? 
                    ORDER BY created_at DESC
                ''', (tracking_number,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get shipment history: {e}")
            return []
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute('''
                    SELECT * FROM alerts 
                    WHERE active = 1 
                    ORDER BY triggered_at DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved"""
        try:
            with self._get_db_connection() as conn:
                conn.execute('''
                    UPDATE alerts 
                    SET active = 0, resolved_at = ? 
                    WHERE id = ?
                ''', (datetime.now().isoformat(), alert_id))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False

# Global monitor instance
_monitor_instance = None

def get_status_monitor() -> StatusMonitor:
    """Get global status monitor instance"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = StatusMonitor()
    return _monitor_instance

# Convenience functions for webhook integration
def handle_webhook_update(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle webhook updates from carriers"""
    try:
        monitor = get_status_monitor()
        tracking_number = webhook_data.get('tracking_number')
        
        if not tracking_number:
            return {"success": False, "error": "Missing tracking number"}
        
        # Create a mock monitor for processing
        mock_monitor = ShipmentMonitor(
            tracking_number=tracking_number,
            carrier=webhook_data.get('carrier', 'unknown'),
            reference=webhook_data.get('reference', ''),
            status=webhook_data.get('previous_status', ''),
            last_updated=webhook_data.get('timestamp', datetime.now().isoformat())
        )
        
        # Process the webhook data as a tracking result
        tracking_result = {
            'tracking_number': tracking_number,
            'status': webhook_data.get('status', ''),
            'current_location': webhook_data.get('location', ''),
            'last_updated': webhook_data.get('timestamp', datetime.now().isoformat()),
            'estimated_delivery': webhook_data.get('estimated_delivery', ''),
            'carrier': webhook_data.get('carrier', 'unknown')
        }
        
        # Handle status change
        if webhook_data.get('status') != webhook_data.get('previous_status'):
            monitor._handle_status_change(mock_monitor, webhook_data.get('status', ''), tracking_result)
        
        # Check for delays
        monitor._check_for_delays(mock_monitor, tracking_result)
        
        # Save history
        monitor._save_status_history(tracking_number, tracking_result)
        
        return {"success": True, "processed": True}
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {"success": False, "error": str(e)}