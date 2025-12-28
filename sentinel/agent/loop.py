from pathlib import Path
from typing import Dict

from sentinel.agent.prd_writer import PRDAgent
from sentinel.evidence.bind import bind_evidence
from sentinel.evidence.claims import extract_claims_from_artifact
from sentinel.evidence.graph import EvidenceGraph
from sentinel.github.cache import FileCache
from sentinel.github.client import GitHubClient
from sentinel.github.fetch import fetch_repo_milestone_bundle
from sentinel.interventions.policy import Supervisor
from sentinel.interventions.types import InterventionType
from sentinel.packets.decision_packet import generate_packet
from sentinel.report.render_md import generate_report
from sentinel.trace.schema import EventType, new_event
from sentinel.trace.store_jsonl import JsonlTraceStore


def run_agent_with_supervisor(
    repo: str,
    milestone: str,
    run_id: str,
    trace_store: JsonlTraceStore,
    supervisor: Supervisor,
    llm_client=None,
) -> Dict:
    from sentinel.config import get_runs_dir

    runs_dir = get_runs_dir()
    run_dir = runs_dir / run_id
    artifacts_dir = run_dir / "artifacts"
    packets_dir = run_dir / "packets"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    packets_dir.mkdir(parents=True, exist_ok=True)

    trace_store.append(
        new_event(
            EventType.DECISION,
            {
                "type": "run_start",
                "repo": repo,
                "milestone": milestone,
                "run_id": run_id,
            },
        )
    )

    cache = FileCache()
    client = GitHubClient()
    bundle = fetch_repo_milestone_bundle(repo, milestone, cache, client, trace_store)

    graph = EvidenceGraph()
    agent = PRDAgent(bundle, artifacts_dir, trace_store, llm_client=llm_client)
    current_artifacts = {}

    try:
        artifacts = agent.run()

        for name, path in artifacts.items():
            current_artifacts[name] = path

        all_events = list(trace_store.iter_events())

        for artifact_path in artifacts.values():
            claims = extract_claims_from_artifact(artifact_path)
            for claim in claims:
                graph.add_claim(claim)

        bind_evidence(list(graph.claims.values()), all_events, bundle, graph)

        interventions = []
        recent_events = all_events[-20:] if len(all_events) > 20 else all_events
        intervention = supervisor.analyze_step(recent_events, current_artifacts)

        if intervention:
            interventions.append(intervention)

            if intervention.type == InterventionType.ESCALATE:
                context = {
                    "repo": repo,
                    "milestone": milestone,
                    "issue_count": len(bundle.get("issues", [])),
                }
                generate_packet(run_id, context, interventions, graph, packets_dir, trace_store)

                trace_store.append(
                    new_event(
                        EventType.DECISION,
                        {
                            "type": "escalation",
                            "run_id": run_id,
                            "intervention_count": len(interventions),
                        },
                    )
                )

    except Exception as e:
        trace_store.append(
            new_event(
                EventType.OBSERVATION,
                {
                    "error": str(e),
                    "type": "agent_error",
                },
            )
        )
        raise

    report_path = generate_report(run_id, trace_store, artifacts_dir, packets_dir, graph)

    all_events_final = list(trace_store.iter_events())
    return {
        "run_id": run_id,
        "artifacts": {name: str(path) for name, path in artifacts.items()},
        "report_path": str(report_path),
        "packets_dir": str(packets_dir),
        "trace_path": str(trace_store.path),
        "event_count": len(all_events_final),
        "intervention_count": len(interventions),
        "uncovered_claims": len(graph.uncovered_claims(min_severity="HIGH")),
    }
