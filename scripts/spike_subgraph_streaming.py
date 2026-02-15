#!/usr/bin/env python3
"""
FR-030 Phase 2 Spike: Subgraph Token Streaming Research

Run experiments to determine viable approach for streaming from mode=invoke subgraphs.

Usage:
    python scripts/spike_subgraph_streaming.py [experiment_number]

    experiment_number: 1-4 (default: run all)
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def experiment_1_callback_propagation():
    """Verify callbacks reach child graph during invoke()."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 1: Callback Propagation Verification")
    print("=" * 60)

    from langchain_core.callbacks import BaseCallbackHandler

    from yamlgraph.executor_async import load_and_compile_async

    class DebugHandler(BaseCallbackHandler):
        run_inline = True
        events = []

        def on_chat_model_start(
            self, serialized, messages, *, run_id, metadata=None, **kwargs
        ):
            ns = metadata.get("langgraph_checkpoint_ns", "") if metadata else ""
            node = metadata.get("langgraph_node", "") if metadata else ""
            print(f"  [on_chat_model_start] node={node!r} ns={ns!r}")
            self.events.append(("start", node, ns))

        def on_llm_new_token(self, token, *, chunk=None, run_id, **kwargs):
            content = token[:30] if token else ""
            print(f"  [on_llm_new_token] {content!r}...")
            self.events.append(("token", content))

    try:
        app = await load_and_compile_async("examples/demos/subgraph/graph.yaml")

        handler = DebugHandler()
        result = await app.ainvoke(
            {"raw_text": "Test input for callback verification."},
            config={"callbacks": [handler]},
        )

        print(f"\nResult keys: {list(result.keys())}")
        print(f"Events captured: {len(handler.events)}")

        # Analysis
        start_events = [e for e in handler.events if e[0] == "start"]
        token_events = [e for e in handler.events if e[0] == "token"]

        print(f"\non_chat_model_start events: {len(start_events)}")
        for e in start_events:
            print(f"  - node={e[1]!r} ns={e[2]!r}")

        print(f"\non_llm_new_token events: {len(token_events)}")

        return {
            "status": "success",
            "start_events": len(start_events),
            "token_events": len(token_events),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "error": str(e)}


async def experiment_2_subgraphs_true():
    """Test streaming with subgraphs=True from parent astream()."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: astream() with subgraphs=True")
    print("=" * 60)

    from yamlgraph.executor_async import load_and_compile_async

    try:
        app = await load_and_compile_async("examples/demos/subgraph/graph.yaml")

        events = []
        async for event in app.astream(
            {"raw_text": "Test streaming with subgraphs=True."},
            config={},
            stream_mode="messages",
            subgraphs=True,
        ):
            events.append(event)
            print(f"  Event type: {type(event).__name__}")
            if isinstance(event, tuple) and len(event) == 2:
                ns, payload = event
                print(f"    namespace: {ns}")
                if isinstance(payload, tuple) and len(payload) == 2:
                    chunk, meta = payload
                    node = meta.get("langgraph_node", "?")
                    content = getattr(chunk, "content", None)
                    if content:
                        print(f"    node: {node}, content: {str(content)[:50]}...")

        print(f"\nTotal events: {len(events)}")

        return {
            "status": "success",
            "total_events": len(events),
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "error": str(e)}


async def experiment_3_async_wrapper():
    """Test async wrapper with astream() approach."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Async Wrapper with astream()")
    print("=" * 60)

    from yamlgraph.graph_loader import compile_graph, load_graph_config

    try:
        # Load a simple graph to test streaming approach
        child_path = Path("examples/demos/hello/graph.yaml")
        child_config = load_graph_config(child_path)
        child_state_graph = compile_graph(child_config)
        compiled = child_state_graph.compile()

        # Test astream on child directly
        print("\nStreaming from child graph directly:")
        tokens_direct = []
        async for event in compiled.astream(
            {"name": "Test", "style": "brief"},
            config={},
            stream_mode="messages",
        ):
            chunk, meta = event
            if hasattr(chunk, "content") and chunk.content:
                tokens_direct.append(str(chunk.content))
                print(f"  Token: {str(chunk.content)[:30]!r}...")

        print(f"\nDirect streaming tokens: {len(tokens_direct)}")

        # Now test what happens when we wrap it
        print("\nWrapped in sync function (simulating mode=invoke):")

        def sync_wrapper(state, config=None):
            # This is what mode=invoke currently does
            child_output = compiled.invoke(state, config)
            return child_output

        # We can't easily stream from sync wrapper
        result = sync_wrapper({"name": "Test2", "style": "brief"}, {})
        print(f"  Result: {result.get('greeting', '')[:50]}...")

        return {
            "status": "success",
            "direct_tokens": len(tokens_direct),
            "insight": "Direct astream works; sync wrapper blocks streaming",
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "error": str(e)}


async def experiment_4_stream_propagation():
    """Test propagating __pregel_stream to child config."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 4: CONFIG_KEY_STREAM Propagation")
    print("=" * 60)

    from typing import TypedDict

    from langgraph._internal._constants import CONFIG_KEY_STREAM
    from langgraph.graph import StateGraph

    try:
        # Check if CONFIG_KEY_STREAM appears in config during streaming
        print(f"\nCONFIG_KEY_STREAM = {CONFIG_KEY_STREAM!r}")

        # Create a simple graph to inspect config
        class TestState(TypedDict):
            message: str
            config_keys: list

        def inspect_node(state, config=None):
            config = config or {}
            configurable = config.get("configurable", {})
            keys = list(configurable.keys())
            print(f"  Config keys in node: {keys}")
            has_stream = CONFIG_KEY_STREAM in configurable
            print(f"  Has {CONFIG_KEY_STREAM}: {has_stream}")
            return {"config_keys": keys}

        graph = StateGraph(TestState)
        graph.add_node("inspect", inspect_node)
        graph.set_entry_point("inspect")
        graph.set_finish_point("inspect")
        app = graph.compile()

        print("\nRunning with astream():")
        async for _event in app.astream(
            {"message": "test"},
            config={},
            stream_mode="messages",
        ):
            pass  # Just run to see config inspection

        return {
            "status": "success",
            "insight": "CONFIG_KEY_STREAM may or may not be in configurable",
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {"status": "error", "error": str(e)}


async def main():
    """Run all experiments or specific one."""
    experiments = {
        1: experiment_1_callback_propagation,
        2: experiment_2_subgraphs_true,
        3: experiment_3_async_wrapper,
        4: experiment_4_stream_propagation,
    }

    if len(sys.argv) > 1:
        try:
            exp_num = int(sys.argv[1])
            if exp_num in experiments:
                result = await experiments[exp_num]()
                print(f"\nResult: {result}")
            else:
                print(f"Unknown experiment: {exp_num}")
                print(f"Available: {list(experiments.keys())}")
        except ValueError:
            print(f"Invalid experiment number: {sys.argv[1]}")
    else:
        # Run all experiments
        results = {}
        for num, func in experiments.items():
            results[num] = await func()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for num, result in results.items():
            status = result.get("status", "unknown")
            print(f"  Experiment {num}: {status}")


if __name__ == "__main__":
    asyncio.run(main())
