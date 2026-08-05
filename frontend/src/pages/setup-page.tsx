import { type ComponentProps, type FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { ApiError } from "@/lib/api";

export function SetupPage() {
  const { setup, initialized, user, loading } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [city, setCity] = useState("");
  const [locHint, setLocHint] = useState<string | null>(null);
  const [locBusy, setLocBusy] = useState(false);

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (initialized) return <Navigate to={user ? "/" : "/login"} replace />;

  function useBrowserLocation() {
    if (!navigator.geolocation) {
      setLocHint("Geolocation is not available — try city search below.");
      return;
    }
    setLocBusy(true);
    setLocHint("Requesting location permission…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(5));
        setLon(pos.coords.longitude.toFixed(5));
        setLocHint("Location set from your browser. You can edit it anytime in Settings.");
        setLocBusy(false);
      },
      (err) => {
        setLocBusy(false);
        const msg =
          err.code === err.PERMISSION_DENIED
            ? "Location permission denied. Allow location for this site, or search a city below."
            : err.code === err.POSITION_UNAVAILABLE
              ? "Position unavailable. Try city search instead."
              : err.code === err.TIMEOUT
                ? "Location timed out. Try city search instead."
                : "Could not read location — enter a city or lat/lon.";
        setLocHint(msg);
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 60_000 },
    );
  }

  async function lookupCity() {
    const q = city.trim();
    if (!q) {
      setLocHint("Type a city name first (e.g. Amsterdam).");
      return;
    }
    setLocBusy(true);
    setLocHint("Looking up city…");
    try {
      // Open-Meteo geocoding — free, no key
      const url =
        "https://geocoding-api.open-meteo.com/v1/search?count=1&language=en&format=json&name=" +
        encodeURIComponent(q);
      const res = await fetch(url);
      if (!res.ok) throw new Error("Geocoding failed");
      const data = (await res.json()) as {
        results?: Array<{ latitude: number; longitude: number; name: string; country?: string }>;
      };
      const hit = data.results?.[0];
      if (!hit) {
        setLocHint("No match for that city — try another spelling.");
        return;
      }
      setLat(hit.latitude.toFixed(5));
      setLon(hit.longitude.toFixed(5));
      setLocHint(
        `Set to ${hit.name}${hit.country ? ", " + hit.country : ""} (${hit.latitude.toFixed(2)}, ${hit.longitude.toFixed(2)}).`,
      );
    } catch {
      setLocHint("City lookup failed — enter lat/lon manually.");
    } finally {
      setLocBusy(false);
    }
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = new FormData(e.currentTarget);
    try {
      await setup({
        email: String(form.get("email") ?? ""),
        password: String(form.get("password") ?? ""),
        displayName: String(form.get("display_name") ?? ""),
        householdName: String(form.get("household_name") ?? "Home"),
        latitude: lat === "" ? null : Number(lat),
        longitude: lon === "" ? null : Number(lon),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Setup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="text-center space-y-1 pb-1">
        <p className="text-xs font-medium uppercase tracking-wider text-primary">First-time setup</p>
        <h1 className="text-2xl font-semibold tracking-tight">Welcome to PlantPilot</h1>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          Self-hosted plant care for your household. Your account and plants stay on this machine —
          they are not wiped by a normal restart.
        </p>
      </div>

      <Card className="shadow-md border-border/80">
        <CardHeader>
          <CardTitle>Create your admin account</CardTitle>
          <CardDescription>
            This runs once. Later opens go to login — not this screen — as long as the database is
            kept.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={(e) => void onSubmit(e)}>
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-foreground">Account</h2>
              <Field id="display_name" label="Your name" autoComplete="name" required />
              <Field
                id="email"
                label="Username or email"
                type="text"
                autoComplete="username"
                required
                placeholder="joe — no real email needed"
              />
              <Field
                id="password"
                label="Password (min 8 characters)"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
              />
              <Field id="household_name" label="Home name" defaultValue="Home" required />
            </section>

            <section className="space-y-3 rounded-xl border border-border bg-muted/40 p-4">
              <div>
                <h2 className="text-sm font-semibold">Location for weather</h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Free via Open-Meteo — <strong>no API key</strong>. Optional; set later in Settings
                  if you prefer.
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="City (e.g. Utrecht)"
                  className="rounded-xl"
                />
                <Button
                  type="button"
                  variant="secondary"
                  disabled={locBusy}
                  className="rounded-xl shrink-0"
                  onClick={() => void lookupCity()}
                >
                  Find city
                </Button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="lat">Latitude</Label>
                  <Input
                    id="lat"
                    inputMode="decimal"
                    placeholder="e.g. 52.09"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="lon">Longitude</Label>
                  <Input
                    id="lon"
                    inputMode="decimal"
                    placeholder="e.g. 5.12"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                  />
                </div>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={locBusy}
                onClick={useBrowserLocation}
                className="rounded-xl"
              >
                {locBusy ? "Working…" : "Use my current location"}
              </Button>
              {locHint && <p className="text-xs text-muted-foreground">{locHint}</p>}
            </section>

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            <Button type="submit" className="w-full h-11 text-base rounded-xl" disabled={submitting}>
              {submitting ? "Creating…" : "Start PlantPilot"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({
  id,
  label,
  ...props
}: { id: string; label: string } & ComponentProps<typeof Input>) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} name={id} {...props} className="rounded-xl" />
    </div>
  );
}
