#!/usr/bin/env python3
"""POC: Test IBM Granite 4.0 via Replicate.

This script tests if we can use Granite as a cheap model tier
for the cost-router pattern.

Usage:
    python examples/cost-router/poc_granite.py

Requires:
    REPLICATE_API_TOKEN environment variable
"""

import os
import time

# Check for API token early
if not os.getenv("REPLICATE_API_TOKEN"):
    print("❌ REPLICATE_API_TOKEN not set")
    print("   Get your token at: https://replicate.com/account/api-tokens")
    print("   Then: export REPLICATE_API_TOKEN=r8_...")
    exit(1)

# Model to test
MODEL = "ibm-granite/granite-4.0-h-small"


def test_replicate_direct() -> None:
    """Test Granite via Replicate Python SDK directly."""
    print("\n" + "=" * 60)
    print("Test 1: Replicate SDK Direct")
    print("=" * 60)

    import replicate

    prompt = "What is the capital of France? Answer in one word."

    print(f"📤 Model: {MODEL}")
    print(f"📤 Prompt: {prompt}")
    print("⏳ Waiting for model (may cold-start)...")

    start = time.time()
    try:
        output = replicate.run(
            MODEL,
            input={
                "prompt": prompt,
                "max_tokens": 100,
                "temperature": 0.7,
            },
        )
        # Output is a generator, collect it
        result = "".join(output) if hasattr(output, "__iter__") else str(output)
        elapsed = time.time() - start

        print(f"✅ Response: {result}")
        print(f"⏱️  Time: {elapsed:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_replicate_async_poll() -> None:
    """Test Granite with async prediction and polling."""
    print("\n" + "=" * 60)
    print("Test 2: Replicate Async + Polling")
    print("=" * 60)

    import replicate

    prompt = "What is 2 + 2? Answer with just the number."

    print(f"📤 Model: {MODEL}")
    print(f"📤 Prompt: {prompt}")

    start = time.time()
    try:
        # Create prediction
        prediction = replicate.predictions.create(
            model=MODEL,
            input={
                "prompt": prompt,
                "max_tokens": 50,
                "temperature": 0.3,
            },
        )
        print(f"📋 Prediction ID: {prediction.id}")
        print(f"📋 Status: {prediction.status}")

        # Poll until complete
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            print(f"⏳ Status: {prediction.status}...")
            time.sleep(2)
            prediction.reload()

        elapsed = time.time() - start

        if prediction.status == "succeeded":
            result = prediction.output
            if isinstance(result, list):
                result = "".join(result)
            print(f"✅ Response: {result}")
        else:
            print(f"❌ Failed: {prediction.error}")

        print(f"⏱️  Time: {elapsed:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_structured_output() -> None:
    """Test if Granite can produce structured JSON output."""
    print("\n" + "=" * 60)
    print("Test 3: Structured Output (JSON)")
    print("=" * 60)

    import json

    import replicate

    prompt = """You are a classifier. Respond with valid JSON only.

Classify this query's complexity for LLM routing.

Query: "What is the capital of France?"

Respond with JSON:
{"complexity": "simple", "reasoning": "factual lookup"}"""

    print("📤 Testing structured output capability...")

    start = time.time()
    try:
        output = replicate.run(
            MODEL,
            input={
                "prompt": prompt,
                "max_tokens": 200,
                "temperature": 0.3,
            },
        )
        result = "".join(output) if hasattr(output, "__iter__") else str(output)
        elapsed = time.time() - start

        print(f"📄 Raw response:\n{result}")

        # Try to parse as JSON
        try:
            parsed = json.loads(result.strip())
            print(f"✅ Valid JSON: {parsed}")
        except json.JSONDecodeError:
            # Try to extract JSON from response
            if "{" in result and "}" in result:
                json_str = result[result.index("{") : result.rindex("}") + 1]
                try:
                    parsed = json.loads(json_str)
                    print(f"⚠️  Extracted JSON: {parsed}")
                except json.JSONDecodeError:
                    print("❌ Could not parse JSON from response")
            else:
                print("❌ No JSON found in response")

        print(f"⏱️  Time: {elapsed:.2f}s")
    except Exception as e:
        print(f"❌ Error: {e}")


def main() -> None:
    """Run all POC tests."""
    print("🧪 Granite 4.0 POC - Testing Replicate Integration")
    print(f"   Model: {MODEL}")
    print("=" * 60)

    # Test 1: Direct Replicate SDK
    test_replicate_direct()

    # Test 2: Async with polling (handles cold start better)
    test_replicate_async_poll()

    # Test 3: Structured output
    test_structured_output()

    print("\n" + "=" * 60)
    print("POC Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
