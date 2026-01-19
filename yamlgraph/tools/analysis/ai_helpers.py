"""AI helper tools for implementation agent.

Tools that help AI assistants work more effectively:
- summarize_module: Compress module info for context windows
- diff_preview: Validate patches before suggesting
- find_similar_code: Find similar patterns to follow
"""

import ast
import difflib
from pathlib import Path


def summarize_module(file_path: str, max_length: int = 1500) -> dict:
    """Summarize a Python module for AI context compression.

    Extracts:
    - Module docstring
    - Class names with method signatures
    - Function signatures (no bodies)
    - Import summary

    Args:
        file_path: Path to the Python file
        max_length: Maximum summary length in characters

    Returns:
        dict with 'summary' string and 'original_lines' count
        or dict with 'error' key if failed
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        source = path.read_text()
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}

    original_lines = len(source.splitlines())
    parts = []

    # Module docstring
    docstring = ast.get_docstring(tree)
    if docstring:
        # Truncate long docstrings
        if len(docstring) > 200:
            docstring = docstring[:200] + "..."
        parts.append(f'"""{docstring}"""')

    # Imports (summarized)
    imports = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(f"{node.module or ''}")

    if imports:
        # Group and summarize
        unique_imports = sorted(set(imports))[:10]  # Top 10
        parts.append(f"# Imports: {', '.join(unique_imports)}")

    # Classes and functions
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node) or ""
            if len(class_doc) > 100:
                class_doc = class_doc[:100] + "..."

            # Get bases
            bases = [_get_name(b) for b in node.bases]
            bases_str = f"({', '.join(bases)})" if bases else ""

            parts.append(f"\nclass {node.name}{bases_str}:")
            if class_doc:
                parts.append(f'    """{class_doc}"""')

            # Method signatures only
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    sig = _get_signature(item)
                    parts.append(f"    {sig}")

        elif isinstance(node, ast.FunctionDef):
            func_doc = ast.get_docstring(node) or ""
            if len(func_doc) > 100:
                func_doc = func_doc[:100] + "..."

            sig = _get_signature(node)
            parts.append(f"\n{sig}")
            if func_doc:
                parts.append(f'    """{func_doc}"""')

    summary = "\n".join(parts)

    # Truncate if needed
    if len(summary) > max_length:
        summary = summary[: max_length - 3] + "..."

    return {"summary": summary, "original_lines": original_lines}


def _get_name(node: ast.expr) -> str:
    """Get name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    return "?"


def _get_signature(func: ast.FunctionDef) -> str:
    """Extract function signature as string."""
    args = []
    for arg in func.args.args:
        arg_str = arg.arg
        if arg.annotation:
            arg_str += f": {_get_annotation(arg.annotation)}"
        args.append(arg_str)

    # Add *args, **kwargs
    if func.args.vararg:
        args.append(f"*{func.args.vararg.arg}")
    if func.args.kwarg:
        args.append(f"**{func.args.kwarg.arg}")

    args_str = ", ".join(args)

    # Return type
    returns = ""
    if func.returns:
        returns = f" -> {_get_annotation(func.returns)}"

    # Decorators
    decorators = ""
    for dec in func.decorator_list:
        dec_name = _get_name(dec) if isinstance(dec, (ast.Name, ast.Attribute)) else "?"
        decorators += f"@{dec_name}\n    "

    return f"{decorators}def {func.name}({args_str}){returns}: ..."


