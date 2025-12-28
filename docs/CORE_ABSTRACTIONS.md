# Sentinel Core Abstractions

This document explains the core abstractions and contracts that enable plug-and-play integration with external event loops.

## Architecture Overview

Sentinel uses Protocol-based interfaces (Python's `typing.Protocol`) to define contracts that external systems must implement. This allows for loose coupling and easy integration without requiring inheritance hierarchies.

## Core Protocols

### 1. TraceStore Protocol

**Purpose**: Abstract event storage interface

**Contract**:
```python
class TraceStore(Protocol):
    def append(self, event: Event) -> None
    def iter_events(self) -> Iterator[Event]
    def close(self) -> None
```

**Implementation**: External loops can implement their own storage, or use `JsonlTraceStore` provided by Sentinel.

**Key Points**:
- Events are immutable `Event` objects with type, timestamp, and payload
- `iter_events()` should return all events in chronological order
- Storage can be in-memory, file-based, database, etc.

### 2. EventEmitter Protocol

**Purpose**: Standardized event emission interface

**Contract**:
```python
class EventEmitter(Protocol):
    def emit_llm_call(model, messages, response, metadata=None) -> None
    def emit_tool_call(tool_name, parameters, tool_call_id=None, metadata=None) -> None
    def emit_observation(result, tool_call_id=None, metadata=None) -> None
    def emit_artifact(path, artifact_type="document", name=None, metadata=None) -> None
    def emit_decision(decision_type, payload) -> None
```

**Implementation**: `SentinelEventEmitter` adapts this protocol to emit to a `TraceStore`.

**Key Points**:
- External loops emit events as they occur
- Events are automatically converted to Sentinel's `Event` format
- Metadata is optional and extensible

### 3. EvidenceSource Protocol

**Purpose**: Abstract evidence sources for claim binding

**Contract**:
```python
class EvidenceSource(Protocol):
    def get_evidence_items() -> List[Dict[str, Any]]
```

**Evidence Item Format**:
```python
{
    "text": str,           # Evidence text content
    "source_ref": str,     # Reference (e.g., "issue:123", "doc:abc")
    "source_type": str,    # Type (e.g., "issue", "milestone", "document")
}
```

**Implementation**: 
- `GitHubBundleEvidenceSource` adapts GitHub bundles to this protocol
- External systems can implement custom evidence sources

**Key Points**:
- Decouples evidence binding from GitHub-specific formats
- Allows multiple evidence sources to be combined
- Evidence is matched to claims using keyword overlap

### 4. InterventionHandler Protocol

**Purpose**: Handle supervisor interventions in real-time

**Contract**:
```python
class InterventionHandler(Protocol):
    def handle_intervention(intervention: Intervention, context: Dict) -> Optional[Dict]
```

**Return Value**:
- `None`: Continue normally
- `{"stop": True}`: Escalate immediately
- `{"action": "custom", ...}`: Custom action

**Key Points**:
- Called synchronously when intervention is generated
- Can modify intervention behavior (e.g., escalate)
- Context includes events, artifacts, graph state

## Core Components

### SupervisorHook

**Purpose**: Main integration point for external event loops

**Key Methods**:
- `on_artifact_created(path)`: Register artifacts, extract claims, bind evidence
- `on_step(events, window_size)`: Analyze current state, generate interventions
- `get_summary()`: Get supervision statistics

**State Management**:
- Maintains `EvidenceGraph` for claims and evidence
- Tracks artifacts and interventions
- Manages evidence binding lifecycle

**Integration Pattern**:
```python
hook = SupervisorHook(
    trace_store=my_trace_store,
    intervention_handler=my_handler,
    evidence_source=my_evidence_source,
)

# In event loop:
hook.on_artifact_created(artifact_path)
intervention = hook.on_step()
if intervention:
    # Handle intervention
```

### Supervisor

**Purpose**: Core supervision logic (boundary detection, intervention generation)

**Key Methods**:
- `analyze_step(events, artifacts)`: Analyze and generate interventions

**Dependencies**:
- Uses `TraceStore` protocol (not concrete implementation)
- Analyzes `EvidenceGraph` state
- Detects boundaries using heuristics

**Key Points**:
- Stateless analysis (state in graph and trace)
- Returns `Intervention` or `None`
- Emits intervention events to trace store

## Data Flow

```
External Event Loop
    ↓ (emits events)
EventEmitter → TraceStore
    ↓
SupervisorHook.on_step()
    ↓
Supervisor.analyze_step()
    ↓ (generates)
Intervention
    ↓
InterventionHandler.handle_intervention()
    ↓ (may escalate)
SupervisorHook._handle_escalation()
```

## Evidence Binding Flow

```
Artifact Created
    ↓
SupervisorHook.on_artifact_created()
    ↓
Extract Claims → EvidenceGraph
    ↓
Bind Evidence (from EvidenceSource + Trace Events)
    ↓
EvidenceGraph updated with links
```

## Key Design Principles

1. **Protocol-Based**: Use `Protocol` for interfaces, not ABCs or inheritance
2. **Composition Over Inheritance**: Components compose via protocols
3. **Minimal Coupling**: Core logic doesn't depend on concrete implementations
4. **Extensibility**: New evidence sources, handlers, etc. via protocols
5. **Backward Compatibility**: Legacy bundle format still supported

## Integration Checklist

For external event loops to integrate:

- [ ] Implement or use `TraceStore` for event storage
- [ ] Use `SentinelEventEmitter` or implement `EventEmitter` protocol
- [ ] Emit events at key points (LLM calls, tool calls, observations, artifacts)
- [ ] Create `SupervisorHook` with appropriate handlers
- [ ] Call `hook.on_artifact_created()` when artifacts are generated
- [ ] Call `hook.on_step()` periodically during execution
- [ ] Implement `InterventionHandler` to handle interventions
- [ ] Optionally implement `EvidenceSource` for custom evidence

## Example: Minimal Integration

```python
from sentinel.core import SupervisorHook, SentinelEventEmitter
from sentinel.trace.store_jsonl import JsonlTraceStore

# Setup
trace_store = JsonlTraceStore(Path("events.jsonl"))
emitter = SentinelEventEmitter(trace_store)
hook = SupervisorHook(trace_store)

# In event loop
emitter.emit_llm_call("gpt-4", messages, response)
emitter.emit_tool_call("search", {"query": "..."})
emitter.emit_observation(result)

hook.on_artifact_created(Path("output.md"))
intervention = hook.on_step()

if intervention:
    print(f"Intervention: {intervention.rationale}")
```

