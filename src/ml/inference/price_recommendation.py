import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# In production, these would be actual trained models
# For development, we'll create simple placeholder models

class DemandForecastModel:
    """Placeholder for demand forecasting model"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize demand forecasting model
        
        In production, this would load a trained model from disk
        For development, we'll implement a simple model
        """
        self.model_path = model_path
        self.elasticity_coefficients = {
            "Apparel": -1.2,
            "Electronics": -0.8,
            "Home": -1.0,
            "Beauty": -1.5,
            "Food": -2.1,
            "default": -1.0
        }
    
    def predict(self, 
                product_id: int, 
                price: float, 
                current_price: float,
                category: str,
                historical_sales: Optional[List[Dict[str, Any]]] = None) -> float:
        """
        Predict demand at a given price point
        
        Args:
            product_id: Unique identifier for the product
            price: Price point to forecast demand for
            current_price: Current price of the product
            category: Product category
            historical_sales: Historical sales data (optional)
            
        Returns:
            Forecasted demand (units)
        """
        # Get baseline demand (would be based on historical data in production)
        baseline_demand = 100
        
        # Get price elasticity for the category
        elasticity = self.elasticity_coefficients.get(category, 
                                                     self.elasticity_coefficients["default"])
        
        # Calculate price change percentage
        price_change_pct = (price - current_price) / current_price
        
        # Calculate demand change based on elasticity
        demand_change_pct = price_change_pct * elasticity
        
        # Apply demand change to baseline
        predicted_demand = baseline_demand * (1 + demand_change_pct)
        
        # Add some randomness to simulate model uncertainty
        noise = np.random.normal(0, 0.05)  # 5% noise
        predicted_demand *= (1 + noise)
        
        return max(0, predicted_demand)  # Ensure non-negative


class PriceElasticityModel:
    """Placeholder for price elasticity model"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize price elasticity model
        
        In production, this would load a trained model from disk
        For development, we'll implement a simple model
        """
        self.model_path = model_path
        
    def predict_elasticity(self, 
                          product_id: int,
                          category: str,
                          features: Dict[str, Any]) -> float:
        """
        Predict price elasticity for a product
        
        Args:
            product_id: Unique identifier for the product
            category: Product category
            features: Additional features for prediction
            
        Returns:
            Price elasticity coefficient (negative number)
        """
        # In production, this would use a trained model
        # For development, we'll use category-based coefficients
        elasticity_map = {
            "Apparel": -1.2,
            "Electronics": -0.8,
            "Home": -1.0,
            "Beauty": -1.5,
            "Food": -2.1
        }
        
        # Get elasticity for the category, default to -1.0
        elasticity = elasticity_map.get(category, -1.0)
        
        # Add some randomness to simulate model uncertainty
        noise = np.random.normal(0, 0.1)  # 10% noise
        elasticity *= (1 + noise)
        
        return elasticity


