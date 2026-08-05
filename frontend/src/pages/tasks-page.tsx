import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { CareTask, Plant } from "@/lib/types";

export function TasksPage() {
  const { activeHousehold } = useAuth();
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("open");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDue, setEditDue] = useState("");

  const load = useCallback(async () => {
    if (!activeHousehold) return;
    setError(null);
    try {
      const [t, p] = await Promise.all([
        api.listTasks(activeHousehold.id, status),
        api.listPlants(activeHousehold.id, { limit: 100 }),
      ]);
      setTasks(t);
      setPlants(p.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load tasks");
    }
  }, [activeHousehold, status]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!activeHousehold) {
    return <p className="text-sm text-muted-foreground">Select a household first.</p>;
  }

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    // Capture form element before await — React nulls e.currentTarget after yield
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    const plantId = String(form.get("plant_id") || "");
    const dueRaw = String(form.get("due_at") || "").trim();
    let dueAt: string | null = null;
    if (dueRaw) {
      const d = new Date(dueRaw);
      dueAt = Number.isNaN(d.getTime()) ? null : d.toISOString();
    }
    try {
      await api.createTask(activeHousehold.id, {
        title: String(form.get("title") || ""),
        type: String(form.get("type") || "custom"),
        plant_ids: plantId ? [plantId] : [],
        due_at: dueAt,
      });
      formEl.reset();
      setError(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create task");
    } finally {
      setBusy(false);
    }
  }

  function startEdit(task: CareTask) {
    setEditingId(task.id);
    setEditTitle(task.title);
    if (task.due_at) {
      const d = new Date(task.due_at);
      const pad = (n: number) => String(n).padStart(2, "0");
      setEditDue(
        `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`,
      );
    } else setEditDue("");
  }

  async function saveEdit(taskId: string) {
    if (!activeHousehold) return;
    setBusy(true);
    try {
      await api.updateTask(activeHousehold.id, taskId, {
        title: editTitle,
        due_at: editDue ? new Date(editDue).toISOString() : null,
        clear_due: !editDue,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update task");
    } finally {
      setBusy(false);
    }
  }

  async function removeTask(taskId: string) {
    if (!activeHousehold) return;
    if (!confirm("Remove this task permanently?")) return;
    setBusy(true);
    try {
      await api.deleteTask(activeHousehold.id, taskId, true);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete task");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tasks</h1>
          <p className="text-sm text-muted-foreground">
            Care work you can complete, edit, or remove. Dashboard only counts due soon — not every
            future engine task.
          </p>
        </div>
        <div className="flex gap-2">
          {(["open", "done", "all"] as const).map((s) => (
            <Button
              key={s}
              size="sm"
              variant={status === s ? "default" : "outline"}
              className="rounded-xl"
              onClick={() => setStatus(s)}
            >
              {s}
            </Button>
          ))}
        </div>
      </div>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">New task</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => void onCreate(e)}>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" name="title" required placeholder="Repot Monstera" className="rounded-xl" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="type">Type</Label>
              <select
                id="type"
                name="type"
                className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm"
                defaultValue="custom"
              >
                <option value="water">Water</option>
                <option value="fertilize">Fertilize</option>
                <option value="prune">Prune</option>
                <option value="repot">Repot</option>
                <option value="propagate">Propagate</option>
                <option value="harvest">Harvest</option>
                <option value="clean">Clean</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="due_at">Due</Label>
              <Input id="due_at" name="due_at" type="datetime-local" className="rounded-xl" />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="plant_id">Plant (optional)</Label>
              <select
                id="plant_id"
                name="plant_id"
                className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm"
                defaultValue=""
              >
                <option value="">Household task</option>
                {plants.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nickname}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" disabled={busy} className="sm:col-span-2 rounded-xl">
              {busy ? "Creating…" : "Create task"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <ul className="space-y-2">
        {tasks.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tasks in this filter.</p>
        ) : (
          tasks.map((task) => (
            <li
              key={task.id}
              className="flex flex-col gap-2 rounded-xl border border-border bg-card/90 p-3 sm:flex-row sm:items-center sm:justify-between shadow-sm"
            >
              {editingId === task.id ? (
                <div className="flex-1 space-y-2 w-full">
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="rounded-xl"
                  />
                  <Input
                    type="datetime-local"
                    value={editDue}
                    onChange={(e) => setEditDue(e.target.value)}
                    className="rounded-xl"
                  />
                  <div className="flex gap-2">
                    <Button size="sm" className="rounded-xl" disabled={busy} onClick={() => void saveEdit(task.id)}>
                      Save
                    </Button>
                    <Button size="sm" variant="outline" className="rounded-xl" onClick={() => setEditingId(null)}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="min-w-0">
                    <p className="font-medium">{task.title}</p>
                    <p className="text-xs text-muted-foreground capitalize">
                      {task.type} · {task.status} · {task.source}
                      {task.due_at ? " · due " + new Date(task.due_at).toLocaleString() : ""}
                    </p>
                    {task.description ? (
                      <p className="text-xs text-muted-foreground mt-0.5">{task.description}</p>
                    ) : null}
                    {task.plant_ids[0] ? (
                      <Link
                        className="text-xs text-primary hover:underline"
                        to={"/plants/" + task.plant_ids[0]}
                      >
                        View plant
                      </Link>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-1.5 shrink-0">
                    {task.status === "open" && (
                      <Button
                        size="sm"
                        className="rounded-xl"
                        onClick={() =>
                          void api
                            .completeTask(activeHousehold.id, task.id)
                            .then(load)
                            .catch((err) => {
                              setError(err instanceof ApiError ? err.detail : "Failed");
                            })
                        }
                      >
                        Complete
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="secondary"
                      className="rounded-xl"
                      onClick={() => startEdit(task)}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-xl text-destructive"
                      disabled={busy}
                      onClick={() => void removeTask(task.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </>
              )}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
