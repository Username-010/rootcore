import { Plus, Search, Sprout } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { lightDisplay, moistureDrops } from "@/lib/care-labels";
import type { CatalogTaxon } from "@/lib/types";

export function CatalogPage() {
  const { activeHousehold } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [items, setItems] = useState<CatalogTaxon[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (query: string) => {
    if (!activeHousehold) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.catalogTaxa(query.trim(), activeHousehold.id, {
        limit: 60,
        withImages: true,
      });
      setItems(data as CatalogTaxon[]);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Catalog search failed");
    } finally {
      setLoading(false);
    }
  }, [activeHousehold]);

  useEffect(() => {
    if (!activeHousehold) return;
    const delay = q.trim().length >= 1 ? 250 : 100;
    const t = setTimeout(() => void load(q), delay);
    return () => clearTimeout(t);
  }, [load, activeHousehold, q]);

  async function quickAdd(t: CatalogTaxon) {
    if (!activeHousehold) return;
    // Go through form so user can pick garden/room/pot
    const nick = t.common_names[0] || t.scientific_name;
    navigate(
      "/plants/new?taxon=" +
        encodeURIComponent(t.id) +
        "&name=" +
        encodeURIComponent(t.scientific_name) +
        "&nick=" +
        encodeURIComponent(nick),
    );
  }

  if (!activeHousehold) {
    return (
      <p className="text-sm text-muted-foreground">
        Select a household first.{" "}
        <Link to="/household" className="text-primary hover:underline">
          Households
        </Link>
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Species catalog</h1>
          <p className="text-sm text-muted-foreground max-w-xl">
            ~190 species with care defaults. Search with pictures, one-tap add — outdoor plants,
            soil, pot size, and tags fill in automatically.
          </p>
        </div>
        <Button asChild variant="secondary" className="rounded-xl">
          <Link to="/plants/new">Manual add form</Link>
        </Button>
      </header>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9 h-11 rounded-xl"
          placeholder="Search Hot Lips, Phlox, Coreopsis, rose…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
        />
      </div>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {loading && items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Loading catalog…</p>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No matches. Try another name or{" "}
            <Link to="/plants/new" className="text-primary hover:underline">
              add manually
            </Link>
            .
          </CardContent>
        </Card>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((t) => {
            const light = lightDisplay(t.care_profile?.light);
            const env = t.suggested_environment || "indoor";
            return (
              <li key={t.id}>
                <Card className="overflow-hidden h-full flex flex-col">
                  <div className="aspect-[4/3] bg-muted relative">
                    {t.preview_url ? (
                      <img
                        src={t.preview_url}
                        alt={t.scientific_name}
                        className="h-full w-full object-cover"
                        loading="lazy"
                        referrerPolicy="no-referrer"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-muted-foreground">
                        <Sprout className="h-10 w-10 opacity-40" />
                      </div>
                    )}
                    <span
                      className={
                        "absolute left-2 top-2 rounded-full px-2 py-0.5 text-[10px] font-medium " +
                        (env === "outdoor"
                          ? "bg-emerald-600 text-white"
                          : "bg-background/90 text-foreground")
                      }
                    >
                      {env === "outdoor" ? "🌳 Outdoor" : env === "greenhouse" ? "🏠 Greenhouse" : "🪴 Indoor"}
                    </span>
                  </div>
                  <CardHeader className="pb-2 flex-1">
                    <CardTitle className="text-sm italic leading-snug">
                      {t.scientific_name}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {t.common_names[0] || t.family || "—"}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0 space-y-2">
                    <p className="text-xs text-muted-foreground">
                      {light.emoji} {light.label}
                      {t.care_profile?.moisture_preference
                        ? ` · ${moistureDrops(t.care_profile.moisture_preference)}`
                        : ""}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className="flex-1 rounded-xl"
                        onClick={() => void quickAdd(t)}
                      >
                        <Plus className="h-3.5 w-3.5" />
                        Add plant
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