class PriceRecommender:
    """Main price recommendation engine"""
    
    def __init__(self, 
                 demand_model_path: Optional[str] = None,
                 elasticity_model_path: Optional[str] = None):
        """
        Initialize price recommendation engine
        
        Args:
            demand_model_path: Path to demand forecasting model
            elasticity_model_path: Path to price elasticity model
        """
        self.demand_model = DemandForecastModel(demand_model_path)
        self.elasticity_model = PriceElasticityModel(elasticity_model_path)
    
    def _evaluate_price_point(self,
                              price: float,
                              product_id: int,
                              current_price: float,
                              cost: float,
                              category: str,
                              historical_sales: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
        """
        Evaluate a single price point
        
        Args:
            price: Price point to evaluate
            product_id: Unique identifier for the product
            current_price: Current price of the product
            cost: Product cost
            category: Product category
            historical_sales: Historical sales data (optional)
            
        Returns:
            Dictionary with evaluation metrics
        """
        # Predict demand at this price
        demand = self.demand_model.predict(
            product_id=product_id,
            price=price,
            current_price=current_price,
            category=category,
            historical_sales=historical_sales
        )
        
        # Calculate revenue and profit
        revenue = price * demand
        profit = (price - cost) * demand
        margin = (price - cost) / price if price > 0 else 0
        
        return {
            "price": price,
            "demand": demand,
            "revenue": revenue,
            "profit": profit,
            "margin": margin
        }
    
    def generate_recommendation(self,
                               product_id: int,
                               current_price: float,
                               cost: float,
                               category: str,
                               competitor_prices: Optional[List[float]] = None,
                               historical_sales: Optional[List[Dict[str, Any]]] = None,
                               optimization_goal: str = "profit") -> Dict[str, Any]:
        """
        Generate price recommendation
        
        Args:
            product_id: Unique identifier for the product
            current_price: Current price of the product
            cost: Product cost
            category: Product category
            competitor_prices: List of competitor prices (optional)
            historical_sales: Historical sales data (optional)
            optimization_goal: What to optimize for ("profit", "revenue", or "margin")
            
        Returns:
            Dictionary with recommendation details
        """
        # Get features for elasticity prediction
        features = {
            "cost": cost,
            "current_price": current_price,
            "price_to_cost_ratio": current_price / cost if cost > 0 else 0,
        }
        
        if competitor_prices and len(competitor_prices) > 0:
            features["avg_competitor_price"] = sum(competitor_prices) / len(competitor_prices)
            features["min_competitor_price"] = min(competitor_prices)
            features["max_competitor_price"] = max(competitor_prices)
            features["price_gap_to_competitors"] = features["avg_competitor_price"] - current_price
        
        # Get price elasticity
        elasticity = self.elasticity_model.predict_elasticity(
            product_id=product_id,
            category=category,
            features=features
        )
        
        # Generate price points to evaluate
        # Start with a range around current price
        min_price = max(cost * 1.1, current_price * 0.7)  # Ensure minimum margin
        max_price = current_price * 1.5
        
        # If we have competitor prices, use them to refine the range
        if competitor_prices and len(competitor_prices) > 0:
            min_competitor = min(competitor_prices)
            max_competitor = max(competitor_prices)
            
            # Extend range based on competitor prices
            min_price = min(min_price, min_competitor * 0.9)
            max_price = max(max_price, max_competitor * 1.1)
        
        # Generate price points
        step = (max_price - min_price) / 10
        price_points = [min_price + i * step for i in range(11)]  # 11 price points
        
        # Evaluate each price point
        evaluations = [
            self._evaluate_price_point(
                price=price,
                product_id=product_id,
                current_price=current_price,
                cost=cost,
                category=category,
                historical_sales=historical_sales
            )
            for price in price_points
        ]
        
        # Select best price based on optimization goal
        if optimization_goal == "revenue":
            evaluations.sort(key=lambda x: x["revenue"], reverse=True)
        elif optimization_goal == "margin":
            evaluations.sort(key=lambda x: x["margin"], reverse=True)
        else:  # Default to profit
            evaluations.sort(key=lambda x: x["profit"], reverse=True)
        
        best_evaluation = evaluations[0]
        recommended_price = best_evaluation["price"]
        
        # Generate rationale
        rationale_parts = []
        
        if recommended_price > current_price:
            change_pct = ((recommended_price / current_price) - 1) * 100
            rationale_parts.append(f"Recommendation is to increase price by {change_pct:.1f}%")
        else:
            change_pct = ((current_price / recommended_price) - 1) * 100
            rationale_parts.append(f"Recommendation is to decrease price by {change_pct:.1f}%")
        
        if "avg_competitor_price" in features:
            if features["avg_competitor_price"] > recommended_price:
                rationale_parts.append(
                    f"This keeps us below average competitor price of ${features['avg_competitor_price']:.2f}"
                )
            else:
                rationale_parts.append(
                    f"Our recommended price is above average competitor price of ${features['avg_competitor_price']:.2f} due to strong demand elasticity"
                )
        
        rationale_parts.append(f"Price elasticity: {elasticity:.2f}")
        rationale_parts.append(f"Expected demand at this price: {best_evaluation['demand']:.1f} units")
        rationale_parts.append(f"Projected profit: ${best_evaluation['profit']:.2f}")
        
        rationale = ". ".join(rationale_parts)
        
        # Calculate confidence score (would be model-based in production)
        # For development, we'll use a simple heuristic
        confidence_base = 0.8  # Base confidence
        
        # Reduce confidence for prices far from current
        price_change_factor = abs(recommended_price - current_price) / current_price
        confidence_adj = -0.1 * min(1, price_change_factor)  # Max penalty of 0.1
        
        # Adjust confidence based on elasticity certainty (would be model-based)
        elasticity_certainty = 0.05  # Mock adjustment
        
        confidence_score = min(0.95, max(0.6, confidence_base + confidence_adj + elasticity_certainty))
        
        # Format response
        return {
            "product_id": product_id,
            "current_price": current_price,
            "recommended_price": round(recommended_price, 2),
            "min_price": round(min_price, 2),
            "max_price": round(max_price, 2),
            "price_elasticity": round(elasticity, 2),
            "confidence_score": round(confidence_score, 2),
            "estimated_demand": round(best_evaluation["demand"], 1),
            "estimated_revenue": round(best_evaluation["revenue"], 2),
            "estimated_profit": round(best_evaluation["profit"], 2),
            "optimization_goal": optimization_goal,
            "rationale": rationale,
            "evaluations": evaluations,
            "timestamp": datetime.now().isoformat()
        }

# Instantiate the recommender
recommender = None

def get_price_recommendation(
    product_id: int,
    current_price: float,
    cost: float,
    category: str,
    competitor_prices: Optional[List[float]] = None,
    historical_sales: Optional[List[Dict[str, Any]]] = None,
    optimization_goal: str = "profit"
) -> Dict[str, Any]:
    """
    Get price recommendation for a product
    
    Args:
        product_id: Unique identifier for the product
        current_price: Current price of the product
        cost: Product cost
        category: Product category
        competitor_prices: List of competitor prices (optional)
        historical_sales: Historical sales data (optional)
        optimization_goal: What to optimize for ("profit", "revenue", or "margin")
        
    Returns:
        Dictionary with recommendation details
    """
    global recommender
    
    # Lazy load the recommender
    if recommender is None:
        # Get model paths from environment variables or use defaults
        demand_model_path = os.environ.get("DEMAND_MODEL_PATH", "models/demand_forecast.joblib")
        elasticity_model_path = os.environ.get("ELASTICITY_MODEL_PATH", "models/price_elasticity.joblib")
        
        # Initialize the recommender
        recommender = PriceRecommender(
            demand_model_path=demand_model_path,
            elasticity_model_path=elasticity_model_path
        )
    
    # Generate recommendation
    return recommender.generate_recommendation(
        product_id=product_id,
        current_price=current_price,
        cost=cost,
        category=category,
        competitor_prices=competitor_prices,
        historical_sales=historical_sales,
        optimization_goal=optimization_goal
    )