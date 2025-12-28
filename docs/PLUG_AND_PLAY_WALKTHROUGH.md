# Sentinel Plug-and-Play: Core Logic Walkthrough

This document walks through how Sentinel achieves plug-and-play integration and explains the core logic flow.

## 🎯 The Goal: Plug-and-Play Integration

**Problem**: How do we make Sentinel work with ANY LLM event loop (HappyRobot, custom agents, etc.) without requiring them to change their architecture?

**Solution**: Protocol-based interfaces + a simple hook pattern that external loops call at strategic points.

---

## 🏗️ Architecture: Protocol-Based Design

### Why Protocols?

Python's `typing.Protocol` allows **structural typing** - if your class has the right methods, it automatically implements the protocol. No inheritance needed!

```python
# External loop just needs to have these methods - no base class required!
class MyTraceStore:
    def append(self, event: Event) -> None: ...
    def iter_events(self) -> Iterator[Event]: ...
    def close(self) -> None: ...
```

This is **duck typing with type safety** - "if it walks like a duck and quacks like a duck, it's a duck."

---

## 🔄 Core Logic Flow

### Step 1: Event Emission (External Loop → Sentinel)

```
External Event Loop
    ↓
emitter.emit_llm_call(...)
emitter.emit_tool_call(...)
emitter.emit_observation(...)
    ↓
SentinelEventEmitter (adapter)
    ↓
Converts to Sentinel Event format
    ↓
trace_store.append(event)
```

**Key Point**: External loops don't need to know Sentinel's Event format. `SentinelEventEmitter` handles conversion.

**Example**:
```python
# HappyRobot's event loop
response = llm_client.chat.completions.create(...)
emitter.emit_llm_call("gpt-4", messages, response)
# ↑ This automatically converts to Sentinel's Event format
```

### Step 2: Artifact Registration

```
External Loop creates artifact (e.g., PRD.md)
    ↓
hook.on_artifact_created(Path("PRD.md"))
    ↓
1. Extract claims from markdown
2. Add claims to EvidenceGraph
3. Bind evidence to claims
```

**Logic in `on_artifact_created()`**:
```python
def on_artifact_created(self, artifact_path: Path):
    # 1. Register artifact
    self.artifacts[name] = artifact_path
    
    # 2. Extract claims (e.g., "Goal: Increase user engagement by 20%")
    claims = extract_claims_from_artifact(artifact_path)
    for claim in claims:
        self.graph.add_claim(claim)  # Add to evidence graph
    
    # 3. Bind evidence (match claims to evidence sources)
    self._bind_evidence()
```

**Evidence Binding Logic**:
```python
def _bind_evidence(self):
    # Get all events from trace
    all_events = list(self.trace_store.iter_events())
    
    # Get evidence from EvidenceSource protocol (or legacy bundle)
    if self.evidence_source:
        evidence_items = self.evidence_source.get_evidence_items()
        bundle = {"evidence_items": evidence_items}
    else:
        bundle = self.bundle  # Legacy GitHub bundle
    
    # Match claims to evidence using keyword overlap
    bind_evidence(claims, all_events, bundle, self.graph)
```

**Key Point**: Evidence binding is **decoupled** from GitHub. External loops can provide evidence via `EvidenceSource` protocol.

### Step 3: Supervision Analysis

```
External Loop calls hook.on_step()
    ↓
SupervisorHook.on_step()
    ↓
1. Get recent events from trace_store
2. Call Supervisor.analyze_step(events, artifacts)
    ↓
Supervisor analyzes:
  - Uncovered claims (claims without evidence)
  - Boundary violations (empty metrics, missing tradeoffs)
  - Tool call efficiency
    ↓
Returns Intervention or None
```

**Supervisor Analysis Logic** (`Supervisor.analyze_step()`):

