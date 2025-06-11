import json
import logging
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from langchain_core.tools import Tool
from pydantic import BaseModel, Field

# Add the parent directory to sys.path to access carriers module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carriers.aramex_client import create_aramex_client, AramexPickupRequest
from carriers.naqel_client import create_naqel_client, NaqelPickupRequest
from monitors.status_monitor import get_status_monitor, ShipmentMonitor

logger = logging.getLogger(__name__)

# Pydantic models for tool inputs
class SchedulePickupInput(BaseModel):
    """Input schema for scheduling pickup"""
    reference: str = Field(description="Order or shipment reference number")
    carrier: str = Field(description="Carrier name (aramex or naqel)")
    pickup_address: Dict[str, str] = Field(description="Pickup address details")
    delivery_address: Dict[str, str] = Field(description="Delivery address details")
    package_details: Dict[str, Any] = Field(description="Package specifications")
    service_type: str = Field(default="standard", description="Service type (standard, express, economy)")
    pickup_date: Optional[str] = Field(default=None, description="Preferred pickup date (ISO format)")

class TrackShipmentInput(BaseModel):
    """Input schema for tracking shipment"""
    tracking_number: str = Field(description="Shipment tracking number")
    carrier: Optional[str] = Field(default=None, description="Carrier name (aramex or naqel)")

class CheckCarrierStatusInput(BaseModel):
    """Input schema for checking carrier availability"""
    carrier: str = Field(description="Carrier name (aramex or naqel)")
    origin: str = Field(description="Origin city or location")
    destination: str = Field(description="Destination city or location")

class RerouteShipmentInput(BaseModel):
    """Input schema for rerouting shipment"""
    tracking_number: str = Field(description="Shipment tracking number")
    new_carrier: str = Field(description="New carrier for rerouting")
    reason: str = Field(description="Reason for rerouting")

class UpdateDeliveryEstimateInput(BaseModel):
    """Input schema for updating delivery estimates"""
    tracking_number: str = Field(description="Shipment tracking number")
    new_estimate: str = Field(description="New delivery estimate (ISO format)")
    reason: str = Field(description="Reason for estimate change")

def schedule_pickup_func(
    reference: str,
    carrier: str,
    pickup_address: Dict[str, str],
    delivery_address: Dict[str, str],
    package_details: Dict[str, Any],
    service_type: str = "standard",
    pickup_date: Optional[str] = None
) -> str:
    """
    Schedule a pickup with the specified carrier
    """
    try:
        carrier = carrier.lower().strip()
        
        # Parse pickup date if provided
        scheduled_date = None
        if pickup_date:
            try:
                scheduled_date = datetime.fromisoformat(pickup_date.replace('Z', '+00:00'))
            except ValueError:
                scheduled_date = datetime.now() + timedelta(days=1)
        else:
            scheduled_date = datetime.now() + timedelta(days=1)
        
        if carrier == "aramex":
            client = create_aramex_client()
            pickup_request = AramexPickupRequest(
                reference=reference,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                package_details=package_details,
                service_type=service_type,
                pickup_date=scheduled_date
            )
            result = client.schedule_pickup(pickup_request)
            
        elif carrier == "naqel":
            client = create_naqel_client()
            pickup_request = NaqelPickupRequest(
                reference=reference,
                pickup_address=pickup_address,
                delivery_address=delivery_address,
                package_details=package_details,
                service_type=service_type,
                pickup_date=scheduled_date
            )
            result = client.schedule_pickup(pickup_request)
            
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unsupported carrier: {carrier}. Supported carriers: aramex, naqel"
            })
        
        # Initialize monitoring for the shipment with improved error handling
        try:
            monitor = get_status_monitor()
            tracking_number = result.get("tracking_number")
            
            if tracking_number and hasattr(monitor, 'add_shipment_monitor'):
                monitor.add_shipment_monitor(
                    tracking_number=tracking_number,
                    carrier=carrier,
                    reference=reference
                )
                logger.info(f"Added shipment {tracking_number} to monitoring system")
        except Exception as monitor_error:
            logger.warning(f"Failed to add shipment to monitor: {monitor_error}")
        
        logger.info(f"Pickup scheduled successfully for {reference} with {carrier}")
        return json.dumps({
            "status": "success",
            "tracking_number": result.get("tracking_number"),
            "pickup_date": scheduled_date.isoformat(),
            "carrier": carrier,
            "reference": reference,
            "estimated_delivery": result.get("estimated_delivery")
        })
        
    except Exception as e:
        logger.error(f"Error scheduling pickup for {reference}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to schedule pickup: {str(e)}"
        })

