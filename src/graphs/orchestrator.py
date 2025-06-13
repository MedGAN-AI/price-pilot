"""
Optimized Production Orchestrator for Price Pilot
Enhanced multi-agent coordination with advanced intent detection, 
context management, and performance optimizations
"""
import os
import re
import asyncio
from typing import Any, Dict, TypedDict, Annotated, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

# Import memory system
from src.agents.ChatAgent.tools.memory_tools import ConversationMemory

# Import each agent's compiled StateGraph
from src.agents.ChatAgent.agent import shopping_assistant
from src.agents.InventoryAgent.agent import inventory_assistant
from src.agents.RecommendAgent.agent import recommend_assistant
from src.agents.ForecastAgent.agent import forecast_assistant
from src.agents.LogisticsAgent.agent import logistics_assistant
from src.agents.OrderAgent.agent import order_agent_graph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global conversation memory instance
global_memory = ConversationMemory()

class IntentDetector:
    """Advanced intent detection with machine learning-like scoring"""
    
    def __init__(self):
        # Enhanced keyword patterns with weights
        self.intent_patterns = {
            "chat": {
                "primary": ["hello", "hi", "hey", "what is my", "my name", "who am i"],
                "secondary": ["greet", "conversation", "talk", "tell me about", "remember"],
                "context": ["name", "email", "preferences", "context", "memory"],
                "weight": 1.0
            },
            "inventory": {
                "primary": ["stock", "inventory", "available", "in stock", "quantity"],
                "secondary": ["how many", "units", "left", "remaining", "supply"],
                "context": ["check", "show", "tell me", "display"],
                "weight": 1.0
            },
            "recommend": {
                "primary": ["recommend", "suggest", "find", "looking for", "need"],
                "secondary": ["want", "show me", "similar", "like", "best", "good"],
                "context": ["help me", "what", "which", "any"],
                "weight": 1.0
            },
            "order": {
                "primary": ["order", "buy", "purchase", "place order", "checkout"],
                "secondary": ["cart", "add to cart", "get", "take"],
                "context": ["SHOES-", "TSHIRT-", "HAT-", "SOCKS-", "product"],
                "weight": 1.2  # Higher weight for transactional intent
            },
            "logistics": {
                "primary": ["track", "shipping", "delivery", "shipment"],
                "secondary": ["where is", "when will", "arrive", "status"],
                "context": ["my order", "package", "tracking"],
                "weight": 1.1
            },
            "forecast": {
                "primary": ["forecast", "predict", "future", "trend"],
                "secondary": ["projection", "demand", "sales", "analytics"],
                "context": ["what will", "expected", "anticipated"],
                "weight": 0.9
            }
        }
        
        # Cache for performance
        self._intent_cache = {}
        self._cache_expiry = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def detect_intent(self, text: str) -> Dict[str, Any]:
        """
        Advanced intent detection with caching and contextual scoring
        """
        # Check cache first
        cache_key = hash(text.lower().strip())
        if (cache_key in self._intent_cache and 
            datetime.now() - self._cache_expiry.get(cache_key, datetime.min) < self.cache_ttl):
            return self._intent_cache[cache_key]
        
        lower_text = text.lower()
        scores = {}
        
        # CRITICAL FIX: Check for explicit order patterns first
        # Pattern: SKU, quantity, email (in any order)
        sku_pattern = re.search(r'[A-Z]+-[A-Z]+-\d{3}', text)
        email_pattern = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9-.]+', text)
        quantity_pattern = re.search(r'\b\d+\b', text)
        
        if sku_pattern and email_pattern and quantity_pattern:
            # This is definitely an order - override everything else
            result = {
                "intent": "order",
                "confidence": 0.95,
                "all_scores": {"order": 10.0},
                "detected_entities": self._extract_entities(text),
                "order_details": {
                    "sku": sku_pattern.group(),
                    "email": email_pattern.group(),
                    "quantity": quantity_pattern.group()
                }
            }
            
            # Cache the result
            self._intent_cache[cache_key] = result
            self._cache_expiry[cache_key] = datetime.now()
            
            return result
        
        # Advanced scoring algorithm for other intents
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            
            # Primary keywords (high weight)
            for keyword in patterns["primary"]:
                if keyword in lower_text:
                    score += 3.0
                elif self._fuzzy_match(keyword, lower_text):
                    score += 2.0
            
            # Secondary keywords (medium weight)
            for keyword in patterns["secondary"]:
                if keyword in lower_text:
                    score += 2.0
                elif self._fuzzy_match(keyword, lower_text):
                    score += 1.0
            
            # Context keywords (low weight but important)
            for keyword in patterns["context"]:
                if keyword in lower_text:
                    score += 1.0
            
            # Apply intent weight
            score *= patterns["weight"]
            
            # Length penalty for very short queries
            if len(text.strip()) < 5:
                score *= 0.8
            
            # Boost for complete phrases
            if any(phrase in lower_text for phrase in patterns["primary"]):
                score *= 1.2
            
            if score > 0:
                scores[intent] = score
        
        # Determine best intent with confidence
        if scores:
            best_intent = max(scores, key=scores.get)
            max_score = scores[best_intent]
            total_score = sum(scores.values())
            
            # Calculate confidence with better normalization
            confidence = min(max_score / (total_score + 1), 0.95)
            
            # Boost confidence if intent is clearly dominant
            if max_score > sum(v for k, v in scores.items() if k != best_intent):
                confidence = min(confidence * 1.3, 0.95)
        else:
            best_intent = "chat"
            confidence = 0.5
        
        result = {
            "intent": best_intent,
            "confidence": confidence,
            "all_scores": scores,
            "detected_entities": self._extract_entities(text)
        }
        
        # Cache the result
        self._intent_cache[cache_key] = result
        self._cache_expiry[cache_key] = datetime.now()
        
        return result
    
    def _fuzzy_match(self, keyword: str, text: str, threshold: float = 0.8) -> bool:
        """Simple fuzzy matching for typos"""
        for word in text.split():
            if len(word) >= 3 and keyword in word:
                return True
        return False
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities like product codes, numbers, etc."""
        entities = {
            "product_codes": re.findall(r'[A-Z]+-\w+', text),
            "numbers": re.findall(r'\b\d+\b', text),
            "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        }
        return {k: v for k, v in entities.items() if v}

class ContextManager:
    """Advanced context management for better conversation flow with persistent memory"""
    
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.conversation_patterns = defaultdict(int)
        self.user_preferences = defaultdict(dict)
        self.session_data = {}
        self.pending_orders = {}  # Track incomplete orders
        self.user_sessions = {}   # Track user-specific sessions
    
    def update_context(self, state: Dict[str, Any], query: str, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update and enrich user context with memory persistence"""
        session_id = self._get_session_id(query, intent_result)
        
        # Build comprehensive context
        context = {
            "current_query": query,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "query_length": len(query),
            "query_complexity": self._assess_complexity(query),
            "detected_entities": intent_result.get("detected_entities", {}),
            "intent_confidence": intent_result.get("confidence", 0.0),
            "conversation_turn": len(state.get("conversation_history", [])) + 1
        }
        
        # CRITICAL FIX: Handle order context persistence
        if intent_result["intent"] == "order":
            context["is_order_request"] = True
            
            # Check if this is order details following a product listing
            if hasattr(intent_result, 'order_details'):
                context["order_details"] = intent_result['order_details']
                context["order_ready"] = True
            elif self._has_pending_order(session_id):
                context["pending_order"] = self.pending_orders[session_id]
                context["order_continuation"] = True
            else:
                # This is a new order request
                self.pending_orders[session_id] = {
                    "started_at": datetime.now().isoformat(),
                    "status": "initiated"
                }
                context["order_initiated"] = True
        
        # Track conversation patterns
        intent = intent_result["intent"]
        self.conversation_patterns[intent] += 1
        context["intent_frequency"] = dict(self.conversation_patterns)
        
        # Add session continuity with enhanced memory
        if session_id in self.session_data:
            session = self.session_data[session_id]
            context["previous_intents"] = session.get("intents", [])[-5:]
            context["session_duration"] = (
                datetime.now() - 
                datetime.fromisoformat(session["start_time"])
            ).total_seconds()
            
            # Maintain conversation flow context
            recent_intents = [i["intent"] for i in session.get("intents", [])[-3:]]
            if "order" in recent_intents and intent_result["intent"] != "order":
                # User might be continuing an order process
                context["potential_order_continuation"] = True
                
        else:
            self.session_data[session_id] = {
                "start_time": datetime.now().isoformat(),
                "intents": [],
                "user_preferences": {}
            }
            context["previous_intents"] = []
            context["session_duration"] = 0
        
        # Update session data with enhanced tracking
        self.session_data[session_id]["intents"].append({
            "intent": intent,
            "timestamp": context["timestamp"],
            "confidence": intent_result["confidence"],
            "entities": intent_result.get("detected_entities", {}),
            "query": query[:100]  # Store truncated query for context
        })
        
        return context
    
    def _has_pending_order(self, session_id: str) -> bool:
        """Check if there's a pending order for this session"""
        return session_id in self.pending_orders
    
    def _get_session_id(self, query: str, intent_result: Dict[str, Any]) -> str:
        """Generate or retrieve session ID with user context"""
        # Try to identify user by email if present
        entities = intent_result.get("detected_entities", {})
        emails = entities.get("emails", [])
        
        if emails:
            # Use email-based session for continuity
            email_hash = hash(emails[0])
            return f"user_{email_hash}_{datetime.now().strftime('%Y%m%d')}"[:20]
        
        # Fallback to query-based session
        return f"session_{hash(query[:50])}_{datetime.now().strftime('%Y%m%d')}"[:16]
    
    def _assess_complexity(self, query: str) -> float:
        """Assess query complexity for better routing"""
        complexity_factors = [
            len(query.split()) / 20,  # Word count
            len(re.findall(r'[?!]', query)) * 0.1,  # Question marks/exclamations
            len(re.findall(r'\band\b|\bor\b', query.lower())) * 0.2,  # Conjunctions
            len(re.findall(r'\d+', query)) * 0.1,  # Numbers
        ]
        return min(sum(complexity_factors), 1.0)

