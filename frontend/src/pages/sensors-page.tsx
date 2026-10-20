import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Radio, RefreshCw, PlugZap } from "lucide-react";
import { SensorChart, type SensorReading } from "@/components/sensor-chart";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { apiRequest } from "@/lib/api";
import { loadSensorPlants } from "@/lib/sensor-plants";
import type { Household } from "@/lib/types";

type Integration = { id: string; name: string; configured: boolean; capabilities: string[] };
type Binding = { id: string; entity_id: string; plant_id: string; adapter_id: string };
type PlantOption = { id: string; nickname: string };
const inputClass = "rounded-xl border bg-background px-3 py-2 text-sm w-full";
const message = (error: unknown) => error instanceof Error ? error.message : "Request failed. Please try again.";

export function IntegrationGuide() {
  return <Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><PlugZap className="h-5 w-5" />Integration catalog</CardTitle></CardHeader><CardContent className="space-y-3 text-sm">
    <p><strong>Home Assistant · ready</strong> — discovery, current values, Recorder history and plant bindings. Read-only; RootCore never controls devices.</p>
    <p><strong>Administrator-managed:</strong> one authorized household per server instance. The administrator configures the server URL, private token and household ID outside Git. Other households cannot use this connection. No token is sent to your browser.</p>
    <div className="flex flex-wrap gap-2">{["Tuya Cloud", "Tuya Local / LocalTuya", "ESPHome", "MQTT / Zigbee2MQTT", "ZHA"].map(name => <span key={name} className="rounded-full border px-3 py-1">{name} · via Home Assistant</span>)}</div>
    <p className="text-muted-foreground">No direct Tuya cloud/local adapter, paid fallback or background polling. A brand bridge works only if Home Assistant exposes its supported sensor entities. Light and fertility channels depend on the device integration.</p>
    <details><summary className="cursor-pointer font-medium">Setup &amp; extensibility</summary><ol className="list-decimal pl-5 space-y-1 mt-2"><li>Add your device to Home Assistant and verify its numeric sensor entities.</li><li>Ask your server administrator to configure ROOTCORE_HA_URL, ROOTCORE_HA_TOKEN and ROOTCORE_HA_HOUSEHOLD_ID in private server environment.</li><li>Test connection, search the device name or entity family, then link each channel to a plant. No plant is guessed automatically.</li><li>Developers can add a reviewed server-side adapter through the capability registry; arbitrary browser plugins and URLs are not executable.</li></ol><p className="mt-2">Full setup and adapter contract: docs/INTEGRATIONS.md in the RootCore repository.</p></details>
  </CardContent></Card>;
}

export function ChannelInfo({ readings }: { readings: SensorReading[] }) {
  return <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-sm space-y-1">
    {!readings.some(r => r.metric === "illuminance") && <p><strong>Light channel not exposed</strong> in this selection. No lux reading is available; this is not zero light.</p>}
    {readings.some(r => r.metric === "humidity") && <p>Humidity is the Home Assistant source label, not calibrated soil moisture. Check the device documentation before interpreting it.</p>}
    <p>Readings are informational. No watering advice or automatic threshold is inferred. “Stale” means the last source update is over 24 hours old, not necessarily a faulty device.</p>
  </div>;
}

export function SensorsPage() {
  const { activeHousehold } = useAuth();
  if (!activeHousehold) return <p>Pick a home first.</p>;
  return <SensorsHome key={activeHousehold.id} home={activeHousehold} />;
}

