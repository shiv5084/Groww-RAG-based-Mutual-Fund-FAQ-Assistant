"""
Groq LLM client for Phase 5 generation.

Handles API key management and communication with Groq API using OpenAI-compatible interface.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    # Try loading with error handling for encoding issues
    try:
        load_dotenv()
    except Exception as e:
        logger.warning(f"Failed to load .env with default method: {e}")
        # Try manual loading as fallback
        try:
            import os
            env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
            with open(env_path, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key.strip()] = value.strip()
            logger.info("Manual .env loading successful")
        except Exception as e2:
            logger.warning(f"Manual .env loading also failed: {e2}")
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv not installed. Environment variables will not be loaded from .env file")

try:
    import groq
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import openai
    # Fallback to OpenAI client if Groq not available
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class GroqProvider:
    """Groq LLM provider implementation using OpenAI-compatible API."""
    
    def __init__(self, api_key: str, model: str = "llama3-70b-8192", 
                 temperature: float = 0.2, max_tokens: int = 512):
        if not GROQ_AVAILABLE:
            raise ImportError("Groq package not installed. Install with: pip install groq>=0.4.0")
        
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        try:
            self.client = Groq(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def generate(self, messages: list, **kwargs) -> str:
        """Generate response using Groq API (OpenAI-compatible)."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate Groq configuration."""
        if not self.api_key or self.api_key.startswith("your_"):
            return False
        return True


class LLMClient:
    """
    Main LLM client for Phase 5 generation using Groq.
    
    Simplified client that only supports Groq with OpenAI-compatible API.
    """
    
    def __init__(self, api_key: Optional[str] = None,
                 model: Optional[str] = None, temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None):
        """
        Initialize LLM client with Groq.
        
        Args:
            api_key: Groq API key. If None, uses GROQ_API_KEY or LLM_API_KEY env var.
            model: Groq model name. If None, uses LLM_MODEL env var or default.
            temperature: Generation temperature. If None, uses LLM_TEMPERATURE env var.
            max_tokens: Maximum tokens. If None, uses LLM_MAX_TOKENS env var.
        """
        # Try Groq-specific API key first, then fallback to generic LLM_API_KEY
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "llama3-70b-8192")
        self.temperature = float(temperature or os.getenv("LLM_TEMPERATURE", "0.2"))
        self.max_tokens = int(max_tokens or os.getenv("LLM_MAX_TOKENS", "512"))
        
        self._provider_client = self._initialize_groq_provider()
        
        if not self.validate_config():
            raise ValueError("Invalid Groq configuration. Please check your API key.")
    
    def _initialize_groq_provider(self) -> GroqProvider:
        """Initialize Groq provider."""
        return GroqProvider(
            api_key=self.api_key,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    
    def generate(self, messages: list, **kwargs) -> str:
        """
        Generate response using Groq.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional parameters for Groq API
            
        Returns:
            Generated text response
        """
        return self._provider_client.generate(messages, **kwargs)
    
    def validate_config(self) -> bool:
        """Validate the current configuration."""
        return self._provider_client.validate_config()
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information (without exposing API key)."""
        return {
            "provider": "groq",
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "configured": self.validate_config()
        }
    
    @classmethod
    def from_env(cls) -> 'LLMClient':
        """Create LLMClient instance from environment variables."""
        return cls()
    
    @classmethod
    def validate_env(cls) -> Dict[str, bool]:
        """
        Validate environment configuration for Groq.
        
        Returns:
            Dictionary with validation status
        """
        groq_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
        
        return {
            "groq": bool(groq_key and not groq_key.startswith("your_"))
        }
    
    def list_available_models(self) -> list:
        """
        List available Groq models.
        
        Returns:
            List of available model names
        """
        try:
            models = self._provider_client.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Failed to list Groq models: {e}")
            return []


def create_llm_client(**kwargs) -> LLMClient:
    """
    Factory function to create Groq LLM client with common defaults.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Configured LLMClient instance
    """
    return LLMClient(**kwargs)


# Convenience functions for common use cases
def generate_answer(messages: list, **kwargs) -> str:
    """
    Quick answer generation function using Groq.
    
    Args:
        messages: List of message dictionaries
        **kwargs: Additional generation parameters
        
    Returns:
        Generated answer
    """
    client = LLMClient(**kwargs)
    return client.generate(messages)
