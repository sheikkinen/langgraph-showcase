"""CLI command implementations.

Contains all cmd_* functions for CLI subcommands.
"""

import sys

from showcase.cli.validators import validate_run_args


def cmd_run(args):
    """Run the showcase pipeline."""
    if not validate_run_args(args):
        sys.exit(1)

    from showcase.builder import run_pipeline
    from showcase.storage import ShowcaseDB, export_state
    from showcase.utils import get_run_url, is_tracing_enabled

    print("\n🚀 Running showcase pipeline")
    print(f"   Topic: {args.topic}")
    print(f"   Style: {args.style}")
    print(f"   Words: {args.word_count}")
    print()

    # Run pipeline
    result = run_pipeline(
        topic=args.topic,
        style=args.style,
        word_count=args.word_count,
    )

    # Save to database
    db = ShowcaseDB()
    db.save_state(result["thread_id"], result, status="completed")
    print(f"\n💾 Saved to database: thread_id={result['thread_id']}")

    # Export to JSON
    if args.export:
        filepath = export_state(result)
        print(f"📄 Exported to: {filepath}")

    # Show results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if generated := result.get("generated"):
        print(f"\n📝 Generated: {generated.title}")
        print(f"   {generated.content[:200]}...")

    if analysis := result.get("analysis"):
        print("\n🔍 Analysis:")
        print(
            f"   Sentiment: {analysis.sentiment} (confidence: {analysis.confidence:.2f})"
        )
        print(f"   Key points: {len(analysis.key_points)}")

    if summary := result.get("final_summary"):
        print("\n📊 Summary:")
        print(f"   {summary[:300]}...")

    # Show LangSmith link
    if is_tracing_enabled():
        if url := get_run_url():
            print(f"\n🔗 LangSmith: {url}")

    print()


def cmd_list_runs(args):
    """List recent pipeline runs."""
    from showcase.storage import ShowcaseDB

    db = ShowcaseDB()
    runs = db.list_runs(limit=args.limit)

    if not runs:
        print("No runs found.")
        return

    print(f"\n📋 Recent runs ({len(runs)}):\n")
    print(f"{'Thread ID':<12} {'Status':<12} {'Updated':<20}")
    print("-" * 50)

    for run in runs:
        print(f"{run['thread_id']:<12} {run['status']:<12} {run['updated_at'][:19]}")

    print()


def cmd_resume(args):
    """Resume a pipeline from saved state."""
    from showcase.builder import build_resume_graph
    from showcase.storage import ShowcaseDB

    db = ShowcaseDB()
    state = db.load_state(args.thread_id)

    if not state:
        print(f"❌ No run found with thread_id: {args.thread_id}")
        return

    print(f"\n🔄 Resuming from: {state.get('current_step', 'unknown')}")

    # Check what's already completed
    if state.get("final_summary"):
        print("✅ Pipeline already complete!")
        return

    # Show what will be skipped vs run
    skipping = []
    running = []
    if state.get("generated"):
        skipping.append("generate")
    else:
        running.append("generate")
    if state.get("analysis"):
        skipping.append("analyze")
    else:
        running.append("analyze")
    running.append("summarize")  # Always runs if we get here

    if skipping:
        print(f"   Skipping: {', '.join(skipping)} (already in state)")
    print(f"   Running: {', '.join(running)}")

    graph = build_resume_graph().compile()
    result = graph.invoke(state)

    # Save updated state
    db.save_state(args.thread_id, result, status="completed")
    print("\n✅ Pipeline completed!")

    if summary := result.get("final_summary"):
        print(f"\n📊 Summary: {summary[:200]}...")


def cmd_trace(args):
    """Show execution trace for a run."""
    from showcase.utils import get_latest_run_id, get_run_url, print_run_tree
    from showcase.utils.langsmith import get_graph_mermaid

    run_id = args.run_id or get_latest_run_id()

    if not run_id:
        print("❌ No run ID provided and could not find latest run.")
        return

    print(f"\n📊 Execution trace for: {run_id}")
    print("─" * 50)
    print()
    print_run_tree(run_id, verbose=args.verbose)

    # Show graph structure in verbose mode
    if args.verbose:
        print("\n" + "─" * 50)
        print("📈 Pipeline Graph Structure:")
        print("─" * 50 + "\n")
        try:
            mermaid = get_graph_mermaid("main")
            # Print a simplified text version
            print("  generate → analyze → summarize → END")
            print("      ↓")
            print("   (error) → END")
            print()
            print("  Full Mermaid diagram:")
            for line in mermaid.split("\n"):
                print(f"    {line}")
        except Exception as e:
            print(f"  ⚠️  Could not generate graph: {e}")

    if url := get_run_url(run_id):
        print(f"\n🔗 View in LangSmith: {url}")

    print()


def cmd_export(args):
    """Export a run to JSON."""
    from showcase.storage import ShowcaseDB, export_state

    db = ShowcaseDB()
    state = db.load_state(args.thread_id)

    if not state:
        print(f"❌ No run found with thread_id: {args.thread_id}")
        return

    filepath = export_state(state)
    print(f"✅ Exported to: {filepath}")


def cmd_graph(args):
    """Show pipeline graph as Mermaid diagram."""
    from showcase.utils.langsmith import get_graph_mermaid

    try:
        mermaid = get_graph_mermaid(args.type)
        print(mermaid)
    except Exception as e:
        print(f"❌ Error generating graph: {e}")