function SensorsHome({ home }: { home: Household }) {
  const base = `/api/v1/households/${home.id}`;
  const [integration, setIntegration] = useState<Integration | null>(null);
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [bindings, setBindings] = useState<Binding[]>([]);
  const [plants, setPlants] = useState<PlantOption[]>([]);
  const [query, setQuery] = useState("");
  const [metric, setMetric] = useState("");
  const [selected, setSelected] = useState("");
  const [plantId, setPlantId] = useState("");
  const [hours, setHours] = useState(24);
  const [points, setPoints] = useState<SensorReading[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [fetched, setFetched] = useState<string | null>(null);
  const canWrite = home.role !== null && home.role !== "viewer";
  const canAdmin = home.role === "owner" || home.role === "admin";

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [catalog, links, plantList] = await Promise.all([
        apiRequest<Integration[]>(base + "/integrations"), apiRequest<Binding[]>(base + "/sensor-bindings"), loadSensorPlants(home.id),
      ]);
      setIntegration(catalog[0]); setBindings(links); setPlants(plantList);
      if (catalog[0]?.configured) {
        const sensors = await apiRequest<SensorReading[]>(base + "/sensors");
        setReadings(sensors); setFetched(new Date().toISOString());
      } else { setReadings([]); }
    } catch (err) { setError(message(err)); setReadings([]); }
    finally { setLoading(false); }
  }, [base, home.id]);
  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    let active = true;
    setPoints([]); setHistoryError(null);
    if (!selected) { setHistoryLoading(false); return; }
    setHistoryLoading(true);
    apiRequest<{ points: SensorReading[] }>(`${base}/sensors/${encodeURIComponent(selected)}/history?hours=${hours}`)
      .then(data => { if (active) setPoints(data.points); })
      .catch(err => { if (active) setHistoryError(message(err)); })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [base, selected, hours]);

  async function action(run: () => Promise<unknown>, success: string) {
    setBusy(true); setNotice(null); setError(null);
    try { await run(); setNotice(success); await load(); }
    catch (err) { setError(message(err)); }
    finally { setBusy(false); }
  }
  const filtered = readings.filter(r => (!metric || r.metric === metric) && `${r.name} ${r.entity_id} ${r.unit ?? ""}`.toLowerCase().includes(query.toLowerCase()));
  const current = readings.find(r => r.entity_id === selected);
  return <div className="space-y-6">
    <header className="flex flex-wrap justify-between gap-3"><div><p className="text-xs uppercase tracking-wide text-muted-foreground">Connected growing · {home.name}</p><h1 className="text-2xl font-semibold flex items-center gap-2"><Radio className="h-6 w-6 text-primary" />Sensors &amp; integrations</h1><p className="text-sm text-muted-foreground mt-1">Real device readings, linked to your plants. Refresh on demand.</p></div><Button variant="outline" disabled={loading || busy} onClick={() => void load()}><RefreshCw className="h-4 w-4 mr-2" />Refresh sensors</Button></header>
    <details className="rounded-xl border p-3"><summary className="cursor-pointer text-sm font-medium">Integration catalog, setup &amp; supported bridges</summary><div className="mt-3"><IntegrationGuide /></div></details>
    {notice && <p role="status" className="rounded-xl bg-primary/10 p-3">{notice}</p>}
    {error && <p role="alert" className="rounded-xl border border-destructive p-3">Connection unavailable: {error}. No current values are shown.</p>}
    {loading && <p role="status">Loading sensors…</p>}
    {integration && !integration.configured && <Card><CardContent className="pt-5">Home Assistant is not configured for this household. Ask your server administrator to configure the private connection. Existing plant data stays unchanged.</CardContent></Card>}
    {integration?.configured && <>
      <div className="flex flex-wrap items-center gap-3 text-sm"><span className="rounded-full bg-primary/10 px-3 py-1">Home Assistant · read-only</span>{fetched && !error && <span>Fetched {new Date(fetched).toLocaleString()} · source update times shown below</span>}{canAdmin && <Button size="sm" variant="outline" disabled={busy} onClick={() => void action(() => apiRequest(base + "/integrations/home_assistant/test", { method: "POST" }), "Connection test passed. Home Assistant is reachable.")}>Test connection</Button>}</div>
      {!loading && !error && <>
        <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm">Find a device / entity / unit<input className={inputClass} value={query} onChange={e => setQuery(e.target.value)} placeholder="e.g. Soil Fertility Sensor" /></label><label className="text-sm">Channel<select className={inputClass} value={metric} onChange={e => setMetric(e.target.value)}><option value="">All channels</option>{["humidity", "soil_moisture", "temperature", "battery", "illuminance"].map(m => <option key={m} value={m}>{m.replaceAll("_", " ")}</option>)}</select></label></div>
        <p className="text-xs text-muted-foreground">Search a shared entity name to see a device’s channels together. Source names are not proof of physical plant identity; links below are always manual.</p>
        <ChannelInfo readings={filtered} />
        <p role="status" className="text-sm text-muted-foreground">{filtered.length} channels shown · {bindings.length} plant links</p>
        {!filtered.length && <p>No supported sensors match. Try another search, or verify the entity is exposed in Home Assistant.</p>}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{filtered.map(r => <button key={r.entity_id} type="button" onClick={() => setSelected(r.entity_id)} aria-pressed={selected === r.entity_id} className={`rounded-2xl border p-4 text-left space-y-2 hover:bg-muted/50 ${selected === r.entity_id ? "border-primary bg-primary/5" : ""}`}><span className="block font-medium">{r.name}</span><span className="block text-3xl font-semibold tabular-nums">{r.value === null ? "—" : r.value} <span className="text-base font-normal">{r.unit}</span></span><span className="block text-xs uppercase text-muted-foreground">{r.metric.replaceAll("_", " ")} · {r.status.replaceAll("_", " ")}</span><span className="block text-xs break-all text-muted-foreground">{r.entity_id}</span><span className="block text-xs">Source update: {r.timestamp ? new Date(r.timestamp).toLocaleString() : "Not provided"}</span><span className="block text-xs text-primary">View graph &amp; plant links →</span></button>)}</div>
      </>}
      {selected && current && !error && <Card><CardHeader><CardTitle className="text-lg">{current.name} · history</CardTitle></CardHeader><CardContent className="space-y-4"><label className="text-sm">History window<select className={inputClass} value={hours} onChange={e => setHours(Number(e.target.value))}><option value={24}>Last 24 hours</option><option value={168}>Last 7 days</option></select></label><p className="text-xs text-muted-foreground">Source: Home Assistant Recorder. Values and units are unmodified. Recording may start before this window to establish its initial state.</p>{historyLoading ? <p role="status">Loading recorded history…</p> : historyError ? <p role="alert">History unavailable: {historyError}</p> : <SensorChart points={points} />}
        {canWrite && <form className="flex flex-wrap gap-2 items-end" onSubmit={e => { e.preventDefault(); if (plantId) void action(() => apiRequest(base + "/sensor-bindings", { method: "POST", body: { plant_id: plantId, entity_id: selected } }), "Sensor linked to plant."); }}><label className="text-sm flex-1 min-w-48">Link this channel to a plant<select className={inputClass} required value={plantId} onChange={e => setPlantId(e.target.value)}><option value="">Choose a plant (manual)</option>{plants.map(p => <option key={p.id} value={p.id}>{p.nickname}</option>)}</select></label><Button disabled={!plantId || busy} type="submit">Link sensor</Button></form>}
      </CardContent></Card>}
    </>}
    <Card><CardHeader><CardTitle className="text-base">Plant sensor links</CardTitle></CardHeader><CardContent className="space-y-3">{!bindings.length && <p className="text-sm text-muted-foreground">No links yet. Select a sensor channel, then choose its plant. Existing plants are never renamed or moved.</p>}{bindings.map(b => { const r = readings.find(s => s.entity_id === b.entity_id); return <div key={b.id} className="rounded-xl border p-3 flex flex-wrap gap-3 items-center"><div className="flex-1 min-w-0"><Link className="font-medium text-primary" to={`/plants/${b.plant_id}`}>{plants.find(p => p.id === b.plant_id)?.nickname ?? "Open plant"}</Link><p className="text-xs break-all">{r?.name ?? b.entity_id}</p><p className="text-sm">{error ? "Connection unavailable" : r ? `${r.value ?? "—"} ${r.unit ?? ""} · ${r.status}` : "Channel not currently exposed"}</p></div>{canWrite && <Button size="sm" variant="outline" disabled={busy} onClick={() => void action(() => apiRequest(base + "/sensor-bindings/" + b.id, { method: "DELETE" }), "Sensor unlinked. Plant preserved.")}>Unlink</Button>}</div>; })}</CardContent></Card>
  </div>;
}
