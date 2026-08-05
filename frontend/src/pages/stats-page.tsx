import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { StatsSummary } from "@/lib/types";

export function StatsPage() {
  const { activeHousehold } = useAuth();
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeHousehold) return;
    try {
      setStats(await api.statsSummary(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load stats");
    }
  }, [activeHousehold]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!activeHousehold) {
    return <p className="text-sm text-muted-foreground">Select a household first.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Statistics</h1>
        <p className="text-sm text-muted-foreground">Collection health and care activity.</p>
      </div>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {!stats ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric label="Active plants" value={String(stats.plants_active)} />
          <Metric
            label="Survival rate"
            value={
              stats.survival_rate == null
                ? "—"
                : Math.round(stats.survival_rate * 100) + "%"
            }
          />
          <Metric label="Collection value" value={stats.collection_value.toFixed(2)} />
          <Metric label="Waterings (30d)" value={String(stats.waterings_30d)} />
          <Metric
            label="Est. water (30d)"
            value={(stats.estimated_water_ml_30d / 1000).toFixed(2) + " L"}
          />
          <Metric label="Tasks completed (30d)" value={String(stats.tasks_completed_30d)} />
          <Metric label="Open tasks" value={String(stats.tasks_open)} />
          <Metric label="Deceased" value={String(stats.plants_deceased)} />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground font-normal">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}
