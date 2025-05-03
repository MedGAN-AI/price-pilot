from fastapi import APIRouter, HTTPException, Query, Depends, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import os
import json

# In a real app, this would import the ML model
# from src.ml.inference.price_recommendation import get_price_recommendation

# Create router
router = APIRouter(prefix="/pricing", tags=["pricing"])

# Models
class PriceRecommendationRequest(BaseModel):
    product_id: int
    current_price: float
    cost: float
    category: str
    competitor_prices: Optional[List[float]] = None
    historical_sales: Optional[List[Dict[str, Any]]] = None
    
class PriceRecommendationResponse(BaseModel):
    product_id: int
    current_price: float
    recommended_price: float
    min_price: float
    max_price: float
    confidence_score: float = Field(..., ge=0, le=1)
    estimated_demand: float
    estimated_revenue: float
    estimated_profit: float
    rationale: str
    timestamp: datetime

class BulkRecommendationRequest(BaseModel):
    products: List[PriceRecommendationRequest]
    
# Mock price recommendation function (would be replaced with actual ML model)
def mock_price_recommendation(request: PriceRecommendationRequest) -> PriceRecommendationResponse:
    """Generate a mock price recommendation"""
    # In production, this would call the ML model
    
    # Simple logic for demonstration
    if request.competitor_prices and len(request.competitor_prices) > 0:
        avg_competitor = sum(request.competitor_prices) / len(request.competitor_prices)
    else:
        avg_competitor = request.current_price * 1.05
    
    # Calculate mock recommendation based on cost, current price and competitor prices
    markup_factor = 1.4  # 40% markup
    cost_based = request.cost * markup_factor
    competitor_based = avg_competitor * 0.95  # Slightly below competitors
    
    # Balance between cost-based and competitor-based
    recommended = (cost_based + competitor_based) / 2
    
    # Constrain to reasonable bounds
    min_price = max(request.cost * 1.1, request.current_price * 0.8)
    max_price = request.current_price * 1.2
    
    recommended = max(min(recommended, max_price), min_price)
    
    # Generate mock demand and revenue projections
    base_demand = 100  # Units per period
    price_elasticity = -1.2  # Negative elasticity coefficient
    
    # Calculate demand based on price change
    price_change_pct = (recommended - request.current_price) / request.current_price
    demand_change_pct = price_change_pct * price_elasticity
    estimated_demand = base_demand * (1 + demand_change_pct)
    
    # Calculate revenue and profit
    estimated_revenue = recommended * estimated_demand
    estimated_profit = (recommended - request.cost) * estimated_demand
    
    # Generate rationale
    rationale_parts = []
    if recommended > request.current_price:
        rationale_parts.append(f"Recommendation is to increase price by {((recommended/request.current_price)-1)*100:.1f}%")
    else:
        rationale_parts.append(f"Recommendation is to decrease price by {((1-(recommended/request.current_price)))*100:.1f}%")
    
    if avg_competitor > recommended:
        rationale_parts.append(f"This keeps us below average competitor price of ${avg_competitor:.2f}")
    
    rationale_parts.append(f"Expected demand at this price: {estimated_demand:.1f} units")
    rationale_parts.append(f"Projected profit: ${estimated_profit:.2f}")
    
    rationale = ". ".join(rationale_parts)
    
    # Return recommendation
    return PriceRecommendationResponse(
        product_id=request.product_id,
        current_price=request.current_price,
        recommended_price=round(recommended, 2),
        min_price=round(min_price, 2),
        max_price=round(max_price, 2),
        confidence_score=0.85,  # Mock confidence score
        estimated_demand=round(estimated_demand, 1),
        estimated_revenue=round(estimated_revenue, 2),
        estimated_profit=round(estimated_profit, 2),
        rationale=rationale,
        timestamp=datetime.now()
    )

@router.post("/recommend", response_model=PriceRecommendationResponse)
async def get_price_recommendation(request: PriceRecommendationRequest):
    """
    Get a price recommendation for a single product
    """
    try:
        # In production, this would use the ML model
        recommendation = mock_price_recommendation(request)
        return recommendation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendation: {str(e)}")

@router.post("/bulk-recommend", response_model=List[PriceRecommendationResponse])
async def get_bulk_recommendations(request: BulkRecommendationRequest):
    """
    Get price recommendations for multiple products at once
    """
    recommendations = []
    
    for product_request in request.products:
        try:
            recommendation = mock_price_recommendation(product_request)
            recommendations.append(recommendation)
        except Exception as e:
            # In production, you might want to handle errors differently
            # For now, we'll just continue with the next product
            continue
    
    return recommendations

@router.post("/apply/{product_id}")
async def apply_recommendation(
    product_id: int,
    recommended_price: float = Body(..., embed=True)
):
    """
    Apply a price recommendation to a product
    """
    # In production, this would update the product price in the database
    # For now, we'll just return a confirmation
    return {
        "status": "success",
        "message": f"Price for product {product_id} updated to ${recommended_price:.2f}",
        "applied_at": datetime.now().isoformat()
    }

@router.get("/history/{product_id}", response_model=List[Dict[str, Any]])
async def get_pricing_history(
    product_id: int,
    days: int = Query(30, description="Number of days of history to retrieve")
):
    """
    Get price change history for a product
    """
    # In production, this would query the database
    # For now, we'll generate mock data
    
    # Simple mock data
    mock_history = [
        {
            "date": (datetime.now() - timedelta(days=i)).isoformat(),
            "price": round(19.99 * (1 + (i % 3 - 1) * 0.05), 2),
            "changed_by": "system" if i % 2 == 0 else "manual",
            "rationale": "Competitive pricing adjustment" if i % 2 == 0 else "Manual override"
        }
        for i in range(min(days, 10))  # Limit to 10 entries for mock data
    ]
    
    return mock_history