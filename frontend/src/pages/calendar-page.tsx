import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { CalendarItem } from "@/lib/types";
import { amountCopy, formatNextWater, urgencyCopy } from "@/lib/watering-copy";

const TYPE_META: Record<string, { emoji: string; label: string; color: string }> = {
  water: { emoji: "💧", label: "Water", color: "bg-sky-500/15 text-sky-800 dark:text-sky-200" },
  fertilize: {
    emoji: "🌿",
    label: "Fertilize",
    color: "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200",
  },
  prune: {
    emoji: "✂",
    label: "Prune",
    color: "bg-amber-500/15 text-amber-900 dark:text-amber-200",
  },
  repot: {
    emoji: "🪴",
    label: "Repot",
    color: "bg-orange-500/15 text-orange-900 dark:text-orange-200",
  },
  custom: {
    emoji: "📌",
    label: "Task",
    color: "bg-muted text-foreground",
  },
};

function dayKey(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function typeMeta(type: string) {
  return TYPE_META[type] ?? TYPE_META.custom;
}

export function CalendarPage() {
  const { activeHousehold } = useAuth();
  const [items, setItems] = useState<CalendarItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [monthOffset, setMonthOffset] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "watering" | "tasks">("all");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [view, setView] = useState<"grid" | "list">("grid");

  const range = useMemo(() => {
    const now = new Date();
    const start = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + monthOffset, 1));
    const end = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + monthOffset + 1, 0, 23, 59, 59),
    );
    return { start, end };
  }, [monthOffset]);

  const load = useCallback(async () => {
    if (!activeHousehold) return;
    try {
      setItems(
        await api.calendar(
          activeHousehold.id,
          range.start.toISOString(),
          range.end.toISOString(),
        ),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load calendar");
    }
  }, [activeHousehold, range]);

  useEffect(() => {
    void load();
  }, [load]);

  const planItems = useMemo(
    () => items.filter((i) => i.kind === "watering" || i.kind === "task"),
    [items],
  );

  const filtered = useMemo(() => {
    if (filter === "watering") return planItems.filter((i) => i.kind === "watering");
    if (filter === "tasks") return planItems.filter((i) => i.kind === "task");
    return planItems;
  }, [planItems, filter]);

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarItem[]>();
    for (const item of filtered) {
      const k = dayKey(item.at);
      if (!k) continue;
      const list = map.get(k) ?? [];
      list.push(item);
      map.set(k, list);
    }
    return map;
  }, [filtered]);

  const byRoom = useMemo(() => {
    const map = new Map<string, CalendarItem[]>();
    for (const item of filtered.filter((i) => i.kind === "watering")) {
      const room = item.room || "Unassigned";
      const list = map.get(room) ?? [];
      list.push(item);
      map.set(room, list);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered]);

  const gridDays = useMemo(() => {
    const year = range.start.getUTCFullYear();
    const month = range.start.getUTCMonth();
    const firstDow = new Date(Date.UTC(year, month, 1)).getUTCDay(); // 0 Sun
    const daysInMonth = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    const cells: Array<{ key: string; day: number | null }> = [];
    for (let i = 0; i < firstDow; i++) cells.push({ key: `pad-${i}`, day: null });
    for (let d = 1; d <= daysInMonth; d++) {
      const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      cells.push({ key, day: d });
    }
    return cells;
  }, [range]);

  const selectedItems = selectedDay ? (byDay.get(selectedDay) ?? []) : [];

  async function waterPlant(plantId: string) {
    if (!activeHousehold) return;
    setBusyId(plantId);
    try {
      await api.waterPlant(activeHousehold.id, plantId, { amount: "normal" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not log watering");
    } finally {
      setBusyId(null);
    }
  }

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

  if (!activeHousehold) {
    return <p className="text-sm text-muted-foreground">Select a household first.</p>;
  }

  const title = range.start.toLocaleString(undefined, { month: "long", year: "numeric" });
  const todayKey = dayKey(new Date().toISOString());

  // Summary chips for the month
  const waterCount = filtered.filter((i) => i.kind === "watering").length;
  const pruneCount = filtered.filter((i) => i.type === "prune").length;
  const fertCount = filtered.filter((i) => i.type === "fertilize").length;
  const repotCount = filtered.filter((i) => i.type === "repot").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Care calendar</h1>
          <p className="text-sm text-muted-foreground">
            Watering projected across months · fertilize, prune & repot from species logic.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-xl border border-border px-3 py-1.5 text-sm"
            onClick={() => setMonthOffset((m) => m - 1)}
          >
            ← Prev
          </button>
          <button
            type="button"
            className="rounded-xl border border-border px-3 py-1.5 text-sm font-medium"
            onClick={() => setMonthOffset(0)}
          >
            {title}
          </button>
          <button
            type="button"
            className="rounded-xl border border-border px-3 py-1.5 text-sm"
            onClick={() => setMonthOffset((m) => m + 1)}
          >
            Next →
          </button>
        </div>
      </div>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-sky-500/15 px-2.5 py-1">💧 {waterCount} water</span>
        <span className="rounded-full bg-emerald-500/15 px-2.5 py-1">🌿 {fertCount} fertilize</span>
        <span className="rounded-full bg-amber-500/15 px-2.5 py-1">✂ {pruneCount} prune</span>
        <span className="rounded-full bg-orange-500/15 px-2.5 py-1">🪴 {repotCount} repot</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "Everything"],
            ["watering", "Watering"],
            ["tasks", "Care tasks"],
          ] as const
        ).map(([k, label]) => (
          <Button
            key={k}
            size="sm"
            variant={filter === k ? "default" : "outline"}
            className="rounded-xl"
            onClick={() => setFilter(k)}
          >
            {label}
          </Button>
        ))}
        <div className="ml-auto flex gap-1">
          <Button
            size="sm"
            variant={view === "grid" ? "secondary" : "ghost"}
            className="rounded-xl"
            onClick={() => setView("grid")}
          >
            Month
          </Button>
          <Button
            size="sm"
            variant={view === "list" ? "secondary" : "ghost"}
            className="rounded-xl"
            onClick={() => setView("list")}
          >
            List
          </Button>
        </div>
      </div>

      {view === "grid" && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{title}</CardTitle>
            <CardDescription>Tap a day for details. Icons = care types that day.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-medium text-muted-foreground mb-1">
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
                <div key={d}>{d}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {gridDays.map((cell) => {
                if (cell.day == null) {
                  return <div key={cell.key} className="min-h-[4.5rem]" />;
                }
                const dayItems = byDay.get(cell.key) ?? [];
                const isToday = cell.key === todayKey;
                const isSelected = cell.key === selectedDay;
                const icons = new Set(dayItems.map((i) => typeMeta(i.type).emoji));
                return (
                  <button
                    key={cell.key}
                    type="button"
                    onClick={() => setSelectedDay(cell.key)}
                    className={
                      "min-h-[4.5rem] rounded-lg border p-1 text-left transition-colors " +
                      (isSelected
                        ? "border-primary bg-primary/10 ring-1 ring-primary/40"
                        : isToday
                          ? "border-primary/50 bg-accent/40"
                          : "border-border/70 bg-card hover:bg-muted/50")
                    }
                  >
                    <div className="text-xs font-semibold tabular-nums">{cell.day}</div>
                    <div className="mt-0.5 flex flex-wrap gap-0.5 text-[11px] leading-none">
                      {[...icons].slice(0, 4).map((em) => (
                        <span key={em}>{em}</span>
                      ))}
                      {dayItems.length > 4 ? (
                        <span className="text-[9px] text-muted-foreground">+{dayItems.length - 4}</span>
                      ) : null}
                    </div>
                    {dayItems.length > 0 && (
                      <p className="mt-0.5 text-[9px] text-muted-foreground tabular-nums">
                        {dayItems.length} item{dayItems.length === 1 ? "" : "s"}
                      </p>
                    )}
                  </button>
                );
              })}
            </div>

            {selectedDay && (
              <div className="mt-4 rounded-xl border border-border bg-muted/30 p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">
                    {new Date(selectedDay + "T12:00:00Z").toLocaleDateString(undefined, {
                      weekday: "long",
                      month: "short",
                      day: "numeric",
                    })}
                  </p>
                  <button
                    type="button"
                    className="text-xs text-muted-foreground hover:underline"
                    onClick={() => setSelectedDay(null)}
                  >
                    Close
                  </button>
                </div>
                {selectedItems.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Nothing planned this day.</p>
                ) : (
                  <ul className="space-y-2">
                    {selectedItems.map((item) => (
                      <DayItem
                        key={item.id}
                        item={item}
                        busyId={busyId}
                        onWater={waterPlant}
                        onComplete={completeTask}
                      />
                    ))}
                  </ul>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {view === "list" && (
        <>
          {(filter === "all" || filter === "watering") && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{title} · watering by room</CardTitle>
                <CardDescription>
                  Projected from each plant&apos;s schedule (next month fills from the interval).
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {byRoom.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No watering in this month — add plants or check a different month.
                  </p>
                ) : (
                  byRoom.map(([room, roomItems]) => (
                    <div key={room}>
                      <h3 className="text-sm font-semibold mb-2 text-primary">📍 {room}</h3>
                      <ul className="space-y-2">
                        {roomItems.map((item) => {
                          const plantId = item.plant_id;
                          const u = urgencyCopy(item.status || "ok");
                          return (
                            <li
                              key={item.id}
                              className="flex flex-col gap-2 rounded-xl border border-border bg-card px-3 py-2.5 sm:flex-row sm:items-center sm:justify-between"
                            >
                              <div className="min-w-0">
                                {plantId ? (
                                  <Link
                                    to={"/plants/" + plantId}
                                    className="font-medium hover:underline"
                                  >
                                    {item.title.replace(/^Water /, "")}
                                  </Link>
                                ) : (
                                  <span className="font-medium">{item.title}</span>
                                )}
                                <p className="text-xs text-muted-foreground">
                                  {u.title} · {formatNextWater(item.at)}
                                  {item.recommended_amount
                                    ? " · " + amountCopy(item.recommended_amount)
                                    : ""}
                                </p>
                              </div>
                              {plantId && item.status !== "planned" && (
                                <Button
                                  size="sm"
                                  className="shrink-0 rounded-xl"
                                  disabled={busyId === plantId}
                                  onClick={() => void waterPlant(plantId)}
                                >
                                  Watered
                                </Button>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}

          {filter !== "watering" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {filter === "tasks" ? "Care tasks" : "Fertilize · prune · repot · other"}
                </CardTitle>
                <CardDescription>
                  Auto-scheduled from species profiles (bloom months, intervals) and your logs.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {filtered.filter((i) => i.kind === "task").length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No care tasks this month. They appear after plants have watering recomputed
                    (open a plant or water one).
                  </p>
                ) : (
                  <ul className="divide-y divide-border text-sm">
                    {filtered
                      .filter((i) => i.kind === "task")
                      .map((item) => {
                        const meta = typeMeta(item.type);
                        return (
                          <li
                            key={item.id}
                            className="flex flex-col gap-2 py-2.5 sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="flex items-start gap-2 min-w-0">
                              <span
                                className={
                                  "mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 text-xs " + meta.color
                                }
                              >
                                {meta.emoji} {meta.label}
                              </span>
                              <div className="min-w-0">
                                {item.plant_id ? (
                                  <Link
                                    to={"/plants/" + item.plant_id}
                                    className="font-medium hover:underline"
                                  >
                                    {item.title}
                                  </Link>
                                ) : (
                                  <span className="font-medium">{item.title}</span>
                                )}
                                <p className="text-xs text-muted-foreground">
                                  {item.at ? new Date(item.at).toLocaleDateString() : "—"}
                                  {item.source === "engine" ? " · auto" : ""}
                                </p>
                                {item.description ? (
                                  <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
                                    {item.description}
                                  </p>
                                ) : null}
                              </div>
                            </div>
                            {item.status === "open" && (
                              <Button
                                size="sm"
                                variant="secondary"
                                className="shrink-0 rounded-xl"
                                disabled={busyId === item.id}
                                onClick={() => void completeTask(item.id)}
                              >
                                Done
                              </Button>
                            )}
                          </li>
                        );
                      })}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function DayItem({
  item,
  busyId,
  onWater,
  onComplete,
}: {
  item: CalendarItem;
  busyId: string | null;
  onWater: (id: string) => void;
  onComplete: (id: string) => void;
}) {
  const meta = typeMeta(item.type);
  return (
    <li className="flex items-center justify-between gap-2 rounded-lg border border-border bg-card px-2.5 py-2 text-sm">
      <div className="min-w-0 flex items-center gap-2">
        <span className={"shrink-0 rounded px-1.5 py-0.5 text-xs " + meta.color}>
          {meta.emoji}
        </span>
        {item.plant_id ? (
          <Link to={"/plants/" + item.plant_id} className="truncate font-medium hover:underline">
            {item.title}
          </Link>
        ) : (
          <span className="truncate font-medium">{item.title}</span>
        )}
        {item.room ? (
          <span className="hidden sm:inline text-xs text-muted-foreground truncate">
            · {item.room}
          </span>
        ) : null}
      </div>
      {item.kind === "watering" && item.plant_id && item.status !== "planned" ? (
        <Button
          size="sm"
          className="shrink-0 h-8 rounded-lg"
          disabled={busyId === item.plant_id}
          onClick={() => onWater(item.plant_id!)}
        >
          Watered
        </Button>
      ) : null}
      {item.kind === "task" && item.status === "open" ? (
        <Button
          size="sm"
          variant="secondary"
          className="shrink-0 h-8 rounded-lg"
          disabled={busyId === item.id}
          onClick={() => onComplete(item.id)}
        >
          Done
        </Button>
      ) : null}
    </li>
  );
}
