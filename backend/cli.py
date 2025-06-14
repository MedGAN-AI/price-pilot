"""
Optimized Price Pilot Production CLI Interface
Enhanced with performance monitoring, better UX, and smart features
"""

import sys
import os
import asyncio
import signal
from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import time

sys.path.append('.')

def print_header(title: str, color: str = "🚀"):
    """Print a colorful formatted header"""
    print("\n" + "=" * 70)
    print(f"{color} {title}")
    print("=" * 70)

def print_subheader(title: str, color: str = "🔧"):
    """Print a formatted subheader"""
    print(f"\n{color} {title}")
    print("-" * 50)

def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"⚠️  {message}")

class PricePilotCLI:
    """Enhanced Production CLI for Price Pilot multi-agent system"""
    
    def __init__(self):
        self.orchestrator = None
        self.performance_monitor = None
        self.conversation_history = []
        self.user_preferences = {
            "show_performance": False,
            "show_intent_detection": True,
            "auto_save_history": True,
            "theme": "default"
        }
        self.session_stats = {
            "start_time": datetime.now(),
            "queries_processed": 0,
            "average_response_time": 0.0,
            "intents_detected": defaultdict(int)
        }
        self.running = True
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        def signal_handler(signum, frame):
            print("\n\n👋 Gracefully shutting down Price Pilot...")
            self.running = False
            self.save_session_data()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def load_orchestrator(self):
        """Load the optimized orchestrator with error handling"""
        try:
            from src.graphs.orchestrator import (
                orchestrator, 
                initialize_state, 
                performance_monitor,
                monitored_invoke
            )
            
            self.orchestrator = monitored_invoke
            self.initialize_state = initialize_state
            self.performance_monitor = performance_monitor
            
            print_success("Optimized orchestrator loaded successfully")
            print_info("Enhanced features: Smart intent detection, context management, performance monitoring")
            return True
            
        except ImportError as e:
            print_error(f"Failed to load optimized orchestrator: {e}")
            print_info("Falling back to basic orchestrator...")
            
            try:
                from src.graphs.orchestrator import orchestrator, initialize_state
                self.orchestrator = orchestrator.invoke
                self.initialize_state = initialize_state
                print_warning("Basic orchestrator loaded (some features unavailable)")
                return True
            except Exception as e2:
                print_error(f"Failed to load any orchestrator: {e2}")
                return False
            
        except Exception as e:
            print_error(f"Unexpected error loading orchestrator: {e}")
            return False
    
    def interactive_chat(self):
        """Enhanced interactive chat mode with smart features"""
        self.show_welcome_screen()
        
        if not self.orchestrator:
            print_error("Orchestrator not loaded. Exiting.")
            return
        
        # Start background performance monitoring
        if self.performance_monitor:
            self.start_performance_monitoring()
        
        while self.running:
            try:
                user_input = self.get_user_input()
                
                if user_input is None:  # EOF or special case
                    continue
                    
                if self.handle_commands(user_input):
                    continue
                
                if not user_input.strip():
                    continue
                
                # Process query with timing
                start_time = time.time()
                response_data = self.process_query(user_input)
                processing_time = time.time() - start_time
                
                # Display response
                self.display_response(response_data, processing_time)
                
                # Update statistics
                self.update_session_stats(response_data, processing_time)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Session ended!")
                break
            except Exception as e:
                print_error(f"Unexpected error: {e}")
                if self.user_preferences.get("debug_mode", False):
                    import traceback
                    traceback.print_exc()
    
    def show_welcome_screen(self):
        """Display enhanced welcome screen"""
        print_header("Price Pilot Production System", "🎯")
        print("🤖 Multi-Agent Retail Intelligence Platform")
        print("\n🚀 6 Specialized Agents Ready:")
        
        agents = [
            ("ChatAgent", "Conversation Intelligence & General Support"),
            ("InventoryAgent", "Stock Management & Availability"),
            ("RecommendAgent", "Product Discovery & Suggestions"),
            ("OrderAgent", "Order Processing & Management"),
            ("LogisticsAgent", "Shipping & Tracking"),
            ("ForecastAgent", "Demand Prediction & Analytics")
        ]
        
        for agent, description in agents:
            print(f"   • {agent:<15} - {description}")
        
        print("\n💡 Example Queries:")
        examples = [
            "How many red running shoes are in stock?",
            "I need comfortable shoes for jogging",
            "Place an order for SHOES-RUN001",
            "Track my shipment ABC123",
            "What's the demand forecast for winter boots?"
        ]
        
        for example in examples:
            print(f"   • '{example}'")
        
        print("\n🔧 Available Commands:")
        commands = [
            ("help", "Show all commands"),
            ("history", "View conversation history"),
            ("stats", "Show session statistics"),
            ("settings", "Adjust preferences"),
            ("export", "Export conversation data"),
            ("clear", "Clear screen"),
            ("quit", "Exit application")
        ]
        
        for cmd, desc in commands:
            print(f"   • {cmd:<10} - {desc}")
        
        print("\n✨ Ready for intelligent conversations!")
    
    def get_user_input(self) -> Optional[str]:
        """Enhanced user input with features"""
        try:
            # Show performance hint if enabled
            if (self.user_preferences.get("show_performance") and 
                self.performance_monitor and 
                len(self.conversation_history) > 0):
                
                stats = self.performance_monitor.get_stats()
                avg_time = stats.get("avg_response_time", 0)
                print(f"📊 Avg response time: {avg_time:.2f}s")
            
            prompt = "🗣️  You: "
            user_input = input(prompt).strip()
            return user_input
            
        except (EOFError, KeyboardInterrupt):
            return None
    
    def handle_commands(self, user_input: str) -> bool:
        """Handle CLI commands"""
        cmd = user_input.lower().strip()
        
        if cmd == 'quit' or cmd == 'exit':
            print("👋 Thank you for using Price Pilot!")
            self.save_session_data()
            self.running = False
            return True
            
        elif cmd == 'help':
            self.show_help()
            return True
            
        elif cmd == 'history':
            self.show_conversation_history()
            return True
            
        elif cmd == 'stats':
            self.show_session_statistics()
            return True
            
        elif cmd == 'settings':
            self.show_settings_menu()
            return True
            
        elif cmd == 'export':
            self.export_conversation_data()
            return True
            
        elif cmd == 'clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            return True
            
        elif cmd == 'status':
            self.show_system_status()
            return True
            
        elif cmd.startswith('set '):
            self.handle_setting_command(cmd)
            return True
            
        return False
    
    def process_query(self, user_input: str) -> Dict[str, Any]:
        """Process user query with enhanced error handling"""
        try:
            from langchain_core.messages import HumanMessage
            
            # Initialize state
            state = self.initialize_state()
            state["messages"] = [HumanMessage(content=user_input)]
            
            # Show processing indicator
            print("🤖 Processing", end="", flush=True)
            
            # Process with orchestrator
            result = self.orchestrator(state)
            
            print("\r" + " " * 20 + "\r", end="")  # Clear processing indicator
            
            # Extract response
            response = result["messages"][-1].content
            
            return {
                "query": user_input,
                "response": response,
                "intent": result.get("intent", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "agent_used": result.get("agent_selection_reason", "Unknown agent"),
                "performance_metrics": result.get("performance_metrics", {}),
                "user_context": result.get("user_context", {}),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "query": user_input,
                "response": f"I apologize, but I encountered an error: {str(e)}\nPlease try rephrasing your question.",
                "intent": "error",
                "confidence": 0.0,
                "agent_used": "Error handler",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def display_response(self, response_data: Dict[str, Any], processing_time: float):
        """Display response with enhanced formatting"""
        # Show intent detection if enabled
        if self.user_preferences.get("show_intent_detection"):
            intent = response_data.get("intent", "unknown")
            confidence = response_data.get("confidence", 0.0)
            
            # Color-code confidence
            confidence_emoji = "🎯" if confidence > 0.8 else "🤔" if confidence > 0.5 else "❓"
            print(f"{confidence_emoji} Intent: {intent} (confidence: {confidence:.1%})")
        
        # Show performance metrics if enabled
        if self.user_preferences.get("show_performance"):
            print(f"⚡ Response time: {processing_time:.2f}s")
            
            if "performance_metrics" in response_data:
                metrics = response_data["performance_metrics"]
                total_duration = metrics.get("total_duration", 0)
                if total_duration > 0:
                    print(f"🔧 Internal processing: {total_duration:.2f}s")
        
        # Main response
        response = response_data.get("response", "No response available")
        print(f"🤖 Assistant: {response}")
        
        # Show agent info if available
        agent_info = response_data.get("agent_used", "")
        if agent_info and "Agent" in agent_info:
            print(f"🎭 Handled by: {agent_info}")
    
    def update_session_stats(self, response_data: Dict[str, Any], processing_time: float):
        """Update session statistics"""
        self.session_stats["queries_processed"] += 1
        
        # Update average response time
        current_avg = self.session_stats["average_response_time"]
        queries_count = self.session_stats["queries_processed"]
        self.session_stats["average_response_time"] = (
            (current_avg * (queries_count - 1) + processing_time) / queries_count
        )
        
        # Track intent distribution
        intent = response_data.get("intent", "unknown")
        self.session_stats["intents_detected"][intent] += 1
        
        # Store in conversation history
        self.conversation_history.append(response_data)
        
        # Auto-save if enabled
        if self.user_preferences.get("auto_save_history") and len(self.conversation_history) % 10 == 0:
            self.auto_save_history()
    
    def show_help(self):
        """Display comprehensive help"""
        print_subheader("Available Commands", "📖")
        
        commands = {
            "Basic Commands": [
                ("help", "Show this help message"),
                ("quit, exit", "Exit the application"),
                ("clear", "Clear the screen"),
                ("status", "Show system status")
            ],
            "Conversation Management": [
                ("history", "View recent conversation history"),
                ("export", "Export conversation to file"),
                ("stats", "Show detailed session statistics")
            ],
            "Settings & Preferences": [
                ("settings", "Open settings menu"),
                ("set <option> <value>", "Change a setting"),
                ("set performance on/off", "Toggle performance display"),
                ("set intent on/off", "Toggle intent detection display")
            ],
            "Query Examples": [
                ("inventory queries", "'How many blue shirts in stock?'"),
                ("recommendation", "'I need running shoes for marathons'"),
                ("orders", "'Place order for SHOES-RUN001'"),
                ("tracking", "'Track shipment ABC123'"),
                ("forecasting", "'Predict demand for winter coats'")
            ]
        }
        
        for category, cmd_list in commands.items():
            print(f"\n📂 {category}:")
            for cmd, desc in cmd_list:
                print(f"   {cmd:<20} - {desc}")
    
    def show_conversation_history(self):
        """Display enhanced conversation history"""
        print_subheader("Conversation History", "📜")
        
        if not self.conversation_history:
            print("No conversations yet.")
            return
        
        # Show configurable number of recent conversations
        show_count = min(10, len(self.conversation_history))
        recent_conversations = self.conversation_history[-show_count:]
        
        for i, conv in enumerate(recent_conversations, 1):
            print(f"\n{i}. 🗣️  Query: {conv['query']}")
            
            # Truncate long responses
            response = conv.get('response', 'No response')
            if len(response) > 150:
                response = response[:150] + "..."
            print(f"   🤖 Response: {response}")
            
            # Show metadata
            intent = conv.get('intent', 'unknown')
            confidence = conv.get('confidence', 0.0)
            timestamp = conv.get('timestamp', '')
            
            if timestamp:
                time_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = time_obj.strftime('%H:%M:%S')
            else:
                time_str = 'Unknown'
            
            print(f"   📊 Intent: {intent} ({confidence:.1%}) | Time: {time_str}")
        
        if len(self.conversation_history) > show_count:
            remaining = len(self.conversation_history) - show_count
            print(f"\n... and {remaining} more conversations")
            print("💡 Use 'export' to save full history to file")
    
    def show_session_statistics(self):
        """Show detailed session statistics"""
        print_subheader("Session Statistics", "📊")
        
        # Basic stats
        duration = datetime.now() - self.session_stats["start_time"]
        print(f"🕐 Session duration: {self.format_duration(duration)}")
        print(f"💬 Queries processed: {self.session_stats['queries_processed']}")
        print(f"⚡ Average response time: {self.session_stats['average_response_time']:.2f}s")
        
        # Intent distribution
        if self.session_stats["intents_detected"]:
            print(f"\n🎯 Intent Distribution:")
            total_intents = sum(self.session_stats["intents_detected"].values())
            
            for intent, count in sorted(
                self.session_stats["intents_detected"].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                percentage = (count / total_intents) * 100
                bar_length = int(percentage / 5)  # Scale bar to fit
                bar = "█" * bar_length + "░" * (20 - bar_length)
                print(f"   {intent:<12} {bar} {count:>3} ({percentage:>5.1f}%)")
        
        # Performance stats from monitor
        if self.performance_monitor:
            monitor_stats = self.performance_monitor.get_stats()
            if monitor_stats.get("total_requests", 0) > 0:
                print(f"\n🔧 System Performance:")
                print(f"   Total requests: {monitor_stats['total_requests']}")
                print(f"   Avg response time: {monitor_stats['avg_response_time']:.2f}s")
                print(f"   Max response time: {monitor_stats['max_response_time']:.2f}s")
                print(f"   Requests last hour: {monitor_stats['requests_last_hour']}")
    
    def show_settings_menu(self):
        """Interactive settings menu"""
        print_subheader("Settings & Preferences", "⚙️")
        
        settings_options = [
            ("show_performance", "Display performance metrics", bool),
            ("show_intent_detection", "Show intent detection results", bool),
            ("auto_save_history", "Auto-save conversation history", bool),
            ("debug_mode", "Enable debug mode", bool)
        ]
        
        print("Current settings:")
        for i, (key, desc, data_type) in enumerate(settings_options, 1):
            current_value = self.user_preferences.get(key, False)
            status = "✅" if current_value else "❌"
            print(f"   {i}. {desc}: {status}")
        
        print(f"\n💡 To change a setting, use: set <setting_name> <on/off>")
        print(f"   Example: set performance on")
    
    def handle_setting_command(self, cmd: str):
        """Handle setting commands"""
        parts = cmd.split()
        if len(parts) < 3:
            print_error("Usage: set <setting> <value>")
            return
        
        setting_name = parts[1]
        value = parts[2].lower()
        
        # Map common setting names
        setting_map = {
            "performance": "show_performance",
            "intent": "show_intent_detection",
            "autosave": "auto_save_history",
            "debug": "debug_mode"
        }
        
        actual_setting = setting_map.get(setting_name, setting_name)
        
        if actual_setting not in self.user_preferences:
            print_error(f"Unknown setting: {setting_name}")
            return
        
        # Convert value
        if value in ["on", "true", "yes", "1"]:
            new_value = True
        elif value in ["off", "false", "no", "0"]:
            new_value = False
        else:
            print_error(f"Invalid value: {value}. Use on/off, true/false, yes/no")
            return
        
        # Update setting
        old_value = self.user_preferences[actual_setting]
        self.user_preferences[actual_setting] = new_value
        
        status = "enabled" if new_value else "disabled"
        print_success(f"Setting '{setting_name}' {status}")
        
        if old_value != new_value:
            print_info("Setting will take effect for new queries")
    
    def export_conversation_data(self):
        """Export conversation history and statistics"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/price_pilot_session_{timestamp}.json"
            
            export_data = {
                "session_info": {
                    "start_time": self.session_stats["start_time"].isoformat(),
                    "export_time": datetime.now().isoformat(),
                    "total_queries": self.session_stats["queries_processed"],
                    "average_response_time": self.session_stats["average_response_time"]
                },
                "conversation_history": self.conversation_history,
                "session_statistics": {
                    "intents_detected": dict(self.session_stats["intents_detected"])
                },
                "user_preferences": self.user_preferences
            }
            
            # Add performance data if available
            if self.performance_monitor:
                export_data["performance_data"] = self.performance_monitor.get_stats()
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            print_success(f"Conversation data exported to: {filename}")
            print_info(f"File size: {os.path.getsize(filename)} bytes")
            
        except Exception as e:
            print_error(f"Failed to export data: {e}")
    
    def show_system_status(self):
        """Enhanced system status display"""
        print_subheader("System Status", "🖥️")
        
        # Orchestrator status
        orchestrator_status = "🟢 Running (Optimized)" if self.performance_monitor else "🟡 Running (Basic)"
        print(f"Orchestrator: {orchestrator_status}")
        
        # Agent status
        print("🟢 Agents: 6 agents loaded and ready")
        
        # Session info
        print(f"💬 Conversations: {len(self.conversation_history)} this session")
        print(f"🕐 Session uptime: {self.format_duration(datetime.now() - self.session_stats['start_time'])}")
        
        # Recent activity
        if self.conversation_history:
            recent_intents = [
                conv.get("intent", "unknown") 
                for conv in self.conversation_history[-5:]
            ]
            print(f"📊 Recent intents: {', '.join(recent_intents)}")
            
            # Average confidence
            recent_confidences = [
                conv.get("confidence", 0.0) 
                for conv in self.conversation_history[-10:]
                if conv.get("confidence", 0.0) > 0
            ]
            if recent_confidences:
                avg_confidence = sum(recent_confidences) / len(recent_confidences)
                print(f"🎯 Average intent confidence: {avg_confidence:.1%}")
        
        # Performance info
        if self.performance_monitor:
            stats = self.performance_monitor.get_stats()
            if stats.get("total_requests", 0) > 0:
                print(f"⚡ System performance: {stats['avg_response_time']:.2f}s avg response time")
    
    def start_performance_monitoring(self):
        """Start background performance monitoring"""
        def monitor_loop():
            while self.running:
                try:
                    # Could add periodic health checks here
                    time.sleep(30)  # Check every 30 seconds
                except Exception:
                    break
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def auto_save_history(self):
        """Auto-save conversation history"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"auto_save_{timestamp}.json"
            
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "conversation_count": len(self.conversation_history),
                "recent_conversations": self.conversation_history[-10:]  # Last 10 only
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
                
        except Exception:
            pass  # Silent fail for auto-save
    
    def save_session_data(self):
        """Save session data on exit"""
        if self.user_preferences.get("auto_save_history") and self.conversation_history:
            print_info("Saving session data...")
            self.export_conversation_data()
    
    @staticmethod
    def format_duration(duration: timedelta) -> str:
        """Format duration in human-readable format"""
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

def main():
    """Enhanced main CLI function"""
    try:
        cli = PricePilotCLI()
        
        # Load orchestrator with fallback
        if not cli.load_orchestrator():
            print_error("Cannot start without orchestrator. Please check your installation.")
            return 1
        
        # Start interactive mode
        cli.interactive_chat()
        
        return 0
        
    except Exception as e:
        print_error(f"Critical error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)