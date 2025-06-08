import os
import re
import yaml
from typing import Any, Dict, TypedDict, Annotated, List
from datetime import datetime, timedelta, timezone
import json

from dotenv import load_dotenv

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_community.llms import Ollama

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import logistics tools - Fixed import
from tools.logistics_tools import create_logistics_tools

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# LLM configuration - Updated for Ollama
llm_provider = config.get("llm", {}).get("provider", "ollama")
llm_model = config.get("llm", {}).get("model", "llama3.2:1b")
llm_temperature = config.get("llm", {}).get("temperature", 0.1)
ollama_base_url = config.get("llm", {}).get("base_url", "http://localhost:11434")

# Logistics configuration
delay_threshold_hours = config.get("logistics", {}).get("delay_threshold_hours", 4)
preferred_carriers = config.get("logistics", {}).get("preferred_carriers", ["aramex", "naqel"])

# Tracking number regex (compile for reuse)
tracking_pattern_str = config.get("tracking_pattern", "^[A-Z0-9]{8,20}$")
TRACKING_PATTERN = re.compile(tracking_pattern_str)

# Initialize Ollama LLM - FIXED: Removed duplicate stop tokens
print(f"🦙 Initializing Llama 3.2:1b via Ollama...")
try:
    llm = Ollama(
        model=llm_model,
        temperature=llm_temperature,
        base_url=ollama_base_url,
        num_predict=512,  # Limit response length for better performance
        num_ctx=4096,  # Context window
        repeat_penalty=1.1,
        top_k=40,
        top_p=0.9
        # REMOVED: stop parameter from here to avoid conflict
    )
    
    # Test connection
    test_response = llm.invoke("Hello")
    print(f"✅ Ollama connection successful: {test_response[:50]}...")
    
except Exception as e:
    print(f"❌ Ollama connection failed: {e}")
    print("Make sure Ollama is running: ollama serve")
    print("And model is pulled: ollama pull llama3.2:1b")
    raise

# Create tools using the factory function
tools = create_logistics_tools()

# Llama 3.2 optimized system prompt - FIXED: Cleaner format
SYSTEM_PROMPT = """You are LogisticsAgent, a specialized assistant for Aramex and Naqel logistics operations.

Available tools:
{tools}

You help with:
- Tracking shipments and packages
- Scheduling pickups and deliveries  
- Checking carrier status and performance
- Rerouting delayed shipments
- Providing shipping analytics

Guidelines:
1. Always validate tracking numbers and addresses
2. Provide specific details and clear status updates
3. Escalate delays over {delay_threshold_hours} hours
4. Suggest alternatives when needed
5. Use JSON format for tool inputs

Current context: {shipment_context}

IMPORTANT: When using tools, follow this exact format:
Action: tool_name
Action Input: {{"parameter": "value"}}

User request: {input}
{agent_scratchpad}"""

# Load custom prompt if available
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "logistics_prompt.txt")
if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read()
else:
    system_prompt = SYSTEM_PROMPT

prompt = PromptTemplate.from_template(system_prompt)

# Create agent with Llama 3.2
agent = create_react_agent(llm, tools, prompt)

# FIXED: Updated AgentExecutor configuration
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
    return_intermediate_steps=True,
    early_stopping_method="generate",
    # ADDED: Configure stop sequences here instead of in LLM
    stop_sequence=["Human:", "Assistant:", "User:", "Observation:"]
)

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List
    shipment_context: Dict
    user_preferences: Dict
    active_operations: List

def initialize_state() -> AgentState:
    return {
        "messages": [],
        "intermediate_steps": [],
        "shipment_context": {},
        "user_preferences": {},
        "active_operations": []
    }

