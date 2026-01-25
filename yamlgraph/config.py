"""Centralized configuration for the yamlgraph package.

Provides paths, settings, and environment configuration
used across all modules.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Package root (yamlgraph/ directory)
PACKAGE_ROOT = Path(__file__).parent

# Working directory (where the user runs the CLI from)
WORKING_DIR = Path.cwd()

# Load environment variables from current working directory
# This ensures .env is found where the user runs yamlgraph, not in site-packages
load_dotenv(WORKING_DIR / ".env")

# Directory paths (relative to working directory)
PROMPTS_DIR = WORKING_DIR / "prompts"
GRAPHS_DIR = WORKING_DIR / "graphs"
OUTPUTS_DIR = WORKING_DIR / "outputs"
DATABASE_PATH = OUTPUTS_DIR / "yamlgraph.db"

# Default graph configuration
DEFAULT_GRAPH = GRAPHS_DIR / "yamlgraph.yaml"

# LLM Configuration
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096

# Default models per provider (override with {PROVIDER}_MODEL env var)
# API keys expected in .env:
#   ANTHROPIC_API_KEY, MISTRAL_API_KEY, OPENAI_API_KEY, REPLICATE_API_TOKEN, XAI_API_KEY
DEFAULT_MODELS = {
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
    "mistral": os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
    "replicate": os.getenv("REPLICATE_MODEL", "ibm-granite/granite-4.0-h-small"),
    "xai": os.getenv("XAI_MODEL", "grok-4-1-fast-reasoning"),
}

# Retry Configuration
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1.0"))  # seconds
RETRY_MAX_DELAY = float(os.getenv("LLM_RETRY_MAX_DELAY", "30.0"))  # seconds

# CLI Constraints - configurable via environment
MAX_TOPIC_LENGTH = int(os.getenv("YAMLGRAPH_MAX_TOPIC_LENGTH", "500"))
MAX_WORD_COUNT = int(os.getenv("YAMLGRAPH_MAX_WORD_COUNT", "5000"))
MIN_WORD_COUNT = int(os.getenv("YAMLGRAPH_MIN_WORD_COUNT", "50"))

# Valid styles - can be extended via environment (comma-separated)
_default_styles = "informative,casual,technical"
VALID_STYLES = tuple(os.getenv("YAMLGRAPH_VALID_STYLES", _default_styles).split(","))

# Input Sanitization Patterns
# Characters that could be used for prompt injection
DANGEROUS_PATTERNS = [
    "ignore previous",
    "ignore above",
    "disregard",
    "forget everything",
    "new instructions",
    "system:",
    "<|",  # Token delimiters
    "|>",
]
