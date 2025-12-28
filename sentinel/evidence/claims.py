"""Claim extraction from artifacts and trace events."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from sentinel.trace.schema import Event


@dataclass
class Claim:
    """A claim extracted from an artifact."""

    id: str
    text: str
    section: str
    severity: str  # HIGH, MEDIUM, LOW
    source_line: int
    artifact_path: str


def extract_claims_from_artifact(artifact_path: Path) -> List[Claim]:
    """Extract claims from a markdown artifact.

    Args:
        artifact_path: Path to markdown file.

    Returns:
        List of extracted claims.
    """
    if not artifact_path.exists():
        return []

    with open(artifact_path, "r", encoding="utf-8") as f:
        content = f.read()

    claims = []
    current_section = None
    claim_counter = 0

    # Section patterns
    section_patterns = {
        "Goals": r"^#+\s*(?:Goals?|Objectives?)",
        "Non-goals": r"^#+\s*(?:Non-?goals?|Out of Scope)",
        "Scope": r"^#+\s*Scope",
        "Metrics": r"^#+\s*(?:Metrics?|Success Metrics?)",
        "Risks": r"^#+\s*(?:Risks?|Risk Assessment)",
        "Rollout": r"^#+\s*(?:Rollout|Launch Plan|Deployment)",
    }

    for line_num, line in enumerate(content.split("\n"), 1):
        # Check for section headers
        for section_name, pattern in section_patterns.items():
            if re.match(pattern, line, re.IGNORECASE):
                current_section = section_name
                break

        # Extract sentences from sections
        if current_section:
            # Simple sentence extraction (split on periods, exclamation, question marks)
            sentences = re.split(r"[.!?]+\s+", line.strip())
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:  # Filter out very short fragments
                    claim_counter += 1
                    claim_id = f"{artifact_path.stem}_claim_{claim_counter}"

                    # Assign severity based on section
                    if current_section in ["Goals", "Scope", "Metrics", "Rollout"]:
                        severity = "HIGH"
                    elif current_section == "Risks":
                        severity = "MEDIUM"
                    else:
                        severity = "LOW"

                    claims.append(
                        Claim(
                            id=claim_id,
                            text=sentence,
                            section=current_section,
                            severity=severity,
                            source_line=line_num,
                            artifact_path=str(artifact_path),
                        )
                    )

    return claims


def extract_claims_from_trace(trace_events: List[Event]) -> List[Claim]:
    """Extract claims from trace events (artifact events).

    Args:
        trace_events: List of trace events.

    Returns:
        List of extracted claims.
    """
    claims = []
    for event in trace_events:
        if event.type == "artifact":
            artifact_path = event.payload.get("path")
            if artifact_path:
                path = Path(artifact_path)
                if path.exists():
                    artifact_claims = extract_claims_from_artifact(path)
                    claims.extend(artifact_claims)
    return claims
