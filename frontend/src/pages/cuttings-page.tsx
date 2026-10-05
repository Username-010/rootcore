import { Printer, Sprout } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { CuttingsTray, CuttingsTrayPlant } from "@/lib/types";

export function CuttingsPage() {
  const { activeHousehold } = useAuth();
  const [data, setData] = useState<CuttingsTray | null>(null);
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
      setData(await api.cuttingsTray(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load cuttings tray");
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
    <div className="space-y-6 print:space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between print:flex-row">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
            Fill a jar, take a cutting
          </p>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Sprout className="h-6 w-6 text-primary" />
            Cuttings
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            {data.summary} Times in {data.timezone}. Tick jar or soil when the cutting is in.
          </p>
        </div>
        <div className="flex gap-2 print:hidden">
          <Button variant="outline" size="sm" className="rounded-xl" onClick={() => window.print()}>
            <Printer className="h-4 w-4 mr-1.5" />
            Print
          </Button>
          <Button asChild size="sm" className="rounded-xl">
            <Link to="/">Back to Today</Link>
          </Button>
        </div>
      </div>

      {data.total === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            No plants yet. Add one, then print a cuttings tray.
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="py-4 space-y-1 text-sm">
              <p>
                {data.water_jars} water jar{data.water_jars === 1 ? "" : "s"} · {data.soil_pots} soil
                / division
              </p>
              <p className="text-xs text-muted-foreground">
                Indoor plants default to a water jar. Outdoor plants default to soil or division.
              </p>
            </CardContent>
          </Card>
          <div className="space-y-2">
            {data.plants.map((plant) => (
              <CuttingRow key={plant.plant_id} plant={plant} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function CuttingRow({ plant }: { plant: CuttingsTrayPlant }) {
  const extras = [plant.environment, plant.scientific_name, plant.method_label]
    .filter(Boolean)
    .join(" · ");
  return (
    <div className="rounded-xl border px-3 py-3 flex gap-3 items-start break-inside-avoid">
      <div className="min-w-0 flex-1">
        <p className="font-medium inline-flex items-center gap-1.5">
          <span>{plant.emoji || "🪴"}</span>
          <span className="truncate">{plant.nickname}</span>
        </p>
        {extras ? <p className="text-xs text-muted-foreground mt-0.5 capitalize">{extras}</p> : null}
        {plant.already_child ? (
          <p className="text-xs text-muted-foreground mt-0.5">Already grown from a cutting.</p>
        ) : null}
        <p className="text-xs mt-2 flex flex-wrap gap-3">
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-3.5 w-3.5 rounded border border-muted-foreground/50" /> jar
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-3.5 w-3.5 rounded border border-muted-foreground/50" /> soil
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-3.5 w-3.5 rounded border border-muted-foreground/50" /> labeled
          </span>
        </p>
      </div>
    </div>
  );
}
