# Changelog

## 0.2.0 — Sensors & integrations

- New Sensors page in desktop and mobile navigation: search real Home Assistant channels, filter by metric, inspect source values/units/update times and connection state.
- Read-only Home Assistant REST adapter with live discovery, on-demand connection testing and genuine Recorder history (24h/7d); source-time charts and accessible exact-value tables, without invented readings or unavailable-to-zero conversions.
- Explicit manual links between existing household plants and sensor channels; persistent additive `sensor_bindings` table. Unlinking never deletes a plant.
- Shared-household permissions reuse membership roles; the administrator-provisioned private connection is authorized for exactly one household per server instance. Tokens stay server-side, outside Git.
- Capability registry and reviewed server-side adapter protocol. Honest bridge catalog: Tuya Cloud, Tuya Local / LocalTuya, ESPHome, MQTT / Zigbee2MQTT and ZHA **through Home Assistant only**; no native direct-brand adapter claim.
- Clear missing-light, unknown, unavailable, stale and offline states; humidity remains the source label rather than an uncalibrated soil-moisture assertion. No watering advice inferred from uncalibrated channels.
- Bounded upstream requests and history payloads, explicit IP destination policy, redirect/proxy refusal, guarded browser writes and streamed-body size enforcement.
- Sensor plant selector avoids automatic plant-image backfill and paginates within the existing API limit.
- Integration setup/security/plugin documentation in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

### Current limits

One admin-managed HA connection/household per instance; no self-service token UI, native Tuya/MQTT connection, background polling, alert automation or pay-cloud fallback. Exposed device channels and history depend on Home Assistant integration/Recorder support. No light or conductivity data is invented for devices that expose only temperature, humidity and battery.