# Enhanced state with performance tracking
class OrchestrationState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    intermediate_steps: List[Any]
    intent: str
    confidence: float
    user_context: Dict[str, Any]
    conversation_history: List[Dict]
    performance_metrics: Dict[str, Any]
    agent_selection_reason: str

# Initialize components
intent_detector = IntentDetector()
context_manager = ContextManager()

def initialize_state() -> OrchestrationState:
    """Initialize state with performance tracking"""
    return {
        "messages": [], 
        "intermediate_steps": [], 
        "intent": "",
        "confidence": 0.0,
        "user_context": {},
        "conversation_history": [],
        "performance_metrics": {
            "start_time": datetime.now().isoformat(),
            "processing_steps": []
        },
        "agent_selection_reason": ""
    }

def intent_router(state: OrchestrationState) -> OrchestrationState:
    """
    Optimized intent router with advanced detection and context management
    """
    start_time = datetime.now()
    
    try:
        last_msg = state["messages"][-1].content
        
        # Advanced intent detection
        intent_result = intent_detector.detect_intent(last_msg)
        
        # Enhanced context management
        user_context = context_manager.update_context(state, last_msg, intent_result)
        
        # CRITICAL FIX: Update global memory with user input
        # This ensures conversation history accumulates properly
        global_memory.add_interaction(
            user_input=last_msg,
            agent_response="",  # Will be filled in dispatch
            agent_used=f"{intent_result['intent'].capitalize()}Agent"
        )
        
        # Update conversation history with enriched data
        conversation_history = state.get("conversation_history", [])
        conversation_entry = {
            "query": last_msg,
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "timestamp": user_context["timestamp"],
            "entities": intent_result.get("detected_entities", {}),
            "complexity": user_context.get("query_complexity", 0.0)
        }
        conversation_history.append(conversation_entry)
        
        # Performance tracking
        processing_time = (datetime.now() - start_time).total_seconds()
        performance_metrics = state.get("performance_metrics", {})
        performance_metrics["processing_steps"].append({
            "step": "intent_routing",
            "duration": processing_time,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Intent detected: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})")
        
        return {
            "messages": state["messages"],
            "intermediate_steps": [],
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "user_context": user_context,
            "conversation_history": conversation_history[-context_manager.max_history:],
            "performance_metrics": performance_metrics,
            "agent_selection_reason": f"Intent '{intent_result['intent']}' detected with {intent_result['confidence']:.1%} confidence"
        }
        
    except Exception as e:
        logger.error(f"Error in intent routing: {e}")
        return {
            **state,
            "intent": "chat",
            "confidence": 0.3,
            "agent_selection_reason": f"Fallback to chat due to routing error: {str(e)}"
        }

