import { AlertTriangle, CheckCircle2, CloudSun, Droplets, ListTodo, Sprout } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { weatherCodeEmoji } from "@/lib/care-labels";
import type { Dashboard } from "@/lib/types";
import { amountCopy, formatNextWater, urgencyCopy } from "@/lib/watering-copy";

export function DashboardPage() {
  const { user, activeHousehold } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeHousehold) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setData(await api.dashboard(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [activeHousehold]);

  useEffect(() => {
    void load();
  }, [load]);

  async function completeTask(taskId: string) {
    if (!activeHousehold) return;
    setBusyId(taskId);
    try {
      await api.completeTask(activeHousehold.id, taskId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not complete task");
    } finally {
      setBusyId(null);
    }
  }

  async function quickWater(plantId: string, amount: string = "normal") {
    if (!activeHousehold) return;
    setBusyId(plantId);
    try {
      await api.waterPlant(activeHousehold.id, plantId, {
        amount: amount as "light" | "normal" | "deep",
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not log watering");
    } finally {
      setBusyId(null);
    }
  }

  async function undoEvent(eventId: string) {
    if (!activeHousehold) return;
    if (!confirm("Undo this care entry? It will return to your plan if it was a watering or completed task."))
      return;
    setBusyId(eventId);
    setError(null);
    try {
      await api.deleteEvent(activeHousehold.id, eventId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not undo");
    } finally {
      setBusyId(null);
    }
  }

  async function waterAllDue() {
    if (!activeHousehold || !data?.attention.length) return;
    if (!confirm(`Mark all ${data.attention.length} plant(s) as watered?`)) return;
    setBusyId("bulk-water");
    setError(null);
    try {
      const res = await api.bulkWaterAll(activeHousehold.id);
      setError(null);
      await load();
      // reuse error banner as success briefly via message — keep simple
      if (res.message) {
        /* load refreshes plan */
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Bulk water failed");
    } finally {
      setBusyId(null);
    }
  }

  async function completeAllTasks() {
    if (!activeHousehold || !data?.tasks_today.length) return;
    if (!confirm(`Mark all ${data.tasks_today.length} task(s) done?`)) return;
    setBusyId("bulk-tasks");
    setError(null);
    try {
      await api.bulkCompleteTasks(
        activeHousehold.id,
        data.tasks_today.map((t) => t.id),
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Bulk complete failed");
    } finally {
      setBusyId(null);
    }
  }

  async function fertilizeAllDue() {
    if (!activeHousehold) return;
    if (!confirm("Complete all open fertilize tasks?")) return;
    setBusyId("bulk-fert");
    setError(null);
    try {
      await api.bulkFertilizeDue(activeHousehold.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Bulk fertilize failed");
    } finally {
      setBusyId(null);
    }
  }

  if (!activeHousehold) {
    return (
      <Card>
        <CardContent className="py-10 text-center space-y-3">
          <p className="font-medium">No household yet</p>
          <p className="text-sm text-muted-foreground">
            Create or join a household to see today&apos;s care plan.
          </p>
          <Button asChild>
            <Link to="/household">Open households</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-primary">Today</p>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
            Hi{user ? `, ${user.display_name.split(" ")[0]}` : ""}
          </h1>
          <p className="text-sm text-muted-foreground">
            {activeHousehold.name} · what needs you right now
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild>
            <Link to="/plants/new">Add plant</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/calendar">Calendar</Link>
          </Button>
        </div>
      </header>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {loading || !data ? (
        <FlowerLoader label="Growing today's plan…" />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Plants" value={data.counts.plants_active} icon={Sprout} />
            <Stat
              label="Need water"
              value={data.counts.due_soon + data.counts.overdue_water}
              icon={Droplets}
            />
            <Stat label="Due this week" value={data.counts.open_tasks} icon={ListTodo} />
            <Stat label="Overdue" value={data.counts.overdue_water} icon={AlertTriangle} />
          </div>

          {/* Interactive quick plan — updates when you water / undo / bulk */}
          {data.care_brief && (
            <Card className="border-primary/25 bg-primary/5">
              <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between space-y-0 pb-2">
                <div>
                  <CardTitle className="text-base">Quick plan</CardTitle>
                  <CardDescription>
                    Live list — water here or use Water all. Matches the water plan below.
                  </CardDescription>
                </div>
                {(data.care_brief.water_today?.length ?? 0) > 0 && (
                  <Button
                    size="sm"
                    className="rounded-xl shrink-0"
                    disabled={busyId === "bulk-water"}
                    onClick={() => void waterAllDue()}
                  >
                    {busyId === "bulk-water" ? "…" : "Water all in plan"}
                  </Button>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                {(data.care_brief.water_today?.length ?? 0) === 0 ? (
                  <p className="text-sm text-muted-foreground rounded-lg border border-border/60 bg-background/70 px-3 py-2">
                    💧 Nothing to water right now. Undo a recent watering if you want it back on the
                    plan.
                  </p>
                ) : (
                  <ul className="space-y-1.5">
                    {data.care_brief.water_today.map((p) => (
                      <li
                        key={p.plant_id}
                        className="flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-background/80 px-3 py-2 text-sm"
                      >
                        <Link
                          to={"/plants/" + p.plant_id}
                          className="min-w-0 flex-1 font-medium hover:underline inline-flex items-center gap-1.5"
                        >
                          <span>{p.emoji || "🪴"}</span>
                          <span className="truncate">{p.nickname}</span>
                          <span className="text-xs font-normal text-muted-foreground truncate">
                            · {p.amount_label || amountCopy(p.recommended_amount)}
                            {p.room ? ` · ${p.room}` : ""}
                          </span>
                        </Link>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-8 rounded-lg shrink-0"
                          disabled={busyId === p.plant_id}
                          onClick={() =>
                            void quickWater(p.plant_id, p.recommended_amount || "normal")
                          }
                        >
                          {busyId === p.plant_id ? "…" : "Water"}
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}

                {data.care_brief.water_by_zone &&
                  Object.keys(data.care_brief.water_by_zone).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1.5">
                        By zone
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(data.care_brief.water_by_zone).map(([zone, names]) => (
                          <span
                            key={zone}
                            className="rounded-full bg-sky-500/15 px-2.5 py-1 text-xs"
                          >
                            📍 {zone}: {names.join(", ")}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Other care lines: fertilize / prune / upcoming */}
                <ul className="space-y-1 text-sm">
                  {(data.care_brief.upcoming?.length ?? 0) > 0 && (
                    <li className="rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-muted-foreground">
                      ⏱ Soon:{" "}
                      {data.care_brief.upcoming
                        .slice(0, 5)
                        .map((u) => u.nickname)
                        .join(", ")}
                    </li>
                  )}
                  {(data.care_brief.fertilize?.length ?? 0) > 0 && (
                    <li className="flex items-center justify-between gap-2 rounded-lg border border-border/50 bg-background/50 px-3 py-2">
                      <span>
                        🌿 Fertilize:{" "}
                        {data.care_brief.fertilize
                          .slice(0, 4)
                          .map((t) => t.title.replace(/^Fertilize\s*/i, ""))
                          .join(", ")}
                      </span>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 rounded-lg text-xs"
                        disabled={busyId === "bulk-fert"}
                        onClick={() => void fertilizeAllDue()}
                      >
                        All done
                      </Button>
                    </li>
                  )}
                  {(data.care_brief.prune?.length ?? 0) > 0 && (
                    <li className="rounded-lg border border-border/50 bg-background/50 px-3 py-2 text-muted-foreground">
                      ✂ Prune:{" "}
                      {data.care_brief.prune
                        .slice(0, 4)
                        .map((t) => t.title.replace(/^Prune\s*/i, ""))
                        .join(", ")}
                    </li>
                  )}
                </ul>

                <Button asChild variant="ghost" size="sm" className="px-0">
                  <Link to="/calendar">Open full calendar →</Link>
                </Button>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex-row items-start gap-3 space-y-0">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                <CloudSun className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <CardTitle className="text-base">Weather</CardTitle>
                <CardDescription>
                  {data.weather?.configured
                    ? "Open-Meteo · free, no API key — outdoor watering aware"
                    : "Add your location so outdoor plants get smarter advice"}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {data.weather?.configured ? (
                <>
                  <div className="grid grid-cols-3 gap-3 text-sm">
                    <Metric
                      label="Temp"
                      value={
                        data.weather.temperature_c != null
                          ? `${Math.round(data.weather.temperature_c)}°C`
                          : "—"
                      }
                    />
                    <Metric
                      label="Humidity"
                      value={
                        data.weather.humidity != null
                          ? `${Math.round(data.weather.humidity)}%`
                          : "—"
                      }
                    />
                    <Metric
                      label="Rain (24h)"
                      value={
                        data.weather.precip_next_24h_mm != null
                          ? `${data.weather.precip_next_24h_mm.toFixed(1)} mm`
                          : "—"
                      }
                    />
                  </div>
                  {data.weather.daily && data.weather.daily.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-2">
                        7-day forecast
                      </p>
                      <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-7">
                        {data.weather.daily.slice(0, 7).map((d) => {
                          const dt = new Date(d.date + "T12:00:00");
                          const weekday = dt.toLocaleDateString(undefined, { weekday: "short" });
                          return (
                            <div
                              key={d.date}
                              className="rounded-lg border border-border bg-muted/40 px-1.5 py-2 text-center text-xs"
                            >
                              <p className="font-medium">{weekday}</p>
                              <p className="text-base leading-none my-1">
                                {weatherCodeEmoji(d.weather_code)}
                              </p>
                              <p className="tabular-nums font-semibold">
                                {d.temp_max_c != null ? Math.round(d.temp_max_c) : "—"}°
                              </p>
                              <p className="text-muted-foreground tabular-nums">
                                {d.temp_min_c != null ? Math.round(d.temp_min_c) : "—"}°
                              </p>
                              {d.precip_mm != null && d.precip_mm > 0 ? (
                                <p className="text-[10px] text-sky-600 dark:text-sky-400 mt-0.5">
                                  {d.precip_mm.toFixed(1)}mm
                                </p>
                              ) : (
                                <p className="text-[10px] text-muted-foreground mt-0.5">—</p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <Button asChild size="sm">
                  <Link to="/settings">Set location in Settings</Link>
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Heat / humidity banner */}
          {data.weather?.configured &&
            ((data.weather.temperature_c != null && data.weather.temperature_c >= 28) ||
              (data.weather.humidity != null && data.weather.humidity < 35)) && (
              <Card className="border-amber-500/40 bg-amber-500/10">
                <CardContent className="py-3 text-sm">
                  <p className="font-medium">
                    {data.weather.temperature_c != null && data.weather.temperature_c >= 32
                      ? "🔥 Heatwave conditions"
                      : data.weather.temperature_c != null && data.weather.temperature_c >= 28
                        ? "🌡 Hot weather today"
                        : "💨 Dry air"}
                  </p>
                  <p className="text-muted-foreground mt-0.5">
                    {data.weather.temperature_c != null && data.weather.temperature_c >= 28
                      ? `Air ~${Math.round(data.weather.temperature_c)}°C — soil dries faster. Prefer morning water and deeper soaks for outdoor pots.`
                      : `Humidity ~${Math.round(data.weather.humidity ?? 0)}% — tropical houseplants may need water a day sooner.`}
                    {data.weather.precip_next_24h_mm != null &&
                    data.weather.precip_next_24h_mm >= 3
                      ? ` Rain ~${data.weather.precip_next_24h_mm.toFixed(1)} mm expected — outdoor beds may wait.`
                      : ""}
                  </p>
                </CardContent>
              </Card>
            )}

          <Card className="border-primary/25">
            <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between space-y-0">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <Droplets className="h-4 w-4 text-primary" />
                  Water plan — how much &amp; when
                </CardTitle>
                <CardDescription>
                  Clear amounts (ml), best time of day, and weather reasons. Undo a watering under
                  Recent care to put a plant back here.
                </CardDescription>
              </div>
              {data.attention.length > 0 && (
                <Button
                  size="sm"
                  variant="secondary"
                  className="rounded-xl shrink-0"
                  disabled={busyId === "bulk-water"}
                  onClick={() => void waterAllDue()}
                >
                  {busyId === "bulk-water" ? "…" : "Watered all"}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {data.attention.length === 0 ? (
                <p className="text-sm text-muted-foreground flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  Nobody needs water right now. Nice work. Undo a recent watering below to test the
                  plan again.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.attention.map((item) => {
                    const u = urgencyCopy(item.urgency);
                    const amount =
                      item.amount_label || amountCopy(item.recommended_amount);
                    const tone =
                      item.urgency === "overdue"
                        ? "border-destructive/40 bg-destructive/5"
                        : item.urgency === "due" || item.heat_stress
                          ? "border-amber-500/40 bg-amber-500/5"
                          : "border-border bg-card";
                    return (
                      <li
                        key={item.plant_id}
                        className={"rounded-xl border px-3 py-3 space-y-2 " + tone}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <Link
                              to={"/plants/" + item.plant_id}
                              className="font-semibold hover:underline inline-flex items-center gap-1.5"
                            >
                              <span className="text-lg leading-none">{item.emoji || "🪴"}</span>
                              <span className="truncate">{item.nickname}</span>
                            </Link>
                            <p className="text-xs font-medium text-primary mt-0.5">{u.title}</p>
                          </div>
                          <Button
                            size="sm"
                            className="shrink-0 rounded-xl"
                            disabled={busyId === item.plant_id}
                            onClick={() =>
                              void quickWater(
                                item.plant_id,
                                item.recommended_amount || "normal",
                              )
                            }
                          >
                            {busyId === item.plant_id ? "…" : "Watered"}
                          </Button>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-2 text-sm">
                          <div className="rounded-lg bg-background/80 px-2.5 py-2">
                            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
                              When
                            </p>
                            <p className="font-medium">
                              {formatNextWater(item.next_due_at)}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {item.best_time_label || "Morning"}
                              {item.best_time_local ? ` · ${item.best_time_local}` : ""}
                            </p>
                          </div>
                          <div className="rounded-lg bg-background/80 px-2.5 py-2">
                            <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
                              How much
                            </p>
                            <p className="font-medium">
                              {amount}
                              {item.amount_ml != null ? ` · ~${item.amount_ml} ml` : ""}
                            </p>
                            {item.amount_howto && (
                              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                                {item.amount_howto}
                              </p>
                            )}
                          </div>
                        </div>
                        {(item.heat_stress || item.dry_air || item.weather_note) && (
                          <p className="text-xs rounded-lg border border-border/60 bg-background/60 px-2.5 py-1.5 text-muted-foreground">
                            {item.heat_stress ? "🔥 Extra thirst from heat · " : ""}
                            {item.dry_air ? "💨 Dry air · " : ""}
                            {item.weather_note ||
                              (item.interval_days != null
                                ? `About every ${Math.round(item.interval_days)} days right now`
                                : "")}
                          </p>
                        )}
                        {item.schedule_plain && !item.weather_note && (
                          <p className="text-xs text-muted-foreground">{item.schedule_plain}</p>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2">

            <Card>
              <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between space-y-0">
                <div>
                  <CardTitle className="text-base">Tasks due</CardTitle>
                  <CardDescription>Prune, repot, fertilize, and custom reminders.</CardDescription>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {data.tasks_today.some((t) => t.type === "fertilize") && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-xl"
                      disabled={busyId === "bulk-fert"}
                      onClick={() => void fertilizeAllDue()}
                    >
                      Fertilize all
                    </Button>
                  )}
                  {data.tasks_today.length > 0 && (
                    <Button
                      size="sm"
                      variant="secondary"
                      className="rounded-xl"
                      disabled={busyId === "bulk-tasks"}
                      onClick={() => void completeAllTasks()}
                    >
                      Done all
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {data.tasks_today.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No tasks due today.{" "}
                    <Link to="/tasks" className="text-primary hover:underline">
                      Add one
                    </Link>
                  </p>
                ) : (
                  <ul className="space-y-2">
                    {data.tasks_today.map((task) => (
                      <li
                        key={task.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-border px-3 py-3"
                      >
                        <div className="min-w-0">
                          <p className="font-medium truncate">{task.title}</p>
                          <p className="text-xs text-muted-foreground capitalize">{task.type}</p>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busyId === task.id}
                          onClick={() => void completeTask(task.id)}
                        >
                          Done
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          {data.discover && (
            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="border-primary/20 bg-primary/5">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Tip of the day</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  <p className="leading-relaxed">{data.discover.tip_of_day}</p>
                  {data.discover.weather_nudge &&
                    data.discover.weather_nudge !== data.discover.tip_of_day && (
                      <p className="text-xs text-muted-foreground border-t border-border/60 pt-2">
                        {data.discover.weather_nudge}
                      </p>
                    )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Plant of the day</CardTitle>
                  <CardDescription>Inspiration — add from catalog if you like</CardDescription>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  <p className="text-2xl leading-none">{data.discover.plant_of_day.emoji}</p>
                  <p className="font-semibold">{data.discover.plant_of_day.common}</p>
                  <p className="text-xs italic text-muted-foreground">
                    {data.discover.plant_of_day.name}
                  </p>
                  <p className="text-muted-foreground">{data.discover.plant_of_day.why}</p>
                  <Button asChild size="sm" variant="secondary" className="rounded-xl">
                    <Link
                      to={
                        "/catalog?q=" +
                        encodeURIComponent(data.discover.plant_of_day.name.split(" ")[0])
                      }
                    >
                      Browse catalog
                    </Link>
                  </Button>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    Good to grow · {data.discover.season_label}
                  </CardTitle>
                  <CardDescription>{data.discover.season_intro}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 text-sm">
                    {data.discover.recommendations.map((r) => (
                      <li
                        key={r.name}
                        className="rounded-lg border border-border/70 bg-muted/30 px-2.5 py-2"
                      >
                        <p className="font-medium">
                          <span className="mr-1">{r.emoji}</span>
                          {r.name}
                        </p>
                        <p className="text-xs text-muted-foreground mt-0.5">{r.tip}</p>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          )}

          {data.upcoming.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Upcoming (7 days)</CardTitle>
                <CardDescription>Tasks scheduled later this week.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="divide-y divide-border text-sm">
                  {data.upcoming.map((task) => (
                    <li key={task.id} className="flex justify-between gap-3 py-2">
                      <span className="font-medium truncate">
                        {task.type === "prune"
                          ? "✂ "
                          : task.type === "fertilize"
                            ? "🌿 "
                            : task.type === "repot"
                              ? "🪴 "
                              : task.type === "water"
                                ? "💧 "
                                : ""}
                        {task.title}
                      </span>
                      <time className="text-xs text-muted-foreground whitespace-nowrap">
                        {task.due_at
                          ? new Date(task.due_at).toLocaleDateString(undefined, {
                              weekday: "short",
                              month: "short",
                              day: "numeric",
                            })
                          : "—"}
                      </time>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Recent care</CardTitle>
              <Button asChild variant="ghost" size="sm">
                <Link to="/timeline">Edit history</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {data.recent_events.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Water a plant to start your care history.
                </p>
              ) : (
                <ul className="divide-y divide-border text-sm">
                  {data.recent_events.slice(0, 8).map((ev) => (
                    <li
                      key={ev.id}
                      className="flex flex-wrap items-center justify-between gap-2 py-2.5"
                    >
                      <div className="min-w-0">
                        <span className="font-medium capitalize">
                          {ev.type.replaceAll("_", " ")}
                        </span>
                        {ev.plant_nickname ? (
                          <span className="text-muted-foreground"> · {ev.plant_nickname}</span>
                        ) : null}
                        <time className="block text-xs text-muted-foreground">
                          {new Date(ev.occurred_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })}
                        </time>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <Button asChild size="sm" variant="ghost" className="h-7 rounded-lg text-xs">
                          <Link to="/timeline">Edit</Link>
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 rounded-lg text-xs text-destructive"
                          disabled={busyId === ev.id}
                          onClick={() => void undoEvent(ev.id)}
                        >
                          Undo
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number;
  icon: typeof Sprout;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="flex items-center gap-3 p-4">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <p className="text-2xl font-semibold tabular-nums leading-none">{value}</p>
          <p className="text-xs text-muted-foreground mt-1">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/50 px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  );
}
