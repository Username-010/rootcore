import { CheckCircle2, Droplets, ListTodo, Printer } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { WeekRound } from "@/lib/types";
import { amountCopy, urgencyCopy } from "@/lib/watering-copy";

export function WeekRoundPage() {
  const { activeHousehold } = useAuth();
  const [data, setData] = useState<WeekRound | null>(null);
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
      setData(await api.weekRound(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load week round");
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

  const empty = data.counts.plants === 0 && data.counts.tasks === 0;

  return (
    <div className="space-y-6 print:space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between print:flex-row">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">Walk the garden</p>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Droplets className="h-6 w-6 text-primary" />
            Week round
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            Seven-day watering + tasks for {activeHousehold.name}. Print this, take the phone outside, tick as you go.
            Times in {data.timezone}.
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

      <div className="flex gap-3 text-sm print:text-xs">
        <span className="rounded-full bg-primary/10 text-primary px-3 py-1">
          {data.counts.plants} plant{data.counts.plants === 1 ? "" : "s"}
        </span>
        <span className="rounded-full bg-muted px-3 py-1">
          {data.counts.tasks} task{data.counts.tasks === 1 ? "" : "s"}
        </span>
        <span className="text-muted-foreground self-center">
          {data.from} → {data.to}
        </span>
      </div>

      {empty ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            Nothing due this week. Enjoy the quiet.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {data.days.map((day) => {
            const quiet = day.plants.length === 0 && day.tasks.length === 0;
            return (
              <Card
                key={day.date}
                className={
                  day.is_today
                    ? "border-primary/40 shadow-sm shadow-primary/10"
                    : quiet
                      ? "opacity-70"
                      : ""
                }
              >
                <CardHeader className="py-3 space-y-0">
                  <CardTitle className="text-base flex items-center gap-2">
                    <span>{day.weekday}</span>
                    <span className="text-muted-foreground font-normal text-sm">{day.date}</span>
                    {day.is_today && (
                      <span className="text-xs uppercase tracking-wide text-primary">Today</span>
                    )}
                  </CardTitle>
                  <CardDescription>
                    {quiet
                      ? "No water or tasks"
                      : `${day.plants.length} to water · ${day.tasks.length} task${day.tasks.length === 1 ? "" : "s"}`}
                  </CardDescription>
                </CardHeader>
                {!quiet && (
                  <CardContent className="pt-0 space-y-2">
                    {day.plants.map((p) => {
                      const u = urgencyCopy(p.urgency);
                      return (
                        <div
                          key={p.plant_id}
                          className="flex items-start justify-between gap-3 rounded-xl border px-3 py-2"
                        >
                          <div className="min-w-0">
                            <Link
                              to={"/plants/" + p.plant_id}
                              className="font-medium hover:underline inline-flex items-center gap-1.5"
                            >
                              <span>{p.emoji || "🪴"}</span>
                              <span className="truncate">{p.nickname}</span>
                            </Link>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {u.title} · {p.amount_label || amountCopy(p.recommended_amount)}
                              {p.best_time_label ? ` · ${p.best_time_label}` : ""}
                            </p>
                          </div>
                          <span className="text-lg leading-none print:inline" aria-hidden>
                            ☐
                          </span>
                        </div>
                      );
                    })}
                    {day.tasks.map((t) => (
                      <div
                        key={t.id}
                        className="flex items-start justify-between gap-3 rounded-xl border px-3 py-2"
                      >
                        <div className="min-w-0">
                          <p className="font-medium inline-flex items-center gap-1.5">
                            <ListTodo className="h-4 w-4 text-muted-foreground" />
                            {t.title}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">{t.type}</p>
                        </div>
                        <span className="text-lg leading-none" aria-hidden>
                          ☐
                        </span>
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
