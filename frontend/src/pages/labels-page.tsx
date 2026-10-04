import { Printer, Tag } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { FlowerLoader } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { LabelSheet, LabelSheetCard } from "@/lib/types";

export function LabelsPage() {
  const { activeHousehold } = useAuth();
  const [data, setData] = useState<LabelSheet | null>(null);
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
      setData(await api.labelSheet(activeHousehold.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load labels");
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

  return (
    <div className="space-y-6 print:space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between print:flex-row">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
            Stick on the pots
          </p>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Tag className="h-6 w-6 text-primary" />
            Labels
          </h1>
          <p className="text-sm text-muted-foreground mt-1 max-w-xl">
            {data.summary} Print, cut, tape. Times in {data.timezone}.
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

      {data.total === 0 ? (
        <Card>
          <CardContent className="py-8 text-sm text-muted-foreground">
            No plants yet. Add one, then print labels here.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 print:grid-cols-2">
          {data.cards.map((card) => (
            <LabelCard key={card.plant_id} card={card} />
          ))}
        </div>
      )}
    </div>
  );
}

function LabelCard({ card }: { card: LabelSheetCard }) {
  return (
    <div className="rounded-xl border px-3 py-3 min-h-[7rem] flex flex-col justify-between break-inside-avoid">
      <div>
        <p className="font-medium inline-flex items-center gap-1.5">
          <span>{card.emoji || "🪴"}</span>
          <span className="truncate">{card.nickname}</span>
        </p>
        {card.scientific_name ? (
          <p className="text-xs italic text-muted-foreground mt-1">{card.scientific_name}</p>
        ) : null}
        {card.common_name ? (
          <p className="text-xs text-muted-foreground">{card.common_name}</p>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground mt-2 capitalize">{card.environment}</p>
    </div>
  );
}
