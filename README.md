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

| Device | Status |
|---|---|
| Ecobee thermostat (bridge with 8 SmartSensors) | Four new vendor sensors wired up: maintenance alert text, equipment-running state, status code, aux-heat-active. "Current Mode" turned out to be read-only over HAP (no `pw` permission) -- folding it into `preset_mode` isn't viable, corrected from the original plan. |
| First Alert Onelink Safe & Sound (1039102) | Only integration path for this device -- no native HA integration exists. Currently paired over IP, not BLE, so the historical BLE-pairing-failure issues don't appear to affect this unit. Everything it publishes (smoke, CO, nightlight, battery) is already standard-mapped; a disabled battery entity just needs re-enabling in HA, not code. |
| Yardian Pro irrigation | New `HomeKitIrrigationSystem` entity closes the confirmed zero-entity gap on the parent `IrrigationSystem` service. Migrating the 12 existing per-zone entities to HA's native `valve` domain is a deliberate, separate, still-open decision (breaking change). |
| Roku TV | Volume/mute now wired to the linked Speaker service (was previously invisible to HA despite the device supporting it). The "shows unavailable when off" bug is traced but not fixed -- needs live testing to tell which of two code paths is responsible. |

Full findings, corrections, and what's still open per device are in
[`docs/device-notes.md`](docs/device-notes.md).

Full research (HA/aiohomekit architecture, HAP spec sourcing, per-device
characteristic gaps, upstream contribution reality) lives in `docs/`.

No upstream PR track -- everything lands in this fork. `home-assistant/core`
has a strong, documented pattern of closing vendor-specific HomeKit feature
requests as "Not planned," so this is a fully independent fork rather than
a staged upstream contribution.

## Status

- **Phase 0 (repo scaffolding)** -- done. Domain renamed throughout, dev
  environment matches the real target (Python 3.14, HA 2026.8.2 exactly),
  HA core's own ruff config adapted in so lint reflects real HA standards.
- **Phase 1 (live diagnostics audit)** -- done. Real HAP data pulled for
  all four devices; see `docs/device-notes.md`.
- **Phase 2 (aiohomekit library layer)** -- mostly turned out to be
  unnecessary: nearly every vendor characteristic these devices publish
  was already modeled in the `aiohomekit` fork, just not dispatched to a
  platform on the `homekit_controller_pro` side. Onelink's BLE-pairing
  reliability work (originally flagged highest-risk) is on hold since
  this unit pairs over IP successfully, not BLE.
- **Phase 3 (entity/UX work per device)** -- Roku volume/mute, Yardian
  irrigation-system entity, and four Ecobee vendor sensors are done (all
  verified with a real import against the installed HA + aiohomekit, not
  just syntax-checked). Config/reconfigure UX (no way to re-pair without
  delete-and-re-add today) is still open.
- **Phase 4 (cross-integration automation)** -- three blueprints added
  (see below), built directly on the entities from Phase 3.
- **Phase 5 (QA)** -- in progress. 21 tests added, all passing, exercising
  entity logic against real captured HAP data (`tests/fixtures/*.json`,
  extracted from the Phase 1 diagnostics pulls) rather than synthetic
  values -- see Testing below. The blueprint action bodies are still
  unverified beyond manual review (see Blueprints).
- **Phase 6 (HACS packaging)** -- not started. Nothing installed against a
  live HA instance yet.

## Blueprints

`blueprints/automation/`:

- `smoke_co_severe_event.yaml` -- urgent notification the moment a
  smoke or CO binary_sensor trips. Generic (any device_class match), not
  Onelink-specific.
- `ecobee_equipment_anomaly.yaml` -- notifies on a status-code change to
  alert/error, or equipment running continuously past a configurable
  threshold. Built around this session's new Ecobee vendor sensors.
- `irrigation_unexpected_activation.yaml` -- notifies if an irrigation
  switch/valve turns on outside an allowed time window. Built around the
  new Yardian `HomeKitIrrigationSystem` entity but works with any
  switch/valve.

All three validated structurally (blueprint `input`/selector schemas,
trigger and condition schemas) against the real installed
`homeassistant` package. The `notify.send_message` action bodies were
**not** validated end-to-end -- that needs a live HA instance or the
`pytest-homeassistant-custom-component` harness, which isn't wired up
yet (tracked for Phase 5).

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements_test.txt
.venv/Scripts/pip install -e ../aiohomekit-fork
.venv/Scripts/pytest tests/ -v
.venv/Scripts/ruff check custom_components/ tests/
```

Install into a real Home Assistant instance for manual testing by copying
(or symlinking) `custom_components/homekit_controller_pro/` into that
instance's `config/custom_components/`.

## Testing

`tests/` exercises entity logic (properties, `is_on`, `native_value`,
writes via a mocked `put_characteristics`) directly against real captured
HAP data in `tests/fixtures/*_entity_map.json` -- extracted from the Phase
1 `diagnostics_raw/*.json` pulls (pairing keys stripped, only the
service/characteristic structure kept) via a minimal `FakeHKDevice` stub
in `tests/conftest.py`. No running Home Assistant instance needed for
these.

**Windows limitation**: `pytest-homeassistant-custom-component` (needed
for `hass`-fixture-based tests -- config flow, coordinator, anything that
needs a running HA core) auto-registers as a pytest plugin the moment it's
installed, and importing it pulls in `homeassistant.runner`, which imports
the Unix-only `fcntl` module. This breaks pytest entirely on native
Windows, not just tests that use it. `pytest.ini` disables its auto-load
(`-p no:homeassistant`) since the current suite doesn't need it. When
config-flow-level tests are added, either run them under WSL/Linux/CI, or
drop that `addopts` line there.
