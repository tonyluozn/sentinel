"""Evidence graph for tracking claims and evidence."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Evidence:
    """Evidence supporting a claim."""

    id: str
    snippet: str
    source_ref: str
    source_type: str  # "issue", "milestone", "tool_call", etc.


@dataclass
class Edge:
    """Edge in the evidence graph."""

    type: str  # "supports", "contradicts", etc.
    from_id: str
    to_id: str


@dataclass
class Claim:
    """A claim (re-exported from claims.py for convenience)."""

    id: str
    text: str
    section: str
    severity: str
    source_line: int
    artifact_path: str


class EvidenceGraph:
    """In-memory graph tracking claims, evidence, and their relationships."""

    def __init__(self):
        """Initialize empty evidence graph."""
        self.claims: Dict[str, Claim] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.edges: List[Edge] = []

    def add_claim(self, claim: Claim):
        """Add a claim to the graph.

        Args:
            claim: Claim to add.
        """
        self.claims[claim.id] = claim

    def add_evidence(self, evidence: Evidence):
        """Add evidence to the graph.

        Args:
            evidence: Evidence to add.
        """
        self.evidence[evidence.id] = evidence

    def link_support(self, claim_id: str, evidence_id: str):
        """Link evidence to support a claim.

        Args:
            claim_id: ID of the claim.
            evidence_id: ID of the evidence.
        """
        if claim_id not in self.claims:
            return
        if evidence_id not in self.evidence:
            return

        # Check if edge already exists
        for edge in self.edges:
            if (
                edge.type == "supports"
                and edge.from_id == evidence_id
                and edge.to_id == claim_id
            ):
                return

        self.edges.append(Edge(type="supports", from_id=evidence_id, to_id=claim_id))

    def uncovered_claims(self, min_severity: str = "HIGH") -> List[Claim]:
        """Get claims with no supporting evidence.

        Args:
            min_severity: Minimum severity level (HIGH, MEDIUM, LOW).

        Returns:
            List of uncovered claims.
        """
        severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_level = severity_order.get(min_severity, 1)

        uncovered = []
        for claim in self.claims.values():
            claim_level = severity_order.get(claim.severity, 0)
            if claim_level < min_level:
                continue

            # Check if claim has supporting evidence
            has_evidence = False
            for edge in self.edges:
                if edge.type == "supports" and edge.to_id == claim.id:
                    has_evidence = True
                    break

            if not has_evidence:
                uncovered.append(claim)

        return uncovered
