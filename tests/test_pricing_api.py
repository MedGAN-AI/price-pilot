from fastapi.testclient import TestClient
import pytest
from src.api.main import app
from src.api.routes.pricing import PriceRecommendationRequest
import json

client = TestClient(app)

def test_read_root():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "PricePilot API" in response.json()["message"]

def test_price_recommendation():
    """Test the price recommendation endpoint"""
    # Test data
    request_data = {
        "product_id": 1,
        "current_price": 19.99,
        "cost": 8.50,
        "category": "Apparel",
        "competitor_prices": [18.99, 21.99, 22.99]
    }
    
    # Make request
    response = client.post("/api/v1/pricing/recommend", json=request_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    assert "product_id" in data
    assert "current_price" in data
    assert "recommended_price" in data
    assert "min_price" in data
    assert "max_price" in data
    assert "confidence_score" in data
    assert "estimated_demand" in data
    assert "estimated_revenue" in data
    assert "estimated_profit" in data
    assert "rationale" in data
    assert "timestamp" in data
    
    # Check values
    assert data["product_id"] == request_data["product_id"]
    assert data["current_price"] == request_data["current_price"]
    assert data["recommended_price"] > 0
    assert data["confidence_score"] >= 0 and data["confidence_score"] <= 1

def test_bulk_recommendation():
    """Test the bulk recommendation endpoint"""
    # Test data
    request_data = {
        "products": [
            {
                "product_id": 1,
                "current_price": 19.99,
                "cost": 8.50,
                "category": "Apparel",
                "competitor_prices": [18.99, 21.99, 22.99]
            },
            {
                "product_id": 2,
                "current_price": 89.99,
                "cost": 45.00,
                "category": "Electronics",
                "competitor_prices": [79.99, 99.99]
            }
        ]
    }
    
    # Make request
    response = client.post("/api/v1/pricing/bulk-recommend", json=request_data)
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Check results
    assert isinstance(data, list)
    assert len(data) == len(request_data["products"])
    
    # Check each recommendation
    for i, recommendation in enumerate(data):
        product_request = request_data["products"][i]
        assert recommendation["product_id"] == product_request["product_id"]
        assert recommendation["current_price"] == product_request["current_price"]
        assert recommendation["recommended_price"] > 0

def test_apply_recommendation():
    """Test applying a price recommendation"""
    # Test data
    product_id = 1
    recommended_price = 21.99
    
    # Make request
    response = client.post(f"/api/v1/pricing/apply/{product_id}", json={"recommended_price": recommended_price})
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    
    # Check fields
    assert "status" in data
    assert "message" in data
    assert "applied_at" in data
    
    # Check values
    assert data["status"] == "success"
    assert str(product_id) in data["message"]
    assert str(recommended_price) in data["message"]