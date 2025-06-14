"""Tests for OrderAgent functionality."""

import pytest
import json
from unittest.mock import Mock, patch
from src.agents.OrderAgent.tools.order_tools import (
    check_order_status_tool_func,
    create_order_tool_func,
    update_order_status_tool_func,
    cancel_order_tool_func
)


class TestOrderTools:
    """Test cases for order tools."""
    
    def test_check_order_status_valid_uuid(self):
        """Test checking order status with valid UUID."""
        with patch('src.agents.OrderAgent.tools.order_tools.order_service.get_order_status') as mock_service:
            mock_service.return_value = {
                "success": True,
                "order_id": "61e3a030-00b3-4133-97bd-74db4a88fa22",
                "status": "pending"
            }
            
            # Test with string parameter
            result = check_order_status_tool_func("61e3a030-00b3-4133-97bd-74db4a88fa22")
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["order_id"] == "61e3a030-00b3-4133-97bd-74db4a88fa22"
            
    def test_check_order_status_json_parameter(self):
        """Test checking order status with JSON parameter format."""
        with patch('src.agents.OrderAgent.tools.order_tools.order_service.get_order_status') as mock_service:
            mock_service.return_value = {
                "success": True,
                "order_id": "61e3a030-00b3-4133-97bd-74db4a88fa22",
                "status": "pending"
            }
            
            # Test with JSON string parameter
            json_param = '{"order_id": "61e3a030-00b3-4133-97bd-74db4a88fa22"}'
            result = check_order_status_tool_func(json_param)
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["order_id"] == "61e3a030-00b3-4133-97bd-74db4a88fa22"
            
    def test_check_order_status_invalid_uuid(self):
        """Test checking order status with invalid UUID."""
        with patch('src.agents.OrderAgent.tools.order_tools.order_service.get_order_status') as mock_service:
            mock_service.return_value = {
                "success": False,
                "error": "Invalid UUID format",
                "message": "Order ID must be a valid UUID"
            }
            
            result = check_order_status_tool_func("invalid-uuid")
            result_dict = json.loads(result)
            assert result_dict["success"] is False
            assert "Invalid UUID format" in result_dict["error"]
            
    def test_create_order_valid_data(self):
        """Test creating order with valid data."""
        with patch('src.agents.OrderAgent.tools.order_tools.order_service.create_order') as mock_service:
            mock_service.return_value = {
                "success": True,
                "order_id": "61e3a030-00b3-4133-97bd-74db4a88fa22",
                "status": "pending",
                "total_amount": 19.99
            }
            
            order_data = {
                "customer_email": "test@example.com",
                "customer_name": "Test User",
                "items": '[{"sku": "TSHIRT-WHT-003", "quantity": 1}]'
            }
            
            result = create_order_tool_func(json.dumps(order_data))
            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["order_id"] == "61e3a030-00b3-4133-97bd-74db4a88fa22"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
