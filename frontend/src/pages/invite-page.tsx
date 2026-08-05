import { useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api";

export function InvitePage() {
  const { token } = useParams<{ token: string }>();
  const { user, loading, acceptInvite } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!token) return <Navigate to="/" replace />;

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Accept invitation</CardTitle>
          <CardDescription>Sign in or register first, then open this invite link again.</CardDescription>
        </CardHeader>
        <CardContent className="flex gap-2">
          <Button asChild>
            <Link to="/login">Sign in</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link to="/register">Register</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (done) {
    return <Navigate to="/household" replace />;
  }

  async function accept() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await acceptInvite(token);
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not accept invite");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Join household</CardTitle>
        <CardDescription>
          Accepting will add you to the household with the role specified in the invite.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
        <Button onClick={() => void accept()} disabled={busy}>
          {busy ? "Joining…" : "Accept invitation"}
        </Button>
      </CardContent>
    </Card>
  );
}
