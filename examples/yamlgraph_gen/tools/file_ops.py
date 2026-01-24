"""File operations for yamlgraph-generator."""

from pathlib import Path


def read_file(path: str) -> str:
    """Read file contents."""
    return Path(path).read_text()


def write_file(path: str, content: str) -> dict:
    """Write content to file, creating directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return {"path": str(p.resolve()), "bytes": len(content)}


def list_files(directory: str, pattern: str = "*") -> list[str]:
    """List files matching pattern in directory."""
    return [str(p) for p in Path(directory).glob(pattern)]


def ensure_directory(directory: str) -> str:
    """Ensure directory exists."""
    p = Path(directory)
    p.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())


def write_generated_files(
    output_dir: str,
    graph_content: str,
    prompts: list[dict],
) -> dict:
    """Write all generated files to output directory.

    Args:
        output_dir: Target directory
        graph_content: The graph.yaml content
        prompts: List of {filename, content} dicts

    Returns:
        dict with files_written list and status
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    files_written = []

    # Sanitize graph content - fix common LLM mistakes
    # Fix double .yaml extensions: .yaml.yaml -> .yaml
    sanitized_graph = graph_content.replace(".yaml.yaml", ".yaml")

    # Write graph.yaml
    graph_path = output_path / "graph.yaml"
    graph_path.write_text(sanitized_graph)
    files_written.append(str(graph_path))

    # Write prompts
    prompts_dir = output_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)

    for prompt in prompts:
        filename = prompt.get("filename", "")
        content = prompt.get("content", "")
        if filename and content:
            # Handle both "prompts/foo.yaml" and "foo.yaml"
            if filename.startswith("prompts/"):
                filename = filename[8:]
            # Fix double .yaml extensions
            filename = filename.replace(".yaml.yaml", ".yaml")
            prompt_path = prompts_dir / filename
            prompt_path.write_text(content)
            files_written.append(str(prompt_path))

    return {
        "files_written": files_written,
        "status": "success",
    }


def write_generated_files_node(state: dict) -> dict:
    """Yamlgraph node wrapper for write_generated_files.

    Extracts output_dir, assembled_graph, and generated_prompts from state.
    """
    output_dir = state.get("output_dir", "")
    assembled = state.get("assembled_graph", "")
    prompts = state.get("generated_prompts") or []

    # Handle case where assembled_graph is a Pydantic model (AssembledGraph)
    if hasattr(assembled, "graph_yaml"):
        graph_content = assembled.graph_yaml
    elif isinstance(assembled, dict):
        graph_content = assembled.get("graph_yaml", str(assembled))
    else:
        graph_content = str(assembled) if assembled else ""

    # Handle case where prompts is a Pydantic model (GeneratedPrompts) or tuple
    if hasattr(prompts, "prompts"):
        prompts = prompts.prompts
    if isinstance(prompts, tuple):
        prompts = list(prompts)

    # Convert Pydantic models to dicts if needed
    if prompts and hasattr(prompts[0], "model_dump"):
        prompts = [p.model_dump() for p in prompts]

    return write_generated_files(output_dir, graph_content, prompts)
