"""Code analysis tools for impl-agent.

This subpackage provides static and semantic analysis capabilities:
- AST-based structure extraction
- Code context reading and search
- Code navigation and module discovery
- Jedi-based cross-file reference tracking (optional)
"""

from yamlgraph.tools.analysis.ai_helpers import (
    diff_preview,
    find_similar_code,
    summarize_module,
)
from yamlgraph.tools.analysis.ast_analysis import get_module_structure
from yamlgraph.tools.analysis.code_context import (
    find_related_tests,
    read_lines,
    search_codebase,
    search_in_file,
)
from yamlgraph.tools.analysis.code_nav import list_package_modules
from yamlgraph.tools.analysis.dependency_tools import get_dependents, get_imports
from yamlgraph.tools.analysis.example_tools import find_error_handling, find_example
from yamlgraph.tools.analysis.git_tools import git_blame, git_log
from yamlgraph.tools.analysis.jedi_analysis import (
    JEDI_AVAILABLE,
    find_references,
    get_callees,
    get_callers,
)
from yamlgraph.tools.analysis.syntax_tools import syntax_check
from yamlgraph.tools.analysis.template_tools import (
    extract_class_template,
    extract_function_template,
    extract_test_template,
)

__all__ = [
    # AST analysis
    "get_module_structure",
    # Code context
    "read_lines",
    "search_in_file",
    "search_codebase",
    "find_related_tests",
    # Code navigation
    "list_package_modules",
    # Jedi analysis
    "JEDI_AVAILABLE",
    "find_references",
    "get_callers",
    "get_callees",
    # Git analysis
    "git_blame",
    "git_log",
    # Syntax validation
    "syntax_check",
    # Dependency analysis
    "get_imports",
    "get_dependents",
    # AI helpers
    "summarize_module",
    "diff_preview",
    "find_similar_code",
    # Template extraction
    "extract_function_template",
    "extract_class_template",
    "extract_test_template",
    # Example discovery
    "find_example",
    "find_error_handling",
]
