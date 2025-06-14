"""
Dynamic Agent Registry System
Automatically discovers and integrates all agents without manual configuration
"""
import os
import sys
import importlib
import inspect
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    Automatically discovers and manages all agents in the system
    No manual configuration required - agents self-register
    """
    
    def __init__(self, agents_path: str = "src/agents"):
        self.agents_path = agents_path
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.intent_mappings: Dict[str, str] = {}
        self.agent_instances: Dict[str, Any] = {}
        
        # Auto-discover all agents
        self._discover_agents()
    
    def _discover_agents(self):
        """Automatically discover all agents in the agents directory"""
        agents_dir = Path(self.agents_path)
        
        if not agents_dir.exists():
            logger.error(f"Agents directory not found: {agents_dir}")
            return
        
        # Scan for agent directories
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir() and not agent_dir.name.startswith('__'):
                self._discover_agent(agent_dir)
    
    def _discover_agent(self, agent_dir: Path):
        """Discover and register a single agent"""
        agent_name = agent_dir.name
        
        try:
            # Look for agent.py file
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                logger.warning(f"No agent.py found in {agent_dir}")
                return
            
            # Import the agent module
            module_path = f"{self.agents_path.replace('/', '.')}.{agent_name}.agent"
            agent_module = importlib.import_module(module_path)
            
            # Auto-detect agent class and graph
            agent_info = self._extract_agent_info(agent_module, agent_name)
            
            if agent_info:
                self.registered_agents[agent_name] = agent_info
                logger.info(f"✅ Auto-registered {agent_name}: {agent_info['intents']}")
            else:
                logger.warning(f"⚠️ Could not auto-register {agent_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to discover {agent_name}: {e}")
    
    def _extract_agent_info(self, module, agent_name: str) -> Optional[Dict[str, Any]]:
        """Extract agent information from module"""
        agent_info = {
            "name": agent_name,
            "module": module,
            "intents": [],
            "graph": None,
            "wrapper_class": None,
            "prompt_path": None,
            "config_path": None
        }
        
        # Common patterns for agent graphs
        graph_names = [
            f"{agent_name.lower()}_graph",
            f"{agent_name.lower()}_agent_graph", 
            f"{agent_name.lower()}_assistant",
            "agent_graph",
            "graph"
        ]
        
        # Find the agent graph
        for graph_name in graph_names:
            if hasattr(module, graph_name):
                agent_info["graph"] = getattr(module, graph_name)
                break
        
        # Find wrapper class
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.endswith("Agent"):
                agent_info["wrapper_class"] = obj
                break
        
        # Determine intents based on agent name
        intent_mapping = {
            "ChatAgent": ["chat", "greeting", "general"],
            "OrderAgent": ["order", "buy", "purchase"],
            "InventoryAgent": ["inventory", "stock", "available"],
            "RecommendAgent": ["recommend", "suggest", "find"],
            "LogisticsAgent": ["logistics", "shipping", "delivery"],
            "ForecastAgent": ["forecast", "predict", "analytics"]
        }
        
        agent_info["intents"] = intent_mapping.get(agent_name, [agent_name.lower().replace("agent", "")])
        
        # Look for prompt and config files
        agent_dir = Path(self.agents_path) / agent_name
        
        prompt_dir = agent_dir / "prompts"
        if prompt_dir.exists():
            for prompt_file in prompt_dir.glob("*.txt"):
                agent_info["prompt_path"] = str(prompt_file)
                break
        
        config_file = agent_dir / "config.yaml"
        if config_file.exists():
            agent_info["config_path"] = str(config_file)
        
        return agent_info if (agent_info["graph"] or agent_info["wrapper_class"]) else None
    
    def get_agent_for_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        """Get the appropriate agent for an intent"""
        for agent_name, agent_info in self.registered_agents.items():
            if intent in agent_info["intents"]:
                return agent_info
        
        # Fallback to ChatAgent
        return self.registered_agents.get("ChatAgent")
    
    def get_agent_instance(self, agent_name: str) -> Any:
        """Get or create agent instance"""
        if agent_name not in self.agent_instances:
            agent_info = self.registered_agents.get(agent_name)
            if not agent_info:
                return None
            
            # Create instance
            if agent_info["wrapper_class"]:
                self.agent_instances[agent_name] = agent_info["wrapper_class"]()
            elif agent_info["graph"]:
                # Create a simple wrapper for graph-based agents
                self.agent_instances[agent_name] = GraphAgentWrapper(
                    agent_info["graph"], 
                    agent_name
                )
            else:
                return None
        
        return self.agent_instances[agent_name]
    
    def reload_agent(self, agent_name: str):
        """Reload a specific agent (useful for prompt/config changes)"""
        if agent_name in self.agent_instances:
            del self.agent_instances[agent_name]
        
        # Re-discover the agent
        agent_dir = Path(self.agents_path) / agent_name
        if agent_dir.exists():
            # Reload the module
            module_path = f"{self.agents_path.replace('/', '.')}.{agent_name}.agent"
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
            
            self._discover_agent(agent_dir)
            logger.info(f"🔄 Reloaded {agent_name}")
    
    def get_all_agents_status(self) -> Dict[str, str]:
        """Get status of all registered agents"""
        status = {}
        for agent_name, agent_info in self.registered_agents.items():
            try:
                instance = self.get_agent_instance(agent_name)
                if instance:
                    status[agent_name] = "✅ Ready"
                else:
                    status[agent_name] = "❌ Failed to initialize"
            except Exception as e:
                status[agent_name] = f"❌ Error: {str(e)[:50]}"
        
        return status
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get complete registry information"""
        return {
            "total_agents": len(self.registered_agents),
            "agents": {
                name: {
                    "intents": info["intents"],
                    "has_graph": info["graph"] is not None,
                    "has_wrapper": info["wrapper_class"] is not None,
                    "has_prompt": info["prompt_path"] is not None,
                    "has_config": info["config_path"] is not None
                }
                for name, info in self.registered_agents.items()
            },
            "discovery_time": datetime.now().isoformat()
        }


class GraphAgentWrapper:
    """Wrapper for graph-based agents to provide consistent interface"""
    
    def __init__(self, graph, agent_name: str):
        self.graph = graph
        self.agent_name = agent_name
    
    def process_query(self, query: str) -> str:
        """Process query through the graph"""
        try:
            from src.core.base_agent import initialize_state
            from langchain_core.messages import HumanMessage
            
            state = initialize_state()
            state["messages"] = [HumanMessage(content=query)]
            
            result = self.graph.invoke(state)
            
            if result and "messages" in result and result["messages"]:
                return result["messages"][-1].content
            else:
                return f"I apologize, but I couldn't process your request through {self.agent_name}."
                
        except Exception as e:
            return f"I encountered an issue: {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """Get wrapper status"""
        return {
            "agent_name": self.agent_name,
            "type": "graph_wrapper",
            "status": "ready"
        }


# Global registry instance
agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry"""
    return agent_registry


def reload_all_agents():
    """Reload all agents (useful for development)"""
    global agent_registry
    agent_registry = AgentRegistry()
    logger.info("🔄 All agents reloaded")


if __name__ == "__main__":
    # Test the registry
    registry = AgentRegistry()
    
    print("🔍 Discovered Agents:")
    for name, info in registry.get_registry_info()["agents"].items():
        print(f"  {name}: {info['intents']}")
    
    print(f"\n📊 Agent Status:")
    for name, status in registry.get_all_agents_status().items():
        print(f"  {name}: {status}")
