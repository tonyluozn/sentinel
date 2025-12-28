"""Event schema for trace logging."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types in the trace system."""

    TOOL_CALL = "tool_call"
    OBSERVATION = "observation"
    ARTIFACT = "artifact"
    DECISION = "decision"
    INTERVENTION = "intervention"
    ESCALATION_PACKET = "escalation_packet"
    LLM_CALL = "llm_call"


class Event(BaseModel):
    """A trace event."""

    type: EventType = Field(..., description="Event type")
    ts: str = Field(..., description="ISO 8601 timestamp")
    payload: Dict[str, Any] = Field(..., description="Event payload")

    class Config:
        use_enum_values = True


def now_iso() -> str:
    """Return current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def new_event(event_type: EventType, payload: Dict[str, Any]) -> Event:
    """Create a new event with current timestamp."""
    return Event(type=event_type, ts=now_iso(), payload=payload)
