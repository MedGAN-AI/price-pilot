import os
import sys
import re
import yaml
from typing import Any, Dict, TypedDict, Annotated, List
from datetime import datetime, timedelta, timezone
import json

from dotenv import load_dotenv
from supabase import create_client, Client

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Import logistics tools - Fixed import
from tools.logistics_tools import create_logistics_tools

# Display constants
SUCCESS = "✅"
ERROR = "❌"
ROBOT = "🤖"
TRUCK = "🚚"
PACKAGE = "📦"
SEARCH = "🔍"
CHART = "📊"
REFRESH = "🔄"
CLOCK = "⏰"
ANALYTICS = "📈"
CLIPBOARD = "📋"
DATABASE = "🗄️"

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Initialize Supabase client
print(f"{DATABASE} Connecting to Supabase...")
try:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print(f"{SUCCESS} Supabase connection successful")
except Exception as e:
    print(f"{ERROR} Supabase connection failed: {e}")
    raise

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
else:
    config = {"llm": {"provider": "google", "model": "gemini-1.5-flash", "temperature": 0.1}}

# LLM configuration
google_api_key = os.getenv("GOOGLE_API_KEY")
llm_model = config.get("llm", {}).get("model", "gemini-1.5-flash")

# Initialize Gemini
print(f"{ROBOT} Initializing Gemini...")
try:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    llm = ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=0.1,
        google_api_key=google_api_key,
        max_output_tokens=1024
    )
    print(f"{SUCCESS} Gemini connection successful")
except Exception as e:
    print(f"{ERROR} Gemini connection failed: {e}")
    raise

# Supabase logistics functions
def get_logistics_data(tracking_number: str = None) -> List[Dict]:
    """Get logistics data from Supabase."""
    try:
        if tracking_number:
            response = supabase.table('logistics').select('*').eq('tracking_number', tracking_number).execute()
        else:
            response = supabase.table('logistics').select('*').limit(10).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching logistics data: {e}")
        return []

def update_logistics_status(tracking_number: str, status: str, location: str = None) -> bool:
    """Update logistics status in Supabase."""
    try:
        update_data = {
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        if location:
            update_data['current_location'] = location
            
        response = supabase.table('logistics').update(update_data).eq('tracking_number', tracking_number).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error updating logistics status: {e}")
        return False

def create_logistics_entry(data: Dict) -> Dict:
    """Create new logistics entry in Supabase."""
    try:
        response = supabase.table('logistics').insert(data).execute()
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"Error creating logistics entry: {e}")
        return {}

# Enhanced logistics tools with Supabase
def create_enhanced_logistics_tools():
    """Create logistics tools with Supabase integration."""
    
    def track_shipment(tracking_number: str) -> str:
        """Track shipment using Supabase data."""
        data = get_logistics_data(tracking_number)
        if data:
            shipment = data[0]
            return json.dumps({
                "tracking_number": shipment.get('tracking_number'),
                "status": shipment.get('status'),
                "current_location": shipment.get('current_location'),
                "estimated_delivery": shipment.get('estimated_delivery'),
                "carrier": shipment.get('carrier')
            })
        return json.dumps({"error": "Shipment not found"})
    
    def schedule_pickup(origin: str, destination: str, carrier: str = "aramex") -> str:
        """Schedule pickup and create entry in Supabase."""
        tracking_number = f"PU{datetime.now().strftime('%Y%m%d%H%M%S')}"
        data = {
            'tracking_number': tracking_number,
            'origin': origin,
            'destination': destination,
            'carrier': carrier,
            'status': 'pickup_scheduled',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        result = create_logistics_entry(data)
        if result:
            return json.dumps({"success": True, "tracking_number": tracking_number, "status": "pickup_scheduled"})
        return json.dumps({"error": "Failed to schedule pickup"})
    
    def get_all_shipments() -> str:
        """Get all recent shipments."""
        data = get_logistics_data()
        return json.dumps(data)
    
    def update_shipment_status(tracking_number: str, status: str, location: str = None) -> str:
        """Update shipment status."""
        success = update_logistics_status(tracking_number, status, location)
        if success:
            return json.dumps({"success": True, "updated": True})
        return json.dumps({"error": "Failed to update status"})
    
    return [
        Tool(name="track_shipment", description="Track a shipment by tracking number", func=track_shipment),
        Tool(name="schedule_pickup", description="Schedule pickup from origin to destination", func=schedule_pickup),
        Tool(name="get_all_shipments", description="Get all recent shipments", func=get_all_shipments),
        Tool(name="update_shipment_status", description="Update shipment status and location", func=update_shipment_status)
    ]

tools = create_enhanced_logistics_tools()

# Agent capabilities
AGENT_CAPABILITIES = {
    "track": "Track shipments by tracking number",
    "schedule": "Schedule new pickups and deliveries", 
    "status": "Check and update shipment status",
    "list": "View all recent shipments",
    "help": "Show available commands and capabilities"
}

# Load custom prompt from file or use default
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "logistics_prompt.txt")
if os.path.exists(PROMPT_PATH):
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    print(f"{SUCCESS} Loaded custom prompt from logistics_prompt.txt")
else:
    # Default prompt if file doesn't exist
    SYSTEM_PROMPT = """You are LogisticsAgent, connected to a Supabase logistics database.

Available tools: {tools}

I can help you with:
1. Track shipments: "track ABC123"
2. Schedule pickups: "schedule pickup from Riyadh to Jeddah"
3. Update status: "update ABC123 status to delivered"
4. List shipments: "show all shipments"
5. Get help: "what can you do?"

Guidelines:
- Always use Supabase data for tracking and updates
- Provide clear, structured responses with emojis
- Ask for clarification when needed
- Format responses professionally

Current request: {input}
{agent_scratchpad}"""
    print(f"⚠️  Using default prompt. Create prompts/logistics_prompt.txt for custom prompt")

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, max_iterations=3
)

