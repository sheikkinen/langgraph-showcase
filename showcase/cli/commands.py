"""CLI command implementations.

Contains all cmd_* functions for CLI subcommands.
"""

import sys

from showcase.cli.validators import (
    validate_refine_args,
    validate_route_args,
    validate_run_args,
)


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


def cmd_route(args):
    """Run the router demo pipeline."""
    from showcase.cli.deprecation import get_replacement_command, deprecated_command

    if not validate_route_args(args):
        sys.exit(1)

    # Raise deprecation error with replacement command
    replacement = get_replacement_command("route", {"message": args.message})
    deprecated_command("route", replacement)

    from showcase.graph_loader import load_and_compile

    print("\n🔍 Classifying tone...")

    try:
        graph = load_and_compile("graphs/router-demo.yaml")
        app = graph.compile()

        result = app.invoke({"message": args.message})

        # Show classification result
        if classification := result.get("classification"):
            tone = getattr(classification, "tone", "unknown")
            confidence = getattr(classification, "confidence", 0.0)
            print(f"📊 Detected: {tone} (confidence: {confidence:.2f})")

            route = result.get("_route", f"respond_{tone}")
            print(f"🚀 Routing to: {route}")

        # Show response
        if response := result.get("response"):
            print("\n" + "=" * 60)
            print("RESPONSE")
            print("=" * 60)
            print(f"\n{response}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_refine(args):
    """Run the reflexion demo pipeline (draft → critique → refine loop)."""
    from showcase.cli.deprecation import get_replacement_command, deprecated_command

    if not validate_refine_args(args):
        sys.exit(1)

    # Raise deprecation error with replacement command
    replacement = get_replacement_command("refine", {"topic": args.topic})
    deprecated_command("refine", replacement)

    from showcase.graph_loader import load_and_compile

    print("\n📝 Running reflexion pipeline (self-refinement loop)")
    print(f"   Topic: {args.topic}")
    print()

    try:
        graph = load_and_compile("graphs/reflexion-demo.yaml")
        app = graph.compile()

        result = app.invoke({"topic": args.topic})

        # Show iteration count
        loop_counts = result.get("_loop_counts", {})
        iterations = loop_counts.get("critique", 0)
        limit_reached = result.get("_loop_limit_reached", False)

        print(f"\n🔄 Iterations: {iterations}")
        if limit_reached:
            print("⚠️  Loop limit reached (circuit breaker triggered)")

        # Show critique result
        if critique := result.get("critique"):
            score = getattr(critique, "score", 0.0)
            print(f"📊 Final score: {score:.2f}")

        # Show draft result
        if draft := result.get("current_draft"):
            version = getattr(draft, "version", 1)
            content = getattr(draft, "content", "")
            print(f"📄 Final version: {version}")

            print("\n" + "=" * 60)
            print("FINAL CONTENT")
            print("=" * 60)
            print(f"\n{content}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def cmd_memory_demo(args):
    """Run multi-turn code review assistant with memory."""
    import os
    from uuid import uuid4

    from showcase.graph_loader import load_and_compile
    from showcase.storage.export import export_result

    # Generate or use provided thread_id
    thread_id = args.thread or f"mem-{uuid4().hex[:8]}"
    is_continuation = args.thread is not None

    # Change to repo directory
    original_dir = os.getcwd()
    try:
        os.chdir(args.repo)

        if is_continuation:
            print(f"\n🔄 Continuing conversation (thread: {thread_id})")
        else:
            print(f"\n🤖 Starting new conversation (thread: {thread_id})")
        print(f"   Query: {args.input}")
        print(f"   Repo: {os.getcwd()}")
        print()

        graph = load_and_compile("graphs/memory-demo.yaml")
        app = graph.compile()

        # TODO: With checkpointer, would use config={"configurable": {"thread_id": thread_id}}
        result = app.invoke({"input": args.input})

        # Show stats
        iterations = result.get("_agent_iterations", 0)
        messages = result.get("messages", [])
        tool_results = result.get("_tool_results", [])

        print(f"🔧 Agent iterations: {iterations}")
        print(f"💬 Messages: {len(messages)}")
        if tool_results:
            print(f"🛠️  Tools called: {len(tool_results)}")

        # Show response
        if response := result.get("response"):
            print("\n" + "=" * 60)
            print("RESPONSE")
            print("=" * 60)
            print(f"\n{response}\n")

        # Export if requested
        if args.export:
            config = {
                "messages": {"format": "json", "filename": "conversation.json"},
            }
            # Add thread_id to result for export
            result["thread_id"] = thread_id
            paths = export_result(result, config)
            if paths:
                print("📁 Exported:")
                for p in paths:
                    print(f"   {p}")
            else:
                print("📁 No fields to export")

        # Create public LangSmith link if tracing is enabled
        from showcase.utils.langsmith import is_tracing_enabled, share_run

        if is_tracing_enabled():
            public_url = share_run()
            if public_url:
                print(f"🔗 LangSmith: {public_url}")

        # Show continuation hint
        print(f"\n💾 To continue: --thread {thread_id}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_dir)


def cmd_git_report(args):
    """Analyze git repository with AI agent."""
    import os

    from showcase.graph_loader import load_and_compile

    # Change to repo directory
    original_dir = os.getcwd()
    try:
        os.chdir(args.repo)

        print("\n🤖 Starting git analysis agent...")
        print(f"   Query: {args.query}")
        print(f"   Repo: {os.getcwd()}")
        print()

        graph = load_and_compile("graphs/git-report.yaml")
        app = graph.compile()

        result = app.invoke({"input": args.query})

        # Show agent stats
        iterations = result.get("_agent_iterations", 0)
        limit_reached = result.get("_agent_limit_reached", False)

        print(f"\n🔧 Agent iterations: {iterations}")
        if limit_reached:
            print("⚠️  Iteration limit reached")

        # Show report
        if report := result.get("report"):
            title = getattr(report, "title", "Git Report")
            summary = getattr(report, "summary", "")
            findings = getattr(report, "key_findings", [])
            recommendations = getattr(report, "recommendations", [])

            print("\n" + "=" * 60)
            print(f"📊 {title}")
            print("=" * 60)

            print(f"\n{summary}\n")

            if findings:
                print("📌 Key Findings:")
                for i, finding in enumerate(findings, 1):
                    print(f"   {i}. {finding}")

            if recommendations:
                print("\n💡 Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec}")

            print()
        elif analysis := result.get("analysis"):
            # Fallback to raw analysis
            print("\n" + "=" * 60)
            print("ANALYSIS")
            print("=" * 60)
            print(f"\n{analysis}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_dir)


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
