from pathlib import Path
from typing import Dict, List, Optional, Protocol

from sentinel.boundaries.detect import detect_boundaries
from sentinel.evidence.graph import EvidenceGraph
from sentinel.interventions.types import Intervention, InterventionType
from sentinel.trace.schema import Event, EventType, new_event

from sentinel.core.interfaces import TraceStore


class Supervisor:
    def __init__(self, graph: EvidenceGraph, trace_store: TraceStore):
        self.graph = graph
        self.trace_store = trace_store
        self.tool_call_count = 0
        self.interventions_issued = []

    def analyze_step(
        self,
        trace_events: List[Event],
        current_artifacts: Dict[str, Path],
    ) -> Optional[Intervention]:
        for event in trace_events:
            if event.type == "tool_call":
                self.tool_call_count += 1

        boundaries = detect_boundaries(trace_events, self.graph, current_artifacts)

        uncovered = self.graph.uncovered_claims(min_severity="HIGH")
        if uncovered:
            if len(uncovered) >= 3:
                intervention = Intervention(
                    type=InterventionType.ESCALATE,
                    target_id="multiple_claims",
                    rationale=f"{len(uncovered)} HIGH severity claims lack evidence",
                    suggested_next_steps=[
                        "Review uncovered claims",
                        "Gather additional evidence from GitHub issues",
                        "Consider reducing scope or clarifying requirements",
                    ],
                )
                self._emit_intervention(intervention)
                return intervention
            else:
                claim = uncovered[0]
                intervention = Intervention(
                    type=InterventionType.REQUEST_EVIDENCE,
                    target_id=claim.id,
                    rationale=f"HIGH severity claim in {claim.section} needs evidence",
                    suggested_next_steps=[
                        f"Fetch issue details related to: {claim.text[:50]}...",
                        "Search GitHub issues for relevant keywords",
                        "Review milestone description",
                    ],
                    suggested_tool_calls=[
                        {
                            "tool": "github_fetch_issue",
                            "params": {"query": claim.text[:100]},
                        }
                    ],
                )
                self._emit_intervention(intervention)
                return intervention

        for boundary in boundaries:
            if boundary.type == "empty_metrics":
                intervention = Intervention(
                    type=InterventionType.REQUEST_METRICS,
                    target_id=boundary.section,
                    rationale=boundary.rationale,
                    suggested_next_steps=[
                        "Add measurable success metrics",
                        "Include specific targets (e.g., '95% uptime', '1000 users')",
                    ],
                )
                self._emit_intervention(intervention)
                return intervention

            elif boundary.type == "missing_tradeoffs":
                intervention = Intervention(
                    type=InterventionType.REQUEST_OPTIONS,
                    target_id=boundary.section,
                    rationale=boundary.rationale,
                    suggested_next_steps=[
                        "Explicitly list what's out of scope",
                        "Explain tradeoffs and alternatives considered",
                    ],
                )
                self._emit_intervention(intervention)
                return intervention

        if self.tool_call_count > 50:
            total_evidence = len(self.graph.evidence)
            if total_evidence < 5:
                intervention = Intervention(
                    type=InterventionType.ESCALATE,
                    target_id="tool_call_limit",
                    rationale=f"Agent made {self.tool_call_count} tool calls but only found {total_evidence} evidence items",
                    suggested_next_steps=[
                        "Review agent's tool usage",
                        "Consider if agent is stuck in a loop",
                        "Check if GitHub data is sufficient",
                    ],
                )
                self._emit_intervention(intervention)
                return intervention

        return None

    def _emit_intervention(self, intervention: Intervention):
        self.interventions_issued.append(intervention)
        self.trace_store.append(
            new_event(
                EventType.INTERVENTION,
                {
                    "type": intervention.type.value,
                    "target_id": intervention.target_id,
                    "rationale": intervention.rationale,
                    "suggested_next_steps": intervention.suggested_next_steps,
                    "suggested_tool_calls": intervention.suggested_tool_calls,
                },
            )
        )
