import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { useAmbient } from "@/hooks/use-ambient";
import { THEME_META, useTheme, type Theme } from "@/hooks/use-theme";
import { api, ApiError } from "@/lib/api";
import type { Plant } from "@/lib/types";

const IMPORT_PLACEHOLDER = `Hot Lips Sage (1)
Salvia microphylla 'Hot Lips'

Phlox Rosa Spier
Phlox paniculata

Miniature Rose Pink,Rosa (Miniature Group),outdoor
Coreopsis Early Sunrise,Coreopsis grandiflora 'Early Sunrise',outdoor`;

export function SettingsPage() {
  const { user, logout, activeHousehold, refreshHouseholds } = useAuth();
  const { theme, setTheme, themes } = useTheme();
  const {
    enabled: ambientOn,
    setEnabled: setAmbientOn,
    intensity: ambientIntensity,
    setIntensity: setAmbientIntensity,
  } = useAmbient();
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [autoCover, setAutoCover] = useState(true);
  const [plantnetKey, setPlantnetKey] = useState("");
  const [weatherProvider, setWeatherProvider] = useState<"open_meteo" | "met_norway">(
    "open_meteo",
  );
  const [plantIdProvider, setPlantIdProvider] = useState<"plantnet" | "none">("plantnet");
  const [importText, setImportText] = useState("");
  const [importResult, setImportResult] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [archived, setArchived] = useState<Plant[]>([]);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveBusyId, setArchiveBusyId] = useState<string | null>(null);
  const [notifStatus, setNotifStatus] = useState<string>(() =>
    typeof Notification !== "undefined" ? Notification.permission : "unsupported",
  );

  const loadArchived = useCallback(async () => {
    if (!activeHousehold) {
      setArchived([]);
      return;
    }
    setArchiveLoading(true);
    try {
      const res = await api.listPlants(activeHousehold.id, {
        status: "archived",
        limit: 100,
      });
      setArchived(res.items);
    } catch {
      setArchived([]);
    } finally {
      setArchiveLoading(false);
    }
  }, [activeHousehold]);

  useEffect(() => {
    if (activeHousehold) {
      setLat(activeHousehold.latitude != null ? String(activeHousehold.latitude) : "");
      setLon(activeHousehold.longitude != null ? String(activeHousehold.longitude) : "");
      const s = activeHousehold.settings || {};
      setAutoCover(s.auto_cover_images !== false);
      setPlantnetKey(typeof s.plantnet_api_key === "string" ? s.plantnet_api_key : "");
      setWeatherProvider(
        s.weather_provider === "met_norway" ? "met_norway" : "open_meteo",
      );
      setPlantIdProvider(s.plant_id_provider === "none" ? "none" : "plantnet");
    }
  }, [activeHousehold]);

  useEffect(() => {
    void loadArchived();
  }, [loadArchived]);

  const isOwner = activeHousehold?.role === "owner";
  const canAdmin =
    activeHousehold?.role === "owner" || activeHousehold?.role === "admin";

  async function saveLocation(e: FormEvent) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateHousehold(activeHousehold.id, {
        latitude: lat === "" ? null : Number(lat),
        longitude: lon === "" ? null : Number(lon),
      });
      await refreshHouseholds();
      setMessage("Location saved. Weather will use these coordinates.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save location");
    } finally {
      setBusy(false);
    }
  }

  async function saveFeatures(e: FormEvent) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateHousehold(activeHousehold.id, {
        auto_cover_images: autoCover,
        plantnet_api_key: plantnetKey.trim() || null,
        weather_provider: weatherProvider,
        plant_id_provider: plantIdProvider,
      });
      await refreshHouseholds();
      setMessage("Household preferences saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save settings");
    } finally {
      setBusy(false);
    }
  }

  async function refreshWeather() {
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    try {
      await api.refreshWeather(activeHousehold.id);
      setMessage("Weather refreshed from Open-Meteo.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Weather refresh failed");
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    if (!activeHousehold || !importText.trim()) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    setImportResult(null);
    try {
      const res = await api.importPlants(activeHousehold.id, {
        text: importText,
        auto_cover: autoCover,
      });
      setImportResult(
        `Created ${res.created_count} plant(s).` +
          (res.errors.length ? ` ${res.errors.length} error(s).` : ""),
      );
      setMessage(
        res.created
          .slice(0, 8)
          .map((c) => `${c.nickname}${c.taxon ? ` → ${c.taxon}` : ""}${c.environment ? ` (${c.environment})` : ""}`)
          .join(" · ") || "Import finished.",
      );
      if (res.created_count > 0) setImportText("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  async function restoreArchived(plantId: string) {
    if (!activeHousehold) return;
    setArchiveBusyId(plantId);
    setError(null);
    try {
      await api.restorePlant(activeHousehold.id, plantId);
      setMessage("Plant restored to active collection.");
      await loadArchived();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not restore plant");
    } finally {
      setArchiveBusyId(null);
    }
  }

  async function permanentDelete(plantId: string, nickname: string) {
    if (!activeHousehold) return;
    if (
      !confirm(
        `Permanently delete “${nickname}”? Photos and history for this plant will be removed. This cannot be undone.`,
      )
    ) {
      return;
    }
    setArchiveBusyId(plantId);
    setError(null);
    try {
      await api.deletePlant(activeHousehold.id, plantId);
      setMessage(`“${nickname}” permanently deleted.`);
      await loadArchived();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete plant");
    } finally {
      setArchiveBusyId(null);
    }
  }

  async function loadDemoGarden() {
    if (!activeHousehold) return;
    if (
      !confirm(
        "Add a demo garden map (L & U beds) plus sample plants? Existing plants are kept.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.seedDemo(activeHousehold.id);
      setMessage(
        res.message +
          ` (${res.plants?.length ?? 0} plants). Switch area to “Front garden” on the Map page.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Demo seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function stopDemoGarden() {
    if (!activeHousehold) return;
    if (
      !confirm(
        "Remove the demo garden (Demo Home map + plants tagged demo)? Your real plants and other maps stay.",
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const res = await api.clearDemo(activeHousehold.id);
      setMessage(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not remove demo");
    } finally {
      setBusy(false);
    }
  }

  async function enableBrowserNotifications() {
    if (typeof Notification === "undefined") {
      setMessage(
        "This browser does not support notifications. On iPhone: add RootCore to your Home Screen (Share → Add to Home Screen), then open it from there — Safari alone often blocks web notifications.",
      );
      return;
    }
    try {
      const perm = await Notification.requestPermission();
      setNotifStatus(perm);
      if (perm === "granted") {
        new Notification("RootCore", {
          body: "Notifications enabled. You’ll get a local reminder when you open the app and care is due (full push while closed needs a future server setup).",
          icon: "/favicon.svg",
        });
        setMessage("Browser notifications allowed for this device.");
      } else {
        setMessage("Notifications blocked or dismissed. You can change this in browser/site settings.");
      }
    } catch {
      setMessage("Could not request notification permission.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Profile, location, archive, demo garden, and optional online helpers.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <p>
            <span className="text-muted-foreground">Name:</span> {user?.display_name}
          </p>
          <p>
            <span className="text-muted-foreground">Login:</span> {user?.email}
            <span className="text-xs text-muted-foreground"> (username or email)</span>
          </p>
          <p>
            <span className="text-muted-foreground">Timezone:</span> {user?.timezone}
          </p>
        </CardContent>
      </Card>

      {activeHousehold && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Weather location &amp; provider</CardTitle>
              <CardDescription>
                Free providers, no paid keys. Used for heat, humidity, rain and when-to-water
                advice (morning/evening at your place).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => void saveLocation(e)}>
                <div className="space-y-1.5">
                  <Label htmlFor="lat">Latitude</Label>
                  <Input
                    id="lat"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    placeholder="52.52"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="lon">Longitude</Label>
                  <Input
                    id="lon"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    placeholder="13.405"
                    className="rounded-xl"
                  />
                </div>
                <div className="sm:col-span-2 flex flex-wrap gap-2">
                  <Button type="submit" disabled={busy || !isOwner} className="rounded-xl">
                    Save location
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={busy}
                    className="rounded-xl"
                    onClick={() => void refreshWeather()}
                  >
                    Refresh weather
                  </Button>
                </div>
              </form>
              <div className="space-y-1.5">
                <Label htmlFor="weather_provider">Weather source</Label>
                <select
                  id="weather_provider"
                  className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm"
                  value={weatherProvider}
                  disabled={!isOwner}
                  onChange={(e) =>
                    setWeatherProvider(e.target.value as "open_meteo" | "met_norway")
                  }
                >
                  <option value="open_meteo">
                    Open-Meteo (default) — global, free, no key
                  </option>
                  <option value="met_norway">
                    MET Norway (yr.no) — free, no key, good in Europe
                  </option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Save with helper settings below. Both are free and self-host friendly.
                </p>
              </div>
              {!isOwner && (
                <p className="text-xs text-muted-foreground">
                  Only the household owner can change location and providers.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Online helpers</CardTitle>
              <CardDescription>
                Photos, weather provider, and plant photo ID — all optional.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={(e) => void saveFeatures(e)}>
                <label className="flex items-start gap-3 rounded-xl border border-border p-3 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={autoCover}
                    onChange={(e) => setAutoCover(e.target.checked)}
                    disabled={!isOwner}
                  />
                  <span>
                    <span className="font-medium">Auto plant photos (Wikimedia)</span>
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      When you add a plant with a species name, fetch a free public photo. Turn off
                      for offline / no outbound image downloads.
                    </span>
                  </span>
                </label>

                <div className="space-y-1.5">
                  <Label htmlFor="plant_id_provider">Plant photo ID</Label>
                  <select
                    id="plant_id_provider"
                    className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm"
                    value={plantIdProvider}
                    disabled={!isOwner}
                    onChange={(e) =>
                      setPlantIdProvider(e.target.value as "plantnet" | "none")
                    }
                  >
                    <option value="plantnet">PlantNet (free key, good accuracy)</option>
                    <option value="none">Off — pick species from catalog only</option>
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Commercial apps (PictureThis, Plant.id) need paid APIs — PlantNet is the best
                    open option for self-hosting. iNaturalist is geared to observations, not pot
                    plants.
                  </p>
                </div>

                {plantIdProvider === "plantnet" && (
                  <div className="space-y-1.5">
                    <Label htmlFor="plantnet">PlantNet API key</Label>
                    <Input
                      id="plantnet"
                      type="password"
                      autoComplete="off"
                      value={plantnetKey}
                      onChange={(e) => setPlantnetKey(e.target.value)}
                      placeholder="From my.plantnet.org"
                      disabled={!isOwner}
                      className="rounded-xl"
                    />
                    <p className="text-xs text-muted-foreground">
                      Free key:{" "}
                      <a
                        className="text-primary underline"
                        href="https://my.plantnet.org/"
                        target="_blank"
                        rel="noreferrer"
                      >
                        my.plantnet.org
                      </a>
                    </p>
                  </div>
                )}

                <Button type="submit" disabled={busy || !isOwner} className="rounded-xl">
                  Save helper settings
                </Button>
              </form>
            </CardContent>
          </Card>
        </>
      )}

      {activeHousehold && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Archive</CardTitle>
              <CardDescription>
                Restored plants return to your collection. Permanent delete removes photos and
                history for that plant. Archived plants leave the calendar and map.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {archiveLoading ? (
                <FlowerLoader label="Loading archive…" />
              ) : archived.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No archived plants. Archive from a plant&apos;s detail page when you no longer
                  need it active.
                </p>
              ) : (
                <ul className="space-y-2">
                  {archived.map((p) => (
                    <li
                      key={p.id}
                      className="flex flex-col gap-2 rounded-xl border border-border bg-card/80 p-3 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0 flex items-center gap-3">
                        {p.cover_photo?.thumb_url || p.cover_photo?.display_url ? (
                          <img
                            src={
                              p.cover_photo.thumb_url ||
                              p.cover_photo.display_url ||
                              ""
                            }
                            alt=""
                            className="h-12 w-12 rounded-lg object-cover shrink-0"
                          />
                        ) : (
                          <span className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-lg shrink-0">
                            🪴
                          </span>
                        )}
                        <div className="min-w-0">
                          <p className="font-medium truncate">{p.nickname}</p>
                          <p className="text-xs text-muted-foreground">
                            {p.taxon?.scientific_name ?? "No species"}
                            {p.archived_at
                              ? ` · archived ${new Date(p.archived_at).toLocaleDateString()}`
                              : ""}
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 shrink-0">
                        <Button
                          size="sm"
                          className="rounded-xl"
                          disabled={archiveBusyId === p.id}
                          onClick={() => void restoreArchived(p.id)}
                        >
                          {archiveBusyId === p.id ? "…" : "Restore"}
                        </Button>
                        {canAdmin && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="rounded-xl text-destructive"
                            disabled={archiveBusyId === p.id}
                            onClick={() => void permanentDelete(p.id, p.nickname)}
                          >
                            Delete forever
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" className="rounded-xl" asChild>
                          <Link to={`/plants/${p.id}`}>View</Link>
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
              {!canAdmin && archived.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Permanent delete requires household admin or owner.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Demo garden</CardTitle>
              <CardDescription>
                One click: sample plants, an indoor room, and outdoor beds including L- and
                U-shaped freehand pots — great for trying the map.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button
                type="button"
                className="rounded-xl"
                disabled={busy}
                onClick={() => void loadDemoGarden()}
              >
                {busy ? "Working…" : "Load demo garden"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="rounded-xl text-destructive"
                disabled={busy}
                onClick={() => void stopDemoGarden()}
              >
                Stop / remove demo
              </Button>
              <Button type="button" variant="secondary" className="rounded-xl" asChild>
                <Link to="/layout">Open map</Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Bulk import plants</CardTitle>
              <CardDescription>
                Paste from HortusFox-style lists or CSV. Matches species in the catalog, sets outdoor
                for garden plants, and can fetch free cover photos.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                className="flex min-h-40 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm font-mono"
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                placeholder={IMPORT_PLACEHOLDER}
              />
              <p className="text-xs text-muted-foreground">
                Formats: nickname + scientific on next line; or{" "}
                <code className="text-[11px]">nickname,scientific,environment,notes</code>. Quantity
                in parentheses like <code className="text-[11px]">Rose (2)</code> creates two plants.
                Prefer the{" "}
                <Link to="/catalog" className="text-primary hover:underline">
                  photo catalog
                </Link>{" "}
                for one-offs.
              </p>
              <Button
                type="button"
                className="rounded-xl"
                disabled={busy || !importText.trim()}
                onClick={() => void runImport()}
              >
                {busy ? "Importing…" : "Import plants"}
              </Button>
              {importResult && <p className="text-sm font-medium text-primary">{importResult}</p>}
            </CardContent>
          </Card>
        </>
      )}

      {message && <p className="text-sm text-primary">{message}</p>}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Appearance & themes</CardTitle>
          <CardDescription>
            Blossom and meadow add soft flower patterns. Your choice is saved in this browser.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-border p-3 space-y-3 text-sm">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1"
                checked={ambientOn}
                onChange={(e) => setAmbientOn(e.target.checked)}
              />
              <span>
                <span className="font-medium">Garden animations</span>
                <span className="block text-xs text-muted-foreground mt-0.5">
                  Butterflies, bees, floating leaves and mountain silhouettes. Drag the slider for
                  how busy the sky feels (0 = none, 100 = a lot).
                </span>
              </span>
            </label>
            <div className="space-y-1.5 pl-0 sm:pl-7">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Calm</span>
                <span className="font-medium text-foreground tabular-nums">
                  {ambientOn ? ambientIntensity : 0}
                </span>
                <span>Busy</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={ambientOn ? ambientIntensity : 0}
                disabled={!ambientOn}
                onChange={(e) => setAmbientIntensity(Number(e.target.value))}
                className="w-full accent-primary disabled:opacity-40"
                aria-label="Animation intensity"
              />
              <p className="text-[11px] text-muted-foreground">
                {ambientOn
                  ? ambientIntensity === 0
                    ? "Slider at 0 — no flying critters (scenery off too)."
                    : ambientIntensity < 25
                      ? "A few visitors."
                      : ambientIntensity < 60
                        ? "Comfortable garden buzz."
                        : ambientIntensity < 85
                          ? "Lively meadow."
                          : "Full festival of bees and butterflies."
                  : "Turn on garden animations to use the slider."}
              </p>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {themes.map((t) => {
              const m = THEME_META[t as Theme];
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t as Theme)}
                  className={
                    "rounded-xl border px-3 py-3 text-left text-sm transition-colors " +
                    (theme === t
                      ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                      : "border-border hover:bg-muted/60")
                  }
                >
                  <span className="text-lg leading-none">{m.emoji}</span>
                  <p className="font-medium mt-1">{m.label}</p>
                  <p className="text-xs text-muted-foreground">{m.description}</p>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notifications (phone &amp; desktop)</CardTitle>
          <CardDescription>
            Self-hosted apps use the browser notification API. On iPhone this works best when you{" "}
            <strong>Add to Home Screen</strong> (iOS 16.4+). Native Apple Push would need extra
            Apple developer setup — not required for self-host.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Status:{" "}
            <span className="font-medium text-foreground">
              {notifStatus === "unsupported"
                ? "not available in this browser"
                : notifStatus}
            </span>
          </p>
          <Button
            type="button"
            variant="secondary"
            className="rounded-xl"
            onClick={() => void enableBrowserNotifications()}
          >
            Enable browser notifications
          </Button>
          <ul className="text-xs text-muted-foreground list-disc pl-4 space-y-1">
            <li>
              <strong>iPhone:</strong> Safari → Share → Add to Home Screen → open RootCore from
              the icon → enable notifications here.
            </li>
            <li>
              Reminders while the app is open work immediately; push while closed may need a future
              Web Push server (optional advanced feature).
            </li>
            <li>Calendar apps still work: export due tasks manually or check Today daily.</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Session</CardTitle>
        </CardHeader>
        <CardContent>
          <button
            type="button"
            className="text-sm text-destructive underline-offset-2 hover:underline"
            onClick={() => void logout()}
          >
            Log out
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
