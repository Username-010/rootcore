/** Plain-language watering UX helpers. */

import type { WateringInfo } from "@/lib/types";

const URGENCY_COPY: Record<
  string,
  { title: string; hint: string; tone: "ok" | "warn" | "bad" }
> = {
  ok: {
    title: "No water needed yet",
    hint: "Soil should still be fine — wait for the next date.",
    tone: "ok",
  },
  soon: {
    title: "Water soon",
    hint: "Plan a drink in the next day or so.",
    tone: "warn",
  },
  due: {
    title: "Water today",
    hint: "This plant is due for a drink.",
    tone: "warn",
  },
  overdue: {
    title: "Overdue — water now",
    hint: "Water as soon as you can (check soil first if unsure).",
    tone: "bad",
  },
};

const FACTOR_PLAIN: Record<string, (detail?: string | null) => string> = {
  species_baseline: (d) =>
    d ? `Typical for this species (${d})` : "Typical schedule for this species",
  pot_size: (d) =>
    d?.includes("L") && Number.parseFloat(d) < 3
      ? "Small pot dries out faster"
      : d
        ? `Pot size: ${d}`
        : "Pot size affects drying speed",
  pot_material: (d) =>
    d && /terra|clay/i.test(d)
      ? "Terracotta dries soil faster"
      : d && /plastic|glazed/i.test(d)
        ? "Plastic/glazed pots hold moisture longer"
        : "Pot material affects drying",
  soil_type: (d) =>
    d && /free|drain|cactus/i.test(d)
      ? "Fast-draining soil dries quicker"
      : d && /moist|retent/i.test(d)
        ? "Moisture-holding soil stays wet longer"
        : "Soil type affects drying",
  environment: (d) =>
    d === "outdoor"
      ? "Outdoor — sun, wind and rain matter more"
      : d === "greenhouse"
        ? "Greenhouse — warmer, often drier air"
        : "Indoor placement",
  growth_stage: () => "Young plants often need water more often",
  season: (d) =>
    d?.toLowerCase().includes("winter")
      ? "Winter: plants usually drink less"
      : d?.toLowerCase().includes("summer")
        ? "Summer: plants usually drink more"
        : "Season of the year",
  weather_temp: (d) => (d ? `Temperature (${d})` : "Air temperature"),
  weather_humidity: (d) => (d ? `Humidity (${d})` : "Air humidity"),
  weather_precip: (d) =>
    d ? `Rain expected (${d}) — outdoor plants may wait` : "Rain in the forecast",
  user_learning: () => "Adjusted from your past feedback",
  manual_override: () => "You set a custom next-water date",
  paused: () => "Watering reminders are paused",
};

export function urgencyCopy(urgency: string) {
  return URGENCY_COPY[urgency] ?? URGENCY_COPY.ok;
}

export function formatNextWater(iso: string | null | undefined): string {
  if (!iso) return "Not sure yet — log a watering to start";
  const due = new Date(iso);
  const now = new Date();
  const diffMs = due.getTime() - now.getTime();
  const diffH = diffMs / 3_600_000;
  const day = due.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const time = due.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  if (diffH < -24) return `Was due ${day}`;
  if (diffH < 0) return `Due now · ideally ${time}`;
  if (diffH < 24) return `Today · ${time}`;
  if (diffH < 48) return `Tomorrow · ${day} ${time}`;
  return `${day} · ${time}`;
}

export function amountCopy(amount: string | null | undefined): string {
  switch (amount) {
    case "light":
      return "Light water";
    case "deep":
      return "Deep soak";
    case "normal":
    default:
      return "Normal water";
  }
}

/** Prefer server amount_label when present. */
export function amountHeadline(w: WateringInfo): string {
  if (w.amount_label) return w.amount_label;
  return amountCopy(w.recommended_amount);
}

export function amountDetail(w: WateringInfo): string {
  if (w.amount_howto) return w.amount_howto;
  if (w.volume_guide) return w.volume_guide;
  const base = amountCopy(w.recommended_amount);
  if (w.amount_ml) return `${base} · about ${w.amount_ml} ml`;
  return base;
}

export function whenDetail(w: WateringInfo): string {
  if (w.schedule_plain) return w.schedule_plain;
  const time = w.best_time_label || "Morning";
  const local = w.best_time_local ? ` (${w.best_time_local})` : "";
  return `${formatNextWater(w.next_due_at)} · ${time}${local}`;
}

export function plainFactors(watering: WateringInfo): string[] {
  return (watering.factors || [])
    .filter((f) => f.key !== "species_baseline" || watering.factors.length <= 3)
    .slice(0, 8)
    .map((f) => {
      const fn = FACTOR_PLAIN[f.key];
      if (fn) return fn(f.detail ?? null);
      return f.label;
    });
}

export function shortWhy(watering: WateringInfo): string {
  if (watering.weather_note) {
    const factors = plainFactors(watering).filter(
      (l) => !/temperature|humidity|rain/i.test(l),
    );
    return [watering.weather_note, ...factors.slice(0, 1)].join(" · ");
  }
  const lines = plainFactors(watering);
  if (lines.length === 0) return "Based on species and pot info.";
  return lines.slice(0, 2).join(" · ");
}