def track_shipment_func(tracking_number: str, carrier: Optional[str] = None) -> str:
    """
    Track a shipment using tracking number
    """
    try:
        # If carrier not specified, try to determine from tracking number format
        if not carrier:
            # Check tracking number patterns
            if tracking_number.upper().startswith(("AR", "AMX")):
                carrier = "aramex"
            elif tracking_number.upper().startswith(("NQ", "NQL")):
                carrier = "naqel"
            else:
                # Try to auto-detect by testing both carriers
                for test_carrier in ["naqel", "aramex"]:  # Try naqel first as shown in your output
                    try:
                        result = _get_tracking_info(tracking_number, test_carrier)
                        if result.get("status") != "error" and not result.get("mock_mode", False):
                            carrier = test_carrier
                            break
                    except Exception as e:
                        logger.debug(f"Failed to track with {test_carrier}: {e}")
                        continue
                
                # If still no carrier found, default to naqel (as shown in your output)
                if not carrier:
                    carrier = "naqel"
                    logger.info(f"Could not auto-detect carrier for {tracking_number}, defaulting to naqel")
        
        result = _get_tracking_info(tracking_number, carrier)
        
        # Enhanced monitoring system update with better error handling
        try:
            monitor = get_status_monitor()
            if result.get("status") != "error":
                current_status = result.get("status", result.get("current_status"))
                
                # Try to update status using available methods
                updated = False
                
                # List of possible method names to try
                update_methods = [
                    'check_shipment_status',  # This method exists in your monitor
                    'update_status', 
                    'update_shipment_status',
                    'set_status',
                    'record_status'
                ]
                
                for method_name in update_methods:
                    if hasattr(monitor, method_name):
                        try:
                            method = getattr(monitor, method_name)
                            if method_name == 'check_shipment_status':
                                # This method might just check status, not update it
                                method(tracking_number)
                            else:
                                method(tracking_number, current_status)
                            updated = True
                            logger.debug(f"Successfully updated status using {method_name}")
                            break
                        except Exception as method_error:
                            logger.debug(f"Failed to use {method_name}: {method_error}")
                            continue
                
                if not updated:
                    # Try to add the shipment to monitoring if not already there
                    if hasattr(monitor, 'add_shipment_monitor'):
                        try:
                            monitor.add_shipment_monitor(
                                tracking_number=tracking_number,
                                carrier=carrier
                            )
                            logger.info(f"Added {tracking_number} to monitoring system")
                        except Exception as add_error:
                            logger.debug(f"Failed to add shipment to monitor: {add_error}")
                    
                    logger.warning(f"Could not update shipment status in monitor for {tracking_number}")
                    
        except Exception as monitor_error:
            logger.warning(f"Monitor operation failed for {tracking_number}: {monitor_error}")
        
        # Add additional metadata to result
        result.update({
            "tracking_number": tracking_number,
            "carrier": carrier,
            "last_updated": datetime.now().isoformat(),
            "mock_mode": result.get("mock_mode", False)
        })
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error tracking shipment {tracking_number}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to track shipment: {str(e)}",
            "tracking_number": tracking_number,
            "carrier": carrier
        })

