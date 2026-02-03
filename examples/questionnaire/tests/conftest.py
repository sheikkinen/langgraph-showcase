"""Pytest configuration for questionnaire tests."""

import sys
from pathlib import Path

# Add tools directory to path for imports
questionnaire_dir = Path(__file__).parent.parent
sys.path.insert(0, str(questionnaire_dir))
