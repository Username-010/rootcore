# Home Assistant sensors & integration adapters (0.2.0)

Open **Sensors** in the desktop navigation or **More → Sensors** on mobile. RootCore reads Home Assistant sensor values and Recorder history; it never controls devices or changes Home Assistant configuration.

## What is implemented

| Integration | Status | How it connects |
|---|---|---|
| Home Assistant | Working server-side adapter | Read-only REST states + Recorder history |
| Tuya Cloud | Bridge only | Add Tuya to Home Assistant; consume the entities HA actually exposes |
| Tuya Local / LocalTuya | Bridge only | Separate community HA integrations; no native RootCore local-key implementation |
| ESPHome | Bridge only | Expose the device in Home Assistant |
| MQTT / Zigbee2MQTT / ZHA | Bridge only | Expose numeric sensor entities through Home Assistant |

No direct Tuya cloud/local API, native MQTT broker/subscriber, executable browser plugins, paid fallback, or background polling is implemented. The catalog labels are compatibility paths, not separately connected native providers.

Supported source device classes: `moisture`, `illuminance`, `temperature`, `humidity`, `battery`. An integration must expose a matching `sensor.*` entity; arbitrary switches, lights, monetary counters, and device-control actions are excluded.

## Private server setup

The first release deliberately uses **one administrator-managed Home Assistant connection for one explicitly authorized household per RootCore instance**. Existing household owners/admins/members/viewers share it according to their role. Other households cannot discover or request history using that connection, even if they own another collection on the same server. Self-hosters configure their own HA instance; self-service per-household secret entry is not included.

1. Add your sensor/device to Home Assistant. Verify current values and units there first.
2. Create a long-lived Home Assistant access token for a dedicated account if practical. RootCore uses GET only, but the underlying HA token may carry broader authority: treat it as a secret and restrict network access.
3. Read the intended household UUID from your signed-in household API response. Do not substitute a display name or the ID of another household.
4. Create an administrator-owned private environment file **outside the repository**, mode `0600`. Set:

   ```dotenv
   ROOTCORE_HA_URL=http://192.168.1.20:8123
   ROOTCORE_HA_TOKEN=<your-private-token>
   ROOTCORE_HA_HOUSEHOLD_ID=<authorized-household-uuid>
   ```

   The example token/UUID placeholders are not working credentials. Never paste real tokens in a URL, docs, screenshots, issues, Git, or browser storage. `ROOTCORE_HA_TOKEN` is a server-only `SecretStr` and never appears in API responses. Restart/recreate **only RootCore** after changing this private configuration.
5. Add this file to `env_file` on the RootCore service only, preserving its existing environment files. For example:

   ```yaml
   services:
     rootcore:
       env_file:
         - .env
         - /absolute/private/path/rootcore-ha.env
   ```

6. In Sensors, an owner/admin can **Test connection**. Members/viewers can read channels; members and above can create/remove plant links. All operations require existing RootCore authentication and household membership.

### Destination policy

The server URL must be HTTP(S), a literal IP address, and port 80, 443 or 8123. No DNS hostname, URL credentials, non-root path, query string, fragment, loopback, link-local, reserved/multicast destination or cloud metadata endpoint. Use a reachable fixed LAN IP such as your Home Assistant server; the URL is not accepted from API clients. HTTPS must have a certificate trusted by the container (no insecure verification switch). HTTP is appropriate only on a trusted private network. Redirects and environment HTTP proxies are disabled. IPv6 requires bracket URL syntax.

## Read a device and bind a plant

1. Search **Find a device / entity / unit** for the shared device name, e.g. `Soil Fertility Sensor`. Discovery names/entity IDs come from HA; a shared name helps show channels together but is not automatic physical-device/plant identification.
2. Optionally filter by channel. Select a channel card to view its **Last 24 hours / Last 7 days** source-time graph and expandable recorded-value table.
3. Choose an existing plant and **Link sensor**. This stores only household, plant and entity identifiers. No plant is automatically chosen, renamed, moved or watered. Each channel is linked explicitly; one plant can have multiple channels.
4. **Unlink** removes the sensor link, never the plant or HA entity. Existing links remain visible if a device goes offline or disappears.

The selector fetches plants in valid 200-record pages, up to 2,000 plants, explicitly disabling the plant browser's automatic cover backfill so viewing sensors does not fetch unrelated plant images.

