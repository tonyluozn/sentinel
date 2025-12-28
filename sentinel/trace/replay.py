from pathlib import Path
from typing import List

from sentinel.trace.schema import Event
from sentinel.trace.store_jsonl import JsonlTraceStore


def load_events(path: Path) -> List[Event]:
    store = JsonlTraceStore(path)
    return list(store.iter_events())
