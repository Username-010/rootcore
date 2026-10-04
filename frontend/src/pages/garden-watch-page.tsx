import { CloudRain, Snowflake, Sun, Thermometer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { GardenWatch } from "@/lib/types";
import { cn } from "@/lib/utils";

export function GardenWatchPage() {
  const { activeHousehold } = useAuth();
  const [data, setData] = useState<GardenWatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!activeHousehold) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await api.gardenWatch(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load garden watch");
    } finally {
      setLoading(false);
    }
  }, [activeHousehold]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!activeHousehold) {
    return <p className="text-sm text-muted-foreground">Pick a home first.</p>;
  }
  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <FlowerLoader />
      </div>
    );
  }
  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
            Outdoor week
          </p>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Snowflake className="h-6 w-6 text-sky-600" />
            Garden watch
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">{data.summary}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm" className="rounded-xl">
            <Link to="/settings">Location</Link>
          </Button>
          <Button asChild size="sm" className="rounded-xl">
            <Link to="/">Back to Today</Link>
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        <span className="rounded-full bg-sky-500/10 text-sky-800 dark:text-sky-200 px-3 py-1">
          {data.counts.frost_nights} frost night{data.counts.frost_nights === 1 ? "" : "s"}
        </span>
        <span className="rounded-full bg-muted px-3 py-1">
          {data.counts.rain_days} wet day{data.counts.rain_days === 1 ? "" : "s"}
        </span>
        <span className="rounded-full bg-primary/10 text-primary px-3 py-1">
          {data.counts.outdoor_plants} outdoor
        </span>
      </div>

      {!data.configured && (
        <Card className="border-amber-500/40 bg-amber-500/10">
          <CardContent className="py-4 text-sm">
            Add latitude and longitude in Settings so RootCore can warn you about frost and rain.
            <Button asChild size="sm" className="mt-3 rounded-xl">
              <Link to="/settings">Open Settings</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {data.alerts.length > 0 && (
        <div className="grid gap-3">
          {data.alerts.map((a) => (
            <Card
              key={`${a.kind}-${a.date}-${a.title}`}
              className={
                a.severity === "danger"
                  ? "border-sky-600/50 bg-sky-500/10"
                  : a.severity === "warning"
                    ? "border-amber-500/40 bg-amber-500/10"
                    : "border-primary/25 bg-primary/5"
              }
            >
              <CardContent className="py-3 text-sm flex gap-3">
                <span className="mt-0.5">
                  {a.kind === "frost" ? (
                    <Snowflake className="h-5 w-5 text-sky-700" />
                  ) : a.kind === "rain" ? (
                    <CloudRain className="h-5 w-5 text-primary" />
                  ) : (
                    <Sun className="h-5 w-5 text-amber-600" />
                  )}
                </span>
                <div>
                  <p className="font-medium">{a.title}</p>
                  <p className="text-muted-foreground mt-0.5">{a.detail}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Thermometer className="h-4 w-4" />
            Seven nights
          </CardTitle>
          <CardDescription>Times in {data.timezone}. Frost = 4°C or colder at night.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.nights.length === 0 ? (
            <p className="text-sm text-muted-foreground">No forecast days yet.</p>
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {data.nights.map((n) => (
                <div
                  key={n.date}
                  className={cn(
                    "rounded-xl border px-2 py-3 text-center text-xs",
                    n.frost_hard
                      ? "border-sky-600 bg-sky-500/15"
                      : n.frost_risk
                        ? "border-sky-400/60 bg-sky-500/10"
                        : n.rain_skip
                          ? "border-primary/30 bg-primary/5"
                          : "border-border bg-muted/40",
                  )}
                >
                  <p className="font-medium">
                    {n.weekday.slice(0, 3)}
                    {n.is_today ? " · today" : ""}
                  </p>
                  <p className="text-lg font-semibold tabular-nums mt-1">
                    {n.temp_min_c != null ? `${Math.round(n.temp_min_c)}°` : "—"}
                  </p>
                  <p className="text-muted-foreground">night low</p>
                  <p className="tabular-nums mt-1">
                    {n.temp_max_c != null ? `high ${Math.round(n.temp_max_c)}°` : ""}
                  </p>
                  {n.frost_hard ? (
                    <p className="mt-1 font-medium text-sky-800 dark:text-sky-200">Hard frost</p>
                  ) : n.frost_risk ? (
                    <p className="mt-1 font-medium text-sky-700 dark:text-sky-300">Frost risk</p>
                  ) : n.rain_skip ? (
                    <p className="mt-1 text-primary">Rain skip</p>
                  ) : (
                    <p className="mt-1 text-muted-foreground">Clear</p>
                  )}
                  {n.precip_mm != null && n.precip_mm > 0 && (
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {n.precip_mm.toFixed(1)} mm
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Outdoor plants to protect</CardTitle>
          <CardDescription>
            Mapped to a garden / balcony / outdoor area. Indoor rooms are skipped.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.outdoor_plants.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No plants on an outdoor map yet. Place pots on the{" "}
              <Link to="/layout" className="text-primary hover:underline">
                Map
              </Link>{" "}
              in a garden area.
            </p>
          ) : (
            <ul className="grid gap-2 sm:grid-cols-2">
              {data.outdoor_plants.map((p) => (
                <li key={p.plant_id}>
                  <Link
                    to={"/plants/" + p.plant_id}
                    className="flex items-center gap-2 rounded-xl border px-3 py-2 hover:bg-muted/50"
                  >
                    <span>{p.emoji || "🪴"}</span>
                    <span className="font-medium truncate">{p.nickname}</span>
                    <span className="ml-auto text-xs text-muted-foreground truncate">
                      {p.space_name}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
