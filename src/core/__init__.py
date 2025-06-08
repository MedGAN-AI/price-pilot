"""
Core module for shared agent functionality.

This module provides base classes, utilities, and factories for building
multi-agent systems with consistent structure and behavior.
"""
'''
from .base_agent import BaseAgent, AgentState, initialize_state, build_agent
from .llm_factory import LLMFactory
from .utils import (
    load_config,
    load_prompt_from_file,
    compile_regex_pattern,
    validate_agent_config,
    get_project_root,
    safe_get_nested_config
)

__all__ = [
    # Base Agent Classes
    'BaseAgent',
    'AgentState',
    'initialize_state',
    'build_agent',
    
    # LLM Factory
    'LLMFactory',
    
    # Utility Functions
    'load_config',
    'load_prompt_from_file',
    'compile_regex_pattern',
    'validate_agent_config',
    'get_project_root',
    'safe_get_nested_config'
]

# Version information
__version__ = "1.0.0"
__author__ = "Price Pilot Team"'''