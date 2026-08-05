import { type FormEvent, useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { Invitation, Member } from "@/lib/types";

export function HouseholdPage() {
  const {
    activeHousehold,
    households,
    setActiveHousehold,
    refreshHouseholds,
  } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rename, setRename] = useState("");

  const canManage =
    activeHousehold?.role === "owner" || activeHousehold?.role === "admin";
  const isOwner = activeHousehold?.role === "owner";

  useEffect(() => {
    setRename(activeHousehold?.name ?? "");
  }, [activeHousehold?.id, activeHousehold?.name]);

  const load = useCallback(async () => {
    if (!activeHousehold) {
      setMembers([]);
      setInvites([]);
      return;
    }
    setError(null);
    try {
      const m = await api.listMembers(activeHousehold.id);
      setMembers(m);
      if (canManage) {
        setInvites(await api.listInvitations(activeHousehold.id));
      } else {
        setInvites([]);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load household");
    }
  }, [activeHousehold, canManage]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onCreateHousehold(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    const form = new FormData(e.currentTarget);
    const name = String(form.get("name") ?? "Home").trim() || "Home";
    try {
      const h = await api.createHousehold({ name });
      await refreshHouseholds();
      setActiveHousehold(h);
      setMessage(`Created “${h.name}” and switched to it.`);
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create household");
    } finally {
      setBusy(false);
    }
  }

  async function onRename(e: FormEvent) {
    e.preventDefault();
    if (!activeHousehold || !isOwner) return;
    const name = rename.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateHousehold(activeHousehold.id, { name });
      await refreshHouseholds();
      setMessage("Home renamed.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not rename");
    } finally {
      setBusy(false);
    }
  }

  async function onInvite(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    setInviteLink(null);
    const form = new FormData(e.currentTarget);
    try {
      const inv = await api.createInvitation(activeHousehold.id, {
        email: String(form.get("email") || "") || undefined,
        role: String(form.get("role") || "member"),
      });
      if (inv.token) {
        setInviteLink(`${window.location.origin}/invite/${inv.token}`);
      }
      await load();
      e.currentTarget.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Invite failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Homes</h1>
        <p className="text-muted-foreground">
          Each home (household) has its own plants, map, and members. Switch from the top bar or
          here — create as many as you need (city garden, balcony, parents&apos; house…).
        </p>
      </div>

      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {message && <p className="text-sm text-primary">{message}</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your homes</CardTitle>
          <CardDescription>
            The dropdown in the header switches the active home. Use <strong>Open</strong> here to
            switch, or rename the active one below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {households.length === 0 ? (
            <p className="text-sm text-muted-foreground">No homes yet — create one below.</p>
          ) : (
            <ul className="divide-y divide-border text-sm">
              {households.map((h) => (
                <li key={h.id} className="py-2.5 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">
                      {h.name}
                      {activeHousehold?.id === h.id ? (
                        <span className="ml-2 text-xs font-normal text-primary">· active</span>
                      ) : null}
                    </p>
                    <p className="text-xs text-muted-foreground capitalize">Your role: {h.role}</p>
                  </div>
                  {activeHousehold?.id !== h.id && (
                    <Button
                      size="sm"
                      variant="secondary"
                      className="rounded-xl"
                      onClick={() => {
                        setActiveHousehold(h);
                        setMessage(`Switched to “${h.name}”.`);
                      }}
                    >
                      Open
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {activeHousehold && isOwner && (
            <form className="flex flex-col sm:flex-row gap-2 pt-2 border-t border-border" onSubmit={(e) => void onRename(e)}>
              <div className="flex-1 space-y-1">
                <Label htmlFor="rename">Rename active home</Label>
                <Input
                  id="rename"
                  value={rename}
                  onChange={(e) => setRename(e.target.value)}
                  className="rounded-xl"
                  required
                />
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={busy || rename.trim() === activeHousehold.name} className="rounded-xl">
                  Save name
                </Button>
              </div>
            </form>
          )}
          {activeHousehold && !isOwner && (
            <p className="text-xs text-muted-foreground">Only the owner can rename this home.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Add another home</CardTitle>
          <CardDescription>You become the owner. Plants and maps stay separate per home.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col sm:flex-row gap-2" onSubmit={(e) => void onCreateHousehold(e)}>
            <Input
              name="name"
              placeholder="e.g. Balcony, Allotment, Cabin"
              required
              className="sm:flex-1 rounded-xl"
            />
            <Button type="submit" disabled={busy} className="rounded-xl">
              Create home
            </Button>
          </form>
        </CardContent>
      </Card>

      {activeHousehold && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Members — {activeHousehold.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border text-sm">
                {members.map((m) => (
                  <li key={m.user_id} className="flex justify-between py-2 gap-2">
                    <div>
                      <p className="font-medium">{m.display_name}</p>
                      <p className="text-muted-foreground text-xs">{m.email}</p>
                    </div>
                    <span className="capitalize text-muted-foreground">{m.role}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {canManage && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Invite someone</CardTitle>
                <CardDescription>
                  Share the one-time link. Optional login restriction (username or email) locks the
                  invite to that account.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <form
                  className="grid gap-3 sm:grid-cols-[1fr_auto_auto]"
                  onSubmit={(e) => void onInvite(e)}
                >
                  <div className="space-y-1.5">
                    <Label htmlFor="email">Username or email (optional)</Label>
                    <Input
                      id="email"
                      name="email"
                      type="text"
                      placeholder="friend or friend@example.com"
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="role">Role</Label>
                    <select
                      id="role"
                      name="role"
                      defaultValue="member"
                      className="flex h-10 w-full rounded-xl border border-border bg-card px-3 text-sm"
                    >
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <div className="flex items-end">
                    <Button type="submit" disabled={busy} className="rounded-xl">
                      Create invite
                    </Button>
                  </div>
                </form>
                {inviteLink && (
                  <div className="rounded-lg bg-muted p-3 text-sm break-all">
                    <p className="font-medium mb-1">Invite link (copy now — token shown once)</p>
                    <code>{inviteLink}</code>
                  </div>
                )}
                {invites.length > 0 && (
                  <ul className="text-sm divide-y divide-border">
                    {invites.map((i) => (
                      <li key={i.id} className="py-2 flex justify-between gap-2">
                        <span>
                          {i.email ?? "Open link"} · {i.role}
                        </span>
                        <span className="text-muted-foreground">
                          {i.accepted_at ? "Accepted" : "Pending"}
                        </span>
                      </li>
                    ))}
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
