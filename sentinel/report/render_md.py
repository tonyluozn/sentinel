from pathlib import Path
from typing import Dict

from sentinel.evidence.graph import EvidenceGraph
from sentinel.trace.schema import EventType
from sentinel.trace.store_jsonl import JsonlTraceStore


def generate_report(
    run_id: str,
    trace_store: JsonlTraceStore,
    artifacts_dir: Path,
    packets_dir: Path,
    graph: EvidenceGraph,
) -> Path:
    events = list(trace_store.iter_events())

    event_counts: Dict[str, int] = {}
    for event in events:
        event_counts[event.type] = event_counts.get(event.type, 0) + 1

    interventions = [e for e in events if e.type == EventType.INTERVENTION]
    uncovered = graph.uncovered_claims(min_severity="HIGH")
    artifacts = list(artifacts_dir.glob("*.md")) if artifacts_dir.exists() else []
    packets = list(packets_dir.glob("packet_*.md")) if packets_dir.exists() else []

    report_dir = Path("runs") / run_id / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "report.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Sentinel Run Report\n\n")
        f.write(f"**Run ID**: {run_id}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Events**: {len(events)}\n")
        f.write(f"- **LLM Calls**: {event_counts.get(EventType.LLM_CALL, 0)}\n")
        f.write(f"- **Tool Calls**: {event_counts.get(EventType.TOOL_CALL, 0)}\n")
        f.write(f"- **Artifacts Created**: {event_counts.get(EventType.ARTIFACT, 0)}\n")
        f.write(f"- **Interventions Issued**: {len(interventions)}\n")
        f.write(f"- **Uncovered Claims**: {len(uncovered)}\n\n")

        f.write("## Interventions\n\n")
        if interventions:
            for i, intervention_event in enumerate(interventions, 1):
                payload = intervention_event.payload
                f.write(f"### Intervention {i}\n\n")
                f.write(f"- **Type**: {payload.get('type', 'N/A')}\n")
                f.write(f"- **Rationale**: {payload.get('rationale', 'N/A')}\n")
                f.write(f"- **Target**: {payload.get('target_id', 'N/A')}\n\n")
        else:
            f.write("No interventions issued.\n\n")

        f.write("## Uncovered Claims\n\n")
        if uncovered:
            for claim in uncovered:
                f.write(f"- **{claim.section}**: {claim.text[:100]}... (Severity: {claim.severity})\n")
        else:
            f.write("All HIGH severity claims have supporting evidence.\n\n")

        f.write("## Artifacts\n\n")
        if artifacts:
            for artifact in artifacts:
                f.write(f"- [{artifact.name}]({artifact.relative_to(report_path.parent.parent)})\n")
        else:
            f.write("No artifacts found.\n\n")

        f.write("## Packets\n\n")
        if packets:
            for packet in packets:
                f.write(f"- [{packet.name}]({packet.relative_to(report_path.parent.parent)})\n")
        else:
            f.write("No escalation packets generated.\n\n")

        f.write("## Trace\n\n")
        f.write(f"Trace file: `trace/events.jsonl` ({len(events)} events)\n\n")

    return report_path
