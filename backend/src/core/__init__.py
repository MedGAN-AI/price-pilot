"""
Core module for shared agent functionality.

This module provides base classes, utilities, and factories for building
multi-agent systems with consistent structure and behavior.
"""

from .base_agent import AgentState, initialize_state, build_agent, create_llm_from_config, load_prompt_from_file, AgentType
from .llm_factory import LLMFactory
from .utils import (
    load_config,
    compile_regex_pattern,
    validate_agent_config,
    get_project_root,
    safe_get_nested_config,
    standardize_agent_config,
    create_agent_config_template,
    extract_agent_patterns,
    create_prompt_from_template
)
from .error_handling import ErrorHandler, AgentErrorHandler, create_agent_error_handler
from .display_constants import *
from .agent_template import AgentTemplate, create_migration_checklist

__all__ = [
    # Base Agent Framework
    'AgentState',
    'initialize_state', 
    'build_agent',
    'create_llm_from_config',
    'load_prompt_from_file',
    'AgentType',
    
    # LLM Factory
    'LLMFactory',
    
    # Enhanced Utilities
    'load_config',
    'compile_regex_pattern',
    'validate_agent_config',
    'get_project_root',
    'safe_get_nested_config',
    'standardize_agent_config',
    'create_agent_config_template',
    'extract_agent_patterns',
    'create_prompt_from_template',
    
    # Error Handling
    'ErrorHandler',
    'AgentErrorHandler',
    'create_agent_error_handler',
    
    # Agent Template
    'AgentTemplate',
    'create_migration_checklist'
]

# Version information
__version__ = "2.0.0"
__author__ = "Price Pilot Team"