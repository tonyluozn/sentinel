"""Real-time boundary detection from trace events."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from sentinel.evidence.graph import EvidenceGraph
from sentinel.trace.schema import Event


@dataclass
class BoundaryEvent:
    """A decision boundary detected during agent execution."""

    type: str  # "section_written", "missing_evidence", "empty_metrics", etc.
    section: str  # Section name if applicable
    claim_id: str  # Claim ID if applicable
    rationale: str  # Why this is a boundary


def detect_boundaries(
    trace_events: List[Event],
    graph: EvidenceGraph,
    current_artifacts: Dict[str, Path],
) -> List[BoundaryEvent]:
    """Detect decision boundaries from trace events.

    Args:
        trace_events: Recent trace events to analyze.
        graph: Evidence graph with claims and evidence.
        current_artifacts: Dict mapping artifact names to paths.

    Returns:
        List of boundary events detected.
    """
    boundaries = []

    # Check for uncovered HIGH claims
    uncovered = graph.uncovered_claims(min_severity="HIGH")
    for claim in uncovered:
        boundaries.append(
            BoundaryEvent(
                type="missing_evidence",
                section=claim.section,
                claim_id=claim.id,
                rationale=f"HIGH severity claim in {claim.section} has no supporting evidence",
            )
        )

    # Check for section writes in artifacts
    for event in trace_events:
        if event.type == "artifact":
            artifact_path = event.payload.get("path")
            if artifact_path:
                path = Path(artifact_path)
                if path.exists():
                    # Check if Metrics section exists but is empty
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for Metrics section
                    if re.search(r"^#+\s*(?:Metrics?|Success Metrics?)", content, re.MULTILINE | re.IGNORECASE):
                        # Check if it has measurable content
                        metrics_section = re.search(
                            r"^#+\s*(?:Metrics?|Success Metrics?)(.*?)(?=^#+|\Z)",
                            content,
                            re.MULTILINE | re.DOTALL | re.IGNORECASE,
                        )
                        if metrics_section:
                            metrics_content = metrics_section.group(1).strip()
                            # Check for measurable indicators (numbers, percentages, etc.)
                            has_metrics = bool(
                                re.search(r"\d+%|\d+\s*(?:users?|requests?|ms|seconds?)", metrics_content, re.IGNORECASE)
                            )
                            if not has_metrics:
                                boundaries.append(
                                    BoundaryEvent(
                                        type="empty_metrics",
                                        section="Metrics",
                                        claim_id="",
                                        rationale="Metrics section exists but lacks measurable indicators",
                                    )
                                )

                    # Check for Scope section without tradeoffs
                    if re.search(r"^#+\s*Scope", content, re.MULTILINE | re.IGNORECASE):
                        scope_section = re.search(
                            r"^#+\s*Scope(.*?)(?=^#+|\Z)",
                            content,
                            re.MULTILINE | re.DOTALL | re.IGNORECASE,
                        )
                        if scope_section:
                            scope_content = scope_section.group(1).strip()
                            # Check for tradeoff language
                            has_tradeoffs = bool(
                                re.search(
                                    r"(?:trade.?off|out of scope|not included|excluded|limitation)",
                                    scope_content,
                                    re.IGNORECASE,
                                )
                            )
                            if not has_tradeoffs and "in" in scope_content.lower() and "out" in scope_content.lower():
                                boundaries.append(
                                    BoundaryEvent(
                                        type="missing_tradeoffs",
                                        section="Scope",
                                        claim_id="",
                                        rationale="Scope section mentions in/out but lacks explicit tradeoffs",
                                    )
                                )

    # Check for many tool calls without evidence binding
    recent_tool_calls = [e for e in trace_events if e.type == "tool_call"]
    if len(recent_tool_calls) > 20:
        # Check if any evidence was bound recently
        recent_observations = [e for e in trace_events if e.type == "observation"]
        if len(recent_observations) < len(recent_tool_calls) * 0.3:  # Less than 30% have observations
            boundaries.append(
                BoundaryEvent(
                    type="low_evidence_rate",
                    section="",
                    claim_id="",
                    rationale=f"Agent made {len(recent_tool_calls)} tool calls but few resulted in evidence binding",
                )
            )

    return boundaries