def smart_dispatch(state: OrchestrationState) -> OrchestrationState:
    """
    Intelligent dispatch with performance optimization and conversation context awareness
    """
    start_time = datetime.now()
    
    try:
        intent = state.get("intent", "chat")
        confidence = state.get("confidence", 0.5)
        user_context = state.get("user_context", {})
        
        # Enhanced agent selection with fallback logic
        agent_map = {
            "chat": shopping_assistant,
            "inventory": inventory_assistant,
            "recommend": recommend_assistant,
            "forecast": forecast_assistant,
            "logistics": logistics_assistant,
            "order": order_agent_graph
        }
        
        # CRITICAL FIX: Smart agent selection with order context awareness
        selected_agent = agent_map.get(intent, shopping_assistant)
        agent_name = intent.capitalize() + "Agent"
        
        # MEMORY FIX: Check if this is a memory-related query that should go to ChatAgent
        query = state.get("messages", [])[-1].content if state.get("messages") else ""
        memory_keywords = ["my name", "what is my", "who am i", "remember", "my email", "my preferences"]
        if any(keyword in query.lower() for keyword in memory_keywords):
            selected_agent = shopping_assistant
            agent_name = "ChatAgent (memory query)"
            confidence = max(confidence, 0.80)
            logger.info(f"Memory-related query detected - routing to ChatAgent")
        
        # Special handling for order-related queries
        elif user_context.get("is_order_request") or user_context.get("order_continuation"):
            selected_agent = order_agent_graph
            agent_name = "OrderAgent"
            confidence = max(confidence, 0.85)  # Boost confidence for order continuations
            logger.info(f"Order context detected - routing to OrderAgent")
        
        # Check for potential order continuation from conversation history
        elif user_context.get("potential_order_continuation"):
            recent_intents = user_context.get("previous_intents", [])
            if any(intent_entry.get("intent") == "order" for intent_entry in recent_intents[-2:]):
                # User was recently in order flow, this might be order details
                entities = user_context.get("detected_entities", {})
                if entities.get("product_codes") or entities.get("emails"):
                    selected_agent = order_agent_graph
                    agent_name = "OrderAgent (context-aware)"
                    confidence = 0.80
                    logger.info(f"Order continuation detected via context - routing to OrderAgent")
        
        # Low confidence fallback logic with conversation awareness
        elif confidence < 0.4:
            # Use conversation history to make better decision
            conversation_history = state.get("conversation_history", [])
            recent_intents = [h.get("intent", "chat") for h in conversation_history[-3:]]
            
            if recent_intents:
                # Use most common recent intent if confidence is low
                from collections import Counter
                common_intent = Counter(recent_intents).most_common(1)[0][0]
                if common_intent != "chat":
                    selected_agent = agent_map.get(common_intent, shopping_assistant)
                    agent_name = common_intent.capitalize() + "Agent (history-based)"
                    confidence = 0.60  # Moderate confidence for history-based selection
                    logger.info(f"Low confidence fallback: using {agent_name} based on conversation history")
        
        # Log agent selection with reasoning
        selection_reason = f"Intent: {intent}, Confidence: {confidence:.2f}"
        if user_context.get("is_order_request"):
            selection_reason += ", Order context detected"
        if user_context.get("order_continuation"):
            selection_reason += ", Order continuation"
        
        logger.info(f"Dispatching to {agent_name} ({selection_reason})")
        
        # DEBUG: Log the actual message being sent
        if state.get("messages"):
            actual_message = state["messages"][-1].content
            logger.info(f"DEBUG: Message being sent to {agent_name}: '{actual_message}'")
        
        # Prepare enhanced sub-state with full context
        sub_state = {
            "messages": state["messages"],
            "intermediate_steps": [],
            "intent": intent,
            "confidence": confidence,
            "user_context": user_context,
            "conversation_history": state.get("conversation_history", [])
        }
        
        # Invoke selected agent with enhanced error handling
        try:
            result = selected_agent.invoke(sub_state)
            
            # CRITICAL FIX: Update global memory with agent response
            if hasattr(result, "get") and result.get("messages"):
                agent_response = result["messages"][-1].content if result["messages"] else ""
                # Update the last interaction in global memory with agent response
                if global_memory.conversation_history:
                    global_memory.conversation_history[-1]["agent_response"] = agent_response
                    global_memory.conversation_history[-1]["agent_used"] = agent_name
            
            # Post-process result to maintain context
            if hasattr(result, "get") and result.get("messages"):
                # Agent completed successfully
                pass
            else:
                # Handle unexpected result format
                logger.warning(f"Unexpected result format from {agent_name}")
                result = {"messages": state["messages"]}
                
        except Exception as agent_error:
            logger.error(f"Agent {agent_name} failed: {agent_error}")
            
            # Intelligent fallback based on the original intent
            if intent == "order":
                # For order failures, provide helpful order-specific fallback
                fallback_message = (
                    "I'm having trouble processing your order right now. "
                    "Please provide your order details in this format: "
                    "Product SKU, quantity, email address"
                )
            else:
                # General fallback
                fallback_message = (
                    "I'm experiencing some technical difficulties. "
                    "Let me try to help you in a different way. Could you please rephrase your question?"
                )
            
            # Try chat agent as fallback
            try:
                fallback_state = {**sub_state, "messages": [HumanMessage(content=fallback_message)]}
                result = shopping_assistant.invoke(fallback_state)
                agent_name = "ChatAgent (error fallback)"
            except Exception as fallback_error:
                logger.error(f"Fallback agent also failed: {fallback_error}")
                result = {
                    "messages": [AIMessage(content=fallback_message)],
                    "intermediate_steps": []
                }
                agent_name = "Emergency fallback"
        
        # Performance tracking
        processing_time = (datetime.now() - start_time).total_seconds()
        performance_metrics = state.get("performance_metrics", {})
        if "processing_steps" not in performance_metrics:
            performance_metrics["processing_steps"] = []
            
        performance_metrics["processing_steps"].append({
            "step": f"agent_dispatch_{agent_name}",
            "duration": processing_time,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "intent": intent,
            "confidence": confidence
        })
        performance_metrics["total_duration"] = sum(
            step["duration"] for step in performance_metrics["processing_steps"]
        )
        
        return {
            "messages": result.get("messages", state["messages"]),
            "intermediate_steps": result.get("intermediate_steps", []),
            "intent": intent,
            "confidence": confidence,
            "user_context": user_context,
            "conversation_history": state["conversation_history"],
            "performance_metrics": performance_metrics,
            "agent_selection_reason": f"Processed by {agent_name} - {selection_reason}"
        }
        
    except Exception as e:
        logger.error(f"Critical error in dispatch: {e}")
        
        # Emergency fallback with better error context
        error_message = (
            "I apologize, but I'm experiencing some technical difficulties. "
            "Let me try to help you in a different way. Could you please rephrase your question?"
        )
        
        return {
            "messages": [AIMessage(content=error_message)],
            "intermediate_steps": [],
            "intent": "error",
            "confidence": 0.0,
            "user_context": state.get("user_context", {}),
            "conversation_history": state.get("conversation_history", []),
            "performance_metrics": state.get("performance_metrics", {}),
            "agent_selection_reason": f"Emergency fallback due to critical error: {str(e)}"
        }

