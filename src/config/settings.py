import os
from pydantic import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PricePilot"
    
    # Database
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # ML model paths
    DEMAND_MODEL_PATH: str = os.getenv("DEMAND_MODEL_PATH", "models/demand_forecast.joblib")
    ELASTICITY_MODEL_PATH: str = os.getenv("ELASTICITY_MODEL_PATH", "models/price_elasticity.joblib")
    
    # RAG settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "data/vector_store")
    
    class Config:
        case_sensitive = True

# Create global settings object
settings = Settings()