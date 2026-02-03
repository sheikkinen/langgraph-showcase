#!/usr/bin/env python3
"""Demo script to run questionnaire with mock inputs."""

import asyncio
from pathlib import Path

from langgraph.types import Command

from yamlgraph.graph_loader import (
    compile_graph,
    get_checkpointer_for_graph,
    load_graph_config,
)


def get_interrupt_message(result: dict) -> str:
    """Extract message from interrupt."""
    interrupt = result.get("__interrupt__", ())
    if interrupt and len(interrupt) > 0:
        interrupt_obj = interrupt[0]
        if hasattr(interrupt_obj, "value"):
            value = interrupt_obj.value
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                return value.get("message", value.get("question", str(value)))
    return result.get("response", "?")


async def main():
    """Run questionnaire with mock inputs."""
    graph_path = Path(__file__).parent / "graph.yaml"

    # Mock inputs for the conversation
    mock_inputs = [
        "I want to add URL support for loading remote graph files. The title would be 'URL Graph Loading'. Priority is high because it's blocking CI/CD integration. The summary is: Allow loading graphs from HTTP URLs. The problem is that users can only load local files. The solution is to add URL detection and HTTP fetching in graph_loader.",
        "yes, that looks correct",  # confirm recap
    ]
    mock_index = 0

    # Load and compile
    print("📋 Loading questionnaire graph...")
    config = load_graph_config(str(graph_path))
    graph = compile_graph(config)
    checkpointer = get_checkpointer_for_graph(config)
    app = graph.compile(checkpointer=checkpointer)

    # Config with thread
    run_config = {"configurable": {"thread_id": "demo-run"}}

    # Initial state with data_files
    initial_state = {**config.data, "thread_id": "demo-run"}

    print("🚀 Starting conversation...\n")
    result = await app.ainvoke(initial_state, config=run_config)

    # Interrupt loop
    while "__interrupt__" in result:
        message = get_interrupt_message(result)
        # Handle Pydantic models vs strings
        display = str(message.message) if hasattr(message, "message") else str(message)
        if len(display) > 200:
            display = display[:200] + "..."
        print(f"💬 Assistant: {display}")

        if mock_index < len(mock_inputs):
            user_input = mock_inputs[mock_index]
            mock_index += 1
        else:
            user_input = "yes"  # Default confirm

        print(f"👤 User: {user_input}\n")
        result = await app.ainvoke(Command(resume=user_input), config=run_config)

    # Done
    print("\n" + "=" * 60)
    print("✅ Complete!")
    print("=" * 60)

    # Debug: show recap_action
    if result.get("recap_action"):
        print(f"📋 recap_action: {result['recap_action']}")

    if result.get("output_path"):
        print(f"📄 Saved to: {result['output_path']}")

    if result.get("response"):
        response = result["response"]
        display = (
            str(response.message) if hasattr(response, "message") else str(response)
        )
        if len(display) > 300:
            display = display[:300] + "..."
        print(f"\n💬 Final: {display}")


if __name__ == "__main__":
    asyncio.run(main())
