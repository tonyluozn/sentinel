"""Supervisor policy for real-time intervention."""

from pathlib import Path
from typing import Dict, List, Optional

from sentinel.boundaries.detect import BoundaryEvent, detect_boundaries
from sentinel.evidence.graph import EvidenceGraph
from sentinel.interventions.types import Intervention, InterventionType
from sentinel.trace.schema import Event, EventType, new_event
from sentinel.trace.store_jsonl import JsonlTraceStore


class Supervisor:
    """Supervisor that analyzes agent behavior and generates interventions."""

    def __init__(self, graph: EvidenceGraph, trace_store: JsonlTraceStore):
        """Initialize supervisor.

        Args:
            graph: Evidence graph to track claims and evidence.
            trace_store: Trace store for logging decisions and interventions.
        """
        self.graph = graph
        self.trace_store = trace_store
        self.tool_call_count = 0
        self.interventions_issued = []

    def analyze_step(
        self,
        trace_events: List[Event],
        current_artifacts: Dict[str, Path],
    ) -> Optional[Intervention]:
        """Analyze agent step and generate intervention if needed.

        Args:
            trace_events: Recent trace events from agent.
            current_artifacts: Current artifacts (name -> path mapping).

        Returns:
            Intervention if needed, None otherwise.
        """
        # Update tool call count
        for event in trace_events:
            if event.type == "tool_call":
                self.tool_call_count += 1

        # Detect boundaries
        boundaries = detect_boundaries(trace_events, self.graph, current_artifacts)

        # Check for uncovered HIGH claims
        uncovered = self.graph.uncovered_claims(min_severity="HIGH")
        if uncovered:
            if len(uncovered) >= 3:
                # Escalate if too many uncovered
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
                # Request evidence for uncovered claims
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

        # Check boundaries
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

        # Check for too many tool calls without progress
        if self.tool_call_count > 50:
            # Check if we have evidence bindings
            total_evidence = len(self.graph.evidence)
            if total_evidence < 5:  # Very few evidence items
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
        """Emit intervention event to trace.

        Args:
            intervention: Intervention to emit.
        """
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
