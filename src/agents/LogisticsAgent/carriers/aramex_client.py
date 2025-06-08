import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)

@dataclass
class AramexPickupRequest:
    """Aramex pickup request data structure"""
    reference: str
    pickup_address: Dict[str, str]
    delivery_address: Dict[str, str]
    package_details: Dict[str, Any]
    service_type: str = "standard"
    pickup_date: Optional[datetime] = None
    
    def to_aramex_format(self) -> Dict[str, Any]:
        """Convert to Aramex API format"""
        return {
            "Transaction": {
                "Reference1": self.reference,
                "Reference2": "",
                "Reference3": "",
                "Reference4": "",
                "Reference5": ""
            },
            "Shipments": [{
                "Reference1": self.reference,
                "Reference2": "",
                "Reference3": "",
                "Shipper": {
                    "Reference1": self.reference,
                    "Reference2": "",
                    "AccountNumber": os.getenv("ARAMEX_ACCOUNT_NUMBER", ""),
                    "PartyAddress": {
                        "Line1": self.pickup_address.get("street", ""),
                        "Line2": self.pickup_address.get("line2", ""),
                        "Line3": self.pickup_address.get("line3", ""),
                        "City": self.pickup_address.get("city", ""),
                        "StateOrProvinceCode": self.pickup_address.get("state", ""),
                        "PostCode": self.pickup_address.get("postal_code", ""),
                        "CountryCode": self.pickup_address.get("country", "SA")
                    },
                    "Contact": {
                        "PersonName": self.pickup_address.get("contact_name", ""),
                        "CompanyName": self.pickup_address.get("company", ""),
                        "PhoneNumber1": self.pickup_address.get("phone", ""),
                        "EmailAddress": self.pickup_address.get("email", "")
                    }
                },
                "Consignee": {
                    "Reference1": "",
                    "Reference2": "",
                    "AccountNumber": "",
                    "PartyAddress": {
                        "Line1": self.delivery_address.get("street", ""),
                        "Line2": self.delivery_address.get("line2", ""),
                        "Line3": self.delivery_address.get("line3", ""),
                        "City": self.delivery_address.get("city", ""),
                        "StateOrProvinceCode": self.delivery_address.get("state", ""),
                        "PostCode": self.delivery_address.get("postal_code", ""),
                        "CountryCode": self.delivery_address.get("country", "SA")
                    },
                    "Contact": {
                        "PersonName": self.delivery_address.get("contact_name", ""),
                        "CompanyName": self.delivery_address.get("company", ""),
                        "PhoneNumber1": self.delivery_address.get("phone", ""),
                        "EmailAddress": self.delivery_address.get("email", "")
                    }
                },
                "Details": {
                    "Dimensions": {
                        "Length": self.package_details.get("dimensions", {}).get("length", 0),
                        "Width": self.package_details.get("dimensions", {}).get("width", 0),
                        "Height": self.package_details.get("dimensions", {}).get("height", 0),
                        "Unit": "cm"
                    },
                    "ActualWeight": {
                        "Value": self.package_details.get("weight", 0),
                        "Unit": "kg"
                    },
                    "ProductGroup": "DOM" if self.pickup_address.get("country") == self.delivery_address.get("country") else "EXP",
                    "ProductType": self._get_product_type(),
                    "PaymentType": "P",
                    "PaymentOptions": "",
                    "Services": self._get_services(),
                    "NumberOfPieces": self.package_details.get("pieces", 1),
                    "DescriptionOfGoods": self.package_details.get("description", "General Goods"),
                    "GoodsOriginCountry": self.pickup_address.get("country", "SA")
                }
            }],
            "LabelInfo": {
                "ReportID": 9201,
                "ReportType": "URL"
            }
        }
    
    def _get_product_type(self) -> str:
        """Map service type to Aramex product type"""
        service_mapping = {
            "express": "PDX",
            "standard": "PPX", 
            "economy": "GND"
        }
        return service_mapping.get(self.service_type, "PPX")
    
    def _get_services(self) -> str:
        """Get additional services"""
        services = []
        if self.package_details.get("cod_amount"):
            services.append("COD")
        if self.package_details.get("insurance"):
            services.append("INS")
        return ",".join(services)