def _get_tracking_info(tracking_number: str, carrier: str) -> Dict[str, Any]:
    """Helper function to get tracking information from specific carrier"""
    try:
        carrier = carrier.lower().strip()
        
        if carrier == "aramex":
            client = create_aramex_client()
            return client.track_shipment(tracking_number)
        elif carrier == "naqel":
            client = create_naqel_client()
            return client.track_shipment(tracking_number)
        else:
            return {
                "status": "error",
                "message": f"Unsupported carrier: {carrier}. Supported carriers: aramex, naqel"
            }
    except Exception as e:
        logger.error(f"Error getting tracking info from {carrier}: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get tracking information from {carrier}: {str(e)}"
        }

def check_carrier_status_func(carrier: str, origin: str, destination: str) -> str:
    """
    Check carrier service availability and capacity
    """
    try:
        carrier = carrier.lower().strip()
        
        if carrier == "aramex":
            client = create_aramex_client()
            result = client.check_service_availability(origin, destination)
        elif carrier == "naqel":
            client = create_naqel_client()
            result = client.check_service_availability(origin, destination)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Unsupported carrier: {carrier}. Supported carriers: aramex, naqel"
            })
        
        return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error checking carrier status for {carrier}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to check carrier status: {str(e)}"
        })

def reroute_shipment_func(tracking_number: str, new_carrier: str, reason: str) -> str:
    """
    Reroute shipment to a different carrier
    """
    try:
        # First, get current shipment details
        current_info = None
        current_carrier = None
        
        for carrier in ["aramex", "naqel"]:
            try:
                info = _get_tracking_info(tracking_number, carrier)
                if info.get("status") != "error":
                    current_info = info
                    current_carrier = carrier
                    break
            except Exception as e:
                logger.debug(f"Failed to get info from {carrier}: {e}")
                continue
        
        if not current_info:
            return json.dumps({
                "status": "error",
                "message": "Could not find shipment information for rerouting"
            })
        
        # Check if shipment can be rerouted (not yet delivered or in transit)
        current_status = current_info.get("status", current_info.get("current_status", "")).lower()
        if current_status in ["delivered", "out_for_delivery", "ofd"]:
            return json.dumps({
                "status": "error",
                "message": "Cannot reroute shipment - already delivered or out for delivery"
            })
        
        new_carrier = new_carrier.lower().strip()
        
        # Validate new carrier
        if new_carrier not in ["aramex", "naqel"]:
            return json.dumps({
                "status": "error",
                "message": f"Invalid new carrier: {new_carrier}. Supported carriers: aramex, naqel"
            })
        
        # Cancel current shipment
        try:
            if current_carrier == "aramex":
                client = create_aramex_client()
                cancel_result = client.cancel_shipment(tracking_number, reason)
            else:
                client = create_naqel_client()
                cancel_result = client.cancel_shipment(tracking_number, reason)
            
            if cancel_result.get("status") != "success":
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to cancel current shipment: {cancel_result.get('message', 'Unknown error')}"
                })
        except Exception as e:
            logger.error(f"Failed to cancel shipment {tracking_number}: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to cancel current shipment: {str(e)}"
            })
        
        # Create new shipment with new carrier
        new_pickup_result = schedule_pickup_func(
            reference=f"REROUTE_{tracking_number}_{datetime.now().strftime('%Y%m%d_%H%M')}",
            carrier=new_carrier,
            pickup_address=current_info.get("pickup_address", {}),
            delivery_address=current_info.get("delivery_address", {}),
            package_details=current_info.get("package_details", {}),
            service_type=current_info.get("service_type", "standard")
        )
        
        new_pickup_data = json.loads(new_pickup_result)
        
        if new_pickup_data.get("status") == "success":
            # Update monitoring system
            try:
                monitor = get_status_monitor()
                # Remove old monitoring
                if hasattr(monitor, 'remove_shipment_monitor'):
                    monitor.remove_shipment_monitor(tracking_number)
                # Add new monitoring is handled in schedule_pickup_func
            except Exception as monitor_error:
                logger.warning(f"Failed to update reroute in monitor: {monitor_error}")
            
            logger.info(f"Shipment {tracking_number} rerouted from {current_carrier} to {new_carrier}")
            return json.dumps({
                "status": "success",
                "old_tracking_number": tracking_number,
                "old_carrier": current_carrier,
                "new_tracking_number": new_pickup_data.get("tracking_number"),
                "new_carrier": new_carrier,
                "reason": reason,
                "estimated_delivery": new_pickup_data.get("estimated_delivery")
            })
        else:
            return json.dumps({
                "status": "error",
                "message": f"Failed to create new shipment with {new_carrier}: {new_pickup_data.get('message', 'Unknown error')}"
            })
        
    except Exception as e:
        logger.error(f"Error rerouting shipment {tracking_number}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to reroute shipment: {str(e)}"
        })

