#!/usr/bin/env python3
"""TDD Test: Subgraph Checkpointer Inheritance (FR-006)

This script validates subgraph + interrupt in THREE scenarios:

SCENARIO A: Child WITHOUT checkpointer config (memory parent)
    - Expected: ✅ PASS (runtime checkpointer propagation works)
    - Graph: interrupt-parent.yaml → interrupt-child.yaml

SCENARIO B: Child WITH its own checkpointer config (memory parent)
    - Expected: ✅ PASS with memory (runtime propagation works)
    - Graph: interrupt-parent-with-checkpointer-child.yaml
             → interrupt-child-with-checkpointer.yaml

SCENARIO C: Redis checkpointer (reproduces the actual FR-006 bug)
    - Expected: ❌ FAIL before fix, ✅ PASS after fix
    - Graph: interrupt-parent-redis.yaml
             → interrupt-child-with-checkpointer-redis.yaml
    - Bug: Subgraph restarts from init instead of resuming

Usage:
    python scripts/test_subgraph_interrupt.py          # Run A, B only (no redis)
    python scripts/test_subgraph_interrupt.py --a      # Scenario A only
    python scripts/test_subgraph_interrupt.py --b      # Scenario B only
    python scripts/test_subgraph_interrupt.py --c      # Scenario C only (redis bug)
    python scripts/test_subgraph_interrupt.py --all    # Run all including redis

See: feature-requests/006-subgraph-checkpointer-inheritance.md
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.types import Command

from yamlgraph.graph_loader import (
    compile_graph,
    get_checkpointer_for_graph,
    load_graph_config,
)

# Test configurations
SCENARIO_A = {
    "name": "A: Child WITHOUT checkpointer (memory)",
    "graph_path": "graphs/interrupt-parent.yaml",
    "thread_id": "test-fr006-scenario-a",
    "description": "Child has no checkpointer config - relies on runtime propagation",
}

SCENARIO_B = {
    "name": "B: Child WITH checkpointer (memory)",
    "graph_path": "graphs/interrupt-parent-with-checkpointer-child.yaml",
    "thread_id": "test-fr006-scenario-b",
    "description": "Child HAS its own checkpointer config - memory works via runtime",
}

SCENARIO_C = {
    "name": "C: Redis checkpointer (FR-006 bug)",
    "graph_path": "graphs/interrupt-parent-redis.yaml",
    "thread_id": "test-fr006-scenario-c",
    "description": "Redis checkpointer - REPRODUCES the actual bug!",
}


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title: str) -> None:
    """Print a subheader."""
    print("\n" + "-" * 70)
    print(f"  {title}")
    print("-" * 70)


def print_step(step: int, description: str) -> None:
    """Print a step marker."""
    print(f"\n📍 Step {step}: {description}")


def print_result(key: str, value: str, max_len: int = 80) -> None:
    """Print a result value, truncated if needed."""
    val_str = str(value)
    if len(val_str) > max_len:
        val_str = val_str[:max_len] + "..."
    print(f"   {key}: {val_str}")


def run_scenario(scenario: dict) -> tuple[bool, str]:
    """Run a single test scenario.

    Returns:
        Tuple of (success: bool, error_message: str or None)
    """
    print_subheader(f"Scenario {scenario['name']}")
    print(f"   {scenario['description']}")

    graph_path = scenario["graph_path"]
    thread_id = scenario["thread_id"]

    # =========================================================================
    # SETUP
    # =========================================================================
    print_step(0, "Load and compile graph")

    try:
        config = load_graph_config(graph_path)
        print_result("Graph", config.name)
        print_result("Parent checkpointer", str(config.checkpointer))
    except FileNotFoundError:
        return False, f"Graph not found: {graph_path}"

    # Check if subgraph has its own checkpointer
    for node_name, node_config in config.nodes.items():
        if node_config.get("type") == "subgraph":
            child_graph_path = Path(graph_path).parent / node_config["graph"]
            try:
                child_config = load_graph_config(child_graph_path)
                print_result(f"Child graph ({node_name})", child_config.name)
                print_result("Child checkpointer", str(child_config.checkpointer))
            except FileNotFoundError:
                pass

    graph = compile_graph(config)
    checkpointer = get_checkpointer_for_graph(config)
    app = graph.compile(checkpointer=checkpointer)

    run_config = {"configurable": {"thread_id": thread_id}}
    print_result("Thread ID", thread_id)

    # =========================================================================
    # INVOKE 1: Start - Should hit interrupt in subgraph child
    # =========================================================================
    print_step(1, "Invoke with initial input (expect interrupt)")

    try:
        result = app.invoke({"user_input": "hello from parent"}, run_config)
    except ValueError as e:
        if "No checkpointer set" in str(e):
            error_msg = f"BUG: Subgraph has no checkpointer - {e}"
            print(f"\n❌ {error_msg}")
            print("\n   This is the FR-006 bug. The subgraph was compiled without")
            print("   inheriting the parent's checkpointer.")
            return False, error_msg
        raise

    # Check for interrupt
    interrupt_info = result.get("__interrupt__")
    if interrupt_info:
        print("   ✅ Interrupt received from subgraph")
        payload = interrupt_info[0].value if interrupt_info else None
        print_result("Interrupt message", payload)
    else:
        child_phase = result.get("child_phase")
        child_data = result.get("child_data")
        print_result("child_phase", child_phase)
        print_result("child_data", child_data)

        if child_phase == "processing":
            print("   ✅ Subgraph interrupted, partial state mapped to parent")
        else:
            return False, "Expected interrupt or partial state, got neither"

    # =========================================================================
    # INVOKE 2: Resume - Subgraph should continue from interrupt point
    # =========================================================================
    print_step(2, "Resume with user answer (subgraph should NOT restart)")

    try:
        result = app.invoke(Command(resume="my answer"), run_config)
    except ValueError as e:
        if "No checkpointer set" in str(e):
            error_msg = f"BUG on resume: {e}"
            print(f"\n❌ {error_msg}")
            return False, error_msg
        raise

    child_phase = result.get("child_phase")
    final_result = result.get("final_result")

    print_result("child_phase", child_phase)
    print_result("final_result", final_result)

    if child_phase == "processing":
        error_msg = "Subgraph restarted from init instead of resuming!"
        print(f"   ❌ FAIL: {error_msg}")
        return False, error_msg
    elif final_result:
        print("   ✅ Subgraph completed successfully (did not restart)")
    else:
        print("   ⚠️  Unexpected state (but may be OK)")

    # =========================================================================
    # FINAL ASSERTIONS
    # =========================================================================
    print_step(3, "Verify final state")

    if final_result:
        print("   ✅ final_result populated from subgraph")
    else:
        print("   ⚠️  final_result not set")

    if not result.get("__interrupt__"):
        print("   ✅ No pending interrupts (graph completed)")
    else:
        return False, "Unexpected interrupt remaining"

    return True, None


def main():
    """Run tests and report results."""
    print("\n" + "🧪" * 35)
    print("  TDD Test: Subgraph + Interrupt Checkpointer Inheritance (FR-006)")
    print("🧪" * 35)

    # Parse args
    args = sys.argv[1:]
    run_a = "--a" in args or (not args) or ("--all" in args)
    run_b = "--b" in args or (not args) or ("--all" in args)
    run_c = "--c" in args or ("--all" in args)  # Redis only with --c or --all

    results = {}

    if run_a:
        print_header("SCENARIO A: Child WITHOUT checkpointer config (memory)")
        success, error = run_scenario(SCENARIO_A)
        results["A"] = (success, error)

    if run_b:
        print_header("SCENARIO B: Child WITH checkpointer config (memory)")
        success, error = run_scenario(SCENARIO_B)
        results["B"] = (success, error)

    if run_c:
        print_header("SCENARIO C: Redis checkpointer (FR-006 BUG)")
        print("\n⚠️  This scenario reproduces the actual FR-006 bug!")
        print("   Requires: Local Redis running on localhost:6379")
        success, error = run_scenario(SCENARIO_C)
        results["C"] = (success, error)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_header("TEST SUMMARY")

    all_passed = True
    for scenario, (success, error) in results.items():
        if success:
            print(f"\n✅ Scenario {scenario}: PASS")
        else:
            print(f"\n❌ Scenario {scenario}: FAIL")
            print(f"   Error: {error}")
            all_passed = False

    print("\n" + "-" * 70)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n   FR-006 behavior:")
        if "A" in results:
            print(
                "   - Scenario A: Child without checkpointer works (runtime propagation)"
            )
        if "B" in results:
            print(
                "   - Scenario B: Child with memory checkpointer works (runtime propagation)"
            )
        if "C" in results:
            print("   - Scenario C: Redis checkpointer works (fix applied!)")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("\n   Expected behavior:")
        print("   - Scenario A: PASS (memory, no child checkpointer)")
        print("   - Scenario B: PASS (memory, child has checkpointer)")
        print("   - Scenario C: FAIL before fix (redis, child has checkpointer)")
        print("\n   After FR-006 fix:")
        print("   - All scenarios should PASS")
        print("\n   To fix, update node_compiler.py to pass parent checkpointer:")
        print("   - compile_nodes(..., checkpointer=checkpointer)")
        print("   - compile_node(..., checkpointer=checkpointer)")
        print("   - create_subgraph_node(..., parent_checkpointer=checkpointer)")
        sys.exit(1)


if __name__ == "__main__":
    main()