def is_logistics_related(message: str) -> bool:
    """Enhanced logistics query detection."""
    logistics_keywords = [
        'ship', 'shipping', 'delivery', 'pickup', 'track', 'tracking',
        'carrier', 'aramex', 'naqel', 'route', 'reroute', 'dispatch',
        'logistics', 'transport', 'freight', 'schedule', 'status',
        'delay', 'estimate', 'eta', 'delivery time', 'when will',
        'where is', 'shipment', 'package', 'order', 'location',
        'warehouse', 'distribution', 'fulfillment', 'courier',
        'express', 'standard', 'economy', 'overnight', 'same day'
    ]
    
    lower_msg = message.lower()

    # Check for logistics keywords
    for kw in logistics_keywords:
        if kw in lower_msg:
            return True

    # Check for tracking number patterns
    if TRACKING_PATTERN.search(message.upper()):
        return True
    
    # Check for common logistics phrases
    logistics_phrases = [
        'when will it arrive', 'where is my package', 'delivery status',
        'shipping cost', 'pickup time', 'delivery address'
    ]
    
    for phrase in logistics_phrases:
        if phrase in lower_msg:
            return True

    return False

def extract_tracking_numbers(message: str) -> List[str]:
    """Extract tracking numbers from message text."""
    return TRACKING_PATTERN.findall(message.upper())

def check_for_delays(shipment_info: Dict) -> Dict[str, Any]:
    """Enhanced delay detection with proper timezone handling."""
    if not shipment_info:
        return {"has_delay": False}
    
    estimated_time = shipment_info.get('estimated_delivery')
    if not estimated_time:
        return {"has_delay": False}
    
    try:
        # Parse delivery time with proper timezone handling
        if isinstance(estimated_time, str):
            if estimated_time.endswith('Z'):
                est_dt = datetime.fromisoformat(estimated_time.replace('Z', '+00:00'))
            elif '+' in estimated_time or estimated_time.endswith('UTC'):
                est_dt = datetime.fromisoformat(estimated_time.replace('UTC', '+00:00'))
            else:
                # Assume UTC for naive datetime
                naive_dt = datetime.fromisoformat(estimated_time)
                est_dt = naive_dt.replace(tzinfo=timezone.utc)
        else:
            est_dt = estimated_time
        
        # Current time in UTC
        current_time = datetime.now(timezone.utc)
        
        # Ensure both datetimes are timezone-aware
        if est_dt.tzinfo is None:
            est_dt = est_dt.replace(tzinfo=timezone.utc)
        
        delay_hours = (current_time - est_dt).total_seconds() / 3600
        
        if delay_hours > delay_threshold_hours:
            return {
                "has_delay": True,
                "delay_hours": delay_hours,
                "severity": "high" if delay_hours > 24 else "medium",
                "recommended_action": "reroute" if delay_hours > 12 else "monitor"
            }
    except Exception as e:
        print(f"Error parsing delivery time: {e}")
        return {"has_delay": False}
    
    return {"has_delay": False}

def format_response(content: str, context: Dict = None) -> str:
    """Format response with context."""
    if context and context.get("tracking_number"):
        tracking_info = f"📦 Tracking: {context['tracking_number']}\n"
        content = tracking_info + content
    
    return content

