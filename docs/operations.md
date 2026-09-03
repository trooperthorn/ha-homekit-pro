# Operations

## Installing the test harness

`pytest-homeassistant-custom-component` is extracted from a specific core
release, sometimes a beta, and pulls that exact core version in as a
dependency. Installing it in the same resolver pass as
`requirements_test.txt` can produce a version conflict, because
`requirements_test.txt` pins the stable `homeassistant` release. Install it
first if `hass`-based tests are enabled (see "Running tests on Windows"),
then install this file so its stable pin re-resolves core to the release
this repository targets:

```bash
pip install pytest-homeassistant-custom-component==0.13.362
pip install -r requirements_test.txt
```

## Bluetooth, USB, and Thread test dependencies

`sensor.py` and `connection.py` import directly from
`homeassistant.components.bluetooth` and `homeassistant.components.thread`
at module load time (the manifest declares `bluetooth` support and
`after_dependencies: ["thread"]`). Home Assistant only installs a
component's own requirements when that component is actually set up at
runtime; a static top-level import does not trigger that, and importing
`homeassistant.components.bluetooth` pulls in a chain through
`homeassistant.components.usb` and `homeassistant.components.hassio` as
well. `requirements_test.txt` lists every package in that chain
(`aiousbwatcher`, `serialx`, `bleak` and its related packages, `dbus-fast`,
`habluetooth`, `aiohasupervisor`, `python-otbr-api`, `pyroute2`) pinned to
the exact version core 2026.9.0's own manifests declare for `bluetooth`,
`usb`, `hassio`, and `thread`, so importing the integration's modules
succeeds without installing anything beyond what those specific chains
need.

## Running tests on Windows

`pytest-homeassistant-custom-component` auto-registers as a pytest11 plugin
just by being installed, and importing it pulls in `homeassistant.runner`,
which imports the Unix-only `fcntl` module. That breaks pytest entirely on
native Windows. `pytest.ini` disables the plugin's auto-load
(`-p no:homeassistant`) because the current test suite tests entity logic
directly against real captured HAP data through a lightweight stub
(`tests/conftest.py`) rather than through the `hass` fixture. Re-enable the
plugin (drop that addopt) once `hass`-based tests are added, and run those
under WSL, Linux, or CI rather than native Windows.
