"""Python nodes for the beautify example."""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

THEMES = {
    "dark": {
        "bg_primary": "#0f172a",
        "bg_secondary": "#1e293b",
        "bg_card": "rgba(30, 41, 59, 0.5)",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "border": "#334155",
        "gradient_start": "#1e3a5f",
        "gradient_end": "#0f172a",
    },
    "light": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8fafc",
        "bg_card": "rgba(248, 250, 252, 0.8)",
        "text_primary": "#0f172a",
        "text_secondary": "#64748b",
        "border": "#e2e8f0",
        "gradient_start": "#dbeafe",
        "gradient_end": "#ffffff",
    },
}


def load_graph(state: dict[str, Any]) -> dict[str, Any]:
    """Load the graph.yaml file as raw text."""
    graph_path = state.get("graph_path")
    if not graph_path:
        raise ValueError("graph_path is required")

    path = Path(graph_path)
    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {path}")

    logger.info(f"📂 Loading: {path}")
    graph_yaml = path.read_text()

    return {"graph_yaml": graph_yaml, "current_step": "load_graph"}


def render_html(state: dict[str, Any]) -> dict[str, Any]:
    """Render HTML template with analysis data."""
    logger.info("🎨 Rendering HTML...")

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template("infographic.html.j2")

    theme_name = state.get("theme") or "dark"
    theme = THEMES.get(theme_name, THEMES["dark"])

    # Convert Pydantic models to dicts if needed
    analysis = state.get("analysis") or {}
    if hasattr(analysis, "model_dump"):
        analysis = analysis.model_dump()

    mermaid = state.get("mermaid_code") or {}
    if hasattr(mermaid, "model_dump"):
        mermaid = mermaid.model_dump()

    title = state.get("title_override") or analysis.get("title", "Graph")

    html = template.render(
        title=title,
        theme=theme,
        theme_name=theme_name,
        analysis=analysis,
        mermaid_code=mermaid.get("diagram", ""),
    )

    logger.info(f"   Generated {len(html):,} bytes")
    return {"html_output": html, "current_step": "render_html"}


def save_output(state: dict[str, Any]) -> dict[str, Any]:
    """Save HTML to file."""
    html = state.get("html_output")
    if not html:
        raise ValueError("No HTML to save")

    output_path = state.get("output_path")
    if not output_path:
        analysis = state.get("analysis") or {}
        if hasattr(analysis, "model_dump"):
            analysis = analysis.model_dump()
        name = analysis.get("title", "graph").replace(" ", "-").lower()
        output_dir = Path(__file__).parent / "outputs"
        output_path = output_dir / f"{name}_infographic.html"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    logger.info(f"💾 Saved: {output_path}")
    print(f"\n✅ Saved: {output_path}")

    return {"output_file": str(output_path), "current_step": "save_output"}
