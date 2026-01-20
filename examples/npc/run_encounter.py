#!/usr/bin/env python3
"""Run a multi-turn NPC encounter with human-in-the-loop.

This script demonstrates the interrupt feature for turn-by-turn gameplay.
The DM provides input each turn, and the NPC responds.

Usage:
    python examples/npc/run_encounter.py

    # With pre-created NPC data
    python examples/npc/run_encounter.py --npc-file outputs/npc.json
"""

import argparse
import json
import uuid
from pathlib import Path

from langgraph.types import Command

from yamlgraph.graph_loader import (
    compile_graph,
    get_checkpointer_for_graph,
    load_graph_config,
)


# ANSI colors
class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    RESET = "\033[0m"


def load_npc_data(npc_file: str | None) -> dict:
    """Load NPC data from file or use defaults."""
    if npc_file and Path(npc_file).exists():
        with open(npc_file) as f:
            data = json.load(f)
        print(f"{C.GREEN}✓ Loaded NPC from {npc_file}{C.RESET}")
        return data

    # Default NPC for demo
    return {
        "npc_name": "Thorin Ironfoot",
        "npc_appearance": "A stocky dwarf with burn scars on his forearms and a braided copper beard",
        "npc_voice": "Gruff, low rumble with occasional grunts of approval or disapproval",
        "npc_personality": "Stoic and hardworking, values craftsmanship above all. Distrustful of magic but respects those who earn their keep through honest labor.",
        "npc_behavior": "Observes before acting, prefers direct confrontation to subtlety. Will help those in genuine need but has no patience for fools.",
        "npc_goals": "Run a successful smithy, find an apprentice worthy of his techniques, forget the war",
    }


def run_encounter():
    """Run the interactive encounter."""
    parser = argparse.ArgumentParser(description="Multi-turn NPC Encounter")
    parser.add_argument("--npc-file", "-n", help="Path to NPC JSON file")
    parser.add_argument(
        "--location", "-l", default="The Rusty Anchor tavern", help="Location name"
    )
    args = parser.parse_args()

    print(f"\n{C.BOLD}{'=' * 60}{C.RESET}")
    print(f"{C.BOLD}⚔️  YAMLGraph NPC Encounter - Human-in-the-Loop{C.RESET}")
    print(f"{C.BOLD}{'=' * 60}{C.RESET}\n")

    # Load graph
    config = load_graph_config("examples/npc/encounter-loop.yaml")
    graph = compile_graph(config)
    checkpointer = get_checkpointer_for_graph(config)
    app = graph.compile(checkpointer=checkpointer)

    # Session setup
    thread_id = str(uuid.uuid4())
    run_config = {"configurable": {"thread_id": thread_id}}

    # Initial state
    npc_data = load_npc_data(args.npc_file)
    initial_state = {
        **npc_data,
        "location": args.location,
        "location_description": "A dimly lit tavern with rough wooden tables and the smell of ale",
        "turn_number": 1,
        "encounter_history": [],
    }

    print(f"{C.CYAN}🎭 NPC: {C.BOLD}{npc_data['npc_name']}{C.RESET}")
    print(f"{C.CYAN}📍 Location: {args.location}{C.RESET}")
    print(f"\n{C.DIM}Type 'end' to finish the encounter, 'quit' to exit.{C.RESET}\n")

    # Start the graph
    result = app.invoke(initial_state, run_config)
    turn = 1

    while True:
        # Check for interrupt
        interrupt_info = result.get("__interrupt__")

        if interrupt_info:
            print(f"\n{C.YELLOW}{'─' * 50}{C.RESET}")
            print(f"{C.YELLOW}🎲 Turn {turn}{C.RESET}")
            print(f"{C.YELLOW}{'─' * 50}{C.RESET}")

            # Get DM input
            try:
                dm_input = input(f"\n{C.BOLD}DM:{C.RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n\n{C.RED}👋 Encounter ended.{C.RESET}")
                return

            if dm_input.lower() in ("quit", "q"):
                print(f"\n{C.RED}👋 Goodbye!{C.RESET}")
                return

            # Resume with DM's input
            result = app.invoke(Command(resume=dm_input), run_config)

            # Show NPC response if we got one
            if result.get("narration") and dm_input.lower() != "end":
                print(f"\n{C.MAGENTA}📜 {npc_data['npc_name']}:{C.RESET}")
                narration = result.get("narration", "")
                if isinstance(narration, dict):
                    narration = narration.get("narration", str(narration))
                print(
                    f"{C.DIM}{narration[:500]}...{C.RESET}"
                    if len(str(narration)) > 500
                    else f"{C.DIM}{narration}{C.RESET}"
                )
                turn += 1
        else:
            # No interrupt means we're done
            break

    # Final summary
    print(f"\n{C.GREEN}{'=' * 60}{C.RESET}")
    print(f"{C.GREEN}⚔️  Encounter Complete! ({turn - 1} turns){C.RESET}")
    print(f"{C.GREEN}{'=' * 60}{C.RESET}\n")


if __name__ == "__main__":
    run_encounter()
