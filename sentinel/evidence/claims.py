import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from sentinel.trace.schema import Event


@dataclass
class Claim:
    id: str
    text: str
    section: str
    severity: str
    source_line: int
    artifact_path: str


def extract_claims_from_artifact(artifact_path: Path) -> List[Claim]:
    if not artifact_path.exists():
        return []

    with open(artifact_path, "r", encoding="utf-8") as f:
        content = f.read()

    claims = []
    current_section = None
    claim_counter = 0

    section_patterns = {
        "Goals": r"^#+\s*(?:Goals?|Objectives?)",
        "Non-goals": r"^#+\s*(?:Non-?goals?|Out of Scope)",
        "Scope": r"^#+\s*Scope",
        "Metrics": r"^#+\s*(?:Metrics?|Success Metrics?)",
        "Risks": r"^#+\s*(?:Risks?|Risk Assessment)",
        "Rollout": r"^#+\s*(?:Rollout|Launch Plan|Deployment)",
    }

    for line_num, line in enumerate(content.split("\n"), 1):
        for section_name, pattern in section_patterns.items():
            if re.match(pattern, line, re.IGNORECASE):
                current_section = section_name
                break

        if current_section:
            sentences = re.split(r"[.!?]+\s+", line.strip())
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20:
                    claim_counter += 1
                    claim_id = f"{artifact_path.stem}_claim_{claim_counter}"

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
