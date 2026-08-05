import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

type Hit = {
  title: string;
  url: string;
  thumb_url: string;
  source: string;
};

export function PhotoSearchPicker({
  householdId,
  plantId,
  defaultQuery,
  onPicked,
  compact,
}: {
  householdId: string;
  plantId: string;
  defaultQuery?: string;
  onPicked: () => void | Promise<void>;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState(defaultQuery || "");
  const [results, setResults] = useState<Hit[]>([]);
  const [busy, setBusy] = useState(false);
  const [picking, setPicking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function search(query?: string) {
    setBusy(true);
    setError(null);
    setSearched(true);
    try {
      const res = await api.searchPlantPhotos(householdId, plantId, query ?? q);
      setResults(res.results);
      if (res.query && !q) setQ(res.query);
      if (res.results.length === 0) {
        setError("No free photos found — try another name or upload your own.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Search failed");
      setResults([]);
    } finally {
      setBusy(false);
    }
  }

  async function pick(hit: Hit) {
    setPicking(hit.url);
    setError(null);
    try {
      await api.setCoverFromUrl(householdId, plantId, {
        url: hit.url,
        caption: hit.title ? `Wikimedia · ${hit.title}` : "From Wikimedia",
      });
      setOpen(false);
      await onPicked();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not set photo");
    } finally {
      setPicking(null);
    }
  }

  if (!open) {
    return (
      <Button
        type="button"
        size="sm"
        variant={compact ? "outline" : "default"}
        className="rounded-xl"
        onClick={() => {
          setOpen(true);
          void search(defaultQuery || q || undefined);
        }}
      >
        {compact ? "Find photo" : "📷 Find / choose photo"}
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-3 text-left">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">Search free photos</p>
        <button
          type="button"
          className="text-xs text-muted-foreground hover:underline"
          onClick={() => setOpen(false)}
        >
          Close
        </button>
      </div>
      <p className="text-xs text-muted-foreground">
        Wikimedia / Wikipedia — free to use. Pick one for the cover.
      </p>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-1">
          <Label htmlFor={`photo-q-${plantId}`} className="text-xs">
            Search
          </Label>
          <Input
            id={`photo-q-${plantId}`}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g. Monstera deliciosa or lavender"
            className="rounded-xl h-9"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void search();
              }
            }}
          />
        </div>
        <Button
          type="button"
          size="sm"
          className="rounded-xl"
          disabled={busy}
          onClick={() => void search()}
        >
          {busy ? "Searching…" : "Search"}
        </Button>
      </div>
      {error && (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
      {searched && !busy && results.length > 0 && (
        <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {results.map((hit) => (
            <li key={hit.url}>
              <button
                type="button"
                disabled={picking !== null}
                onClick={() => void pick(hit)}
                className="group relative w-full overflow-hidden rounded-lg border border-border bg-muted aspect-square hover:ring-2 hover:ring-primary/40 disabled:opacity-50"
                title={hit.title}
              >
                <img
                  src={hit.thumb_url || hit.url}
                  alt={hit.title}
                  className="h-full w-full object-cover"
                  loading="lazy"
                  referrerPolicy="no-referrer"
                />
                <span className="absolute inset-x-0 bottom-0 bg-background/85 px-1 py-0.5 text-[9px] truncate opacity-0 group-hover:opacity-100">
                  {picking === hit.url ? "Saving…" : "Use this"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
