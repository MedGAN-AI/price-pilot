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

# Import self-updating orchestrator system
from src.core.self_updating_orchestrator import get_orchestrator, reload_orchestrator
from src.core.agent_registry import get_agent_registry
from src.core.gemini_intent_detector import GeminiIntentDetector
from src.agents.ChatAgent.tools.memory_tools import conversation_memory
from langchain_core.messages import HumanMessage, SystemMessage

# Initialize self-updating orchestrator
orchestrator = get_orchestrator()
agent_registry = get_agent_registry()

# Helper function for the new intent detector
def get_gemini_detector():
    """Get the new Gemini intent detector"""
    return GeminiIntentDetector()

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

class FeedbackRequest(BaseModel):
    query: str = Field(..., description="Original user query")
    predicted_intent: str = Field(..., description="System's predicted intent")
    actual_intent: str = Field(..., description="User's corrected intent")
    confidence: float = Field(..., description="System's confidence level")
    user_rating: Optional[int] = Field(None, description="User rating (1-5 stars)", ge=1, le=5)
    feedback_notes: Optional[str] = Field(None, description="Optional user feedback notes")

class FeedbackResponse(BaseModel):
    success: bool = Field(..., description="Whether feedback was collected successfully")
    message: str = Field(..., description="Response message")

class AnalyticsResponse(BaseModel):
    period: str = Field(..., description="Analytics period")
    overall_accuracy: float = Field(..., description="Overall prediction accuracy")
    total_feedback_entries: int = Field(..., description="Total feedback entries")
    intent_performance: Dict[str, Any] = Field(..., description="Performance by intent")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Improvement suggestions")

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
    """Health check endpoint with self-updating orchestrator"""
    try:
        # Get system status from orchestrator
        system_status = orchestrator.get_system_status()
        
        agents_status = system_status.get("agent_status", {})
        overall_status = "healthy" if all("✅" in status for status in agents_status.values()) else "degraded"
        
        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now().isoformat(),
            version="2.1.0-dynamic",
            agents_status=agents_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Self-updating chat endpoint - automatically adapts to agent changes
    """
    try:
        logger.info(f"Processing chat request: {request.message[:100]}...")
        
        # Process through self-updating orchestrator
        result = orchestrator.process_query(
            query=request.message,
            session_id=request.session_id
        )
        
        # Save to memory for context continuity
        conversation_memory.add_interaction(request.message, result["response"])
        
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            intent=result["intent"],
            confidence=result["confidence"],
            agent_used=result["agent_used"],
            timestamp=result["timestamp"]
        )
            
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        
        # Generate helpful error response
        error_response = orchestrator._generate_fallback_response(request.message, str(e))
        
        return ChatResponse(
            response=error_response,
            session_id=request.session_id or f"error_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            intent="error",
            confidence=0.0,
            agent_used="ErrorHandler",
            timestamp=datetime.now().isoformat()
        )

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
            "timestamp": datetime.now().isoformat(),
            "system_status": orchestrator.get_system_status(),
            "registry_info": agent_registry.get_registry_info()
        }
    except Exception as e:
        logger.error(f"Agent status error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting agent status: {str(e)}")

# System management endpoints
@app.post("/system/reload")
async def reload_system():
    """Reload the entire agent system (for development)"""
    try:
        orchestrator.reload_system()
        return {
            "status": "success",
            "message": "System reloaded successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"System reload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error reloading system: {str(e)}")

@app.post("/agents/{agent_name}/reload")
async def reload_agent(agent_name: str):
    """Reload a specific agent"""
    try:
        agent_registry.reload_agent(agent_name)
        return {
            "status": "success", 
            "message": f"Agent {agent_name} reloaded successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Agent reload error: {e}")
        raise HTTPException(status_code=500, detail=f"Error reloading agent {agent_name}: {str(e)}")

@app.get("/system/config")
async def get_system_config():
    """Get current system configuration"""
    try:
        return {
            "config": orchestrator.config,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Config retrieval error: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving config: {str(e)}")
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

# ==================== FEEDBACK COLLECTION ENDPOINTS ====================

@app.post("/feedback/collect", response_model=FeedbackResponse)
async def collect_feedback(feedback: FeedbackRequest):
    """
    Collect user feedback for intent prediction improvement
    """
    try:
        gemini_detector = get_gemini_detector()
        
        success = gemini_detector.collect_feedback(
            query=feedback.query,
            predicted_intent=feedback.predicted_intent,
            actual_intent=feedback.actual_intent,
            confidence=feedback.confidence,
            user_rating=feedback.user_rating,
            feedback_notes=feedback.feedback_notes
        )
        
        if success:
            logger.info(f"✅ Feedback collected for query: '{feedback.query[:50]}...'")
            return FeedbackResponse(
                success=True,
                message="Feedback collected successfully. Thank you for helping us improve!"
            )
        else:
            return FeedbackResponse(
                success=False,
                message="Failed to collect feedback. Please try again."
            )
            
    except Exception as e:
        logger.error(f"Failed to collect feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect feedback: {str(e)}")

@app.get("/feedback/analytics", response_model=AnalyticsResponse)
async def get_feedback_analytics():
    """
    Get comprehensive feedback analytics and performance metrics
    """
    try:
        gemini_detector = get_gemini_detector()
        analytics = gemini_detector.get_feedback_analytics()
        
        if analytics.get("status") == "No feedback data available":
            return AnalyticsResponse(
                period="No data",
                overall_accuracy=0.0,
                total_feedback_entries=0,
                intent_performance={},
                improvement_suggestions=[{
                    "issue": "No feedback data available",
                    "suggestion": "Start collecting user feedback to enable analytics",
                    "priority": "high"
                }]
            )
        
        return AnalyticsResponse(
            period=analytics.get("period", "Unknown"),
            overall_accuracy=analytics.get("overall_accuracy", 0.0),
            total_feedback_entries=analytics.get("total_feedback_entries", 0),
            intent_performance=analytics.get("intent_performance", {}),
            improvement_suggestions=analytics.get("improvement_suggestions", [])
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@app.post("/feedback/optimize")
async def auto_optimize_system():
    """
    Automatically optimize the system based on collected feedback
    """
    try:
        gemini_detector = get_gemini_detector()
        optimization_results = gemini_detector.auto_optimize_from_feedback()
        
        logger.info("🔧 System optimization completed")
        return {
            "success": True,
            "message": "System optimization completed",
            "optimization_results": optimization_results
        }
        
    except Exception as e:
        logger.error(f"Failed to optimize system: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to optimize system: {str(e)}")

@app.get("/feedback/stats")
async def get_feedback_stats():
    """
    Get basic feedback statistics
    """
    try:
        gemini_detector = get_gemini_detector()
        stats = gemini_detector.get_performance_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# ==================== GEMINI DETECTOR ENDPOINTS ====================

@app.get("/detector/status")
async def get_detector_status():
    """
    Get Gemini detector status and configuration
    """
    try:
        gemini_detector = get_gemini_detector()
        stats = gemini_detector.get_performance_stats()
        
        return {
            "detector_type": "Gemini Embeddings",
            "model": stats.get("gemini_model", "text-embedding-004"),
            "status": "active",
            "similarity_threshold": stats.get("similarity_threshold", 0.4),
            "intents_configured": stats.get("intents_configured", 0),
            "total_predictions": stats.get("total_predictions", 0),
            "feedback_entries": stats.get("total_feedback_entries", 0),
            "recent_accuracy": stats.get("recent_accuracy"),
            "learning_enabled": stats.get("learning_enabled", True)
        }
        
    except Exception as e:
        logger.error(f"Failed to get detector status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get detector status: {str(e)}")

@app.post("/detector/reload")
async def reload_detector():
    """
    Reload the Gemini detector system
    """
    try:
        gemini_detector = get_gemini_detector()
        gemini_detector.reload_system()
        
        logger.info("🔄 Gemini detector reloaded")
        return {
            "success": True,
            "message": "Gemini detector reloaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to reload detector: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload detector: {str(e)}")

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
