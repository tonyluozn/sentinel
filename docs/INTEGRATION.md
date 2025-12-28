# Sentinel Integration Guide

This guide explains how to integrate Sentinel's supervision capabilities into external LLM event loops, such as HappyRobot (voice agent) or other custom agent systems.

## Overview

Sentinel provides plug-and-play supervision through Protocol-based interfaces and a `SupervisorHook` that can be called at strategic points in your event loop. The integration requires:

1. **Event Emission**: Your event loop emits events (LLM calls, tool calls, observations, artifacts)
2. **Supervisor Hook**: Call the hook periodically to analyze events and generate interventions
3. **Intervention Handling**: Handle interventions when they occur

## Core Interfaces

### TraceStore Protocol

Your event loop needs to provide a trace store that implements the `TraceStore` protocol:

```python
from sentinel.core.interfaces import TraceStore
from sentinel.trace.schema import Event
from typing import Iterator

class MyTraceStore:
    def append(self, event: Event) -> None:
        # Store event
        pass
    
    def iter_events(self) -> Iterator[Event]:
        # Return iterator over events
        pass
    
    def close(self) -> None:
        # Cleanup
        pass
```

Or use Sentinel's built-in `JsonlTraceStore`:

```python
from sentinel.trace.store_jsonl import JsonlTraceStore
from pathlib import Path

trace_store = JsonlTraceStore(Path("events.jsonl"))
```

### EventEmitter Protocol

Emit events using the `EventEmitter` protocol. Sentinel provides `SentinelEventEmitter` that automatically converts to the correct format:

```python
from sentinel.core.adapter import SentinelEventEmitter

emitter = SentinelEventEmitter(trace_store)

# In your event loop:
emitter.emit_llm_call(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    response=llm_response,
)

emitter.emit_tool_call(
    tool_name="search_web",
    parameters={"query": "python"},
    tool_call_id="call_123",
)

emitter.emit_observation(
    result={"results": [...]},
    tool_call_id="call_123",
)

emitter.emit_artifact(
    path="/path/to/output.md",
    artifact_type="document",
    name="output",
)
```

## Integration Pattern

### Basic Integration

```python
from pathlib import Path
from sentinel.core.hook import SupervisorHook
from sentinel.core.adapter import SentinelEventEmitter
from sentinel.trace.store_jsonl import JsonlTraceStore
from sentinel.core.interfaces import InterventionHandler
from sentinel.interventions.types import Intervention

# 1. Set up trace store and emitter
trace_store = JsonlTraceStore(Path("events.jsonl"))
emitter = SentinelEventEmitter(trace_store)

# 2. Create supervisor hook
hook = SupervisorHook(
    trace_store=trace_store,
    bundle=github_bundle,  # Optional: for evidence binding
    run_id="my_run_001",
    packets_dir=Path("packets"),
)

# 3. Implement intervention handler (optional)
class MyInterventionHandler:
    def handle_intervention(
        self, intervention: Intervention, context: dict
    ) -> dict:
        print(f"Intervention: {intervention.type}")
        print(f"Rationale: {intervention.rationale}")
        
        # Return {"stop": True} to escalate, or None to continue
        if intervention.type == InterventionType.ESCALATE:
            return {"stop": True}
        return None

hook.intervention_handler = MyInterventionHandler()

# 4. In your event loop:
def my_event_loop():
    for step in agent_steps:
        # Make LLM call
        response = llm_client.chat.completions.create(...)
        emitter.emit_llm_call("gpt-4", messages, response)
        
        # Execute tool calls
        for tool_call in response.tool_calls:
            emitter.emit_tool_call(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                tool_call.id,
            )
            
            result = execute_tool(tool_call)
            emitter.emit_observation(result, tool_call.id)
        
        # Check for interventions periodically
        intervention = hook.on_step()
        
        if intervention:
            if intervention.type == InterventionType.ESCALATE:
                # Handle escalation
                break
        
        # When artifacts are created
        if artifact_created:
            hook.on_artifact_created(Path(artifact_path))
    
    # Get summary
    summary = hook.get_summary()
    print(f"Events: {summary['event_count']}")
    print(f"Interventions: {summary['intervention_count']}")
```

## HappyRobot Integration Example

Here's a concrete example for integrating with HappyRobot (voice agent):

