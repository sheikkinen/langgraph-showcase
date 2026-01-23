#!/usr/bin/env python3
"""Async Executor Demo - Showcases async graph execution with interrupts.

Demonstrates:
- Async graph loading with load_and_compile_async()
- Async execution with run_graph_async()
- Interrupt handling and Command(resume=...) flow
- Real-time user interaction

Usage:
    # Interactive mode (real LLM + user input)
    python scripts/demo_async_executor.py --interactive

    # Verification mode (mock inputs for CI)
    python scripts/demo_async_executor.py --verify

    # Custom graph
    python scripts/demo_async_executor.py --graph graphs/my-graph.yaml
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.types import Command

from yamlgraph.executor_async import load_and_compile_async, run_graph_async


def print_banner(title: str) -> None:
    """Print a styled banner."""
    width = 50
    print("┌" + "─" * width + "┐")
    print(f"│ {title:<{width - 1}}│")
    print("├" + "─" * width + "┤")


def print_footer() -> None:
    """Print footer."""
    print("└" + "─" * 50 + "┘")


def get_interrupt_message(result: dict) -> str:
    """Extract message from interrupt payload."""
    if "__interrupt__" not in result:
        return ""
    interrupt = result["__interrupt__"][0]
    value = interrupt.value
    if isinstance(value, dict):
        return value.get("question") or value.get("prompt") or str(value)
    return str(value)


async def run_demo(
    graph_path: str,
    interactive: bool = False,
    mock_inputs: list[str] | None = None,
) -> dict:
    """Run the async executor demo.

    Args:
        graph_path: Path to YAML graph definition
        interactive: If True, prompt for real user input
        mock_inputs: List of mock inputs for verification mode

    Returns:
        Final state dict
    """
    mock_inputs = mock_inputs or ["TestUser", "Python"]
    mock_index = 0

    print_banner("🚀 Async Executor Demo")
    print(f"│ Graph: {graph_path:<41}│")
    print(f"│ Mode: {'interactive' if interactive else 'verify':<42}│")
    print("│" + " " * 50 + "│")

    # Load and compile
    print("│ Loading graph...                                │")
    try:
        app = await load_and_compile_async(graph_path)
        print("│ ✅ Compiled with memory checkpointer            │")
    except FileNotFoundError:
        print(f"│ ❌ Graph not found: {graph_path:<28}│")
        print_footer()
        return {"error": "Graph not found"}

    print("│" + " " * 50 + "│")

    # Config with thread_id for checkpointer
    config = {"configurable": {"thread_id": "demo-async-001"}}

    # Initial run
    print("│ Running graph async...                          │")
    result = await run_graph_async(app, {"input": "start"}, config)

    # Show welcome if present
    if welcome := result.get("welcome_message"):
        preview = welcome[:40] + "..." if len(welcome) > 40 else welcome
        print(f'│ 💬 Welcome: "{preview}"│')

    # Interrupt loop
    interrupt_count = 0
    while "__interrupt__" in result:
        interrupt_count += 1
        message = get_interrupt_message(result)
        print("│" + " " * 50 + "│")
        print(f"│ ⏸️  INTERRUPT #{interrupt_count}: {message:<30}│")

        # Get input
        if interactive:
            print("│" + " " * 50 + "│")
            user_input = input("│ > ")
        else:
            user_input = (
                mock_inputs[mock_index] if mock_index < len(mock_inputs) else "default"
            )
            mock_index += 1
            print(f"│ > {user_input:<47}│")

        # Resume
        print("│" + " " * 50 + "│")
        print("│ Resuming...                                     │")
        result = await run_graph_async(app, Command(resume=user_input), config)

    # Complete
    print("│" + " " * 50 + "│")
    print("│ ✅ Complete!                                     │")

    # Show final response
    response = result.get("greeting") or result.get("response") or result.get("output")
    if response:
        # Truncate for display
        preview = response[:38] + "..." if len(response) > 38 else response
        print(f'│ 📝 Response: "{preview}"│')

    print_footer()

    # Verification output
    if not interactive:
        print("\n📊 Final State:")
        for key, value in result.items():
            if not key.startswith("_") and value is not None:
                val_str = str(value)[:50]
                print(f"  {key}: {val_str}")

    return result


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Async Executor Demo")
    parser.add_argument(
        "--graph",
        default="graphs/interview-demo.yaml",
        help="Path to YAML graph definition",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode with real user input",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run in verification mode with mock inputs",
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=["Alice", "async programming"],
        help="Mock inputs for verification mode",
    )
    args = parser.parse_args()

    # Verify mode is default if neither specified
    interactive = args.interactive and not args.verify

    result = await run_demo(
        graph_path=args.graph,
        interactive=interactive,
        mock_inputs=args.inputs,
    )

    # Exit with error if graph failed
    if "error" in result:
        sys.exit(1)

    # Verify expected state in verify mode
    if args.verify:
        print("\n🔍 Verification:")
        checks = [
            ("user_name", result.get("user_name")),
            ("user_topic", result.get("user_topic")),
            ("greeting", result.get("greeting")),
        ]
        all_pass = True
        for field, value in checks:
            status = "✅" if value else "❌"
            print(f"  {status} {field}: {'present' if value else 'MISSING'}")
            if not value:
                all_pass = False

        if not all_pass:
            print("\n❌ Verification FAILED")
            sys.exit(1)
        print("\n✅ Verification PASSED")


if __name__ == "__main__":
    asyncio.run(main())
