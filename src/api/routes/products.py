from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Create router
router = APIRouter(prefix="/products", tags=["products"])

# Models
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    base_cost: float
    current_price: float
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
class ProductCreate(ProductBase):
    sku: str
    
class ProductResponse(ProductBase):
    id: int
    sku: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Mock data for development
MOCK_PRODUCTS = [
    {
        "id": 1,
        "sku": "PROD-001",
        "name": "Premium T-shirt",
        "description": "100% cotton premium quality t-shirt",
        "category": "Apparel",
        "base_cost": 8.50,
        "current_price": 19.99,
        "min_price": 14.99,
        "max_price": 24.99,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": 2,
        "sku": "PROD-002",
        "name": "Wireless Headphones",
        "description": "Noise cancelling wireless headphones",
        "category": "Electronics",
        "base_cost": 45.00,
        "current_price": 89.99,
        "min_price": 69.99,
        "max_price": 119.99,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]

@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0, 
    limit: int = 100,
    category: Optional[str] = None
):
    """
    Retrieve products with optional filtering by category
    """
    products = MOCK_PRODUCTS
    
    # Apply category filter if provided
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    
    # Apply pagination
    products = products[skip:skip+limit]
    
    return products

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """
    Retrieve a specific product by ID
    """
    for product in MOCK_PRODUCTS:
        if product["id"] == product_id:
            return product
    
    raise HTTPException(status_code=404, detail="Product not found")

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(product: ProductCreate):
    """
    Create a new product
    """
    # This would normally interact with a database
    # For now, we'll just mock the response
    new_product = product.dict()
    new_product["id"] = len(MOCK_PRODUCTS) + 1
    new_product["created_at"] = datetime.now()
    new_product["updated_at"] = datetime.now()
    
    return new_product

@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product: ProductBase):
    """
    Update an existing product
    """
    for p in MOCK_PRODUCTS:
        if p["id"] == product_id:
            # Mock update
            updated = {**p, **product.dict(exclude_unset=True), "updated_at": datetime.now()}
            return updated
            
    raise HTTPException(status_code=404, detail="Product not found")