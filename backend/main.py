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

class OrderRequest(BaseModel):
    customer_email: str = Field(..., description="Customer email")
    customer_name: str = Field(..., description="Customer full name") 
    items: str = Field(..., description="JSON string of order items")
    shipping_address: Optional[str] = Field(None, description="Shipping address")
    billing_address: Optional[str] = Field(None, description="Billing address")
    payment_method: Optional[str] = Field("credit_card", description="Payment method")

class OrderResponse(BaseModel):
    success: bool
    order_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

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
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],  # React dev servers
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

# Order management endpoint
@app.post("/order/create", response_model=OrderResponse)
async def create_order(request: OrderRequest):
    """Create a new order using the OrderAgent"""
    try:
        logger.info(f"Creating order for customer: {request.customer_email}")
        
        # Format the message for the OrderAgent
        order_message = f"""Create an order with the following details:
Customer Email: {request.customer_email}
Customer Name: {request.customer_name}  
Items: {request.items}
Shipping Address: {request.shipping_address or "TBD - Address collection needed"}
Billing Address: {request.billing_address or "TBD - Address collection needed"}
Payment Method: {request.payment_method or "credit_card"}"""

        # Process through orchestrator to reach OrderAgent
        result = orchestrator.process_query(
            query=order_message,
            session_id=f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
          # Parse the response to extract order information
        response_text = result.get('response', '')
        logger.info(f"OrderAgent response: {response_text}")  # Debug log
        
        # Look for order ID in the response - it should be in the format "Order XXXX-XXXX-XXXX has been created"
        import re
        import json
        
        # Try to find JSON in the agent response first
        json_match = re.search(r'\{[^}]*"success"[^}]*\}', response_text)
        if json_match:
            try:
                order_data = json.loads(json_match.group(0))
                if order_data.get('success'):
                    return OrderResponse(
                        success=True,
                        order_id=order_data.get('order_id'),
                        message=order_data.get('message', 'Order created successfully')
                    )
            except json.JSONDecodeError:
                pass
        
        # Updated regex patterns to match the actual response format
        order_id_patterns = [
            r'Order ([a-f0-9-]{36}) has been successfully created',  # New pattern
            r'Order ([a-f0-9-]{36}) has been created successfully',  # Original pattern
            r'([a-f0-9-]{36})[^a-f0-9-].*has been.*created',        # Flexible pattern
        ]
        
        order_id = None
        for pattern in order_id_patterns:
            match = re.search(pattern, response_text)
            if match:
                order_id = match.group(1)
                break
        
        # Check if the response indicates success
        success_indicators = [
            "has been successfully created",
            "created successfully", 
            "order has been created",
            "successfully created"
        ]
        
        is_success = any(indicator in response_text.lower() for indicator in success_indicators)
        
        if is_success:
            # If we don't have an order ID yet, try to extract any UUID from the response
            if not order_id:
                uuid_match = re.search(r'([a-f0-9-]{36})', response_text)
                order_id = uuid_match.group(1) if uuid_match else None
            
            return OrderResponse(
                success=True,
                order_id=order_id,
                message="Order created successfully"
            )        
        # If we get here, the order creation failed
        logger.error(f"Order creation failed. Full response: {response_text}")
        return OrderResponse(
            success=False,
            error="Order creation failed",
            message=f"Order processing failed. Response: {response_text[:200]}..."
        )
            
    except Exception as e:
        logger.error(f"Order creation error: {e}")
        return OrderResponse(
            success=False,
            error=str(e),
            message=f"Failed to create order: {str(e)}"
        )
