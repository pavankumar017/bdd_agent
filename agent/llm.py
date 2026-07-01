"""
LLM factory — returns the configured LangChain LLM instance.
Reads provider and model from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

_llm_instance = None  # Simple module-level cache


def get_llm():
    """
    Returns a LangChain chat model based on LLM_PROVIDER env var.
    Supported: openai (default), anthropic
    """
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("LLM_MODEL", "gpt-4o")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        base_url = os.getenv("OPENAI_BASE_URL")  # Optional proxy/local endpoint
        _llm_instance = ChatOpenAI(
            model=model,
            temperature=0.2,       # Low temp for consistent structured output
            max_tokens=4096,
            **({"base_url": base_url} if base_url else {}),
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        _llm_instance = ChatAnthropic(
            model=model or "claude-3-5-sonnet-20241022",
            temperature=0.2,
            max_tokens=4096,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        _llm_instance = ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash",
            temperature=0.2,
            max_output_tokens=4096,
        )

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            "Set LLM_PROVIDER=openai or LLM_PROVIDER=anthropic in your .env"
        )

    return _llm_instance


def reset_llm():
    """Reset the cached LLM instance (useful for testing)."""
    global _llm_instance
    _llm_instance = None
