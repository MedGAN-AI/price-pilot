"""
Self-Updating Orchestrator
Automatically adapts to agent changes without manual configuration
Enhanced with semantic intent detection for better accuracy
"""
import sys
import os
import yaml
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Add the backend/src directory to the path  
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

try:
    from src.core.agent_registry import AgentRegistry, get_agent_registry
except ImportError:
    from .agent_registry import AgentRegistry, get_agent_registry

try:
    from src.core.gemini_intent_detector import GeminiIntentDetector
except ImportError:
    from .gemini_intent_detector import GeminiIntentDetector

try:
    from src.graphs.orchestrator import ContextManager
except ImportError:
    # Fallback if ContextManager is not available
    ContextManager = None

logger = logging.getLogger(__name__)

class FallbackIntentDetector:
    """
    Fallback intent detector using keyword patterns
    Used when semantic detection is unavailable
    """
    
    def __init__(self, agent_registry: AgentRegistry, config: Dict[str, Any]):
        self.agent_registry = agent_registry
        self.config = config
        
        # Basic keyword patterns for each intent
        self.intent_patterns = {
            "order": ["buy", "purchase", "order", "want", "need", "get", "checkout", "cart"],
            "inventory": ["stock", "available", "inventory", "how many", "in stock", "quantity"],
            "recommend": ["recommend", "suggest", "best", "show", "good", "help find", "what should"],
            "logistics": ["track", "shipment", "delivery", "where", "when", "arrive", "shipping"],
            "forecast": ["predict", "forecast", "analytics", "trends", "outlook", "projections"],
            "chat": ["hello", "hi", "thanks", "thank you", "name", "what can you", "help"]
        }
    
    def detect_intent(self, query: str) -> Dict[str, Any]:
        """Basic keyword-based intent detection"""
        lower_query = query.lower()
        
        # Score each intent based on keyword matches
        scores = {}
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in lower_query)
            if score > 0:
                scores[intent] = score / len(keywords)  # Normalize by keyword count
        
        if scores:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] * 2, 0.8)  # Scale confidence
            
            return {
                "intent": best_intent,
                "confidence": confidence,
                "method": "keyword_fallback",
                "reason": f"Keyword match with score {scores[best_intent]:.2f}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Default to chat
        return {
            "intent": "chat",
            "confidence": 0.5,
            "method": "keyword_fallback",
            "reason": "No keywords matched, defaulting to chat",
            "timestamp": datetime.now().isoformat()
        }


class SelfUpdatingOrchestrator:
    """
    Orchestrator that automatically adapts to agent changes
    Enhanced with semantic intent detection for superior accuracy
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "src/core/orchestrator_config.yaml"
        self.config = self._load_config()
          # Initialize components with semantic enhancement
        self.agent_registry = get_agent_registry()
        
        # Initialize intent detection (semantic first, fallback if unavailable)
        self.intent_detector = self._create_intent_detector()
        
        self.context_manager = ContextManager()
        
        # Track configuration changes
        self._last_config_check = datetime.now()
        
        logger.info("🚀 Self-Updating Orchestrator initialized with semantic detection")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with defaults"""
        default_config = {
            "intent_detection": {
                "confidence_threshold": 0.6,
                "fallback_agent": "ChatAgent",
                "cache_ttl_minutes": 5
            },
            "agent_routing": {
                "max_retries": 3,
                "timeout_seconds": 30,
                "circuit_breaker_enabled": True
            },            "custom_intent_patterns": {},
            "agent_preferences": {}
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f)                # Merge user config with defaults
                merged_config = {**default_config}
                if user_config:
                    merged_config.update(user_config)
                    
                return merged_config
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
                
        return default_config
    
    def _create_intent_detector(self):
        """Create the Gemini intent detector"""
        try:
            # Use Gemini detector
            gemini_detector = GeminiIntentDetector()
            logger.info("✅ Using Gemini intent detection")
            return gemini_detector
        except Exception as e:
            logger.error(f"Failed to initialize Gemini detector: {e}")
            logger.info("🔄 Falling back to keyword-based detection")
            return self._create_fallback_detector()
    
    def _create_fallback_detector(self) -> FallbackIntentDetector:
        """Create fallback intent detector for when semantic detection fails"""
        return FallbackIntentDetector(
            agent_registry=self.agent_registry,
            config=self.config["intent_detection"]
        )
    
    def process_query(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process query with automatic agent selection and routing
        """
        start_time = datetime.now()
        
        try:
            # Check for configuration updates
            self._check_for_updates()
            
            # Step 1: Detect intent
            intent_result = self.intent_detector.detect_intent(query)
            
            # Step 2: Select appropriate agent
            agent_info = self.agent_registry.get_agent_for_intent(intent_result["intent"])
            
            if not agent_info:
                logger.warning(f"No agent found for intent: {intent_result['intent']}")
                agent_info = self.agent_registry.get_agent_for_intent("chat")
            
            # Step 3: Route to agent
            agent_name = agent_info["name"]
            agent_instance = self.agent_registry.get_agent_instance(agent_name)
            
            if not agent_instance:
                raise Exception(f"Could not initialize {agent_name}")
            
            # Step 4: Process query
            response = self._process_with_agent(agent_instance, query, agent_name)
            
            # Step 5: Prepare result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                "response": response,
                "agent_used": agent_name,
                "intent": intent_result["intent"],
                "confidence": intent_result["confidence"],
                "processing_time": processing_time,
                "session_id": session_id or f"session_{hash(query)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Query processed by {agent_name} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            
            # Fallback response
            return {
                "response": self._generate_fallback_response(query, str(e)),
                "agent_used": "ErrorHandler",
                "intent": "error",
                "confidence": 0.0,
                "processing_time": (datetime.now() - start_time).total_seconds(),
                "session_id": session_id or f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _process_with_agent(self, agent_instance: Any, query: str, agent_name: str) -> str:
        """Process query with specific agent"""
        try:
            # Try standard process_query method first
            if hasattr(agent_instance, 'process_query'):
                return agent_instance.process_query(query)
            
            # Try invoke method for graph-based agents
            elif hasattr(agent_instance, 'invoke'):
                from src.core.base_agent import initialize_state
                from langchain_core.messages import HumanMessage
                
                state = initialize_state()
                state["messages"] = [HumanMessage(content=query)]
                
                result = agent_instance.invoke(state)
                
                if result and "messages" in result and result["messages"]:
                    return result["messages"][-1].content
                else:
                    return f"I processed your request but couldn't generate a response."
            
            else:
                return f"I'm having trouble processing your request with {agent_name}."
                
        except Exception as e:
            logger.error(f"Agent {agent_name} processing failed: {e}")
            return f"I encountered an issue while processing your request: {str(e)}"
    
    def _check_for_updates(self):
        """Check for configuration and agent updates"""
        # Check config file changes
        if os.path.exists(self.config_path):
            config_mtime = os.path.getmtime(self.config_path)
            if config_mtime > self._last_config_check.timestamp():
                logger.info("🔄 Configuration updated, reloading...")
                self.config = self._load_config()
                self.intent_detector = self._create_intent_detector()
                self._last_config_check = datetime.now()
        
        # Could add agent file monitoring here
    
    def _generate_fallback_response(self, query: str, error: str) -> str:
        """Generate helpful fallback response"""
        return f"""I apologize, but I'm experiencing some technical difficulties processing your request.

Here's how I can help you:
• **For orders**: Provide product SKU, your email, and quantity
• **For inventory**: Ask about specific products or show all available items
• **For recommendations**: Tell me what you're looking for
• **For general questions**: Ask me anything about our products or services

Please try rephrasing your request, and I'll do my best to assist you!"""
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        return {
            "orchestrator_status": "✅ Running",
            "configuration": {
                "config_loaded": os.path.exists(self.config_path),
                "last_update": self._last_config_check.isoformat(),
                "intent_threshold": self.config["intent_detection"]["confidence_threshold"]
            },
            "agent_registry": self.agent_registry.get_registry_info(),
            "agent_status": self.agent_registry.get_all_agents_status(),            "intent_detector": {
                "type": type(self.intent_detector).__name__,
                "status": "✅ Active",
                "info": self._get_detector_info()            }
        }
    
    def _get_detector_info(self):
        """Get information about the current intent detector"""
        try:
            if hasattr(self.intent_detector, 'intent_patterns'):
                # Fallback detector
                return {"patterns_loaded": len(self.intent_detector.intent_patterns)}
            else:
                # Gemini detector
                return {"model": "text-embedding-004", "embedding_based": True}
        except Exception:
            return {"status": "unknown"}
    
    def reload_system(self):
        """Reload entire system (for development)"""
        logger.info("🔄 Reloading entire orchestrator system...")
        
        # Reload agent registry
        from src.core.agent_registry import reload_all_agents
        reload_all_agents()
        
        # Reload config
        self.config = self._load_config()
        
        # Recreate components
        self.agent_registry = get_agent_registry()
        self.intent_detector = self._create_intent_detector()
        
        logger.info("✅ System reloaded successfully")


class DynamicIntentDetector:
    """Intent detector that adapts to available agents"""
    
    def __init__(self, agent_registry: AgentRegistry, config: Dict[str, Any], custom_patterns: Dict[str, Any]):
        self.agent_registry = agent_registry
        self.config = config
        self.custom_patterns = custom_patterns
        
        # Build intent patterns from available agents
        self.intent_patterns = self._build_dynamic_patterns()
        
        # Cache for performance
        self._cache = {}
        self._cache_expiry = {}
    
    def _build_dynamic_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build intent patterns from available agents"""
        patterns = {}
        
        # Get all registered agents
        for agent_name, agent_info in self.agent_registry.registered_agents.items():
            for intent in agent_info["intents"]:
                if intent not in patterns:
                    patterns[intent] = self._generate_pattern_for_intent(intent, agent_name)
        
        # Add custom patterns from config
        for intent, custom_pattern in self.custom_patterns.items():
            if intent in patterns:
                # Merge custom patterns with generated ones
                patterns[intent].update(custom_pattern)
            else:
                patterns[intent] = custom_pattern
        
        return patterns
    
    def _generate_pattern_for_intent(self, intent: str, agent_name: str) -> Dict[str, Any]:
        """Generate pattern for an intent based on agent name"""
        pattern_templates = {
            "order": {
                "primary": ["order", "buy", "purchase", "get", "want"],
                "secondary": ["checkout", "cart", "add", "need"],
                "context": ["product", "item", "quantity"],
                "weight": 1.2
            },
            "inventory": {
                "primary": ["stock", "inventory", "available", "in stock"],
                "secondary": ["how many", "quantity", "left", "remaining"],
                "context": ["check", "show", "tell me"],
                "weight": 1.0
            },
            "recommend": {
                "primary": ["recommend", "suggest", "find", "looking for"],
                "secondary": ["show me", "what", "best", "good", "similar"],
                "context": ["help", "need", "want"],
                "weight": 1.0
            },
            "chat": {
                "primary": ["hello", "hi", "hey", "what is", "who am"],
                "secondary": ["greet", "talk", "tell me", "remember"],
                "context": ["name", "help", "about"],
                "weight": 1.0
            }
        }
        
        # Return pattern for intent, or generate generic one
        if intent in pattern_templates:
            return pattern_templates[intent]
        else:
            return {
                "primary": [intent, intent.replace("_", " ")],
                "secondary": [agent_name.lower().replace("agent", "")],
                "context": ["help", "need", "want"],                "weight": 1.0
            }
    
    def detect_intent(self, text: str) -> Dict[str, Any]:
        """Detect intent using dynamic patterns"""
        lower_text = text.lower().strip()
        scores = {}
        
        # Special case: Explicit order patterns (SKU + Email + Quantity)
        import re
        sku_pattern = re.search(r'[A-Z]+-[A-Z]+-\d{3}', text)
        email_pattern = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z0-9-.]+', text)
        quantity_patterns = re.findall(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b', lower_text)
        
        if sku_pattern and email_pattern:
            return {
                "intent": "order",
                "confidence": 0.98,
                "all_scores": {"order": 15.0},
                "routing_reason": "Explicit order pattern detected (SKU + Email)"
            }
        
        # Score against all available patterns
        for intent, pattern in self.intent_patterns.items():
            score = 0.0
            
            # Primary keywords
            for keyword in pattern.get("primary", []):
                if keyword in lower_text:
                    score += 3.0
                    
            # Secondary keywords  
            for keyword in pattern.get("secondary", []):
                if keyword in lower_text:
                    score += 2.0
            
            # Context keywords
            for keyword in pattern.get("context", []):
                if keyword in lower_text:
                    score += 1.0
            
            # Apply weight
            score *= pattern.get("weight", 1.0)
            
            # Boost for intent-specific patterns
            if intent == "order" and any(word in lower_text for word in ["buy", "purchase", "order", "want", "need"]):
                score += 2.0
            elif intent == "inventory" and any(word in lower_text for word in ["stock", "available", "how many"]):
                score += 2.0
            elif intent == "recommend" and any(word in lower_text for word in ["recommend", "suggest", "best"]):
                score += 2.0
            
            if score > 0:
                scores[intent] = score
        
        # Determine best intent with improved logic
        if scores:
            best_intent = max(scores, key=scores.get)
            max_score = scores[best_intent]
            total_score = sum(scores.values())
            
            # Better confidence calculation
            if total_score > 0:
                confidence = min(max_score / total_score, 0.95)
                
                # Boost confidence if clearly dominant
                second_highest = sorted(scores.values())[-2] if len(scores) > 1 else 0
                if max_score > second_highest * 2:
                    confidence = min(confidence * 1.2, 0.95)
            else:
                confidence = 0.5
            
            # Apply confidence threshold - but be less aggressive about fallback
            if confidence < 0.4:  # Lowered from 0.6 to 0.4
                best_intent = "chat"
                confidence = 0.5
                
        else:
            best_intent = "chat"
            confidence = 0.5
        
        logger.info(f"🎯 Intent Detection: '{text[:50]}...' → {best_intent} (confidence: {confidence:.2f}, scores: {scores})")
        
        return {
            "intent": best_intent,
            "confidence": confidence,
            "all_scores": scores,
            "routing_reason": f"Dynamic detection - confidence: {confidence:.2f}"
        }


# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> SelfUpdatingOrchestrator:
    """Get the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SelfUpdatingOrchestrator()
    return _orchestrator

def reload_orchestrator():
    """Reload the orchestrator (for development)"""
    global _orchestrator
    _orchestrator = None
    _orchestrator = SelfUpdatingOrchestrator()
    logger.info("🔄 Orchestrator reloaded")


if __name__ == "__main__":
    # Test the orchestrator
    orchestrator = SelfUpdatingOrchestrator()
    
    test_queries = [
        "I want to order shoes",
        "How many products are in stock?", 
        "Recommend me something good",
        "Hello there!"
    ]
    
    for query in test_queries:
        result = orchestrator.process_query(query)
        print(f"Query: {query}")
        print(f"Agent: {result['agent_used']} (confidence: {result['confidence']:.2f})")
        print(f"Response: {result['response'][:100]}...")
        print("-" * 50)
