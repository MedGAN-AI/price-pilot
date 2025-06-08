import os
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class NaqelShipment:
    """Naqel shipment data structure"""
    tracking_number: str
    status: str
    current_location: str
    estimated_delivery: str
    pickup_date: str
    delivery_date: Optional[str] = None
    carrier: str = "naqel"
    service_type: str = "standard"

@dataclass
class NaqelPickupRequest:
    """Naqel pickup request structure"""
    reference: str
    pickup_address: Dict[str, str]
    delivery_address: Dict[str, str]
    package_details: Dict[str, Any]
    service_type: str = "standard"
    pickup_date: str = None

class NaqelClient:
    """
    Naqel Express API client for shipping operations in Saudi Arabia and Gulf region.
    Handles pickup scheduling, tracking, and shipment management.
    """
    
    def __init__(self):
        self.base_url = os.getenv("NAQEL_API_URL", "https://api.naqelexpress.com/v1")
        self.api_key = os.getenv("NAQEL_API_KEY")
        self.client_id = os.getenv("NAQEL_CLIENT_ID")
        self.client_secret = os.getenv("NAQEL_CLIENT_SECRET")
        self.account_number = os.getenv("NAQEL_ACCOUNT_NUMBER")
        
        if not all([self.api_key, self.client_id, self.client_secret]):
            logger.warning("Naqel credentials not found. Using mock mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        # Naqel service areas (primarily Saudi Arabia and Gulf)
        self.service_areas = {
            "SA": ["Riyadh", "Jeddah", "Dammam", "Mecca", "Medina", "Khobar", "Jubail", "Abha"],
            "AE": ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
            "KW": ["Kuwait City", "Al Ahmadi", "Hawalli"],
            "QA": ["Doha", "Al Rayyan", "Al Wakrah"],
            "BH": ["Manama", "Riffa", "Muharraq"],
            "OM": ["Muscat", "Salalah", "Nizwa"]
        }
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for Naqel API"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Client-ID": self.client_id
        }
    
    def _authenticate(self) -> Optional[str]:
        """Get OAuth token for Naqel API"""
        if self.mock_mode:
            return "mock_token"
        
        try:
            auth_payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(
                f"{self.base_url}/auth/token",
                json=auth_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("access_token")
            else:
                logger.error(f"Naqel authentication failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Naqel authentication error: {str(e)}")
            return None
    
    def schedule_pickup(self, pickup_request: NaqelPickupRequest) -> Dict[str, Any]:
        """
        Schedule a pickup with Naqel Express
        """
        if self.mock_mode:
            return self._mock_schedule_pickup(pickup_request)
        
        try:
            token = self._authenticate()
            if not token:
                raise Exception("Failed to authenticate with Naqel API")
            
            headers = self._get_auth_headers()
            headers["Authorization"] = f"Bearer {token}"
            
            # Naqel API payload structure
            payload = {
                "shipment": {
                    "reference_number": pickup_request.reference,
                    "service_type": pickup_request.service_type.upper(),
                    "pickup_date": pickup_request.pickup_date or datetime.now().strftime("%Y-%m-%d"),
                    "shipper": {
                        "name": pickup_request.pickup_address.get("contact_name", ""),
                        "company": pickup_request.pickup_address.get("company", ""),
                        "phone": pickup_request.pickup_address.get("phone", ""),
                        "email": pickup_request.pickup_address.get("email", ""),
                        "address": {
                            "street": pickup_request.pickup_address.get("line1", ""),
                            "area": pickup_request.pickup_address.get("line2", ""),
                            "city": pickup_request.pickup_address.get("city", ""),
                            "country": pickup_request.pickup_address.get("country_code", "SA"),
                            "postal_code": pickup_request.pickup_address.get("postal_code", "")
                        }
                    },
                    "consignee": {
                        "name": pickup_request.delivery_address.get("contact_name", ""),
                        "company": pickup_request.delivery_address.get("company", ""),
                        "phone": pickup_request.delivery_address.get("phone", ""),
                        "email": pickup_request.delivery_address.get("email", ""),
                        "address": {
                            "street": pickup_request.delivery_address.get("line1", ""),
                            "area": pickup_request.delivery_address.get("line2", ""),
                            "city": pickup_request.delivery_address.get("city", ""),
                            "country": pickup_request.delivery_address.get("country_code", "SA"),
                            "postal_code": pickup_request.delivery_address.get("postal_code", "")
                        }
                    },
                    "package": {
                        "weight": pickup_request.package_details.get("weight", 1),
                        "length": pickup_request.package_details.get("length", 10),
                        "width": pickup_request.package_details.get("width", 10),
                        "height": pickup_request.package_details.get("height", 10),
                        "pieces": pickup_request.package_details.get("pieces", 1),
                        "description": pickup_request.package_details.get("description", "General Goods"),
                        "value": pickup_request.package_details.get("value", 100),
                        "currency": pickup_request.package_details.get("currency", "SAR")
                    },
                    "special_instructions": pickup_request.package_details.get("instructions", ""),
                    "payment_method": "PREPAID"  # Default for business accounts
                }
            }
            
            response = requests.post(
                f"{self.base_url}/shipments",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                
                if result.get("success", False):
                    shipment_data = result.get("data", {})
                    return {
                        "success": True,
                        "tracking_number": shipment_data.get("tracking_number", ""),
                        "reference": pickup_request.reference,
                        "pickup_scheduled": True,
                        "estimated_pickup": pickup_request.pickup_date,
                        "carrier": "naqel",
                        "service_type": pickup_request.service_type,
                        "cost": shipment_data.get("cost", {})
                    }
                else:
                    error_msg = result.get("message", "Unknown error")
                    raise Exception(f"Naqel API Error: {error_msg}")
            
            raise Exception(f"Naqel API request failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Naqel pickup scheduling failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "carrier": "naqel"
            }
    
    def track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """
        Track a shipment using Naqel tracking API
        """
        if self.mock_mode:
            return self._mock_track_shipment(tracking_number)
        
        try:
            token = self._authenticate()
            if not token:
                raise Exception("Failed to authenticate with Naqel API")
            
            headers = self._get_auth_headers()
            headers["Authorization"] = f"Bearer {token}"
            
            response = requests.get(
                f"{self.base_url}/shipments/{tracking_number}/track",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get("success", False):
                    tracking_data = result.get("data", {})
                    shipment_status = tracking_data.get("status", {})
                    tracking_events = tracking_data.get("events", [])
                    
                    # Get latest event
                    latest_event = tracking_events[0] if tracking_events else {}
                    
                    return {
                        "tracking_number": tracking_number,
                        "status": shipment_status.get("description", "Unknown"),
                        "status_code": shipment_status.get("code", ""),
                        "current_location": latest_event.get("location", "Unknown"),
                        "last_updated": latest_event.get("timestamp", ""),
                        "estimated_delivery": self._calculate_estimated_delivery(shipment_status),
                        "carrier": "naqel",
                        "delivery_attempts": tracking_data.get("delivery_attempts", 0),
                        "all_events": [
                            {
                                "timestamp": event.get("timestamp", ""),
                                "status": event.get("status", ""),
                                "location": event.get("location", ""),
                                "description": event.get("description", ""),
                                "facility": event.get("facility", "")
                            }
                            for event in tracking_events
                        ]
                    }
                else:
                    error_msg = result.get("message", "Tracking information not found")
                    raise Exception(f"Naqel Tracking Error: {error_msg}")
            
            raise Exception(f"Naqel tracking request failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Naqel tracking failed: {str(e)}")
            return {
                "tracking_number": tracking_number,
                "status": "error",
                "error": str(e),
                "carrier": "naqel"
            }
    
    def get_service_availability(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Check Naqel service availability between origin and destination
        """
        if self.mock_mode:
            return self._mock_service_availability(origin, destination)
        
        try:
            # Check if locations are in Naqel service areas
            origin_supported = self._is_location_supported(origin)
            destination_supported = self._is_location_supported(destination)
            
            if not (origin_supported and destination_supported):
                return {
                    "available": False,
                    "error": "Location not in Naqel service area",
                    "carrier": "naqel",
                    "supported_areas": self.service_areas
                }
            
            token = self._authenticate()
            if not token:
                raise Exception("Failed to authenticate with Naqel API")
            
            headers = self._get_auth_headers()
            headers["Authorization"] = f"Bearer {token}"
            
            payload = {
                "origin": origin,
                "destination": destination
            }
            
            response = requests.post(
                f"{self.base_url}/services/availability",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    services = result.get("data", {}).get("services", [])
                    return {
                        "available": True,
                        "services": services,
                        "carrier": "naqel"
                    }
            
            # Fallback to standard services if API call fails
            return self._get_standard_services()
            
        except Exception as e:
            logger.error(f"Naqel service availability check failed: {str(e)}")
            return self._get_standard_services()
    
    def cancel_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """
        Cancel a Naqel shipment
        """
        if self.mock_mode:
            return {
                "success": True,
                "tracking_number": tracking_number,
                "status": "cancelled",
                "carrier": "naqel",
                "mock_mode": True
            }
        
        try:
            token = self._authenticate()
            if not token:
                raise Exception("Failed to authenticate with Naqel API")
            
            headers = self._get_auth_headers()
            headers["Authorization"] = f"Bearer {token}"
            
            response = requests.delete(
                f"{self.base_url}/shipments/{tracking_number}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    return {
                        "success": True,
                        "tracking_number": tracking_number,
                        "status": "cancelled",
                        "carrier": "naqel"
                    }
                else:
                    error_msg = result.get("message", "Cancellation failed")
                    raise Exception(f"Naqel Cancellation Error: {error_msg}")
            
            raise Exception(f"Naqel cancellation request failed: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Naqel shipment cancellation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "carrier": "naqel"
            }
    
    def _is_location_supported(self, location: str) -> bool:
        """Check if location is in Naqel service areas"""
        location_lower = location.lower()
        for country_cities in self.service_areas.values():
            for city in country_cities:
                if city.lower() in location_lower or location_lower in city.lower():
                    return True
        return False
    
    def _get_standard_services(self) -> Dict[str, Any]:
        """Return standard Naqel services as fallback"""
        return {
            "available": True,
            "services": [
                {
                    "service_type": "EXPRESS",
                    "estimated_days": "1-2",
                    "cost_estimate": "30-50 SAR",
                    "description": "Next day delivery for major cities"
                },
                {
                    "service_type": "STANDARD",
                    "estimated_days": "2-4",
                    "cost_estimate": "20-35 SAR",
                    "description": "Standard delivery service"
                },
                {
                    "service_type": "ECONOMY",
                    "estimated_days": "3-5",
                    "cost_estimate": "15-25 SAR",
                    "description": "Economical delivery option"
                }
            ],
            "carrier": "naqel"
        }
    
    def _calculate_estimated_delivery(self, status_info: Dict) -> str:
        """Calculate estimated delivery based on current status"""
        status_code = status_info.get("code", "").lower()
        status_desc = status_info.get("description", "").lower()
        
        if "delivered" in status_desc or status_code == "DEL":
            return datetime.now().isoformat()
        elif "out for delivery" in status_desc or status_code == "OFD":
            return (datetime.now() + timedelta(hours=6)).isoformat()
        elif "in transit" in status_desc or status_code == "INT":
            return (datetime.now() + timedelta(days=1)).isoformat()
        elif "at facility" in status_desc or status_code == "ATF":
            return (datetime.now() + timedelta(hours=12)).isoformat()
        else:
            return (datetime.now() + timedelta(days=2)).isoformat()
    
    # Mock methods for testing without API credentials
    def _mock_schedule_pickup(self, pickup_request: NaqelPickupRequest) -> Dict[str, Any]:
        """Mock pickup scheduling for testing"""
        import random
        tracking_number = f"NQX{random.randint(100000000, 999999999)}"
        
        return {
            "success": True,
            "tracking_number": tracking_number,
            "reference": pickup_request.reference,
            "pickup_scheduled": True,
            "estimated_pickup": pickup_request.pickup_date or (datetime.now() + timedelta(hours=3)).isoformat(),
            "carrier": "naqel",
            "service_type": pickup_request.service_type,
            "cost": {
                "amount": random.randint(20, 45),
                "currency": "SAR"
            },
            "mock_mode": True
        }
    
    def _mock_track_shipment(self, tracking_number: str) -> Dict[str, Any]:
        """Mock tracking for testing"""
        import random
        
        statuses = [
            {"code": "PKD", "description": "Package picked up"},
            {"code": "INT", "description": "In transit"},
            {"code": "ATF", "description": "At sorting facility"},
            {"code": "OFD", "description": "Out for delivery"},
            {"code": "DEL", "description": "Delivered"}
        ]
        
        locations = [
            "Riyadh Main Hub",
            "Jeddah Distribution Center",
            "Dammam Facility",
            "Mecca Sorting Center",
            "Khobar Branch"
        ]
        
        current_status = random.choice(statuses)
        current_location = random.choice(locations)
        
        return {
            "tracking_number": tracking_number,
            "status": current_status["description"],
            "status_code": current_status["code"],
            "current_location": current_location,
            "last_updated": datetime.now().isoformat(),
            "estimated_delivery": (datetime.now() + timedelta(days=1)).isoformat(),
            "carrier": "naqel",
            "delivery_attempts": 0,
            "mock_mode": True,
            "all_events": [
                {
                    "timestamp": (datetime.now() - timedelta(hours=i*2)).isoformat(),
                    "status": statuses[min(i, len(statuses)-1)]["code"],
                    "location": random.choice(locations),
                    "description": statuses[min(i, len(statuses)-1)]["description"],
                    "facility": f"{random.choice(locations)} - Processing"
                }
                for i in range(4)
            ]
        }
    
    def _mock_service_availability(self, origin: str, destination: str) -> Dict[str, Any]:
        """Mock service availability for testing"""
        return {
            "available": True,
            "services": [
                {
                    "service_type": "EXPRESS",
                    "estimated_days": "1-2",
                    "cost_estimate": "30-50 SAR",
                    "description": "Next day delivery for major cities"
                },
                {
                    "service_type": "STANDARD",
                    "estimated_days": "2-4", 
                    "cost_estimate": "20-35 SAR",
                    "description": "Standard delivery service"
                },
                {
                    "service_type": "ECONOMY",
                    "estimated_days": "3-5",
                    "cost_estimate": "15-25 SAR",
                    "description": "Economical delivery option"
                }
            ],
            "carrier": "naqel",
            "mock_mode": True
        }

# Convenience function for external usage
def create_naqel_client() -> NaqelClient:
    """Factory function to create Naqel client"""
    return NaqelClient()