def update_delivery_estimate_func(tracking_number: str, new_estimate: str, reason: str) -> str:
    """
    Update delivery estimate for a shipment
    """
    try:
        # Parse new estimate
        try:
            new_delivery_date = datetime.fromisoformat(new_estimate.replace('Z', '+00:00'))
        except ValueError:
            return json.dumps({
                "status": "error",
                "message": "Invalid date format for new estimate. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            })
        
        # Find the carrier for this tracking number
        carrier = None
        shipment_info = None
        
        for test_carrier in ["aramex", "naqel"]:
            try:
                info = _get_tracking_info(tracking_number, test_carrier)
                if info.get("status") != "error":
                    carrier = test_carrier
                    shipment_info = info
                    break
            except Exception as e:
                logger.debug(f"Failed to check {test_carrier}: {e}")
                continue
        
        if not carrier or not shipment_info:
            return json.dumps({
                "status": "error",
                "message": "Could not find shipment information"
            })
        
        # Update estimate with carrier
        try:
            if carrier == "aramex":
                client = create_aramex_client()
                result = client.update_delivery_estimate(tracking_number, new_delivery_date, reason)
            else:
                client = create_naqel_client()
                result = client.update_delivery_estimate(tracking_number, new_delivery_date, reason)
        except Exception as e:
            logger.error(f"Failed to update delivery estimate with {carrier}: {e}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to update delivery estimate with {carrier}: {str(e)}"
            })
        
        if result.get("status") == "success":
            # Update monitoring system
            try:
                monitor = get_status_monitor()
                if hasattr(monitor, 'update_delivery_estimate'):
                    monitor.update_delivery_estimate(tracking_number, new_delivery_date, reason)
            except Exception as monitor_error:
                logger.warning(f"Failed to update delivery estimate in monitor: {monitor_error}")
            
            logger.info(f"Delivery estimate updated for {tracking_number}")
            return json.dumps({
                "status": "success",
                "tracking_number": tracking_number,
                "new_estimate": new_delivery_date.isoformat(),
                "reason": reason,
                "carrier": carrier
            })
        else:
            return json.dumps(result)
        
    except Exception as e:
        logger.error(f"Error updating delivery estimate for {tracking_number}: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to update delivery estimate: {str(e)}"
        })

def get_shipment_analytics_func() -> str:
    """
    Get analytics and insights from monitored shipments
    """
    try:
        monitor = get_status_monitor()
        
        # Try different methods to get analytics
        analytics = {}
        
        if hasattr(monitor, 'get_analytics'):
            analytics = monitor.get_analytics()
        elif hasattr(monitor, 'get_active_monitors'):
            active_monitors = monitor.get_active_monitors()
            analytics = {
                "active_shipments": len(active_monitors) if active_monitors else 0,
                "monitors": active_monitors
            }
        else:
            analytics = {
                "message": "Analytics not available - monitor system limited",
                "available_methods": [method for method in dir(monitor) if not method.startswith('_')]
            }
        
        return json.dumps({
            "status": "success",
            "analytics": analytics,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting shipment analytics: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get analytics: {str(e)}"
        })

