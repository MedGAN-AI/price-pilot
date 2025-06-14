"""
Agent Template for Core Framework Migration
Standardized template for creating new agents or migrating existing ones
"""
import os
import yaml
from typing import List, Dict, Any, Optional

# Import core framework
from .base_agent import build_agent, create_llm_from_config, AgentState, initialize_state, AgentType
from .utils import load_config, create_prompt_from_template, standardize_agent_config
from .error_handling import create_agent_error_handler
from .display_constants import SUCCESS, ERROR, ROBOT

class AgentTemplate:
    """
    Template class for creating standardized agents using core framework.
    Use this as a base for new agents or migration guide for existing ones.
    """
    
    def __init__(self, agent_name: str, agent_directory: str):
        self.agent_name = agent_name
        self.agent_directory = agent_directory
        self.error_handler = create_agent_error_handler(agent_name)
        
        # Load and standardize configuration
        config_path = os.path.join(agent_directory, "config.yaml")
        raw_config = load_config(config_path)
        self.config = standardize_agent_config(raw_config)
        
        # Create LLM from standardized config
        self.llm = create_llm_from_config(self.config)
        
        # Load tools (to be implemented by each agent)
        self.tools = self._load_tools()
        
        # Load prompt template
        prompt_path = os.path.join(agent_directory, "prompts", f"{agent_name.lower()}_prompt.txt")
        self.prompt = create_prompt_from_template(prompt_path)
        
        # Build agent graph
        self.agent_graph = self._build_agent()
    
    def _load_tools(self) -> List:
        """
        Load agent-specific tools. Override this method in each agent.
        """
        raise NotImplementedError("Each agent must implement _load_tools()")
    
    def _build_agent(self):
        """Build the agent using core framework"""
        agent_config = self.config.get("agent", {})
        agent_type = agent_config.get("type", AgentType.REACT)
        max_iterations = agent_config.get("max_iterations", 10)
        
        # Build configuration for the core framework
        build_config = {
            "early_stopping_method": agent_config.get("early_stopping_method"),
            "max_execution_time": agent_config.get("max_execution_time"),
            "stop_keywords": self.config.get("specialized_config", {}).get("stop_keywords", []),
            "context_key": self.config.get("specialized_config", {}).get("context_key", "context")
        }
        
        return build_agent(
            llm=self.llm,
            tools=self.tools,
            prompt_template=self.prompt,
            max_iterations=max_iterations,
            agent_type=agent_type,
            agent_config=build_config
        )
    
    def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a user query using the standardized agent.
        """
        try:
            # Initialize state with optional context
            state = initialize_state()
            if context:
                state["context"] = context
            
            # Add user message
            state["messages"] = [{"type": "human", "content": query}]
            
            # Invoke agent
            result = self.agent_graph.invoke(state)
            
            # Extract response
            if result.get("messages"):
                final_message = result["messages"][-1]
                if hasattr(final_message, 'content'):
                    return final_message.content
                elif isinstance(final_message, dict):
                    return final_message.get('content', 'No response')
            
            return 'No response generated'
            
        except Exception as e:
            return self.error_handler.handle_llm_error(e)
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information"""
        return {
            "agent_name": self.agent_name,
            "status": "active",
            "tools_count": len(self.tools),
            "config": self.config,
            "framework_version": "core_v2"
        }

def create_migration_checklist(agent_name: str) -> List[str]:
    """
    Generate migration checklist for an existing agent.
    """
    return [
        f"✅ Update {agent_name}/agent.py imports to use core framework",
        f"✅ Standardize {agent_name}/config.yaml structure",
        f"✅ Update prompt template format in {agent_name}/prompts/",
        f"✅ Replace custom AgentState with core AgentState",
        f"✅ Replace custom initialize_state with core initialize_state",
        f"✅ Replace custom agent building with build_agent()",
        f"✅ Replace custom LLM creation with create_llm_from_config()",
        f"✅ Add error handling using core error_handling",
        f"✅ Update test files to use new agent interface",
        f"✅ Verify agent works with orchestrator"
    ]

# Export template for easy imports
__all__ = ['AgentTemplate', 'create_migration_checklist']
