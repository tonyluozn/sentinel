"""
Event adapters for converting external event formats to Sentinel events.

These utilities help external event loops convert their native event formats
to Sentinel's Event schema.
"""

from typing import Any, Dict, List, Optional

from sentinel.trace.schema import Event, EventType, new_event

from sentinel.core.interfaces import EventEmitter, TraceStore


class SentinelEventEmitter:
    """
    Adapter that implements EventEmitter protocol and emits to a TraceStore.

    This allows external event loops to use the EventEmitter interface
    while automatically converting to Sentinel's Event format.
    """

    def __init__(self, trace_store: TraceStore):
        """
        Initialize the event emitter.

        Args:
            trace_store: Trace store to emit events to
        """
        self.trace_store = trace_store

    def emit_llm_call(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an LLM call event."""
        payload: Dict[str, Any] = {
            "model": model,
        }

        # Extract token usage if available
        if hasattr(response, "usage"):
            if hasattr(response.usage, "prompt_tokens"):
                payload["prompt_tokens"] = response.usage.prompt_tokens
            if hasattr(response.usage, "completion_tokens"):
                payload["completion_tokens"] = response.usage.completion_tokens
            if hasattr(response.usage, "total_tokens"):
                payload["total_tokens"] = response.usage.total_tokens

        # Add metadata
        if metadata:
            payload.update(metadata)

        self.trace_store.append(new_event(EventType.LLM_CALL, payload))

    def emit_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a tool call event."""
        payload: Dict[str, Any] = {
            "tool": tool_name,
            "parameters": parameters,
        }

        if tool_call_id:
            payload["tool_call_id"] = tool_call_id

        if metadata:
            payload.update(metadata)

        self.trace_store.append(new_event(EventType.TOOL_CALL, payload))

    def emit_observation(
        self,
        result: Any,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an observation event."""
        payload: Dict[str, Any] = {}

        # Convert result to dict if it's not already
        if isinstance(result, dict):
            payload["result"] = result
        elif isinstance(result, str):
            payload["result"] = {"content": result}
        else:
            payload["result"] = {"value": str(result)}

        if tool_call_id:
            payload["tool_call_id"] = tool_call_id

        if metadata:
            payload.update(metadata)

        self.trace_store.append(new_event(EventType.OBSERVATION, payload))

    def emit_artifact(
        self,
        path: str,
        artifact_type: str = "document",
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an artifact event."""
        payload: Dict[str, Any] = {
            "path": path,
            "type": artifact_type,
        }

        if name:
            payload["name"] = name

        if metadata:
            payload.update(metadata)

        self.trace_store.append(new_event(EventType.ARTIFACT, payload))

    def emit_decision(
        self,
        decision_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Emit a decision event."""
        payload_dict = {"type": decision_type, **payload}
        self.trace_store.append(new_event(EventType.DECISION, payload_dict))


def create_event_from_dict(event_dict: Dict[str, Any]) -> Event:
    """
    Create a Sentinel Event from a dictionary.

    This is useful for converting external event formats to Sentinel events.

    Args:
        event_dict: Dictionary with event data. Should have:
                   - type: Event type (string or EventType)
                   - ts: Optional timestamp (ISO 8601 string)
                   - payload: Event payload dictionary

    Returns:
        Sentinel Event object
    """
    event_type_str = event_dict.get("type")
    if isinstance(event_type_str, str):
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            # Fallback to OBSERVATION for unknown types
            event_type = EventType.OBSERVATION
    else:
        event_type = event_type_str

    payload = event_dict.get("payload", event_dict)
    ts = event_dict.get("ts")

    if ts:
        return Event(type=event_type, ts=ts, payload=payload)
    else:
        return new_event(event_type, payload)