## Honest values, graphs and limitations

- Current value, source unit, source update time and fetched-at time are distinct. `unknown`/`unavailable`, nonnumeric and nonfinite values are `null`, displayed `—`, **not zero**. A real measured zero remains zero.
- Stale means the last source update is over 24 hours old. HA can retain an unchanged value without a new update; stale is not a calibrated device-health diagnosis. Missing/invalid/naive timestamps show unknown time.
- Graph x-axis positions use source timestamps. Lines join recorded samples only, break at unavailable values or unit changes, and do not invent measurements in between. The expandable table exposes exact timestamps, values, units and state. No sample downsampling or fabricated history is used.
- Empty history means Recorder has no rows in the response, is disabled/excluded, or the entity is new; offline/invalid upstream responses are separate errors. HA may return an initial state whose original timestamp precedes the requested window. Recorder retention controls actual availability. RootCore does not silently fall back to cached or paid data.
- Operation bounds: 8-second HTTP timeout and 12-second total upstream request; 4 MB decoded-response cap, 500 discovered supported sensors, 10,000 history samples, 24-hour or 7-day windows only. Choose 24 hours if 7 days exceeds limits. No background poller is enabled.
- A humidity channel remains labelled **humidity**, even when its device is marketed as a soil sensor. It is **not calibrated soil moisture** unless you establish that separately. Neither source percentages nor lights imply universal watering thresholds. This release makes no watering recommendation from sensor values.
- If HA exposes no illuminance channel, UI says **Light channel not exposed**. This does not mean `0 lux`. Some Tuya Soil Fertility devices expose only temperature, humidity and battery through the installed integration; RootCore cannot manufacture lux or conductivity from those three channels. The same applies to advertised fertility/conductivity that HA does not expose.

## Server-side plugin contract

Adapters are trusted code reviewed and installed with the application, not arbitrary downloaded scripts. Registry: `backend/app/modules/sensors/registry.py`; first implementation: `adapter.py`. A new adapter implements the `SensorAdapter` protocol:

```python
async def discover(self) -> list[dict]: ...
async def history(self, entity_id: str, hours: int) -> list[dict]: ...
```

Each public reading contains `entity_id`, `name`, finite numeric `value` or null, `unit`, timezone-aware source `timestamp` or null, `metric`, and `status`. Preserve source meaning and units; reject malformed responses, sanitize errors and never include credentials in return values or exception details. Cap outbound time, payload sizes, discovery counts and history windows. Add truthful capability metadata to `CATALOG` and the server factory to `ADAPTERS`; adding metadata alone does **not** implement an integration. Before routing new provider requests, extend connection configuration/tenant authorization and binding provider validation explicitly: current HTTP routes intentionally select only Home Assistant. Native provider authentication and credential persistence must be designed and security-tested before enabling them.

Tests must cover real adapter parsing against clearly test-only upstream fixtures, authorization before outbound I/O, all household roles, foreign plant/binding IDs, secret nonserialization, URL/metadata/redirect/proxy guards, unavailable/stale/empty/offline values and graph gaps. Migrations must be additive and backed up before production application.

## API added in 0.2.0

All below are under `/api/v1/households/{household_id}`:

| Method | Path | Minimum role |
|---|---|---|
| GET | `/integrations` | viewer |
| POST | `/integrations/home_assistant/test` | admin |
| GET | `/sensors` | viewer |
| GET | `/sensors/{entity_id}/history?hours=24` | viewer |
| GET | `/sensor-bindings` | viewer |
| POST | `/sensor-bindings` (`plant_id`, `entity_id`) | member |
| DELETE | `/sensor-bindings/{binding_id}` | member |

Connection/discovery/history additionally require the exact configured household. Origin/Sec-Fetch-Site checks reject cross-site writes. Sensor writes are limited to 4,096 body bytes before JSON parsing, including streamed requests. No URL/token mutation endpoint exists.

## References

- [Home Assistant REST API](https://www.home-assistant.io/developers/rest_api/)
- [Home Assistant Plant integration](https://www.home-assistant.io/integrations/plant/) — a separate HA integration, not required for this adapter
- [Tuya Local](https://github.com/make-all/tuya-local)
- [LocalTuya](https://github.com/rospogrigio/localtuya) — distinct project from Tuya Local

Screenshots of actual authenticated device data are added only after live release QA; no generated/fake sensor screenshots.