# Build the optimized orchestration graph
builder = StateGraph(OrchestrationState)
builder.add_node("intent_router", intent_router)
builder.add_node("smart_dispatch", smart_dispatch)

builder.add_edge(START, "intent_router")
builder.add_edge("intent_router", "smart_dispatch")
builder.add_edge("smart_dispatch", END)

# Compile the optimized orchestrator
orchestrator = builder.compile()

# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor and log orchestrator performance"""
    
    def __init__(self):
        self.metrics = deque(maxlen=1000)  # Keep last 1000 requests
    
    def log_request(self, state: OrchestrationState):
        """Log request metrics"""
        metrics = state.get("performance_metrics", {})
        if metrics:
            self.metrics.append({
                "timestamp": datetime.now().isoformat(),
                "intent": state.get("intent", "unknown"),
                "confidence": state.get("confidence", 0.0),
                "total_duration": metrics.get("total_duration", 0.0),
                "steps": len(metrics.get("processing_steps", []))
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.metrics:
            return {"status": "No metrics available"}
        
        durations = [m["total_duration"] for m in self.metrics if "total_duration" in m]
        intents = [m["intent"] for m in self.metrics]
        
        from collections import Counter
        
        return {
            "total_requests": len(self.metrics),
            "avg_response_time": sum(durations) / len(durations) if durations else 0,
            "max_response_time": max(durations) if durations else 0,
            "intent_distribution": dict(Counter(intents)),
            "requests_last_hour": len([
                m for m in self.metrics 
                if datetime.now() - datetime.fromisoformat(m["timestamp"]) < timedelta(hours=1)
            ])
        }

# Global performance monitor
performance_monitor = PerformanceMonitor()

def monitored_invoke(state: OrchestrationState) -> OrchestrationState:
    """Wrapper to monitor orchestrator performance"""
    result = orchestrator.invoke(state)
    performance_monitor.log_request(result)
    return result

# Memory access functions for testing and debugging
def get_global_memory() -> ConversationMemory:
    """Get the global memory instance for testing/debugging"""
    return global_memory

def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics for monitoring"""
    return {
        "conversation_history_length": len(global_memory.conversation_history),
        "user_context_keys": list(global_memory.user_context.keys()),
        "session_start": global_memory.session_metadata.get("session_start"),
        "interaction_count": global_memory.session_metadata.get("interaction_count", 0)
    }

def reset_global_memory():
    """Reset global memory (for testing purposes)"""
    global global_memory
    global_memory = ConversationMemory()

# Export the monitored version
__all__ = ["orchestrator", "initialize_state", "performance_monitor", "monitored_invoke", 
           "get_global_memory", "get_memory_stats", "reset_global_memory", "context_manager"]