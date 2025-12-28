"""Evidence binding - match claims with evidence from bundle and trace."""

import re
from typing import Dict, List

from sentinel.evidence.claims import Claim
from sentinel.evidence.graph import Evidence, EvidenceGraph
from sentinel.trace.schema import Event


def _extract_keywords(text: str) -> set:
    """Extract keywords from text for matching.

    Args:
        text: Text to extract keywords from.

    Returns:
        Set of keywords (lowercased, non-stopwords).
    """
    # Simple stopwords
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "can",
    }

    # Extract words
    words = re.findall(r"\b\w+\b", text.lower())
    keywords = {w for w in words if len(w) > 2 and w not in stopwords}
    return keywords


def _keyword_overlap(text1: str, text2: str) -> float:
    """Calculate keyword overlap between two texts.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Overlap score (0.0 to 1.0).
    """
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
    """Bind evidence to claims from bundle and trace events.

    Args:
        claims: List of claims to bind evidence for.
        trace_events: Trace events (may contain tool call results).
        bundle: GitHub bundle with issues and milestone data.
        graph: Evidence graph to update.

    Returns:
        List of evidence objects created.
    """
    evidence_list = []

    # Collect evidence sources
    evidence_sources = []

    # From bundle: issues
    for issue in bundle.get("issues", []):
        evidence_sources.append(
            {
                "text": f"{issue.get('title', '')} {issue.get('body', '')}",
                "source_ref": f"issue:{issue.get('number')}",
                "source_type": "issue",
            }
        )

    # From bundle: milestone
    milestone = bundle.get("milestone", {})
    if milestone.get("description"):
        evidence_sources.append(
            {
                "text": milestone["description"],
                "source_ref": f"milestone:{milestone.get('number')}",
                "source_type": "milestone",
            }
        )

    # From trace: tool call results
    for event in trace_events:
        if event.type == "observation":
            result = event.payload.get("result") or event.payload.get("data")
            if result and isinstance(result, dict):
                # Extract text from result
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

    # Match claims to evidence
    evidence_counter = 0
    for claim in claims:
        best_match = None
        best_score = 0.0

        for source in evidence_sources:
            score = _keyword_overlap(claim.text, source["text"])
            if score > best_score and score > 0.2:  # Threshold for matching
                best_score = score
                best_match = source

        if best_match:
            evidence_counter += 1
            evidence_id = f"evidence_{evidence_counter}"
            snippet = best_match["text"][:200]  # Truncate for snippet

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
