# base_agent.py
# Enhanced shared scaffold for all agents: supports multiple agent types and patterns

import os
from dotenv import load_dotenv
from typing import Any, Dict, List, TypedDict, Annotated, Optional, Union, Callable
from langchain.agents import AgentExecutor, create_react_agent, create_structured_chat_agent, create_tool_calling_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Enhanced common state shape to support different agent patterns
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List
    # Additional optional fields for specialized agents
    context: Optional[Dict[str, Any]]  # For LogisticsAgent shipment_context, etc.
    user_preferences: Optional[Dict[str, Any]]
    active_operations: Optional[List[str]]

# Helper to initialize state with optional fields
def initialize_state(additional_fields: Optional[Dict[str, Any]] = None) -> AgentState:
    base_state = {
        "messages": [], 
        "intermediate_steps": [],
        "context": {},
        "user_preferences": {},
        "active_operations": []
    }
    if additional_fields:
        base_state.update(additional_fields)
    return base_state

# Supported agent types
class AgentType:
    REACT = "react"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_CHAT = "structured_chat"

# Enhanced factory to build different types of agents
def build_agent(
    llm, 
    tools, 
    prompt_template: Union[PromptTemplate, ChatPromptTemplate, str], 
    max_iterations: int = 10,
    agent_type: str = AgentType.REACT,
    custom_assistant_fn: Optional[Callable] = None,
    agent_config: Optional[Dict[str, Any]] = None
) -> StateGraph:
    """
    Enhanced agent builder supporting multiple agent patterns.
    
    Args:
        llm: Pre-configured LLM instance
        tools: List of LangChain tools
        prompt_template: Prompt template (PromptTemplate, ChatPromptTemplate, or string)
        max_iterations: Maximum iterations for agent execution
        agent_type: Type of agent (react, tool_calling, structured_chat)
        custom_assistant_fn: Optional custom assistant function
        agent_config: Additional configuration for specialized behavior
    
    Returns:
        Compiled StateGraph
    """
    load_dotenv()
    
    # Prepare agent configuration
    config = agent_config or {}    # Handle different prompt types based on agent type
    if isinstance(prompt_template, str):
        if agent_type == AgentType.TOOL_CALLING:
            # For tool calling agents, use ChatPromptTemplate
            prompt = ChatPromptTemplate.from_messages([
                ("system", prompt_template),
                MessagesPlaceholder("chat_history", optional=True),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ])
        elif agent_type == AgentType.STRUCTURED_CHAT:
            # For structured chat agents, use PromptTemplate with required variables
            # The prompt should already contain {tools} and {tool_names} placeholders
            prompt = PromptTemplate.from_template(prompt_template)
        else:
            # For ReAct agents, use simple PromptTemplate
            # Add the required variables for ReAct agents
            formatted_template = prompt_template + "\n\nQuestion: {input}\n{agent_scratchpad}"
            prompt = PromptTemplate.from_template(formatted_template)
    else:
        prompt = prompt_template

    # Create appropriate agent based on type
    if agent_type == AgentType.REACT:
        agent = create_react_agent(llm, tools, prompt)
    elif agent_type == AgentType.TOOL_CALLING:
        agent = create_tool_calling_agent(llm, tools, prompt)
    elif agent_type == AgentType.STRUCTURED_CHAT:
        agent = create_structured_chat_agent(llm, tools, prompt)
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")

    # Create executor with enhanced configuration
    executor_config = {
        "agent": agent,
        "tools": tools,
        "verbose": True,
        "handle_parsing_errors": True,
        "max_iterations": max_iterations,
        "return_intermediate_steps": True
    }
    
    # Add optional configurations
    if config.get("early_stopping_method"):
        executor_config["early_stopping_method"] = config["early_stopping_method"]
    if config.get("max_execution_time"):
        executor_config["max_execution_time"] = config["max_execution_time"]
        
    executor = AgentExecutor.from_agent_and_tools(**executor_config)

    # Use custom assistant function if provided, otherwise use default
    assistant_fn = custom_assistant_fn or _default_assistant_factory(executor, config)

    # Build and compile the StateGraph
    builder = StateGraph(AgentState)
    builder.add_node("assistant", assistant_fn)
    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", END)
    return builder.compile()

def _default_assistant_factory(executor: AgentExecutor, config: Dict[str, Any]):
    """Factory to create default assistant function with configuration"""
    
    def assistant(state: AgentState) -> Dict[str, Any]:
        try:
            user_message = state["messages"][-1].content
            
            # Custom stopping logic for specific tools (like get_available_products)
            stop_keywords = config.get("stop_keywords", ["get_available_products"])
            for keyword in stop_keywords:
                if keyword in str(state.get("intermediate_steps", [])):
                    stop_message = config.get("stop_message", 
                        "I've already provided the information you requested. Please let me know if you need anything else.")
                    return {
                        "messages": [AIMessage(content=stop_message)],
                        "intermediate_steps": [],
                        "context": state.get("context", {}),
                        "user_preferences": state.get("user_preferences", {}),
                        "active_operations": state.get("active_operations", [])
                    }
            
            # Prepare input for executor
            executor_input = {"input": user_message}
            
            # Add chat history for structured chat agents
            if len(state["messages"]) > 1:
                # Include previous messages as chat history (excluding the current user message)
                executor_input["chat_history"] = state["messages"][:-1]
            
            # Add context fields if they exist
            if state.get("context"):
                # For agents that need context (like LogisticsAgent)
                context_key = config.get("context_key", "context")
                if context_key != "chat_history":  # Avoid conflict with chat_history
                    executor_input[context_key] = state["context"]
            
            result = executor.invoke(executor_input)
            content = result["output"]
            
            if isinstance(content, dict):
                content = content.get("output") or content.get("tool_input") or str(content)
                
            return {
                "messages": [AIMessage(content=content)], 
                "intermediate_steps": result.get("intermediate_steps", []),
                "context": state.get("context", {}),
                "user_preferences": state.get("user_preferences", {}),
                "active_operations": state.get("active_operations", [])
            }
            
        except Exception as e:
            error_msg = config.get("error_message", f"I apologize, but I encountered an error: {e}")
            return {
                "messages": [AIMessage(content=error_msg)], 
                "intermediate_steps": [],
                "context": state.get("context", {}),
                "user_preferences": state.get("user_preferences", {}),
                "active_operations": state.get("active_operations", [])
            }
    
    return assistant

# Helper to create LLM from config
def create_llm_from_config(config: Dict[str, Any]):
    """Create LLM instance based on config settings."""
    load_dotenv()
    
    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "google-genai")
    model = llm_config.get("model", "gemini-2.0-flash")
    temperature = llm_config.get("temperature", 0.0)
    
    if provider == "google-genai":
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set in .env to use google-genai provider.")
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
    else:
        raise ValueError(f"Unsupported llm.provider in config: {provider}")


# Helper to load prompt from file
def load_prompt_from_file(prompt_path: str) -> Union[PromptTemplate, ChatPromptTemplate]:
    """Load system prompt from file and convert to appropriate template."""
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    # Return as string - build_agent will handle conversion
    return system_prompt