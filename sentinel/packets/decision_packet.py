"""Generate decision packets for escalation."""

from pathlib import Path
from typing import Dict, List

from sentinel.evidence.graph import EvidenceGraph
from sentinel.interventions.types import Intervention
from sentinel.trace.schema import EventType, new_event
from sentinel.trace.store_jsonl import JsonlTraceStore


def generate_packet(
    run_id: str,
    context: Dict,
    interventions: List[Intervention],
    graph: EvidenceGraph,
    output_dir: Path,
    trace_store: JsonlTraceStore,
) -> Path:
    """Generate a decision packet markdown file.

    Args:
        run_id: Run identifier.
        context: Context dict with repo, milestone, etc.
        interventions: List of interventions that triggered escalation.
        graph: Evidence graph with claims and evidence.
        output_dir: Directory to write packet to.
        trace_store: Trace store for logging.

    Returns:
        Path to generated packet file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find next packet number
    existing_packets = list(output_dir.glob("packet_*.md"))
    packet_num = len(existing_packets)
    packet_path = output_dir / f"packet_{packet_num}.md"

    # Gather uncovered claims
    uncovered = graph.uncovered_claims(min_severity="HIGH")

    # Gather evidence summary
    evidence_summary = []
    for evidence in graph.evidence.values():
        evidence_summary.append(f"- {evidence.snippet[:100]}... (from {evidence.source_ref})")

    # Write packet
    with open(packet_path, "w", encoding="utf-8") as f:
        f.write(f"# Decision Packet {packet_num}\n\n")
        f.write(f"**Run ID**: {run_id}\n\n")
        f.write(f"**Generated**: {new_event(EventType.DECISION, {}).ts}\n\n")

        f.write("## Context\n\n")
        f.write(f"- **Repository**: {context.get('repo', 'N/A')}\n")
        f.write(f"- **Milestone**: {context.get('milestone', 'N/A')}\n")
        f.write(f"- **Issue Count**: {context.get('issue_count', 0)}\n\n")

        f.write("## Decision Boundary Reason\n\n")
        if interventions:
            f.write(f"Escalation triggered by: {interventions[0].type.value}\n\n")
            f.write(f"**Rationale**: {interventions[0].rationale}\n\n")

        f.write("## Uncovered Claims\n\n")
        if uncovered:
            for claim in uncovered:
                f.write(f"### {claim.section}: {claim.text[:100]}...\n\n")
                f.write(f"- **Severity**: {claim.severity}\n")
                f.write(f"- **Source**: {claim.artifact_path}\n\n")
        else:
            f.write("No uncovered HIGH severity claims.\n\n")

        f.write("## Evidence Gathered\n\n")
        if evidence_summary:
            f.write("\n".join(evidence_summary[:10]))  # Limit to 10 items
            f.write("\n\n")
        else:
            f.write("No evidence gathered yet.\n\n")

        f.write("## Assumptions\n\n")
        f.write("- Agent is working with available GitHub milestone data\n")
        f.write("- Evidence binding uses keyword matching\n")
        f.write("- HIGH severity claims require supporting evidence\n\n")

        f.write("## Recommended Next Actions\n\n")
        if interventions:
            for step in interventions[0].suggested_next_steps:
                f.write(f"- {step}\n")
        f.write("\n")

    # Emit escalation_packet event
    trace_store.append(
        new_event(
            EventType.ESCALATION_PACKET,
            {
                "run_id": run_id,
                "packet_path": str(packet_path),
                "intervention_count": len(interventions),
                "uncovered_claims_count": len(uncovered),
            },
        )
    )

    return packet_path
