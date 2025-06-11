# base_agent.py
# Shared scaffold for all agents: initializes LLM, tools, and builds a LangGraph StateGraph

import os
from dotenv import load_dotenv
from typing import Any, Dict, List, TypedDict, Annotated
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

# Define common state shape
class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    intermediate_steps: List

# Helper to initialize state
def initialize_state() -> AgentState:
    return {"messages": [], "intermediate_steps": []}

# Factory to build an executor + graph for an agent
# llm: pre-configured LLM instance
# tools: list of langchain_core.tools.Tool
# prompt_template: PromptTemplate or raw system prompt string
# max_iterations: safety for loops
def build_agent(llm, tools, prompt_template: PromptTemplate, max_iterations: int = 10) -> StateGraph:
    load_dotenv()
    # Convert raw prompt string to PromptTemplate if needed
    if isinstance(prompt_template, str):
        prompt = PromptTemplate.from_template(prompt_template)
    else:
        prompt = prompt_template    # Create the agent and executor
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,  # Reduced from 10 to 3 to force faster completion
        early_stopping_method="generate",  # Stop early if possible
        return_intermediate_steps=True
    )    # Define the assistant node for the StateGraph
    def assistant(state: AgentState) -> Dict[str, Any]:
        try:
            user_message = state["messages"][-1].content
            
            # Custom stopping logic for get_available_products
            if "get_available_products" in str(state.get("intermediate_steps", [])):
                # If we already called get_available_products, don't run executor again
                return {
                    "messages": [AIMessage(content="I've already shown you the available products. Please let me know which items you'd like to order.")],
                    "intermediate_steps": []
                }
            
            result = executor.invoke({"input": user_message})
            content = result["output"]
            if isinstance(content, dict):
                content = content.get("output") or content.get("tool_input") or str(content)
            return {"messages": [AIMessage(content=content)], "intermediate_steps": result.get("intermediate_steps", [])}
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {e}"
            return {"messages": [AIMessage(content=error_msg)], "intermediate_steps": []}

    # Build and compile the StateGraph
    builder = StateGraph(AgentState)
    builder.add_node("assistant", assistant)
    builder.add_edge(START, "assistant")
    builder.add_edge("assistant", END)
    return builder.compile()


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
def load_prompt_from_file(prompt_path: str) -> PromptTemplate:
    """Load system prompt from file and convert to PromptTemplate."""
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    return PromptTemplate.from_template(system_prompt)