def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        user_message = state["messages"][-1].content
        current_context = state.get("shipment_context", {})

        # Check if logistics related
        if not is_logistics_related(user_message):
            response = (
                "Hello! I'm your LogisticsAgent 🚚\n\n"
                "I can help you with:\n"
                "• 📦 Schedule pickups (Aramex & Naqel)\n"
                "• 🔍 Track shipments\n"
                "• 📊 Check carrier status\n"
                "• 🔄 Reroute packages\n"
                "• ⏰ Update delivery estimates\n"
                "• 📈 Get shipping analytics\n\n"
                "Try: 'Track ABC123XYZ' or 'Schedule pickup from Riyadh'"
            )
            return {
                "messages": [AIMessage(content=response)],
                "intermediate_steps": [],
                "shipment_context": current_context,
                "user_preferences": state.get("user_preferences", {}),
                "active_operations": state.get("active_operations", [])
            }

        # Extract tracking numbers
        tracking_numbers = extract_tracking_numbers(user_message)
        if tracking_numbers:
            current_context["extracted_tracking"] = tracking_numbers

        # Prepare agent input - FIXED: Cleaner input format
        agent_input = {
            "input": user_message,
            "shipment_context": json.dumps(current_context),
            "delay_threshold_hours": delay_threshold_hours,
            "preferred_carriers": preferred_carriers
        }

        # Execute agent with error handling
        try:
            result = agent_executor.invoke(agent_input)
        except Exception as agent_error:
            # Fallback response if agent fails
            print(f"Agent execution error: {agent_error}")
            return {
                "messages": [AIMessage(content=f"I encountered an issue processing your request. Please try rephrasing your query.")],
                "intermediate_steps": [],
                "shipment_context": current_context,
                "user_preferences": state.get("user_preferences", {}),
                "active_operations": state.get("active_operations", [])
            }

        # Process results
        content = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        
        updated_context = current_context.copy()
        active_ops = state.get("active_operations", [])
        
        # Process tool results
        for step in intermediate_steps:
            if hasattr(step, 'observation') and step.observation:
                try:
                    if isinstance(step.observation, str):
                        obs_data = json.loads(step.observation)
                    else:
                        obs_data = step.observation
                    
                    if isinstance(obs_data, dict):
                        # Update context
                        if obs_data.get("tracking_number"):
                            updated_context["tracking_number"] = obs_data["tracking_number"]
                        if obs_data.get("status"):
                            updated_context["current_status"] = obs_data["status"]
                        if obs_data.get("estimated_delivery"):
                            updated_context["estimated_delivery"] = obs_data["estimated_delivery"]
                        
                        # Check for delays
                        delay_info = check_for_delays(obs_data)
                        if delay_info.get("has_delay"):
                            delay_msg = (
                                f"\n\n⚠️ DELAY ALERT: {delay_info['delay_hours']:.1f}h delay\n"
                                f"Severity: {delay_info['severity'].upper()}\n"
                                f"Action: {delay_info['recommended_action'].upper()}"
                            )
                            content += delay_msg
                            
                            active_ops.append({
                                "type": "delay_monitoring",
                                "tracking_number": obs_data.get("tracking_number"),
                                "delay_hours": delay_info["delay_hours"],
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                            
                            if delay_info["recommended_action"] == "reroute":
                                content += "\n📋 Escalating to optimization..."
                
                except (json.JSONDecodeError, TypeError):
                    continue

        formatted_content = format_response(content, updated_context)

        return {
            "messages": [AIMessage(content=formatted_content)],
            "intermediate_steps": [],
            "shipment_context": updated_context,
            "user_preferences": state.get("user_preferences", {}),
            "active_operations": active_ops
        }

    except Exception as e:
        error_msg = (
            f"❌ Error: {str(e)}\n\n"
            "Please try again or ask about:\n"
            "• Scheduling pickups\n"
            "• Tracking shipments\n"
            "• Checking carrier status\n"
            "• Rerouting packages"
        )
        return {
            "messages": [AIMessage(content=error_msg)],
            "intermediate_steps": [],
            "shipment_context": state.get("shipment_context", {}),
            "user_preferences": state.get("user_preferences", {}),
            "active_operations": state.get("active_operations", [])
        }

# Build LangGraph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
logistics_assistant = builder.compile()

def handle_carrier_webhook(webhook_data: Dict) -> Dict[str, Any]:
    """Enhanced webhook handler."""
    try:
        tracking_number = webhook_data.get('tracking_number')
        status = webhook_data.get('status')
        location = webhook_data.get('current_location')
        estimated_delivery = webhook_data.get('estimated_delivery')
        carrier = webhook_data.get('carrier', 'unknown')
        
        if not tracking_number or not status:
            return {
                'processed': False,
                'error': 'Missing required fields'
            }
        
        state = initialize_state()
        state["messages"] = [
            HumanMessage(content=f"Status update for {tracking_number}: {status}")
        ]
        state["shipment_context"] = {
            'tracking_number': tracking_number,
            'status': status,
            'current_location': location,
            'estimated_delivery': estimated_delivery,
            'carrier': carrier,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'webhook_source': True
        }
        
        response_state = logistics_assistant.invoke(state)
        
        delay_info = check_for_delays(state["shipment_context"])
        needs_escalation = delay_info.get("has_delay") and delay_info.get("severity") == "high"
        
        return {
            'processed': True,
            'response': response_state["messages"][-1].content,
            'context': response_state["shipment_context"],
            'needs_escalation': needs_escalation,
            'active_operations': response_state.get("active_operations", [])
        }
        
    except Exception as e:
        return {
            'processed': False,
            'error': str(e)
        }

def get_agent_status() -> Dict[str, Any]:
    """Get agent status."""
    return {
        "status": "active",
        "model": llm_model,
        "provider": "ollama",
        "supported_carriers": preferred_carriers,
        "delay_threshold_hours": delay_threshold_hours,
        "available_tools": [tool.name for tool in tools],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def process_batch_requests(requests: List[Dict]) -> List[Dict]:
    """Process batch requests."""
    results = []
    
    for request in requests:
        try:
            state = initialize_state()
            state["messages"] = [HumanMessage(content=request.get("query", ""))]
            
            response_state = logistics_assistant.invoke(state)
            results.append({
                "request_id": request.get("id", "unknown"),
                "status": "success",
                "response": response_state["messages"][-1].content,
                "context": response_state.get("shipment_context", {})
            })
        except Exception as e:
            results.append({
                "request_id": request.get("id", "unknown"),
                "status": "error",
                "error": str(e)
            })
    
    return results

if __name__ == "__main__":
    print("=== LogisticsAgent with Llama 3.2:1b Test Suite ===")
    
    # Test 1: Agent Executor
    print("\n1. Testing AgentExecutor...")
    try:
        test_result = agent_executor.invoke({
            "input": "Schedule pickup from Riyadh to Jeddah via Aramex",
            "shipment_context": "{}",
            "delay_threshold_hours": delay_threshold_hours
        })
        print("✅ AgentExecutor test passed")
        print("Output:", test_result["output"][:200] + "...")
    except Exception as e:
        print(f"❌ AgentExecutor test failed: {e}")

    # Test 2: LangGraph
    print("\n2. Testing LangGraph...")
    try:
        state = initialize_state()
        state["messages"] = [HumanMessage(content="Track shipment ABC123XYZ")]
        
        response_state = logistics_assistant.invoke(state)
        print("✅ LangGraph test passed")
        print("Response:", response_state["messages"][-1].content[:200] + "...")
    except Exception as e:
        print(f"❌ LangGraph test failed: {e}")

    # Test 3: Webhook Handler
    print("\n3. Testing Webhook Handler...")
    try:
        webhook_data = {
            'tracking_number': 'ABC123XYZ',
            'status': 'delayed',
            'current_location': 'Riyadh Distribution Center',
            'estimated_delivery': '2025-06-06T14:00:00Z',
            'carrier': 'aramex'
        }
        result = handle_carrier_webhook(webhook_data)
        print("✅ Webhook test passed")
        print("Processed:", result.get('processed'))
        print("Needs escalation:", result.get('needs_escalation'))
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")

    # Test 4: Batch Processing
    print("\n4. Testing Batch Processing...")
    try:
        batch_requests = [
            {"id": "req1", "query": "Track ABC123"},
            {"id": "req2", "query": "Aramex status Riyadh to Jeddah"}
        ]
        batch_results = process_batch_requests(batch_requests)
        print("✅ Batch processing test passed")
        print(f"Processed {len(batch_results)} requests")
    except Exception as e:
        print(f"❌ Batch processing test failed: {e}")

    # Test 5: Agent Status
    print("\n5. Testing Agent Status...")
    try:
        status = get_agent_status()
        print("✅ Agent status test passed")
        print("Status:", status["status"])
        print("Model:", status["model"])
        print("Tools:", len(status["available_tools"]))
    except Exception as e:
        print(f"❌ Agent status test failed: {e}")

    print("\n=== Test Suite Complete ===")