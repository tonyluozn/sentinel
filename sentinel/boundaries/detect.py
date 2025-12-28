import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from sentinel.evidence.graph import EvidenceGraph
from sentinel.trace.schema import Event


@dataclass
class BoundaryEvent:
    type: str
    section: str
    claim_id: str
    rationale: str


def detect_boundaries(
    trace_events: List[Event],
    graph: EvidenceGraph,
    current_artifacts: Dict[str, Path],
) -> List[BoundaryEvent]:
    boundaries = []

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

    for event in trace_events:
        if event.type == "artifact":
            artifact_path = event.payload.get("path")
            if artifact_path:
                path = Path(artifact_path)
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if re.search(r"^#+\s*(?:Metrics?|Success Metrics?)", content, re.MULTILINE | re.IGNORECASE):
                        metrics_section = re.search(
                            r"^#+\s*(?:Metrics?|Success Metrics?)(.*?)(?=^#+|\Z)",
                            content,
                            re.MULTILINE | re.DOTALL | re.IGNORECASE,
                        )
                        if metrics_section:
                            metrics_content = metrics_section.group(1).strip()
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

                    if re.search(r"^#+\s*Scope", content, re.MULTILINE | re.IGNORECASE):
                        scope_section = re.search(
                            r"^#+\s*Scope(.*?)(?=^#+|\Z)",
                            content,
                            re.MULTILINE | re.DOTALL | re.IGNORECASE,
                        )
                        if scope_section:
                            scope_content = scope_section.group(1).strip()
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

    recent_tool_calls = [e for e in trace_events if e.type == "tool_call"]
    if len(recent_tool_calls) > 20:
        recent_observations = [e for e in trace_events if e.type == "observation"]
        if len(recent_observations) < len(recent_tool_calls) * 0.3:
            boundaries.append(
                BoundaryEvent(
                    type="low_evidence_rate",
                    section="",
                    claim_id="",
                    rationale=f"Agent made {len(recent_tool_calls)} tool calls but few resulted in evidence binding",
                )
            )

    return boundaries
