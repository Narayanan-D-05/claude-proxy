"""Utilities for sanitizing model identity in requests."""

import re
from loguru import logger
from config.settings import Settings

def cleanup_model_identity(request_data, settings: Settings) -> None:
    """Replace Claude/Anthropic/Sonnet references with the actual model name."""
    if not settings.enable_model_identity_cleanup:
        return

    # Extract the target model name (short version if possible)
    # e.g. "nvidia_nim/moonshotai/kimi-k2-instruct-0905" -> "Kimi-K2-Instruct"
    # Priority for model name:
    # 1. Explicitly resolved provider model from routes
    # 2. The model field in the request
    # 3. The default model from settings
    full_model = getattr(request_data, "resolved_provider_model", None) or getattr(request_data, "model", None) or settings.model
    
    model_name = Settings.parse_model_name(full_model) if "/" in full_model else full_model

    
    # Try to simplify name (e.g. meta/llama-3.1-405b -> Llama-3.1-405b)
    if "/" in model_name:
        model_name = model_name.split("/")[-1]
    
    # Title case for brand appearance
    model_name = model_name.replace("-", " ").title().replace(" ", "-")
    
    # Basic replacements
    # We use regex with word boundaries to handle various case sensitivity and pluralization
    # We replace the most specific multi-word patterns FIRST.
    replacements = [
        # Full product names
        (re.compile(r"\bClaude Code\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bClaude Sonnet\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bClaude Haiku\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bClaude Opus\b", re.IGNORECASE), f"{model_name}"),
        
        # Specific model versions (handles the '-sonnet-4-6' issue)
        (re.compile(r"\bclaude-sonnet-[0-9\.-]+\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bclaude-haiku-[0-9\.-]+\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bclaude-opus-[0-9\.-]+\b", re.IGNORECASE), f"{model_name}"),
        
        # General brands
        (re.compile(r"\bSonnet 4\.6\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bSonnet 3\.5\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bClaude\b", re.IGNORECASE), f"{model_name}"),
        (re.compile(r"\bAnthropic\b", re.IGNORECASE), "the AI provider"),
    ]

    def sanitize_text(text: str) -> str:
        if not text:
            return text
        new_text = text
        for pattern, replacement in replacements:
            new_text = pattern.sub(replacement, new_text)
        return new_text

    # 1. Sanitize System Prompt
    if request_data.system:
        if isinstance(request_data.system, str):
            request_data.system = sanitize_text(request_data.system)
        elif isinstance(request_data.system, list):
            for block in request_data.system:
                if hasattr(block, "text"):
                    block.text = sanitize_text(block.text)

    # 2. Sanitize Messages (both user and assistant to maintain consistency)
    for msg in request_data.messages:
        if isinstance(msg.content, str):
            msg.content = sanitize_text(msg.content)
        elif isinstance(msg.content, list):
            for block in msg.content:
                if hasattr(block, "text"):
                    block.text = sanitize_text(block.text)
                elif hasattr(block, "thinking"):
                    block.thinking = sanitize_text(block.thinking)

    logger.debug(f"IDENTITY_CLEANUP: Applied replacements for model '{model_name}'")
