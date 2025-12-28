"""
Core interfaces and hooks for plug-and-play integration with external event loops.

This module provides Protocol-based interfaces and integration hooks that allow
any LLM event loop (e.g., HappyRobot voice agent) to easily integrate with Sentinel's
supervision capabilities.
"""

from sentinel.core.adapter import SentinelEventEmitter
from sentinel.core.adapters import GitHubBundleEvidenceSource
from sentinel.core.hook import SupervisorHook
from sentinel.core.interfaces import (
    EventEmitter,
    EvidenceSource,
    InterventionHandler,
    LLMClient,
    TraceStore,
)

__all__ = [
    "TraceStore",
    "EventEmitter",
    "LLMClient",
    "InterventionHandler",
    "EvidenceSource",
    "SupervisorHook",
    "SentinelEventEmitter",
    "GitHubBundleEvidenceSource",
]

