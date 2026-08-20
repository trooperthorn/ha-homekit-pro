# Notice

This project is a derivative work under the Apache License, Version 2.0
(see `LICENSE.md`).

`custom_components/homekit_controller_pro/` is derived from the
`homekit_controller` integration in
[home-assistant/core](https://github.com/home-assistant/core)
(Copyright Home Assistant / Open Home Foundation authors, Apache-2.0).

Changes made from the upstream source, in summary: the integration domain
was renamed from `homekit_controller` to `homekit_controller_pro`
(`manifest.json`, `const.py`'s `DOMAIN` and device-registry identifier
prefixes, and `strings.json`'s self-referencing translation keys) so this
fork can be installed alongside stock Home Assistant without overriding it.
Functional changes beyond the rename are tracked in this repository's git
history.

The `requirements` entry in `manifest.json` points at
[trooperthorn/aiohomekit](https://github.com/trooperthorn/aiohomekit), a
fork of [Jc2k/aiohomekit](https://github.com/Jc2k/aiohomekit)
(Apache-2.0), rather than the upstream PyPI package.
