from dataclasses import dataclass
from typing import Dict, List

from sentinel.evidence.claims import Claim


@dataclass
class Evidence:
    id: str
    snippet: str
    source_ref: str
    source_type: str


@dataclass
class Edge:
    type: str
    from_id: str
    to_id: str


class EvidenceGraph:
    def __init__(self):
        self.claims: Dict[str, Claim] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.edges: List[Edge] = []

    def add_claim(self, claim: Claim):
        self.claims[claim.id] = claim

    def add_evidence(self, evidence: Evidence):
        self.evidence[evidence.id] = evidence

    def link_support(self, claim_id: str, evidence_id: str):
        if claim_id not in self.claims:
            return
        if evidence_id not in self.evidence:
            return

        for edge in self.edges:
            if (
                edge.type == "supports"
                and edge.from_id == evidence_id
                and edge.to_id == claim_id
            ):
                return

        self.edges.append(Edge(type="supports", from_id=evidence_id, to_id=claim_id))

    def uncovered_claims(self, min_severity: str = "HIGH") -> List[Claim]:
        severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_level = severity_order.get(min_severity, 1)

        uncovered = []
        for claim in self.claims.values():
            claim_level = severity_order.get(claim.severity, 0)
            if claim_level < min_level:
                continue

            has_evidence = False
            for edge in self.edges:
                if edge.type == "supports" and edge.to_id == claim.id:
                    has_evidence = True
                    break

            if not has_evidence:
                uncovered.append(claim)

        return uncovered
