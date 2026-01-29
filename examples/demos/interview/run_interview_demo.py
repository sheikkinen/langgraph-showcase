#!/usr/bin/env python3
"""Demo script for human-in-the-loop interrupt nodes.

This script demonstrates the interrupt feature:
1. Graph pauses at interrupt nodes
2. User provides input via terminal
3. Graph resumes with user's response

Usage:
    cd examples/demos/interview
    python run_interview_demo.py
"""

import uuid
from pathlib import Path

from dotenv import load_dotenv

# Load environment from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from langgraph.types import Command  # noqa: E402

from yamlgraph.graph_loader import (  # noqa: E402
    compile_graph,
    get_checkpointer_for_graph,
    load_graph_config,
)

# Graph path relative to this script
GRAPH_PATH = Path(__file__).parent / "graph.yaml"


def run_interview():
    """Run the interactive interview demo."""
    print("\n" + "=" * 50)
    print("🎤 YAMLGraph Interview Demo - Human-in-the-Loop")
    print("=" * 50 + "\n")

    # Load and compile graph
    config = load_graph_config(str(GRAPH_PATH))
    graph = compile_graph(config)

    # Get checkpointer (required for interrupts)
    checkpointer = get_checkpointer_for_graph(config)

    # Compile with checkpointer
    app = graph.compile(checkpointer=checkpointer)

    # Generate unique thread ID for this session
    thread_id = str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    print("Starting interview...\n")

    # Initial invocation - will hit first interrupt
    state = {}
    result = app.invoke(state, run_config)

    # Loop through interrupts
    while True:
        # Check for interrupt
        interrupt_info = result.get("__interrupt__")

        if interrupt_info:
            # Extract the interrupt payload (question)
            payload = interrupt_info[0].value if interrupt_info else "Input needed:"
            print(f"\n💬 {payload}")

            # Get user input
            user_response = input("   Your answer: ").strip()

            if user_response.lower() in ("quit", "exit", "q"):
                print("\n👋 Goodbye!")
                return

            # Resume with user's response
            result = app.invoke(Command(resume=user_response), run_config)
        else:
            # No more interrupts - we're done
            break

    # Display final result
    print("\n" + "-" * 50)
    print("✨ Final Response:")
    print("-" * 50)

    greeting = result.get("greeting")
    if greeting:
        # Handle both string and Pydantic model responses
        if hasattr(greeting, "content"):
            print(greeting.content)
        elif isinstance(greeting, str):
            print(greeting)
        else:
            print(greeting)

    print("\n" + "=" * 50)
    print("Demo complete!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    run_interview()
