# llm_factory.py
# Factory for creating LLM instances with different providers

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class LLMFactory:
    """Factory class for creating LLM instances based on configuration."""
    
    @staticmethod
    def create_llm(config: Dict[str, Any]) -> Any:
        """
        Create LLM instance based on configuration.
        
        Args:
            config: Dictionary containing LLM configuration
            
        Returns:
            Configured LLM instance
            
        Raises:
            ValueError: If provider is unsupported or required credentials are missing
        """
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider", "google-genai")
        model = llm_config.get("model", "gemini-2.0-flash")
        temperature = llm_config.get("temperature", 0.0)
        
        if provider == "google-genai":
            return LLMFactory._create_google_genai_llm(model, temperature)
        elif provider == "openai":
            return LLMFactory._create_openai_llm(model, temperature)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def _create_google_genai_llm(model: str, temperature: float) -> ChatGoogleGenerativeAI:
        """Create Google Generative AI LLM instance."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY must be set in .env to use google-genai provider.")
        
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )
    
    @staticmethod
    def _create_openai_llm(model: str, temperature: float):
        """Create OpenAI LLM instance (placeholder for future implementation)."""
        # This would be implemented when OpenAI support is added
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """
        Validate LLM configuration.
        
        Args:
            config: Dictionary containing LLM configuration
            
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        llm_config = config.get("llm", {})
        provider = llm_config.get("provider")
        
        if not provider:
            raise ValueError("LLM provider must be specified in config")
        
        if provider == "google-genai" and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY must be set for google-genai provider")
        
        return True