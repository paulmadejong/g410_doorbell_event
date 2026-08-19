# G410 Ring Event 0.1.0

This is a Home Assistant custom integration for the Aqara G410 Matter doorbell.

## Why this exists

Current Matter support for Aqara video doorbells in Home Assistant is still incomplete. In practice, users often end up with either:

- too little exposed by the stock Matter integration,
- Aqara-specific Matter signals that need manual setup first,
- or short/brief occupancy-style ring pulses that are awkward to automate against directly.

This integration exists to make the Aqara G410 usable as a reliable Home Assistant doorbell trigger by:

- discovering the correct Aqara Matter signal endpoint automatically,
- converting the Aqara occupancy-style ring signal into a proper Home Assistant `ring` event entity,
- and exposing custom bus events for automation compatibility.

Background and related issues:

- Home Assistant core issue about limited G410 Matter exposure:
  [home-assistant/core#153274](https://github.com/home-assistant/core/issues/153274)
- Open Home Foundation roadmap item about making Matter video doorbells behave more like established HA camera/doorbell integrations:
  [OpenHomeFoundation/roadmap#84](https://github.com/OpenHomeFoundation/roadmap/issues/84)

Practical problem this component is trying to solve:

- Aqara's Matter signal for the G410 ring currently behaves like a very short occupancy-style pulse.
- Depending on how you automate against that signal, those short pulses can be awkward to catch reliably or can lead to inconsistent behavior.
- This integration normalizes that behavior into a proper Home Assistant doorbell `ring` event surface and compatible custom bus events.

Observed behavior from real-world Matter logs:

- the ring signal is exposed as `occupancySensing.occupancyChanged`
- it appears as a short `occupied: true` pulse followed by `occupied: false`
- the pulse duration is not stable
- in testing, pulses ranged from extremely short bursts in the single-digit millisecond range up to multi-second pulses

Anonymized examples from real captures:

```text
occupied: true  -> occupied: false after ~9 ms
occupied: true  -> occupied: false after ~593 ms
occupied: true  -> occupied: false after ~986 ms
occupied: true  -> occupied: false after ~1001 ms
occupied: true  -> occupied: false after ~3642 ms
```

That variability is exactly why this integration does not rely on a plain exposed binary-style occupancy state alone. Instead, it listens directly to the raw Matter node events and translates those pulses into a clearer Home Assistant doorbell event model.

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
- Fires `g410_doorbell_event` for backward compatibility.
- Fires `aqara_g410_ring` as the clearer custom bus event alias.

## Aqara setup required

Before this integration can work, the Aqara G410 must actually publish the relevant Aqara Matter signal into Matter.

In the Aqara app this is done through the experimental Matter signal sync feature.

Reference:

- Aqara forum post describing the G410 third-party Matter signal workflow:
  [Integrating the Aqara G410 Doorbell with Third-Party Platforms: Home Assistant and Homey Pro](https://forum.aqara.com/t/integrating-the-aqara-g410-doorbell-with-third-party-platforms-home-assistant-and-homey-pro/247856)

### Enable Aqara Matter Signal Management

In the Aqara Home app:

1. Open `Profile`.
2. Open `Connect to ecosystems`.
3. Open `Matter`.
4. Open `Scene and Signal Synchronization` (experimental).
5. Open `Signal Management`.
6. Use the add button to create a new signal.
7. Choose the doorbell ring condition, for example when someone rings the doorbell.
8. Give the signal a clear name, for example `Doorbell` or `Aangebeld`.
9. Save the signal.

After that, Home Assistant Matter should receive the Aqara-generated Matter signal, typically as an occupancy-style signal endpoint that this custom integration can discover and translate into a proper ring event.

If you skip this Aqara-side step, this integration usually has nothing useful to detect.

Event fired:

- Standard Home Assistant event entity type: `ring`
- Legacy Home Assistant bus event: `g410_doorbell_event`
- Preferred custom Home Assistant bus event alias: `aqara_g410_ring`

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

Compatibility fallback, using the preferred custom bus event alias:

```yaml
alias: G410 doorbell ring alias
triggers:
  - trigger: event
    event_type: aqara_g410_ring
actions:
  - action: notify.mobile_app_iphone
    data:
      title: Doorbell
      message: Aqara G410 doorbell rang.
mode: single
```

Legacy compatibility fallback:

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
- The preferred custom bus event alias is `aqara_g410_ring`.
- The legacy `g410_doorbell_event` bus event remains available for backward compatibility.
- Technically, the trigger source is `occupancyChanged` with `occupied: true`.
- If one clear candidate is found, the integration uses it automatically.
- If no Occupancy Sensing endpoint is found, the integration logs a warning and stays inactive.
- If multiple candidates tie for the best match, the setup flow shows the found candidates and lets you choose the correct node and endpoint manually.

Version is intentionally fixed at `0.1.0` so you can start your Git repository from that baseline later.
