"""JSONL trace store implementation."""

import json
import sys
from pathlib import Path
from typing import Iterator, Optional

from sentinel.trace.schema import Event


class JsonlTraceStore:
    """Store trace events in JSONL format."""

    def __init__(self, path: Path):
        """Initialize trace store.

        Args:
            path: Path to JSONL file. Parent directories will be created if needed.
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._lock_acquired = False

    def _acquire_lock(self):
        """Acquire file lock (Unix only)."""
        if sys.platform != "win32":
            try:
                import fcntl

                if self._file is None:
                    self._file = open(self.path, "a", encoding="utf-8")
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX)
                self._lock_acquired = True
            except ImportError:
                pass  # fcntl not available

    def _release_lock(self):
        """Release file lock."""
        if sys.platform != "win32" and self._lock_acquired:
            try:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
                self._lock_acquired = False
            except ImportError:
                pass

    def append(self, event: Event):
        """Append an event to the trace store.

        Args:
            event: Event to append.
        """
        self._acquire_lock()
        try:
            if self._file is None:
                self._file = open(self.path, "a", encoding="utf-8")
            line = json.dumps(event.model_dump(), ensure_ascii=False)
            self._file.write(line + "\n")
            self._file.flush()
        finally:
            self._release_lock()

    def iter_events(self) -> Iterator[Event]:
        """Iterate over all events in the store.

        Yields:
            Event objects from the trace store.
        """
        if not self.path.exists():
            return

        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    yield Event(**data)
                except (json.JSONDecodeError, ValueError) as e:
                    # Skip malformed lines, but log warning
                    continue

    def close(self):
        """Close the trace store file."""
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
