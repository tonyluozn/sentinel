from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class InterventionType(str, Enum):
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    REQUEST_OPTIONS = "REQUEST_OPTIONS"
    REQUEST_RISKS = "REQUEST_RISKS"
    REQUEST_METRICS = "REQUEST_METRICS"
    ESCALATE = "ESCALATE"


@dataclass
class Intervention:
    type: InterventionType
    target_id: str
    rationale: str
    suggested_next_steps: List[str] = field(default_factory=list)
    suggested_tool_calls: List[Dict] = field(default_factory=list)
