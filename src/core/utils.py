# utils.py
# Shared utility functions for all agents

import os
import yaml
import re
from typing import Dict, Any, Optional
from langchain_core.prompts import PromptTemplate

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration from file.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        Dictionary containing configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file {config_path}: {e}")

def load_prompt_from_file(prompt_path: str) -> PromptTemplate:
    """
    Load system prompt from file and convert to PromptTemplate.
    
    Args:
        prompt_path: Path to the prompt text file
        
    Returns:
        PromptTemplate instance
        
    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    return PromptTemplate.from_template(system_prompt)

def compile_regex_pattern(pattern: str) -> re.Pattern:
    """
    Compile regex pattern with error handling.
    
    Args:
        pattern: Regular expression pattern string
        
    Returns:
        Compiled regex pattern
        
    Raises:
        re.error: If pattern is invalid
    """
    try:
        return re.compile(pattern)
    except re.error as e:
        raise re.error(f"Invalid regex pattern '{pattern}': {e}")

def validate_agent_config(config: Dict[str, Any], required_keys: list = None) -> bool:
    """
    Validate agent configuration has required keys.
    
    Args:
        config: Configuration dictionary
        required_keys: List of required configuration keys
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If required keys are missing
    """
    if required_keys is None:
        required_keys = ["llm"]
    
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(f"Missing required configuration keys: {missing_keys}")
    
    return True

def get_project_root() -> str:
    """
    Get the project root directory.
    
    Returns:
        Path to project root directory
    """
    # This assumes we're in src/core/utils.py and project root is 2 levels up
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, "../.."))

def safe_get_nested_config(config: Dict[str, Any], keys: list, default: Any = None) -> Any:
    """
    Safely get nested configuration value.
    
    Args:
        config: Configuration dictionary
        keys: List of nested keys (e.g., ['llm', 'provider'])
        default: Default value if key path doesn't exist
        
    Returns:
        Configuration value or default
    """
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current