# Create LangChain tools
def create_logistics_tools() -> List[Tool]:
    """
    Create and return all logistics tools for the agent
    """
    
    schedule_pickup_tool = Tool(
        name="schedule_pickup",
        description="Schedule a pickup with a carrier (Aramex or Naqel). Requires reference number, carrier, addresses, and package details.",
        func=lambda x: schedule_pickup_func(**json.loads(x)),
        args_schema=SchedulePickupInput
    )
    
    track_shipment_tool = Tool(
        name="track_shipment",
        description="Track a shipment using tracking number. Can auto-detect carrier or specify explicitly.",
        func=lambda x: track_shipment_func(**json.loads(x)),
        args_schema=TrackShipmentInput
    )
    
    check_carrier_status_tool = Tool(
        name="check_carrier_status",
        description="Check carrier service availability and capacity between origin and destination.",
        func=lambda x: check_carrier_status_func(**json.loads(x)),
        args_schema=CheckCarrierStatusInput
    )
    
    reroute_shipment_tool = Tool(
        name="reroute_shipment",
        description="Reroute an existing shipment to a different carrier. Requires tracking number, new carrier, and reason.",
        func=lambda x: reroute_shipment_func(**json.loads(x)),
        args_schema=RerouteShipmentInput
    )
    
    update_delivery_estimate_tool = Tool(
        name="update_delivery_estimate",
        description="Update the delivery estimate for a shipment. Requires tracking number, new estimate date, and reason.",
        func=lambda x: update_delivery_estimate_func(**json.loads(x)),
        args_schema=UpdateDeliveryEstimateInput
    )
    
    get_analytics_tool = Tool(
        name="get_shipment_analytics",
        description="Get analytics and insights from all monitored shipments including performance metrics and trends.",
        func=lambda x: get_shipment_analytics_func()
    )
    
    return [
        schedule_pickup_tool,
        track_shipment_tool,
        check_carrier_status_tool,
        reroute_shipment_tool,
        update_delivery_estimate_tool,
        get_analytics_tool
    ]

# Utility functions for the agent
def validate_address(address: Dict[str, str]) -> bool:
    """Validate address format"""
    required_fields = ["street", "city", "country"]
    return all(field in address and address[field].strip() for field in required_fields)

def validate_package_details(package: Dict[str, Any]) -> bool:
    """Validate package details format"""
    required_fields = ["weight", "dimensions"]
    return all(field in package for field in required_fields)

def get_supported_carriers() -> List[str]:
    """Get list of supported carriers"""
    return ["aramex", "naqel"]

def format_tracking_response(tracking_data: Dict[str, Any]) -> str:
    """Format tracking response for better readability"""
    if tracking_data.get("status") == "error":
        return f"[ERROR] Error: {tracking_data.get('message')}"
    
    status = tracking_data.get("status", tracking_data.get("current_status", "Unknown"))
    location = tracking_data.get("current_location", "Unknown")
    estimated_delivery = tracking_data.get("estimated_delivery", "Not available")
    mock_mode = "[TEST] (Mock Mode)" if tracking_data.get("mock_mode") else ""
    
    return f"""
[PACKAGE] Shipment Status: {status} {mock_mode}
[LOCATION] Current Location: {location}
[TRUCK] Estimated Delivery: {estimated_delivery}
[BUILDING] Carrier: {tracking_data.get('carrier', 'Unknown')}
[NUMBER] Tracking Number: {tracking_data.get('tracking_number', 'Unknown')}
"""

def get_monitor_info() -> Dict[str, Any]:
    """Get information about the monitoring system"""
    try:
        monitor = get_status_monitor()
        return {
            "available_methods": [method for method in dir(monitor) if not method.startswith('_')],
            "active_monitors": getattr(monitor, 'get_active_monitors', lambda: [])(),
            "monitoring_active": getattr(monitor, 'monitoring_active', False)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Test the tools
    tools = create_logistics_tools()
    print(f"Created {len(tools)} logistics tools:")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")
    
    # Display monitor info for debugging
    print("\nMonitor System Info:")
    monitor_info = get_monitor_info()
    print(json.dumps(monitor_info, indent=2))