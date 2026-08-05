import { type FormEvent, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api";

export function RegisterPage() {
  const { register, user, loading, initialized, registrationMode } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (initialized === false) return <Navigate to="/setup" replace />;
  if (user) return <Navigate to="/" replace />;
  if (registrationMode && registrationMode !== "open") {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Registration closed</CardTitle>
          <CardDescription>
            This instance only allows invite-based or closed registration. Ask a household admin
            for an invite link.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="secondary" className="w-full">
            <Link to="/login">Back to sign in</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = new FormData(e.currentTarget);
    try {
      await register(
        String(form.get("email") ?? ""),
        String(form.get("password") ?? ""),
        String(form.get("display_name") ?? ""),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create account</CardTitle>
        <CardDescription>Join this PlantPilot instance, then accept an invite or create a household.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={(e) => void onSubmit(e)}>
          <div className="space-y-1.5">
            <Label htmlFor="display_name">Display name</Label>
            <Input id="display_name" name="display_name" autoComplete="name" required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Username or email</Label>
            <Input
              id="email"
              name="email"
              type="text"
              autoComplete="username"
              required
              placeholder="Any login name — email optional"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>
          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Creating…" : "Register"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link className="text-primary underline-offset-2 hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
