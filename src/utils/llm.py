"""
Docstring for src.tools.llm
"""
import os
from typing import Optional
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from src.utils.config import cfg

def get_llm(profile: str = "default") -> BaseChatModel:
    """
    Factory to get an LLM instance based on configuration profiles.
    
    Args:
        profile: The key in config.yaml under 'llm' (e.g., 'default', 'creative')
    """
    provider = cfg.get("llm.provider")
    
    # Fetch specific settings for this profile, falling back to default if missing
    model_name = cfg.get(f"llm.{profile}.model", cfg.get("llm.default.model"))
    temperature = cfg.get(f"llm.{profile}.temperature", cfg.get("llm.default.temperature"))
    max_tokens = cfg.get(f"llm.{profile}.max_tokens", cfg.get("llm.default.max_tokens"))
    
    if provider == "google":
        # Gemini specific setup
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable is missing.")

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=cfg.get(f"llm.{profile}.top_p", 0.95),
            top_k=cfg.get(f"llm.{profile}.top_k", 64),
            # Gemini Safety Settings - Crucial for coding to prevent blocking valid code
            safety_settings={
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_ONLY_HIGH",
                "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH",
            }
        )
        
    elif provider == "openai":
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
    elif provider == "anthropic":
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")