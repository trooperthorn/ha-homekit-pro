# HomeKit Controller Pro

A Home Assistant custom integration forked from core's `homekit_controller`,
paired with a forked [`aiohomekit`](https://github.com/trooperthorn/aiohomekit)
(upstream: [Jc2k/aiohomekit](https://github.com/Jc2k/aiohomekit)). Home
Assistant acts as a HomeKit *controller* here -- pairing with and reading/
writing to third-party HomeKit accessories -- not the reverse `homekit`
integration that exposes HA itself as a bridge.

Installs alongside stock `homekit_controller` under a different domain
(`homekit_controller_pro`) rather than overriding it, so devices are
re-paired once under this integration and there's a clean fallback to stock
HA at any time.

## Why this exists

Reworking local communication with four paired HomeKit accessories to pull
more data, support writing values where the device allows, cut latency, and
shrink the device-to-HA update delay:

| Device | Focus |
|---|---|
| Ecobee thermostat | Already fairly capable via HomeKit on this (older) unit -- full climate control plus per-room temperature/motion/occupancy sensors work today. Tightening what's exposed: fold "Current Mode" into the climate entity's `preset_mode`, fan-state/`hvac_action` reliability. |
| First Alert Onelink Safe & Sound (1039102) | Only integration path for this device -- no native HA integration exists. Two known upstream BLE pairing-failure bugs ([core#77926](https://github.com/home-assistant/core/issues/77926), [core#80451](https://github.com/home-assistant/core/issues/80451)) never got fixed; highest-risk workstream. |
| Yardian Pro irrigation | Native `yardian` integration is richer, but improving the HomeKit path anyway for a consistent HomeKit-based approach. Needs a real `valve` domain entity instead of today's `switch` mapping. |
| Roku TV | Confirmed bug: shows as unavailable/"lost" when off instead of a clean `off` state. |

Full research (HA/aiohomekit architecture, HAP spec sourcing, per-device
characteristic gaps, upstream contribution reality) lives in `docs/`.

No upstream PR track -- everything lands in this fork. `home-assistant/core`
has a strong, documented pattern of closing vendor-specific HomeKit feature
requests as "Not planned," so this is a fully independent fork rather than
a staged upstream contribution.

## Status

**Phase 0 (repo scaffolding) -- in progress.** `custom_components/homekit_controller_pro/`
is seeded from HA core's `homekit_controller` (domain renamed throughout:
`DOMAIN`, manifest, device-registry identifier prefixes, `strings.json`
translation-key self-references -- see git history for the exact diff from
upstream). Not yet installed against a live HA instance; no tests yet.

**Next: Phase 1**, a live diagnostics audit against the real paired
accessories on the local network, before writing any feature code --
verifying exactly what each device publishes over HAP rather than assuming
from public docs (this already caught one wrong assumption: generic
community reports claimed Ecobee never exposes room sensors over HomeKit,
but this unit does).

See the full phased plan for Phases 2-6 (library-layer fixes, entity/UX
work per device, automation blueprints, QA, HACS packaging).

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements_test.txt
.venv/Scripts/pip install -e ../aiohomekit-fork
.venv/Scripts/pytest tests/ -v
```

Install into a real Home Assistant instance for manual testing by copying
(or symlinking) `custom_components/homekit_controller_pro/` into that
instance's `config/custom_components/`.
