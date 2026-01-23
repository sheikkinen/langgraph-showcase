#!/usr/bin/env python3
"""Demo script for booking assistant with interrupt nodes.

This script demonstrates the interrupt feature for multi-turn booking:
1. Graph greets user and asks for appointment type
2. User provides name/request
3. Graph shows available slots
4. User selects slot
5. Graph confirms booking

Usage:
    python examples/booking/run_booking.py
"""

import uuid

from langgraph.types import Command

from yamlgraph.graph_loader import (
    compile_graph,
    get_checkpointer_for_graph,
    load_graph_config,
)


def run_booking():
    """Run the interactive booking demo."""
    print("\n" + "=" * 50)
    print("📅 YAMLGraph Booking Assistant Demo")
    print("=" * 50 + "\n")

    # Load and compile graph
    config = load_graph_config("examples/booking/graph.yaml")
    graph = compile_graph(config)

    # Get checkpointer (required for interrupts)
    checkpointer = get_checkpointer_for_graph(config)

    # Compile with checkpointer
    app = graph.compile(checkpointer=checkpointer)

    # Generate unique thread ID for this session
    thread_id = str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    print("Starting booking conversation...\n")

    # Initial invocation with service_name
    state = {"service_name": "Health Clinic"}
    result = app.invoke(state, run_config)

    # Loop through interrupts
    while True:
        # Check for interrupt
        interrupt_info = result.get("__interrupt__")

        if interrupt_info:
            # Extract the interrupt payload (message to user)
            payload = interrupt_info[0].value if interrupt_info else "Input needed:"
            print(f"\n💬 {payload}")

            # Get user input
            user_response = input("   Your response: ").strip()

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
    print("✨ Booking Complete!")
    print("-" * 50)

    # Show booking details
    booking_display = result.get("booking_display")
    confirmation = result.get("confirmation")

    if booking_display:
        print(f"\n{booking_display}")

    if confirmation:
        if hasattr(confirmation, "content"):
            print(f"\n{confirmation.content}")
        elif isinstance(confirmation, str):
            print(f"\n{confirmation}")

    print("\n" + "=" * 50)
    print("Demo complete!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    run_booking()
