import { type FormEvent, useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import {
  ENVIRONMENTS,
  GROWTH_STAGES,
  POT_MATERIALS,
  POT_SIZES,
  SOIL_TYPES,
  todayISODate,
} from "@/lib/plant-presets";
import { applyTaxonDefaults } from "@/lib/plant-defaults";
import type { LayoutSite, Taxon } from "@/lib/types";

export function PlantFormPage() {
  const { plantId } = useParams<{ plantId: string }>();
  const isEdit = Boolean(plantId) && plantId !== "new";
  const { activeHousehold } = useAuth();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(window.location.search);

  const [nickname, setNickname] = useState("");
  const [taxonQuery, setTaxonQuery] = useState(searchParams.get("name") || "");
  const [taxa, setTaxa] = useState<Taxon[]>([]);
  const [taxonId, setTaxonId] = useState<string | null>(searchParams.get("taxon"));
  const [selectedLabel, setSelectedLabel] = useState<string | null>(
    searchParams.get("name"),
  );
  const [environment, setEnvironment] = useState("indoor");
  const [potSizePreset, setPotSizePreset] = useState("2");
  const [potSizeCustom, setPotSizeCustom] = useState("");
  const [potMaterial, setPotMaterial] = useState("plastic");
  const [soilType, setSoilType] = useState("standard");
  const [growthStage, setGrowthStage] = useState("mature");
  const [acquiredAt, setAcquiredAt] = useState(todayISODate());
  const [lastFertilized, setLastFertilized] = useState("");
  const [tags, setTags] = useState("");
  const [notes, setNotes] = useState("");
  const [emoji, setEmoji] = useState("🪴");
  const [autoCover, setAutoCover] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(isEdit);
  // Location on create: space_id or space_id:container_id
  const [layoutSites, setLayoutSites] = useState<LayoutSite[]>([]);
  const [placeTarget, setPlaceTarget] = useState<string>("");

  // PlantNet identify + own photo as cover
  const [idBusy, setIdBusy] = useState(false);
  const [idCandidates, setIdCandidates] = useState<
    Array<{ score: number; scientific_name: string; common_names: string[] }>
  >([]);
  const [ownPhoto, setOwnPhoto] = useState<File | null>(null);
  const [ownPhotoPreview, setOwnPhotoPreview] = useState<string | null>(null);

  useEffect(() => {
    if (activeHousehold?.settings) {
      const s = activeHousehold.settings as { auto_cover_images?: boolean };
      if (typeof s.auto_cover_images === "boolean") setAutoCover(s.auto_cover_images);
    }
  }, [activeHousehold]);

  useEffect(() => {
    if (!activeHousehold || isEdit) return;
    void api
      .listSites(activeHousehold.id)
      .then(setLayoutSites)
      .catch(() => setLayoutSites([]));
  }, [activeHousehold, isEdit]);

  const placeOptions = (() => {
    const opts: Array<{ value: string; label: string }> = [
      { value: "", label: "None — place later on Map" },
    ];
    for (const site of layoutSites) {
      for (const sp of site.spaces) {
        opts.push({
          value: sp.id,
          label: `${site.name} · ${sp.name} (area)`,
        });
        for (const c of sp.containers) {
          opts.push({
            value: `${sp.id}:${c.id}`,
            label: `${site.name} · ${sp.name} · 🪴 ${c.name}`,
          });
        }
      }
    }
    return opts;
  })();

  useEffect(() => {
    if (!activeHousehold || !isEdit || !plantId) return;
    void (async () => {
      try {
        const plant = await api.getPlant(activeHousehold.id, plantId);
        setNickname(plant.nickname);
        setEnvironment(plant.environment);
        if (plant.pot_size_liters != null) {
          const v = String(plant.pot_size_liters);
          const match = POT_SIZES.find((p) => p.value === v);
          if (match) setPotSizePreset(v);
          else {
            setPotSizePreset("custom");
            setPotSizeCustom(v);
          }
        }
        setPotMaterial(plant.pot_material ?? "plastic");
        setSoilType(plant.soil_type ?? "standard");
        setGrowthStage(plant.growth_stage ?? "mature");
        setAcquiredAt(plant.acquired_at ?? todayISODate());
        setNotes(plant.notes ?? "");
        setTags(plant.tags.map((t) => t.name).join(", "));
        const em =
          plant.emoji ||
          (typeof plant.custom_attributes?.emoji === "string"
            ? plant.custom_attributes.emoji
            : "🪴");
        setEmoji(em || "🪴");
        if (plant.taxon) {
          setTaxonId(plant.taxon.id);
          setSelectedLabel(plant.taxon.scientific_name);
          setTaxonQuery(plant.taxon.scientific_name);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Failed to load plant");
      } finally {
        setLoading(false);
      }
    })();
  }, [activeHousehold, isEdit, plantId]);

  useEffect(() => {
    if (!taxonQuery || taxonQuery.length < 2) {
      setTaxa([]);
      return;
    }
    const t = setTimeout(() => {
      void api
        .searchTaxa(taxonQuery, activeHousehold?.id)
        .then(setTaxa)
        .catch(() => setTaxa([]));
    }, 200);
    return () => clearTimeout(t);
  }, [taxonQuery, activeHousehold?.id]);

  // Prefill taxon from catalog deep-link
  useEffect(() => {
    if (isEdit || !activeHousehold || !taxonId) return;
    const nickParam = searchParams.get("nick");
    if (nickParam && !nickname) setNickname(nickParam);
    void api
      .searchTaxa(taxonQuery || selectedLabel || "", activeHousehold.id)
      .then((list) => {
        const t = list.find((x) => x.id === taxonId) ?? list[0];
        if (t) applyTaxon(t);
      })
      .catch(() => undefined);
    // only on mount for deep link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeHousehold?.id]);

  function applyTaxon(t: Taxon) {
    setTaxonId(t.id);
    setSelectedLabel(t.scientific_name);
    setTaxonQuery(t.scientific_name);
    setTaxa([]);
    const defaults = applyTaxonDefaults(t);
    if (!nickname.trim() && defaults.nicknameHint) {
      setNickname(defaults.nicknameHint);
    }
    setEnvironment(defaults.environment);
    setSoilType(defaults.soilType);
    if (defaults.potMaterial) setPotMaterial(defaults.potMaterial);
    // Smart pot size from plant habit (not always XL)
    if (defaults.potSizePreset === "") {
      setPotSizePreset("none");
    } else {
      setPotSizePreset(defaults.potSizePreset);
    }
    if (defaults.tags.length && !tags.trim()) {
      setTags(defaults.tags.join(", "));
    }
  }

  function keepOwnPhoto(file: File | null) {
    if (ownPhotoPreview) URL.revokeObjectURL(ownPhotoPreview);
    setOwnPhoto(file);
    setOwnPhotoPreview(file ? URL.createObjectURL(file) : null);
  }

  async function onIdentifyFile(file: File | null) {
    if (!file || !activeHousehold) return;
    keepOwnPhoto(file); // always keep as plant photo (your own plant)
    setIdBusy(true);
    setError(null);
    setIdCandidates([]);
    try {
      const res = await api.identifyPlant(activeHousehold.id, file);
      setIdCandidates(res.candidates || []);
      if (!res.candidates?.length) {
        setError(
          "No ID matches — photo is still saved as your plant’s cover when you add it.",
        );
      }
    } catch (err) {
      // Still keep the photo even if identify fails / no PlantNet key
      setError(
        (err instanceof ApiError ? err.detail : "Identification failed") +
          " — your photo will still be used as the plant picture.",
      );
    } finally {
      setIdBusy(false);
    }
  }

  async function pickCandidate(c: {
    scientific_name: string;
    common_names: string[];
  }) {
    if (!activeHousehold) return;
    setTaxonQuery(c.scientific_name);
    // Try match in catalog
    try {
      const found = await api.searchTaxa(c.scientific_name, activeHousehold.id);
      const exact =
        found.find(
          (t) => t.scientific_name.toLowerCase() === c.scientific_name.toLowerCase(),
        ) ?? found[0];
      if (exact) {
        applyTaxon(exact);
      } else {
        setSelectedLabel(c.scientific_name);
        if (!nickname && c.common_names[0]) setNickname(c.common_names[0]);
      }
    } catch {
      setSelectedLabel(c.scientific_name);
    }
    setIdCandidates([]);
  }

  if (!activeHousehold) return <Navigate to="/plants" replace />;
  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;

  function potLiters(): number | null {
    if (potSizePreset === "none" || potSizePreset === "") return null;
    if (potSizePreset === "custom") {
      return potSizeCustom ? Number(potSizeCustom) : null;
    }
    return potSizePreset ? Number(potSizePreset) : null;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      nickname,
      taxon_id: taxonId,
      environment,
      pot_size_liters: potLiters(),
      pot_material: potMaterial || null,
      soil_type: soilType || null,
      growth_stage: growthStage || null,
      acquired_at: acquiredAt || null,
      notes: notes || null,
      custom_attributes: { emoji: emoji || "🪴" },
      tag_names: tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    };
    if (!isEdit) {
      // Prefer user's own photo; only fetch Wikimedia if no own photo
      body.auto_cover_image = autoCover && !ownPhoto;
      if (lastFertilized) body.last_fertilized_at = lastFertilized;
    }
    try {
      if (isEdit && plantId) {
        await api.updatePlant(activeHousehold.id, plantId, body);
        navigate(`/plants/${plantId}`);
      } else {
        const plant = await api.createPlant(activeHousehold.id, body as never);
        // Your photo (from identify or upload) becomes the cover — best for "my plant"
        if (ownPhoto) {
          try {
            await api.uploadPhoto(activeHousehold.id, plant.id, ownPhoto, {
              caption: "My plant photo",
              setCover: true,
            });
          } catch {
            /* plant still created */
          }
        }
        // Optional place into garden / room / pot
        if (placeTarget) {
          try {
            const [spaceId, containerId] = placeTarget.includes(":")
              ? placeTarget.split(":")
              : [placeTarget, null];
            const n = plant.nickname.length;
            await api.putPlacement(activeHousehold.id, plant.id, {
              space_id: spaceId,
              container_id: containerId,
              x: 40 + (n % 5) * 48,
              y: 40 + (n % 3) * 48,
            });
          } catch {
            /* placement optional */
          }
        }
        navigate(`/plants/${plant.id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  const selectClass =
    "flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <div>
        <Link
          to={isEdit ? `/plants/${plantId}` : "/plants"}
          className="text-sm text-muted-foreground hover:underline"
        >
          ← Back
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight mt-1">
          {isEdit ? "Edit plant" : "Add plant"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Pick from presets — change anything anytime. Set an emoji so it stands out on the map.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Emoji</CardTitle>
          <CardDescription>Shown on the map and plant list — pick any style you like.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {["🪴", "🌱", "🌿", "🌵", "🌳", "🌲", "🌴", "🍃", "🌸", "🌺", "🌻", "🌼", "🌹", "🌷", "🍄", "🍋", "🍅", "🌶️", "🥬", "🫐"].map(
              (em) => (
                <button
                  key={em}
                  type="button"
                  className={
                    "h-9 w-9 rounded-xl border text-lg " +
                    (emoji === em
                      ? "border-primary bg-primary/10 ring-1 ring-primary/30"
                      : "border-border hover:bg-muted")
                  }
                  onClick={() => setEmoji(em)}
                >
                  {em}
                </button>
              ),
            )}
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="emoji_custom" className="text-xs shrink-0">
              Or custom
            </Label>
            <Input
              id="emoji_custom"
              value={emoji}
              onChange={(e) => setEmoji(e.target.value.slice(0, 8))}
              className="rounded-xl h-9 max-w-[6rem] text-center text-lg"
              maxLength={8}
            />
          </div>
        </CardContent>
      </Card>

      {!isEdit && (
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" className="rounded-xl">
            <Link to="/catalog">📷 Browse catalog with photos</Link>
          </Button>
        </div>
      )}

      {!isEdit && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">📷 Your plant photo</CardTitle>
            <CardDescription>
              Upload a picture of <em>your</em> plant — used as the cover so you recognize it.
              Optional: try PlantNet identify (needs free API key in Settings).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={idBusy}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                if (f) void onIdentifyFile(f);
                else keepOwnPhoto(null);
              }}
            />
            {ownPhotoPreview && (
              <div className="flex items-center gap-3">
                <img
                  src={ownPhotoPreview}
                  alt="Your plant"
                  className="h-20 w-20 rounded-xl object-cover border border-border"
                />
                <div className="text-xs text-muted-foreground">
                  <p className="font-medium text-foreground">Will be the plant cover</p>
                  <button
                    type="button"
                    className="text-destructive underline"
                    onClick={() => keepOwnPhoto(null)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}
            {idBusy && <p className="text-xs text-muted-foreground">Identifying…</p>}
            {idCandidates.length > 0 && (
              <ul className="space-y-1 rounded-xl border border-border p-2">
                {idCandidates.map((c) => (
                  <li key={c.scientific_name + c.score}>
                    <button
                      type="button"
                      className="w-full rounded-lg px-2 py-1.5 text-left text-sm hover:bg-accent"
                      onClick={() => void pickCandidate(c)}
                    >
                      <span className="font-medium italic">{c.scientific_name}</span>
                      <span className="text-muted-foreground">
                        {" "}
                        · {Math.round(c.score * 100)}%
                        {c.common_names[0] ? ` · ${c.common_names[0]}` : ""}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <label className="flex items-start gap-3 text-sm pt-1 border-t border-border/60">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4"
                checked={autoCover}
                onChange={(e) => setAutoCover(e.target.checked)}
              />
              <span>
                <span className="font-medium">Also try free species photo</span>
                <span className="block text-xs text-muted-foreground mt-0.5">
                  From Wikipedia/Commons if you didn’t upload your own. Skipped when you have a
                  personal photo.
                </span>
              </span>
            </label>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Details</CardTitle>
          <CardDescription>
            Picking a species fills outdoor/indoor, soil, and pot defaults automatically.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
            <div className="space-y-1.5">
              <Label htmlFor="nickname">Nickname</Label>
              <Input
                id="nickname"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                required
                placeholder="Monstera by the window"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-1.5 relative">
              <Label htmlFor="taxon">Species</Label>
              <Input
                id="taxon"
                value={taxonQuery}
                onChange={(e) => {
                  setTaxonQuery(e.target.value);
                  setTaxonId(null);
                  setSelectedLabel(null);
                }}
                placeholder="Search scientific or common name…"
                autoComplete="off"
                className="rounded-xl"
              />
              {selectedLabel && (
                <p className="text-xs text-primary">
                  Selected: {selectedLabel}
                  {environment === "outdoor" ? " · will default outdoor" : ""}
                </p>
              )}
              {taxa.length > 0 && !taxonId && (
                <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-xl border border-border bg-card shadow-md">
                  {taxa.map((t) => {
                    const d = applyTaxonDefaults(t);
                    return (
                      <li key={t.id}>
                        <button
                          type="button"
                          className="w-full px-3 py-2 text-left text-sm hover:bg-accent"
                          onClick={() => applyTaxon(t)}
                        >
                          <span className="font-medium italic">{t.scientific_name}</span>
                          {t.common_names[0] && (
                            <span className="text-muted-foreground"> — {t.common_names[0]}</span>
                          )}
                          <span className="block text-[11px] text-muted-foreground">
                            {d.environment === "outdoor" ? "🌳 Outdoor" : "🪴 Indoor"}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            {!isEdit && (
              <div className="space-y-1.5">
                <Label htmlFor="place">Map location (optional)</Label>
                <select
                  id="place"
                  className={selectClass}
                  value={placeTarget}
                  onChange={(e) => {
                    const v = e.target.value;
                    setPlaceTarget(v);
                    // Garden beds → outdoor care automatically
                    if (v) {
                      const spaceId = v.includes(":") ? v.split(":")[0] : v;
                      const sp = layoutSites
                        .flatMap((s) => s.spaces.map((x) => ({ ...x, siteName: s.name })))
                        .find((x) => x.id === spaceId);
                      if (sp && (sp.kind === "garden" || /garden|yard|bed|outdoor/i.test(sp.name))) {
                        setEnvironment("outdoor");
                      } else if (sp && (sp.kind === "room" || /living|kitchen|indoor|room/i.test(sp.name))) {
                        setEnvironment("indoor");
                      }
                    }
                  }}
                >
                  {placeOptions.map((o) => (
                    <option key={o.value || "none"} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground">
                  {layoutSites.length === 0
                    ? "No gardens yet — create one under Map, or leave as none."
                    : "Garden locations set outdoor care automatically."}
                </p>
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="environment">Indoor / outdoor</Label>
                <select
                  id="environment"
                  className={selectClass}
                  value={environment}
                  onChange={(e) => setEnvironment(e.target.value)}
                >
                  {ENVIRONMENTS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="growth">Growth stage</Label>
                <select
                  id="growth"
                  className={selectClass}
                  value={growthStage}
                  onChange={(e) => setGrowthStage(e.target.value)}
                >
                  {GROWTH_STAGES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="pot">Pot size</Label>
                <select
                  id="pot"
                  className={selectClass}
                  value={potSizePreset}
                  onChange={(e) => setPotSizePreset(e.target.value)}
                >
                  {POT_SIZES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                {potSizePreset === "custom" && (
                  <Input
                    type="number"
                    min={0.1}
                    step={0.1}
                    placeholder="Litres"
                    value={potSizeCustom}
                    onChange={(e) => setPotSizeCustom(e.target.value)}
                    className="mt-1 rounded-xl"
                  />
                )}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="material">Pot material</Label>
                <select
                  id="material"
                  className={selectClass}
                  value={potMaterial}
                  onChange={(e) => setPotMaterial(e.target.value)}
                >
                  {POT_MATERIALS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="soil">Soil type</Label>
                <select
                  id="soil"
                  className={selectClass}
                  value={soilType}
                  onChange={(e) => setSoilType(e.target.value)}
                >
                  {SOIL_TYPES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="acquired">Got it / planted on</Label>
                <Input
                  id="acquired"
                  type="date"
                  value={acquiredAt}
                  onChange={(e) => setAcquiredAt(e.target.value)}
                  className="rounded-xl"
                />
                <button
                  type="button"
                  className="text-xs text-primary hover:underline"
                  onClick={() => setAcquiredAt(todayISODate())}
                >
                  Use today
                </button>
              </div>
              {!isEdit && (
                <div className="space-y-1.5">
                  <Label htmlFor="fert">Last fertilized (optional)</Label>
                  <Input
                    id="fert"
                    type="date"
                    value={lastFertilized}
                    onChange={(e) => setLastFertilized(e.target.value)}
                    className="rounded-xl"
                  />
                  <button
                    type="button"
                    className="text-xs text-primary hover:underline"
                    onClick={() => setLastFertilized(todayISODate())}
                  >
                    Use today
                  </button>
                </div>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tags">Tags (comma-separated)</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="trailing, pet-safe"
                className="rounded-xl"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="notes">Notes</Label>
              <textarea
                id="notes"
                className="flex min-h-24 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full h-11 rounded-xl" disabled={busy}>
              {busy ? "Saving…" : isEdit ? "Save changes" : "Add plant"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
