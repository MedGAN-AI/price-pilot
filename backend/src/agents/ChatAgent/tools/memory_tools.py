"""
ChatAgent Memory Management
Handles convers        # Remove memory artifacts that create loops
        memory_artifacts = [
            "No user context available yet.",
            "This is the start of our conversation.",
            "Name: ",
            "Email: ", 
            "Interested in: ",
            "User: ",
            "Assistant: ",
            "Successfully updated user context",
            "Successfully updated",
            "User context updated successfully",
            "Proceed with your response",
            "Invalid format",
            "Failed to update context"
        ]user context, and session state
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from langchain_core.tools import Tool

class ConversationMemory:
    """In-memory conversation storage for the current session"""
    
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.user_context: Dict[str, Any] = {}
        self.session_metadata: Dict[str, Any] = {
            "session_start": datetime.now(timezone.utc).isoformat(),
            "interaction_count": 0
        }
        self.context_update_tracker: set = set()  # Track recent context updates to prevent loops
        self.context_update_tracker: set = set()  # Track recent context updates
    
    def add_interaction(self, user_input: str, agent_response: str, agent_used: str = "ChatAgent"):
        """Add a new interaction to conversation history"""
        # Clean agent response - remove memory context pollution
        cleaned_response = self._clean_agent_response(agent_response)
        
        interaction = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_input": user_input,
            "agent_response": cleaned_response,
            "agent_used": agent_used,
            "interaction_id": self.session_metadata["interaction_count"]
        }
        
        self.conversation_history.append(interaction)
        self.session_metadata["interaction_count"] += 1
        
        # Extract and update user context ONLY from user input
        self._extract_user_context(user_input)
    
    def _clean_agent_response(self, response: str) -> str:
        """Clean agent response to prevent memory pollution"""
        if not response:
            return response
            
        cleaned = response
        
        # Remove memory artifacts that create loops
        memory_artifacts = [
            "No user context available yet.",
            "This is the start of our conversation.",
            "Name: ",
            "Email: ", 
            "Interested in: ",
            "User: ",
            "Assistant: ",
            "Successfully updated user context:",
            "Successfully updated",
            "Invalid format",
            "Failed to update context"
        ]
        
        for artifact in memory_artifacts:
            # Remove these phrases if they appear at the start
            while cleaned.strip().startswith(artifact):
                cleaned = cleaned[len(artifact):].strip()
            
            # Also remove if they appear standalone
            cleaned = cleaned.replace(artifact, "").strip()
        
        # Remove excessive whitespace and newlines
        cleaned = " ".join(cleaned.split())
        
        # If the cleaned response is too short or empty, return original
        return cleaned if len(cleaned) > 10 else response
    
    def _extract_user_context(self, user_input: str):
        """Extract user information from input"""
        text_lower = user_input.lower()
        
        # Extract email addresses
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, user_input)
        if emails:
            self.user_context["email"] = emails[0]
        
        # Extract names (simple heuristic)
        if "my name is" in text_lower:
            name_start = text_lower.find("my name is") + 10
            potential_name = user_input[name_start:name_start+50].strip().split()[0:2]
            if potential_name:
                self.user_context["name"] = " ".join(potential_name)
        
        # Extract names from order context
        if "for " in user_input and "@" in user_input:
            parts = user_input.split("for ")[1].split("@")[0].strip()
            if len(parts.split()) <= 3:  # Reasonable name length
                self.user_context["name"] = parts
        
        # Extract product preferences
        products_mentioned = []
        product_keywords = ["shoes", "hat", "shirt", "pants", "jacket", "dress", "skirt"]
        for keyword in product_keywords:
            if keyword in text_lower:
                products_mentioned.append(keyword)
        
        if products_mentioned:
            if "product_preferences" not in self.user_context:
                self.user_context["product_preferences"] = []
            self.user_context["product_preferences"].extend(products_mentioned)
            # Keep unique items
            self.user_context["product_preferences"] = list(set(self.user_context["product_preferences"]))
    
    def get_user_context_summary(self) -> str:
        """Get a summary of what we know about the user"""
        if not self.user_context:
            return "No user context available yet."
        
        summary_parts = []
        
        if "name" in self.user_context:
            summary_parts.append(f"Name: {self.user_context['name']}")
        
        if "email" in self.user_context:
            summary_parts.append(f"Email: {self.user_context['email']}")
        
        if "product_preferences" in self.user_context:
            prefs = ", ".join(self.user_context['product_preferences'])
            summary_parts.append(f"Interested in: {prefs}")
        
        return "; ".join(summary_parts) if summary_parts else "Basic context available."
    
    def get_conversation_context(self, last_n: int = 3) -> str:
        """Get recent conversation context"""
        if not self.conversation_history:
            return "This is the start of our conversation."
        
        recent_interactions = self.conversation_history[-last_n:]
        context_lines = []
        
        for interaction in recent_interactions:
            user_part = interaction["user_input"][:100] + "..." if len(interaction["user_input"]) > 100 else interaction["user_input"]
            context_lines.append(f"User: {user_part}")
            
            agent_part = interaction["agent_response"][:100] + "..." if len(interaction["agent_response"]) > 100 else interaction["agent_response"]
            context_lines.append(f"Assistant: {agent_part}")
        
        return "\n".join(context_lines)
    
    def remember_order_details(self, order_id: str, order_details: Dict[str, Any]):
        """Remember order details for future reference"""
        if "orders" not in self.user_context:
            self.user_context["orders"] = []
        
        order_record = {
            "order_id": order_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **order_details
        }
        
        self.user_context["orders"].append(order_record)

# Global memory instance for the session
conversation_memory = ConversationMemory()

def get_user_context_tool(query: str = "") -> str:
    """
    Get information about the user from conversation memory.
    Use this to remember user details like name, email, preferences, etc.
    """
    return conversation_memory.get_user_context_summary()

def get_conversation_context_tool(query: str = "") -> str:
    """
    Get recent conversation context to maintain continuity.
    Use this to reference previous interactions.
    """
    return conversation_memory.get_conversation_context()

def update_user_context_tool(context_update: str) -> str:
    """
    Update user context with new information.
    Format: 'key:value' or JSON string
    """
    # Check if this update was already done recently to prevent loops
    # Use content-based key to prevent the same update multiple times
    update_key = f"{context_update}"
    if update_key in conversation_memory.context_update_tracker:
        return "Context update already processed. Please use Final Answer to respond to the user."
    
    try:
        # Try to parse as JSON first
        try:
            update_data = json.loads(context_update)
            conversation_memory.user_context.update(update_data)
            conversation_memory.context_update_tracker.add(update_key)
            return "Context updated successfully. Use Final Answer to respond to the user - do not call any more tools."
        except json.JSONDecodeError:
            # Parse as key:value format
            if ":" in context_update:
                key, value = context_update.split(":", 1)
                conversation_memory.user_context[key.strip()] = value.strip()
                conversation_memory.context_update_tracker.add(update_key)
                return "Context updated successfully. Use Final Answer to respond to the user - do not call any more tools."
            else:
                return "Invalid format. Use 'key:value' or JSON format. Then use Final Answer to respond."
    except Exception as e:
        return f"Failed to update context: {e}. Use Final Answer to respond to the user."

# Create LangChain Tools
get_user_context_tool_lc = Tool(
    name="GetUserContext",
    func=get_user_context_tool,
    description="Get information about the user from conversation memory (name, email, preferences, etc.)"
)

get_conversation_context_tool_lc = Tool(
    name="GetConversationContext", 
    func=get_conversation_context_tool,
    description="Get recent conversation context to maintain continuity and reference previous interactions"
)

update_user_context_tool_lc = Tool(
    name="UpdateUserContext",
    func=update_user_context_tool,
    description="Update user context with new information. Format: 'key:value' or JSON string"
)

# Memory tools for ChatAgent
memory_tools = [
    get_user_context_tool_lc,
    get_conversation_context_tool_lc,
    update_user_context_tool_lc
]

# Function to save conversation interaction
def save_interaction(user_input: str, agent_response: str, agent_used: str = "ChatAgent"):
    """Save an interaction to conversation memory"""
    conversation_memory.add_interaction(user_input, agent_response, agent_used)
