# Interactive Chat Interface with Session Memory for ChatAgent
# This file provides a command-line interface for context-aware conversations

import os
import sys
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Add the src directory to the path for proper imports
sys.path.append('src')

class SessionMemory:
    """
    Tracks conversation context and user state across multiple interactions.
    This makes the agent smart and context-aware.
    """
    
    def __init__(self):
        # Core session data
        self.user_email = None
        self.user_preferences = {}
        self.conversation_history = []
        
        # Shopping context
        self.products_viewed = []
        self.products_mentioned = []
        self.shopping_cart = []
        self.last_search_query = None
        
        # Conversation flow
        self.current_intent = None  # shopping, browsing, order_checking, etc.
        self.pending_actions = []   # Things user might want to do next
        
        print("💭 Session memory initialized - I'll remember our conversation!")
    
    def add_interaction(self, user_input: str, agent_response: str):
        """Track each interaction for context"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response
        }
        self.conversation_history.append(interaction)
        # Extract insights from the interaction
        self._extract_context(user_input, agent_response)
    
    def _extract_context(self, user_input: str, agent_response: str):
        """Extract useful context from the conversation"""
        user_lower = user_input.lower()
        response_lower = agent_response.lower()
        
        # Detect shopping intent
        if any(word in user_lower for word in ['buy', 'purchase', 'order', 'cart']):
            self.current_intent = 'shopping'
        elif any(word in user_lower for word in ['search', 'find', 'show', 'looking for']):
            self.current_intent = 'browsing'
        elif any(word in user_lower for word in ['order status', 'track', 'delivery']):
            self.current_intent = 'order_checking'
        
        # Extract email if mentioned
        if '@' in user_input and not self.user_email:
            words = user_input.split()
            for word in words:
                if '@' in word and '.' in word:
                    self.user_email = word.strip('.,!?')
                    print(f"📧 I'll remember your email: {self.user_email}")
                    break
        
        # Enhanced product tracking - Extract from both user input AND agent responses
        self._extract_products_from_text(user_input, "user input")
        self._extract_products_from_text(agent_response, "agent response")
    
    def _extract_products_from_text(self, text: str, source: str):
        """Extract product information from any text (user input or agent response)"""
        import re
        
        # Look for SKU patterns in format: SKU: PRODUCT-NAME-001 or (SKU: PRODUCT-NAME-001)
        sku_patterns = [
            r'SKU:\s*([A-Z0-9\-]+)',  # SKU: SHOES-RED-001
            r'\(SKU:\s*([A-Z0-9\-]+)\)',  # (SKU: SHOES-RED-001)
            r'sku\s*[:\-]\s*([A-Z0-9\-]+)',  # sku: SHOES-RED-001 or sku-SHOES-RED-001
        ]
        
        for pattern in sku_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for sku in matches:
                sku = sku.upper().strip()
                if sku not in self.products_mentioned:
                    self.products_mentioned.append(sku)
                    print(f"📝 Found product {sku} in {source}")
        
        # Look for product names with prices in multiple formats:
        # Format 1: **Product Name** (SKU: XXX) — $XX.XX
        # Format 2: Product Name (SKU: XXX) for $XX.XX
        # Format 3: Product Name (SKU: XXX) — $XX.XX
        product_patterns = [
            # Format: "Red Running Shoes (SKU: SHOES-RED-001) — $79.99"
            r'([A-Za-z\s]+?)\s*\(SKU:\s*([A-Z0-9\-]+)\)\s*[—\-]\s*\$([0-9.]+)',
            # Format: "**Red Running Shoes** (SKU: SHOES-RED-001) — $79.99"  
            r'\*\*([^*]+)\*\*\s*\(SKU:\s*([A-Z0-9\-]+)\)\s*[—\-]\s*\$([0-9.]+)',
            # Format: "Red Running Shoes (SKU: SHOES-RED-001) for $79.99"
            r'([A-Za-z\s]+?)\s*\(SKU:\s*([A-Z0-9\-]+)\)\s+for\s+\$([0-9.]+)',
            # More flexible pattern
            r'([A-Za-z\s\w]+?)\s*\(SKU:\s*([A-Z0-9\-]+)\)\s*.*?\$([0-9.]+)',
        ]
        
        # Debug: Show what we're trying to match
        print(f"🔍 DEBUG - Searching for products in {source}: '{text[:100]}...'")
        
        product_matches = []
        for i, pattern in enumerate(product_patterns):
            matches = re.findall(pattern, text, re.IGNORECASE)
            product_matches.extend(matches)
            print(f"🔍 DEBUG - Pattern {i+1} found {len(matches)} matches")
        
        print(f"🔍 DEBUG - Total {len(product_matches)} product matches found")
        
        for product_name, sku, price in product_matches:
            product_info = {
                'name': product_name.strip(),
                'sku': sku.upper().strip(),
                'price': price.strip()
            }
            
            # Store detailed product info
            if sku.upper() not in self.products_mentioned:
                self.products_mentioned.append(sku.upper())
                self.products_viewed.append(product_info)
                print(f"💎 Remembered product: {product_name} ({sku.upper()}) - ${price}")
        
        # Track simple product mentions (like "red shoes", "running shoes") 
        # Only detect as separate words to avoid false positives like "address" → "red dress"
        product_keywords = ['shoes', 'shirt', 'jacket', 'pants', 'dress', 'watch', 'bag']
        colors = ['red', 'blue', 'green', 'black', 'white', 'yellow', 'pink', 'purple']

        text_lower = text.lower()
        words = text_lower.split()
        for keyword in product_keywords:
            if keyword in words:  # Changed from 'in text_lower' to 'in words'
                for color in colors:
                    if color in words and f"{color} {keyword}" not in [p.get('search_term', '') for p in self.products_viewed]:
                        # Store this as a search preference
                        if not hasattr(self, 'search_preferences'):
                            self.search_preferences = []
                        
                        search_term = f"{color} {keyword}"
                        if search_term not in self.search_preferences:
                            self.search_preferences.append(search_term)
                            print(f"🔍 Noted interest in: {search_term}")

    def get_context_summary(self) -> str:
        """Generate a summary of current session context"""
        summary_parts = []
        
        if self.user_email:
            summary_parts.append(f"User email: {self.user_email}")
        
        if self.current_intent:
            summary_parts.append(f"Current intent: {self.current_intent}")
        
        if self.products_viewed:
            product_names = [p['name'] for p in self.products_viewed]
            summary_parts.append(f"Products viewed: {', '.join(product_names)}")
        elif self.products_mentioned:
            summary_parts.append(f"Products discussed: {', '.join(self.products_mentioned)}")
        
        if hasattr(self, 'search_preferences') and self.search_preferences:
            summary_parts.append(f"Interests: {', '.join(self.search_preferences)}")
        
        if self.shopping_cart:
            summary_parts.append(f"Items in consideration: {len(self.shopping_cart)} items")
        
        if summary_parts:
            return "Session Context: " + " | ".join(summary_parts)
        
        return "New conversation - no context yet"

    def enhance_user_input(self, user_input: str) -> str:
        """Add context to user input to help the agent understand better"""
        context_parts = []
        
        # Add conversation context if relevant
        if len(self.conversation_history) > 0:
            context_parts.append("Previous conversation context:")
            
            if self.products_mentioned:
                context_parts.append(f"Products we've discussed: {', '.join(self.products_mentioned)}")
            
            # Add detailed product information if available
            if self.products_viewed:
                context_parts.append("Products the user has seen:")
                for product in self.products_viewed[-3:]:  # Last 3 products
                    context_parts.append(f"  • {product['name']} (SKU: {product['sku']}) - ${product['price']}")
            
            # Debug: Show what products are stored
            print(f"🔍 DEBUG - Products in memory: {len(self.products_viewed)} items")
            for i, product in enumerate(self.products_viewed):
                print(f"  Product {i}: {product}")
            
            # Add search preferences
            if hasattr(self, 'search_preferences') and self.search_preferences:
                context_parts.append(f"User has shown interest in: {', '.join(self.search_preferences)}")
            
            if self.current_intent:
                context_parts.append(f"Current user intent: {self.current_intent}")
            
            # Smart cross-referencing: If user mentions a product type we've seen before
            user_lower = user_input.lower()
            matched_products = []
            
            for product in self.products_viewed:
                product_name_lower = product['name'].lower()
                product_words = set(product_name_lower.split())
                
                # Count matching words between user input and product name
                user_words = set(user_lower.split())
                matching_words = product_words.intersection(user_words)
                # If user mentions multiple key words from a product name, it's likely a match
                if len(matching_words) >= 2:  # Need at least 2 matching words
                    matched_products.append((product, len(matching_words)))
                elif len(matching_words) == 1:
                    # For single word matches, be more careful
                    matching_word = list(matching_words)[0]
                    # Only exclude very common/meaningless words
                    if matching_word not in ['the', 'and', 'or', 'a', 'an', 'with', 'for', 'in', 'on', 'at']:
                        # Check if user is asking about buying/ordering
                        if any(action in user_lower for action in ['buy', 'purchase', 'order', 'get', 'want']):
                            matched_products.append((product, 1))
            
            # Sort by number of matching words and add context for best matches
            if matched_products:
                matched_products.sort(key=lambda x: x[1], reverse=True)
                best_match = matched_products[0][0]
                context_parts.append(f"IMPORTANT: User is likely referring to '{best_match['name']}' (SKU: {best_match['sku']}) - Price: ${best_match['price']} that we discussed earlier. Use this specific product information.")
                
                # If multiple products match, mention them too
                if len(matched_products) > 1:
                    other_matches = [p[0] for p in matched_products[1:3]]  # Show up to 2 more
                    other_names = [f"{p['name']} (SKU: {p['sku']})" for p in other_matches]
                    context_parts.append(f"Other possible matches: {', '.join(other_names)}")
        
        if context_parts:
            enhanced_input = "\n".join(context_parts) + "\n\nCurrent user message: " + user_input
            return enhanced_input
        
        return user_input

def start_interactive_chat():
    """
    Start an interactive chat session with session memory.
    The agent will remember everything about your conversation!
    """
    
    # Load environment variables
    load_dotenv()
    
    # Check if Google API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ ERROR: GOOGLE_API_KEY not found in environment variables")
        print("Please set it in your .env file")
        return False
    
    print("🛍️ Welcome to your Smart Shopping Assistant!")
    print("I'll remember our conversation and provide personalized help.")
    print("Type 'quit', 'exit', or 'bye' to end the conversation.")
    print("Type 'memory' to see what I remember about our session.")
    print("=" * 60)
    
    # Initialize session memory
    session = SessionMemory()
    
    try:
        # Import the agent
        from agents.ChatAgent.llm_agent import agent_executor
        print("✅ Shopping assistant loaded successfully!")
        print()
        
        # Start the conversation loop
        while True:
            # Show context summary if we have some history
            if len(session.conversation_history) > 0:
                print(f"💭 {session.get_context_summary()}")
            
            # Get user input
            user_input = input("\nYou: ").strip()
            
            # Check for special commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                print("🛍️ Thank you for shopping with us! I'll remember our conversation for next time.")
                break
            
            if user_input.lower() == 'memory':
                print("\n🧠 Here's what I remember about our session:")
                print(session.get_context_summary())
                if session.conversation_history:
                    print(f"💬 We've had {len(session.conversation_history)} interactions")
                    print("Recent topics:", [h['user_input'][:30] + "..." for h in session.conversation_history[-3:]])
                continue
            
            # Skip empty inputs
            if not user_input:
                print("Please type something, 'memory' to see session info, or 'quit' to exit.")
                continue
            
            # Process the user's message with context
            try:
                print("🤖 Assistant: ", end="", flush=True)
                
                # Enhance the input with session context
                enhanced_input = session.enhance_user_input(user_input)
                
                # Debug: Show what context is being sent to the agent
                if enhanced_input != user_input:
                    print(f"\n🔍 DEBUG - Enhanced context being sent to agent:")
                    print("=" * 50)
                    print(enhanced_input)
                    print("=" * 50)
                
                # Get agent response
                result = agent_executor.invoke({"input": enhanced_input})
                response = result["output"]
                
                print(response)
                
                # Store this interaction in memory
                session.add_interaction(user_input, response)
                
                print()  # Add spacing for readability
                
            except Exception as e:
                print(f"❌ Sorry, I encountered an error: {str(e)}")
                print("Please try again or type 'quit' to exit.")
                print()
                
    except ImportError as e:
        print(f"❌ Failed to load the shopping assistant: {e}")
        print("Please check your agent configuration.")
        return False
    except KeyboardInterrupt:
        print("\n🛍️ Chat interrupted. Thank you for shopping with us!")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_interactive_chat()
