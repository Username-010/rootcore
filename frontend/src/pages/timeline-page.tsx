import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { CareEvent } from "@/lib/types";

export function TimelinePage() {
  const { activeHousehold } = useAuth();
  const [events, setEvents] = useState<CareEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editType, setEditType] = useState("");
  const [editWhen, setEditWhen] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    if (!activeHousehold) return;
    try {
      setEvents(await api.listEvents(activeHousehold.id, { limit: 100 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load timeline");
    }
  }, [activeHousehold]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!activeHousehold) {
    return <p className="text-sm text-muted-foreground">Select a household first.</p>;
  }

  function startEdit(ev: CareEvent) {
    setEditingId(ev.id);
    setEditType(ev.type);
    const d = new Date(ev.occurred_at);
    const pad = (n: number) => String(n).padStart(2, "0");
    setEditWhen(
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`,
    );
    const notes = typeof ev.payload?.notes === "string" ? ev.payload.notes : "";
    setEditNotes(notes);
  }

  async function saveEdit(eventId: string) {
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateEvent(activeHousehold.id, eventId, {
        type: editType,
        occurred_at: editWhen ? new Date(editWhen).toISOString() : undefined,
        notes: editNotes,
      });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update event");
    } finally {
      setBusy(false);
    }
  }

  async function removeEvent(eventId: string) {
    if (!activeHousehold) return;
    if (!confirm("Remove this care entry from history?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteEvent(activeHousehold.id, eventId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete event");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Timeline</h1>
        <p className="text-sm text-muted-foreground">
          Household care history — edit times, types, or remove mistakes.
        </p>
      </div>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No events yet.</p>
          ) : (
            <ol className="relative border-l border-border ml-2 space-y-4">
              {events.map((ev) => (
                <li key={ev.id} className="ml-4">
                  <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full bg-primary" />
                  {editingId === ev.id ? (
                    <div className="space-y-2 rounded-xl border border-border bg-card p-3 max-w-md">
                      <Input
                        value={editType}
                        onChange={(e) => setEditType(e.target.value)}
                        className="rounded-xl"
                        placeholder="Type (watered, fertilized…)"
                      />
                      <Input
                        type="datetime-local"
                        value={editWhen}
                        onChange={(e) => setEditWhen(e.target.value)}
                        className="rounded-xl"
                      />
                      <Input
                        value={editNotes}
                        onChange={(e) => setEditNotes(e.target.value)}
                        className="rounded-xl"
                        placeholder="Notes (optional)"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          className="rounded-xl"
                          disabled={busy}
                          onClick={() => void saveEdit(ev.id)}
                        >
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-xl"
                          onClick={() => setEditingId(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <time className="text-xs text-muted-foreground">
                        {new Date(ev.occurred_at).toLocaleString()}
                      </time>
                      <p className="text-sm font-medium capitalize">
                        {ev.type.replaceAll("_", " ")}
                        {ev.plant_nickname ? (
                          <>
                            {" · "}
                            <Link
                              className="text-primary hover:underline"
                              to={"/plants/" + ev.plant_id}
                            >
                              {ev.plant_nickname}
                            </Link>
                          </>
                        ) : null}
                      </p>
                      {typeof ev.payload?.notes === "string" && ev.payload.notes ? (
                        <p className="text-xs text-muted-foreground">{ev.payload.notes}</p>
                      ) : null}
                      {ev.actor_name ? (
                        <p className="text-xs text-muted-foreground">by {ev.actor_name}</p>
                      ) : null}
                      <div className="mt-1 flex gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 rounded-lg text-xs"
                          onClick={() => startEdit(ev)}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 rounded-lg text-xs text-destructive"
                          disabled={busy}
                          onClick={() => void removeEvent(ev.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    </>
                  )}
                </li>
              ))}
            </ol>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
