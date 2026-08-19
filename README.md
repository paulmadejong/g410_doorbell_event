# G410 Ring Event 0.1.0

This is a Home Assistant custom integration for the Aqara G410 Matter doorbell.

HACS files included in this repository:

- `hacs.json` in the repository root
- `brand/icon.png`
- `LICENSE`
- `pyproject.toml`
- `.github/workflows/`

Repository notes for HACS publication:

- Set the GitHub repository description and topics.
- Add the repository to Home Assistant brands if you want it listed as a polished public integration.

What it does:

- Uses the existing Home Assistant Matter integration.
- Auto-discovers the matching Matter node and endpoint from the current Matter inventory.
- Requires the endpoint to expose the `OccupancySensing` cluster.
- Listens to raw Matter `NODE_EVENT` messages.
- Treats `occupancyChanged` with `occupied: true` as the doorbell ring signal.
- Exposes a Home Assistant doorbell event entity with the standard event type `ring`.
- Keeps the legacy `g410_doorbell_event` bus event for backward compatibility.

Event fired:

- Standard Home Assistant event entity type: `ring`
- Legacy Home Assistant bus event: `g410_doorbell_event`

In other words: this integration emits the standard doorbell `ring` event through a Home Assistant `event` entity, even though the underlying Matter signal currently comes from `OccupancySensing.occupancyChanged`.

Event payload:

- `node_id`
- `endpoint_id`
- `cluster_id`
- `event_id`
- `event_number`
- `priority`
- `timestamp`
- `timestamp_type`
- `occupied`
- `raw_data`

## Installation

Preferred install path: HACS custom repository.

[![Open your Home Assistant instance and open the custom repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=paulmadejong&repository=g410_doorbell_event&category=integration)

If the badge is not visible in your editor or local preview, use this same link directly:

`https://my.home-assistant.io/redirect/hacs_repository/?owner=paulmadejong&repository=g410_doorbell_event&category=integration`

1. Open the HACS custom repository dialog with the button above.
2. Add this repository as an `Integration`.
3. Install `G410 Ring Event` from HACS.
4. Restart Home Assistant.
5. Add the integration from Settings -> Devices & services.
6. Keep the built-in Matter integration installed and loaded. This component depends on it.

Manual fallback:

1. Copy `custom_components/g410_doorbell_event/` into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings -> Devices & services.
4. Keep the built-in Matter integration installed and loaded. This component depends on it.

## HACS

This repository is structured for HACS as a custom integration repository.

The button above will work after you publish this repository on GitHub and replace the placeholder owner in the URL.

For a public HACS repository you still need:

1. A public GitHub repository.
2. A repository description.
3. Repository topics.
4. A GitHub release for the version you want to publish.
5. A brand icon in `brand/icon.png`.

## Development

`pyproject.toml` is included for local test, lint and `uv` dependency management.

A runtime `requirements.txt` is intentionally not used here, because Home Assistant custom integrations declare Python runtime dependencies in `manifest.json`, not in a repository-level requirements file.

For local development this repository now uses `uv` with a `dev` dependency group in `pyproject.toml`.

Typical local workflow:

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

## Automation examples

Recommended, using the Home Assistant event entity:

```yaml
alias: G410 doorbell ring
triggers:
  - trigger: event.received
    target:
      entity_id: event.g410_doorbell_event
    options:
      event_type:
        - ring
actions:
  - action: notify.mobile_app_iphone
    data:
      title: Doorbell
      message: Aqara G410 doorbell rang.
mode: single
```

Compatibility fallback, using the legacy bus event:

```yaml
alias: G410 doorbell pressed
triggers:
  - trigger: event
    event_type: g410_doorbell_event
actions:
  - action: notify.mobile_app_iphone
    data:
      title: Doorbell
      message: Aqara G410 doorbell rang.
mode: single
```

## Behavior

- The primary Home Assistant surface is a doorbell `event` entity with standard event type `ring`.
- The legacy `g410_doorbell_event` bus event remains available for backward compatibility.
- Technically, the trigger source is `occupancyChanged` with `occupied: true`.
- If one clear candidate is found, the integration uses it automatically.
- If no Occupancy Sensing endpoint is found, the integration logs a warning and stays inactive.
- If multiple candidates tie for the best match, the setup flow shows the found candidates and lets you choose the correct node and endpoint manually.

Version is intentionally fixed at `0.1.0` so you can start your Git repository from that baseline later.