def _get_annotation(node: ast.expr) -> str:
    """Get type annotation as string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    elif isinstance(node, ast.Subscript):
        return f"{_get_name(node.value)}[{_get_annotation(node.slice)}]"
    elif isinstance(node, ast.Tuple):
        return ", ".join(_get_annotation(e) for e in node.elts)
    return "..."


def diff_preview(
    file_path: str,
    line: int,
    action: str,
    new_code: str,
    validate_syntax: bool = False,
) -> dict:
    """Preview what a patch would look like applied.

    Args:
        file_path: Path to the file
        line: Line number (1-indexed)
        action: ADD, MODIFY, or DELETE
        new_code: New code to add/replace
        validate_syntax: Whether to check syntax of result

    Returns:
        dict with 'diff' string showing the change
        or dict with 'error' key if failed
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    lines = path.read_text().splitlines(keepends=True)

    if line < 1 or line > len(lines) + 1:
        return {"error": f"Invalid line {line}, file has {len(lines)} lines"}

    # Create modified version
    new_lines = lines.copy()
    action = action.upper()

    if action == "ADD":
        # Insert after the specified line
        insert_pos = min(line, len(new_lines))
        new_lines.insert(insert_pos, new_code + "\n")
    elif action == "MODIFY":
        if line > len(lines):
            return {"error": f"Cannot modify line {line}, file has {len(lines)} lines"}
        new_lines[line - 1] = new_code + "\n"
    elif action == "DELETE":
        if line > len(lines):
            return {"error": f"Cannot delete line {line}, file has {len(lines)} lines"}
        del new_lines[line - 1]
    else:
        return {"error": f"Invalid action: {action}. Use ADD, MODIFY, or DELETE"}

    # Generate unified diff
    diff = difflib.unified_diff(
        lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    diff_str = "\n".join(diff)

    result = {"diff": diff_str}

    # Optionally validate syntax
    if validate_syntax:
        try:
            ast.parse("".join(new_lines))
            result["syntax_valid"] = True
        except SyntaxError:
            result["syntax_valid"] = False

    return result


def find_similar_code(
    file_path: str,
    symbol_name: str,
    project_path: str,
    max_results: int = 5,
) -> dict:
    """Find code similar to the specified function/class.

    Similarity based on:
    - Parameter patterns
    - Return type
    - Decorator usage
    - Error handling patterns

    Args:
        file_path: Path to file containing the symbol
        symbol_name: Name of function/class to find similar to
        project_path: Root path to search for similar code
        max_results: Maximum number of results

    Returns:
        dict with 'similar' list of matches
        or dict with 'error' key if failed
    """
    source_path = Path(file_path)
    if not source_path.exists():
        return {"error": f"File not found: {file_path}"}

    project = Path(project_path)
    if not project.exists():
        return {"error": f"Project path not found: {project_path}"}

    # Parse source and find target symbol
    try:
        source = source_path.read_text()
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error in {file_path}: {e}"}

    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == symbol_name:
            target = node
            break
        elif isinstance(node, ast.ClassDef) and node.name == symbol_name:
            target = node
            break

    if target is None:
        return {"error": f"Symbol '{symbol_name}' not found in {file_path}"}

    # Extract target characteristics
    target_traits = _extract_traits(target)

    # Search for similar code
    similar = []

    for py_file in project.rglob("*.py"):
        if py_file == source_path:
            continue

        try:
            file_source = py_file.read_text()
            file_tree = ast.parse(file_source)
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(file_tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if node.name == symbol_name:
                    continue  # Skip exact matches

                node_traits = _extract_traits(node)
                score, reasons = _compare_traits(target_traits, node_traits)

                if score > 0.3:  # Threshold
                    # Get code snippet
                    lines = file_source.splitlines()
                    start = node.lineno - 1
                    end = min(start + 5, len(lines))
                    snippet = "\n".join(lines[start:end])

                    similar.append(
                        {
                            "file": str(py_file),
                            "name": node.name,
                            "line": node.lineno,
                            "score": round(score, 2),
                            "reason": ", ".join(reasons),
                            "snippet": snippet,
                        }
                    )

    # Sort by score and limit
    similar.sort(key=lambda x: x["score"], reverse=True)
    similar = similar[:max_results]

    return {"similar": similar}


def _extract_traits(node: ast.FunctionDef | ast.ClassDef) -> dict:
    """Extract characteristics for comparison."""
    traits = {
        "type": type(node).__name__,
        "param_count": 0,
        "has_return_type": False,
        "decorators": [],
        "has_try_except": False,
        "returns_dict": False,
        "has_docstring": False,
    }

    if isinstance(node, ast.FunctionDef):
        traits["param_count"] = len(node.args.args)
        traits["has_return_type"] = node.returns is not None
        traits["decorators"] = [
            _get_name(d)
            for d in node.decorator_list
            if isinstance(d, (ast.Name, ast.Attribute))
        ]
        traits["has_docstring"] = ast.get_docstring(node) is not None

        # Check for try/except and dict return
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                traits["has_try_except"] = True
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                traits["returns_dict"] = True

    elif isinstance(node, ast.ClassDef):
        traits["has_docstring"] = ast.get_docstring(node) is not None
        traits["decorators"] = [
            _get_name(d)
            for d in node.decorator_list
            if isinstance(d, (ast.Name, ast.Attribute))
        ]
        # Count methods
        traits["param_count"] = sum(
            1 for n in node.body if isinstance(n, ast.FunctionDef)
        )

    return traits


def _compare_traits(a: dict, b: dict) -> tuple[float, list[str]]:
    """Compare two trait dicts and return similarity score + reasons."""
    score = 0.0
    reasons = []

    # Same type (function vs class)
    if a["type"] == b["type"]:
        score += 0.2
        reasons.append(f"same type ({a['type']})")

    # Similar param count
    if a["type"] == "FunctionDef" and b["type"] == "FunctionDef":
        if abs(a["param_count"] - b["param_count"]) <= 1:
            score += 0.2
            reasons.append("similar params")

    # Both have return types
    if a.get("has_return_type") and b.get("has_return_type"):
        score += 0.1
        reasons.append("typed return")

    # Both have try/except
    if a.get("has_try_except") and b.get("has_try_except"):
        score += 0.2
        reasons.append("error handling")

    # Both return dict
    if a.get("returns_dict") and b.get("returns_dict"):
        score += 0.2
        reasons.append("returns dict")

    # Shared decorators
    shared_decorators = set(a["decorators"]) & set(b["decorators"])
    if shared_decorators:
        score += 0.1
        reasons.append(f"decorators: {shared_decorators}")

    # Both have docstrings
    if a.get("has_docstring") and b.get("has_docstring"):
        score += 0.1
        reasons.append("documented")

    return score, reasons
