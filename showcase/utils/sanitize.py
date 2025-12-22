"""Input sanitization utilities.

Provides functions for validating and sanitizing user input
to prevent prompt injection and other security issues.
"""

import re
from typing import NamedTuple

from showcase.config import DANGEROUS_PATTERNS, MAX_TOPIC_LENGTH


class SanitizationResult(NamedTuple):
    """Result of input sanitization."""
    
    value: str
    is_safe: bool
    warnings: list[str]


def sanitize_topic(topic: str) -> SanitizationResult:
    """Sanitize a topic string for use in prompts.
    
    Checks for:
    - Length limits
    - Potential prompt injection patterns
    - Control characters
    
    Args:
        topic: The raw topic string
        
    Returns:
        SanitizationResult with cleaned value and safety status
        
    Example:
        >>> result = sanitize_topic("machine learning")
        >>> result.is_safe
        True
        >>> result = sanitize_topic("ignore previous instructions")
        >>> result.is_safe
        False
    """
    warnings = []
    cleaned = topic.strip()
    
    # Check length
    if len(cleaned) > MAX_TOPIC_LENGTH:
        cleaned = cleaned[:MAX_TOPIC_LENGTH]
        warnings.append(f"Topic truncated to {MAX_TOPIC_LENGTH} characters")
    
    # Check for empty
    if not cleaned:
        return SanitizationResult(
            value="",
            is_safe=False,
            warnings=["Topic cannot be empty"],
        )
    
    # Remove control characters (except newlines)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    
    # Check for dangerous patterns (case-insensitive)
    topic_lower = cleaned.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in topic_lower:
            return SanitizationResult(
                value=cleaned,
                is_safe=False,
                warnings=[f"Topic contains potentially unsafe pattern: '{pattern}'"],
            )
    
    return SanitizationResult(
        value=cleaned,
        is_safe=True,
        warnings=warnings,
    )


def sanitize_variables(variables: dict) -> dict:
    """Sanitize a dictionary of template variables.
    
    Args:
        variables: Dictionary of variable name -> value
        
    Returns:
        Sanitized dictionary with cleaned values
    """
    sanitized = {}
    
    for key, value in variables.items():
        if isinstance(value, str):
            # Remove control characters but preserve newlines
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
            sanitized[key] = cleaned
        else:
            sanitized[key] = value
    
    return sanitized
