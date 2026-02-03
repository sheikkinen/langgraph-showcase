#!/usr/bin/env python3
"""CLI runner for the beautify example.

Usage:
    python -m examples.beautify.run <graph_path> [--theme dark|light] [--open]
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from yamlgraph.graph_loader import compile_graph, load_graph_config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transform graph.yaml into HTML infographic"
    )
    parser.add_argument("graph_path", help="Path to graph.yaml")
    parser.add_argument("--output", "-o", help="Output HTML path")
    parser.add_argument("--theme", "-t", choices=["dark", "light"], default="dark")
    parser.add_argument("--title", help="Override title")
    parser.add_argument("--open", action="store_true", help="Open in browser")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    graph_path = Path(args.graph_path)
    if not graph_path.exists():
        logger.error(f"❌ Not found: {graph_path}")
        return 1

    logger.info(f"\n🎨 Beautifying: {graph_path.name}\n")

    try:
        beautify_path = Path(__file__).parent / "graph.yaml"
        config = load_graph_config(str(beautify_path))
        graph = compile_graph(config)
        app = graph.compile()

        state = {"graph_path": str(graph_path.resolve()), "theme": args.theme}
        if args.output:
            state["output_path"] = args.output
        if args.title:
            state["title_override"] = args.title

        result = app.invoke(state)

        if args.open and result.get("output_file"):
            subprocess.run(["open", result["output_file"]], check=False)

        return 0

    except Exception as e:
        logger.error(f"❌ {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
