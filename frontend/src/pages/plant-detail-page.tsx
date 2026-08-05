import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { PhotoSearchPicker } from "@/components/photo-search-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import {
  CARE_GLOSSARY,
  DROUGHT_LABELS,
  HUMIDITY_LABELS,
  MONTHS_FULL,
  MONTHS_SHORT,
  lightDisplay,
  moistureDisplay,
  moistureDrops,
} from "@/lib/care-labels";
import type { CareEvent, Plant, PlantPhoto, WateringInfo } from "@/lib/types";
import { labelEnvironment, labelPotMaterial, labelSoil } from "@/lib/labels";
import {
  amountDetail,
  amountHeadline,
  formatNextWater,
  plainFactors,
  urgencyCopy,
} from "@/lib/watering-copy";

export function PlantDetailPage() {
  const { plantId } = useParams<{ plantId: string }>();
  const { activeHousehold } = useAuth();
  const [plant, setPlant] = useState<Plant | null>(null);
  const [photos, setPhotos] = useState<PlantPhoto[]>([]);
  const [watering, setWatering] = useState<WateringInfo | null>(null);
  const [events, setEvents] = useState<CareEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [wateringBusy, setWateringBusy] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [justWatered, setJustWatered] = useState(false);
  const [caption, setCaption] = useState("");
  const [tab, setTab] = useState<"care" | "info" | "photos" | "timeline">("care");
  const [coverBusy, setCoverBusy] = useState(false);

  const load = useCallback(async () => {
    if (!activeHousehold || !plantId) return;
    setLoading(true);
    setError(null);
    try {
      const [p, ph, w, ev] = await Promise.all([
        api.getPlant(activeHousehold.id, plantId),
        api.listPhotos(activeHousehold.id, plantId),
        api.getWatering(activeHousehold.id, plantId),
        api.listPlantEvents(activeHousehold.id, plantId),
      ]);
      setPlant(p);
      setPhotos(ph);
      setWatering(w);
      setEvents(ev);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load plant");
      setPlant(null);
    } finally {
      setLoading(false);
    }
  }, [activeHousehold, plantId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!activeHousehold) return <Navigate to="/plants" replace />;
  if (loading) return <FlowerLoader label="Loading plant…" />;
  if (!plant) {
    return (
      <p className="text-sm text-destructive" role="alert">
        {error ?? "Plant not found"}
      </p>
    );
  }

  const care = plant.taxon?.care_profile;
  const extra = care?.extra ?? {};
  const bloomMonths = Array.isArray(extra.bloom_months)
    ? (extra.bloom_months as number[]).filter((m) => m >= 1 && m <= 12)
    : [];
  const canWrite =
    activeHousehold.role === "owner" ||
    activeHousehold.role === "admin" ||
    activeHousehold.role === "member";

  let potLabel = "In ground / no pot";
  if (plant.pot_size_liters != null) {
    const mat = labelPotMaterial(plant.pot_material);
    potLabel =
      mat !== "—"
        ? plant.pot_size_liters + " L · " + mat
        : plant.pot_size_liters + " L";
  } else if (plant.pot_material) {
    potLabel = labelPotMaterial(plant.pot_material);
  }

  let waterIntervalLabel = "—";
  if (care?.baseline_interval_days_min != null) {
    waterIntervalLabel =
      String(care.baseline_interval_days_min) +
      "–" +
      String(care.baseline_interval_days_max) +
      " days";
  }

  let toxicityLabel = "—";
  if (care?.toxic_to_pets === true) toxicityLabel = "⚠️ Toxic to pets";
  if (care?.toxic_to_pets === false) toxicityLabel = "✅ Generally pet-safe";

  const light = lightDisplay(care?.light);
  const moisture = moistureDisplay(care?.moisture_preference);

  const coverSrc = plant.cover_photo?.display_url ?? plant.cover_photo?.thumb_url ?? "";
  const editPath = "/plants/" + plant.id + "/edit";
  const commonNames = plant.taxon?.common_names?.join(" / ") ?? "";

  async function onUpload(file: File | null) {
    if (!file || !activeHousehold || !plantId) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadPhoto(activeHousehold.id, plantId, file, {
        caption: caption || undefined,
        setCover: photos.length === 0,
      });
      setCaption("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function archive() {
    if (!activeHousehold || !plantId) return;
    if (!confirm("Archive this plant? It will leave the active list and calendar.")) return;
    await api.archivePlant(activeHousehold.id, plantId);
    await load();
  }

  async function restore() {
    if (!activeHousehold || !plantId) return;
    setCoverBusy(true);
    setError(null);
    try {
      await api.restorePlant(activeHousehold.id, plantId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not restore plant");
    } finally {
      setCoverBusy(false);
    }
  }

  async function logWater(amount: "light" | "normal" | "deep" = "normal") {
    if (!activeHousehold || !plantId) return;
    setWateringBusy(true);
    setError(null);
    try {
      await api.waterPlant(activeHousehold.id, plantId, { amount });
      setJustWatered(true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not log watering");
    } finally {
      setWateringBusy(false);
    }
  }

  async function sendFeedback(rating: "too_dry" | "ok" | "too_wet") {
    if (!activeHousehold || !plantId) return;
    setWateringBusy(true);
    try {
      setWatering(await api.wateringFeedback(activeHousehold.id, plantId, rating));
      setJustWatered(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Feedback failed");
    } finally {
      setWateringBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/plants" className="text-sm text-muted-foreground hover:underline">
            ← Back to plants
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight mt-1">{plant.nickname}</h1>
          <p className="text-muted-foreground italic">
            {plant.taxon?.scientific_name ?? "Unknown species"}
          </p>
          {commonNames ? (
            <p className="text-sm text-muted-foreground">{commonNames}</p>
          ) : null}
        </div>
        {canWrite && (
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="secondary">
              <Link to={editPath}>Edit</Link>
            </Button>
            <Button
              variant="outline"
              disabled={coverBusy}
              title="Create a duplicate with the same species and settings"
              onClick={() => {
                if (!confirm(`Duplicate “${plant.nickname}”? A new plant will be created.`)) return;
                void (async () => {
                  setCoverBusy(true);
                  setError(null);
                  try {
                    const copy = await api.copyPlant(activeHousehold.id, plant.id);
                    window.location.href = "/plants/" + copy.id;
                  } catch (err) {
                    setError(err instanceof ApiError ? err.detail : "Could not duplicate plant");
                  } finally {
                    setCoverBusy(false);
                  }
                })();
              }}
            >
              Duplicate
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                void api.downloadLabelPdf(activeHousehold.id, plant.id).then((blob) => {
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "label-" + plant.nickname + ".pdf";
                  a.click();
                  URL.revokeObjectURL(url);
                })
              }
            >
              Print label
            </Button>
            {plant.status === "active" && (
              <Button variant="outline" onClick={() => void archive()}>
                Archive
              </Button>
            )}
            {plant.status === "archived" && (
              <Button variant="default" disabled={coverBusy} onClick={() => void restore()}>
                Restore from archive
              </Button>
            )}
          </div>
        )}
      </div>

      {plant.status === "archived" && (
        <p className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm">
          This plant is archived. It is hidden from the main list and calendar. Restore it here or
          under <Link className="text-primary underline" to="/settings">Settings → Archive</Link>.
        </p>
      )}


      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1 overflow-hidden">
          <div className="aspect-square bg-muted relative">
            {coverSrc ? (
              <img src={coverSrc} alt={plant.nickname} className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground text-sm p-4">
                <span className="text-4xl">
                  {plant.emoji ||
                    (typeof plant.custom_attributes?.emoji === "string"
                      ? plant.custom_attributes.emoji
                      : "🌱")}
                </span>
                <span>No photo yet</span>
              </div>
            )}
          </div>
          {canWrite && (
            <CardContent className="space-y-2 py-3 border-t border-border">
              <PhotoSearchPicker
                householdId={activeHousehold.id}
                plantId={plant.id}
                defaultQuery={
                  plant.taxon?.scientific_name ||
                  plant.taxon?.common_names?.[0] ||
                  plant.nickname
                }
                onPicked={async () => {
                  setError(null);
                  await load();
                }}
              />
              {plant.taxon && (
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl w-full"
                  disabled={coverBusy}
                  onClick={() => {
                    void (async () => {
                      setCoverBusy(true);
                      setError(null);
                      try {
                        await api.fetchAutoCover(activeHousehold.id, plant.id);
                        await load();
                      } catch (err) {
                        setError(
                          err instanceof ApiError
                            ? err.detail
                            : "Could not fetch free photo",
                        );
                      } finally {
                        setCoverBusy(false);
                      }
                    })();
                  }}
                >
                  {coverBusy ? "Fetching…" : "⚡ Auto-pick first match"}
                </Button>
              )}
              <p className="text-[11px] text-muted-foreground">
                Search free Wikimedia photos and choose one, or upload under Photos.
              </p>
            </CardContent>
          )}
          {/* Quick care chips */}
          {care && (
            <CardContent className="space-y-2 py-3 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Light</span>
                <span className="font-medium text-right">
                  {light.emoji} {light.label}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">Moisture</span>
                <span className="font-medium" title={moisture.hint}>
                  {moistureDrops(care.moisture_preference)}
                </span>
              </div>
              {bloomMonths.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Bloom</p>
                  <BloomBar months={bloomMonths} />
                </div>
              )}
            </CardContent>
          )}
        </Card>

        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Overview</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
              <Info label="Status" value={plant.status} />
              <Info label="Environment" value={labelEnvironment(plant.environment)} />
              <Info label="Pot" value={potLabel} />
              <Info label="Soil" value={labelSoil(plant.soil_type)} />
              <Info label="Acquired" value={plant.acquired_at ?? "—"} />
              <div className="sm:col-span-2">
                <p className="text-xs text-muted-foreground">Tags</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {plant.tags.length === 0 ? (
                    <span>—</span>
                  ) : (
                    plant.tags.map((t) => (
                      <span key={t.id} className="rounded bg-accent px-2 py-0.5 text-xs">
                        {t.name}
                      </span>
                    ))
                  )}
                </div>
              </div>
              {plant.notes ? (
                <div className="sm:col-span-2">
                  <p className="text-xs text-muted-foreground">Notes</p>
                  <p className="whitespace-pre-wrap">{plant.notes}</p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {watering ? (
            <WateringCard
              watering={watering}
              canWrite={canWrite}
              busy={wateringBusy}
              justWatered={justWatered}
              showDetails={showDetails}
              onToggleDetails={() => setShowDetails((v) => !v)}
              onWater={(amount) => void logWater(amount)}
              onFeedback={(r) => void sendFeedback(r)}
              onSkipFeedback={() => setJustWatered(false)}
            />
          ) : null}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-2">
        {(
          [
            ["care", "🌿 Care"],
            ["info", "ℹ️ Info"],
            ["timeline", "📜 Timeline"],
            ["photos", "📷 Photos"],
          ] as const
        ).map(([k, label]) => (
          <Button
            key={k}
            size="sm"
            variant={tab === k ? "default" : "ghost"}
            className="rounded-xl"
            onClick={() => setTab(k)}
          >
            {label}
          </Button>
        ))}
      </div>

      {tab === "care" && (
        <div className="grid gap-4 lg:grid-cols-2">
          {care ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Species care profile</CardTitle>
                <CardDescription>Defaults for this taxon — adjust watering via feedback.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <CareRow
                  emoji={light.emoji}
                  label="Light"
                  value={light.label}
                  hint={light.hint}
                />
                <CareRow
                  emoji="💧"
                  label="Moisture"
                  value={`${moisture.label}  ${moistureDrops(care.moisture_preference)}`}
                  hint={moisture.hint}
                />
                <CareRow
                  emoji="🌵"
                  label="Drought tolerance"
                  value={
                    care.drought_tolerance
                      ? DROUGHT_LABELS[care.drought_tolerance] ?? care.drought_tolerance
                      : "—"
                  }
                />
                <CareRow
                  emoji="💨"
                  label="Humidity"
                  value={
                    care.humidity_preference
                      ? HUMIDITY_LABELS[care.humidity_preference] ?? care.humidity_preference
                      : "—"
                  }
                />
                <CareRow emoji="⏱" label="Baseline water interval" value={waterIntervalLabel} />
                <CareRow emoji="🐾" label="Pets" value={toxicityLabel} />
                {typeof extra.fertilize_interval_days === "number" && (
                  <CareRow
                    emoji="🌿"
                    label="Fertilize about every"
                    value={`${extra.fertilize_interval_days} days (growing season)`}
                  />
                )}
                {typeof extra.repot_every_months === "number" && (
                  <CareRow
                    emoji="🪴"
                    label="Repot about every"
                    value={`${extra.repot_every_months} months`}
                  />
                )}
                {care.soil_notes ? (
                  <div>
                    <p className="text-xs text-muted-foreground">Soil notes</p>
                    <p>{care.soil_notes}</p>
                  </div>
                ) : null}
                {care.fertilize_notes ? (
                  <div>
                    <p className="text-xs text-muted-foreground">Fertilize notes</p>
                    <p>{care.fertilize_notes}</p>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-8 text-sm text-muted-foreground">
                No species linked — edit the plant and pick a taxon for care defaults.
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">🌸 Bloom calendar</CardTitle>
              <CardDescription>
                Typical flowering months (outdoor climates vary). Prune is often suggested after the
                last bloom month.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {bloomMonths.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No bloom months in the seed profile for this species.
                </p>
              ) : (
                <div className="space-y-3">
                  <BloomBar months={bloomMonths} large />
                  <p className="text-sm text-muted-foreground">
                    Blooms roughly{" "}
                    {bloomMonths.map((m) => MONTHS_FULL[m - 1]).join(", ")}.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "info" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">What do these mean?</CardTitle>
            <CardDescription>
              Quick glossary for care fields and calendar tasks.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {CARE_GLOSSARY.map((g) => (
              <div key={g.term} className="rounded-xl border border-border bg-muted/30 px-3 py-2.5">
                <p className="font-medium text-sm">{g.term}</p>
                <p className="text-sm text-muted-foreground mt-0.5">{g.body}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {tab === "timeline" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Plant timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground">No care events yet.</p>
            ) : (
              <ul className="divide-y divide-border text-sm">
                {events.map((ev) => (
                  <li key={ev.id} className="py-2 flex justify-between gap-2">
                    <span className="capitalize font-medium">
                      {ev.type.replaceAll("_", " ")}
                      {ev.actor_name ? (
                        <span className="text-muted-foreground font-normal">
                          {" "}
                          · {ev.actor_name}
                        </span>
                      ) : null}
                    </span>
                    <time className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(ev.occurred_at).toLocaleString()}
                    </time>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      {tab === "photos" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Photos</CardTitle>
            <CardDescription>
              Upload your own, or search free Wikimedia photos for a cover.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {canWrite ? (
              <>
                <PhotoSearchPicker
                  householdId={activeHousehold.id}
                  plantId={plant.id}
                  defaultQuery={
                    plant.taxon?.scientific_name ||
                    plant.taxon?.common_names?.[0] ||
                    plant.nickname
                  }
                  onPicked={async () => {
                    setError(null);
                    await load();
                  }}
                />
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                  <div className="space-y-1.5 flex-1">
                    <Label htmlFor="caption">Caption (optional)</Label>
                    <Input
                      id="caption"
                      value={caption}
                      onChange={(e) => setCaption(e.target.value)}
                      placeholder="After repot"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="file">Upload</Label>
                    <Input
                      id="file"
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={uploading}
                      onChange={(e) => void onUpload(e.target.files?.[0] ?? null)}
                    />
                  </div>
                </div>
              </>
            ) : null}

            {photos.length === 0 ? (
              <p className="text-sm text-muted-foreground">No photos yet.</p>
            ) : (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                {photos.map((ph) => (
                  <li
                    key={ph.id}
                    className="group relative overflow-hidden rounded-lg border border-border"
                  >
                    <img
                      src={ph.thumb_url ?? ph.display_url ?? ""}
                      alt={ph.caption ?? "Plant photo"}
                      className="aspect-square w-full object-cover"
                    />
                    {ph.is_cover ? (
                      <span className="absolute left-1 top-1 rounded bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">
                        Cover
                      </span>
                    ) : null}
                    {canWrite && !ph.is_cover ? (
                      <button
                        type="button"
                        className="absolute bottom-1 right-1 rounded bg-card/90 px-2 py-0.5 text-[10px] opacity-0 group-hover:opacity-100"
                        onClick={() =>
                          void api.setCoverPhoto(activeHousehold.id, plant.id, ph.id).then(load)
                        }
                      >
                        Set cover
                      </button>
                    ) : null}
                    {ph.caption ? (
                      <p className="truncate px-2 py-1 text-xs text-muted-foreground">{ph.caption}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function BloomBar({ months, large }: { months: number[]; large?: boolean }) {
  const set = new Set(months);
  return (
    <div className={"grid grid-cols-12 gap-0.5 " + (large ? "gap-1" : "")}>
      {MONTHS_SHORT.map((label, i) => {
        const on = set.has(i + 1);
        return (
          <div
            key={label + i}
            title={MONTHS_FULL[i] + (on ? " · blooming" : "")}
            className={
              "flex flex-col items-center rounded " +
              (large ? "py-2" : "py-1") +
              " " +
              (on
                ? "bg-pink-500/80 text-white shadow-sm"
                : "bg-muted text-muted-foreground")
            }
          >
            <span className={large ? "text-xs font-semibold" : "text-[9px] font-medium"}>
              {label}
            </span>
            {large && on ? <span className="text-[10px]">🌸</span> : null}
          </div>
        );
      })}
    </div>
  );
}

function CareRow({
  emoji,
  label,
  value,
  hint,
}: {
  emoji: string;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="flex gap-3">
      <span className="text-lg leading-none mt-0.5 w-6 text-center">{emoji}</span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-medium capitalize">{value}</p>
        {hint ? <p className="text-xs text-muted-foreground mt-0.5">{hint}</p> : null}
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}

function WateringCard({
  watering,
  canWrite,
  busy,
  justWatered,
  showDetails,
  onToggleDetails,
  onWater,
  onFeedback,
  onSkipFeedback,
}: {
  watering: WateringInfo;
  canWrite: boolean;
  busy: boolean;
  justWatered: boolean;
  showDetails: boolean;
  onToggleDetails: () => void;
  onWater: (amount: "light" | "normal" | "deep") => void;
  onFeedback: (r: "too_dry" | "ok" | "too_wet") => void;
  onSkipFeedback: () => void;
}) {
  const u = urgencyCopy(watering.urgency);
  const tone =
    u.tone === "bad"
      ? "border-destructive/40 bg-destructive/5"
      : u.tone === "warn"
        ? "border-amber-500/40 bg-amber-500/5"
        : "border-primary/30 bg-primary/5";

  const amountKey = (watering.recommended_amount || "normal") as "light" | "normal" | "deep";

  return (
    <Card className={tone}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{u.title}</CardTitle>
            <CardDescription className="text-sm mt-1">{u.hint}</CardDescription>
          </div>
          <span className="rounded-full bg-background/80 px-2.5 py-1 text-xs font-semibold shrink-0">
            {amountHeadline(watering)}
            {watering.amount_ml != null ? ` · ~${watering.amount_ml} ml` : ""}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {/* Big clear schedule card */}
        <div className="rounded-xl border border-border/80 bg-background/80 p-3 space-y-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              When
            </p>
            <p className="font-semibold text-base mt-0.5">
              {formatNextWater(watering.next_due_at)}
            </p>
            <p className="text-sm text-muted-foreground mt-0.5">
              {watering.best_time_label || "Morning"}
              {watering.best_time_local ? ` · ${watering.best_time_local}` : ""}
            </p>
          </div>
          <div className="border-t border-border/60 pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              How much
            </p>
            <p className="font-semibold text-base mt-0.5">{amountHeadline(watering)}</p>
            <p className="text-sm leading-snug mt-1 text-foreground/90">
              {amountDetail(watering)}
            </p>
          </div>
          {watering.interval_days != null && (
            <p className="text-xs text-muted-foreground">
              About every <strong>{Math.round(watering.interval_days)}</strong> days right now
              {watering.moisture_score != null
                ? ` · soil moisture estimate ${Math.round(watering.moisture_score * 100)}%`
                : ""}
            </p>
          )}
        </div>

        {watering.schedule_plain && (
          <p className="text-sm leading-relaxed rounded-lg bg-primary/5 border border-primary/15 px-3 py-2">
            {watering.schedule_plain}
          </p>
        )}

        {watering.weather_note && (
          <p className="text-xs text-muted-foreground rounded-lg border border-border px-3 py-2">
            🌤 {watering.weather_note}
          </p>
        )}

        {watering.advice?.check_soil && (
          <p className="text-xs text-muted-foreground">💡 {watering.advice.check_soil}</p>
        )}

        {canWrite && !justWatered ? (
          <div className="space-y-2">
            <Button
              className="w-full h-11"
              disabled={busy}
              onClick={() => onWater(amountKey)}
            >
              {busy
                ? "Saving…"
                : `I watered · ${amountHeadline(watering)}${
                    watering.amount_ml != null ? ` (~${watering.amount_ml} ml)` : ""
                  }`}
            </Button>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                size="sm"
                className="rounded-xl"
                disabled={busy}
                onClick={() => onWater("light")}
              >
                Light only
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="rounded-xl"
                disabled={busy}
                onClick={() => onWater("normal")}
              >
                Normal
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="rounded-xl"
                disabled={busy}
                onClick={() => onWater("deep")}
              >
                Deep soak
              </Button>
            </div>
          </div>
        ) : null}

        {canWrite && justWatered ? (
          <div className="rounded-xl border border-border bg-background/80 p-3 space-y-2">
            <p className="font-medium">How was the soil when you watered?</p>
            <p className="text-xs text-muted-foreground">
              This helps RootCore learn your plant — optional, takes one tap.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onFeedback("too_dry")}>
                Already very dry
              </Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onFeedback("ok")}>
                About right
              </Button>
              <Button size="sm" variant="outline" disabled={busy} onClick={() => onFeedback("too_wet")}>
                Still quite wet
              </Button>
              <Button size="sm" variant="ghost" disabled={busy} onClick={onSkipFeedback}>
                Skip
              </Button>
            </div>
          </div>
        ) : null}

        <button
          type="button"
          className="text-xs text-muted-foreground underline-offset-2 hover:underline"
          onClick={onToggleDetails}
        >
          {showDetails ? "Hide details" : "Show how this was calculated"}
        </button>

        {showDetails ? (
          <ul className="space-y-1.5 rounded-lg bg-background/70 p-3 text-xs text-muted-foreground">
            {plainFactors(watering).map((line) => (
              <li key={line}>· {line}</li>
            ))}
            {watering.confidence != null ? (
              <li>
                · Estimate quality:{" "}
                {watering.confidence < 0.4
                  ? "learning (log more waterings)"
                  : watering.confidence < 0.7
                    ? "getting better"
                    : "fairly reliable for this plant"}
              </li>
            ) : null}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