```python
def analyze_step(self, events, artifacts):
    # 1. Count tool calls
    for event in events:
        if event.type == "tool_call":
            self.tool_call_count += 1
    
    # 2. Detect boundaries (heuristics)
    boundaries = detect_boundaries(events, self.graph, artifacts)
    
    # 3. Check for uncovered HIGH severity claims
    uncovered = self.graph.uncovered_claims(min_severity="HIGH")
    if uncovered:
        if len(uncovered) >= 3:
            return Intervention(type=ESCALATE, ...)  # Too many uncovered
        else:
            return Intervention(type=REQUEST_EVIDENCE, ...)  # Need evidence
    
    # 4. Check boundary violations
    for boundary in boundaries:
        if boundary.type == "empty_metrics":
            return Intervention(type=REQUEST_METRICS, ...)
        elif boundary.type == "missing_tradeoffs":
            return Intervention(type=REQUEST_OPTIONS, ...)
    
    # 5. Check tool call efficiency
    if self.tool_call_count > 50 and evidence_count < 5:
        return Intervention(type=ESCALATE, ...)  # Inefficient tool usage
    
    return None  # No intervention needed
```

### Step 4: Intervention Handling

```
Supervisor returns Intervention
    ↓
hook.on_step() receives intervention
    ↓
1. Add to interventions list
2. Call intervention_handler.handle_intervention() if provided
3. If handler returns {"stop": True}, escalate
4. If intervention.type == ESCALATE, generate packet
    ↓
Return intervention to external loop
```

**Intervention Handler Logic**:
```python
if intervention:
    self.interventions.append(intervention)
    
    # Call external handler (e.g., HappyRobot's handler)
    if self.intervention_handler:
        response = self.intervention_handler.handle_intervention(
            intervention, 
            context={"events": events, "artifacts": artifacts, ...}
        )
        
        # Handler can request escalation
        if response and response.get("stop", False):
            intervention = Intervention(type=ESCALATE, ...)
    
    # Auto-escalate if needed
    if intervention.type == ESCALATE:
        self._handle_escalation(intervention)  # Generate packet
```

**Key Point**: External loops can **customize intervention behavior** via `InterventionHandler` protocol.

---

## 🔌 How Plug-and-Play Works

### 1. **Protocol-Based Contracts**

External loops implement protocols (not inherit classes):

```python
# HappyRobot implements TraceStore protocol
class HappyRobotTraceStore:
    def append(self, event: Event) -> None:
        # Store in HappyRobot's database
        self.db.save(event)
    
    def iter_events(self) -> Iterator[Event]:
        return self.db.get_all_events()
    
    def close(self) -> None:
        self.db.close()

# Sentinel accepts it because it has the right methods!
hook = SupervisorHook(trace_store=HappyRobotTraceStore())
```

### 2. **Adapter Pattern**

`SentinelEventEmitter` adapts external events to Sentinel format:

```python
# External loop doesn't need to know Sentinel's Event format
emitter = SentinelEventEmitter(trace_store)

# Just call the protocol methods
emitter.emit_llm_call("gpt-4", messages, response)
# ↑ Internally converts to: Event(type=LLM_CALL, payload={...})
```

### 3. **Hook Pattern**

External loops call the hook at strategic points - **no tight coupling**:

```python
# In HappyRobot's event loop
while conversation_active:
    # HappyRobot's normal flow
    response = llm_client.chat.completions.create(...)
    emitter.emit_llm_call("gpt-4", messages, response)
    
    # Call hook periodically
    intervention = hook.on_step()
    
    if intervention:
        if intervention.type == ESCALATE:
            pause_voice_agent()
            break
```

**Key Point**: External loop controls **when** to call the hook. Sentinel doesn't control the loop.

### 4. **Evidence Source Abstraction**

Evidence binding is decoupled from GitHub:

```python
# HappyRobot can provide its own evidence
class HappyRobotEvidenceSource:
    def get_evidence_items(self):
        return [
            {"text": "User said: I want voice commands", 
             "source_ref": "conversation:123",
             "source_type": "conversation"},
            {"text": "Previous session notes...",
             "source_ref": "session:456",
             "source_type": "session"},
        ]

hook = SupervisorHook(
    trace_store=trace_store,
    evidence_source=HappyRobotEvidenceSource()
)
```

---

## 📊 Complete Flow Example

### HappyRobot Integration

