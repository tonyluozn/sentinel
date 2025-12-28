import argparse
import sys
from datetime import datetime
from pathlib import Path

from sentinel.agent.loop import run_agent_with_supervisor
from sentinel.config import get_runs_dir
from sentinel.evidence.graph import EvidenceGraph
from sentinel.github.cache import FileCache
from sentinel.github.client import GitHubClient
from sentinel.github.fetch import fetch_repo_milestone_bundle
from sentinel.interventions.policy import Supervisor
from sentinel.report.render_md import generate_report
from sentinel.trace.store_jsonl import JsonlTraceStore


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def cmd_fetch(args):
    cache = FileCache()
    client = GitHubClient()
    trace_store = JsonlTraceStore(Path("/dev/null"))

    try:
        bundle = fetch_repo_milestone_bundle(args.repo, args.milestone, cache, client, trace_store)
        print(f"✓ Fetched bundle for {args.repo} milestone '{args.milestone}'")
        print(f"  Issues: {len(bundle.get('issues', []))}")
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_run(args):
    run_id = args.run_id or generate_run_id()

    runs_dir = get_runs_dir()
    run_dir = runs_dir / run_id
    trace_path = run_dir / "trace" / "events.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    trace_store = JsonlTraceStore(trace_path)
    graph = EvidenceGraph()
    supervisor = Supervisor(graph, trace_store)

    try:
        result = run_agent_with_supervisor(
            args.repo,
            args.milestone,
            run_id,
            trace_store,
            supervisor,
            llm_client=None,
        )

        print(f"✓ Run completed: {run_id}")
        print(f"  Artifacts: {len(result['artifacts'])}")
        print(f"  Events: {result['event_count']}")
        print(f"  Interventions: {result['intervention_count']}")
        print(f"  Uncovered claims: {result['uncovered_claims']}")
        print(f"\n  Report: {result['report_path']}")
        print(f"  Trace: {result['trace_path']}")

        latest_path = runs_dir / "latest"
        if latest_path.exists():
            latest_path.unlink()
        latest_path.symlink_to(run_id)

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        trace_store.close()


def cmd_report(args):
    runs_dir = get_runs_dir()
    run_dir = runs_dir / args.run_id

    if not run_dir.exists():
        print(f"✗ Run {args.run_id} not found", file=sys.stderr)
        sys.exit(1)

    trace_path = run_dir / "trace" / "events.jsonl"
    artifacts_dir = run_dir / "artifacts"
    packets_dir = run_dir / "packets"

    if not trace_path.exists():
        print(f"✗ Trace file not found: {trace_path}", file=sys.stderr)
        sys.exit(1)

    trace_store = JsonlTraceStore(trace_path)
    graph = EvidenceGraph()

    report_path = generate_report(args.run_id, trace_store, artifacts_dir, packets_dir, graph)

    print(f"✓ Report generated: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Sentinel: Runtime supervision for AI agents")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch and cache GitHub milestone bundle")
    fetch_parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    fetch_parser.add_argument("--milestone", required=True, help="Milestone title")

    run_parser = subparsers.add_parser("run", help="Run agent with supervisor")
    run_parser.add_argument("--repo", required=True, help="Repository (owner/repo)")
    run_parser.add_argument("--milestone", required=True, help="Milestone title")
    run_parser.add_argument("--run-id", help="Run ID (default: auto-generated)")

    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("--run-id", required=True, help="Run ID")
    report_parser.add_argument("--format", default="markdown", help="Report format (default: markdown)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
