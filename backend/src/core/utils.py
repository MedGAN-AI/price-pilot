# utils.py
# Enhanced shared utility functions for all agents

import os
import yaml
import re
from typing import Dict, Any, Optional, Union, List
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

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

def create_agent_config_template() -> Dict[str, Any]:
    """
    Create a standardized agent configuration template.
    All agents should follow this structure for consistency.
    """
    return {
        "llm": {
            "provider": "google-genai",
            "model": "gemini-2.0-flash",
            "temperature": 0.0
        },
        "agent": {
            "type": "react",  # react, tool_calling, structured_chat
            "max_iterations": 10,
            "early_stopping_method": "generate",
            "max_execution_time": 30
        },
        "specialized_config": {
            # Agent-specific configurations go here
        }
    }

def standardize_agent_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize an agent configuration by filling in defaults.
    """
    template = create_agent_config_template()
    
    # Merge with provided config
    if "llm" in config:
        template["llm"].update(config["llm"])
    if "agent" in config:
        template["agent"].update(config["agent"])
    if "specialized_config" in config:
        template["specialized_config"].update(config["specialized_config"])
    
    # Add any additional top-level keys
    for key, value in config.items():
        if key not in template:
            template[key] = value
    
    return template

def extract_agent_patterns(message: str) -> Dict[str, bool]:
    """
    Extract common patterns from user messages that help with agent behavior.
    """
    lower_msg = message.lower()
    
    return {
        "is_question": "?" in message,
        "is_urgent": any(word in lower_msg for word in ["urgent", "asap", "quickly", "fast", "immediately"]),
        "is_complex": len(message.split()) > 20,
        "mentions_multiple_items": message.count(" and ") > 1 or message.count(",") > 1,
        "contains_tracking": bool(re.search(r'[A-Z0-9]{8,20}', message)),
        "contains_sku": bool(re.search(r'[A-Z0-9\-]{5,}', message)),
        "contains_email": bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message))
    }

def create_prompt_from_template(template_path: str, replacements: Optional[Dict[str, str]] = None) -> Union[PromptTemplate, ChatPromptTemplate]:
    """
    Load prompt from file and apply optional replacements.
    Auto-detects whether to create PromptTemplate or ChatPromptTemplate.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Apply replacements if provided
    if replacements:
        for key, value in replacements.items():
            content = content.replace(f"{{{key}}}", value)
    
    # Detect if this should be a ChatPromptTemplate (contains role indicators)
    if any(indicator in content for indicator in ["{{system}}", "{{human}}", "{{assistant}}"]):
        # Parse chat template format
        return _parse_chat_template(content)
    else:
        return PromptTemplate.from_template(content)

def _parse_chat_template(content: str) -> ChatPromptTemplate:
    """Parse a chat template with role indicators"""
    # This is a simplified parser - can be enhanced as needed
    messages = []
    
    if "{{system}}" in content:
        system_content = content.split("{{system}}")[1].split("{{")[0].strip()
        messages.append(("system", system_content))
    
    if "{{human}}" in content:
        human_content = "{input}\n{agent_scratchpad}"
        messages.append(("human", human_content))
    
    return ChatPromptTemplate.from_messages(messages)