"""Data models for the G410 Ring Event integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DoorbellCandidate:
    """A possible node/endpoint match for the G410."""

    node_id: int
    endpoint_id: int
    node_name: str | None
    endpoint_name: str | None
    score: int
    reasons: tuple[str, ...]


@dataclass(slots=True)
class MonitorState:
    """Current discovery state."""

    candidate: DoorbellCandidate | None = None
    status: str = "unknown"
    detail: str = ""
    last_occupied: bool | None = None


DoorbellListener = Callable[[dict[str, Any]], None]
