#!/usr/bin/env python3
"""End-to-end test for interrupt node demo.

This script tests the full interrupt/resume flow:
1. Graph pauses at first interrupt (ask_name)
2. Resume with "Alice"
3. Graph pauses at second interrupt (ask_topic)
4. Resume with "Python"
5. LLM generates personalized greeting

Can run as:
- Automated test: cd examples/demos/interview && python demo_interview_e2e.py
- Interactive mode: python demo_interview_e2e.py --interactive
"""

import argparse
import sys
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


def run_demo(interactive: bool = False) -> dict:
    """Run the interview demo.

    Args:
        interactive: If True, prompt for user input. Otherwise use test values.

    Returns:
        Final state dict with greeting
    """
    print("\n" + "=" * 50)
    print("🎤 YAMLGraph Interview Demo - Human-in-the-Loop")
    print("=" * 50 + "\n")

    # Load and compile graph
    config = load_graph_config(str(GRAPH_PATH))
    graph = compile_graph(config)
    checkpointer = get_checkpointer_for_graph(config)
    app = graph.compile(checkpointer=checkpointer)

    # Generate unique thread ID
    thread_id = str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    print(f"Thread ID: {thread_id[:8]}...")
    print()

    # First invoke - LLM generates welcome, then hits first interrupt
    result = app.invoke({}, run_config)
    interrupt = result.get("__interrupt__")

    if not interrupt:
        raise RuntimeError("Expected interrupt at ask_name node")

    # Show the LLM-generated welcome message
    welcome = result.get("welcome_message", "")
    if welcome:
        print(f"🤖 {welcome}")
        print()

    question1 = interrupt[0].value
    print(f"💬 {question1}")

    if interactive:
        answer1 = input("   Your answer: ").strip()
    else:
        answer1 = "Alice"
        print(f"   Your answer: {answer1}")

    print()

    # Resume with first answer - hits second interrupt
    result = app.invoke(Command(resume=answer1), run_config)
    interrupt = result.get("__interrupt__")

    if not interrupt:
        raise RuntimeError("Expected interrupt at ask_topic node")

    question2 = interrupt[0].value
    print(f"💬 {question2}")

    if interactive:
        answer2 = input("   Your answer: ").strip()
    else:
        answer2 = "Python"
        print(f"   Your answer: {answer2}")

    print()

    # Resume with second answer - completes graph
    result = app.invoke(Command(resume=answer2), run_config)

    # Verify no more interrupts
    if result.get("__interrupt__"):
        raise RuntimeError("Unexpected interrupt after ask_topic")

    # Display result
    print("-" * 50)
    print("✨ Final Response:")
    print("-" * 50)

    greeting = result.get("greeting", "")
    if greeting:
        print(greeting)
    else:
        print("(No greeting generated)")

    print()
    print("=" * 50)
    print("Demo complete!")
    print("=" * 50 + "\n")

    return result


def verify_result(result: dict) -> bool:
    """Verify the demo produced expected output.

    Args:
        result: Final state dict

    Returns:
        True if verification passed
    """
    errors = []

    # Check state contains expected keys
    if "user_name" not in result:
        errors.append("Missing 'user_name' in state")
    elif result["user_name"] != "Alice":
        errors.append(f"Expected user_name='Alice', got '{result['user_name']}'")

    if "user_topic" not in result:
        errors.append("Missing 'user_topic' in state")
    elif result["user_topic"] != "Python":
        errors.append(f"Expected user_topic='Python', got '{result['user_topic']}'")

    if "greeting" not in result:
        errors.append("Missing 'greeting' in state")
    elif not result["greeting"]:
        errors.append("Greeting is empty")

    # Check greeting mentions the user and topic
    greeting = str(result.get("greeting", "")).lower()
    if "alice" not in greeting:
        errors.append("Greeting doesn't mention 'Alice'")
    if "python" not in greeting:
        errors.append("Greeting doesn't mention 'Python'")

    if errors:
        print("\n❌ Verification FAILED:")
        for error in errors:
            print(f"   - {error}")
        return False

    print("\n✅ Verification PASSED:")
    print("   - State contains user_name='Alice'")
    print("   - State contains user_topic='Python'")
    print("   - Greeting mentions both user and topic")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Interview demo E2E test")
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run in interactive mode (prompt for input)",
    )
    parser.add_argument(
        "--verify",
        "-v",
        action="store_true",
        help="Verify output after demo",
    )
    args = parser.parse_args()

    try:
        result = run_demo(interactive=args.interactive)

        if args.verify or not args.interactive:
            success = verify_result(result)
            sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
