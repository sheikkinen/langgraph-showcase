"""Showcase CLI - Command-line interface for the showcase app.

Demonstrates how to expose LangGraph pipelines via CLI.

Usage:
    showcase run --topic "machine learning" --style casual
    showcase list-runs
    showcase resume --thread-id abc123
    showcase trace --run-id <run-id>
"""

import argparse
import sys

from showcase.config import MAX_TOPIC_LENGTH, MAX_WORD_COUNT, MIN_WORD_COUNT, VALID_STYLES
from showcase.utils.sanitize import sanitize_topic


def validate_run_args(args) -> bool:
    """Validate and sanitize run command arguments.
    
    Args:
        args: Parsed arguments namespace
        
    Returns:
        True if valid, False otherwise (prints error message)
    """
    # Sanitize topic
    result = sanitize_topic(args.topic)
    if not result.is_safe:
        for warning in result.warnings:
            print(f"❌ {warning}")
        return False
    
    # Update args with sanitized value
    args.topic = result.value
    
    # Print any warnings (e.g., truncation)
    for warning in result.warnings:
        print(f"⚠️  {warning}")
    
    if args.word_count < MIN_WORD_COUNT or args.word_count > MAX_WORD_COUNT:
        print(f"❌ Word count must be between {MIN_WORD_COUNT} and {MAX_WORD_COUNT}")
        return False
    
    return True


def cmd_run(args):
    """Run the showcase pipeline."""
    if not validate_run_args(args):
        sys.exit(1)
    
    from showcase.builder import run_pipeline
    from showcase.storage import ShowcaseDB, export_state
    from showcase.utils import get_run_url, is_tracing_enabled
    
    print(f"\n🚀 Running showcase pipeline")
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
        print(f"\n🔍 Analysis:")
        print(f"   Sentiment: {analysis.sentiment} (confidence: {analysis.confidence:.2f})")
        print(f"   Key points: {len(analysis.key_points)}")
    
    if summary := result.get("final_summary"):
        print(f"\n📊 Summary:")
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
    
    # Determine where to resume from
    if state.get("generated") and not state.get("analysis"):
        start_from = "analyze"
    elif state.get("analysis") and not state.get("final_summary"):
        start_from = "summarize"
    else:
        print("✅ Pipeline already complete!")
        return
    
    print(f"   Starting from: {start_from}")
    
    graph = build_resume_graph(start_from=start_from).compile()
    result = graph.invoke(state)
    
    # Save updated state
    db.save_state(args.thread_id, result, status="completed")
    print(f"\n✅ Pipeline completed!")
    
    if summary := result.get("final_summary"):
        print(f"\n📊 Summary: {summary[:200]}...")


def cmd_trace(args):
    """Show execution trace for a run."""
    from showcase.utils import get_latest_run_id, get_run_url, print_run_tree
    
    run_id = args.run_id or get_latest_run_id()
    
    if not run_id:
        print("❌ No run ID provided and could not find latest run.")
        return
    
    print(f"\n📊 Execution trace for: {run_id}\n")
    print_run_tree(run_id, verbose=args.verbose)
    
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Showcase App - LangGraph Pipeline Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the pipeline")
    run_parser.add_argument("--topic", "-t", required=True, help="Topic to generate content about")
    run_parser.add_argument("--style", "-s", default="informative", 
                           choices=["informative", "casual", "technical"],
                           help="Writing style")
    run_parser.add_argument("--word-count", "-w", type=int, default=300,
                           help="Target word count")
    run_parser.add_argument("--export", "-e", action="store_true",
                           help="Export result to JSON")
    run_parser.set_defaults(func=cmd_run)
    
    # List runs command
    list_parser = subparsers.add_parser("list-runs", help="List recent runs")
    list_parser.add_argument("--limit", "-l", type=int, default=10,
                            help="Maximum runs to show")
    list_parser.set_defaults(func=cmd_list_runs)
    
    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a pipeline")
    resume_parser.add_argument("--thread-id", "-i", required=True,
                              help="Thread ID to resume")
    resume_parser.set_defaults(func=cmd_resume)
    
    # Trace command
    trace_parser = subparsers.add_parser("trace", help="Show execution trace")
    trace_parser.add_argument("--run-id", "-r", help="Run ID (uses latest if not provided)")
    trace_parser.add_argument("--verbose", "-v", action="store_true",
                             help="Include timing details")
    trace_parser.set_defaults(func=cmd_trace)
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export a run to JSON")
    export_parser.add_argument("--thread-id", "-i", required=True,
                              help="Thread ID to export")
    export_parser.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == "__main__":
    main()
