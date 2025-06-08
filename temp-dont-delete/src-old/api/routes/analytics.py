from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

# Create router
router = APIRouter(prefix="/analytics", tags=["analytics"])

# Models
class MetricResponse(BaseModel):
    name: str
    value: float
    comparison: Optional[float] = None
    change_percent: Optional[float] = None

class TimeSeriesPoint(BaseModel):
    date: datetime
    value: float

class TimeSeriesData(BaseModel):
    metric: str
    data: List[TimeSeriesPoint]
    
class RecommendationImpact(BaseModel):
    revenue_impact: float
    margin_impact: float
    confidence_score: float

# Mock data
def generate_mock_timeseries(days: int, base_value: float, volatility: float = 0.1):
    """Generate mock time series data for testing"""
    data = []
    current_value = base_value
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        # Add some randomness to the value
        change = (0.5 - float(i % 3) / 3) * volatility * base_value
        current_value = max(0, current_value + change)
        data.append({"date": date, "value": round(current_value, 2)})
        
    return data

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    days: int = Query(30, description="Number of days to include in the analysis")
):
    """
    Get summary metrics for the dashboard
    """
    # In a real application, these would be calculated from actual data
    start_date = datetime.now() - timedelta(days=days)
    
    # Mock data for development
    return {
        "key_metrics": [
            {
                "name": "Average Margin",
                "value": 42.5,
                "comparison": 39.8,
                "change_percent": 6.8
            },
            {
                "name": "Revenue",
                "value": 125430.75,
                "comparison": 118650.20,
                "change_percent": 5.7
            },
            {
                "name": "Price Recommendations",
                "value": 87,
                "comparison": 62,
                "change_percent": 40.3
            },
            {
                "name": "Products Optimized",
                "value": 76,
                "comparison": 58,
                "change_percent": 31.0
            }
        ],
        "time_series": [
            {
                "metric": "Daily Revenue",
                "data": generate_mock_timeseries(days, 4500, 0.08)
            },
            {
                "metric": "Average Margin %",
                "data": generate_mock_timeseries(days, 40, 0.04)
            }
        ]
    }

@router.get("/revenue-forecast", response_model=TimeSeriesData)
async def get_revenue_forecast(days_ahead: int = Query(14, description="Days to forecast")):
    """
    Get revenue forecast for the upcoming period
    """
    # This would normally call the ML model
    forecast_data = generate_mock_timeseries(days_ahead, 4700, 0.1)
    
    return {
        "metric": "Revenue Forecast",
        "data": forecast_data
    }

@router.get("/price-elasticity/{product_id}", response_model=Dict[str, Any])
async def get_price_elasticity(product_id: int):
    """
    Get price elasticity data for a specific product
    """
    # Check if product exists (would use a database in production)
    if product_id not in [1, 2]:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Mock elasticity data
    price_points = [
        {"price": 14.99, "demand": 120, "revenue": 1798.80},
        {"price": 16.99, "demand": 105, "revenue": 1783.95},
        {"price": 19.99, "demand": 100, "revenue": 1999.00},
        {"price": 21.99, "demand": 85, "revenue": 1869.15},
        {"price": 24.99, "demand": 65, "revenue": 1624.35}
    ]
    
    elasticity = -1.2 if product_id == 1 else -0.8
    
    return {
        "product_id": product_id,
        "elasticity_coefficient": elasticity,
        "price_points": price_points,
        "optimal_price": 19.99 if product_id == 1 else 21.99,
        "confidence_score": 0.85
    }

@router.get("/recommendation-impact", response_model=RecommendationImpact)
async def get_recommendation_impact():
    """
    Get the estimated impact of current price recommendations
    """
    return {
        "revenue_impact": 12450.75,
        "margin_impact": 3250.40,
        "confidence_score": 0.82
    }