```python
# 1. Setup
from sentinel.core import SupervisorHook, SentinelEventEmitter
from sentinel.trace.store_jsonl import JsonlTraceStore

trace_store = JsonlTraceStore(Path("events.jsonl"))
emitter = SentinelEventEmitter(trace_store)

class HappyRobotHandler:
    def handle_intervention(self, intervention, context):
        if intervention.type == ESCALATE:
            return {"stop": True, "notify_user": True}
        return None

hook = SupervisorHook(
    trace_store=trace_store,
    intervention_handler=HappyRobotHandler(),
    evidence_source=HappyRobotEvidenceSource(),
)

# 2. In HappyRobot's event loop
def happyrobot_loop():
    while active:
        # Step 1: LLM call
        response = llm_client.chat.completions.create(...)
        emitter.emit_llm_call("gpt-4", messages, response)
        
        # Step 2: Tool calls
        for tool_call in response.tool_calls:
            emitter.emit_tool_call(tool_call.name, tool_call.params)
            result = execute_tool(tool_call)
            emitter.emit_observation(result)
        
        # Step 3: Artifact creation
        if audio_file_created:
            emitter.emit_artifact(audio_path, "audio")
            hook.on_artifact_created(Path(audio_path))
        
        # Step 4: Supervision check
        intervention = hook.on_step()
        
        # Step 5: Handle intervention
        if intervention:
            if intervention.type == ESCALATE:
                pause_agent()
                notify_user(intervention.rationale)
                break
            elif intervention.type == REQUEST_EVIDENCE:
                # Inject suggestion into next LLM call
                messages.append({
                    "role": "system",
                    "content": intervention.suggested_next_steps[0]
                })
```

### What Happens Internally

1. **Events flow**: `emitter.emit_*()` → `trace_store.append()` → Events stored
2. **Artifact processing**: `hook.on_artifact_created()` → Extract claims → Bind evidence
3. **Supervision**: `hook.on_step()` → `Supervisor.analyze_step()` → Check graph state → Generate intervention
4. **Intervention**: Handler called → External loop acts on it

---

## 🎨 Key Design Patterns

### 1. **Protocol-Based Interfaces**
- No inheritance required
- Structural typing (duck typing with type safety)
- Easy to mock for testing

### 2. **Adapter Pattern**
- `SentinelEventEmitter` adapts external events to Sentinel format
- `GitHubBundleEvidenceSource` adapts GitHub bundles to EvidenceSource protocol

### 3. **Hook Pattern**
- External loops call hook at strategic points
- Hook doesn't control the loop - loop controls hook
- Minimal coupling

### 4. **Strategy Pattern**
- `InterventionHandler` protocol allows custom intervention handling
- `EvidenceSource` protocol allows custom evidence sources

---

## 🔑 Key Abstractions

### TraceStore Protocol
**Purpose**: Abstract event storage
**Why**: External loops may use databases, files, in-memory, etc.
**Contract**: `append()`, `iter_events()`, `close()`

### EventEmitter Protocol
**Purpose**: Standardized event emission
**Why**: External loops have different event formats
**Contract**: `emit_llm_call()`, `emit_tool_call()`, `emit_observation()`, etc.

### EvidenceSource Protocol
**Purpose**: Abstract evidence sources
**Why**: Not all loops use GitHub - could be conversations, documents, etc.
**Contract**: `get_evidence_items()`

### InterventionHandler Protocol
**Purpose**: Custom intervention handling
**Why**: Different loops need different responses (pause, notify, inject, etc.)
**Contract**: `handle_intervention(intervention, context)`

---

## ✅ Integration Checklist

For an external loop to integrate:

1. ✅ **Implement TraceStore** (or use `JsonlTraceStore`)
2. ✅ **Use SentinelEventEmitter** (or implement `EventEmitter` protocol)
3. ✅ **Create SupervisorHook** with handlers
4. ✅ **Emit events** at key points (LLM calls, tool calls, observations, artifacts)
5. ✅ **Call `hook.on_artifact_created()`** when artifacts are created
6. ✅ **Call `hook.on_step()`** periodically during execution
7. ✅ **Implement InterventionHandler** to handle interventions
8. ✅ **Optionally implement EvidenceSource** for custom evidence

---

## 🎯 Why This Works

1. **No Tight Coupling**: External loops don't inherit from Sentinel classes
2. **Protocol-Based**: Structural typing means "if it has the methods, it works"
3. **Hook Pattern**: External loop controls when supervision happens
4. **Adapter Pattern**: Conversion happens automatically
5. **Extensible**: New evidence sources, handlers via protocols

**Result**: Any LLM event loop can integrate with ~10 lines of code!