```python
from sentinel.core.hook import SupervisorHook
from sentinel.core.adapter import SentinelEventEmitter
from sentinel.trace.store_jsonl import JsonlTraceStore
from sentinel.core.interfaces import InterventionHandler
from sentinel.interventions.types import Intervention, InterventionType
from pathlib import Path

class HappyRobotSentinelIntegration:
    def __init__(self, run_id: str):
        # Set up Sentinel
        self.trace_store = JsonlTraceStore(
            Path(f"runs/{run_id}/trace/events.jsonl")
        )
        self.emitter = SentinelEventEmitter(self.trace_store)
        
        self.hook = SupervisorHook(
            trace_store=self.trace_store,
            intervention_handler=HappyRobotInterventionHandler(),
            run_id=run_id,
            packets_dir=Path(f"runs/{run_id}/packets"),
        )
    
    def on_llm_call(self, model: str, messages: list, response):
        """Call this from HappyRobot's LLM call handler."""
        self.emitter.emit_llm_call(model, messages, response)
    
    def on_tool_call(self, tool_name: str, params: dict, tool_id: str = None):
        """Call this from HappyRobot's tool call handler."""
        self.emitter.emit_tool_call(tool_name, params, tool_id)
    
    def on_tool_result(self, result, tool_id: str = None):
        """Call this from HappyRobot's tool result handler."""
        self.emitter.emit_observation(result, tool_id)
    
    def on_artifact_created(self, path: str, artifact_type: str = "audio"):
        """Call this when HappyRobot generates audio or transcripts."""
        self.emitter.emit_artifact(path, artifact_type)
        self.hook.on_artifact_created(Path(path))
    
    def on_step(self):
        """Call this periodically in HappyRobot's event loop."""
        intervention = self.hook.on_step()
        
        if intervention:
            if intervention.type == InterventionType.ESCALATE:
                # Pause voice agent, notify user
                return {"action": "pause", "reason": intervention.rationale}
            elif intervention.type == InterventionType.REQUEST_EVIDENCE:
                # Suggest gathering more information
                return {
                    "action": "suggest",
                    "message": intervention.suggested_next_steps[0],
                }
        
        return None
    
    def get_summary(self):
        """Get supervision summary."""
        return self.hook.get_summary()


class HappyRobotInterventionHandler(InterventionHandler):
    def handle_intervention(
        self, intervention: Intervention, context: dict
    ) -> dict:
        """Handle interventions in HappyRobot context."""
        # For voice agents, we might want to pause on escalation
        if intervention.type == InterventionType.ESCALATE:
            return {"stop": True, "notify_user": True}
        
        # For other interventions, continue but log
        print(f"[Sentinel] {intervention.type}: {intervention.rationale}")
        return None


# Usage in HappyRobot event loop:
def happyrobot_event_loop():
    sentinel = HappyRobotSentinelIntegration(run_id="voice_session_001")
    
    while conversation_active:
        # HappyRobot's normal flow
        user_input = get_user_voice_input()
        
        # LLM call
        response = llm_client.chat.completions.create(...)
        sentinel.on_llm_call("gpt-4", messages, response)
        
        # Tool calls
        for tool_call in response.tool_calls:
            sentinel.on_tool_call(
                tool_call.function.name,
                json.loads(tool_call.function.arguments),
                tool_call.id,
            )
            
            result = execute_tool(tool_call)
            sentinel.on_tool_result(result, tool_call.id)
        
        # Check for interventions
        intervention_action = sentinel.on_step()
        if intervention_action:
            if intervention_action.get("action") == "pause":
                pause_voice_agent()
                notify_user(intervention_action["reason"])
                break
        
        # When audio/transcript is generated
        if audio_file_created:
            sentinel.on_artifact_created(audio_file_path, "audio")
    
    # Get final summary
    summary = sentinel.get_summary()
    print(f"Session completed with {summary['intervention_count']} interventions")
```

## Key Integration Points

### 1. Event Emission

Emit events at these points in your event loop:
- **LLM Calls**: After each LLM API call
- **Tool Calls**: Before executing tools
- **Observations**: After tool execution
- **Artifacts**: When files/documents are created

### 2. Supervisor Hook Calls

Call `hook.on_step()`:
- After each agent step/iteration
- After tool call sequences
- Periodically (e.g., every N events)

### 3. Artifact Registration

Call `hook.on_artifact_created()` when:
- Documents are written
- Code files are generated
- Audio/video files are created
- Any output artifact is produced

### 4. Intervention Handling

Implement `InterventionHandler` to:
- Log interventions
- Pause/stop the agent on escalation
- Inject suggestions into the agent's context
- Notify users

## Intervention Types

- `REQUEST_EVIDENCE`: Agent should gather more evidence for claims
- `REQUEST_METRICS`: Agent should add measurable metrics
- `REQUEST_OPTIONS`: Agent should consider tradeoffs/alternatives
- `REQUEST_RISKS`: Agent should identify risks
- `ESCALATE`: Critical issue - should pause and escalate to human

## Best Practices

1. **Emit events immediately**: Don't batch events, emit them as they happen
2. **Call hook frequently**: Check for interventions every few steps
3. **Handle escalations**: Always handle `ESCALATE` interventions appropriately
4. **Register artifacts early**: Call `on_artifact_created` as soon as artifacts are written
5. **Use summaries**: Call `get_summary()` to monitor supervision state

## Advanced: Custom Evidence Binding

If your event loop has domain-specific evidence sources (beyond GitHub), you can extend the evidence binding:

```python
from sentinel.evidence.graph import EvidenceGraph
from sentinel.evidence.claims import Claim

# Add custom evidence sources
def bind_custom_evidence(claims: list[Claim], custom_data: dict, graph: EvidenceGraph):
    # Your custom evidence binding logic
    pass

# Call after artifact creation
hook.on_artifact_created(artifact_path)
# Then bind custom evidence
bind_custom_evidence(list(hook.graph.claims.values()), custom_data, hook.graph)
```

## Troubleshooting

**Events not being analyzed?**
- Ensure events are being emitted before calling `hook.on_step()`
- Check that `trace_store.iter_events()` returns events

**Interventions not triggering?**
- Verify artifacts are registered with `on_artifact_created()`
- Check that claims are being extracted (artifacts should be markdown/text)

**Performance concerns?**
- Call `hook.on_step()` less frequently (e.g., every 10 steps)
- Limit `window_size` parameter in `on_step()`

