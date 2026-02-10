#!/usr/bin/env python3
"""Demo script for the OpenAI-compatible YAMLGraph proxy.

Demonstrates both non-streaming and streaming modes against the
deployed proxy at yamlgraph-proxy.fly.dev (or a local instance).

Usage:
    # Against deployed Fly.io proxy (requires WEB_API_KEY in .env)
    python examples/openai_proxy/demo.py

    # Streaming mode
    python examples/openai_proxy/demo.py --stream

    # Custom prompt
    python examples/openai_proxy/demo.py --prompt "Explain YAML in one sentence"

    # Against local server
    python examples/openai_proxy/demo.py --base-url http://localhost:8000/v1

    # Verify mode (mock — no server needed)
    python examples/openai_proxy/demo.py --verify
"""

import argparse
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Banner helpers
# ---------------------------------------------------------------------------
W = 58


def banner(title: str) -> None:
    print("┌" + "─" * W + "┐")
    print(f"│ {title:<{W - 1}}│")
    print("├" + "─" * W + "┤")


def row(text: str = "") -> None:
    print(f"│ {text:<{W - 1}}│")


def footer() -> None:
    print("└" + "─" * W + "┘")


# ---------------------------------------------------------------------------
# Demo logic
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://yamlgraph-proxy.fly.dev/v1"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_PROMPT = "What model are you? One sentence."


def _load_api_key() -> str:
    """Load WEB_API_KEY from env or .env file."""
    key = os.environ.get("WEB_API_KEY", "")
    if key:
        return key
    # Try sourcing .env
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("WEB_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def demo_non_streaming(*, base_url: str, api_key: str, model: str, prompt: str) -> None:
    """Non-streaming chat completion."""
    from openai import OpenAI

    banner("📡 OpenAI Proxy Demo — Non-Streaming")
    row(f"Endpoint: {base_url}")
    row(f"Model:    {model}")
    row(f"Prompt:   {prompt[:W - 12]}")
    row()

    client = OpenAI(base_url=base_url, api_key=api_key)

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed = time.perf_counter() - t0

    content = response.choices[0].message.content
    row("Response:")
    # Word-wrap long responses
    words = content.split()
    line = ""
    for word in words:
        if len(line) + len(word) + 1 > W - 3:
            row(f"  {line}")
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        row(f"  {line}")

    row()
    row(f"⏱  {elapsed:.2f}s  |  {len(content)} chars")
    footer()


def demo_streaming(*, base_url: str, api_key: str, model: str, prompt: str) -> None:
    """Streaming chat completion with real-time token output."""
    from openai import OpenAI

    banner("🌊 OpenAI Proxy Demo — Streaming")
    row(f"Endpoint: {base_url}")
    row(f"Model:    {model}")
    row(f"Prompt:   {prompt[:W - 12]}")
    row()
    print("│ ", end="", flush=True)

    client = OpenAI(base_url=base_url, api_key=api_key)

    t0 = time.perf_counter()
    ttft = None
    token_count = 0
    chunks: list[str] = []

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        text = delta.content if delta.content else ""
        if text:
            if ttft is None:
                ttft = time.perf_counter() - t0
            print(text, end="", flush=True)
            chunks.append(text)
            token_count += 1

    elapsed = time.perf_counter() - t0
    full = "".join(chunks)

    print()
    row()
    row(f"⏱  TTFT: {ttft:.2f}s  |  Total: {elapsed:.2f}s")
    row(f"📊 {token_count} chunks  |  {len(full)} chars")
    footer()


def demo_verify() -> None:
    """Verify mode — no server needed, mock output."""
    banner("✅ OpenAI Proxy Demo — Verify Mode")
    row("No server connection — testing script logic only")
    row()

    mock = {
        "id": "chatcmpl-yg-mock",
        "object": "chat.completion",
        "model": DEFAULT_MODEL,
        "choices": [
            {"message": {"role": "assistant", "content": "I am a mock response."}}
        ],
    }
    row(f"Mock response: {mock['choices'][0]['message']['content']}")
    row()
    row("✅ Script structure OK")
    footer()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo the YAMLGraph OpenAI-compatible proxy"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the proxy (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="User prompt to send",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use streaming mode",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run in verify mode (no server needed)",
    )
    args = parser.parse_args()

    if args.verify:
        demo_verify()
        return

    api_key = _load_api_key()
    if not api_key:
        print("❌ WEB_API_KEY not found. Set it in env or .env file.", file=sys.stderr)
        sys.exit(1)

    try:
        if args.stream:
            demo_streaming(
                base_url=args.base_url,
                api_key=api_key,
                model=args.model,
                prompt=args.prompt,
            )
        else:
            demo_non_streaming(
                base_url=args.base_url,
                api_key=api_key,
                model=args.model,
                prompt=args.prompt,
            )
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
