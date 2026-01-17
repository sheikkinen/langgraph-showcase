"""Centralized configuration for the yamlgraph package.

Provides paths, settings, and environment configuration
used across all modules.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Package root (yamlgraph/ directory)
PACKAGE_ROOT = Path(__file__).parent

# Project root (parent of yamlgraph/)
PROJECT_ROOT = PACKAGE_ROOT.parent

# Load environment variables from project root
load_dotenv(PROJECT_ROOT / ".env")

# Directory paths
PROMPTS_DIR = PROJECT_ROOT / "prompts"
GRAPHS_DIR = PROJECT_ROOT / "graphs"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATABASE_PATH = OUTPUTS_DIR / "yamlgraph.db"

# Default graph configuration
DEFAULT_GRAPH = GRAPHS_DIR / "yamlgraph.yaml"

# LLM Configuration
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4096

# Default models per provider (override with {PROVIDER}_MODEL env var)
DEFAULT_MODELS = {
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5"),
    "mistral": os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
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
