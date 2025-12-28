import re
from typing import Dict, List

from sentinel.evidence.claims import Claim
from sentinel.evidence.graph import Evidence, EvidenceGraph
from sentinel.trace.schema import Event


def _extract_keywords(text: str) -> set:
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "is", "are", "was", "were", "be", "been", "have", "has",
        "had", "do", "does", "did", "will", "would", "should", "could", "may",
        "might", "must", "can",
    }

    words = re.findall(r"\b\w+\b", text.lower())
    keywords = {w for w in words if len(w) > 2 and w not in stopwords}
    return keywords


def _keyword_overlap(text1: str, text2: str) -> float:
    keywords1 = _extract_keywords(text1)
    keywords2 = _extract_keywords(text2)

    if not keywords1 or not keywords2:
        return 0.0

    intersection = keywords1 & keywords2
    union = keywords1 | keywords2

    if not union:
        return 0.0

    return len(intersection) / len(union)


def bind_evidence(
    claims: List[Claim],
    trace_events: List[Event],
    bundle: Dict,
    graph: EvidenceGraph,
) -> List[Evidence]:
    evidence_list = []
    evidence_sources = []

    # Support new evidence_items format (from EvidenceSource protocol)
    if "evidence_items" in bundle:
        evidence_sources.extend(bundle["evidence_items"])
    else:
        # Legacy GitHub bundle format
        for issue in bundle.get("issues", []):
            evidence_sources.append(
                {
                    "text": f"{issue.get('title', '')} {issue.get('body', '')}",
                    "source_ref": f"issue:{issue.get('number')}",
                    "source_type": "issue",
                }
            )

        milestone = bundle.get("milestone", {})
        if milestone.get("description"):
            evidence_sources.append(
                {
                    "text": milestone["description"],
                    "source_ref": f"milestone:{milestone.get('number')}",
                    "source_type": "milestone",
                }
            )

    for event in trace_events:
        if event.type == "observation":
            result = event.payload.get("result") or event.payload.get("data")
            if result and isinstance(result, dict):
                text_parts = []
                if "title" in result:
                    text_parts.append(str(result["title"]))
                if "body" in result:
                    text_parts.append(str(result["body"]))
                if text_parts:
                    evidence_sources.append(
                        {
                            "text": " ".join(text_parts),
                            "source_ref": f"trace:{event.ts}",
                            "source_type": "tool_call",
                        }
                    )

    evidence_counter = 0
    for claim in claims:
        best_match = None
        best_score = 0.0

        for source in evidence_sources:
            score = _keyword_overlap(claim.text, source["text"])
            if score > best_score and score > 0.2:
                best_score = score
                best_match = source

        if best_match:
            evidence_counter += 1
            evidence_id = f"evidence_{evidence_counter}"
            snippet = best_match["text"][:200]

            evidence = Evidence(
                id=evidence_id,
                snippet=snippet,
                source_ref=best_match["source_ref"],
                source_type=best_match["source_type"],
            )

            graph.add_evidence(evidence)
            graph.link_support(claim.id, evidence_id)
            evidence_list.append(evidence)

    return evidence_list
