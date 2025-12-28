"""Replay trace events for testing and debugging."""

from pathlib import Path
from typing import List

from sentinel.trace.schema import Event
from sentinel.trace.store_jsonl import JsonlTraceStore


def load_events(path: Path) -> List[Event]:
    """Load all events from a trace file.

    Args:
        path: Path to JSONL trace file.

    Returns:
        List of events.
    """
    store = JsonlTraceStore(path)
    return list(store.iter_events())