class AramexClient:
    """Aramex API client for logistics operations"""
    
    def __init__(self):
        self.base_url = os.getenv("ARAMEX_API_URL", "https://ws.aramex.net/ShippingAPI.V2/Shipping/Service_1_0.svc/json")
        self.username = os.getenv("ARAMEX_USERNAME", "")
        self.password = os.getenv("ARAMEX_PASSWORD", "")
        self.account_number = os.getenv("ARAMEX_ACCOUNT_NUMBER", "")
        self.account_pin = os.getenv("ARAMEX_ACCOUNT_PIN", "")
        self.account_entity = os.getenv("ARAMEX_ACCOUNT_ENTITY", "RUH")
        self.account_country_code = os.getenv("ARAMEX_COUNTRY_CODE", "SA")
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _get_client_info(self) -> Dict[str, Any]:
        """Get client information for API requests"""
        return {
            "UserName": self.username,
            "Password": self.password,
            "Version": "v1.0",
            "AccountNumber": self.account_number,
            "AccountPin": self.account_pin,
            "AccountEntity": self.account_entity,
            "AccountCountryCode": self.account_country_code,
            "Source": 24
        }
    
    def schedule_pickup(self, request: AramexPickupRequest) -> Dict[str, Any]:
        """Schedule a pickup with Aramex"""
        try:
            # Prepare the API payload
            payload = {
                "ClientInfo": self._get_client_info(),
                **request.to_aramex_format()
            }
            
            # Make API request
            response = self.session.post(
                f"{self.base_url}/CreateShipments",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("HasErrors", True):
                    errors = result.get("Notifications", [])
                    error_msg = "; ".join([error.get("Message", "") for error in errors])
                    logger.error(f"Aramex API error: {error_msg}")
                    return {
                        "status": "error",
                        "message": f"Aramex API error: {error_msg}"
                    }
                
                # Extract tracking information
                shipments = result.get("Shipments", [])
                if shipments:
                    shipment = shipments[0]
                    tracking_number = shipment.get("ID", "")
                    
                    return {
                        "status": "success",
                        "tracking_number": f"AMX{tracking_number}",
                        "reference": request.reference,
                        "carrier": "aramex",
                        "estimated_delivery": self._calculate_estimated_delivery(request.service_type),
                        "pickup_date": request.pickup_date.isoformat() if request.pickup_date else None,
                        "service_type": request.service_type
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No shipment data returned from Aramex"
                    }
            else:
                logger.error(f"Aramex HTTP error: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"HTTP error: {response.status_code}"
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Aramex request error: {str(e)}")
            return {
                "status": "error",
                "message": f"Request failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Aramex general error: {str(e)}")
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
    
    def track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Track a shipment with Aramex"""
        try:
            # Remove AMX prefix if present
            clean_tracking = tracking_number.replace("AMX", "")
            
            payload = {
                "ClientInfo": self._get_client_info(),
                "GetLastTrackingUpdateOnly": False,
                "Shipments": [clean_tracking]
            }
            
            response = self.session.post(
                f"{self.base_url}/TrackShipments",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("HasErrors", True):
                    errors = result.get("Notifications", [])
                    error_msg = "; ".join([error.get("Message", "") for error in errors])
                    return {
                        "status": "error",
                        "message": f"Tracking error: {error_msg}"
                    }
                
                # Extract tracking information
                tracking_results = result.get("TrackingResults", [])
                if tracking_results:
                    tracking = tracking_results[0]
                    updates = tracking.get("UpdatesDetails", [])
                    
                    current_status = "unknown"
                    current_location = "unknown"
                    
                    if updates:
                        latest_update = updates[0]
                        current_status = latest_update.get("UpdateDescription", "unknown")
                        current_location = latest_update.get("UpdateLocation", "unknown")
                    
                    return {
                        "status": "success",
                        "tracking_number": tracking_number,
                        "current_status": current_status,
                        "current_location": current_location,
                        "carrier": "aramex",
                        "updates": [
                            {
                                "status": update.get("UpdateDescription", ""),
                                "location": update.get("UpdateLocation", ""),
                                "timestamp": update.get("UpdateDateTime", ""),
                                "comments": update.get("Comments", "")
                            }
                            for update in updates
                        ]
                    }
                else:
                    return {
                        "status": "error",
                        "message": "No tracking information found"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"HTTP error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Aramex tracking error: {str(e)}")
            return {
                "status": "error",
                "message": f"Tracking failed: {str(e)}"
            }
    
    def check_service_availability(self, origin: str, destination: str) -> Dict[str, Any]:
        """Check service availability between locations"""
        try:
            # For now, return mock data - implement actual rate calculation API
            return {
                "status": "success",
                "available": True,
                "origin": origin,
                "destination": destination,
                "carrier": "aramex",
                "service_types": {
                    "express": {
                        "available": True,
                        "transit_time": "1-2 days",
                        "estimated_cost": "SAR 45.00"
                    },
                    "standard": {
                        "available": True,
                        "transit_time": "2-3 days", 
                        "estimated_cost": "SAR 25.00"
                    },
                    "economy": {
                        "available": True,
                        "transit_time": "3-5 days",
                        "estimated_cost": "SAR 15.00"
                    }
                },
                "restrictions": [],
                "special_services": ["COD", "Insurance", "Signature Required"]
            }
            
        except Exception as e:
            logger.error(f"Aramex availability check error: {str(e)}")
            return {
                "status": "error",
                "message": f"Availability check failed: {str(e)}"
            }
    
    def cancel_shipment(self, tracking_number: str, reason: str) -> Dict[str, Any]:
        """Cancel a shipment"""
        try:
            clean_tracking = tracking_number.replace("AMX", "")
            
            # Note: Implement actual cancellation API when available
            logger.info(f"Cancelling Aramex shipment {clean_tracking}, reason: {reason}")
            
            return {
                "status": "success",
                "tracking_number": tracking_number,
                "cancelled": True,
                "reason": reason,
                "carrier": "aramex"
            }
            
        except Exception as e:
            logger.error(f"Aramex cancellation error: {str(e)}")
            return {
                "status": "error",
                "message": f"Cancellation failed: {str(e)}"
            }
    
    def update_delivery_estimate(self, tracking_number: str, new_date: datetime, reason: str) -> Dict[str, Any]:
        """Update delivery estimate"""
        try:
            logger.info(f"Updating Aramex delivery estimate for {tracking_number}")
            
            return {
                "status": "success",
                "tracking_number": tracking_number,
                "new_estimate": new_date.isoformat(),
                "reason": reason,
                "carrier": "aramex",
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Aramex estimate update error: {str(e)}")
            return {
                "status": "error",
                "message": f"Estimate update failed: {str(e)}"
            }
    
    def _calculate_estimated_delivery(self, service_type: str) -> str:
        """Calculate estimated delivery date based on service type"""
        now = datetime.now()
        
        delivery_days = {
            "express": 1,
            "standard": 2,
            "economy": 4
        }
        
        days = delivery_days.get(service_type, 2)
        estimated_date = now + timedelta(days=days)
        
        return estimated_date.isoformat()

def create_aramex_client() -> AramexClient:
    """Factory function to create Aramex client"""
    return AramexClient()

# For testing purposes
if __name__ == "__main__":
    client = create_aramex_client()
    
    # Test pickup request
    test_request = AramexPickupRequest(
        reference="TEST123",
        pickup_address={
            "street": "King Fahd Road",
            "city": "Riyadh",
            "country": "SA",
            "contact_name": "Test Sender",
            "phone": "+966501234567"
        },
        delivery_address={
            "street": "Prince Sultan Road", 
            "city": "Jeddah",
            "country": "SA",
            "contact_name": "Test Recipient",
            "phone": "+966507654321"
        },
        package_details={
            "weight": 2.5,
            "dimensions": {"length": 30, "width": 20, "height": 15},
            "description": "Test Package"
        },
        service_type="standard"
    )
    
    print("Testing Aramex client...")
    result = client.schedule_pickup(test_request)
    print("Pickup result:", json.dumps(result, indent=2))