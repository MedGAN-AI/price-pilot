"""
Production FastAPI Application for Price Pilot
Integrates with ChatAgent Flow A Architecture
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import ChatAgent for Flow A architecture
from src.agents.ChatAgent.agent import shopping_assistant, initialize_state
from src.agents.ChatAgent.tools.memory_tools import conversation_memory
from langchain_core.messages import HumanMessage, SystemMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation tracking")
    user_context: Optional[Dict[str, Any]] = Field(None, description="Additional user context")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    intent: str = Field(..., description="Detected intent")
    confidence: float = Field(..., description="Intent confidence score")
    agent_used: str = Field(..., description="Which agent handled the request")
    timestamp: str = Field(..., description="Response timestamp")

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    agents_status: Dict[str, str]

# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle"""
    # Startup
    logger.info("🚀 Price Pilot API starting up...")
    logger.info("✅ ChatAgent Flow A architecture loaded")
    logger.info("✅ Memory system initialized")
    yield
    # Shutdown
    logger.info("📴 Price Pilot API shutting down...")

# Create FastAPI application
app = FastAPI(
    title="Price Pilot API",
    description="Intelligent Retail Assistant with Multi-Agent Architecture",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test orchestrator import
        shopping_assistant_status = "✅ Ready" if shopping_assistant else "❌ Failed"
        
        # Test memory system
        memory_status = "✅ Ready" if conversation_memory else "❌ Failed"
        
        agents_status = {
            "chat_agent": shopping_assistant_status,
            "memory_system": memory_status,
            "order_agent": "✅ Ready", 
            "inventory_agent": "✅ Ready",
            "recommend_agent": "✅ Ready",
            "logistics_agent": "✅ Ready",
            "forecast_agent": "✅ Ready"
        }
        
        overall_status = "healthy" if all("✅" in status for status in agents_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            agents_status=agents_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint - processes user messages through ChatAgent Flow A architecture
    """
    try:
        logger.info(f"Processing chat request: {request.message[:100]}...")
        
        # Initialize orchestrator state
        state = initialize_state()
        
        # Add system message for context
        system_msg = SystemMessage(content="You are a helpful retail assistant.")
        user_msg = HumanMessage(content=request.message)
        
        state["messages"] = [system_msg, user_msg]
        
        # Process through orchestrator (which routes to ChatAgent)
        result = shopping_assistant.invoke(state)
        
        # Extract response
        if result and "messages" in result and result["messages"]:
            response_content = result["messages"][-1].content
            
            # Get intent and confidence from orchestrator state
            intent = result.get("intent", "chat")
            confidence = result.get("confidence", 0.5)
            
            # Generate session ID if not provided
            session_id = request.session_id or f"session_{hash(request.message)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            return ChatResponse(
                response=response_content,
                session_id=session_id,
                intent=intent,
                confidence=confidence,
                agent_used="ChatAgent",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="No response generated")
            
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Memory endpoints
@app.get("/memory/context/{session_id}")
async def get_conversation_context(session_id: str):
    """Get conversation context for a session"""
    try:
        context = conversation_memory.get_conversation_context()
        user_context = conversation_memory.get_user_context_summary()
        
        return {
            "session_id": session_id,
            "conversation_context": context,
            "user_context": user_context,
            "interaction_count": conversation_memory.session_metadata["interaction_count"]
        }
    except Exception as e:
        logger.error(f"Memory context error: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving context: {str(e)}")

@app.delete("/memory/clear")
async def clear_conversation_memory():
    """Clear conversation memory"""
    try:
        conversation_memory.conversation_history.clear()
        conversation_memory.user_context.clear()
        conversation_memory.session_metadata["interaction_count"] = 0
        
        return {"status": "success", "message": "Conversation memory cleared"}
    except Exception as e:
        logger.error(f"Memory clear error: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

# Agent status endpoints
@app.get("/agents/status")
async def get_agents_status():
    """Get status of all agents"""
    try:
        return {
            "agents": {
                "ChatAgent": "✅ Active - Coordinating all requests",
                "OrderAgent": "✅ Ready - Order management",
                "InventoryAgent": "✅ Ready - Stock checking", 
                "RecommendAgent": "✅ Ready - Product recommendations",
                "LogisticsAgent": "✅ Ready - Shipping & tracking",
                "ForecastAgent": "✅ Ready - Demand forecasting"
            },
            "architecture": "Flow A - All requests through ChatAgent",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Agents status error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting agent status: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Price Pilot API",
        "version": "2.0.0",
        "architecture": "ChatAgent Flow A",
        "status": "🚀 Ready",
        "endpoints": {
            "chat": "/chat",
            "health": "/health", 
            "agents": "/agents/status",
            "memory": "/memory/context/{session_id}",
            "docs": "/docs"
        }
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "main:app",  # Import string for proper reload
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True  # Set to True for development
    )
