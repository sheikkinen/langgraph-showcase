#!/usr/bin/env python3
"""Streaming Demo - Showcases token-by-token LLM output.

Demonstrates:
- execute_prompt_streaming() async generator
- Real-time token output to terminal
- Collecting streamed tokens

Usage:
    # Interactive streaming
    python scripts/demo_streaming.py

    # With custom prompt
    python scripts/demo_streaming.py --prompt "Tell me a short story about a robot"

    # Verification mode (no LLM, mock output)
    python scripts/demo_streaming.py --verify
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from yamlgraph.executor_async import execute_prompt_streaming


def print_banner(title: str) -> None:
    """Print a styled banner."""
    width = 50
    print("┌" + "─" * width + "┐")
    print(f"│ {title:<{width - 1}}│")
    print("├" + "─" * width + "┤")


def print_footer() -> None:
    """Print footer."""
    print("└" + "─" * 50 + "┘")


async def run_streaming_demo(
    user_prompt: str,
    verify: bool = False,
) -> str:
    """Run the streaming demo.

    Args:
        user_prompt: What to ask the LLM
        verify: If True, skip actual LLM call

    Returns:
        Full collected response
    """
    print_banner("🌊 Streaming Demo")
    print(f"│ Prompt: {user_prompt[:40]:<41}│")
    print("│" + " " * 50 + "│")

    if verify:
        # Mock streaming for verification
        print("│ [Verify mode - mock streaming]                  │")
        print("│" + " " * 50 + "│")
        print("│ Response:                                        │")
        print("│ ", end="")

        mock_response = "Hello! This is a mock streaming response for testing purposes."
        for char in mock_response:
            print(char, end="", flush=True)
            await asyncio.sleep(0.02)

        print()
        print("│" + " " * 50 + "│")
        print_footer()
        return mock_response

    # Real streaming from LLM
    print("│ Streaming response:                              │")
    print("│" + " " * 50 + "│")

    tokens_collected = []

    # Create a simple prompt YAML on the fly by using greet prompt
    # In real usage, you'd have a prompt file
    try:
        async for token in execute_prompt_streaming(
            "greet",
            variables={"name": "streaming demo user", "style": user_prompt},
            provider="mistral",
        ):
            print(token, end="", flush=True)
            tokens_collected.append(token)
    except Exception as e:
        print(f"\n│ ❌ Error: {e!s:.40}│")
        print_footer()
        return ""

    full_response = "".join(tokens_collected)

    print()
    print("│" + " " * 50 + "│")
    print(f"│ ✅ Received {len(tokens_collected)} chunks, {len(full_response)} chars│")
    print_footer()

    return full_response


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Streaming Demo")
    parser.add_argument(
        "--prompt",
        default="casual and friendly",
        help="Style for the greeting prompt",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run in verification mode (mock output)",
    )
    args = parser.parse_args()

    result = await run_streaming_demo(
        user_prompt=args.prompt,
        verify=args.verify,
    )

    if args.verify:
        # Verification check
        print("\n🔍 Verification:")
        if len(result) > 0:
            print("  ✅ Streaming produced output")
        else:
            print("  ❌ No output received")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
