"""
Protocol-based interfaces for Sentinel integration.

These protocols define the contracts that external event loops must implement
to integrate with Sentinel's supervision system.
"""

from typing import Any, Dict, Iterator, List, Optional, Protocol

from sentinel.interventions.types import Intervention
from sentinel.trace.schema import Event


class TraceStore(Protocol):
    """
    Protocol for event storage.

    External event loops can implement this interface to provide their own
    event storage mechanism, or use Sentinel's JsonlTraceStore.
    """

    def append(self, event: Event) -> None:
        """Append an event to the store."""
        ...

    def iter_events(self) -> Iterator[Event]:
        """Iterate over all events in the store."""
        ...

    def close(self) -> None:
        """Close the store and release resources."""
        ...


class EventEmitter(Protocol):
    """
    Protocol for emitting events from external event loops.

    External loops should emit events using this interface so Sentinel can
    monitor agent behavior in real-time.
    """

    def emit_llm_call(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        response: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an LLM call event.

        Args:
            model: Model identifier (e.g., "gpt-4", "claude-3")
            messages: Conversation messages sent to the LLM
            response: LLM response object
            metadata: Optional metadata (tokens, latency, etc.)
        """
        ...

    def emit_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a tool call event.

        Args:
            tool_name: Name of the tool being called
            parameters: Tool call parameters
            tool_call_id: Optional tool call identifier
            metadata: Optional metadata
        """
        ...

    def emit_observation(
        self,
        result: Any,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an observation event (tool result).

        Args:
            result: Tool execution result
            tool_call_id: Optional tool call identifier this observation relates to
            metadata: Optional metadata
        """
        ...

    def emit_artifact(
        self,
        path: str,
        artifact_type: str = "document",
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an artifact creation event.

        Args:
            path: Path to the artifact file
            artifact_type: Type of artifact (e.g., "document", "code", "audio")
            name: Optional artifact name
            metadata: Optional metadata
        """
        ...

    def emit_decision(
        self,
        decision_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Emit a decision event.

        Args:
            decision_type: Type of decision (e.g., "run_start", "escalation")
            payload: Decision payload
        """
        ...


class LLMClient(Protocol):
    """
    Protocol for LLM clients.

    External loops can provide their own LLM client implementation, or use
    Sentinel's default OpenAI client.
    """

    def chat_completions_create(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Create a chat completion.

        Args:
            model: Model identifier
            messages: Conversation messages
            tools: Optional tool definitions
            tool_choice: Optional tool choice strategy
            **kwargs: Additional parameters

        Returns:
            Response object with choices, usage, etc.
        """
        ...


class InterventionHandler(Protocol):
    """
    Protocol for handling interventions from the supervisor.

    External event loops should implement this to receive and act on
    supervisor interventions in real-time.
    """

    def handle_intervention(
        self,
        intervention: Intervention,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an intervention from the supervisor.

        Args:
            intervention: The intervention object
            context: Additional context (events, artifacts, etc.)

        Returns:
            Optional response dict with:
            - "stop": bool - If True, escalate immediately
            - "action": str - Custom action identifier
            - Any other custom fields
            None to continue normally
        """
        ...


class EvidenceSource(Protocol):
    """
    Protocol for evidence sources.

    Allows external systems to provide evidence in a generic format
    instead of being tied to GitHub bundle structure.
    """

    def get_evidence_items(self) -> List[Dict[str, Any]]:
        """
        Get evidence items for binding to claims.

        Returns:
            List of evidence dicts with:
            - "text": str - Evidence text content
            - "source_ref": str - Reference to source (e.g., "issue:123")
            - "source_type": str - Type of source (e.g., "issue", "milestone")
        """
        ...

