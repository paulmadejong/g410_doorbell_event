"""Pure discovery helpers for the G410 Doorbell Event integration."""

from __future__ import annotations

from typing import Any

from .const import OCCUPANCY_SENSING_CLUSTER_ID
from .models import DoorbellCandidate


def bool_from_value(value: Any) -> bool:
    """Interpret the device payload's occupied flag as a boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "occupied"}
    return bool(value)


def extract_occupied_flag(payload: Any) -> bool:
    """Extract the occupied flag from flat or nested Matter event payloads."""

    if not isinstance(payload, dict):
        return False

    if "occupied" in payload:
        return bool_from_value(payload.get("occupied"))

    occupancy = payload.get("occupancy")
    if isinstance(occupancy, dict):
        return bool_from_value(occupancy.get("occupied"))

    return False


def safe_name(value: Any) -> str | None:
    """Return a human readable name if available."""

    if value in (None, ""):
        return None
    return str(value)


def type_name(value: Any) -> str:
    """Return a readable type name for a device type class."""

    return getattr(value, "__name__", str(value))


def extract_endpoint_name(node: Any, endpoint: Any) -> str | None:
    """Best-effort endpoint label for logging."""

    for candidate in (
        getattr(endpoint, "name", None),
        getattr(endpoint, "endpoint_name", None),
        getattr(endpoint, "label", None),
    ):
        if candidate:
            return str(candidate)

    device_info = getattr(endpoint, "device_info", None)
    for attr in ("nodeLabel", "productLabel", "manufacturer", "model"):
        if device_info is not None and hasattr(device_info, attr):
            value = getattr(device_info, attr)
            if value:
                return str(value)

    return safe_name(getattr(node, "name", None))


def extract_cluster_ids(endpoint: Any) -> set[int]:
    """Collect cluster ids from an endpoint object."""

    cluster_ids: set[int] = set()

    if getattr(endpoint, "occupancy_cluster_supported", False):
        cluster_ids.add(OCCUPANCY_SENSING_CLUSTER_ID)

    clusters = getattr(endpoint, "clusters", None)
    if isinstance(clusters, dict):
        for key in clusters:
            if isinstance(key, int):
                cluster_ids.add(key)
        for cluster in clusters.values():
            cluster_id = getattr(cluster, "id", None)
            if isinstance(cluster_id, int):
                cluster_ids.add(cluster_id)

    for attr_name in ("cluster_ids", "supported_clusters", "supportedClusterIds"):
        raw = getattr(endpoint, attr_name, None)
        if raw is None:
            continue
        if isinstance(raw, dict):
            raw = raw.keys()
        items = raw if isinstance(raw, list | set | tuple) else [raw]
        for item in items:
            if isinstance(item, int):
                cluster_ids.add(item)
                continue
            cluster_id = getattr(item, "id", None) or getattr(item, "cluster_id", None)
            if isinstance(cluster_id, int):
                cluster_ids.add(cluster_id)

    return cluster_ids


def extract_device_type_names(endpoint: Any) -> set[str]:
    """Collect device type names from an endpoint."""

    names: set[str] = set()
    device_types = getattr(endpoint, "device_types", None)
    if not device_types:
        return names
    for device_type in device_types:
        names.add(type_name(device_type))
    return names


def score_candidate(node: Any, endpoint: Any) -> tuple[int, tuple[str, ...]]:
    """Build a heuristic score for a node/endpoint candidate."""

    reasons: list[str] = []
    score = 0

    if OCCUPANCY_SENSING_CLUSTER_ID in extract_cluster_ids(endpoint):
        score += 100
        reasons.append("occupancy sensing cluster present")

    device_type_names = extract_device_type_names(endpoint)
    if any("Occupancy" in name for name in device_type_names):
        score += 20
        reasons.append("occupancy device type present")
    if any("DoorBell" in name or "Doorbell" in name for name in device_type_names):
        score += 10
        reasons.append("doorbell device type present")

    if getattr(node, "available", True):
        score += 1
        reasons.append("node available")

    if getattr(endpoint, "endpoint_id", 0) != 0:
        score += 1

    return score, tuple(reasons)


def iter_candidates(matter_client: Any) -> list[DoorbellCandidate]:
    """Return all possible candidates from the current Matter node inventory."""

    candidates: list[DoorbellCandidate] = []
    for node in matter_client.get_nodes():
        node_id = getattr(node, "node_id", None)
        if not isinstance(node_id, int):
            continue

        if not getattr(node, "available", True):
            continue

        endpoints = getattr(node, "endpoints", {}) or {}
        for endpoint in endpoints.values():
            endpoint_id = getattr(endpoint, "endpoint_id", None)
            if not isinstance(endpoint_id, int) or endpoint_id == 0:
                continue

            if OCCUPANCY_SENSING_CLUSTER_ID not in extract_cluster_ids(endpoint):
                continue

            score, reasons = score_candidate(node, endpoint)
            candidates.append(
                DoorbellCandidate(
                    node_id=node_id,
                    endpoint_id=endpoint_id,
                    node_name=safe_name(getattr(node, "name", None)),
                    endpoint_name=extract_endpoint_name(node, endpoint),
                    score=score,
                    reasons=reasons,
                )
            )

    return candidates


def summarize_candidate(candidate: DoorbellCandidate) -> str:
    """Return a compact log summary for one candidate."""

    node_part = f"node={candidate.node_id}"
    if candidate.node_name:
        node_part += f" ({candidate.node_name})"
    endpoint_part = f"endpoint={candidate.endpoint_id}"
    if candidate.endpoint_name:
        endpoint_part += f" ({candidate.endpoint_name})"
    reasons = ", ".join(candidate.reasons) if candidate.reasons else "no extra hints"
    return f"{node_part}, {endpoint_part}, score={candidate.score}, reasons={reasons}"
