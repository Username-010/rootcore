import { AlarmClock, CheckCircle2, Printer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { DueCan, DueCanPlant } from "@/lib/types";
import { amountCopy, urgencyCopy } from "@/lib/watering-copy";

const GROUP_ORDER = ["overdue", "due", "soon"] as const;

export function DueCanPage() {
  const { activeHousehold } = useAuth();
  const [data, setData] = useState<DueCan | null>(null);
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
      setData(await api.dueCan(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load due can");
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
            Water these now
          </p>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <AlarmClock className="h-6 w-6 text-primary" />
            Due can
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            {data.summary} Print, walk the rooms, tick the box. Times in {data.timezone}.
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

      <div className="flex gap-3 text-sm print:text-xs flex-wrap">
        <span className="rounded-full bg-primary/10 text-primary px-3 py-1">{data.total} thirsty</span>
        <span className="rounded-full bg-muted px-3 py-1">{data.counts.overdue} overdue</span>
        <span className="rounded-full bg-muted px-3 py-1">{data.counts.due} due</span>
        <span className="rounded-full bg-muted px-3 py-1">{data.counts.soon} soon</span>
      </div>

      {data.total === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            Can is empty. Nothing needs water right now.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {GROUP_ORDER.map((key) => {
            const plants = data.groups[key] ?? [];
            if (plants.length === 0) return null;
            return (
              <Card key={key}>
                <CardHeader className="py-3 space-y-0">
                  <CardTitle className="text-base capitalize">{key}</CardTitle>
                  <CardDescription>
                    {plants.length} plant{plants.length === 1 ? "" : "s"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-0 space-y-2">
                  {plants.map((p) => (
                    <DueRow key={p.plant_id} plant={p} />
                  ))}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DueRow({ plant }: { plant: DueCanPlant }) {
  const u = urgencyCopy(plant.urgency);
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border px-3 py-2">
      <div className="min-w-0">
        <Link
          to={"/plants/" + plant.plant_id}
          className="font-medium hover:underline inline-flex items-center gap-1.5"
        >
          <span>{plant.emoji || "🪴"}</span>
          <span className="truncate">{plant.nickname}</span>
        </Link>
        <p className="text-xs text-muted-foreground mt-0.5">
          {u.title} · {amountCopy(plant.recommended_amount)} · {plant.environment}
        </p>
      </div>
      <span className="text-lg leading-none print:inline" aria-hidden>
        ☐
      </span>
    </div>
  );
}
