import { Copy, Plus, Search, Sprout } from "lucide-react";
import { type MouseEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { PhotoSearchPicker } from "@/components/photo-search-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { labelEnvironment } from "@/lib/labels";
import type { LayoutSite, Plant } from "@/lib/types";

type ZoneKey = "all" | "unassigned" | string;

export function PlantsPage() {
  const { activeHousehold } = useAuth();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [sites, setSites] = useState<LayoutSite[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [zone, setZone] = useState<ZoneKey>("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [photoPlantId, setPhotoPlantId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeHousehold) {
      setPlants([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [data, layout] = await Promise.all([
        api.listPlants(activeHousehold.id, { q: q || undefined, limit: 100 }),
        api.listSites(activeHousehold.id).catch(() => [] as LayoutSite[]),
      ]);
      setPlants(data.items);
      setTotal(data.total);
      setSites(layout);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load plants");
    } finally {
      setLoading(false);
    }
  }, [activeHousehold, q]);

  useEffect(() => {
    const t = setTimeout(() => void load(), 200);
    return () => clearTimeout(t);
  }, [load]);

  // plant_id → "Site / Space" or pot path
  const plantZone = useMemo(() => {
    const map = new Map<string, { spaceId: string; label: string }>();
    for (const site of sites) {
      for (const sp of site.spaces) {
        const potNames = new Map(sp.containers.map((c) => [c.id, c.name]));
        for (const pl of sp.placements) {
          const pot = pl.container_id ? potNames.get(pl.container_id) : null;
          map.set(pl.plant_id, {
            spaceId: sp.id,
            label: pot
              ? `${site.name} · ${sp.name} · ${pot}`
              : `${site.name} · ${sp.name}`,
          });
        }
      }
    }
    return map;
  }, [sites]);

  const zones = useMemo(() => {
    const list: Array<{ id: ZoneKey; label: string; count: number }> = [
      { id: "all", label: "All plants", count: plants.length },
    ];
    let unassigned = 0;
    const bySpace = new Map<string, { label: string; count: number }>();
    for (const p of plants) {
      const z = plantZone.get(p.id);
      if (!z) {
        unassigned += 1;
        continue;
      }
      const cur = bySpace.get(z.spaceId) ?? {
        label: z.label.split(" · ").slice(0, 2).join(" · "),
        count: 0,
      };
      cur.count += 1;
      bySpace.set(z.spaceId, cur);
    }
    list.push({ id: "unassigned", label: "Unassigned", count: unassigned });
    for (const [id, v] of [...bySpace.entries()].sort((a, b) =>
      a[1].label.localeCompare(b[1].label),
    )) {
      list.push({ id, label: v.label, count: v.count });
    }
    return list;
  }, [plants, plantZone]);

  const filtered = useMemo(() => {
    if (zone === "all") return plants;
    if (zone === "unassigned") return plants.filter((p) => !plantZone.has(p.id));
    return plants.filter((p) => plantZone.get(p.id)?.spaceId === zone);
  }, [plants, zone, plantZone]);

  async function copyPlant(plantId: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!activeHousehold) return;
    setCopyingId(plantId);
    setError(null);
    try {
      const copy = await api.copyPlant(activeHousehold.id, plantId);
      setToast(`Duplicated as “${copy.nickname}”`);
      await load();
      setTimeout(() => setToast(null), 3500);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not copy plant");
    } finally {
      setCopyingId(null);
    }
  }

  if (!activeHousehold) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Select or create a household to manage plants.{" "}
          <Link className="text-primary underline-offset-2 hover:underline" to="/household">
            Household settings
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Your plants</h1>
          <p className="text-muted-foreground text-sm">
            {total} living in {activeHousehold.name}
            {zone !== "all" ? ` · showing ${filtered.length}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" className="rounded-xl">
            <Link to="/catalog">
              <Search className="h-4 w-4" />
              Catalog
            </Link>
          </Button>
          <Button asChild className="rounded-xl">
            <Link to="/plants/new">
              <Plus className="h-4 w-4" />
              Add plant
            </Link>
          </Button>
        </div>
      </div>

      {/* Zone filters */}
      <div className="flex flex-wrap gap-1.5">
        {zones.map((z) => (
          <button
            key={z.id}
            type="button"
            onClick={() => setZone(z.id)}
            className={
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors " +
              (zone === z.id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-muted-foreground hover:bg-muted")
            }
          >
            {z.label}
            <span className="ml-1 opacity-70 tabular-nums">{z.count}</span>
          </button>
        ))}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9 rounded-xl"
          placeholder="Search by nickname…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search plants"
        />
      </div>

      {toast && (
        <p className="rounded-xl border border-primary/30 bg-primary/10 px-3 py-2 text-sm text-primary">
          {toast}{" "}
          <button
            type="button"
            className="underline font-medium"
            onClick={() => {
              /* toast only — list already refreshed */
              setToast(null);
            }}
          >
            Dismiss
          </button>
        </p>
      )}

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <FlowerLoader label="Gathering your plants…" />
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <Sprout className="h-10 w-10 text-primary" />
            <p className="font-medium">
              {zone === "all" ? "No plants yet" : "Nothing in this zone"}
            </p>
            <p className="text-sm text-muted-foreground max-w-sm">
              {zone === "all"
                ? "Add your first plant to start care history and watering."
                : "Try another zone filter or place plants on the Map."}
            </p>
            <div className="flex gap-2">
              {zone !== "all" && (
                <Button variant="secondary" onClick={() => setZone("all")}>
                  Show all
                </Button>
              )}
              <Button asChild>
                <Link to="/plants/new">Add plant</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {filtered.map((plant) => {
            const loc = plantZone.get(plant.id);
            return (
              <li key={plant.id} className="relative group">
                <Link
                  to={`/plants/${plant.id}`}
                  className="flex gap-3 rounded-xl border border-border bg-card/90 p-3 shadow-sm transition-all hover:bg-accent/40 hover:shadow-md"
                >
                  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-muted ring-1 ring-border/50 relative">
                    {plant.cover_photo?.thumb_url ? (
                      <img
                        src={plant.cover_photo.thumb_url}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-2xl">
                        {typeof plant.emoji === "string" && plant.emoji ? (
                          plant.emoji
                        ) : typeof plant.custom_attributes?.emoji === "string" &&
                          plant.custom_attributes.emoji ? (
                          plant.custom_attributes.emoji
                        ) : (
                          <Sprout className="h-6 w-6 text-muted-foreground" />
                        )}
                      </div>
                    )}
                    {(() => {
                      const em =
                        (typeof plant.emoji === "string" && plant.emoji) ||
                        (typeof plant.custom_attributes?.emoji === "string"
                          ? plant.custom_attributes.emoji
                          : "");
                      return em && plant.cover_photo?.thumb_url ? (
                        <span className="absolute bottom-0.5 right-0.5 text-sm drop-shadow">{em}</span>
                      ) : null;
                    })()}
                  </div>
                  <div className="min-w-0 flex-1 pr-16">
                    <p className="font-medium truncate">
                      {(() => {
                        const em =
                          (typeof plant.emoji === "string" && plant.emoji) ||
                          (typeof plant.custom_attributes?.emoji === "string"
                            ? plant.custom_attributes.emoji
                            : "");
                        return em ? <span className="mr-1">{em}</span> : null;
                      })()}
                      {plant.nickname}
                    </p>
                    <p className="text-xs text-muted-foreground truncate italic">
                      {plant.taxon?.scientific_name ?? "Unknown species"}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <span className="rounded bg-muted px-1.5 py-0.5 text-[10px]">
                        {labelEnvironment(plant.environment)}
                      </span>
                      {loc && (
                        <span className="rounded bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] truncate max-w-[12rem]">
                          📍 {loc.label}
                        </span>
                      )}
                      {plant.tags.slice(0, 2).map((t) => (
                        <span
                          key={t.id}
                          className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-accent-foreground"
                        >
                          {t.name}
                        </span>
                      ))}
                    </div>
                  </div>
                </Link>
                <div className="absolute right-2 top-2 flex flex-col gap-1 items-end">
                  <button
                    type="button"
                    title="Duplicate this plant"
                    disabled={copyingId === plant.id}
                    onClick={(e) => void copyPlant(plant.id, e)}
                    className="inline-flex items-center gap-1 rounded-lg border border-border bg-background/95 px-2 py-1 text-[11px] font-medium text-muted-foreground shadow-sm hover:text-primary hover:border-primary/40 disabled:opacity-50"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    {copyingId === plant.id ? "…" : "Duplicate"}
                  </button>
                  {!plant.cover_photo?.thumb_url && (
                    <button
                      type="button"
                      title="Find a free photo"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setPhotoPlantId(
                          photoPlantId === plant.id ? null : plant.id,
                        );
                      }}
                      className="inline-flex items-center gap-1 rounded-lg border border-primary/30 bg-primary/10 px-2 py-1 text-[11px] font-medium text-primary shadow-sm hover:bg-primary/15"
                    >
                      📷 Photo
                    </button>
                  )}
                </div>
                {photoPlantId === plant.id && activeHousehold && (
                  <div
                    className="border-t border-border bg-card px-3 py-3"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <PhotoSearchPicker
                      householdId={activeHousehold.id}
                      plantId={plant.id}
                      defaultQuery={
                        plant.taxon?.scientific_name ||
                        plant.taxon?.common_names?.[0] ||
                        plant.nickname
                      }
                      onPicked={async () => {
                        setPhotoPlantId(null);
                        setToast("Photo set");
                        await load();
                        setTimeout(() => setToast(null), 2000);
                      }}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
