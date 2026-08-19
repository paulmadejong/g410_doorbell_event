"""Unit tests for discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from custom_components.g410_doorbell_event.const import OCCUPANCY_SENSING_CLUSTER_ID
from custom_components.g410_doorbell_event.discovery import (
    bool_from_value,
    extract_occupied_flag,
    iter_candidates,
    resolve_candidate,
    summarize_candidate,
)


class OccupancySensor:
    """Fake Occupancy Sensor device type."""


class DoorbellDevice:
    """Fake Doorbell device type."""


@dataclass
class FakeCluster:
    """Fake cluster metadata."""

    id: int


@dataclass
class FakeEndpoint:
    """Fake Matter endpoint."""

    endpoint_id: int
    name: str | None = None
    device_types: list[type] = field(default_factory=list)
    clusters: dict[int, FakeCluster] = field(default_factory=dict)


@dataclass
class FakeNode:
    """Fake Matter node."""

    node_id: int
    endpoints: dict[int, FakeEndpoint]
    available: bool = True
    name: str | None = None


class FakeMatterClient:
    """Fake Matter client."""

    def __init__(self, nodes: list[FakeNode]) -> None:
        self._nodes = nodes

    def get_nodes(self) -> list[FakeNode]:
        return self._nodes


def test_bool_from_value_accepts_expected_truthy_values() -> None:
    """Truthiness parsing should handle Matter payload variants."""

    assert bool_from_value(True) is True
    assert bool_from_value(1) is True
    assert bool_from_value("occupied") is True
    assert bool_from_value(" true ") is True
    assert bool_from_value(0) is False
    assert bool_from_value("false") is False


def test_extract_occupied_flag_supports_flat_and_nested_payloads() -> None:
    """Matter payload parsing should support both known occupancyChanged shapes."""

    assert extract_occupied_flag({"occupied": True}) is True
    assert extract_occupied_flag({"occupancy": {"occupied": True}}) is True
    assert extract_occupied_flag({"occupancy": {"occupied": False}}) is False
    assert extract_occupied_flag({"unexpected": "value"}) is False


def test_iter_candidates_returns_ranked_candidate() -> None:
    """Candidates should be extracted from occupancy-capable endpoints."""

    endpoint = FakeEndpoint(
        endpoint_id=2,
        name="Doorbell Endpoint",
        device_types=[OccupancySensor, DoorbellDevice],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    node = FakeNode(node_id=17, name="Aqara G410", endpoints={2: endpoint})

    candidates = iter_candidates(FakeMatterClient([node]))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.node_id == 17
    assert candidate.endpoint_id == 2
    assert candidate.node_name == "Aqara G410"
    assert candidate.endpoint_name == "Doorbell Endpoint"
    assert candidate.score >= 100
    assert "occupancy sensing cluster present" in candidate.reasons


def test_summarize_candidate_includes_names_and_ids() -> None:
    """Candidate summary should stay readable for logs."""

    endpoint = FakeEndpoint(
        endpoint_id=3,
        name="Occupancy",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    node = FakeNode(node_id=21, name="G410", endpoints={3: endpoint})
    candidate = iter_candidates(FakeMatterClient([node]))[0]

    summary = summarize_candidate(candidate)

    assert "node=21" in summary
    assert "endpoint=3" in summary
    assert "G410" in summary
    assert "Occupancy" in summary


def test_resolve_candidate_prefers_endpoint_two_tiebreaker() -> None:
    """Endpoint 2 should win a same-score tie when present."""

    endpoint_one = FakeEndpoint(
        endpoint_id=1,
        name="Occupancy One",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    endpoint_two = FakeEndpoint(
        endpoint_id=2,
        name="Occupancy Two",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    node = FakeNode(node_id=3, name="G410", endpoints={1: endpoint_one, 2: endpoint_two})
    status, candidate, ranked = resolve_candidate(iter_candidates(FakeMatterClient([node])))

    assert status == "ready"
    assert candidate is not None
    assert candidate.endpoint_id == 2
    assert ranked[0].endpoint_id == 2


def test_ranked_candidates_can_still_be_ambiguous_on_score() -> None:
    """The config flow should still surface ambiguity for equal-score candidates."""

    endpoint_one = FakeEndpoint(
        endpoint_id=1,
        name="Occupancy One",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    endpoint_two = FakeEndpoint(
        endpoint_id=2,
        name="Occupancy Two",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    node_a = FakeNode(node_id=3, name="G410", endpoints={1: endpoint_one})
    node_b = FakeNode(node_id=17, name="Other", endpoints={2: endpoint_two})
    candidates = iter_candidates(FakeMatterClient([node_a, node_b]))

    status, candidate, ranked = resolve_candidate(candidates)

    assert status == "ready"
    assert candidate is not None
    assert ranked[0].score == ranked[1].score


def test_resolve_candidate_accepts_manual_override() -> None:
    """Manual override should resolve an otherwise non-default endpoint."""

    endpoint_one = FakeEndpoint(
        endpoint_id=1,
        name="Occupancy One",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    endpoint_two = FakeEndpoint(
        endpoint_id=2,
        name="Occupancy Two",
        device_types=[OccupancySensor],
        clusters={OCCUPANCY_SENSING_CLUSTER_ID: FakeCluster(id=OCCUPANCY_SENSING_CLUSTER_ID)},
    )
    node = FakeNode(node_id=3, name="G410", endpoints={1: endpoint_one, 2: endpoint_two})
    candidates = iter_candidates(FakeMatterClient([node]))

    status, candidate, _ = resolve_candidate(
        candidates,
        preferred_node_id=3,
        preferred_endpoint_id=1,
    )

    assert status == "ready"
    assert candidate is not None
    assert candidate.endpoint_id == 1
