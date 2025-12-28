"""
Supervisor hook for real-time integration with external event loops.

This hook allows external event loops to integrate Sentinel's supervision
capabilities by calling the supervisor at strategic points during execution.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sentinel.evidence.bind import bind_evidence
from sentinel.evidence.claims import extract_claims_from_artifact
from sentinel.evidence.graph import EvidenceGraph
from sentinel.interventions.types import Intervention, InterventionType
from sentinel.packets.decision_packet import generate_packet
from sentinel.trace.schema import Event, EventType, new_event

from sentinel.core.interfaces import EvidenceSource, InterventionHandler, TraceStore


class SupervisorHook:
    """
    Hook for integrating Sentinel supervision into external event loops.

    Usage:
        hook = SupervisorHook(trace_store, intervention_handler=my_handler)
        
        # In your event loop, after each step:
        intervention = hook.on_step(events, artifacts)
        
        # Or after artifact creation:
        hook.on_artifact_created(artifact_path)
        
        # Handle intervention if needed:
        if intervention:
            # Act on intervention
    """

    def __init__(
        self,
        trace_store: TraceStore,
        intervention_handler: Optional[InterventionHandler] = None,
        evidence_source: Optional[EvidenceSource] = None,
        bundle: Optional[Dict[str, Any]] = None,
        packets_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
    ):
        """
        Initialize the supervisor hook.

        Args:
            trace_store: Event trace store
            intervention_handler: Optional handler for interventions
            evidence_source: Optional evidence source (preferred over bundle)
            bundle: Optional GitHub bundle for evidence binding (legacy, use evidence_source)
            packets_dir: Optional directory for escalation packets
            run_id: Optional run ID for escalation packets
        """
        # Lazy import to avoid circular dependency
        from sentinel.interventions.policy import Supervisor
        
        self.trace_store = trace_store
        self.intervention_handler = intervention_handler
        self.evidence_source = evidence_source
        self.bundle = bundle or {}
        self.packets_dir = packets_dir
        self.run_id = run_id

        self.graph = EvidenceGraph()
        self.supervisor = Supervisor(self.graph, trace_store)
        self.artifacts: Dict[str, Path] = {}
        self.interventions: List[Intervention] = []

    def on_artifact_created(self, artifact_path: Path, artifact_name: Optional[str] = None) -> None:
        """
        Notify the hook when an artifact is created.

        This triggers claim extraction and evidence binding.

        Args:
            artifact_path: Path to the created artifact
            artifact_name: Optional name for the artifact
        """
        name = artifact_name or artifact_path.stem
        self.artifacts[name] = artifact_path

        # Extract claims from artifact
        claims = extract_claims_from_artifact(artifact_path)
        for claim in claims:
            self.graph.add_claim(claim)

        # Bind evidence
        self._bind_evidence()

    def _bind_evidence(self) -> None:
        """Bind evidence to claims using available sources."""
        if not self.graph.claims:
            return

        all_events = list(self.trace_store.iter_events())

        # Use evidence_source if available, otherwise fall back to bundle
        if self.evidence_source:
            # Convert evidence_source to bundle-like format for bind_evidence
            evidence_items = self.evidence_source.get_evidence_items()
            bundle = {"evidence_items": evidence_items}
        elif self.bundle:
            bundle = self.bundle
        else:
            # No evidence source, only bind from trace events
            bundle = {}

        bind_evidence(
            list(self.graph.claims.values()),
            all_events,
            bundle,
            self.graph,
        )

    def bind_evidence_now(self) -> None:
        """
        Manually trigger evidence binding.

        Useful when evidence sources are updated after artifacts are created.
        """
        self._bind_evidence()

    def on_step(
        self,
        recent_events: Optional[List[Event]] = None,
        window_size: int = 20,
    ) -> Optional[Intervention]:
        """
        Call the supervisor to analyze the current state.

        This should be called periodically during the event loop execution,
        typically after each agent step or tool call.

        Args:
            recent_events: Optional list of recent events to analyze.
                          If None, will fetch from trace_store.
            window_size: Number of recent events to analyze if recent_events is None

        Returns:
            Intervention if one is generated, None otherwise
        """
        # Get recent events if not provided
        if recent_events is None:
            all_events = list(self.trace_store.iter_events())
            recent_events = all_events[-window_size:] if len(all_events) > window_size else all_events

        # Analyze step
        intervention = self.supervisor.analyze_step(recent_events, self.artifacts)

        if intervention:
            self.interventions.append(intervention)

            # Call intervention handler if provided
            if self.intervention_handler:
                context = {
                    "events": recent_events,
                    "artifacts": self.artifacts,
                    "graph": self.graph,
                    "intervention_count": len(self.interventions),
                }
                response = self.intervention_handler.handle_intervention(intervention, context)

                # If handler returns a stop signal, replace with escalation
                if response and response.get("stop", False):
                    # Replace the intervention with an escalation
                    intervention = Intervention(
                        type=InterventionType.ESCALATE,
                        target_id=intervention.target_id,
                        rationale=f"Handler requested escalation: {intervention.rationale}",
                        suggested_next_steps=intervention.suggested_next_steps,
                    )
                    # Update the last intervention in the list
                    self.interventions[-1] = intervention

            # Handle escalation
            if intervention.type == InterventionType.ESCALATE:
                self._handle_escalation(intervention)

        return intervention

    def _handle_escalation(self, intervention: Intervention) -> None:
        """Handle escalation by generating a packet."""
        if not self.packets_dir or not self.run_id:
            return

        self.packets_dir.mkdir(parents=True, exist_ok=True)

        context = {
            "issue_count": len(self.bundle.get("issues", [])) if self.bundle else 0,
        }

        generate_packet(
            self.run_id,
            context,
            [intervention],
            self.graph,
            self.packets_dir,
            self.trace_store,
        )

        self.trace_store.append(
            new_event(
                EventType.DECISION,
                {
                    "type": "escalation",
                    "run_id": self.run_id,
                    "intervention_count": len(self.interventions),
                },
            )
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current supervision state.

        Returns:
            Dictionary with summary statistics
        """
        all_events = list(self.trace_store.iter_events())
        uncovered_high = self.graph.uncovered_claims(min_severity="HIGH")
        uncovered_medium = self.graph.uncovered_claims(min_severity="MEDIUM")

        return {
            "event_count": len(all_events),
            "artifact_count": len(self.artifacts),
            "intervention_count": len(self.interventions),
            "uncovered_high_claims": len(uncovered_high),
            "uncovered_medium_claims": len(uncovered_medium),
            "total_claims": len(self.graph.claims),
            "total_evidence": len(self.graph.evidence),
        }