class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]

def assistant(state: AgentState) -> Dict[str, Any]:
    try:
        user_message = state["messages"][-1].content.lower()
        
        # Handle help requests
        if any(word in user_message for word in ['help', 'what can you do', 'capabilities', 'options']):
            help_response = f"""
{ROBOT} **LogisticsAgent Capabilities**

I'm connected to your Supabase logistics database and can help with:

{PACKAGE} **Tracking**: Track any shipment
• "track ABC123" - Get shipment details
• "where is my package ABC123"

{TRUCK} **Scheduling**: Create new shipments  
• "schedule pickup from Riyadh to Jeddah"
• "book delivery via Aramex"

{CHART} **Status Updates**: Modify shipment status
• "update ABC123 status to delivered" 
• "mark ABC123 as delayed"

{SEARCH} **Listing**: View all shipments
• "show all shipments"
• "list recent deliveries"

{CLIPBOARD} **Database**: Real-time Supabase integration
• All data synced with your logistics table
• Automatic tracking number generation

What would you like me to help you with?
            """
            return {"messages": [AIMessage(content=help_response.strip())]}
        
        # Handle specific logistics requests
        if any(word in user_message for word in ['track', 'schedule', 'update', 'list', 'show']):
            try:
                result = agent_executor.invoke({"input": user_message})
                content = result.get("output", "I couldn't process that request.")
                
                # Add context based on action
                if 'track' in user_message:
                    content = f"{SEARCH} **Tracking Result**\n\n{content}"
                elif 'schedule' in user_message:
                    content = f"{TRUCK} **Pickup Scheduled**\n\n{content}"
                elif 'update' in user_message:
                    content = f"{REFRESH} **Status Updated**\n\n{content}"
                elif any(word in user_message for word in ['list', 'show']):
                    content = f"{CHART} **Shipment List**\n\n{content}"
                    
                return {"messages": [AIMessage(content=content)]}
            except Exception as e:
                return {"messages": [AIMessage(content=f"{ERROR} Error processing request: {str(e)}")]}
        
        # Default response for unclear requests
        suggestion_response = f"""
{ROBOT} I'm not sure what you'd like me to do. Here are some options:

**Quick Actions:**
• "track [tracking_number]" - Track a shipment
• "schedule pickup from [origin] to [destination]" - Book pickup
• "show all shipments" - View recent shipments
• "help" - See all capabilities

**Examples:**
• "track ABC123XYZ"
• "schedule pickup from Riyadh to Jeddah via Aramex"
• "update ABC123 status to delivered"

What would you like me to help you with?
        """
        
        return {"messages": [AIMessage(content=suggestion_response.strip())]}
        
    except Exception as e:
        error_msg = f"{ERROR} Something went wrong: {str(e)}\n\nTry: 'help' to see what I can do."
        return {"messages": [AIMessage(content=error_msg)]}

# Build LangGraph
builder = StateGraph(AgentState)
builder.add_node("assistant", assistant)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)
logistics_assistant = builder.compile()

def chat_with_agent(message: str) -> str:
    """Simple chat interface."""
    state = {"messages": [HumanMessage(content=message)]}
    response = logistics_assistant.invoke(state)
    return response["messages"][-1].content

if __name__ == "__main__":
    print(f"\n{SUCCESS} LogisticsAgent with Supabase Integration Ready!")
    print(f"{DATABASE} Connected to: {SUPABASE_URL}")
    print(f"{ROBOT} Model: {llm_model}")
    
    # Interactive chat loop
    print(f"\n{TRUCK} Type 'help' to see what I can do, or 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"{SUCCESS} Goodbye!")
                break
            if user_input:
                response = chat_with_agent(user_input)
                print(f"\nAgent: {response}\n")
        except KeyboardInterrupt:
            print(f"\n{SUCCESS} Goodbye!")
            break
        except Exception as e:
            print(f"{ERROR} Error: {e}")